import os
import secrets
from pathlib import Path


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

    is_production = any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
        )
    ) or os.getenv("FLASK_ENV") == "production"

    if is_production:
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
