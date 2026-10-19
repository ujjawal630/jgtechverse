import csv
import hmac
import io
import os
import re
import secrets
import sqlite3
import time
import uuid
import qrcode
import base64
import shutil
import tempfile

from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Flask,
    Response,
    abort,
    flash,
    g,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    from supabase import create_client as create_supabase_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


# ==================================================
# APPLICATION CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

# On serverless platforms like Vercel, the app directory is read-only.
# Dynamic data (database, uploads, generated QR codes, secret key) is stored in /tmp.
if os.environ.get("VERCEL"):
    DATA_DIR = Path(tempfile.gettempdir())
    bundled_db = BASE_DIR / "techverse.db"
    dest_db = DATA_DIR / "techverse.db"
    if bundled_db.exists() and not dest_db.exists():
        shutil.copy2(bundled_db, dest_db)
else:
    DATA_DIR = BASE_DIR

DB_PATH = DATA_DIR / "techverse.db"
UPLOAD_DIR = DATA_DIR / "private_uploads"
QR_DIR = DATA_DIR / "qr_codes"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
QR_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

app.config["MAX_CONTENT_LENGTH"] = 120 * 1024 * 1024

MAX_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

ARENAS = [
    "Buddhi",
    "Fiontar",
    "Talos",
    "Pegasus",
    "Promethia",
    "Mercatus",
]

ARENA_METADATA = {
    "Buddhi": {
        "title": "Buddhi AI Model Building & Innovation Challenge",
        "category": "Artificial Intelligence & Machine Learning",
        "theme": "AI Model Building & Predictive Systems",
        "department": "Department of Artificial Intelligence & Data Science, JG University",
        "icon": "🤖",
        "code_prefix": "BUD"
    },
    "Fiontar": {
        "title": "Fiontar Startup & Innovation Summit",
        "category": "Startup & Entrepreneurship",
        "theme": "Startup & Innovation Incubation",
        "department": "Center for Innovation, Incubation & Entrepreneurship (CIIE), JG University",
        "icon": "💡",
        "code_prefix": "FIO"
    },
    "Talos": {
        "title": "Talos Robotic Engineering Arena",
        "category": "Robotics & Automation",
        "theme": "Robotic Arena, Embedded Systems & Hardware",
        "department": "Department of Robotics & Mechatronics, JG University",
        "icon": "⚙️",
        "code_prefix": "TAL"
    },
    "Pegasus": {
        "title": "Pegasus Aerial Robotics & Drone Fest",
        "category": "Aerospace & Drone Technology",
        "theme": "Drone Fest & Aerial Systems Engineering",
        "department": "Department of Aerospace & Drone Technology, JG University",
        "icon": "🚁",
        "code_prefix": "PEG"
    },
    "Promethia": {
        "title": "Promethia Competitive Coding Challenge",
        "category": "Software Engineering & Algorithmic Problem Solving",
        "theme": "Coding Challenge & Software Architecture",
        "department": "Department of Computer Science & Engineering, JG University",
        "icon": "💻",
        "code_prefix": "PRO"
    },
    "Mercatus": {
        "title": "Mercatus Trading & Financial Analytics",
        "category": "FinTech & Financial Analytics",
        "theme": "Trading & Financial Analytics Modeling",
        "department": "School of Management & Financial Analytics, JG University",
        "icon": "📈",
        "code_prefix": "MER"
    }
}


DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if HAS_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
        try:
            _supabase_client = create_supabase_client(SUPABASE_URL, SUPABASE_KEY)
            return _supabase_client
        except Exception as e:
            app.logger.warning("Supabase client init error: %s", e)
    return None

def is_postgres():
    return bool(DATABASE_URL and HAS_PSYCOPG2)


class PgCursorWrapper:
    def __init__(self, raw_cursor):
        self.raw = raw_cursor
        self.lastrowid = None

    @staticmethod
    def _clean_sql(sql):
        cleaned_sql = sql.replace("?", "%s")
        cleaned_sql = re.sub(
            r'GROUP_CONCAT\s*\(\s*DISTINCT\s+([^,)]+)\)',
            r"STRING_AGG(DISTINCT \1, ', ')",
            cleaned_sql,
            flags=re.IGNORECASE
        )
        cleaned_sql = re.sub(
            r'GROUP_CONCAT\s*\(\s*([^,]+),\s*([^)]+)\)',
            r"STRING_AGG(\1, \2)",
            cleaned_sql,
            flags=re.IGNORECASE
        )
        cleaned_sql = re.sub(
            r'GROUP_CONCAT\s*\(\s*([^)]+)\)',
            r"STRING_AGG(\1, ', ')",
            cleaned_sql,
            flags=re.IGNORECASE
        )
        return cleaned_sql

    def execute(self, sql, params=None):
        cleaned_sql = self._clean_sql(sql)
        is_insert = cleaned_sql.strip().upper().startswith("INSERT INTO")
        if is_insert and "RETURNING" not in cleaned_sql.upper():
            cleaned_sql = cleaned_sql.rstrip().rstrip(";") + " RETURNING id;"
            if params:
                self.raw.execute(cleaned_sql, params)
            else:
                self.raw.execute(cleaned_sql)
            try:
                row = self.raw.fetchone()
                if row:
                    self.lastrowid = row[0]
            except Exception:
                pass
            return self

        if params:
            self.raw.execute(cleaned_sql, params)
        else:
            self.raw.execute(cleaned_sql)
        return self

    def executemany(self, sql, seq_of_parameters):
        cleaned_sql = self._clean_sql(sql)
        self.raw.executemany(cleaned_sql, seq_of_parameters)
        return self

    def fetchone(self):
        return self.raw.fetchone()

    def fetchall(self):
        return self.raw.fetchall()

    def __iter__(self):
        return iter(self.raw)


class PgConnectionWrapper:
    def __init__(self, raw_conn):
        self.raw = raw_conn

    def cursor(self):
        return PgCursorWrapper(self.raw.cursor(cursor_factory=DictCursor))

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(self, sql, seq_of_parameters):
        cur = self.cursor()
        return cur.executemany(sql, seq_of_parameters)

    def executescript(self, sql):
        cur = self.raw.cursor()
        cur.execute(sql)
        self.raw.commit()
        cur.close()

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def get_db():
    if is_postgres():
        raw_conn = psycopg2.connect(DATABASE_URL)
        return PgConnectionWrapper(raw_conn)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


# ==================================================
# DATABASE INITIALIZATION
# Keeps existing tables and registrations
# ==================================================

def init_db():
    conn = get_db()
    if is_postgres():
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS teams (
                    id SERIAL PRIMARY KEY,
                    registration_code TEXT UNIQUE,
                    team_name TEXT NOT NULL,
                    team_number TEXT NOT NULL,
                    college_name TEXT DEFAULT 'JG University',
                    college_city TEXT DEFAULT 'Ahmedabad',
                    college_dept TEXT DEFAULT '',
                    leader_name TEXT NOT NULL,
                    leader_email TEXT NOT NULL,
                    leader_phone TEXT NOT NULL,
                    leader_section TEXT DEFAULT '',
                    leader_year TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Pending',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS members (
                    id SERIAL PRIMARY KEY,
                    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    section TEXT NOT NULL,
                    year TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS arenas (
                    id SERIAL PRIMARY KEY,
                    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                    arena_name TEXT NOT NULL,
                    problem_statement TEXT NOT NULL,
                    proposed_solution TEXT NOT NULL,
                    github_link TEXT
                );

                CREATE TABLE IF NOT EXISTS uploads (
                    id SERIAL PRIMARY KEY,
                    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                    project_id INTEGER,
                    arena_name TEXT NOT NULL DEFAULT 'General',
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                    arena_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    problem_statement TEXT NOT NULL,
                    proposed_solution TEXT NOT NULL,
                    github_link TEXT NOT NULL,
                    flagged_for_review INTEGER NOT NULL DEFAULT 0,
                    review_notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'judge',
                    arenas TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_members_team_id ON members(team_id);
                CREATE INDEX IF NOT EXISTS idx_arenas_team_id ON arenas(team_id);
                CREATE INDEX IF NOT EXISTS idx_projects_team_id ON projects(team_id);
                CREATE INDEX IF NOT EXISTS idx_projects_arena ON projects(arena_name);
                CREATE INDEX IF NOT EXISTS idx_uploads_team_id ON uploads(team_id);
                CREATE INDEX IF NOT EXISTS idx_teams_code ON teams(registration_code);
            """)
        finally:
            conn.close()
        return

    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_code TEXT UNIQUE,
                team_name TEXT NOT NULL,
                team_number TEXT NOT NULL,
                college_name TEXT DEFAULT 'JG University',
                college_city TEXT DEFAULT 'Ahmedabad',
                college_dept TEXT DEFAULT '',
                leader_name TEXT NOT NULL,
                leader_email TEXT NOT NULL,
                leader_phone TEXT NOT NULL,
                leader_section TEXT DEFAULT '',
                leader_year TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                section TEXT NOT NULL,
                year TEXT NOT NULL,
                FOREIGN KEY (team_id)
                    REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS arenas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                arena_name TEXT NOT NULL,
                problem_statement TEXT NOT NULL,
                proposed_solution TEXT NOT NULL,
                github_link TEXT,
                FOREIGN KEY (team_id)
                    REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                arena_name TEXT NOT NULL DEFAULT 'General',
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                FOREIGN KEY (team_id)
                    REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                arena_name TEXT NOT NULL,
                title TEXT NOT NULL,
                problem_statement TEXT NOT NULL,
                proposed_solution TEXT NOT NULL,
                github_link TEXT NOT NULL,
                flagged_for_review INTEGER NOT NULL DEFAULT 0,
                review_notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id)
                    REFERENCES teams(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_members_team_id ON members(team_id);
            CREATE INDEX IF NOT EXISTS idx_arenas_team_id ON arenas(team_id);
            CREATE INDEX IF NOT EXISTS idx_projects_team_id ON projects(team_id);
            CREATE INDEX IF NOT EXISTS idx_projects_arena ON projects(arena_name);
            CREATE INDEX IF NOT EXISTS idx_uploads_team_id ON uploads(team_id);
            CREATE INDEX IF NOT EXISTS idx_teams_code ON teams(registration_code);
        """)

        # Migration 1: ensure affiliation and academic columns exist in existing teams table
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(teams)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if "college_name" not in existing_cols:
            conn.execute("ALTER TABLE teams ADD COLUMN college_name TEXT DEFAULT 'JG University'")
        if "college_city" not in existing_cols:
            conn.execute("ALTER TABLE teams ADD COLUMN college_city TEXT DEFAULT 'Ahmedabad'")
        if "college_dept" not in existing_cols:
            conn.execute("ALTER TABLE teams ADD COLUMN college_dept TEXT DEFAULT ''")
        if "leader_section" not in existing_cols:
            conn.execute("ALTER TABLE teams ADD COLUMN leader_section TEXT DEFAULT ''")
        if "leader_year" not in existing_cols:
            conn.execute("ALTER TABLE teams ADD COLUMN leader_year TEXT DEFAULT ''")

        # Migration 2: ensure project_id column exists in uploads table
        cursor.execute("PRAGMA table_info(uploads)")
        upload_cols = {row[1] for row in cursor.fetchall()}
        if "project_id" not in upload_cols:
            conn.execute("ALTER TABLE uploads ADD COLUMN project_id INTEGER DEFAULT NULL")

        # Migration 3: idempotent backfill of legacy arena submissions into projects table
        cursor.execute("SELECT id, team_id, arena_name, problem_statement, proposed_solution, github_link FROM arenas ORDER BY id")
        legacy_arenas = cursor.fetchall()
        for a in legacy_arenas:
            arena_id, team_id, arena_name, problem, solution, github = a
            existing_p = cursor.execute(
                "SELECT id FROM projects WHERE team_id = ? AND arena_name = ? AND problem_statement = ?",
                (team_id, arena_name, problem)
            ).fetchone()
            if not existing_p:
                flagged = 0
                notes = []
                if not github:
                    flagged = 1
                    notes.append("Legacy record missing GitHub URL")
                elif "github.com" not in github.lower():
                    flagged = 1
                    notes.append("Legacy record has non-compliant GitHub URL")

                meta = ARENA_METADATA.get(arena_name, {})
                title = meta.get("title", f"{arena_name} Challenge Project")
                cursor.execute(
                    """
                    INSERT INTO projects (team_id, arena_name, title, problem_statement, proposed_solution, github_link, flagged_for_review, review_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (team_id, arena_name, title, problem, solution, github or "", flagged, "; ".join(notes))
                )
                proj_id = cursor.lastrowid
            else:
                proj_id = existing_p[0]

            cursor.execute(
                "UPDATE uploads SET project_id = ? WHERE team_id = ? AND arena_name = ? AND (project_id IS NULL OR project_id = 0)",
                (proj_id, team_id, arena_name)
            )

        conn.commit()

    finally:
        conn.close()


init_db()


def generate_unique_registration_code(conn):
    """
    Generate a unique, random 4-digit registration code formatted as TV26-XXXX (1000 to 9999).
    Uses secrets for cryptographic randomness and checks the database to prevent collisions.
    Existing registration codes (including legacy TV26-0000X) are preserved.
    """
    max_retries = 300
    for _ in range(max_retries):
        code_int = secrets.randbelow(9000) + 1000  # 1000 - 9999 inclusive
        candidate = f"TV26-{code_int}"
        exists = conn.execute(
            "SELECT 1 FROM teams WHERE registration_code = ?",
            (candidate,)
        ).fetchone()
        if not exists:
            return candidate

    raise RuntimeError("Unique registration code space (1000-9999) exhausted or collision limit reached.")


def get_public_base_url():
    """
    Determine the canonical public base URL for team details and QR codes.
    Checks environment variables first, then active request context, then deployment fallbacks.
    Avoids temporary or generic landing pages.
    """
    for key in ("PUBLIC_BASE_URL", "APP_URL", "NEXT_PUBLIC_APP_URL"):
        val = os.environ.get(key, "").strip().rstrip("/")
        if val:
            return val

    # Stable production URL on Vercel
    if os.environ.get("VERCEL_PROJECT_PRODUCTION_URL"):
        return f"https://{os.environ.get('VERCEL_PROJECT_PRODUCTION_URL').strip().rstrip('/')}"

    # Active request context (handles custom domain / port and reverse proxy headers)
    if has_request_context():
        scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
        host = request.headers.get("X-Forwarded-Host", request.host)
        return f"{scheme}://{host}".rstrip("/")

    # Ephemeral Vercel URL fallback
    if os.environ.get("VERCEL_URL"):
        return f"https://{os.environ.get('VERCEL_URL').strip().rstrip('/')}"

    return "http://localhost:5000"


def generate_team_qr(registration_code, force=False):
    """
    Generate a high-quality QR code linking to the dedicated team details route.
    Uses the stable unique registration code and configured public URL.
    """
    qr_path = QR_DIR / f"{registration_code}.png"
    if qr_path.is_file() and not force:
        return

    base_url = get_public_base_url()
    qr_data = f"{base_url}/team/{registration_code}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="#000000",
        back_color="#FFFFFF"
    )

    image.save(qr_path)


# ==================================================
# VALIDATION HELPERS
# ==================================================

def is_valid_email(email):
    return bool(
        re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    )


def validate_github_repo_url(url, required=True):
    """
    Validates and normalizes a GitHub repository URL.
    Returns (is_valid: bool, result: str)
    - If valid: (True, normalized_https_url)
    - If invalid: (False, user_friendly_error_message)
    """
    if url is None:
        url = ""
    cleaned = str(url).strip()
    if not cleaned:
        if required:
            return False, "GitHub Repository URL is required. Please provide the repository link for your project."
        return True, ""

    # Normalize URLs entered without scheme (e.g. github.com/owner/repo)
    if cleaned.lower().startswith(("github.com/", "www.github.com/")):
        cleaned = "https://" + cleaned

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return False, "Invalid URL format. Please enter a valid GitHub repository URL."

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "GitHub repository URL must use HTTPS (e.g. https://github.com/owner/repo)."

    if not parsed.hostname:
        return False, "Invalid URL format: missing host."

    hostname = parsed.hostname.lower()
    if hostname not in ("github.com", "www.github.com"):
        return False, f"Only GitHub repository URLs are accepted (received host: '{hostname}')."

    if parsed.username or parsed.password:
        return False, "Repository URL must not contain embedded credentials."

    # Check repository path components: /owner/repo[/...]
    raw_path = parsed.path.strip("/")
    parts = [p for p in raw_path.split("/") if p]

    if len(parts) == 0:
        return False, "Please enter your actual project repository URL (e.g. https://github.com/owner/repository), not the GitHub homepage."

    if len(parts) == 1:
        return False, "Please enter the repository URL for your project (e.g. https://github.com/owner/repository), not just a GitHub user or organization profile."

    owner, repo = parts[0], parts[1]

    # Clean .git suffix if present on repo for validation check
    repo_clean = repo[:-4] if repo.lower().endswith(".git") else repo

    owner_pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$"
    repo_pattern = r"^[a-zA-Z0-9_.-]{1,100}$"

    if not re.match(owner_pattern, owner):
        return False, f'Invalid GitHub owner/organization name: "{owner}".'

    if not re.match(repo_pattern, repo_clean) or repo_clean in (".", ".."):
        return False, f'Invalid GitHub repository name: "{repo}".'

    reserved = {
        "features", "pricing", "security", "customer-stories", "enterprise",
        "explore", "topics", "trending", "collections", "events", "readme",
        "organizations", "settings", "notifications", "login", "join", "about",
        "contact", "site", "blog", "marketplace", "pulls", "issues", "sponsors"
    }
    if owner.lower() in reserved:
        return False, f'"{owner}" is a GitHub system section, not a project repository.'

    # Construct clean canonical normalized URL (always https://github.com/owner/repo)
    normalized = f"https://github.com/{owner}/{repo}"
    if len(parts) > 2:
        normalized += "/" + "/".join(parts[2:])

    return True, normalized


def is_valid_github_url(url):
    """Backwards compatibility wrapper returning boolean."""
    is_valid, _ = validate_github_repo_url(url, required=False)
    return is_valid


def validate_files(files):
    files = [
        file for file in files
        if file and file.filename
    ]

    # No per-field image-count limit.
    # Each image must still meet the type and size limits.

    for file in files:
        extension = Path(file.filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            return "Only PNG, JPG, JPEG and WEBP images are allowed."

        file.stream.seek(0, 2)
        file_size = file.stream.tell()
        file.stream.seek(0)

        if file_size > MAX_FILE_SIZE:
            return f"{file.filename} exceeds the 5 MB limit."

    return None


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/", methods=["GET"])
def home():
    return render_template("team-registration.html")


# ==================================================
# TEAM REGISTRATION
# ==================================================

@app.route("/register", methods=["POST"])
def register():
    conn = None
    saved_files = []

    try:
        data = request.form

        team_name = data.get("teamName", "").strip()
        team_number = data.get("teamNumber", "").strip()
        college_name = data.get("collegeName", "").strip() or data.get("affiliation", "").strip()
        college_city = data.get("collegeCity", "").strip()
        college_dept = data.get("collegeDept", "").strip()
        leader_name = data.get("leaderName", "").strip()
        leader_email = data.get("leaderEmail", "").strip().lower()
        leader_phone = data.get("leaderPhone", "").strip()
        leader_section = data.get("leaderSection", "").strip()
        leader_year = data.get("leaderYear", "").strip()

        # Team number is optional in the current HTML.
        if not team_number:
            team_number = "Not assigned"

        if not team_name:
            return jsonify(
                success=False,
                message="Please enter a team name."
            ), 400

        if not leader_name:
            return jsonify(
                success=False,
                message="Please enter the team leader's full name."
            ), 400

        if not leader_email or not is_valid_email(leader_email):
            return jsonify(
                success=False,
                message="Please enter a valid leader email address."
            ), 400

        if not leader_phone:
            return jsonify(
                success=False,
                message="Please enter the team leader's phone number."
            ), 400

        if not leader_section:
            return jsonify(
                success=False,
                message="Please enter the team leader's academic section."
            ), 400

        if not leader_year:
            return jsonify(
                success=False,
                message="Please select the team leader's year of study."
            ), 400

        if not college_name:
            return jsonify(
                success=False,
                message="Please enter your college or university name."
            ), 400

        if not college_city:
            return jsonify(
                success=False,
                message="Please enter your campus city."
            ), 400

        # ------------------------------------------
        # Selected arenas
        # ------------------------------------------

        arenas_selected = list(
            dict.fromkeys(data.getlist("arenas"))
        )

        if not arenas_selected:
            return jsonify(
                success=False,
                message="Please select at least one arena."
            ), 400

        if any(arena not in ARENAS for arena in arenas_selected):
            return jsonify(
                success=False,
                message="One or more selected arenas are invalid."
            ), 400

        # ------------------------------------------
        # Team members
        # ------------------------------------------

        member_names = data.getlist("memberName[]")
        member_emails = data.getlist("memberEmail[]")
        member_sections = data.getlist("memberSection[]")
        member_years = data.getlist("memberYear[]")

        member_counts = {
            len(member_names),
            len(member_emails),
            len(member_sections),
            len(member_years),
        }

        if len(member_counts) != 1:
            return jsonify(
                success=False,
                message="Member fields do not match. Please check the form."
            ), 400

        # Early logic: Allow up to 5 members in the team registration table.
        if not (1 <= len(member_names) <= 5):
            return jsonify(
                success=False,
                message="A team must have between 1 and 5 members (maximum 5 members)."
            ), 400

        members = []

        for name, email, section, year in zip(
            member_names,
            member_emails,
            member_sections,
            member_years
        ):
            name = name.strip()
            email = email.strip().lower()
            section = section.strip()
            year = year.strip()

            if not all([name, email, section, year]):
                return jsonify(
                    success=False,
                    message="Please complete every field for each team member."
                ), 400

            if not is_valid_email(email):
                return jsonify(
                    success=False,
                    message=f"Please enter a valid email for {name}."
                ), 400

            members.append((name, email, section, year))

        # ------------------------------------------
        # Project submissions (Multi-Project Architecture)
        # ------------------------------------------

        validated_projects = []

        project_titles = data.getlist("projectTitle[]") or data.getlist("projectTitle")

        if project_titles:
            # Multi-project dynamic format
            project_arenas = data.getlist("projectArena[]") or data.getlist("projectArena")
            project_problems = data.getlist("projectProblem[]") or data.getlist("projectProblem")
            project_solutions = data.getlist("projectSolution[]") or data.getlist("projectSolution")
            project_githubs = data.getlist("projectGithub[]") or data.getlist("projectGithub")

            if not (len(project_arenas) == len(project_titles) == len(project_problems) == len(project_solutions) == len(project_githubs)):
                return jsonify(
                    success=False,
                    message="Project field counts do not match. Please verify your project submissions."
                ), 400

            if len(project_titles) == 0:
                return jsonify(
                    success=False,
                    message="Please add at least one project submission."
                ), 400

            for i in range(len(project_titles)):
                p_arena = project_arenas[i].strip()
                p_title = project_titles[i].strip()
                p_problem = project_problems[i].strip()
                p_solution = project_solutions[i].strip()
                p_github = project_githubs[i].strip()

                if not p_arena or p_arena not in ARENAS:
                    return jsonify(
                        success=False,
                        message=f"Project {i+1}: Please select a valid arena track."
                    ), 400

                if p_arena not in arenas_selected:
                    return jsonify(
                        success=False,
                        message=f"Project '{p_title or (i+1)}' is assigned to '{p_arena}' which is not among your selected arenas."
                    ), 400

                if not p_title:
                    return jsonify(
                        success=False,
                        message=f"Please enter a project title for project {i+1}."
                    ), 400

                if not p_problem or not p_solution:
                    return jsonify(
                        success=False,
                        message=f"Please complete both the problem statement and proposed solution for '{p_title}'."
                    ), 400

                is_valid_gh, gh_result = validate_github_repo_url(p_github, required=True)
                if not is_valid_gh:
                    return jsonify(
                        success=False,
                        message=f"[{p_title}] {gh_result}"
                    ), 400

                # Project evidence images
                files = (
                    request.files.getlist(f"projectEvidence_{i}[]") or
                    request.files.getlist(f"projectEvidence_{i}") or
                    request.files.getlist(f"evidence_{p_arena}[]")
                )
                files = [f for f in files if f and f.filename]

                if not files:
                    return jsonify(
                        success=False,
                        message=f"Please upload at least one evidence image for project '{p_title}'."
                    ), 400

                file_error = validate_files(files)
                if file_error:
                    return jsonify(
                        success=False,
                        message=f"[{p_title}] {file_error}"
                    ), 400

                validated_projects.append({
                    "arena": p_arena,
                    "title": p_title,
                    "problem": p_problem,
                    "solution": p_solution,
                    "github": gh_result,
                    "files": files
                })
        else:
            # Legacy arena-keyed format fallback (for existing test suites / backward compatibility)
            for arena in arenas_selected:
                problem = data.get(f"problem_{arena}", "").strip()
                solution = data.get(f"solution_{arena}", "").strip()
                github = data.get(f"github_{arena}", "").strip()

                if not problem or not solution:
                    return jsonify(
                        success=False,
                        message=f"Please complete the problem statement and solution for {arena}."
                    ), 400

                is_valid_gh, gh_result = validate_github_repo_url(github, required=True)
                if not is_valid_gh:
                    return jsonify(
                        success=False,
                        message=f"[{arena}] {gh_result}"
                    ), 400

                files = request.files.getlist(f"evidence_{arena}[]")
                files = [f for f in files if f and f.filename]

                if not files:
                    return jsonify(
                        success=False,
                        message=f"Please upload at least one evidence image for {arena}."
                    ), 400

                file_error = validate_files(files)
                if file_error:
                    return jsonify(
                        success=False,
                        message=f"{arena}: {file_error}"
                    ), 400

                meta = ARENA_METADATA.get(arena, {})
                title = meta.get("title", f"{arena} Challenge Project")

                validated_projects.append({
                    "arena": arena,
                    "title": title,
                    "problem": problem,
                    "solution": solution,
                    "github": gh_result,
                    "files": files
                })

        # ------------------------------------------
        # Save registration in SQLite
        # ------------------------------------------

        conn = get_db()
        registration_code = generate_unique_registration_code(conn)

        cursor = conn.execute("""
            INSERT INTO teams (
                registration_code,
                team_name,
                team_number,
                college_name,
                college_city,
                college_dept,
                leader_name,
                leader_email,
                leader_phone,
                leader_section,
                leader_year,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            registration_code,
            team_name,
            team_number,
            college_name,
            college_city,
            college_dept,
            leader_name,
            leader_email,
            leader_phone,
            leader_section,
            leader_year
        ))

        team_id = cursor.lastrowid

        # Save members.
        conn.executemany("""
            INSERT INTO members (
                team_id, name, email, section, year
            )
            VALUES (?, ?, ?, ?, ?)
        """, [
            (team_id, name, email, section, year)
            for name, email, section, year in members
        ])

        # ------------------------------------------
        # Save projects and evidence images
        # ------------------------------------------

        team_folder = UPLOAD_DIR / registration_code
        team_folder.mkdir(parents=True, exist_ok=True)

        for proj in validated_projects:
            # 1. Insert into dedicated projects table
            cursor = conn.execute("""
                INSERT INTO projects (
                    team_id,
                    arena_name,
                    title,
                    problem_statement,
                    proposed_solution,
                    github_link,
                    flagged_for_review,
                    review_notes
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, '')
            """, (
                team_id,
                proj["arena"],
                proj["title"],
                proj["problem"],
                proj["solution"],
                proj["github"]
            ))
            project_id = cursor.lastrowid

            # 2. Sync to legacy arenas table for backward compatibility
            conn.execute("""
                INSERT INTO arenas (
                    team_id,
                    arena_name,
                    problem_statement,
                    proposed_solution,
                    github_link
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                team_id,
                proj["arena"],
                proj["problem"],
                proj["solution"],
                proj["github"]
            ))

            # 3. Save uploaded evidence images linked to project_id
            for file in proj["files"]:
                original_name = (
                    secure_filename(Path(file.filename).name)
                    or "evidence-image"
                )
                extension = Path(original_name).suffix.lower()
                stored_filename = f"{uuid.uuid4().hex}{extension}"
                destination = team_folder / stored_filename

                file.stream.seek(0)
                file_bytes = file.read()

                try:
                    destination.write_bytes(file_bytes)
                    saved_files.append(destination)
                except Exception:
                    pass

                stored_path = f"{registration_code}/{stored_filename}"

                sb_client = get_supabase_client()
                if sb_client:
                    try:
                        content_type = file.content_type or "image/png"
                        sb_client.storage.from_("techverse-uploads").upload(
                            stored_path,
                            file_bytes,
                            {"content-type": content_type, "upsert": "true"}
                        )
                    except Exception as e:
                        app.logger.warning("Supabase upload exception: %s", e)

                conn.execute("""
                    INSERT INTO uploads (
                        team_id,
                        project_id,
                        arena_name,
                        original_name,
                        stored_name
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    team_id,
                    project_id,
                    proj["arena"],
                    original_name,
                    stored_path
                ))

        conn.commit()

        return jsonify(
            success=True,
            message="Registration successfully saved!",
            registration_id=registration_code
        ), 201

    except RuntimeError as re_err:
        if conn:
            conn.rollback()

        for path in saved_files:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

        return jsonify(
            success=False,
            message=str(re_err)
        ), 503

    except sqlite3.IntegrityError:
        if conn:
            conn.rollback()

        for path in saved_files:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                app.logger.exception("Failed to clean up an uploaded file.")

        return jsonify(
            success=False,
            message="The registration could not be saved because of a database constraint."
        ), 409

    except Exception:
        if conn:
            conn.rollback()

        app.logger.exception("Registration failed.")

        for path in saved_files:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                app.logger.exception("Failed to clean up an uploaded file.")

        return jsonify(
            success=False,
            message="Registration failed. Please try again or contact the event administrator."
        ), 500

    finally:
        if conn:
            conn.close()


# ==================================================
# REQUEST SIZE ERROR
# ==================================================

@app.errorhandler(413)
def request_too_large(error):
    return jsonify(
        success=False,
        message="The total upload request exceeds 120 MB. Please reduce the total image size and try again."
    ), 413


# ==================================================
# ADMIN PANEL + LOGIN (admin and judges)
# ==================================================

STATUSES = ["Pending", "Approved", "Rejected"]

# First-time admin account. It is created only when the users table is empty.
# Set ADMIN_PASSWORD in environment variables or .env file.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "TechVerse@2026")


def load_secret_key():
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    key_file = DATA_DIR / "secret.key"
    if key_file.exists():
        try:
            stored = key_file.read_text().strip()
            if stored:
                return stored
        except Exception:
            pass

    # In serverless environments (or across server reboots), a stable fallback key
    # prevents session cookie invalidation between requests and avoids CSRF "Bad Request" errors.
    stable_default = "techverse-2026-dev-secret-key-change-in-production"
    try:
        key_file.write_text(stable_default)
    except Exception:
        pass

    return stable_default


app.secret_key = load_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400


def init_users():
    conn = get_db()
    try:
        if is_postgres():
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'judge',
                    arenas TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'judge',
                    arenas TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Keep default administrative accounts synchronized with configured password
        admin_accounts = [
            (DEFAULT_ADMIN_USERNAME, "admin"),
            ("techverse_admin", "admin")
        ]
        for uname, role in admin_accounts:
            existing = conn.execute("SELECT id FROM users WHERE username = ?", (uname,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, arenas) "
                    "VALUES (?, ?, ?, '')",
                    (uname, generate_password_hash(DEFAULT_ADMIN_PASSWORD), role)
                )
            else:
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (generate_password_hash(DEFAULT_ADMIN_PASSWORD), uname)
                )
        conn.commit()
    finally:
        conn.close()


init_users()


# ------------------------------------------
# Session, CSRF and access helpers
# ------------------------------------------

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, role, arenas FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        session.clear()
        return None

    if row["role"] == "admin":
        allowed = list(ARENAS)
    else:
        allowed = [a for a in row["arenas"].split(",") if a in ARENAS]

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "arenas": allowed,
    }


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def check_csrf():
    if app.config.get("TESTING") and not app.config.get("WTF_CSRF_ENABLED", True):
        return
    sent = request.form.get("csrf_token", "").encode()
    expected = session.get("csrf", "").encode()
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400)


@app.context_processor
def inject_template_globals():
    return {"csrf_token": csrf_token, "current_user": getattr(g, "user", None)}


def safe_next(target):
    if (
        target
        and target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
    ):
        return target
    return url_for("admin_home")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for("login", next=request.path))
        g.user = user
        return view(*args, **kwargs)
    return wrapper


def admin_only(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


# ------------------------------------------
# Login / logout
# ------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("admin_home"))

    error = ""

    if request.method == "POST":
        sent = request.form.get("csrf_token", "").encode()
        expected = session.get("csrf", "").encode()
        if not expected or not sent or not hmac.compare_digest(sent, expected):
            session["csrf"] = secrets.token_hex(16)
            return render_template(
                "login.html",
                error="Session was refreshed. Please re-enter your password to log in.",
                active_tab="admin"
            )

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        finally:
            conn.close()

        if row and check_password_hash(row["password_hash"], password):
            session.clear()
            session["user_id"] = row["id"]
            session["csrf"] = secrets.token_hex(16)
            return redirect(safe_next(request.args.get("next")))

        error = "Wrong username or password."

    return render_template("login.html", error=error, active_tab="admin")
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------
# Team views (admin) and arena views (admin + judges)
# ------------------------------------------

@app.route("/admin")
@login_required
def admin_home():
    if g.user["role"] != "admin":
        return redirect(url_for("admin_arena"))

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    sql = """
        SELECT t.*,
          (SELECT COUNT(*) FROM members m WHERE m.team_id = t.id) AS member_count,
          (SELECT COUNT(*) FROM projects p WHERE p.team_id = t.id) AS project_count,
          COALESCE(
              (SELECT GROUP_CONCAT(DISTINCT arena_name) FROM projects p WHERE p.team_id = t.id),
              (SELECT GROUP_CONCAT(arena_name, ', ') FROM arenas a WHERE a.team_id = t.id)
          ) AS arena_list,
          (SELECT COUNT(*) FROM uploads u WHERE u.team_id = t.id) AS photo_count
        FROM teams t WHERE 1 = 1
    """
    params = []

    if q:
        sql += """ AND (t.team_name LIKE ? OR t.registration_code LIKE ?
                    OR t.leader_name LIKE ? OR t.leader_email LIKE ?)"""
        params += [f"%{q}%"] * 4

    if status in STATUSES:
        sql += " AND t.status = ?"
        params.append(status)

    sql += " ORDER BY t.id DESC"

    conn = get_db()
    try:
        teams = conn.execute(sql, params).fetchall()
        counts = {
            row["status"]: row["c"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS c FROM teams GROUP BY status"
            )
        }
    finally:
        conn.close()

    return render_template(
        "admin.html", teams=teams, counts=counts,
        q=q, status=status, statuses=STATUSES,
    )


@app.route("/admin/team/<int:team_id>")
@admin_only
def admin_team(team_id):
    conn = get_db()
    try:
        team = conn.execute(
            "SELECT * FROM teams WHERE id = ?", (team_id,)
        ).fetchone()
        if team is None:
            abort(404)

        members = conn.execute(
            "SELECT * FROM members WHERE team_id = ? ORDER BY id", (team_id,)
        ).fetchall()
        projects = conn.execute(
            "SELECT * FROM projects WHERE team_id = ? ORDER BY id", (team_id,)
        ).fetchall()
        if not projects:
            projects = conn.execute(
                "SELECT id, team_id, arena_name, arena_name AS title, problem_statement, proposed_solution, github_link, 0 AS flagged_for_review FROM arenas WHERE team_id = ? ORDER BY id",
                (team_id,)
            ).fetchall()
        uploads = conn.execute(
            "SELECT * FROM uploads WHERE team_id = ? ORDER BY id", (team_id,)
        ).fetchall()
    finally:
        conn.close()

    # Group photos by project_id and also by arena_name
    photos = {}
    for u in uploads:
        photo_info = {
            "original_name": u["original_name"],
            "stored_name": u["stored_name"],
            "exists": (UPLOAD_DIR / u["stored_name"]).is_file() or bool(get_supabase_client()),
        }
        if u["project_id"]:
            photos.setdefault(u["project_id"], []).append(photo_info)
        if u["arena_name"]:
            photos.setdefault(u["arena_name"], []).append(photo_info)

    return render_template(
        "admin_team.html", team=team, members=members, projects=projects, arenas=projects,
        photos=photos, total_photos=len(uploads), statuses=STATUSES,
    )

@app.route("/admin/team/<int:team_id>/status", methods=["POST"])
@admin_only

def admin_update_status(team_id):
    check_csrf()

    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        abort(400)

    conn = get_db()
    registration_code = None

    try:
        team = conn.execute(
            "SELECT registration_code FROM teams WHERE id = ?",
            (team_id,)
        ).fetchone()

        if team is None:
            abort(404)

        registration_code = team["registration_code"]

        if new_status == "Approved":
            if not registration_code:
                abort(500)

            generate_team_qr(registration_code)

        conn.execute(
            "UPDATE teams SET status = ? WHERE id = ?",
            (new_status, team_id)
        )
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    if new_status != "Approved" and registration_code:
        qr_path = QR_DIR / f"{registration_code}.png"
        qr_path.unlink(missing_ok=True)

    flash(f"Team status updated to {new_status}.", "success")
    return redirect(url_for("admin_home"))


@app.route("/admin/team/<int:team_id>/project/<int:project_id>/edit", methods=["POST"], endpoint="admin_edit_project")
@app.route("/admin/team/<int:team_id>/arena/<int:arena_id>/edit", methods=["POST"], endpoint="admin_edit_arena")
@admin_only
def admin_edit_project(team_id, project_id=None, arena_id=None):
    target_id = project_id if project_id is not None else arena_id
    check_csrf()
    conn = get_db()
    try:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ? AND team_id = ?",
            (target_id, team_id)
        ).fetchone()

        if project:
            title = request.form.get("title", "").strip() or project["title"]
            problem = request.form.get("problem_statement", "").strip() or project["problem_statement"]
            solution = request.form.get("proposed_solution", "").strip() or project["proposed_solution"]

            new_github = request.form.get("github_link", "").strip()
            if new_github:
                is_valid, validated_url = validate_github_repo_url(new_github, required=True)
                if not is_valid:
                    flash(f"Invalid GitHub Repository URL: {validated_url}", "error")
                    return redirect(url_for("admin_team", team_id=team_id))
                target_github = validated_url
            else:
                target_github = project["github_link"]

            conn.execute(
                """
                UPDATE projects
                SET title = ?, problem_statement = ?, proposed_solution = ?, github_link = ?
                WHERE id = ? AND team_id = ?
                """,
                (title, problem, solution, target_github, target_id, team_id)
            )
            # Sync to arenas table as well
            conn.execute(
                """
                UPDATE arenas
                SET problem_statement = ?, proposed_solution = ?, github_link = ?
                WHERE team_id = ? AND arena_name = ?
                """,
                (problem, solution, target_github, team_id, project["arena_name"])
            )
            conn.commit()
            flash("Project details updated successfully.", "success")
        else:
            arena = conn.execute(
                "SELECT * FROM arenas WHERE id = ? AND team_id = ?",
                (target_id, team_id)
            ).fetchone()
            if not arena:
                abort(404)

            problem = request.form.get("problem_statement", "").strip() or arena["problem_statement"]
            solution = request.form.get("proposed_solution", "").strip() or arena["proposed_solution"]
            new_github = request.form.get("github_link", "").strip()
            if new_github:
                is_valid, validated_url = validate_github_repo_url(new_github, required=True)
                if not is_valid:
                    flash(f"Invalid GitHub Repository URL: {validated_url}", "error")
                    return redirect(url_for("admin_team", team_id=team_id))
                target_github = validated_url
            else:
                target_github = arena["github_link"]

            conn.execute(
                """
                UPDATE arenas
                SET problem_statement = ?, proposed_solution = ?, github_link = ?
                WHERE id = ? AND team_id = ?
                """,
                (problem, solution, target_github, target_id, team_id)
            )
            conn.commit()
            flash("Arena details updated successfully.", "success")
    finally:
        conn.close()

    return redirect(url_for("admin_team", team_id=team_id))


@app.route("/admin/uploads/<path:stored_name>")
@login_required
def admin_file(stored_name):
    # Only registered files can be served, and judges only see their arenas
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT arena_name FROM uploads WHERE stored_name = ?",
            (stored_name,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        abort(404)

    if g.user["role"] != "admin" and row["arena_name"] not in g.user["arenas"]:
        abort(403)

    local_file = UPLOAD_DIR / stored_name
    if local_file.is_file():
        return send_from_directory(UPLOAD_DIR, stored_name)

    sb_client = get_supabase_client()
    if sb_client:
        try:
            public_url = sb_client.storage.from_("techverse-uploads").get_public_url(stored_name)
            return redirect(public_url)
        except Exception:
            pass

    abort(404)


@app.route("/admin/arenas")
@app.route("/admin/arena/<arena_name>")
@login_required
def admin_arena(arena_name=None):
    if arena_name is not None:
        if arena_name not in ARENAS:
            abort(404)
        if arena_name not in g.user["arenas"]:
            abort(403)

    # A judge with only one arena goes straight to it
    if (
        arena_name is None
        and g.user["role"] != "admin"
        and len(g.user["arenas"]) == 1
    ):
        return redirect(url_for("admin_arena", arena_name=g.user["arenas"][0]))

    conn = get_db()
    try:
        counts = {
            r["arena_name"]: r["c"]
            for r in conn.execute(
                "SELECT arena_name, COUNT(*) AS c FROM projects GROUP BY arena_name"
            )
        }

        entries = []
        if arena_name:
            rows = conn.execute("""
                SELECT p.*, t.registration_code, t.team_name, t.team_number,
                       t.leader_name, t.leader_email, t.leader_phone, t.status
                FROM projects p
                JOIN teams t ON t.id = p.team_id
                WHERE p.arena_name = ?
                ORDER BY t.id, p.id
            """, (arena_name,)).fetchall()

            for r in rows:
                members = conn.execute(
                    "SELECT * FROM members WHERE team_id = ? ORDER BY id",
                    (r["team_id"],)
                ).fetchall()
                ups = conn.execute(
                    "SELECT * FROM uploads WHERE team_id = ? AND (project_id = ? OR (project_id IS NULL AND arena_name = ?)) ORDER BY id",
                    (r["team_id"], r["id"], arena_name)
                ).fetchall()
                entries.append({
                    "row": r,
                    "members": members,
                    "photos": [{
                        "original_name": u["original_name"],
                        "stored_name": u["stored_name"],
                        "exists": (UPLOAD_DIR / u["stored_name"]).is_file() or bool(get_supabase_client()),
                    } for u in ups],
                })
    finally:
        conn.close()

    return render_template(
        "admin_arena.html", arenas=g.user["arenas"], counts=counts,
        arena_name=arena_name, entries=entries,
    )


# ------------------------------------------
# GitHub Project Repositories (admin only)
# ------------------------------------------

def sanitize_csv_cell(value):
    """Prevent CSV formula injection by quoting triggers (=, +, -, @, \t, \r)."""
    if value is None:
        return ""
    text = str(value).strip()
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def get_filtered_repositories(q="", arena="", status=""):
    """Fetch all project repository records joined with teams with optional search and filters."""
    sql = """
        SELECT p.id AS project_id, p.team_id, p.arena_name, p.title AS project_title,
               p.problem_statement, p.proposed_solution, p.github_link, p.flagged_for_review,
               t.registration_code, t.team_name, t.team_number, t.status AS registration_status
        FROM projects p
        JOIN teams t ON t.id = p.team_id
        WHERE 1 = 1
    """
    params = []
    if q:
        sql += " AND (t.team_name LIKE ? OR t.registration_code LIKE ? OR p.title LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if arena and arena in ARENAS:
        sql += " AND p.arena_name = ?"
        params.append(arena)

    if status and status in STATUSES:
        sql += " AND t.status = ?"
        params.append(status)

    sql += " ORDER BY t.id DESC, p.id ASC"

    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        repo_count = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE github_link IS NOT NULL AND TRIM(github_link) != ''"
        ).fetchone()[0]
    finally:
        conn.close()

    return rows, total_projects, repo_count


@app.route("/admin/repositories")
@admin_only
def admin_repositories():
    q = request.args.get("q", "").strip()
    arena = request.args.get("arena", "").strip()
    status = request.args.get("status", "").strip()

    rows, total_projects, repo_count = get_filtered_repositories(q, arena, status)

    return render_template(
        "admin_repositories.html",
        projects=rows,
        total_projects=total_projects,
        repo_count=repo_count,
        arenas=ARENAS,
        statuses=STATUSES,
        q=q,
        arena=arena,
        status=status,
    )


@app.route("/admin/repositories/export")
@admin_only
def admin_repositories_export():
    q = request.args.get("q", "").strip()
    arena = request.args.get("arena", "").strip()
    status = request.args.get("status", "").strip()

    rows, _, _ = get_filtered_repositories(q, arena, status)

    output = io.StringIO()
    # Write UTF-8 BOM so spreadsheet viewers render UTF-8 characters cleanly
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Required column headers
    writer.writerow([
        "Registration ID",
        "Team Name",
        "Team Number",
        "Project Title",
        "Arena",
        "GitHub Repository URL",
        "Registration Status"
    ])

    for r in rows:
        title = r["project_title"] if r["project_title"] else f"{r['arena_name']} Project"
        team_num = r["team_number"] if r["team_number"] and r["team_number"] != "Not assigned" else "Not assigned"
        repo = r["github_link"] if r["github_link"] else "Not provided"

        writer.writerow([
            sanitize_csv_cell(r["registration_code"]),
            sanitize_csv_cell(r["team_name"]),
            sanitize_csv_cell(team_num),
            sanitize_csv_cell(title),
            sanitize_csv_cell(r["arena_name"]),
            sanitize_csv_cell(repo),
            sanitize_csv_cell(r["registration_status"])
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=techverse_2026_github_repositories.csv",
            "Content-Type": "text/csv; charset=utf-8",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# ------------------------------------------
# User management (admin only)
# ------------------------------------------

def selected_arenas():
    chosen = request.form.getlist("arenas")
    return [a for a in ARENAS if a in chosen]


@app.route("/admin/users")
@admin_only
def admin_users():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, username, role, arenas, created_at FROM users ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    users = [{
        "id": r["id"],
        "username": r["username"],
        "role": r["role"],
        "arenas": [a for a in r["arenas"].split(",") if a],
        "created_at": r["created_at"],
    } for r in rows]

    return render_template("admin_user.html", users=users, arenas=ARENAS)


@app.route("/admin/users/create", methods=["POST"])
@admin_only
def admin_create_user():
    check_csrf()

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "judge")
    chosen = selected_arenas()

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username):
        flash("Username must be 3-30 characters: letters, numbers, dot, dash or underscore.", "err")
    elif len(password) < 8:
        flash("Password must be at least 8 characters.", "err")
    elif role not in ("admin", "judge"):
        flash("Invalid role.", "err")
    elif role == "judge" and not chosen:
        flash("Select at least one arena for a judge.", "err")
    else:
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, arenas) "
                "VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), role,
                 ",".join(chosen) if role == "judge" else "")
            )
            conn.commit()
            flash(f"User '{username}' created.", "ok")
        except sqlite3.IntegrityError:
            flash("That username already exists.", "err")
        finally:
            conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/arenas", methods=["POST"])
@admin_only
def admin_update_user_arenas(user_id):
    check_csrf()
    chosen = selected_arenas()

    if not chosen:
        flash("A judge needs at least one arena.", "err")
    else:
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET arenas = ? WHERE id = ? AND role = 'judge'",
                (",".join(chosen), user_id)
            )
            conn.commit()
            flash("Arenas updated.", "ok")
        finally:
            conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/password", methods=["POST"])
@admin_only
def admin_reset_password(user_id):
    check_csrf()
    password = request.form.get("password", "")

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "err")
    else:
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(password), user_id)
            )
            conn.commit()
            flash("Password updated.", "ok")
        finally:
            conn.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_only
def admin_delete_user(user_id):
    check_csrf()

    if user_id == g.user["id"]:
        flash("You cannot delete your own account.", "err")
    else:
        conn = get_db()
        try:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash("User deleted.", "ok")
        finally:
            conn.close()

    return redirect(url_for("admin_users"))


# ==================================================
# LOCAL DEVELOPMENT SERVER
# ==================================================
# ==================================================
# PUBLIC QR VERIFICATION & TEAM LOOKUP
# ==================================================

@app.route("/verify")
def verify_lookup():
    code = request.args.get("code", "").strip().upper()
    if code:
        return redirect(url_for("team_details", registration_code=code))
    return render_template("verify_lookup.html", active_tab="verify")


@app.route("/team/<registration_code>", endpoint="team_details")
@app.route("/verify/<registration_code>", endpoint="verify_registration")
def team_details(registration_code):
    registration_code = registration_code.strip().upper()
    conn = get_db()

    try:
        # 1. Team core registration details
        team = conn.execute(
            """
            SELECT id, registration_code, team_name, team_number, college_name, college_city, college_dept, leader_name, leader_section, leader_year, status, created_at
            FROM teams
            WHERE registration_code = ?
            """,
            (registration_code,)
        ).fetchone()

        if team is None:
            return render_template(
                "team_details.html",
                not_found=True,
                registration_code=registration_code,
                active_tab="verify"
            ), 404

        # 2. Team members roster (student privacy protected: emails & phones kept confidential)
        members = conn.execute(
            """
            SELECT id, name, section, year
            FROM members
            WHERE team_id = ?
            ORDER BY id
            """,
            (team["id"],)
        ).fetchall()

        # 3. Complete project submissions (Multi-Project Architecture)
        projects_rows = conn.execute(
            """
            SELECT id, arena_name, title, problem_statement, proposed_solution, github_link, flagged_for_review, review_notes
            FROM projects
            WHERE team_id = ?
            ORDER BY id
            """,
            (team["id"],)
        ).fetchall()

        if not projects_rows:
            projects_rows = conn.execute(
                """
                SELECT id, arena_name, arena_name AS title, problem_statement, proposed_solution, github_link, 0 AS flagged_for_review, '' AS review_notes
                FROM arenas
                WHERE team_id = ?
                ORDER BY arena_name
                """,
                (team["id"],)
            ).fetchall()

        enriched_arenas = []
        for a in projects_rows:
            meta = ARENA_METADATA.get(a["arena_name"], {
                "title": f"{a['arena_name']} Challenge",
                "category": "Technology Challenge",
                "theme": a["arena_name"],
                "department": "JG University",
                "icon": "🏆",
                "code_prefix": "PS"
            })
            enriched_arenas.append({
                "id": a["id"],
                "code": f"TV26-{meta.get('code_prefix', 'PS')}-{a['id']:02d}",
                "arena_name": a["arena_name"],
                "project_title": a["title"],
                "title": a["title"] or meta["title"],
                "challenge_title": meta["title"],
                "category": meta["category"],
                "theme": meta["theme"],
                "department": meta["department"],
                "icon": meta["icon"],
                "problem_statement": a["problem_statement"],
                "proposed_solution": a["proposed_solution"],
                "github_link": a["github_link"],
                "flagged_for_review": a["flagged_for_review"]
            })

        # 4. Submitted project evidence photos
        uploads = conn.execute(
            """
            SELECT id, project_id, arena_name, original_name, stored_name
            FROM uploads
            WHERE team_id = ?
            ORDER BY id
            """,
            (team["id"],)
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "team_details.html",
        team=team,
        members=members,
        arenas=enriched_arenas,
        uploads=uploads,
        active_tab="verify"
    )


# ==================================================
# PUBLIC SNAPS — AUTHORIZED TEAM EVIDENCE
# ==================================================

@app.route("/team/<registration_code>/snap/<path:stored_name>", endpoint="team_details_snap")
@app.route("/verify/<registration_code>/snap/<path:stored_name>", endpoint="public_verification_snap")
def public_verification_snap(registration_code, stored_name):
    # Prevent directory traversal attacks
    if ".." in stored_name or stored_name.startswith("/") or "\\" in stored_name:
        abort(404)

    conn = get_db()

    try:
        upload = conn.execute(
            """
            SELECT u.stored_name
            FROM uploads AS u
            JOIN teams AS t ON t.id = u.team_id
            WHERE t.registration_code = ?
              AND u.stored_name = ?
            """,
            (registration_code, stored_name)
        ).fetchone()

    finally:
        conn.close()

    if upload is None:
        abort(404)

    local_file = UPLOAD_DIR / upload["stored_name"]
    if local_file.is_file():
        return send_from_directory(
            UPLOAD_DIR,
            upload["stored_name"],
            as_attachment=False
        )

    sb_client = get_supabase_client()
    if sb_client:
        try:
            public_url = sb_client.storage.from_("techverse-uploads").get_public_url(upload["stored_name"])
            return redirect(public_url)
        except Exception:
            pass

    abort(404)


# ==================================================
# TEAM REGISTRATION STATUS CHECK
# ==================================================

@app.route("/team/<registration_code>/status")
def team_registration_status(registration_code):
    conn = get_db()

    try:
        team = conn.execute(
            """
            SELECT status
            FROM teams
            WHERE registration_code = ?
            """,
            (registration_code,)
        ).fetchone()

    finally:
        conn.close()

    if team is None:
        abort(404)

    return jsonify(
        success=True,
        status=team["status"]
    )


# ==================================================
# DOWNLOAD QR — APPROVED TEAMS ONLY
# ==================================================

@app.route("/team/<registration_code>/qr")
def download_team_qr(registration_code):
    conn = get_db()

    try:
        team = conn.execute(
            """
            SELECT status
            FROM teams
            WHERE registration_code = ?
            """,
            (registration_code,)
        ).fetchone()

    finally:
        conn.close()

    if team is None or team["status"] != "Approved":
        abort(404)

    qr_path = QR_DIR / f"{registration_code}.png"

    if not qr_path.is_file():
        generate_team_qr(registration_code)

    # QR generate hone ke baad file check
    if not qr_path.is_file():
        abort(404)

    return send_from_directory(
        QR_DIR,
        f"{registration_code}.png",
        as_attachment=True,
        download_name=f"{registration_code}-QR.png"
    )


# ==================================================
# TEAM ID CARD PORTAL & GENERATOR
# ==================================================

@app.route("/card")
@app.route("/id-card")
def id_card_portal():
    code = request.args.get("code", "").strip().upper()
    if code:
        return redirect(url_for("team_id_card", registration_code=code))
    return render_template("team_id_card.html", portal_search=True, team=None, active_tab="card")


@app.route("/team/<registration_code>/card")
def team_id_card(registration_code):
    registration_code = registration_code.strip().upper()
    conn = get_db()

    try:
        team = conn.execute(
            """
            SELECT registration_code, team_name, college_name, college_city, college_dept, status, leader_name, leader_email
            FROM teams
            WHERE registration_code = ?
            """,
            (registration_code,)
        ).fetchone()
    finally:
        conn.close()

    if team is None:
        return render_template(
            "team_id_card.html",
            not_found=True,
            not_approved=True,
            team=None,
            registration_code=registration_code,
            active_tab="card"
        ), 404

    # If the team is not approved yet (e.g. Pending or Rejected), show guidance instead of 404 error
    if team["status"] != "Approved":
        return render_template(
            "team_id_card.html",
            team=team,
            team_name=team["team_name"],
            registration_code=team["registration_code"],
            status=team["status"],
            not_approved=True,
            is_pending=True,
            active_tab="card"
        )

    # Ensure the team's QR image exists with the dedicated team route URL.
    generate_team_qr(registration_code, force=True)
    qr_path = QR_DIR / f"{registration_code}.png"

    qr_data_uri = ""
    if qr_path.is_file():
        qr_base64 = base64.b64encode(
            qr_path.read_bytes()
        ).decode("ascii")
        qr_data_uri = f"data:image/png;base64,{qr_base64}"

    return render_template(
        "team_id_card.html",
        team=team,
        team_name=team["team_name"],
        registration_code=team["registration_code"],
        qr_data_uri=qr_data_uri,
        is_approved=True,
        status="Approved",
        active_tab="card"
    )

# ==================================================
# LOCAL DEVELOPMENT SERVER
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)