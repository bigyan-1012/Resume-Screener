import os
import re
import json
import logging
import secrets
import urllib.parse
import requests
import sqlite3
import mysql.connector
import pypdf
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

# ──────────────────────────────────────────────────────────────────────────────
# Flask Application
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.secret_key = os.environ.get('SECRET_KEY', 'screener-matching-secure-key-9a8f')

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

# ──────────────────────────────────────────────────────────────────────────────
# Database Configuration & Dual-Mode Engine (MySQL + SQLite Fallback)
# ──────────────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Nabeen@1427',
}
DB_NAME = 'resume_screener'
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resume_screener.db')
USE_MYSQL = False


def init_db():
    """Initialize database tables using MySQL if available, or SQLite fallback."""
    global USE_MYSQL
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.commit()
        cursor.close()
        conn.close()

        db_conn_config = DB_CONFIG.copy()
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
        conn.commit()
        cursor.close()
        conn.close()
        USE_MYSQL = True
        logger.info("MySQL database and tables initialized successfully.")
    except Exception as e:
        logger.warning(f"MySQL connection failed ({e}). Initializing SQLite fallback.")
        USE_MYSQL = False
        conn = sqlite3.connect(SQLITE_DB_PATH)
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
        conn.commit()
        conn.close()
        logger.info(f"SQLite fallback database initialized at {SQLITE_DB_PATH}.")


# Run DB initialization at module load
init_db()


def get_db():
    """Get a database connection for the current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        if USE_MYSQL:
            db_conn_config = DB_CONFIG.copy()
            db_conn_config['database'] = DB_NAME
            db = g._database = mysql.connector.connect(**db_conn_config)
        else:
            db = g._database = sqlite3.connect(SQLITE_DB_PATH)
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
def landing():
    logged_in = 'username' in session
    username = session.get('username', '')
    return render_template('landing.html', logged_in=logged_in, username=username)


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('landing', _anchor='dashboard'))


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
# Entry Point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)

