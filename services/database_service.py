import os
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

from services.constants import SQLITE_TIMEOUT_SECONDS, USER_PROFILE_COLUMN_DEFINITIONS


DEFAULT_ADMIN_PASSWORD = "admin12345"


class DatabaseAccessError(RuntimeError):
    pass


def is_production_environment():
    return any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
        )
    ) or os.getenv("FLASK_ENV") == "production"


def get_admin_seed_credentials():
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD")

    if not password:
        if is_production_environment():
            raise RuntimeError(
                "ADMIN_PASSWORD environment variable is required in production."
            )
        password = DEFAULT_ADMIN_PASSWORD

    return email, password


def resolve_app_path(path_value, app_root):
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = app_root / path
    return path.resolve()


def configure_database_paths(app, app_root):
    for config_key in (
        "DATABASE",
        "SCHEMA",
        "UPLOAD_FOLDER",
        "AVATAR_UPLOAD_FOLDER",
        "CHAT_UPLOAD_FOLDER",
    ):
        app.config[config_key] = str(resolve_app_path(app.config[config_key], app_root))


def get_database_path():
    return Path(current_app.config["DATABASE"])


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
        current_app.logger.info("Database tidak ditemukan. SQLite akan membuat file baru: %s", database_path)

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


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except sqlite3.Error:
            pass


# ── Database initialisation (split into focused steps) ──────────

def _create_storage_dirs():
    for key in ("UPLOAD_FOLDER", "AVATAR_UPLOAD_FOLDER", "CHAT_UPLOAD_FOLDER"):
        Path(current_app.config[key]).mkdir(parents=True, exist_ok=True)
    Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)


def _run_schema(db):
    with open(current_app.config["SCHEMA"], "r", encoding="utf-8") as schema:
        db.executescript(schema.read())


def _migrate_documents(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(documents)").fetchall()}
    if "file_path" not in columns:
        db.execute("ALTER TABLE documents ADD COLUMN file_path TEXT DEFAULT ''")


def _migrate_chat_messages(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(chat_messages)").fetchall()}
    for col, definition in {
        "attachment_path": "TEXT DEFAULT ''",
        "attachment_type": "TEXT DEFAULT ''",
        "attachment_name": "TEXT DEFAULT ''",
    }.items():
        if col not in columns:
            db.execute(f"ALTER TABLE chat_messages ADD COLUMN {col} {definition}")


def _migrate_users(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
    if "role" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'jobseeker'")
    if "account_status" not in columns:
        db.execute(
            """
            ALTER TABLE users
            ADD COLUMN account_status TEXT NOT NULL DEFAULT 'approved'
                CHECK (account_status IN ('pending', 'approved', 'rejected'))
            """
        )
    if "company_name" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN company_name TEXT DEFAULT ''")
    if "company_position" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN company_position TEXT DEFAULT ''")
    for col, definition in USER_PROFILE_COLUMN_DEFINITIONS.items():
        if col not in columns:
            db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")

    db.execute(
        """
        UPDATE users
        SET role = 'jobseeker'
        WHERE role = 'student' OR role IS NULL OR role = ''
           OR role NOT IN ('jobseeker', 'recruiter', 'admin')
        """
    )
    db.execute(
        """
        UPDATE users
        SET account_status = 'approved'
        WHERE account_status IS NULL OR account_status = ''
           OR account_status NOT IN ('pending', 'approved', 'rejected')
        """
    )

    info = {row[1]: row for row in db.execute("PRAGMA table_info(users)").fetchall()}
    if info["role"][4] not in {"'jobseeker'", '"jobseeker"', "jobseeker"}:
        _rebuild_users_table(db)


def _rebuild_users_table(db):
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("DROP TABLE IF EXISTS users_new")
    db.execute(
        """
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'jobseeker'
                CHECK (role IN ('jobseeker', 'recruiter', 'admin')),
            account_status TEXT NOT NULL DEFAULT 'approved'
                CHECK (account_status IN ('pending', 'approved', 'rejected')),
            skills TEXT DEFAULT '', company_name TEXT DEFAULT '',
            company_position TEXT DEFAULT '', nickname TEXT DEFAULT '',
            phone TEXT DEFAULT '', birth_date TEXT DEFAULT '',
            gender TEXT DEFAULT '', domicile TEXT DEFAULT '', bio TEXT DEFAULT '',
            university TEXT DEFAULT '', faculty TEXT DEFAULT '', major TEXT DEFAULT '',
            degree TEXT DEFAULT '', semester TEXT DEFAULT '', gpa TEXT DEFAULT '',
            entry_year TEXT DEFAULT '', desired_positions TEXT DEFAULT '',
            preferred_program TEXT DEFAULT '', preferred_locations TEXT DEFAULT '',
            work_arrangement TEXT DEFAULT '', interests TEXT DEFAULT '',
            linkedin TEXT DEFAULT '', github TEXT DEFAULT '',
            portfolio_url TEXT DEFAULT '', avatar_path TEXT DEFAULT '',
            updated_at TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        INSERT INTO users_new
        (id, name, email, password_hash, role, account_status, skills,
         company_name, company_position, nickname, phone, birth_date,
         gender, domicile, bio, university, faculty, major, degree,
         semester, gpa, entry_year, desired_positions, preferred_program,
         preferred_locations, work_arrangement, interests, linkedin,
         github, portfolio_url, avatar_path, updated_at, created_at)
        SELECT id, name, email, password_hash,
               CASE WHEN role IN ('jobseeker','recruiter','admin') THEN role ELSE 'jobseeker' END,
               CASE WHEN account_status IN ('pending','approved','rejected')
                    THEN account_status ELSE 'approved' END,
               COALESCE(skills,''), COALESCE(company_name,''), COALESCE(company_position,''),
               COALESCE(nickname,''), COALESCE(phone,''), COALESCE(birth_date,''),
               COALESCE(gender,''), COALESCE(domicile,''), COALESCE(bio,''),
               COALESCE(university,''), COALESCE(faculty,''), COALESCE(major,''),
               COALESCE(degree,''), COALESCE(semester,''), COALESCE(gpa,''),
               COALESCE(entry_year,''), COALESCE(desired_positions,''),
               COALESCE(preferred_program,''), COALESCE(preferred_locations,''),
               COALESCE(work_arrangement,''), COALESCE(interests,''),
               COALESCE(linkedin,''), COALESCE(github,''),
               COALESCE(portfolio_url,''), COALESCE(avatar_path,''),
               COALESCE(updated_at,''), created_at
        FROM users
        """
    )
    db.execute("DROP TABLE users")
    db.execute("ALTER TABLE users_new RENAME TO users")
    db.execute("PRAGMA foreign_keys = ON")


def _migrate_opportunities(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(opportunities)").fetchall()}
    if "official_link" not in columns:
        db.execute("ALTER TABLE opportunities ADD COLUMN official_link TEXT DEFAULT ''")
    if "created_by" not in columns:
        db.execute("ALTER TABLE opportunities ADD COLUMN created_by INTEGER")
    if "company_name" not in columns:
        db.execute("ALTER TABLE opportunities ADD COLUMN company_name TEXT DEFAULT ''")


def _seed_admin(db):
    email, password = get_admin_seed_credentials()
    admin = db.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if admin is None:
        db.execute(
            """
            INSERT INTO users
                (name, email, password_hash, role, account_status, skills)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Admin", email, generate_password_hash(password), "admin", "approved", ""),
        )
    else:
        db.execute(
            "UPDATE users SET role = ?, account_status = ? WHERE email = ?",
            ("admin", "approved", email),
        )


def _seed_sample_opportunities(db):
    count = db.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    if count > 0:
        return
    db.executemany(
        """
        INSERT INTO opportunities
        (title, provider, type, description, requirements, required_skills, location, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("Data Analyst Internship", "Nusantara Tech", "internship",
             "Program magang untuk mahasiswa yang ingin belajar analisis data bisnis.",
             "Mahasiswa aktif, memahami dasar statistik, dan mampu bekerja dalam tim.",
             "python,sql,excel", "Jakarta / Hybrid", "2026-06-15"),
            ("Beasiswa Data Science Muda", "Yayasan Sains Indonesia", "scholarship",
             "Beasiswa untuk mahasiswa yang tertarik pada proyek data science terapan.",
             "IPK minimal 3.00, esai motivasi, dan transkrip nilai.",
             "python,statistics,communication", "Indonesia", "2026-07-01"),
            ("Business Intelligence Intern", "Bright Retail Group", "internship",
             "Kesempatan magang membuat dashboard dan laporan performa penjualan.",
             "Terbiasa dengan spreadsheet dan visualisasi data sederhana.",
             "excel,sql,tableau", "Bandung", "2026-05-30"),
        ],
    )


def init_database():
    _create_storage_dirs()

    with closing(open_database_connection()) as db:
        _run_schema(db)
        _migrate_documents(db)
        _migrate_chat_messages(db)
        _migrate_users(db)
        _migrate_opportunities(db)
        _seed_admin(db)
        _seed_sample_opportunities(db)
        db.commit()


def register_database_teardown(app):
    app.teardown_appcontext(close_db)


def initialize_application_storage(app):
    with app.app_context():
        try:
            init_database()
        except (DatabaseAccessError, sqlite3.Error) as exc:
            message = build_database_error_message(f"Startup database gagal: {exc}")
            print(message)
            raise RuntimeError(message) from exc
