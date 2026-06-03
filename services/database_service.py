import os
from pathlib import Path

from flask import current_app
from flask_migrate import upgrade
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from config import is_production_environment
from extensions import db
from models import OpportunityORM, UserORM


DEFAULT_ADMIN_PASSWORD = "admin12345"


class DatabaseAccessError(RuntimeError):
    pass


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
        "MIGRATIONS_DIR",
        "UPLOAD_FOLDER",
        "AVATAR_UPLOAD_FOLDER",
        "CHAT_UPLOAD_FOLDER",
    ):
        app.config[config_key] = str(resolve_app_path(app.config[config_key], app_root))


def describe_database_target():
    database_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    try:
        return make_url(database_uri).render_as_string(hide_password=True)
    except Exception:
        return database_uri or "SQLALCHEMY_DATABASE_URI belum dikonfigurasi"


def build_database_error_message(message):
    details = [message, f"Target database: {describe_database_target()}"]
    if os.getenv("DATABASE_URL"):
        details.append("Database dikonfigurasi melalui DATABASE_URL.")
    else:
        details.append(f"Path SQLite lokal: {current_app.config['DATABASE']}")
    return " ".join(details)


def check_database_health():
    db.session.execute(text("SELECT 1")).scalar()


def close_db(error=None):
    db.session.remove()


def _create_storage_dirs():
    for key in ("UPLOAD_FOLDER", "AVATAR_UPLOAD_FOLDER", "CHAT_UPLOAD_FOLDER"):
        Path(current_app.config[key]).mkdir(parents=True, exist_ok=True)

    database_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if database_uri.startswith("sqlite:"):
        Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)


def _run_migrations():
    upgrade(directory=current_app.config["MIGRATIONS_DIR"])


def _seed_admin():
    email, password = get_admin_seed_credentials()
    admin = db.session.execute(
        select(UserORM).where(UserORM.email == email)
    ).scalar_one_or_none()

    if admin is None:
        db.session.add(
            UserORM(
                name="Admin",
                email=email,
                password_hash=generate_password_hash(password),
                role="admin",
                account_status="approved",
                skills="",
            )
        )
        return

    admin.role = "admin"
    admin.account_status = "approved"


def _seed_sample_opportunities():
    count = db.session.execute(select(func.count(OpportunityORM.id))).scalar_one()
    if count > 0:
        return

    db.session.add_all(
        [
            OpportunityORM(
                title="Data Analyst Internship",
                provider="Nusantara Tech",
                type="internship",
                description=(
                    "Program magang untuk mahasiswa yang ingin belajar "
                    "analisis data bisnis."
                ),
                requirements=(
                    "Mahasiswa aktif, memahami dasar statistik, dan mampu "
                    "bekerja dalam tim."
                ),
                required_skills="python,sql,excel",
                location="Jakarta / Hybrid",
                deadline="2026-06-15",
            ),
            OpportunityORM(
                title="Beasiswa Data Science Muda",
                provider="Yayasan Sains Indonesia",
                type="scholarship",
                description=(
                    "Beasiswa untuk mahasiswa yang tertarik pada proyek "
                    "data science terapan."
                ),
                requirements="IPK minimal 3.00, esai motivasi, dan transkrip nilai.",
                required_skills="python,statistics,communication",
                location="Indonesia",
                deadline="2026-07-01",
            ),
            OpportunityORM(
                title="Business Intelligence Intern",
                provider="Bright Retail Group",
                type="internship",
                description=(
                    "Kesempatan magang membuat dashboard dan laporan "
                    "performa penjualan."
                ),
                requirements=(
                    "Terbiasa dengan spreadsheet dan visualisasi data sederhana."
                ),
                required_skills="excel,sql,tableau",
                location="Bandung",
                deadline="2026-05-30",
            ),
        ]
    )


def init_database():
    _create_storage_dirs()
    try:
        _run_migrations()
        check_database_health()
        _seed_admin()
        _seed_sample_opportunities()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise DatabaseAccessError(
            build_database_error_message(f"Startup database gagal: {exc}")
        ) from exc


def register_database_teardown(app):
    app.teardown_appcontext(close_db)


def initialize_application_storage(app):
    with app.app_context():
        try:
            init_database()
        except DatabaseAccessError as exc:
            print(exc)
            raise RuntimeError(str(exc)) from exc
