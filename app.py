import os
import re
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import secrets
import urllib.parse
import requests
import sqlite3
import mysql.connector
import pypdf
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import (
    Flask, request, jsonify, render_template,
    session, redirect, url_for, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from engine import (
    KnowledgeBaseRetriever, ResumeParser, TaxonomyMatcher,
    MatchingScorer, EvidenceRecommender
)

# Load environment variables from .env
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Logging configuration
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("app")

# Initialize Phase 3B Occupational Knowledge Base Matching Engine
kb_retriever = KnowledgeBaseRetriever()
resume_parser = ResumeParser()
taxonomy_matcher = TaxonomyMatcher(retriever=kb_retriever)
matching_scorer = MatchingScorer()
evidence_recommender = EvidenceRecommender()

# Base & Runtime Environment Detection
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

# On Vercel / serverless microVMs, the app root is read-only.
# Only /tmp is writable for ephemeral storage and SQLite.
if IS_VERCEL or not os.access(BASE_DIR, os.W_OK):
    WRITABLE_DIR = '/tmp'
else:
    WRITABLE_DIR = BASE_DIR

# ──────────────────────────────────────────────────────────────────────────────
# Flask Application
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.secret_key = os.environ.get('SECRET_KEY', 'hirehive-screener-matching-secure-key-9a8f')

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(WRITABLE_DIR, 'uploads')
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception:
        pass
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

# ──────────────────────────────────────────────────────────────────────────────
# Customer Support & Email Configuration
# ──────────────────────────────────────────────────────────────────────────────
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@hirehive.ai').strip()
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '').strip()
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'HireHive Support <support@hirehive.ai>').strip()

# Optional SMTP Settings (alternative to Resend)
MAIL_SERVER = os.environ.get('MAIL_SERVER', '').strip()
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '').strip()
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '').strip()
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', SUPPORT_EMAIL).strip()

# ──────────────────────────────────────────────────────────────────────────────
# Database Configuration & Dual-Mode Engine (MySQL + SQLite Fallback)
# ──────────────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'connection_timeout': 2,
}
DB_NAME = os.environ.get('DB_NAME', 'resume_screener')
SQLITE_DB_PATH = os.path.join(WRITABLE_DIR, 'resume_screener.db')
USE_MYSQL = False


def init_db():
    """Initialize database tables using MySQL if available, or SQLite fallback."""
    global USE_MYSQL, SQLITE_DB_PATH

    # On Vercel / Serverless, localhost MySQL does not exist. Fail fast to avoid Lambda timeouts.
    skip_mysql = IS_VERCEL and DB_CONFIG.get('host') in ('localhost', '127.0.0.1', '', None)

    if not skip_mysql:
        try:
            db_conn_cfg = DB_CONFIG.copy()
            db_conn_cfg['connection_timeout'] = 2
            conn = mysql.connector.connect(**db_conn_cfg)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            conn.commit()
            cursor.close()
            conn.close()

            db_conn_config = db_conn_cfg.copy()
            db_conn_config['database'] = DB_NAME
            conn = mysql.connector.connect(**db_conn_config)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    job_title VARCHAR(255),
                    match_score FLOAT NOT NULL,
                    grade VARCHAR(50),
                    matched_skills TEXT,
                    missing_skills TEXT,
                    ats_score INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ticket_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(150) NOT NULL,
                    subject VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'open',
                    email_status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    ip_address VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.commit()
            cursor.close()
            conn.close()
            USE_MYSQL = True
            logger.info("MySQL database and tables initialized successfully.")
            return
        except Exception as e:
            logger.warning(f"MySQL connection skipped or failed ({e}). Initializing SQLite fallback.")
            USE_MYSQL = False
    else:
        USE_MYSQL = False

    # Resilient SQLite fallback across writable candidate locations
    candidate_db_paths = [
        SQLITE_DB_PATH,
        os.path.join('/tmp', 'resume_screener.db'),
        ':memory:'
    ]
    for db_path in candidate_db_paths:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    job_title TEXT,
                    match_score REAL NOT NULL,
                    grade TEXT,
                    matched_skills TEXT,
                    missing_skills TEXT,
                    ats_score INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    email_status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            SQLITE_DB_PATH = db_path
            logger.info(f"SQLite database initialized successfully at {SQLITE_DB_PATH}.")
            break
        except Exception as sqle:
            logger.warning(f"Failed to initialize SQLite at {db_path}: {sqle}")


# Run DB initialization at module load
init_db()


def get_db():
    """Get a database connection for the current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        if USE_MYSQL:
            db_conn_config = DB_CONFIG.copy()
            db_conn_config['database'] = DB_NAME
            db_conn_config['connection_timeout'] = 2
            db = g._database = mysql.connector.connect(**db_conn_config)
        else:
            try:
                db = g._database = sqlite3.connect(SQLITE_DB_PATH)
            except Exception:
                db = g._database = sqlite3.connect('/tmp/resume_screener.db')
            db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection at the end of each request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """Database query wrapper compatible with both MySQL and SQLite."""
    db = get_db()
    if USE_MYSQL:
        cursor = db.cursor(dictionary=True)
        cursor.execute(query, params)
        if commit:
            db.commit()
            lastid = cursor.lastrowid
            cursor.close()
            return lastid
        if fetchone:
            res = cursor.fetchone()
            cursor.close()
            return res
        if fetchall:
            res = cursor.fetchall()
            cursor.close()
            return res
        cursor.close()
        return None
    else:
        sqlite_query = query.replace('%s', '?')
        cursor = db.cursor()
        cursor.execute(sqlite_query, params)
        if commit:
            db.commit()
            lastid = cursor.lastrowid
            cursor.close()
            return lastid
        if fetchone:
            row = cursor.fetchone()
            res = dict(row) if row else None
            cursor.close()
            return res
        if fetchall:
            rows = cursor.fetchall()
            res = [dict(r) for r in rows] if rows else []
            cursor.close()
            return res
        cursor.close()
        return None


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ──────────────────────────────────────────────────────────────────────────────
# Authentication Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('landing'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = "Username and password are required."
        else:
            try:
                user = db_query("SELECT * FROM users WHERE username = %s", (username,), fetchone=True)
                if user and check_password_hash(user['password_hash'], password):
                    session['username'] = username
                    return redirect(url_for('landing'))
                else:
                    error = "Invalid username or password."
            except Exception as e:
                error = f"Database error: {e}"

    return render_template('auth.html', action='login', error=error)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect(url_for('landing'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = "Username and password are required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            try:
                existing = db_query("SELECT id FROM users WHERE username = %s", (username,), fetchone=True)
                if existing:
                    error = f"Username '{username}' is already taken."
                else:
                    hashed_pw = generate_password_hash(password)
                    db_query(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (username, hashed_pw),
                        commit=True
                    )
                    session['username'] = username
                    return redirect(url_for('landing'))
            except Exception as e:
                error = f"Database error: {e}"

    return render_template('auth.html', action='signup', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


# ──────────────────────────────────────────────────────────────────────────────
# Google OAuth 2.0 Configuration & Handlers
# ──────────────────────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')



def get_google_redirect_uri():
    """Returns the absolute callback URL for Google OAuth."""
    explicit_uri = os.environ.get('GOOGLE_REDIRECT_URI')
    if explicit_uri:
        return explicit_uri
    return url_for('google_callback', _external=True)


@app.route('/login/google')
def google_login():
    """Initiates Google OAuth 2.0 authorization code flow."""
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    
    redirect_uri = get_google_redirect_uri()
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@app.route('/login/google/callback')
def google_callback():
    """Handles Google OAuth 2.0 callback, exchanges code for tokens, and logs user in."""
    error = request.args.get('error')
    if error:
        logger.warning(f"Google OAuth authorization error: {error}")
        return render_template('auth.html', action='login', error=f"Google authentication failed: {error}")
        
    code = request.args.get('code')
    state = request.args.get('state')
    
    # CSRF State Verification
    stored_state = session.pop('oauth_state', None)
    if not state or state != stored_state:
        logger.warning("Google OAuth state mismatch detected.")
        return render_template('auth.html', action='login', error="Security error: Invalid state token. Please try again.")

    if not code:
        return render_template('auth.html', action='login', error="Authorization code missing from Google response.")

    redirect_uri = get_google_redirect_uri()

    # Exchange Authorization Code for Tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }

    try:
        token_resp = requests.post(token_url, data=token_data, timeout=10)
        token_json = token_resp.json()

        if 'error' in token_json:
            err_msg = token_json.get('error_description', token_json['error'])
            logger.error(f"Google token exchange failed: {err_msg}")
            return render_template('auth.html', action='login', error=f"Google Token Exchange Error: {err_msg}")

        access_token = token_json.get('access_token')
        if not access_token:
            return render_template('auth.html', action='login', error="Failed to acquire access token from Google.")

        # Retrieve User Profile Data from Google
        user_info_resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        user_info = user_info_resp.json()

        email = user_info.get('email', '')
        name = user_info.get('name', '') or user_info.get('given_name', '')
        
        if not email:
            return render_template('auth.html', action='login', error="Could not retrieve email from Google profile.")

        # Determine target username (name or email prefix)
        base_username = email.split('@')[0] if email else name.replace(' ', '_')
        if not base_username:
            base_username = f"google_user_{user_info.get('id', '1234')[:6]}"

        # Search for existing user by username
        existing_user = db_query("SELECT * FROM users WHERE username = %s", (base_username,), fetchone=True)
        
        if not existing_user:
            alt_user = db_query("SELECT * FROM users WHERE username = %s", (email,), fetchone=True)
            if alt_user:
                username_to_use = email
            else:
                username_to_use = base_username
                dummy_hash = generate_password_hash(secrets.token_urlsafe(16))
                try:
                    db_query(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (username_to_use, dummy_hash),
                        commit=True
                    )
                except Exception:
                    username_to_use = email
                    db_query(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (username_to_use, dummy_hash),
                        commit=True
                    )
        else:
            username_to_use = base_username

        # Set User Session
        session['username'] = username_to_use
        session['user_email'] = email
        session['user_avatar'] = user_info.get('picture', '')
        logger.info(f"User '{username_to_use}' authenticated successfully via Google OAuth.")

        return redirect(url_for('landing', _anchor='dashboard'))

    except Exception as e:
        logger.error(f"Google OAuth Exception: {e}", exc_info=True)
        return render_template('auth.html', action='login', error=f"Google authentication system error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Page Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/')
@app.route('/api/index')
def landing():
    logged_in = 'username' in session
    username = session.get('username', '')
    return render_template('landing.html', logged_in=logged_in, username=username)


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('landing', _anchor='dashboard'))


@app.route('/contact')
@app.route('/api/index/contact')
def contact_page():
    logged_in = 'username' in session
    username = session.get('username', '')
    return render_template('landing.html', logged_in=logged_in, username=username, active_tab='contact')


# ──────────────────────────────────────────────────────────────────────────────
# Resume Upload Route
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload_resume():
    """Handle PDF resume upload — validate, store, and return success immediately (single or multiple)."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized. Please log in."}), 401

    files = request.files.getlist('resumes') or request.files.getlist('resume')
    if not files or len(files) == 0 or files[0].filename == '':
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    if len(files) > 10:
        return jsonify({"success": False, "error": "Maximum 10 resumes can be uploaded at a time in HR mode."}), 400

    saved_filenames = []
    for file in files:
        if file and file.filename != '':
            if not allowed_file(file.filename):
                return jsonify({"success": False, "error": f"Invalid file '{file.filename}'. Only PDF files are allowed."}), 400
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            saved_filenames.append(filename)

    if not saved_filenames:
        return jsonify({"success": False, "error": "No valid PDF files saved."}), 400

    logger.info(f"Resumes uploaded successfully: {saved_filenames}")
    return jsonify({
        "success": True,
        "message": f"{len(saved_filenames)} resume(s) uploaded successfully!",
        "filename": saved_filenames[0],
        "filenames": saved_filenames
    })



# ──────────────────────────────────────────────────────────────────────────────
# Core NLP, Skill Matching & TF-IDF Cosine Similarity Engine
# ──────────────────────────────────────────────────────────────────────────────

KNOWN_SKILLS = [
    # Programming Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "ruby", "go", "golang", "rust",
    "php", "swift", "kotlin", "r", "matlab", "scala", "perl", "sql", "html", "css", "bash", "shell",
    # Frameworks & Libraries
    "react", "react.js", "angular", "vue", "vue.js", "next.js", "node.js", "express", "django",
    "flask", "fastapi", "spring", "spring boot", "asp.net", "laravel", "rails", "graphql", "rest api",
    # Databases & Storage
    "mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite", "oracle", "elasticsearch",
    "dynamodb", "cassandra", "firebase",
    # Cloud, DevOps & Tools
    "aws", "amazon web services", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "jenkins", "terraform", "ansible", "ci/cd", "git", "github", "gitlab", "bitbucket", "linux",
    # AI / ML / Data Science
    "machine learning", "deep learning", "ai", "artificial intelligence", "pandas", "numpy",
    "scikit-learn", "sklearn", "tensorflow", "pytorch", "opencv", "nlp", "natural language processing",
    "data analysis", "data science", "tableau", "power bi", "keras",
    # Core Concepts & Software Engineering
    "agile", "scrum", "kanban", "microservices", "system design", "object oriented programming",
    "oop", "test driven development", "tdd", "unit testing", "cybersecurity", "ui/ux", "figma"
]


def extract_text_from_pdf(filepath):
    """Extract clean raw text from a PDF document using pypdf."""
    try:
        reader = pypdf.PdfReader(filepath)
        text_runs = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_runs.append(extracted)
        return "\n".join(text_runs).strip()
    except Exception as e:
        logger.error(f"Error reading PDF file {filepath}: {e}")
        return ""


def clean_text(text):
    """Normalize text by stripping URLs, numbers/symbols, and whitespace."""
    if not text:
        return ""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s\+#\.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_skills_from_text(text):
    """Extract known technical skills from clean text."""
    cleaned = clean_text(text)
    found = set()
    for skill in KNOWN_SKILLS:
        pattern = r'(?:\b|_)' + re.escape(skill) + r'(?:\b|_)'
        if re.search(pattern, cleaned):
            if skill in ['sql', 'aws', 'gcp', 'ai', 'nlp', 'ui/ux', 'oop', 'tdd', 'ci/cd', 'k8s', 'r']:
                display_name = skill.upper()
            elif skill in ['c++', 'c#']:
                display_name = skill.upper()
            elif '.' in skill:
                parts = skill.split('.')
                display_name = parts[0].title() + '.' + parts[1]
            else:
                display_name = skill.title()
            found.add(display_name)
    return sorted(list(found))


def check_ats_formatting(resume_text):
    """Evaluate structural readiness of resume text for ATS parsers."""
    if not resume_text:
        return {"ats_score": 0, "checks": [], "recommendations": ["No readable text found."]}

    text_lower = resume_text.lower()
    checks = []
    recommendations = []
    earned_points = 0

    # 1. Email Check (20 pts)
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text))
    if has_email:
        earned_points += 20
        checks.append({"name": "Contact Email", "passed": True, "details": "Found valid email address."})
    else:
        checks.append({"name": "Contact Email", "passed": False, "details": "No contact email detected."})
        recommendations.append("Include a clear email address at the top of your resume.")

    # 2. Phone Check (15 pts)
    has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+\d{1,3}[-.\s]?\d{6,14}', resume_text))
    if has_phone:
        earned_points += 15
        checks.append({"name": "Phone Number", "passed": True, "details": "Found phone contact number."})
    else:
        checks.append({"name": "Phone Number", "passed": False, "details": "No phone number detected."})
        recommendations.append("Add a direct phone number for recruiter communication.")

    # 3. Work Experience Section Check (20 pts)
    exp_keywords = ["experience", "employment", "work history", "career", "professional experience"]
    has_exp = any(k in text_lower for k in exp_keywords)
    if has_exp:
        earned_points += 20
        checks.append({"name": "Work Experience Section", "passed": True, "details": "Detected Work Experience heading."})
    else:
        checks.append({"name": "Work Experience Section", "passed": False, "details": "Work Experience section heading missing."})
        recommendations.append("Use standard headings like 'Work Experience' or 'Professional Experience'.")

    # 4. Education Section Check (20 pts)
    edu_keywords = ["education", "university", "bachelor", "master", "degree", "college", "b.s", "m.s", "phd", "diploma"]
    has_edu = any(k in text_lower for k in edu_keywords)
    if has_edu:
        earned_points += 20
        checks.append({"name": "Education Section", "passed": True, "details": "Detected Education section or academic degree."})
    else:
        checks.append({"name": "Education Section", "passed": False, "details": "Education section heading missing."})
        recommendations.append("Add an 'Education' section detailing relevant degrees and institutions.")

    # 5. Technical Skills Section Check (15 pts)
    skill_keywords = ["skills", "technologies", "tech stack", "tools", "proficiencies", "competencies"]
    has_skills = any(k in text_lower for k in skill_keywords)
    if has_skills:
        earned_points += 15
        checks.append({"name": "Skills Section", "passed": True, "details": "Explicit Technical Skills heading found."})
    else:
        checks.append({"name": "Skills Section", "passed": False, "details": "No explicit 'Skills' section heading."})
        recommendations.append("Group your technical skills under a dedicated 'Technical Skills' heading.")

    # 6. Word Count & Length Check (10 pts)
    words = clean_text(resume_text).split()
    word_count = len(words)
    if 200 <= word_count <= 1200:
        earned_points += 10
        checks.append({"name": "Optimal Document Length", "passed": True, "details": f"Ideal length ({word_count} words)."})
    elif word_count < 200:
        checks.append({"name": "Optimal Document Length", "passed": False, "details": f"Document is concise ({word_count} words)."})
        recommendations.append("Expand section descriptions to detail achievements and project outcomes.")
    else:
        checks.append({"name": "Optimal Document Length", "passed": False, "details": f"Document is lengthy ({word_count} words)."})
        recommendations.append("Condense resume to 1-2 focused pages for optimal recruiter scanning.")

    if not recommendations:
        recommendations.append("Excellent layout! Resume complies with standard ATS scanning conventions.")

    return {
        "ats_score": earned_points,
        "checks": checks,
        "recommendations": recommendations
    }


def analyze_resume_against_jd(resume_text, jd_text, job_title="General Match"):
    """Compute JobFitScore match percentage using Phase 3B engine, ATS readiness, and extract matched vs missing skills."""
    clean_resume = clean_text(resume_text)
    clean_jd = clean_text(jd_text)

    if not clean_resume or not clean_jd:
        return {
            "match_percentage": 0,
            "grade": "Insufficient Data",
            "matched_skills": [],
            "missing_skills": [],
            "top_keywords": [],
            "recommendation": "Could not extract text from resume or job description.",
            "ats_analysis": check_ats_formatting(resume_text),
            "ats_score": 0,
            "resume_word_count": len(clean_resume.split()) if clean_resume else 0,
            "jd_word_count": len(clean_jd.split()) if clean_jd else 0,
        }

    # 1. Parse document structure & negation
    parsed = resume_parser.parse(resume_text)

    # 2. Extract candidate skills using taxonomy matcher
    cand_skills = taxonomy_matcher.extract_skills(
        parsed["clean_text"], negated_terms=parsed["negated_terms"]
    )

    # 3. Extract target job requirements (ESCO / O*NET taxonomy)
    target_reqs = taxonomy_matcher.extract_target_requirements(job_title, jd_text)

    # 4. Score job fit using calibrated multi-dimensional feature model
    score_res = matching_scorer.compute_score(
        resume_text=parsed["clean_text"],
        jd_text=clean_jd,
        candidate_skills=cand_skills,
        essential_skills=target_reqs["essential_skills"],
        optional_skills=target_reqs["optional_skills"],
        job_title=job_title,
        retrieved_requirements=target_reqs,
    )

    # 5. Generate evidence-based recommendations
    rec_res = evidence_recommender.generate_recommendations(
        candidate_skills=cand_skills,
        essential_skills=target_reqs["essential_skills"],
        optional_skills=target_reqs["optional_skills"],
        experience_bullets=parsed["experience_bullets"],
        negated_terms=parsed["negated_terms"],
    )

    # 6. Evaluate ATS formatting
    ats_info = check_ats_formatting(resume_text)

    return {
        "match_percentage": score_res["match_percentage"],
        "grade": score_res["grade"],
        "matched_skills": rec_res["matched_skills"],
        "missing_skills": rec_res["missing_skills"],
        "top_keywords": score_res["top_keywords"],
        "recommendation": score_res["recommendation"],
        "ats_analysis": ats_info,
        "ats_score": ats_info["ats_score"],
        "resume_word_count": len(clean_resume.split()),
        "jd_word_count": len(clean_jd.split()),
        "context_gaps": rec_res["context_gaps"],
        "feature_vector": score_res["feature_vector"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Analysis & History Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Extract text from resume PDF(s), process NLP, compute match against Job Description, rank candidates, and store history."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized. Please log in."}), 401

    data = request.get_json() or {}
    filenames = data.get('filenames') or []
    single_filename = data.get('filename')
    if single_filename and not filenames:
        filenames = [single_filename]

    jd_text = data.get('job_description', '').strip()
    job_title = data.get('job_title', 'General Match').strip() or 'General Match'
    mode = data.get('mode', 'candidate')

    if not filenames or len(filenames) == 0:
        return jsonify({"success": False, "error": "No resume file specified."}), 400

    if not jd_text:
        return jsonify({"success": False, "error": "Please provide a job description."}), 400

    username = session.get('username')
    results = []

    for fname in filenames:
        sec_fname = secure_filename(fname)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], sec_fname)
        if not os.path.exists(filepath):
            logger.warning(f"File not found during analysis: {sec_fname}")
            continue

        resume_text = extract_text_from_pdf(filepath)
        if not resume_text:
            logger.warning(f"Could not extract text from PDF: {sec_fname}")
            continue

        res = analyze_resume_against_jd(resume_text, jd_text, job_title=job_title)
        res['filename'] = sec_fname
        res['job_title'] = job_title

        # Store analysis result in Database
        try:
            inserted_id = db_query(
                "INSERT INTO analyses (username, filename, job_title, match_score, grade, matched_skills, missing_skills, ats_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    username, sec_fname, job_title,
                    res['match_percentage'], res['grade'],
                    json.dumps(res['matched_skills']),
                    json.dumps(res['missing_skills']),
                    res['ats_score']
                ),
                commit=True
            )
            res['id'] = inserted_id
        except Exception as e:
            logger.warning(f"Unable to store analysis record in database: {e}")

        results.append(res)

    if not results:
        return jsonify({"success": False, "error": "Unable to extract readable text from uploaded resume PDF(s)."}), 400

    # Rank candidates from HIGH to LOW based on JobFit match percentage (and secondary sort by ATS score)
    results.sort(key=lambda x: (x.get('match_percentage', 0), x.get('ats_score', 0)), reverse=True)
    for idx, cand in enumerate(results, start=1):
        cand['rank'] = idx

    top_cand = results[0]

    return jsonify({
        "success": True,
        "mode": mode,
        "is_batch": len(results) > 1,
        "total_candidates": len(results),
        "candidates": results,
        "filename": top_cand['filename'],
        "job_title": top_cand['job_title'],
        "match_percentage": top_cand['match_percentage'],
        "grade": top_cand['grade'],
        "matched_skills": top_cand['matched_skills'],
        "missing_skills": top_cand['missing_skills'],
        "top_keywords": top_cand['top_keywords'],
        "recommendation": top_cand['recommendation'],
        "ats_analysis": top_cand['ats_analysis'],
        "ats_score": top_cand['ats_score'],
        "resume_word_count": top_cand['resume_word_count'],
        "jd_word_count": top_cand['jd_word_count']
    })



@app.route('/api/history', methods=['GET'])
def get_history():
    """Fetch past resume screening history for current user."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized."}), 401

    username = session.get('username')
    try:
        rows = db_query(
            "SELECT id, filename, job_title, match_score, grade, matched_skills, missing_skills, ats_score, created_at FROM analyses WHERE username = %s ORDER BY created_at DESC",
            (username,),
            fetchall=True
        )
        history = []
        for r in rows:
            matched = json.loads(r['matched_skills']) if r.get('matched_skills') else []
            missing = json.loads(r['missing_skills']) if r.get('missing_skills') else []
            history.append({
                "id": r['id'],
                "filename": r['filename'],
                "job_title": r['job_title'] or 'General Match',
                "match_score": r['match_score'],
                "grade": r['grade'] or 'N/A',
                "matched_skills": matched,
                "missing_skills": missing,
                "ats_score": r.get('ats_score', 0),
                "created_at": str(r['created_at'])
            })
        return jsonify({"success": True, "history": history})
    except Exception as e:
        logger.error(f"Error fetching analysis history: {e}")
        return jsonify({"success": False, "error": f"Failed to retrieve history: {e}"}), 500


@app.route('/api/history/<int:analysis_id>', methods=['DELETE'])
def delete_history_item(analysis_id):
    """Delete a single analysis history item."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized."}), 401

    username = session.get('username')
    try:
        db_query(
            "DELETE FROM analyses WHERE id = %s AND username = %s",
            (analysis_id, username),
            commit=True
        )
        return jsonify({"success": True, "message": "History entry deleted."})
    except Exception as e:
        logger.error(f"Error deleting history item: {e}")
        return jsonify({"success": False, "error": "Failed to delete history entry."}), 500


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear all analysis history for current user."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized."}), 401

    username = session.get('username')
    try:
        db_query(
            "DELETE FROM analyses WHERE username = %s",
            (username,),
            commit=True
        )
        return jsonify({"success": True, "message": "All history cleared."})
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({"success": False, "error": "Failed to clear history."}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Automated Customer Support & Contact Us Automation
# ──────────────────────────────────────────────────────────────────────────────

contact_rate_limit_store = {}


def is_contact_rate_limited(identifier: str, max_requests: int = 5, window_seconds: int = 600) -> bool:
    """Sliding-window in-memory rate limiter for contact form submissions."""
    now = time.time()
    history = contact_rate_limit_store.get(identifier, [])
    history = [t for t in history if now - t < window_seconds]
    if len(history) >= max_requests:
        contact_rate_limit_store[identifier] = history
        return True
    history.append(now)
    contact_rate_limit_store[identifier] = history
    return False


def generate_ticket_id() -> str:
    """Generates a unique HireHive Support Ticket Reference (e.g., HH-TK-7C38A1D2)."""
    return f"HH-TK-{secrets.token_hex(4).upper()}"


def build_support_notification_html(ticket_id: str, name: str, email: str, subject: str, message: str) -> str:
    """Generates professional HTML email sent to support@hirehive.ai."""
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    safe_email = email.replace('<', '&lt;').replace('>', '&gt;')
    safe_subject = subject.replace('<', '&lt;').replace('>', '&gt;')
    safe_msg = message.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f121d; color: #e5e7eb; padding: 24px;">
    <div style="max-width: 600px; margin: 0 auto; background: #1a1e2e; border: 1px solid #374151; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        <div style="border-bottom: 2px solid #FFD000; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="color: #FFD000; margin: 0; font-size: 20px;">📬 New HireHive Support Ticket</h2>
            <p style="color: #9ca3af; margin: 4px 0 0 0; font-size: 13px;">Reference ID: <strong style="color: #ffffff;">{ticket_id}</strong></p>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
            <tr>
                <td style="padding: 8px 0; color: #9ca3af; width: 120px;">Customer:</td>
                <td style="padding: 8px 0; color: #ffffff; font-weight: 600;">{safe_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #9ca3af;">Email:</td>
                <td style="padding: 8px 0;"><a href="mailto:{safe_email}" style="color: #FFD000; text-decoration: none;">{safe_email}</a></td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #9ca3af;">Subject:</td>
                <td style="padding: 8px 0; color: #ffffff;">{safe_subject}</td>
            </tr>
        </table>
        <div style="background: #111422; border-left: 4px solid #FFD000; padding: 16px; border-radius: 6px; margin-bottom: 20px;">
            <div style="font-size: 12px; text-transform: uppercase; color: #9ca3af; margin-bottom: 8px; font-weight: 700;">Customer Message</div>
            <div style="line-height: 1.6; color: #f3f4f6; font-size: 14px;">{safe_msg}</div>
        </div>
        <div style="font-size: 12px; color: #6b7280; text-align: center; border-top: 1px solid #374151; padding-top: 16px;">
            Automated notification generated by HireHive Support Engine.
        </div>
    </div>
</body>
</html>"""


def build_customer_ack_html(ticket_id: str, name: str, subject: str) -> str:
    """Generates customer acknowledgment email confirming ticket creation."""
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    safe_subject = subject.replace('<', '&lt;').replace('>', '&gt;')

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b0d14; color: #e5e7eb; padding: 24px;">
    <div style="max-width: 600px; margin: 0 auto; background: #141724; border: 1px solid rgba(255, 208, 0, 0.25); border-radius: 14px; padding: 28px; box-shadow: 0 12px 30px rgba(0,0,0,0.6);">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; background: rgba(255, 208, 0, 0.15); border: 1px solid #FFD000; border-radius: 50%; width: 50px; height: 50px; line-height: 50px; font-size: 24px;">🐝</div>
            <h2 style="color: #ffffff; margin: 12px 0 4px 0; font-size: 22px;">We've Received Your Request</h2>
            <p style="color: #9ca3af; margin: 0; font-size: 14px;">HireHive Customer Support & ATS Advisory</p>
        </div>
        <p style="color: #e5e7eb; font-size: 15px; line-height: 1.6;">Hi <strong>{safe_name}</strong>,</p>
        <p style="color: #d1d5db; font-size: 14px; line-height: 1.6;">
            Thank you for reaching out to HireHive! Your inquiry regarding <em>"{safe_subject}"</em> has been received and logged in our system.
        </p>
        <div style="background: rgba(255, 208, 0, 0.08); border: 1px solid rgba(255, 208, 0, 0.3); border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
            <span style="display: block; font-size: 12px; text-transform: uppercase; color: #FFD000; font-weight: 700; letter-spacing: 1px;">Your Support Reference ID</span>
            <span style="display: block; font-size: 22px; font-weight: 800; color: #ffffff; margin-top: 4px; font-family: monospace;">{ticket_id}</span>
        </div>
        <p style="color: #9ca3af; font-size: 13px; line-height: 1.6;">
            Our support engineers and product specialists review tickets during business hours and typically respond within <strong>24 hours</strong>. If you have any additional information to add, simply reply to this email or cite your Ticket ID.
        </p>
        <hr style="border: none; border-top: 1px solid #2a2f42; margin: 24px 0;" />
        <div style="font-size: 12px; color: #6b7280; line-height: 1.5;">
            Best regards,<br>
            <strong style="color: #ffffff;">The HireHive Team</strong><br>
            <a href="mailto:{SUPPORT_EMAIL}" style="color: #FFD000; text-decoration: none;">{SUPPORT_EMAIL}</a>
        </div>
    </div>
</body>
</html>"""


def send_contact_emails(ticket_id: str, name: str, email: str, subject: str, message: str):
    """
    Dispatches:
      1. Notification to support@hirehive.ai
      2. Acknowledgment to customer
    Supports Resend API, SMTP, or graceful Demo Mode fallback.
    Returns: (email_status: str, error_message: str | None)
    """
    notify_html = build_support_notification_html(ticket_id, name, email, subject, message)
    ack_html = build_customer_ack_html(ticket_id, name, subject)

    # 1. Resend API Integration
    if RESEND_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            res_notify = requests.post(
                "https://api.resend.com/emails",
                headers=headers,
                json={
                    "from": RESEND_FROM_EMAIL or "onboarding@resend.dev",
                    "to": [SUPPORT_EMAIL],
                    "subject": f"[HireHive Support] Ticket {ticket_id}: {subject}",
                    "html": notify_html,
                    "reply_to": email
                },
                timeout=8
            )
            res_ack = requests.post(
                "https://api.resend.com/emails",
                headers=headers,
                json={
                    "from": RESEND_FROM_EMAIL or "onboarding@resend.dev",
                    "to": [email],
                    "subject": f"[HireHive Support] We received your request ({ticket_id})",
                    "html": ack_html
                },
                timeout=8
            )
            if res_notify.status_code in (200, 201) and res_ack.status_code in (200, 201):
                logger.info(f"Emails successfully dispatched via Resend for ticket {ticket_id}.")
                return ("sent", None)
            else:
                err_text = f"Resend response codes: notify={res_notify.status_code}, ack={res_ack.status_code}."
                logger.warning(f"Resend dispatch warning for ticket {ticket_id}: {err_text}")
                return ("sent_with_warnings", err_text)
        except Exception as e:
            logger.error(f"Failed to dispatch email via Resend for ticket {ticket_id}: {e}")
            return ("failed", str(e))

    # 2. SMTP Integration
    elif MAIL_SERVER and MAIL_USERNAME:
        try:
            server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=12)
            server.ehlo()
            if MAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            if MAIL_PASSWORD:
                server.login(MAIL_USERNAME, MAIL_PASSWORD)

            # Send Notification to Support
            msg_notify = MIMEMultipart('alternative')
            msg_notify['Subject'] = f"[HireHive Support] Ticket {ticket_id}: {subject}"
            msg_notify['From'] = MAIL_DEFAULT_SENDER
            msg_notify['To'] = SUPPORT_EMAIL
            msg_notify['Reply-To'] = email
            msg_notify.attach(MIMEText(notify_html, 'html'))
            server.sendmail(MAIL_DEFAULT_SENDER, [SUPPORT_EMAIL], msg_notify.as_string())

            # Send Acknowledgment to Customer
            msg_ack = MIMEMultipart('alternative')
            msg_ack['Subject'] = f"[HireHive Support] We received your request ({ticket_id})"
            msg_ack['From'] = MAIL_DEFAULT_SENDER
            msg_ack['To'] = email
            msg_ack.attach(MIMEText(ack_html, 'html'))
            server.sendmail(MAIL_DEFAULT_SENDER, [email], msg_ack.as_string())

            server.quit()
            logger.info(f"Emails successfully dispatched via SMTP for ticket {ticket_id}.")
            return ("sent", None)
        except Exception as e:
            logger.error(f"Failed to dispatch email via SMTP for ticket {ticket_id}: {e}")
            return ("failed", str(e))

    # 3. Demo Mode (Local / Unconfigured Mail)
    else:
        logger.info(
            f"[DEMO MODE] Support ticket {ticket_id} registered. "
            f"Sender: {name} <{email}>. Subject: '{subject}'. "
            f"Message: '{message[:60]}...'. Notification logged to server console."
        )
        return ("demo_mode", None)


@app.route('/api/contact', methods=['POST'])
def submit_contact():
    """Submit a customer support request, validate, generate ticket ID, save to DB, and send notifications."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    # Honeypot spam trap
    honeypot = data.get('hp_field', '').strip() or data.get('hp_website', '').strip()
    if honeypot:
        logger.warning(f"Contact submission blocked by honeypot from IP: {request.remote_addr}")
        return jsonify({
            "success": True,
            "ticket_id": generate_ticket_id(),
            "message": "Thank you! Your support ticket has been received.",
            "email_status": "demo_mode"
        }), 200

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    subject = data.get('subject', '').strip() or 'General Support Inquiry'
    message = data.get('message', '').strip()

    # Validations
    if not name or len(name) < 2 or len(name) > 100:
        return jsonify({"success": False, "error": "Please provide your name (2 to 100 characters)."}), 400

    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not email or not re.match(email_regex, email) or len(email) > 150:
        return jsonify({"success": False, "error": "Please provide a valid email address."}), 400

    if not subject or len(subject) < 3 or len(subject) > 200:
        return jsonify({"success": False, "error": "Subject must be between 3 and 200 characters."}), 400

    if not message or len(message) < 10 or len(message) > 5000:
        return jsonify({"success": False, "error": "Message must be between 10 and 5000 characters."}), 400

    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1')
    if is_contact_rate_limited(f"ip:{client_ip}") or is_contact_rate_limited(f"email:{email.lower()}"):
        return jsonify({
            "success": False,
            "error": "You have submitted too many requests recently. Please wait a few minutes before trying again."
        }), 429

    ticket_id = generate_ticket_id()
    email_status, error_msg = send_contact_emails(ticket_id, name, email, subject, message)

    try:
        db_query(
            """INSERT INTO support_tickets 
               (ticket_id, name, email, subject, message, status, email_status, error_message, ip_address) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (ticket_id, name, email, subject, message, 'open', email_status, error_msg, client_ip),
            commit=True
        )
        logger.info(f"Support ticket {ticket_id} created for {email} ({name}). Email status: {email_status}")
    except Exception as e:
        logger.error(f"Error saving support ticket to database: {e}")
        return jsonify({"success": False, "error": "Failed to store ticket in database."}), 500

    return jsonify({
        "success": True,
        "ticket_id": ticket_id,
        "message": f"Thank you, {name}! Your ticket ({ticket_id}) has been registered. Our support team will follow up shortly.",
        "email_status": email_status
    }), 201


@app.route('/api/contact/status/<ticket_id>', methods=['GET'])
def get_ticket_status(ticket_id):
    """Check the status of a specific ticket by reference ID."""
    clean_id = ticket_id.strip()
    try:
        ticket = db_query(
            "SELECT ticket_id, name, subject, status, email_status, created_at FROM support_tickets WHERE ticket_id = %s",
            (clean_id,),
            fetchone=True
        )
        if not ticket:
            return jsonify({"success": False, "error": "Ticket not found."}), 404

        return jsonify({
            "success": True,
            "ticket": {
                "ticket_id": ticket['ticket_id'],
                "name": ticket['name'],
                "subject": ticket['subject'],
                "status": ticket['status'],
                "email_status": ticket.get('email_status', 'pending'),
                "created_at": str(ticket['created_at'])
            }
        })
    except Exception as e:
        logger.error(f"Error fetching ticket status: {e}")
        return jsonify({"success": False, "error": "Failed to look up ticket."}), 500


@app.route('/api/contact/tickets', methods=['GET'])
def list_support_tickets():
    """Retrieve recent support tickets for logged-in administration review."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized."}), 401

    try:
        tickets = db_query(
            "SELECT id, ticket_id, name, email, subject, status, email_status, created_at FROM support_tickets ORDER BY id DESC LIMIT 50",
            fetchall=True
        )
        return jsonify({"success": True, "tickets": tickets or []})
    except Exception as e:
        logger.error(f"Error loading support tickets: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve support tickets."}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)

