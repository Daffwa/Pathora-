import csv
import io
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

from config import Config
from models.document import Document
from models.opportunity import Opportunity
from services.scoring_service import (
    calculate_days_left,
    calculate_deadline_score,
    calculate_document_score,
    calculate_priority_score,
    calculate_skill_match_score,
    get_priority_label,
)


app = Flask(__name__)
app.config.from_object(Config)

SQLITE_TIMEOUT_SECONDS = 10
JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def resolve_app_path(path_value):
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = APP_ROOT / path
    return path.resolve()


for config_key in (
    "DATABASE",
    "SCHEMA",
    "UPLOAD_FOLDER",
    "AVATAR_UPLOAD_FOLDER",
    "CHAT_UPLOAD_FOLDER",
):
    app.config[config_key] = str(resolve_app_path(app.config[config_key]))


class DatabaseAccessError(RuntimeError):
    pass

APPLICATION_STATUS_APPLIED = "Sudah Daftar"
RECRUITER_APPLICATION_STATUSES = [
    APPLICATION_STATUS_APPLIED,
    "Sedang Direview",
    "Interview",
    "Diterima",
    "Ditolak",
]
APPLICATION_STATUSES = RECRUITER_APPLICATION_STATUSES
LEGACY_APPLICATION_STATUS_LABELS = {
    "Belum Daftar": APPLICATION_STATUS_APPLIED,
    "Dokumen Disiapkan": APPLICATION_STATUS_APPLIED,
    "Applied": APPLICATION_STATUS_APPLIED,
    "Seleksi Administrasi": "Sedang Direview",
    "Reviewed": "Sedang Direview",
    "Shortlisted": "Sedang Direview",
    "Accepted": "Diterima",
    "Rejected": "Ditolak",
}
APPLICATION_STATUS_BADGE_CLASSES = {
    APPLICATION_STATUS_APPLIED: "status-applied",
    "Sedang Direview": "status-review",
    "Interview": "status-interview",
    "Diterima": "status-accepted",
    "Ditolak": "status-rejected",
}
APPLICANT_SORT_RECENT = "recent"
APPLICANT_SORT_SKILL_MATCH = "skill_match"
APPLICANT_SORT_OPTIONS = {APPLICANT_SORT_RECENT, APPLICANT_SORT_SKILL_MATCH}

DOCUMENT_TYPES = [
    "CV",
    "Transkrip",
    "Sertifikat",
    "Motivation Letter",
    "Portofolio",
    "KTP/KTM",
]

GOOGLE_MODEL_DEFAULT = "gemma-4-26b-a4b-it"
GOOGLE_TIMEOUT_DEFAULT_SECONDS = 120
AI_ASSISTANT_MAX_MESSAGE_LENGTH = 1000
CHAT_MESSAGE_MAX_LENGTH = 2000
AI_ASSISTANT_GENERIC_ERROR = (
    "AI Assistant belum bisa memproses pertanyaan. Coba lagi nanti."
)
AI_ASSISTANT_SYSTEM_PROMPT = """
Kamu adalah AI Assistant untuk platform Pathora.
Pathora adalah platform internship, scholarship, dan career tracker untuk mahasiswa/jobseeker dan recruiter.
Jawab hanya seputar penggunaan Pathora:
- cara daftar
- cara login
- cara mencari peluang
- cara apply/lamar
- bookmark peluang
- pelacakan lamaran
- status lamaran
- kelola dokumen
- upload dokumen
- profile/edit profile
- chat antar user
- recruiter/jobseeker
- bantuan penggunaan platform

Gunakan Bahasa Indonesia yang jelas, singkat, ramah, dan profesional.
Jika pertanyaan di luar konteks Pathora, arahkan kembali ke bantuan penggunaan platform.
Jangan mengarang fitur yang tidak tersedia di Pathora.
Untuk daftar akun, arahkan user membuka halaman Daftar, memilih role Jobseeker atau Recruiter, mengisi form yang tersedia, lalu login setelah berhasil.
Jangan menyebut verifikasi email, OTP, login sosial, atau integrasi pihak ketiga kecuali user menanyakannya dan fitur itu jelas tersedia.
Jangan meminta password, OTP, API key, token, atau data sensitif pengguna.
""".strip()

def get_int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def redact_sensitive_log_text(value):
    text = str(value)
    replacements = [
        (r"AIza[0-9A-Za-z_-]{20,}", "<redacted-google-api-key>"),
        (r"sk-[A-Za-z0-9_-]{8,}", "<redacted-api-key>"),
        (r"nvapi-[A-Za-z0-9_-]{8,}", "<redacted-api-key>"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def create_google_client():
    if genai is None or not GOOGLE_API_KEY:
        return None

    http_options = None
    if genai_types is not None:
        http_options = genai_types.HttpOptions(
            timeout=GOOGLE_TIMEOUT_SECONDS * 1000
        )

    return genai.Client(api_key=GOOGLE_API_KEY, http_options=http_options)


GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
).strip()
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", GOOGLE_MODEL_DEFAULT).strip() or GOOGLE_MODEL_DEFAULT
GOOGLE_TIMEOUT_SECONDS = max(
    1,
    get_int_env("GOOGLE_TIMEOUT_SECONDS", GOOGLE_TIMEOUT_DEFAULT_SECONDS),
)
try:
    google_client = create_google_client()
except Exception as error:
    app.logger.warning(
        "Google AI Assistant client init failed: %s: %s",
        error.__class__.__name__,
        redact_sensitive_log_text(error),
    )
    google_client = None

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_CHAT_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_CHAT_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}
CHAT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
VALID_ROLES = {"jobseeker", "recruiter", "admin"}
PUBLIC_REGISTER_ROLES = {"jobseeker", "recruiter"}
ROLE_LABELS = {
    "jobseeker": "Jobseeker",
    "recruiter": "Recruiter / HRD",
    "admin": "Admin",
}
RECRUITER_POSITION_OPTIONS = [
    "HRD",
    "Human Resources Staff",
    "HR Generalist",
    "HR Specialist",
    "Recruiter",
    "Technical Recruiter",
    "Talent Acquisition",
    "Talent Acquisition Specialist",
    "Recruitment Officer",
    "People Operations",
    "People Development",
    "Employer Branding",
    "Internship Coordinator",
    "Campus Hiring Officer",
    "Hiring Manager",
    "Company Representative",
    "Founder / Owner",
    "Manager",
    "Supervisor",
    "Other",
]

USER_PROFILE_COLUMN_DEFINITIONS = {
    "nickname": "TEXT DEFAULT ''",
    "phone": "TEXT DEFAULT ''",
    "birth_date": "TEXT DEFAULT ''",
    "gender": "TEXT DEFAULT ''",
    "domicile": "TEXT DEFAULT ''",
    "bio": "TEXT DEFAULT ''",
    "university": "TEXT DEFAULT ''",
    "faculty": "TEXT DEFAULT ''",
    "major": "TEXT DEFAULT ''",
    "degree": "TEXT DEFAULT ''",
    "semester": "TEXT DEFAULT ''",
    "gpa": "TEXT DEFAULT ''",
    "entry_year": "TEXT DEFAULT ''",
    "desired_positions": "TEXT DEFAULT ''",
    "preferred_program": "TEXT DEFAULT ''",
    "preferred_locations": "TEXT DEFAULT ''",
    "work_arrangement": "TEXT DEFAULT ''",
    "interests": "TEXT DEFAULT ''",
    "linkedin": "TEXT DEFAULT ''",
    "github": "TEXT DEFAULT ''",
    "portfolio_url": "TEXT DEFAULT ''",
    "avatar_path": "TEXT DEFAULT ''",
    "updated_at": "TEXT DEFAULT ''",
}

PROFILE_FORM_FIELDS = [
    "name",
    "email",
    "skills",
    "nickname",
    "phone",
    "birth_date",
    "gender",
    "domicile",
    "bio",
    "university",
    "faculty",
    "major",
    "degree",
    "semester",
    "gpa",
    "entry_year",
    "desired_positions",
    "preferred_program",
    "preferred_locations",
    "work_arrangement",
    "interests",
    "linkedin",
    "github",
    "portfolio_url",
]

PROFILE_COMPLETION_FIELDS = [
    "name",
    "email",
    "skills",
    "university",
    "major",
    "degree",
    "gpa",
    "desired_positions",
    "preferred_program",
    "interests",
    "linkedin",
    "portfolio_url",
]


def get_database_path():
    return Path(app.config["DATABASE"])


def get_database_journal_path():
    database_path = get_database_path()
    return database_path.with_name(f"{database_path.name}-journal")


def build_database_error_message(message):
    database_path = get_database_path()
    details = [message, f"Path database: {database_path}"]
    journal_path = get_database_journal_path()
    if journal_path.exists():
        details.append(
            "File journal SQLite ditemukan. Backup app.db dan app.db-journal "
            "sebelum menjalankan recovery atau integrity check."
        )
    return " ".join(details)


def check_database_health(connection):
    connection.execute("SELECT 1").fetchone()


def open_database_connection():
    database_path = get_database_path()
    database_dir = database_path.parent

    if not database_dir.exists():
        database_dir.mkdir(parents=True, exist_ok=True)

    if database_path.exists() and not database_path.is_file():
        raise DatabaseAccessError(
            build_database_error_message("Path database bukan file.")
        )

    if not database_path.exists():
        app.logger.info("Database tidak ditemukan. SQLite akan membuat file baru: %s", database_path)

    connection = None
    try:
        connection = sqlite3.connect(
            str(database_path),
            timeout=SQLITE_TIMEOUT_SECONDS,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_TIMEOUT_SECONDS * 1000}")
        check_database_health(connection)
        return connection
    except sqlite3.Error as exc:
        if connection is not None:
            connection.close()
        raise DatabaseAccessError(
            build_database_error_message(f"Database tidak bisa diakses: {exc}")
        ) from exc


def get_db():
    if "db" not in g:
        g.db = open_database_connection()
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except sqlite3.Error:
            pass


@app.context_processor
def inject_template_options():
    sidebar_user = None
    if "user_id" in session:
        try:
            sidebar_user = get_db().execute(
                """
                SELECT id, name, role, avatar_path
                FROM users
                WHERE id = ?
                """,
                (session["user_id"],),
            ).fetchone()
        except (sqlite3.Error, DatabaseAccessError):
            sidebar_user = None

    return {
        "application_status_badge_class": application_status_badge_class,
        "application_status_label": application_status_label,
        "recruiter_position_options": RECRUITER_POSITION_OPTIONS,
        "sidebar_user": sidebar_user,
    }


def init_database():
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["AVATAR_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["CHAT_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    with closing(open_database_connection()) as db:
        with open(app.config["SCHEMA"], "r", encoding="utf-8") as schema:
            db.executescript(schema.read())

        document_columns = [
            row[1] for row in db.execute("PRAGMA table_info(documents)").fetchall()
        ]
        if "file_path" not in document_columns:
            db.execute("ALTER TABLE documents ADD COLUMN file_path TEXT DEFAULT ''")

        chat_message_columns = [
            row[1] for row in db.execute("PRAGMA table_info(chat_messages)").fetchall()
        ]
        chat_attachment_columns = {
            "attachment_path": "TEXT DEFAULT ''",
            "attachment_type": "TEXT DEFAULT ''",
            "attachment_name": "TEXT DEFAULT ''",
        }
        for column_name, column_definition in chat_attachment_columns.items():
            if column_name not in chat_message_columns:
                db.execute(
                    f"ALTER TABLE chat_messages ADD COLUMN {column_name} {column_definition}"
                )

        user_columns = [
            row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()
        ]
        if "role" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'jobseeker'")
        if "company_name" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN company_name TEXT DEFAULT ''")
        if "company_position" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN company_position TEXT DEFAULT ''")
        for column_name, column_definition in USER_PROFILE_COLUMN_DEFINITIONS.items():
            if column_name not in user_columns:
                db.execute(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}"
                )

        db.execute(
            """
            UPDATE users
            SET role = 'jobseeker'
            WHERE role = 'student'
               OR role IS NULL
               OR role = ''
               OR role NOT IN ('jobseeker', 'recruiter', 'admin')
            """
        )
        user_column_info = db.execute("PRAGMA table_info(users)").fetchall()
        user_column_map = {row[1]: row for row in user_column_info}
        role_default = user_column_map["role"][4]
        if role_default not in {"'jobseeker'", '"jobseeker"', "jobseeker"}:
            db.execute("PRAGMA foreign_keys = OFF")
            db.execute("DROP TABLE IF EXISTS users_new")
            db.execute(
                """
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'jobseeker'
                        CHECK (role IN ('jobseeker', 'recruiter', 'admin')),
                    skills TEXT DEFAULT '',
                    company_name TEXT DEFAULT '',
                    company_position TEXT DEFAULT '',
                    nickname TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    birth_date TEXT DEFAULT '',
                    gender TEXT DEFAULT '',
                    domicile TEXT DEFAULT '',
                    bio TEXT DEFAULT '',
                    university TEXT DEFAULT '',
                    faculty TEXT DEFAULT '',
                    major TEXT DEFAULT '',
                    degree TEXT DEFAULT '',
                    semester TEXT DEFAULT '',
                    gpa TEXT DEFAULT '',
                    entry_year TEXT DEFAULT '',
                    desired_positions TEXT DEFAULT '',
                    preferred_program TEXT DEFAULT '',
                    preferred_locations TEXT DEFAULT '',
                    work_arrangement TEXT DEFAULT '',
                    interests TEXT DEFAULT '',
                    linkedin TEXT DEFAULT '',
                    github TEXT DEFAULT '',
                    portfolio_url TEXT DEFAULT '',
                    avatar_path TEXT DEFAULT '',
                    updated_at TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            db.execute(
                """
                INSERT INTO users_new
                (id, name, email, password_hash, role, skills,
                 company_name, company_position, nickname, phone, birth_date,
                 gender, domicile, bio, university, faculty, major, degree,
                 semester, gpa, entry_year, desired_positions, preferred_program,
                 preferred_locations, work_arrangement, interests, linkedin,
                 github, portfolio_url, avatar_path, updated_at, created_at)
                SELECT
                    id,
                    name,
                    email,
                    password_hash,
                    CASE
                        WHEN role IN ('jobseeker', 'recruiter', 'admin') THEN role
                        ELSE 'jobseeker'
                    END,
                    COALESCE(skills, ''),
                    COALESCE(company_name, ''),
                    COALESCE(company_position, ''),
                    COALESCE(nickname, ''),
                    COALESCE(phone, ''),
                    COALESCE(birth_date, ''),
                    COALESCE(gender, ''),
                    COALESCE(domicile, ''),
                    COALESCE(bio, ''),
                    COALESCE(university, ''),
                    COALESCE(faculty, ''),
                    COALESCE(major, ''),
                    COALESCE(degree, ''),
                    COALESCE(semester, ''),
                    COALESCE(gpa, ''),
                    COALESCE(entry_year, ''),
                    COALESCE(desired_positions, ''),
                    COALESCE(preferred_program, ''),
                    COALESCE(preferred_locations, ''),
                    COALESCE(work_arrangement, ''),
                    COALESCE(interests, ''),
                    COALESCE(linkedin, ''),
                    COALESCE(github, ''),
                    COALESCE(portfolio_url, ''),
                    COALESCE(avatar_path, ''),
                    COALESCE(updated_at, ''),
                    created_at
                FROM users
                """
            )
            db.execute("DROP TABLE users")
            db.execute("ALTER TABLE users_new RENAME TO users")
            db.execute("PRAGMA foreign_keys = ON")

        opportunity_columns = [
            row[1] for row in db.execute("PRAGMA table_info(opportunities)").fetchall()
        ]
        if "official_link" not in opportunity_columns:
            db.execute("ALTER TABLE opportunities ADD COLUMN official_link TEXT DEFAULT ''")
        if "created_by" not in opportunity_columns:
            db.execute("ALTER TABLE opportunities ADD COLUMN created_by INTEGER")
        if "company_name" not in opportunity_columns:
            db.execute("ALTER TABLE opportunities ADD COLUMN company_name TEXT DEFAULT ''")

        admin = db.execute(
            "SELECT id FROM users WHERE email = ?", ("admin@example.com",)
        ).fetchone()
        if admin is None:
            db.execute(
                """
                INSERT INTO users (name, email, password_hash, role, skills)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Admin",
                    "admin@example.com",
                    generate_password_hash("admin12345"),
                    "admin",
                    "",
                ),
            )
        else:
            db.execute(
                "UPDATE users SET role = ? WHERE email = ?",
                ("admin", "admin@example.com"),
            )

        count = db.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        if count == 0:
            db.executemany(
                """
                INSERT INTO opportunities
                (title, provider, type, description, requirements, required_skills, location, deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Data Analyst Internship",
                        "Nusantara Tech",
                        "internship",
                        "Program magang untuk mahasiswa yang ingin belajar analisis data bisnis.",
                        "Mahasiswa aktif, memahami dasar statistik, dan mampu bekerja dalam tim.",
                        "python,sql,excel",
                        "Jakarta / Hybrid",
                        "2026-06-15",
                    ),
                    (
                        "Beasiswa Data Science Muda",
                        "Yayasan Sains Indonesia",
                        "scholarship",
                        "Beasiswa untuk mahasiswa yang tertarik pada proyek data science terapan.",
                        "IPK minimal 3.00, esai motivasi, dan transkrip nilai.",
                        "python,statistics,communication",
                        "Indonesia",
                        "2026-07-01",
                    ),
                    (
                        "Business Intelligence Intern",
                        "Bright Retail Group",
                        "internship",
                        "Kesempatan magang membuat dashboard dan laporan performa penjualan.",
                        "Terbiasa dengan spreadsheet dan visualisasi data sederhana.",
                        "excel,sql,tableau",
                        "Bandung",
                        "2026-05-30",
                    ),
                ],
            )

        db.commit()


def get_deadline_info(deadline_text):
    days_left = calculate_days_left(deadline_text)

    if days_left is None:
        return {"days_left": None, "status": "Unknown"}

    if days_left < 0:
        status = "Closed"
    elif days_left <= 7:
        status = "Urgent"
    else:
        status = "Open"

    return {"days_left": days_left, "status": status}


def get_opportunity_or_404(opportunity_id):
    row = get_db().execute(
        "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
    ).fetchone()

    if row is None:
        abort(404)

    return row


def get_application_for_user_or_404(application_id):
    application = get_db().execute(
        """
        SELECT id FROM applications
        WHERE id = ? AND user_id = ?
        """,
        (application_id, session["user_id"]),
    ).fetchone()

    if application is None:
        abort(404)

    return application


def get_document_for_user(doc_type):
    return get_db().execute(
        """
        SELECT * FROM documents
        WHERE user_id = ? AND doc_type = ?
        """,
        (session["user_id"], doc_type),
    ).fetchone()


def get_current_user_profile():
    return get_db().execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()


def profile_form_data_from_user(user):
    return {field: (user[field] or "") for field in PROFILE_FORM_FIELDS}


def split_profile_list(value):
    if not value:
        return []

    normalized = value.replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def get_document_progress_for_user(user_id):
    rows = get_db().execute(
        """
        SELECT * FROM documents
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchall()
    document_by_type = {row["doc_type"]: Document.from_row(row, user_id) for row in rows}

    documents = []
    for doc_type in DOCUMENT_TYPES:
        documents.append(
            document_by_type.get(
                doc_type,
                Document(document_id=None, user_id=user_id, doc_type=doc_type),
            )
        )

    complete_count = sum(1 for document in documents if document.is_complete())
    total_count = len(DOCUMENT_TYPES)
    percent = round((complete_count / total_count) * 100) if total_count else 0

    return {
        "documents": documents,
        "complete_count": complete_count,
        "total_count": total_count,
        "percent": percent,
    }


def get_saved_profile_opportunities(user_id):
    rows = get_db().execute(
        """
        SELECT
            opportunities.*,
            bookmarks.saved_at,
            applications.status AS application_status
        FROM bookmarks
        JOIN opportunities ON opportunities.id = bookmarks.opportunity_id
        LEFT JOIN applications
            ON applications.opportunity_id = opportunities.id
           AND applications.user_id = bookmarks.user_id
        WHERE bookmarks.user_id = ?
        ORDER BY bookmarks.saved_at DESC
        """,
        (user_id,),
    ).fetchall()

    scoring_context = get_user_scoring_context()
    saved_opportunities = []
    for row in rows:
        opportunity = Opportunity.from_row(row)
        opportunity.saved_at = row["saved_at"]
        opportunity.application_status = row["application_status"] or ""
        apply_priority_score(opportunity, scoring_context)
        saved_opportunities.append(opportunity)

    return saved_opportunities


def get_profile_completion(user, document_progress):
    completed_fields = sum(
        1 for field in PROFILE_COMPLETION_FIELDS if (user[field] or "").strip()
    )
    total_items = len(PROFILE_COMPLETION_FIELDS) + 1
    completed_items = completed_fields

    if document_progress["complete_count"] > 0:
        completed_items += 1

    percent = round((completed_items / total_items) * 100) if total_items else 0

    return {
        "completed": completed_items,
        "total": total_items,
        "percent": percent,
    }


def is_allowed_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def is_allowed_chat_image_file(uploaded_file):
    if uploaded_file is None or not uploaded_file.filename:
        return False

    if "." not in uploaded_file.filename:
        return False

    extension = uploaded_file.filename.rsplit(".", 1)[1].lower()
    return (
        extension in ALLOWED_CHAT_IMAGE_EXTENSIONS
        and uploaded_file.mimetype in ALLOWED_CHAT_IMAGE_MIME_TYPES
        and has_allowed_chat_image_signature(uploaded_file, extension)
    )


def has_allowed_chat_image_signature(uploaded_file, extension):
    try:
        current_position = uploaded_file.stream.tell()
        uploaded_file.stream.seek(0)
        header = uploaded_file.stream.read(16)
        uploaded_file.stream.seek(current_position)
    except (OSError, AttributeError):
        return False

    if extension == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == "gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if extension == "webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"

    return False


def get_uploaded_file_size(uploaded_file):
    if uploaded_file is None:
        return 0

    try:
        current_position = uploaded_file.stream.tell()
        uploaded_file.stream.seek(0, os.SEEK_END)
        size = uploaded_file.stream.tell()
        uploaded_file.stream.seek(current_position)
        return size
    except (OSError, AttributeError):
        return uploaded_file.content_length or 0


def make_chat_attachment_filename(user_id, original_filename):
    safe_name = secure_filename(original_filename or "")
    extension = safe_name.rsplit(".", 1)[1].lower()
    timestamp = now_utc().strftime("%Y%m%d%H%M%S")
    return f"chat_{user_id}_{timestamp}_{uuid.uuid4().hex}.{extension}"


def make_avatar_filename(user_id, original_filename):
    extension = original_filename.rsplit(".", 1)[1].lower()
    return f"user_{user_id}_avatar.{extension}"


def get_user_scoring_context():
    if "user_id" not in session:
        return None
    if get_current_role() != "jobseeker":
        return None

    user = get_db().execute(
        "SELECT skills FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    completed_documents = get_db().execute(
        """
        SELECT COUNT(*) FROM documents
        WHERE user_id = ? AND is_uploaded = 1
        """,
        (session["user_id"],),
    ).fetchone()[0]

    return {
        "skills": user["skills"] if user else "",
        "completed_documents": completed_documents,
        "total_documents": len(DOCUMENT_TYPES),
    }


def apply_priority_score(opportunity, scoring_context):
    deadline_info = get_deadline_info(opportunity.deadline)
    opportunity.days_left = deadline_info["days_left"]
    opportunity.deadline_status = deadline_info["status"]

    if scoring_context is None:
        return opportunity

    deadline_score = calculate_deadline_score(opportunity.days_left)
    skill_score = calculate_skill_match_score(
        scoring_context["skills"], opportunity.required_skills
    )
    document_score = calculate_document_score(
        scoring_context["completed_documents"],
        scoring_context["total_documents"],
    )
    priority_score = calculate_priority_score(
        deadline_score, skill_score, document_score
    )
    is_closed = opportunity.days_left is not None and opportunity.days_left < 0

    opportunity.deadline_score = deadline_score
    opportunity.skill_match_score = skill_score
    opportunity.document_score = document_score
    opportunity.priority_score = priority_score
    opportunity.priority_label = get_priority_label(priority_score, is_closed)
    return opportunity


def get_dashboard_summary(user_id):
    total_saved = get_db().execute(
        "SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    total_applications = get_db().execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    completed_documents = get_db().execute(
        """
        SELECT COUNT(*) FROM documents
        WHERE user_id = ? AND is_uploaded = 1
        """,
        (user_id,),
    ).fetchone()[0]

    return {
        "total_saved": total_saved,
        "total_applications": total_applications,
        "completed_documents": completed_documents,
        "total_documents": len(DOCUMENT_TYPES),
    }


def get_recent_saved_opportunities(user_id):
    return get_db().execute(
        """
        SELECT opportunities.id, opportunities.title, opportunities.provider,
               opportunities.deadline
        FROM bookmarks
        JOIN opportunities ON opportunities.id = bookmarks.opportunity_id
        WHERE bookmarks.user_id = ?
        ORDER BY bookmarks.saved_at DESC
        LIMIT 3
        """,
        (user_id,),
    ).fetchall()


def get_recent_applications(user_id):
    return get_db().execute(
        """
        SELECT applications.status, applications.notes, applications.updated_at,
               opportunities.title
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
        ORDER BY applications.updated_at DESC
        LIMIT 3
        """,
        (user_id,),
    ).fetchall()


def get_urgent_deadlines(user_id):
    rows = get_db().execute(
        """
        SELECT DISTINCT opportunities.*
        FROM opportunities
        LEFT JOIN bookmarks ON bookmarks.opportunity_id = opportunities.id
        LEFT JOIN applications ON applications.opportunity_id = opportunities.id
        WHERE bookmarks.user_id = ? OR applications.user_id = ?
        """,
        (user_id, user_id),
    ).fetchall()

    urgent_opportunities = []
    scoring_context = get_user_scoring_context()
    for row in rows:
        opportunity = Opportunity.from_row(row)
        apply_priority_score(opportunity, scoring_context)
        if opportunity.days_left is not None and 0 <= opportunity.days_left <= 7:
            urgent_opportunities.append(opportunity)

    return sorted(urgent_opportunities, key=lambda opportunity: opportunity.days_left)


def get_top_priority_opportunity():
    scoring_context = get_user_scoring_context()
    if scoring_context is None:
        return None

    rows = get_db().execute("SELECT * FROM opportunities").fetchall()
    opportunities = []
    for row in rows:
        opportunity = Opportunity.from_row(row)
        apply_priority_score(opportunity, scoring_context)
        if opportunity.priority_label != "Closed":
            opportunities.append(opportunity)

    if not opportunities:
        return None

    return max(opportunities, key=lambda opportunity: opportunity.priority_score or 0)


def require_login(message="Silakan login terlebih dahulu."):
    if "user_id" not in session:
        flash(message)
        return redirect(url_for("login"))

    return None


def normalize_role(role):
    normalized_role = (role or "").strip().lower()
    if normalized_role == "student":
        return "jobseeker"
    if normalized_role in VALID_ROLES:
        return normalized_role
    return None


def get_current_user():
    if "user_id" not in session:
        return None

    try:
        db = get_db()
        return db.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    except sqlite3.Error as exc:
        raise DatabaseAccessError(
            build_database_error_message("Data user tidak bisa dibaca dari database.")
        ) from exc


def get_current_role():
    try:
        user = get_current_user()
    except DatabaseAccessError:
        raise

    if user is None:
        return None

    current_role = normalize_role(user["role"])
    session["user_name"] = user["name"]
    session["user_role"] = current_role
    return current_role


def application_status_label(status):
    return LEGACY_APPLICATION_STATUS_LABELS.get(status, status or APPLICATION_STATUS_APPLIED)


def application_status_badge_class(status):
    normalized_status = application_status_label(status)
    return APPLICATION_STATUS_BADGE_CLASSES.get(normalized_status, "status-unknown")


def role_required(*roles, message="Silakan login terlebih dahulu."):
    login_redirect = require_login(message)
    if login_redirect is not None:
        return login_redirect

    allowed_roles = {normalize_role(role) for role in roles}
    current_role = get_current_role()

    if current_role not in allowed_roles:
        flash("Akses ditolak. Role akun kamu tidak memiliki izin untuk halaman ini.")
        abort(403)

    return None


def jobseeker_required():
    return role_required("jobseeker", message="Silakan login sebagai jobseeker.")


def recruiter_required():
    return role_required("recruiter", message="Silakan login sebagai recruiter.")


def recruiter_or_admin_required():
    return role_required(
        "recruiter",
        "admin",
        message="Silakan login sebagai recruiter atau admin.",
    )


def admin_required():
    return role_required("admin", message="Silakan login sebagai admin.")


def is_valid_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False

    return True


def get_opportunity_form_data():
    opportunity_type = request.form.get(
        "opportunity_type", request.form.get("type", "")
    ).strip().lower()
    return {
        "title": request.form.get("title", "").strip(),
        "type": opportunity_type,
        "provider": request.form.get("provider", "").strip(),
        "location": request.form.get("location", "").strip(),
        "deadline": request.form.get("deadline", "").strip(),
        "description": request.form.get("description", "").strip(),
        "requirements": request.form.get("requirements", "").strip(),
        "official_link": request.form.get("official_link", "").strip(),
        "required_skills": request.form.get("required_skills", "").strip(),
    }


def validate_opportunity_form(data):
    errors = []

    if not data["title"]:
        errors.append("Title wajib diisi.")
    if data["type"] not in {"internship", "scholarship"}:
        errors.append("Opportunity type harus internship atau scholarship.")
    if not data["provider"]:
        errors.append("Organizer wajib diisi.")
    if not data["location"]:
        errors.append("Location wajib diisi.")
    if not data["deadline"] or not is_valid_date(data["deadline"]):
        errors.append("Deadline wajib diisi dengan format YYYY-MM-DD.")

    return errors


def get_recruiter_opportunity_or_404(opportunity_id):
    current_role = get_current_role()
    params = [opportunity_id]
    owner_filter = ""
    if current_role == "recruiter":
        owner_filter = "AND created_by = ?"
        params.append(session["user_id"])

    row = get_db().execute(
        f"""
        SELECT * FROM opportunities
        WHERE id = ?
        {owner_filter}
        """,
        params,
    ).fetchone()

    if row is None:
        abort(404)

    return row


def normalize_applicant_sort(sort_value):
    return sort_value if sort_value in APPLICANT_SORT_OPTIONS else APPLICANT_SORT_RECENT


def get_applicant_list_url(opportunity_id=None, sort_by=None):
    route_args = {}
    if opportunity_id is not None:
        route_args["opportunity_id"] = opportunity_id
        endpoint = "recruiter_opportunity_applicants"
    else:
        endpoint = "recruiter_applicants"

    if sort_by == APPLICANT_SORT_SKILL_MATCH:
        route_args["sort"] = sort_by

    return url_for(endpoint, **route_args)


def enrich_recruiter_applicant_rows(rows, sort_by=APPLICANT_SORT_RECENT):
    applicants = []
    for row in rows:
        applicant = dict(row)
        applicant["skill_match_score"] = calculate_skill_match_score(
            applicant.get("applicant_skills", ""),
            applicant.get("required_skills", ""),
        )
        applicants.append(applicant)

    if sort_by == APPLICANT_SORT_SKILL_MATCH:
        applicants.sort(
            key=lambda applicant: (
                applicant["skill_match_score"],
                applicant.get("updated_at") or "",
                applicant["application_id"],
            ),
            reverse=True,
        )

    return applicants


def get_recruiter_applicant_rows(opportunity_id=None, sort_by=APPLICANT_SORT_RECENT):
    current_role = get_current_role()
    filters = []
    params = []

    if current_role == "recruiter":
        filters.append("opportunities.created_by = ?")
        params.append(session["user_id"])

    if opportunity_id is not None:
        get_recruiter_opportunity_or_404(opportunity_id)
        filters.append("opportunities.id = ?")
        params.append(opportunity_id)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    rows = get_db().execute(
        f"""
        SELECT
            applications.id AS application_id,
            applications.status,
            applications.notes,
            applications.applied_at,
            applications.updated_at,
            users.name AS applicant_name,
            users.email AS applicant_email,
            users.skills AS applicant_skills,
            opportunities.id AS opportunity_id,
            opportunities.title AS opportunity_title,
            opportunities.deadline AS opportunity_deadline,
            opportunities.required_skills
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        JOIN users ON users.id = applications.user_id
        {where_clause}
        ORDER BY applications.updated_at DESC
        """,
        params,
    ).fetchall()

    return enrich_recruiter_applicant_rows(rows, normalize_applicant_sort(sort_by))


def get_recruiter_application_or_404(application_id):
    current_role = get_current_role()
    params = [application_id]
    owner_filter = ""

    if current_role == "recruiter":
        owner_filter = "AND opportunities.created_by = ?"
        params.append(session["user_id"])

    application = get_db().execute(
        f"""
        SELECT
            applications.id AS application_id,
            applications.user_id AS applicant_user_id,
            applications.status,
            applications.notes,
            applications.applied_at,
            applications.updated_at,
            users.name AS applicant_name,
            users.email AS applicant_email,
            users.skills AS applicant_skills,
            opportunities.id AS opportunity_id,
            opportunities.title AS opportunity_title,
            opportunities.provider AS opportunity_provider,
            opportunities.location AS opportunity_location,
            opportunities.deadline AS opportunity_deadline
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        JOIN users ON users.id = applications.user_id
        WHERE applications.id = ?
        {owner_filter}
        """,
        params,
    ).fetchone()

    if application is None:
        abort(404)

    return application


def parse_positive_int(value):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None

    return parsed_value if parsed_value > 0 else None


def make_recruiter_applicants_csv(applicants, opportunity=None):
    output = io.StringIO(newline="")
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Nama Pelamar",
            "Email",
            "Lowongan",
            "Status",
            "Skill Match %",
            "Tanggal Daftar",
            "Terakhir Update",
            "Deadline Lowongan",
        ]
    )

    for applicant in applicants:
        writer.writerow(
            [
                applicant["applicant_name"],
                applicant["applicant_email"],
                applicant["opportunity_title"],
                application_status_label(applicant["status"]),
                applicant["skill_match_score"],
                applicant["applied_at"],
                applicant["updated_at"],
                applicant["opportunity_deadline"],
            ]
        )

    export_target = opportunity["title"] if opportunity else "semua-pelamar"
    filename_part = re.sub(r"[^A-Za-z0-9_-]+", "-", export_target).strip("-").lower()
    filename_part = filename_part or "pelamar"
    exported_at = datetime.now(JAKARTA_TZ).strftime("%Y%m%d")
    filename = f"pathora-{filename_part}-{exported_at}.csv"

    return Response(
        output.getvalue(),
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def chat_pair(user_id, contact_id):
    return tuple(sorted((int(user_id), int(contact_id))))


def chat_avatar_initials(name):
    words = [word for word in (name or "").strip().split() if word]
    if not words:
        return "U"
    return "".join(word[:1] for word in words[:2]).upper()


def now_utc():
    return datetime.now(timezone.utc)


def parse_chat_timestamp(timestamp):
    if not timestamp:
        return None

    if isinstance(timestamp, datetime):
        parsed_timestamp = timestamp
    else:
        text = str(timestamp).strip()
        if not text:
            return None

        try:
            parsed_timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    parsed_timestamp = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    parsed_timestamp = None
            if parsed_timestamp is None:
                return None

    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

    return parsed_timestamp.astimezone(timezone.utc)


def chat_timestamp_iso(timestamp):
    parsed_timestamp = parse_chat_timestamp(timestamp)
    if parsed_timestamp is None:
        return ""

    return parsed_timestamp.isoformat(timespec="seconds")


def to_jakarta(timestamp):
    parsed_timestamp = parse_chat_timestamp(timestamp)
    if parsed_timestamp is None:
        return None

    return parsed_timestamp.astimezone(JAKARTA_TZ)


def format_jakarta_clock(timestamp):
    jakarta_timestamp = to_jakarta(timestamp)
    if jakarta_timestamp is None:
        return ""

    return jakarta_timestamp.strftime("%H:%M")


def format_chat_contact_time(timestamp):
    jakarta_timestamp = to_jakarta(timestamp)
    if jakarta_timestamp is None:
        return ""

    today = datetime.now(JAKARTA_TZ).date()
    message_date = jakarta_timestamp.date()
    days_difference = (today - message_date).days

    if days_difference == 0:
        return jakarta_timestamp.strftime("%H:%M")
    if days_difference == 1:
        return "Kemarin"

    month_labels = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "Mei",
        6: "Jun",
        7: "Jul",
        8: "Agu",
        9: "Sep",
        10: "Okt",
        11: "Nov",
        12: "Des",
    }
    return f"{jakarta_timestamp.day:02d} {month_labels[jakarta_timestamp.month]}"


def format_chat_time(timestamp):
    return format_jakarta_clock(timestamp)


def get_chat_thread_id(user_id, contact_id):
    participant_one_id, participant_two_id = chat_pair(user_id, contact_id)
    row = get_db().execute(
        """
        SELECT id
        FROM chat_threads
        WHERE participant_one_id = ? AND participant_two_id = ?
        """,
        (participant_one_id, participant_two_id),
    ).fetchone()
    return row["id"] if row else None


def get_or_create_chat_thread_id(user_id, contact_id):
    thread_id = get_chat_thread_id(user_id, contact_id)
    if thread_id is not None:
        return thread_id

    participant_one_id, participant_two_id = chat_pair(user_id, contact_id)
    try:
        cursor = get_db().execute(
            """
            INSERT INTO chat_threads (participant_one_id, participant_two_id)
            VALUES (?, ?)
            """,
            (participant_one_id, participant_two_id),
        )
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return get_chat_thread_id(user_id, contact_id)


def chat_message_preview(message_payload):
    if message_payload.get("text"):
        return message_payload["text"]
    if message_payload.get("imageUrl"):
        return "Mengirim gambar"
    return "Belum ada pesan"


def chat_message_payload(message, current_user_id):
    created_at = chat_timestamp_iso(message["created_at"])
    attachment_path = message["attachment_path"] or ""
    attachment_type = message["attachment_type"] or ""
    image_url = ""
    if attachment_path and attachment_type == "image":
        image_url = url_for("chat_attachment_file", filename=attachment_path)

    return {
        "id": message["id"],
        "sender": "user" if message["sender_id"] == current_user_id else "contact",
        "type": "image" if image_url else "text",
        "text": message["body"] or "",
        "imageUrl": image_url,
        "imageName": message["attachment_name"] or "Gambar",
        "attachmentType": attachment_type,
        "createdAt": created_at,
        "time": format_chat_time(message["created_at"]),
        "contactTime": format_chat_contact_time(message["created_at"]),
    }


def get_chat_messages(thread_id, current_user_id):
    if thread_id is None:
        return []

    rows = get_db().execute(
        """
        SELECT
            id,
            sender_id,
            body,
            attachment_path,
            attachment_type,
            attachment_name,
            created_at
        FROM chat_messages
        WHERE thread_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (thread_id,),
    ).fetchall()
    return [chat_message_payload(row, current_user_id) for row in rows]


def get_recruiter_chat_relation(recruiter_id, applicant_id):
    return get_db().execute(
        """
        SELECT
            applications.status,
            applications.updated_at,
            opportunities.title AS opportunity_title,
            opportunities.provider AS opportunity_provider
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
          AND opportunities.created_by = ?
        ORDER BY applications.updated_at DESC, applications.id DESC
        LIMIT 1
        """,
        (applicant_id, recruiter_id),
    ).fetchone()


def get_jobseeker_chat_relation(jobseeker_id, recruiter_id):
    return get_db().execute(
        """
        SELECT
            applications.status,
            applications.updated_at,
            opportunities.title AS opportunity_title,
            opportunities.provider AS opportunity_provider
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
          AND opportunities.created_by = ?
        ORDER BY applications.updated_at DESC, applications.id DESC
        LIMIT 1
        """,
        (jobseeker_id, recruiter_id),
    ).fetchone()


def build_chat_contact_payload(contact, relation, current_role, thread_id, messages):
    if current_role == "recruiter":
        role_text = f"Pelamar untuk {relation['opportunity_title']}"
        status_text = application_status_label(relation["status"])
        empty_text = "Belum ada pesan. Mulai percakapan dengan pelamar ini."
    else:
        company_name = (
            contact["company_name"]
            or relation["opportunity_provider"]
            or "Perusahaan"
        )
        role_text = f"Recruiter at {company_name}"
        status_text = contact["company_position"] or "Recruiter"
        empty_text = "Belum ada pesan. Mulai percakapan dengan recruiter ini."

    last_message = chat_message_preview(messages[-1]) if messages else "Belum ada pesan"
    last_time = messages[-1]["contactTime"] if messages else ""
    sort_time = messages[-1]["createdAt"] if messages else chat_timestamp_iso(relation["updated_at"])

    return {
        "id": str(contact["id"]),
        "contactId": contact["id"],
        "threadId": thread_id,
        "name": contact["name"],
        "role": role_text,
        "status": status_text,
        "avatar": chat_avatar_initials(contact["name"]),
        "lastMessage": last_message,
        "time": last_time,
        "sortTime": sort_time,
        "emptyText": empty_text,
        "messages": messages,
    }


def get_chat_contact_payload(current_user_id, current_role, contact_id):
    if contact_id == current_user_id:
        return None

    contact = get_db().execute(
        """
        SELECT id, name, email, role, company_name, company_position
        FROM users
        WHERE id = ?
        """,
        (contact_id,),
    ).fetchone()
    if contact is None:
        return None

    relation = None
    if current_role == "recruiter" and normalize_role(contact["role"]) == "jobseeker":
        relation = get_recruiter_chat_relation(current_user_id, contact_id)
    elif current_role == "jobseeker" and normalize_role(contact["role"]) == "recruiter":
        relation = get_jobseeker_chat_relation(current_user_id, contact_id)

    if relation is None:
        return None

    thread_id = get_chat_thread_id(current_user_id, contact_id)
    messages = get_chat_messages(thread_id, current_user_id)
    return build_chat_contact_payload(
        contact,
        relation,
        current_role,
        thread_id,
        messages,
    )


def get_chat_relation_rows(current_user_id, current_role):
    if current_role == "recruiter":
        return get_db().execute(
            """
            SELECT
                users.id,
                users.name,
                users.email,
                users.role,
                users.company_name,
                users.company_position,
                applications.status,
                applications.updated_at,
                opportunities.title AS opportunity_title,
                opportunities.provider AS opportunity_provider
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            JOIN users ON users.id = applications.user_id
            WHERE opportunities.created_by = ?
            ORDER BY applications.updated_at DESC, applications.id DESC
            """,
            (current_user_id,),
        ).fetchall()

    if current_role == "jobseeker":
        return get_db().execute(
            """
            SELECT
                users.id,
                users.name,
                users.email,
                users.role,
                users.company_name,
                users.company_position,
                applications.status,
                applications.updated_at,
                opportunities.title AS opportunity_title,
                opportunities.provider AS opportunity_provider
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            JOIN users ON users.id = opportunities.created_by
            WHERE applications.user_id = ?
              AND opportunities.created_by IS NOT NULL
            ORDER BY applications.updated_at DESC, applications.id DESC
            """,
            (current_user_id,),
        ).fetchall()

    return []


def get_chat_conversations(current_user_id, current_role, selected_contact_id=None):
    contacts = {}

    for row in get_chat_relation_rows(current_user_id, current_role):
        contact_id = row["id"]
        if contact_id in contacts:
            continue

        thread_id = get_chat_thread_id(current_user_id, contact_id)
        messages = get_chat_messages(thread_id, current_user_id)
        contacts[contact_id] = build_chat_contact_payload(
            row,
            row,
            current_role,
            thread_id,
            messages,
        )

    if selected_contact_id and selected_contact_id not in contacts:
        selected_contact = get_chat_contact_payload(
            current_user_id,
            current_role,
            selected_contact_id,
        )
        if selected_contact is not None:
            contacts[selected_contact_id] = selected_contact

    conversations = list(contacts.values())
    conversations.sort(
        key=lambda conversation: conversation["sortTime"] or "",
        reverse=True,
    )
    return conversations


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_document_filename(user_id, doc_type, original_filename):
    extension = original_filename.rsplit(".", 1)[1].lower()
    safe_doc_type = secure_filename(doc_type.replace("/", "_"))
    return f"user_{user_id}_{safe_doc_type}.{extension}"


def delete_uploaded_file(file_path):
    if not file_path:
        return

    upload_folder = Path(app.config["UPLOAD_FOLDER"]).resolve()
    target_path = (upload_folder / file_path).resolve()

    if upload_folder in target_path.parents and target_path.exists():
        try:
            target_path.unlink()
        except OSError:
            pass


def delete_avatar_file(file_name):
    if not file_name:
        return

    avatar_folder = Path(app.config["AVATAR_UPLOAD_FOLDER"]).resolve()
    target_path = (avatar_folder / file_name).resolve()

    if avatar_folder in target_path.parents and target_path.exists():
        try:
            target_path.unlink()
        except OSError:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Email atau password tidak sesuai. Silakan coba lagi.")
            return render_template("login.html"), 401

        current_role = normalize_role(user["role"])
        if current_role is None:
            flash("Role akun tidak valid. Hubungi admin sistem.")
            return render_template("login.html"), 403

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = current_role
        flash(f"Selamat datang, {user['name']}!")
        if current_role == "admin":
            return redirect(url_for("admin_dashboard"))
        if current_role == "recruiter":
            return redirect(url_for("recruiter_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form_data = {
        "role": "jobseeker",
        "name": "",
        "email": "",
        "skills": "",
        "company_name": "",
        "company_position": "",
        "company_position_other": "",
    }

    if request.method == "POST":
        requested_role = normalize_role(request.form.get("role", "jobseeker"))
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        skills = request.form.get("skills", "").strip()
        company_name = request.form.get("company_name", "").strip()
        company_position_choice = request.form.get("company_position", "").strip()
        company_position_other = request.form.get("company_position_other", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        company_position = (
            company_position_other
            if company_position_choice == "Other"
            else company_position_choice
        )
        form_data = {
            "role": requested_role or "jobseeker",
            "name": name,
            "email": email,
            "skills": skills,
            "company_name": company_name,
            "company_position": company_position_choice,
            "company_position_other": company_position_other,
        }

        if requested_role not in PUBLIC_REGISTER_ROLES:
            flash("Pilih role pendaftaran yang valid: Jobseeker atau Recruiter / HRD.")
            return render_template("register.html", form_data=form_data), 400

        if not name:
            flash("Nama tidak boleh kosong.")
            return render_template("register.html", form_data=form_data), 400

        if not email:
            flash("Email tidak boleh kosong.")
            return render_template("register.html", form_data=form_data), 400

        if not password:
            flash("Password tidak boleh kosong.")
            return render_template("register.html", form_data=form_data), 400

        if not confirm_password:
            flash("Confirm Password tidak boleh kosong.")
            return render_template("register.html", form_data=form_data), 400

        if password != confirm_password:
            flash("Password dan Confirm Password belum sama. Silakan cek kembali.")
            return render_template("register.html", form_data=form_data), 400

        if requested_role == "recruiter":
            if not company_name:
                flash("Nama perusahaan wajib diisi untuk akun recruiter.")
                return render_template("register.html", form_data=form_data), 400
            if company_position_choice not in RECRUITER_POSITION_OPTIONS:
                flash("Pilih posisi recruiter yang valid.")
                return render_template("register.html", form_data=form_data), 400
            if not company_position:
                flash("Posisi recruiter wajib diisi untuk akun recruiter.")
                return render_template("register.html", form_data=form_data), 400
            skills = ""
        else:
            company_name = ""
            company_position = ""
            company_position_other = ""

        existing_user = get_db().execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing_user is not None:
            flash("Email sudah terdaftar. Gunakan email lain atau login.")
            return render_template("register.html", form_data=form_data), 409

        password_hash = generate_password_hash(password)
        cursor = get_db().execute(
            """
            INSERT INTO users
            (name, email, skills, password_hash, role, company_name, company_position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                skills,
                password_hash,
                requested_role,
                company_name,
                company_position,
            ),
        )
        get_db().commit()

        session.clear()
        session["user_id"] = cursor.lastrowid
        session["user_name"] = name
        session["user_role"] = requested_role
        flash(f"Selamat datang, {name}!")
        if requested_role == "recruiter":
            return redirect(url_for("recruiter_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("register.html", form_data=form_data)


@app.route("/logout")
def logout():
    session.clear()
    flash("Kamu sudah logout.")
    return redirect(url_for("login"))


@app.route("/uploads/avatars/<path:filename>")
def profile_avatar(filename):
    if "user_id" not in session:
        abort(404)

    return send_from_directory(app.config["AVATAR_UPLOAD_FOLDER"], filename)


@app.route("/uploads/chat/<path:filename>")
def chat_attachment_file(filename):
    if "user_id" not in session:
        abort(404)

    safe_filename = secure_filename(filename)
    if not safe_filename or safe_filename != filename:
        abort(404)

    attachment = get_db().execute(
        """
        SELECT chat_messages.id
        FROM chat_messages
        JOIN chat_threads ON chat_threads.id = chat_messages.thread_id
        WHERE chat_messages.attachment_path = ?
          AND (
              chat_threads.participant_one_id = ?
              OR chat_threads.participant_two_id = ?
          )
        LIMIT 1
        """,
        (safe_filename, session["user_id"], session["user_id"]),
    ).fetchone()

    if attachment is None:
        abort(404)

    return send_from_directory(app.config["CHAT_UPLOAD_FOLDER"], safe_filename)


def get_ai_assistant_context(user, current_role):
    db = get_db()
    user_id = user["id"]
    context = {
        "display_name": (user["nickname"] or user["name"] or "teman").split()[0],
        "role": current_role,
    }

    if current_role == "jobseeker":
        document_progress = get_document_progress_for_user(user_id)
        context.update(
            {
                "saved_count": db.execute(
                    "SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (user_id,)
                ).fetchone()[0],
                "application_count": db.execute(
                    "SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)
                ).fetchone()[0],
                "document_completed": document_progress["complete_count"],
                "document_total": document_progress["total_count"],
                "skills": user["skills"] or "",
                "major": user["major"] or "",
                "desired_positions": user["desired_positions"] or "",
            }
        )
        return context

    if current_role == "recruiter":
        context.update(
            {
                "company_name": user["company_name"] or "perusahaanmu",
                "post_count": db.execute(
                    "SELECT COUNT(*) FROM opportunities WHERE created_by = ?", (user_id,)
                ).fetchone()[0],
                "applicant_count": db.execute(
                    """
                    SELECT COUNT(*)
                    FROM applications
                    JOIN opportunities ON opportunities.id = applications.opportunity_id
                    WHERE opportunities.created_by = ?
                    """,
                    (user_id,),
                ).fetchone()[0],
            }
        )
        return context

    return context


def build_ai_assistant_reply(message, context):
    text = message.lower()
    name = context["display_name"]
    role = context["role"]

    if role == "jobseeker":
        if any(keyword in text for keyword in ["cv", "resume", "dokumen", "berkas"]):
            return (
                f"{name}, dokumenmu sudah {context['document_completed']}/"
                f"{context['document_total']} lengkap. Prioritaskan CV, transkrip, "
                "sertifikat paling relevan, lalu motivation letter yang spesifik ke program. "
                "Kalau mau cepat, buka menu Dokumen dan cek item yang masih kosong."
            )
        if any(keyword in text for keyword in ["interview", "wawancara"]):
            return (
                "Untuk interview, siapkan jawaban 60-90 detik: siapa kamu, proyek data "
                "terkuatmu, dampaknya, dan kenapa cocok dengan peluang itu. Latih juga "
                "1 contoh konflik/tantangan memakai format STAR."
            )
        if any(keyword in text for keyword in ["lamaran", "daftar", "aplikasi", "track"]):
            return (
                f"Saat ini kamu punya {context['application_count']} lamaran/track. "
                "Urutkan dari deadline terdekat, lanjutkan yang statusnya belum lengkap, "
                "dan simpan catatan kecil setelah setiap update supaya progresnya tidak hilang."
            )
        if any(keyword in text for keyword in ["peluang", "beasiswa", "magang", "rekomendasi"]):
            skill_hint = context["skills"] or context["desired_positions"] or context["major"]
            if skill_hint:
                return (
                    f"Aku akan mulai dari kata kunci profilmu: {skill_hint}. "
                    "Coba cari peluang dengan 2-3 skill utama, lalu bandingkan deadline, "
                    "lokasi, dan kecocokan dokumen sebelum menekan Track."
                )
            return (
                "Mulai dari peluang dengan deadline dekat dan requirement yang paling mirip "
                "dengan skill kamu. Lengkapi profil agar skor kecocokan rekomendasi lebih tajam."
            )
        if any(keyword in text for keyword in ["profil", "profile", "skill", "jurusan"]):
            return (
                "Profil yang kuat biasanya punya ringkasan singkat, 5-8 skill spesifik, "
                "jurusan/kampus, target posisi, dan link portofolio. Bagian itu membantu "
                "kartu peluang terasa lebih personal."
            )
        return (
            f"Siap, {name}. Aku bisa bantu review CV, menyusun strategi daftar, "
            "menyiapkan interview, atau memilih peluang yang paling sesuai dengan profilmu."
        )

    if role == "recruiter":
        if any(keyword in text for keyword in ["lowongan", "post", "job", "magang", "peluang"]):
            return (
                f"Untuk {context['company_name']}, buat lowongan dengan judul spesifik, "
                "deskripsi tugas harian, skill wajib, lokasi/arrangement kerja, dan deadline. "
                "Semakin jelas requirement-nya, semakin mudah kandidat yang tepat masuk."
            )
        if any(keyword in text for keyword in ["kandidat", "pelamar", "applicant", "shortlist"]):
            return (
                f"Kamu punya {context['applicant_count']} pelamar dari "
                f"{context['post_count']} posting. Mulai shortlist dari skill wajib, "
                "portofolio/proyek yang relevan, lalu catat alasan status agar proses HR rapi."
            )
        if any(keyword in text for keyword in ["interview", "wawancara"]):
            return (
                "Untuk interview kandidat, pakai 3 blok: validasi pengalaman, studi kasus kecil, "
                "dan motivasi. Tutup dengan ekspektasi timeline supaya kandidat jelas menunggu apa."
            )
        return (
            f"Siap, {name}. Aku bisa bantu merapikan lowongan, menyusun kriteria shortlist, "
            "menyiapkan pertanyaan interview, atau membaca progres applicant."
        )

    return (
        "Aku siap membantu navigasi Pathora: mencari peluang, menyiapkan dokumen, "
        "atau membaca progres akun sesuai role yang sedang aktif."
    )


def contains_sensitive_ai_content(message):
    lowered = message.lower()
    sensitive_value_patterns = [
        r"\b(password|kata sandi|api[_\s-]?key|token|secret)\b\s*[:=]\s*\S+",
        r"\b(otp|kode otp|kode verifikasi)\b.{0,24}\d{4,8}\b",
        r"\b(sk-[A-Za-z0-9_-]{8,}|nvapi-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{20,})\b",
    ]

    if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in sensitive_value_patterns):
        return True

    sensitive_share_patterns = [
        r"\b(password|kata sandi|api[_\s-]?key|token|secret) saya\s+(adalah|=|:)\s+\S+",
        r"\b(otp|kode otp) saya\s+(adalah|=|:)?\s*\d{4,8}\b",
    ]
    return any(
        re.search(pattern, lowered, flags=re.IGNORECASE)
        for pattern in sensitive_share_patterns
    )


def build_google_assistant_prompt(user_message):
    return f"{AI_ASSISTANT_SYSTEM_PROMPT}\n\nPertanyaan user:\n{user_message}"


@app.get("/api/assistant/health")
def api_assistant_health():
    google_genai_imported = genai is not None
    api_key_configured = bool(GOOGLE_API_KEY)
    endpoint_ready = bool(
        google_genai_imported and api_key_configured and google_client is not None
    )
    return jsonify(
        {
            "google_genai_imported": google_genai_imported,
            "api_key_configured": api_key_configured,
            "model": GOOGLE_MODEL,
            "endpoint_ready": endpoint_ready,
        }
    )


@app.post("/api/assistant")
def api_assistant():
    login_redirect = require_login()
    if login_redirect is not None:
        return jsonify({"error": "Silakan login terlebih dahulu."}), 401

    if get_current_user() is None:
        session.clear()
        return jsonify({"error": "Sesi akun tidak ditemukan. Silakan login ulang."}), 401

    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Pesan tidak boleh kosong."}), 400

    if len(user_message) > AI_ASSISTANT_MAX_MESSAGE_LENGTH:
        return jsonify({"error": "Pesan terlalu panjang. Maksimal 1000 karakter."}), 400

    if contains_sensitive_ai_content(user_message):
        return jsonify(
            {
                "error": (
                    "Jangan kirim password, OTP, API key, atau data sensitif "
                    "ke AI Assistant."
                )
            }
        ), 400

    if not GOOGLE_API_KEY or google_client is None:
        return jsonify({"error": "Konfigurasi AI Assistant belum tersedia."}), 500

    try:
        response = None
        for attempt in range(2):
            try:
                response = google_client.models.generate_content(
                    model=GOOGLE_MODEL,
                    contents=build_google_assistant_prompt(user_message),
                )
                break
            except Exception:
                if attempt == 0:
                    sleep(1)
                    continue
                raise

        try:
            answer = (getattr(response, "text", "") or "").strip()
        except Exception as error:
            app.logger.warning(
                "Google AI Assistant response parse failed: %s: %s",
                error.__class__.__name__,
                redact_sensitive_log_text(error),
            )
            answer = ""

        if not answer:
            answer = "Maaf, saya belum bisa memberikan jawaban saat ini."

        return jsonify({"answer": answer})
    except Exception as error:
        app.logger.warning(
            "Google AI Assistant request failed: %s: %s",
            error.__class__.__name__,
            redact_sensitive_log_text(error),
        )
        return jsonify({"error": AI_ASSISTANT_GENERIC_ERROR}), 500


@app.route("/ai-assistant/chat", methods=["POST"])
def ai_assistant_chat():
    response = api_assistant()
    response_body = response[0] if isinstance(response, tuple) else response
    status_code = response[1] if isinstance(response, tuple) and len(response) > 1 else response_body.status_code

    if status_code >= 400:
        return response

    data = response_body.get_json(silent=True) or {}
    answer = data.get("answer") or "Maaf, saya belum bisa memberikan jawaban saat ini."
    return jsonify(
        {
            "answer": answer,
            "reply": answer,
            "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0"),
        }
    )


@app.route("/profile")
def profile():
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    user = get_current_user_profile()
    document_progress = get_document_progress_for_user(session["user_id"])
    profile_completion = get_profile_completion(user, document_progress)

    return render_template(
        "profile.html",
        user=user,
        skills=split_profile_list(user["skills"]),
        interests=split_profile_list(user["interests"]),
        desired_positions=split_profile_list(user["desired_positions"]),
        saved_opportunities=get_saved_profile_opportunities(session["user_id"]),
        document_progress=document_progress,
        profile_completion=profile_completion,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    user = get_current_user_profile()
    if user is None:
        abort(404)

    document_progress = get_document_progress_for_user(session["user_id"])

    if request.method == "POST":
        form_data = {
            field: request.form.get(field, "").strip()
            for field in PROFILE_FORM_FIELDS
        }
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        validation_errors = []

        if not form_data["name"]:
            validation_errors.append("Nama lengkap wajib diisi.")
        if not form_data["email"]:
            validation_errors.append("Email wajib diisi.")

        if form_data["email"]:
            existing_user = get_db().execute(
                """
                SELECT id FROM users
                WHERE email = ? AND id != ?
                """,
                (form_data["email"].lower(), session["user_id"]),
            ).fetchone()
            if existing_user is not None:
                validation_errors.append("Email sudah digunakan akun lain.")
            form_data["email"] = form_data["email"].lower()

        if form_data["birth_date"] and not is_valid_date(form_data["birth_date"]):
            validation_errors.append("Tanggal lahir harus memakai format YYYY-MM-DD.")

        if form_data["gpa"]:
            try:
                gpa_value = float(form_data["gpa"])
            except ValueError:
                validation_errors.append("IPK harus berupa angka antara 0.00 sampai 4.00.")
            else:
                if gpa_value < 0 or gpa_value > 4:
                    validation_errors.append("IPK harus berada di antara 0.00 sampai 4.00.")
                else:
                    form_data["gpa"] = f"{gpa_value:.2f}".rstrip("0").rstrip(".")

        if form_data["semester"]:
            try:
                semester_value = int(form_data["semester"])
            except ValueError:
                validation_errors.append("Semester harus berupa angka.")
            else:
                if semester_value < 1 or semester_value > 14:
                    validation_errors.append("Semester harus berada di rentang 1 sampai 14.")

        if form_data["entry_year"]:
            current_year = datetime.now().year
            try:
                entry_year_value = int(form_data["entry_year"])
            except ValueError:
                validation_errors.append("Tahun masuk harus berupa angka.")
            else:
                if entry_year_value < 1900 or entry_year_value > current_year + 1:
                    validation_errors.append("Tahun masuk tidak valid.")

        wants_password_change = any([old_password, new_password, confirm_password])
        password_hash = user["password_hash"]
        if wants_password_change:
            if not old_password:
                validation_errors.append("Kata sandi lama wajib diisi untuk mengganti password.")
            if not new_password:
                validation_errors.append("Kata sandi baru wajib diisi.")
            if new_password and len(new_password) < 8:
                validation_errors.append("Kata sandi baru minimal 8 karakter.")
            if new_password != confirm_password:
                validation_errors.append("Konfirmasi kata sandi baru belum sama.")
            if old_password and not check_password_hash(user["password_hash"], old_password):
                validation_errors.append("Kata sandi lama tidak sesuai.")
            if not validation_errors:
                password_hash = generate_password_hash(new_password)

        uploaded_avatar = request.files.get("avatar_file")
        if uploaded_avatar and uploaded_avatar.filename:
            if not is_allowed_image_file(uploaded_avatar.filename):
                validation_errors.append("Foto profil harus berupa JPG, JPEG, atau PNG.")

        if validation_errors:
            for error in validation_errors:
                flash(error)
            return (
                render_template(
                    "profile_edit.html",
                    user=user,
                    form_data=form_data,
                    document_progress=document_progress,
                    profile_completion=get_profile_completion(form_data, document_progress),
                ),
                400,
            )

        avatar_path = user["avatar_path"] or ""
        if request.form.get("remove_avatar") == "1":
            delete_avatar_file(avatar_path)
            avatar_path = ""

        if uploaded_avatar and uploaded_avatar.filename:
            avatar_folder = Path(app.config["AVATAR_UPLOAD_FOLDER"])
            avatar_folder.mkdir(parents=True, exist_ok=True)
            avatar_filename = make_avatar_filename(session["user_id"], uploaded_avatar.filename)
            if avatar_path and avatar_path != avatar_filename:
                delete_avatar_file(avatar_path)
            uploaded_avatar.save(avatar_folder / avatar_filename)
            avatar_path = avatar_filename

        update_fields = PROFILE_FORM_FIELDS + ["avatar_path", "password_hash"]
        set_clause = ", ".join(f"{field} = ?" for field in update_fields)
        update_values = [form_data[field] for field in PROFILE_FORM_FIELDS]
        update_values.extend([avatar_path, password_hash, session["user_id"]])

        try:
            get_db().execute(
                f"""
                UPDATE users
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                update_values,
            )
            get_db().commit()
        except sqlite3.Error:
            flash("Profil belum bisa disimpan. Silakan coba lagi.")
            return redirect(url_for("edit_profile"))

        session["user_name"] = form_data["name"]
        flash("Profil berhasil diperbarui.")
        return redirect(url_for("profile"))

    form_data = profile_form_data_from_user(user)
    return render_template(
        "profile_edit.html",
        user=user,
        form_data=form_data,
        document_progress=document_progress,
        profile_completion=get_profile_completion(user, document_progress),
    )


@app.route("/dashboard")
def dashboard():
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    user_id = session["user_id"]
    summary = get_dashboard_summary(user_id)
    progress_percent = 0
    if summary["total_documents"]:
        progress_percent = round(
            (summary["completed_documents"] / summary["total_documents"]) * 100
        )

    urgent_deadlines = get_urgent_deadlines(user_id)
    top_priority = get_top_priority_opportunity()
    summary["total_urgent"] = len(urgent_deadlines)

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        summary=summary,
        progress_percent=progress_percent,
        recent_saved=get_recent_saved_opportunities(user_id),
        recent_applications=get_recent_applications(user_id),
        urgent_deadlines=urgent_deadlines,
        top_priority=top_priority,
    )


@app.route("/opportunities")
def opportunities():
    search_query = request.args.get("q", "").strip()
    opportunity_type = request.args.get("type", "").strip().lower()
    location = request.args.get("location", "").strip()
    sort_by = request.args.get("sort", "deadline").strip().lower()

    filters = []
    params = []

    if search_query:
        filters.append(
            "(title LIKE ? OR provider LIKE ? OR location LIKE ? OR description LIKE ?)"
        )
        keyword = f"%{search_query}%"
        params.extend([keyword, keyword, keyword, keyword])

    if opportunity_type in {"internship", "scholarship"}:
        filters.append("type = ?")
        params.append(opportunity_type)

    if location:
        filters.append("location LIKE ?")
        params.append(f"%{location}%")

    query = "SELECT * FROM opportunities"
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY deadline ASC"

    rows = get_db().execute(query, params).fetchall()
    opportunity_list = [Opportunity.from_row(row) for row in rows]
    current_role = get_current_role() if "user_id" in session else None
    scoring_context = get_user_scoring_context()

    for opportunity in opportunity_list:
        apply_priority_score(opportunity, scoring_context)

    if sort_by == "priority" and scoring_context is not None:
        opportunity_list.sort(
            key=lambda opportunity: opportunity.priority_score or 0,
            reverse=True,
        )

    location_rows = get_db().execute(
        "SELECT DISTINCT location FROM opportunities ORDER BY location ASC"
    ).fetchall()
    locations = [row["location"] for row in location_rows]

    return render_template(
        "opportunities.html",
        opportunities=opportunity_list,
        filters={
            "q": search_query,
            "type": opportunity_type,
            "location": location,
            "sort": sort_by,
        },
        locations=locations,
        is_logged_in="user_id" in session,
        can_use_jobseeker_actions=current_role == "jobseeker",
    )


@app.route("/opportunities/<int:opportunity_id>")
def opportunity_detail(opportunity_id):
    row = get_opportunity_or_404(opportunity_id)
    opportunity = Opportunity.from_row(row)
    current_role = get_current_role() if "user_id" in session else None
    scoring_context = get_user_scoring_context()
    apply_priority_score(opportunity, scoring_context)
    return render_template(
        "opportunity_detail.html",
        opportunity=opportunity,
        is_logged_in="user_id" in session,
        can_use_jobseeker_actions=current_role == "jobseeker",
    )


@app.route("/opportunities/<int:opportunity_id>/bookmark", methods=["POST"])
def bookmark_opportunity(opportunity_id):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    get_opportunity_or_404(opportunity_id)

    try:
        get_db().execute(
            """
            INSERT INTO bookmarks (user_id, opportunity_id)
            VALUES (?, ?)
            """,
            (session["user_id"], opportunity_id),
        )
        get_db().commit()
        flash("Peluang berhasil disimpan.")
    except sqlite3.IntegrityError:
        flash("Peluang ini sudah ada di Bookmark.")
    except sqlite3.Error:
        flash("Peluang belum bisa disimpan. Silakan coba lagi.")

    return redirect(request.referrer or url_for("opportunities"))


@app.route("/bookmarks/<int:opportunity_id>/remove", methods=["POST"])
def remove_bookmark(opportunity_id):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    try:
        get_db().execute(
            """
            DELETE FROM bookmarks
            WHERE user_id = ? AND opportunity_id = ?
            """,
            (session["user_id"], opportunity_id),
        )
        get_db().commit()
        flash("Peluang dihapus dari Bookmark.")
    except sqlite3.Error:
        flash("Peluang belum bisa dihapus. Silakan coba lagi.")

    return redirect(request.referrer or url_for("bookmarks"))


@app.route("/bookmarks")
def bookmarks():
    try:
        login_redirect = jobseeker_required()
        if login_redirect is not None:
            return login_redirect

        saved_opportunities = get_saved_profile_opportunities(session["user_id"])
    except DatabaseAccessError:
        raise
    except sqlite3.Error as exc:
        raise DatabaseAccessError(
            build_database_error_message("Halaman Bookmark tidak bisa membaca database.")
        ) from exc

    return render_template(
        "bookmarks.html",
        opportunities=saved_opportunities,
    )


@app.route("/chat")
def chat():
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect

    current_role = get_current_role()
    selected_contact_id = parse_positive_int(
        request.args.get("user_id")
        or request.args.get("contact_id")
        or request.args.get("contact")
    )
    conversations = get_chat_conversations(
        session["user_id"],
        current_role,
        selected_contact_id,
    )

    if selected_contact_id and not any(
        conversation["contactId"] == selected_contact_id
        for conversation in conversations
    ):
        flash("Kontak chat tidak ditemukan atau tidak dapat diakses.")
        selected_contact_id = None

    return render_template(
        "chat.html",
        chat_conversations=conversations,
        selected_contact_id=str(selected_contact_id) if selected_contact_id else "",
    )


@app.route("/chat/messages", methods=["POST"])
def send_chat_message():
    if "user_id" not in session:
        return jsonify({"error": "Silakan login terlebih dahulu."}), 401

    current_role = get_current_role()
    payload = request.get_json(silent=True) or {}
    form_data = request.form or {}
    contact_id = parse_positive_int(
        payload.get("contact_id") or form_data.get("contact_id")
    )
    message = (payload.get("message") or form_data.get("message") or "").strip()
    uploaded_image = (
        request.files.get("image")
        or request.files.get("attachment")
        or request.files.get("file")
    )

    if contact_id is None:
        return jsonify({"error": "Kontak chat tidak valid."}), 400
    if not message and (uploaded_image is None or not uploaded_image.filename):
        return jsonify({"error": "Pesan atau gambar wajib diisi."}), 400
    if len(message) > CHAT_MESSAGE_MAX_LENGTH:
        return jsonify({"error": "Pesan terlalu panjang."}), 400
    if uploaded_image and uploaded_image.filename:
        if not is_allowed_chat_image_file(uploaded_image):
            return jsonify({"error": "Hanya file gambar yang dapat dikirim."}), 400
        if get_uploaded_file_size(uploaded_image) > CHAT_IMAGE_MAX_BYTES:
            return jsonify({"error": "Ukuran gambar maksimal 5 MB."}), 400

    contact = get_chat_contact_payload(session["user_id"], current_role, contact_id)
    if contact is None:
        return jsonify({"error": "Kontak chat tidak ditemukan atau tidak dapat diakses."}), 403

    attachment_path = ""
    attachment_type = ""
    attachment_name = ""

    if uploaded_image and uploaded_image.filename:
        attachment_path = make_chat_attachment_filename(
            session["user_id"],
            uploaded_image.filename,
        )
        attachment_type = "image"
        attachment_name = secure_filename(uploaded_image.filename) or "gambar"
        try:
            chat_upload_folder = Path(app.config["CHAT_UPLOAD_FOLDER"])
            chat_upload_folder.mkdir(parents=True, exist_ok=True)
            uploaded_image.save(chat_upload_folder / attachment_path)
        except OSError:
            return jsonify({"error": "Gambar belum bisa diunggah. Silakan coba lagi."}), 500

    try:
        thread_id = get_or_create_chat_thread_id(session["user_id"], contact_id)
        created_at = now_utc().isoformat(timespec="seconds")
        cursor = get_db().execute(
            """
            INSERT INTO chat_messages
                (thread_id, sender_id, body, attachment_path, attachment_type,
                 attachment_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                session["user_id"],
                message,
                attachment_path,
                attachment_type,
                attachment_name,
                created_at,
            ),
        )
        get_db().execute(
            """
            UPDATE chat_threads
            SET updated_at = ?
            WHERE id = ?
            """,
            (created_at, thread_id),
        )
        get_db().commit()
        saved_message = get_db().execute(
            """
            SELECT
                id,
                sender_id,
                body,
                attachment_path,
                attachment_type,
                attachment_name,
                created_at
            FROM chat_messages
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    except sqlite3.Error:
        get_db().rollback()
        if attachment_path:
            try:
                (Path(app.config["CHAT_UPLOAD_FOLDER"]) / attachment_path).unlink()
            except OSError:
                pass
        return jsonify({"error": "Pesan belum bisa dikirim. Silakan coba lagi."}), 500

    return jsonify(
        {
            "thread_id": thread_id,
            "message": chat_message_payload(saved_message, session["user_id"]),
        }
    )


@app.route("/opportunities/<int:opportunity_id>/track", methods=["POST"])
def track_opportunity(opportunity_id):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    get_opportunity_or_404(opportunity_id)

    try:
        get_db().execute(
            """
            INSERT INTO applications (user_id, opportunity_id, status, notes)
            VALUES (?, ?, ?, ?)
            """,
            (session["user_id"], opportunity_id, APPLICATION_STATUS_APPLIED, ""),
        )
        get_db().commit()
        flash("Lamaran berhasil dikirim.")
        return redirect(url_for("applications"))
    except sqlite3.IntegrityError:
        flash("Kamu sudah mendaftar pada peluang ini.")
        return redirect(url_for("applications"))
    except sqlite3.Error:
        flash("Tracker belum bisa ditambahkan. Silakan coba lagi.")
        return redirect(request.referrer or url_for("opportunities"))


@app.route("/applications")
def applications():
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    rows = get_db().execute(
        """
        SELECT
            applications.id AS application_id,
            applications.status,
            applications.notes,
            applications.applied_at,
            applications.updated_at,
            opportunities.id AS opportunity_id,
            opportunities.title,
            opportunities.provider,
            opportunities.type,
            opportunities.location,
            opportunities.deadline
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
        ORDER BY applications.updated_at DESC
        """,
        (session["user_id"],),
    ).fetchall()

    return render_template(
        "applications.html",
        applications=rows,
    )


@app.route("/applications/<int:application_id>/update", methods=["POST"])
def update_application(application_id):
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect

    current_role = get_current_role()
    if current_role == "jobseeker":
        flash("Kamu tidak memiliki izin untuk mengubah status lamaran.")
        return redirect(url_for("applications"))

    flash("Kamu tidak memiliki izin untuk mengubah status lamaran.")
    abort(403)


@app.route("/applications/<int:application_id>/remove", methods=["POST"])
def remove_application(application_id):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    get_application_for_user_or_404(application_id)

    try:
        get_db().execute(
            """
            DELETE FROM applications
            WHERE id = ? AND user_id = ?
            """,
            (application_id, session["user_id"]),
        )
        get_db().commit()
        flash("Tracker lamaran berhasil dihapus.")
    except sqlite3.Error:
        flash("Tracker belum bisa dihapus. Silakan coba lagi.")

    return redirect(url_for("applications"))


@app.route("/documents")
def documents():
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    rows = get_db().execute(
        """
        SELECT * FROM documents
        WHERE user_id = ?
        """,
        (session["user_id"],),
    ).fetchall()
    document_by_type = {row["doc_type"]: Document.from_row(row, session["user_id"]) for row in rows}

    documents_list = []
    for doc_type in DOCUMENT_TYPES:
        document = document_by_type.get(
            doc_type,
            Document(
                document_id=None,
                user_id=session["user_id"],
                doc_type=doc_type,
            ),
        )
        documents_list.append(document)

    complete_count = sum(1 for document in documents_list if document.is_complete())

    return render_template(
        "documents.html",
        documents=documents_list,
        complete_count=complete_count,
        total_count=len(DOCUMENT_TYPES),
    )


@app.route("/documents/<path:doc_type>/update", methods=["POST"])
def update_document(doc_type):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    if doc_type not in DOCUMENT_TYPES:
        abort(404)

    notes = request.form.get("notes", "").strip()
    uploaded_file = request.files.get("document_file")

    existing_document = get_document_for_user(doc_type)

    file_name = existing_document["file_name"] if existing_document else ""
    file_path = existing_document["file_path"] if existing_document else ""
    is_uploaded = 1 if request.form.get("is_uploaded") == "on" else 0

    if uploaded_file and uploaded_file.filename:
        if not is_allowed_file(uploaded_file.filename):
            flash("Format file tidak didukung. Gunakan PDF, DOC, DOCX, PNG, JPG, atau JPEG.")
            return redirect(url_for("documents"))

        original_file_name = secure_filename(uploaded_file.filename)
        saved_file_name = make_document_filename(
            session["user_id"], doc_type, original_file_name
        )
        upload_folder = Path(app.config["UPLOAD_FOLDER"])
        upload_folder.mkdir(parents=True, exist_ok=True)
        uploaded_file.save(upload_folder / saved_file_name)

        if existing_document and existing_document["file_path"] != saved_file_name:
            delete_uploaded_file(existing_document["file_path"])

        file_name = original_file_name
        file_path = saved_file_name
        is_uploaded = 1

    try:
        get_db().execute(
            """
            INSERT INTO documents (user_id, doc_type, file_name, file_path, is_uploaded, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, doc_type) DO UPDATE SET
                file_name = excluded.file_name,
                file_path = excluded.file_path,
                is_uploaded = excluded.is_uploaded,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session["user_id"], doc_type, file_name, file_path, is_uploaded, notes),
        )
        get_db().commit()
        flash(f"Dokumen {doc_type} berhasil diperbarui.")
    except sqlite3.Error:
        flash("Dokumen belum bisa diperbarui. Silakan coba lagi.")

    return redirect(url_for("documents"))


@app.route("/documents/<path:doc_type>/reset", methods=["POST"])
def reset_document(doc_type):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    if doc_type not in DOCUMENT_TYPES:
        abort(404)

    existing_document = get_document_for_user(doc_type)

    try:
        if existing_document:
            delete_uploaded_file(existing_document["file_path"])

        get_db().execute(
            """
            INSERT INTO documents (user_id, doc_type, file_name, file_path, is_uploaded, notes)
            VALUES (?, ?, '', '', 0, '')
            ON CONFLICT(user_id, doc_type) DO UPDATE SET
                file_name = '',
                file_path = '',
                is_uploaded = 0,
                notes = '',
                updated_at = CURRENT_TIMESTAMP
            """,
            (session["user_id"], doc_type),
        )
        get_db().commit()
        flash(f"Dokumen {doc_type} berhasil di-reset.")
    except sqlite3.Error:
        flash("Dokumen belum bisa di-reset. Silakan coba lagi.")

    return redirect(url_for("documents"))


@app.route("/documents/<path:doc_type>/download")
def download_document(doc_type):
    login_redirect = jobseeker_required()
    if login_redirect is not None:
        return login_redirect

    if doc_type not in DOCUMENT_TYPES:
        abort(404)

    document = get_document_for_user(doc_type)

    if document is None or not document["file_path"]:
        flash("File dokumen belum tersedia.")
        return redirect(url_for("documents"))

    file_path = Path(app.config["UPLOAD_FOLDER"]) / document["file_path"]
    if not file_path.exists():
        flash("File dokumen tidak ditemukan di folder upload.")
        return redirect(url_for("documents"))

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        document["file_path"],
        as_attachment=False,
        download_name=document["file_name"],
    )


@app.route("/recruiter/dashboard")
def recruiter_dashboard():
    recruiter_redirect = recruiter_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    recruiter = get_current_user()
    total_opportunities = get_db().execute(
        "SELECT COUNT(*) FROM opportunities WHERE created_by = ?",
        (session["user_id"],),
    ).fetchone()[0]
    total_applicants = get_db().execute(
        """
        SELECT COUNT(*)
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE opportunities.created_by = ?
        """,
        (session["user_id"],),
    ).fetchone()[0]
    recent_opportunities = get_db().execute(
        """
        SELECT opportunities.*, COUNT(applications.id) AS applicant_count
        FROM opportunities
        LEFT JOIN applications ON applications.opportunity_id = opportunities.id
        WHERE opportunities.created_by = ?
        GROUP BY opportunities.id
        ORDER BY opportunities.updated_at DESC
        LIMIT 3
        """,
        (session["user_id"],),
    ).fetchall()
    recent_applicants = get_recruiter_applicant_rows()[:5]

    return render_template(
        "recruiter/dashboard.html",
        recruiter=recruiter,
        total_opportunities=total_opportunities,
        total_applicants=total_applicants,
        recent_opportunities=recent_opportunities,
        recent_applicants=recent_applicants,
    )


@app.route("/recruiter/opportunities")
def recruiter_opportunities():
    recruiter_redirect = recruiter_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    rows = get_db().execute(
        """
        SELECT opportunities.*, COUNT(applications.id) AS applicant_count
        FROM opportunities
        LEFT JOIN applications ON applications.opportunity_id = opportunities.id
        WHERE opportunities.created_by = ?
        GROUP BY opportunities.id
        ORDER BY opportunities.updated_at DESC
        """,
        (session["user_id"],),
    ).fetchall()

    return render_template("recruiter/opportunities.html", opportunities=rows)


@app.route("/recruiter/opportunities/create", methods=["GET", "POST"])
def recruiter_create_opportunity():
    recruiter_redirect = recruiter_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    recruiter = get_current_user()
    company_name = recruiter["company_name"] or ""
    opportunity = {
        "title": "",
        "type": "internship",
        "provider": company_name,
        "location": "",
        "deadline": "",
        "description": "",
        "requirements": "",
        "official_link": "",
        "required_skills": "",
    }

    if request.method == "POST":
        opportunity = get_opportunity_form_data()
        errors = validate_opportunity_form(opportunity)
        if errors:
            for error in errors:
                flash(error)
            return render_template(
                "recruiter/opportunity_form.html",
                opportunity=opportunity,
                form_title="Tambah Lowongan",
                action_url=url_for("recruiter_create_opportunity"),
            ), 400

        try:
            get_db().execute(
                """
                INSERT INTO opportunities
                (title, provider, type, description, requirements, official_link,
                 required_skills, location, deadline, created_by, company_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity["title"],
                    opportunity["provider"],
                    opportunity["type"],
                    opportunity["description"],
                    opportunity["requirements"],
                    opportunity["official_link"],
                    opportunity["required_skills"],
                    opportunity["location"],
                    opportunity["deadline"],
                    session["user_id"],
                    company_name,
                ),
            )
            get_db().commit()
            flash("Lowongan berhasil dibuat.")
            return redirect(url_for("recruiter_opportunities"))
        except sqlite3.Error:
            flash("Lowongan belum bisa dibuat. Silakan coba lagi.")

    return render_template(
        "recruiter/opportunity_form.html",
        opportunity=opportunity,
        form_title="Tambah Lowongan",
        action_url=url_for("recruiter_create_opportunity"),
    )


@app.route("/recruiter/opportunities/<int:opportunity_id>/edit", methods=["GET", "POST"])
def recruiter_edit_opportunity(opportunity_id):
    recruiter_redirect = recruiter_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    recruiter = get_current_user()
    row = get_recruiter_opportunity_or_404(opportunity_id)
    opportunity = dict(row)

    if request.method == "POST":
        opportunity = get_opportunity_form_data()
        errors = validate_opportunity_form(opportunity)
        if errors:
            for error in errors:
                flash(error)
            return render_template(
                "recruiter/opportunity_form.html",
                opportunity=opportunity,
                form_title="Edit Lowongan",
                action_url=url_for(
                    "recruiter_edit_opportunity", opportunity_id=opportunity_id
                ),
            ), 400

        try:
            get_db().execute(
                """
                UPDATE opportunities
                SET title = ?, provider = ?, type = ?, description = ?,
                    requirements = ?, official_link = ?, required_skills = ?,
                    location = ?, deadline = ?, company_name = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND created_by = ?
                """,
                (
                    opportunity["title"],
                    opportunity["provider"],
                    opportunity["type"],
                    opportunity["description"],
                    opportunity["requirements"],
                    opportunity["official_link"],
                    opportunity["required_skills"],
                    opportunity["location"],
                    opportunity["deadline"],
                    recruiter["company_name"] or "",
                    opportunity_id,
                    session["user_id"],
                ),
            )
            get_db().commit()
            flash("Lowongan berhasil diperbarui.")
            return redirect(url_for("recruiter_opportunities"))
        except sqlite3.Error:
            flash("Lowongan belum bisa diperbarui. Silakan coba lagi.")

    return render_template(
        "recruiter/opportunity_form.html",
        opportunity=opportunity,
        form_title="Edit Lowongan",
        action_url=url_for("recruiter_edit_opportunity", opportunity_id=opportunity_id),
    )


@app.route("/recruiter/opportunities/<int:opportunity_id>/delete", methods=["POST"])
def recruiter_delete_opportunity(opportunity_id):
    recruiter_redirect = recruiter_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    get_recruiter_opportunity_or_404(opportunity_id)

    try:
        get_db().execute(
            "DELETE FROM bookmarks WHERE opportunity_id = ?", (opportunity_id,)
        )
        get_db().execute(
            "DELETE FROM applications WHERE opportunity_id = ?", (opportunity_id,)
        )
        get_db().execute(
            "DELETE FROM opportunities WHERE id = ? AND created_by = ?",
            (opportunity_id, session["user_id"]),
        )
        get_db().commit()
        flash("Lowongan berhasil dihapus.")
    except sqlite3.Error:
        flash("Lowongan belum bisa dihapus. Silakan coba lagi.")

    return redirect(url_for("recruiter_opportunities"))


@app.route("/recruiter/applicants")
def recruiter_applicants():
    recruiter_redirect = recruiter_or_admin_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    current_sort = normalize_applicant_sort(request.args.get("sort", APPLICANT_SORT_RECENT))
    return render_template(
        "recruiter/applicants.html",
        applicants=get_recruiter_applicant_rows(sort_by=current_sort),
        opportunity=None,
        statuses=RECRUITER_APPLICATION_STATUSES,
        current_sort=current_sort,
    )


@app.route("/recruiter/opportunities/<int:opportunity_id>/applicants")
def recruiter_opportunity_applicants(opportunity_id):
    recruiter_redirect = recruiter_or_admin_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    opportunity = get_recruiter_opportunity_or_404(opportunity_id)
    current_sort = normalize_applicant_sort(request.args.get("sort", APPLICANT_SORT_RECENT))
    return render_template(
        "recruiter/applicants.html",
        applicants=get_recruiter_applicant_rows(opportunity_id, current_sort),
        opportunity=opportunity,
        statuses=RECRUITER_APPLICATION_STATUSES,
        current_sort=current_sort,
    )


@app.route("/recruiter/applicants/export.csv")
def recruiter_applicants_export():
    recruiter_redirect = recruiter_or_admin_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    opportunity_id = parse_positive_int(request.args.get("opportunity_id"))
    opportunity = get_recruiter_opportunity_or_404(opportunity_id) if opportunity_id else None
    current_sort = normalize_applicant_sort(request.args.get("sort", APPLICANT_SORT_RECENT))
    applicants = get_recruiter_applicant_rows(opportunity_id, current_sort)
    return make_recruiter_applicants_csv(applicants, opportunity)


@app.route("/recruiter/applicants/bulk-action", methods=["POST"])
def recruiter_bulk_update_applicants():
    recruiter_redirect = recruiter_or_admin_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    opportunity_id = parse_positive_int(request.form.get("opportunity_id"))
    if opportunity_id is not None:
        get_recruiter_opportunity_or_404(opportunity_id)

    current_sort = normalize_applicant_sort(request.form.get("sort", APPLICANT_SORT_RECENT))
    selected_ids = []
    for raw_application_id in request.form.getlist("application_ids"):
        application_id = parse_positive_int(raw_application_id)
        if application_id is not None and application_id not in selected_ids:
            selected_ids.append(application_id)

    status = request.form.get("status", "").strip()
    return_url = get_applicant_list_url(opportunity_id, current_sort)

    if not selected_ids:
        flash("Pilih minimal satu applicant untuk aksi massal.")
        return redirect(return_url)

    if status not in RECRUITER_APPLICATION_STATUSES:
        flash("Status applicant tidak valid.")
        return redirect(return_url)

    placeholders = ", ".join("?" for _ in selected_ids)
    owner_filter = ""
    params = [status, *selected_ids]
    current_role = get_current_role()

    if current_role == "recruiter":
        owner_filter += " AND opportunities.created_by = ?"
        params.append(session["user_id"])

    if opportunity_id is not None:
        owner_filter += " AND opportunities.id = ?"
        params.append(opportunity_id)

    try:
        cursor = get_db().execute(
            f"""
            UPDATE applications
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
              AND EXISTS (
                  SELECT 1
                  FROM opportunities
                  WHERE opportunities.id = applications.opportunity_id
                  {owner_filter}
              )
            """,
            params,
        )
        get_db().commit()
        if cursor.rowcount:
            flash(f"{cursor.rowcount} applicant berhasil diperbarui menjadi {status}.")
        else:
            flash("Tidak ada applicant yang dapat diperbarui.")
    except sqlite3.Error:
        flash("Aksi massal belum bisa diproses. Silakan coba lagi.")

    return redirect(return_url)


@app.route("/recruiter/applicants/<int:application_id>")
def recruiter_applicant_detail(application_id):
    recruiter_redirect = recruiter_or_admin_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    application = get_recruiter_application_or_404(application_id)
    documents = get_db().execute(
        """
        SELECT doc_type, is_uploaded, updated_at
        FROM documents
        WHERE user_id = ?
        ORDER BY doc_type ASC
        """,
        (application["applicant_user_id"],),
    ).fetchall()

    return render_template(
        "recruiter/applicant_detail.html",
        application=application,
        documents=documents,
        statuses=RECRUITER_APPLICATION_STATUSES,
    )


@app.route("/recruiter/applications/<int:application_id>/status", methods=["POST"])
def recruiter_update_application_status(application_id):
    recruiter_redirect = recruiter_or_admin_required()
    if recruiter_redirect is not None:
        return recruiter_redirect

    get_recruiter_application_or_404(application_id)
    status = request.form.get("status", "").strip()

    if status not in RECRUITER_APPLICATION_STATUSES:
        flash("Status applicant tidak valid.")
        return redirect(url_for("recruiter_applicant_detail", application_id=application_id))

    try:
        get_db().execute(
            """
            UPDATE applications
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, application_id),
        )
        get_db().commit()
        flash("Status applicant berhasil diperbarui.")
    except sqlite3.Error:
        flash("Status applicant belum bisa diperbarui. Silakan coba lagi.")

    return redirect(url_for("recruiter_applicant_detail", application_id=application_id))


@app.route("/admin")
def admin_dashboard():
    admin_redirect = admin_required()
    if admin_redirect is not None:
        return admin_redirect

    total_opportunities = get_db().execute(
        "SELECT COUNT(*) FROM opportunities"
    ).fetchone()[0]
    total_internship = get_db().execute(
        "SELECT COUNT(*) FROM opportunities WHERE type = ?", ("internship",)
    ).fetchone()[0]
    total_scholarship = get_db().execute(
        "SELECT COUNT(*) FROM opportunities WHERE type = ?", ("scholarship",)
    ).fetchone()[0]

    return render_template(
        "admin/dashboard.html",
        total_opportunities=total_opportunities,
        total_internship=total_internship,
        total_scholarship=total_scholarship,
    )


@app.route("/admin/opportunities")
def admin_opportunities():
    admin_redirect = admin_required()
    if admin_redirect is not None:
        return admin_redirect

    rows = get_db().execute(
        "SELECT * FROM opportunities ORDER BY deadline ASC"
    ).fetchall()
    return render_template("admin/opportunities.html", opportunities=rows)


@app.route("/admin/opportunities/create", methods=["GET", "POST"])
def admin_create_opportunity():
    admin_redirect = admin_required()
    if admin_redirect is not None:
        return admin_redirect

    opportunity = {
        "title": "",
        "type": "internship",
        "provider": "",
        "location": "",
        "deadline": "",
        "description": "",
        "requirements": "",
        "official_link": "",
        "required_skills": "",
    }

    if request.method == "POST":
        opportunity = get_opportunity_form_data()
        errors = validate_opportunity_form(opportunity)
        if errors:
            for error in errors:
                flash(error)
            return render_template(
                "admin/opportunity_form.html",
                opportunity=opportunity,
                form_title="Tambah Peluang",
                action_url=url_for("admin_create_opportunity"),
            ), 400

        try:
            get_db().execute(
                """
                INSERT INTO opportunities
                (title, provider, type, description, requirements, official_link,
                 required_skills, location, deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity["title"],
                    opportunity["provider"],
                    opportunity["type"],
                    opportunity["description"],
                    opportunity["requirements"],
                    opportunity["official_link"],
                    opportunity["required_skills"],
                    opportunity["location"],
                    opportunity["deadline"],
                ),
            )
            get_db().commit()
            flash("Peluang berhasil ditambahkan.")
            return redirect(url_for("admin_opportunities"))
        except sqlite3.Error:
            flash("Peluang belum bisa ditambahkan. Silakan coba lagi.")

    return render_template(
        "admin/opportunity_form.html",
        opportunity=opportunity,
        form_title="Tambah Peluang",
        action_url=url_for("admin_create_opportunity"),
    )


@app.route("/admin/opportunities/<int:opportunity_id>/edit", methods=["GET", "POST"])
def admin_edit_opportunity(opportunity_id):
    admin_redirect = admin_required()
    if admin_redirect is not None:
        return admin_redirect

    row = get_opportunity_or_404(opportunity_id)
    opportunity = dict(row)

    if request.method == "POST":
        opportunity = get_opportunity_form_data()
        errors = validate_opportunity_form(opportunity)
        if errors:
            for error in errors:
                flash(error)
            return render_template(
                "admin/opportunity_form.html",
                opportunity=opportunity,
                form_title="Edit Peluang",
                action_url=url_for("admin_edit_opportunity", opportunity_id=opportunity_id),
            ), 400

        try:
            get_db().execute(
                """
                UPDATE opportunities
                SET title = ?, provider = ?, type = ?, description = ?,
                    requirements = ?, official_link = ?, required_skills = ?,
                    location = ?, deadline = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    opportunity["title"],
                    opportunity["provider"],
                    opportunity["type"],
                    opportunity["description"],
                    opportunity["requirements"],
                    opportunity["official_link"],
                    opportunity["required_skills"],
                    opportunity["location"],
                    opportunity["deadline"],
                    opportunity_id,
                ),
            )
            get_db().commit()
            flash("Peluang berhasil diperbarui.")
            return redirect(url_for("admin_opportunities"))
        except sqlite3.Error:
            flash("Peluang belum bisa diperbarui. Silakan coba lagi.")

    return render_template(
        "admin/opportunity_form.html",
        opportunity=opportunity,
        form_title="Edit Peluang",
        action_url=url_for("admin_edit_opportunity", opportunity_id=opportunity_id),
    )


@app.route("/admin/opportunities/<int:opportunity_id>/delete", methods=["POST"])
def admin_delete_opportunity(opportunity_id):
    admin_redirect = admin_required()
    if admin_redirect is not None:
        return admin_redirect

    get_opportunity_or_404(opportunity_id)

    try:
        get_db().execute(
            "DELETE FROM bookmarks WHERE opportunity_id = ?", (opportunity_id,)
        )
        get_db().execute(
            "DELETE FROM applications WHERE opportunity_id = ?", (opportunity_id,)
        )
        get_db().execute(
            "DELETE FROM opportunities WHERE id = ?", (opportunity_id,)
        )
        get_db().commit()
        flash("Peluang berhasil dihapus.")
    except sqlite3.Error:
        flash("Peluang belum bisa dihapus. Silakan coba lagi.")

    return redirect(url_for("admin_opportunities"))


@app.errorhandler(DatabaseAccessError)
def database_access_error(error):
    app.logger.exception("SQLite database access failed: %s", error)
    return (
        "Database sedang tidak bisa diakses. Pastikan file database sudah dibackup, "
        "lalu cek path database dan file journal SQLite sebelum menjalankan "
        "recovery atau integrity check.",
        503,
    )


@app.errorhandler(sqlite3.Error)
def sqlite_error(error):
    app.logger.exception("SQLite operation failed: %s", error)
    return (
        "Database sedang tidak bisa diakses. Pastikan file database sudah dibackup, "
        "lalu cek path database dan file journal SQLite sebelum menjalankan "
        "recovery atau integrity check.",
        503,
    )


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(error):
    if request.path == "/chat/messages":
        return jsonify({"error": "Ukuran gambar maksimal 5 MB."}), 413
    flash("Ukuran file terlalu besar. Maksimal file adalah 5 MB.")
    if request.path.startswith("/profile"):
        return redirect(url_for("edit_profile"))
    return redirect(url_for("documents"))


def initialize_application_storage():
    try:
        init_database()
    except (DatabaseAccessError, sqlite3.Error) as exc:
        message = build_database_error_message(f"Startup database gagal: {exc}")
        print(message)
        raise RuntimeError(message) from exc


initialize_application_storage()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
