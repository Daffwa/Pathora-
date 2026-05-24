import os
import secrets
from pathlib import Path


def get_int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_production_environment():
    return any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
        )
    ) or os.getenv("FLASK_ENV") == "production"


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR_ENV = os.getenv("DATA_DIR")
DATA_DIR = Path(DATA_DIR_ENV).expanduser() if DATA_DIR_ENV else BASE_DIR
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR
DATA_DIR = DATA_DIR.resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_secret_key():
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        return secret_key

    if is_production_environment():
        raise RuntimeError("SECRET_KEY environment variable is required in production.")

    return secrets.token_urlsafe(48)


class Config:
    DATA_DIR = DATA_DIR
    SECRET_KEY = get_secret_key()
    DATABASE = (
        (DATA_DIR / "app.db")
        if DATA_DIR_ENV
        else (BASE_DIR / "database" / "app.db")
    )
    SCHEMA = BASE_DIR / "database" / "schema.sql"
    UPLOAD_FOLDER = DATA_DIR / "uploads" / "documents"
    AVATAR_UPLOAD_FOLDER = DATA_DIR / "uploads" / "avatars"
    CHAT_UPLOAD_FOLDER = DATA_DIR / "uploads" / "chat"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    LOGIN_RATE_LIMIT = get_int_env("LOGIN_RATE_LIMIT", 8)
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = get_int_env("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300)
    AI_RATE_LIMIT = get_int_env("AI_RATE_LIMIT", 12)
    AI_RATE_LIMIT_WINDOW_SECONDS = get_int_env("AI_RATE_LIMIT_WINDOW_SECONDS", 60)
    CHAT_RATE_LIMIT = get_int_env("CHAT_RATE_LIMIT", 30)
    CHAT_RATE_LIMIT_WINDOW_SECONDS = get_int_env("CHAT_RATE_LIMIT_WINDOW_SECONDS", 60)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = is_production_environment()
    USE_BUILT_ASSETS = get_bool_env(
        "USE_BUILT_ASSETS",
        default=is_production_environment(),
    )
    ASSET_MANIFEST_PATH = BASE_DIR / "static" / "dist" / "asset-manifest.json"
