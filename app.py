import hmac
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
    abort,
    flash,
    g,
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


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ==================================================
# DATABASE INITIALIZATION
# Keeps existing tables and registrations
# ==================================================

def init_db():
    conn = get_db()

    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_code TEXT UNIQUE,
                team_name TEXT NOT NULL,
                team_number TEXT NOT NULL,
                leader_name TEXT NOT NULL,
                leader_email TEXT NOT NULL,
                leader_phone TEXT NOT NULL,
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

            CREATE INDEX IF NOT EXISTS idx_members_team_id ON members(team_id);
            CREATE INDEX IF NOT EXISTS idx_arenas_team_id ON arenas(team_id);
            CREATE INDEX IF NOT EXISTS idx_uploads_team_id ON uploads(team_id);
            CREATE INDEX IF NOT EXISTS idx_teams_code ON teams(registration_code);
        """)

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


def generate_team_qr(registration_code):
    public_url = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not public_url and os.environ.get("VERCEL_URL"):
        public_url = f"https://{os.environ.get('VERCEL_URL').strip().rstrip('/')}"

    if public_url:
        qr_data = f"{public_url}/verify/{registration_code}"
    else:
        qr_data = url_for(
            "verify_registration",
            registration_code=registration_code,
            _external=True
        )

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

    image.save(QR_DIR / f"{registration_code}.png")


# ==================================================
# VALIDATION HELPERS
# ==================================================

def is_valid_email(email):
    return bool(
        re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    )


def is_valid_github_url(url):
    if not url:
        return True

    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and parsed.hostname is not None
            and parsed.hostname.lower() == "github.com"
            and parsed.username is None
            and parsed.password is None
        )

    except ValueError:
        return False


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
        leader_name = data.get("leaderName", "").strip()
        leader_email = data.get("leaderEmail", "").strip().lower()
        leader_phone = data.get("leaderPhone", "").strip()

        # Team number is optional in the current HTML.
        if not team_number:
            team_number = "Not assigned"

        if not all([
            team_name,
            leader_name,
            leader_email,
            leader_phone
        ]):
            return jsonify(
                success=False,
                message="Please complete all required team and leader fields."
            ), 400

        if not is_valid_email(leader_email):
            return jsonify(
                success=False,
                message="Please enter a valid leader email address."
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

        # Team limit: 1 leader + 1 to 4 additional members (total 2 to 5 members).
        if not (1 <= len(member_names) <= 4):
            return jsonify(
                success=False,
                message="A team must have between 2 and 5 members total (1 team leader + 1 to 4 additional members)."
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
        # Arena project details
        # ------------------------------------------

        arena_records = []

        for arena in arenas_selected:
            problem = data.get(f"problem_{arena}", "").strip()
            solution = data.get(f"solution_{arena}", "").strip()
            github = data.get(f"github_{arena}", "").strip()

            if not problem or not solution:
                return jsonify(
                    success=False,
                    message=f"Please complete the problem statement and solution for {arena}."
                ), 400

            if not is_valid_github_url(github):
                return jsonify(
                    success=False,
                    message=f"Please enter a valid GitHub URL for {arena}."
                ), 400

            arena_records.append(
                (arena, problem, solution, github)
            )

        # ------------------------------------------
        # Evidence uploads
        # Matches the existing JavaScript field names
        # ------------------------------------------

        file_groups = []

        for arena in arenas_selected:
            files = request.files.getlist(
                f"evidence_{arena}[]"
            )

            files = [
                file for file in files
                if file and file.filename
            ]

            if not files:
                return jsonify(
                    success=False,
                    message=f"Please upload at least one evidence image for {arena}."
                ), 400

            file_groups.append((arena, files))

        # Validate every image before saving anything.
        for arena_name, files in file_groups:
            error = validate_files(files)

            if error:
                return jsonify(
                    success=False,
                    message=f"{arena_name}: {error}"
                ), 400

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
                leader_name,
                leader_email,
                leader_phone,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            registration_code,
            team_name,
            team_number,
            leader_name,
            leader_email,
            leader_phone
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

        # Save arena details.
        conn.executemany("""
            INSERT INTO arenas (
                team_id,
                arena_name,
                problem_statement,
                proposed_solution,
                github_link
            )
            VALUES (?, ?, ?, ?, ?)
        """, [
            (team_id, arena, problem, solution, github)
            for arena, problem, solution, github in arena_records
        ])

        # ------------------------------------------
        # Save images
        # ------------------------------------------

        team_folder = UPLOAD_DIR / registration_code
        team_folder.mkdir(parents=True, exist_ok=True)

        for arena_name, files in file_groups:
            for file in files:
                original_name = (
                    secure_filename(Path(file.filename).name)
                    or "evidence-image"
                )

                extension = Path(original_name).suffix.lower()
                stored_filename = f"{uuid.uuid4().hex}{extension}"

                destination = team_folder / stored_filename

                file.stream.seek(0)
                file.save(destination)
                saved_files.append(destination)

                # Preserve the existing database path format.
                stored_path = (
                    f"{registration_code}/{stored_filename}"
                )

                conn.execute("""
                    INSERT INTO uploads (
                        team_id,
                        arena_name,
                        original_name,
                        stored_name
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    team_id,
                    arena_name,
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
# Change this password from the Users page after your first login.
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "jgtechverse@26")


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
    stable_default = "techverse-2026-jg-university-secret-auth-key-9e2028-d6aa24"
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

        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if total == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, arenas) "
                "VALUES (?, ?, 'admin', '')",
                (DEFAULT_ADMIN_USERNAME,
                 generate_password_hash(DEFAULT_ADMIN_PASSWORD))
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
          (SELECT GROUP_CONCAT(arena_name, ', ') FROM arenas a
             WHERE a.team_id = t.id) AS arena_list,
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
        arenas = conn.execute(
            "SELECT * FROM arenas WHERE team_id = ? ORDER BY id", (team_id,)
        ).fetchall()
        uploads = conn.execute(
            "SELECT * FROM uploads WHERE team_id = ? ORDER BY id", (team_id,)
        ).fetchall()
    finally:
        conn.close()

    # Group photos by arena and check that each file exists on disk
    photos = {}
    for u in uploads:
        photos.setdefault(u["arena_name"], []).append({
            "original_name": u["original_name"],
            "stored_name": u["stored_name"],
            "exists": (UPLOAD_DIR / u["stored_name"]).is_file(),
        })

    return render_template(
        "admin_team.html", team=team, members=members, arenas=arenas,
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

    return send_from_directory(UPLOAD_DIR, stored_name)


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
                "SELECT arena_name, COUNT(*) AS c FROM arenas GROUP BY arena_name"
            )
        }

        entries = []
        if arena_name:
            rows = conn.execute("""
                SELECT a.*, t.registration_code, t.team_name, t.team_number,
                       t.leader_name, t.leader_email, t.leader_phone, t.status
                FROM arenas a
                JOIN teams t ON t.id = a.team_id
                WHERE a.arena_name = ?
                ORDER BY t.id
            """, (arena_name,)).fetchall()

            for r in rows:
                members = conn.execute(
                    "SELECT * FROM members WHERE team_id = ? ORDER BY id",
                    (r["team_id"],)
                ).fetchall()
                ups = conn.execute(
                    "SELECT * FROM uploads WHERE team_id = ? AND arena_name = ? ORDER BY id",
                    (r["team_id"], arena_name)
                ).fetchall()
                entries.append({
                    "row": r,
                    "members": members,
                    "photos": [{
                        "original_name": u["original_name"],
                        "stored_name": u["stored_name"],
                        "exists": (UPLOAD_DIR / u["stored_name"]).is_file(),
                    } for u in ups],
                })
    finally:
        conn.close()

    return render_template(
        "admin_arena.html", arenas=g.user["arenas"], counts=counts,
        arena_name=arena_name, entries=entries,
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
        return redirect(url_for("verify_registration", registration_code=code))
    return render_template("verify_lookup.html", active_tab="verify")


@app.route("/verify/<registration_code>")
def verify_registration(registration_code):
    registration_code = registration_code.strip().upper()
    conn = get_db()

    try:
        # Team basic details - do not expose private contact info (leader phone, email, github)
        team = conn.execute(
            """
            SELECT id, registration_code, team_name, status
            FROM teams
            WHERE registration_code = ?
            """,
            (registration_code,)
        ).fetchone()

        if team is None:
            return render_template(
                "verify_registration.html",
                not_found=True,
                registration_code=registration_code,
                active_tab="verify"
            ), 404

        if team["status"] != "Approved":
            return render_template(
                "verify_registration.html",
                unapproved=True,
                team=team,
                registration_code=team["registration_code"],
                status=team["status"],
                active_tab="verify"
            )

        # Team selected problem statements
        arenas = conn.execute(
            """
            SELECT arena_name, problem_statement
            FROM arenas
            WHERE team_id = ?
            ORDER BY arena_name
            """,
            (team["id"],)
        ).fetchall()

        # Team uploaded snaps
        uploads = conn.execute(
            """
            SELECT arena_name, original_name, stored_name
            FROM uploads
            WHERE team_id = ?
            ORDER BY arena_name, original_name
            """,
            (team["id"],)
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "verify_registration.html",
        team=team,
        arenas=arenas,
        uploads=uploads,
        active_tab="verify"
    )


# ==================================================
# PUBLIC SNAPS — APPROVED TEAMS ONLY
# ==================================================

@app.route("/verify/<registration_code>/snap/<path:stored_name>")
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
              AND t.status = 'Approved'
              AND u.stored_name = ?
            """,
            (registration_code, stored_name)
        ).fetchone()

    finally:
        conn.close()

    if upload is None:
        abort(404)

    return send_from_directory(
        UPLOAD_DIR,
        upload["stored_name"],
        as_attachment=False
    )


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
    return render_template("team_id_card.html", portal_search=True, active_tab="card")


@app.route("/team/<registration_code>/card")
def team_id_card(registration_code):
    registration_code = registration_code.strip().upper()
    conn = get_db()

    try:
        team = conn.execute(
            """
            SELECT registration_code, team_name, status, leader_name, leader_email
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

    # Ensure the team's QR image exists.
    qr_path = QR_DIR / f"{registration_code}.png"

    if not qr_path.is_file():
        generate_team_qr(registration_code)

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