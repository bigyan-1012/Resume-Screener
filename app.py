import os
import re
import json
import logging
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

# ──────────────────────────────────────────────────────────────────────────────
# Logging configuration
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("app")

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
    """Handle PDF resume upload — validate, store, and return success immediately."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized. Please log in."}), 401

    if 'resume' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files['resume']

    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Only PDF files are allowed."}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logger.info(f"Resume uploaded successfully: {filename}")
        return jsonify({
            "success": True,
            "message": "Resume uploaded successfully!",
            "filename": filename
        })
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({"success": False, "error": "Upload failed. Please try again."}), 500


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


def analyze_resume_against_jd(resume_text, jd_text):
    """Compute Cosine Similarity match percentage, ATS readiness, and extract matched vs missing skills."""
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
            "ats_score": 0
        }

    # Calculate TF-IDF Cosine Similarity
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform([clean_jd, clean_resume])
        feature_names = vectorizer.get_feature_names_out()
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        match_percentage = round(float(similarity) * 100, 1)
    except Exception as e:
        logger.error(f"TF-IDF calculation failed: {e}")
        match_percentage = 0.0
        feature_names = []
        tfidf_matrix = None

    # Categorize match quality
    if match_percentage >= 75:
        grade = "Strong Match"
        recommendation = "Excellent candidate alignment! Resume strongly reflects key requirements and technical keywords of the job description."
    elif match_percentage >= 50:
        grade = "Moderate Match"
        recommendation = "Good baseline alignment. Candidate possesses several core skills, but could benefit from highlighting missing job requirements."
    elif match_percentage >= 25:
        grade = "Low Match"
        recommendation = "Fair match. Several key skills and qualifications from the job description appear missing or unemphasized."
    else:
        grade = "Weak Match"
        recommendation = "Low keyword alignment. Significant skill gaps detected relative to the target job description."

    # Extract skill overlap
    resume_skills = set(extract_skills_from_text(clean_resume))
    jd_skills = set(extract_skills_from_text(clean_jd))

    matched_skills = sorted(list(resume_skills.intersection(jd_skills)))
    missing_skills = sorted(list(jd_skills.difference(resume_skills)))

    # Identify key JD terms and whether they exist in resume
    top_keywords = []
    if tfidf_matrix is not None and len(feature_names) > 0:
        jd_vector = tfidf_matrix[0].toarray()[0]
        top_indices = jd_vector.argsort()[::-1][:10]
        for idx in top_indices:
            word = feature_names[idx]
            score = round(float(jd_vector[idx]), 3)
            if score > 0:
                in_resume = word in clean_resume
                top_keywords.append({
                    "word": word.title(),
                    "score": score,
                    "in_resume": in_resume
                })

    # Evaluate ATS formatting
    ats_info = check_ats_formatting(resume_text)

    return {
        "match_percentage": match_percentage,
        "grade": grade,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "top_keywords": top_keywords,
        "recommendation": recommendation,
        "ats_analysis": ats_info,
        "ats_score": ats_info["ats_score"],
        "resume_word_count": len(clean_resume.split()),
        "jd_word_count": len(clean_jd.split())
    }


# ──────────────────────────────────────────────────────────────────────────────
# Analysis & History Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Extract text from resume PDF, process NLP, compute match against Job Description, and store history."""
    if 'username' not in session:
        return jsonify({"success": False, "error": "Unauthorized. Please log in."}), 401

    data = request.get_json() or {}
    filename = data.get('filename')
    jd_text = data.get('job_description', '').strip()
    job_title = data.get('job_title', 'General Match').strip() or 'General Match'

    if not filename:
        return jsonify({"success": False, "error": "No resume file specified."}), 400

    if not jd_text:
        return jsonify({"success": False, "error": "Please provide a job description."}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Uploaded resume file not found."}), 404

    # Extract text from uploaded PDF
    resume_text = extract_text_from_pdf(filepath)
    if not resume_text:
        return jsonify({"success": False, "error": "Unable to extract readable text from PDF."}), 400

    result = analyze_resume_against_jd(resume_text, jd_text)
    result['success'] = True
    result['filename'] = filename
    result['job_title'] = job_title

    # Log analysis result to Database (MySQL or SQLite)
    try:
        username = session.get('username')
        inserted_id = db_query(
            "INSERT INTO analyses (username, filename, job_title, match_score, grade, matched_skills, missing_skills, ats_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                username, filename, job_title,
                result['match_percentage'], result['grade'],
                json.dumps(result['matched_skills']),
                json.dumps(result['missing_skills']),
                result['ats_score']
            ),
            commit=True
        )
        result['id'] = inserted_id
    except Exception as e:
        logger.warning(f"Unable to store analysis record in database: {e}")

    return jsonify(result)


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

