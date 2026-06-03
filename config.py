import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.pool import NullPool


LOCAL_APP_ENVIRONMENTS = {"local", "development", "dev", "test", "testing"}
PRODUCTION_REQUIRED_ENV_VARS = (
    "SECRET_KEY",
    "PASSWORD_RESET_SECRET",
    "ADMIN_PASSWORD",
    "DATABASE_URL",
)
PUBLIC_BASE_URL_ENV_VARS = ("PUBLIC_BASE_URL", "RAILWAY_PUBLIC_DOMAIN")
LOCAL_TRUSTED_HOSTS = ("localhost", "127.0.0.1", "::1")


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


def get_app_environment():
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    if app_env:
        return app_env
    if get_bool_env("PRODUCTION"):
        return "production"
    if os.getenv("FLASK_ENV") == "production":
        return "production"
    if any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
        )
    ):
        return "production"
    return "production"


def is_production_environment():
    return get_app_environment() not in LOCAL_APP_ENVIRONMENTS


def validate_required_production_environment():
    if not is_production_environment():
        return

    missing = [name for name in PRODUCTION_REQUIRED_ENV_VARS if not os.getenv(name)]
    if not get_public_base_url_candidate():
        missing.append("PUBLIC_BASE_URL or RAILWAY_PUBLIC_DOMAIN")
    if missing:
        raise RuntimeError(
            "Missing required production environment variables: "
            + ", ".join(missing)
            + ". Set APP_ENV=development or APP_ENV=test only for local/test runs."
        )


def normalize_database_url(database_url):
    if not database_url:
        return database_url
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def build_database_uri(database_path):
    database_url = normalize_database_url(os.getenv("DATABASE_URL"))
    if database_url:
        return database_url
    if is_production_environment():
        raise RuntimeError("DATABASE_URL environment variable is required.")
    return f"sqlite:///{database_path.as_posix()}"


def build_engine_options(database_uri):
    if database_uri.startswith("sqlite:"):
        return {"poolclass": NullPool}
    return {}


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


def get_public_base_url():
    public_base_url = get_public_base_url_candidate()
    if not public_base_url:
        return ""

    parsed = urlparse(public_base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("PUBLIC_BASE_URL must be an absolute http(s) URL.")
    if parsed.username or parsed.password:
        raise RuntimeError("PUBLIC_BASE_URL must not contain credentials.")
    return public_base_url.rstrip("/")


def get_public_base_url_candidate():
    public_base_url = (os.getenv("PUBLIC_BASE_URL") or "").strip()
    if public_base_url:
        return public_base_url

    railway_public_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway_public_domain:
        if "://" not in railway_public_domain:
            return f"https://{railway_public_domain}"
        return railway_public_domain

    return ""


def _hostname_from_url(url):
    if not url:
        return ""
    return (urlparse(url).hostname or "").strip().lower()


def _split_env_list(name):
    return [
        item.strip()
        for item in (os.getenv(name) or "").split(",")
        if item.strip()
    ]


def build_trusted_hosts(public_base_url):
    hosts = _split_env_list("TRUSTED_HOSTS")
    public_hostname = _hostname_from_url(public_base_url)
    if public_hostname:
        hosts.append(public_hostname)

    server_name = (os.getenv("SERVER_NAME") or "").strip()
    if server_name:
        hosts.append(server_name)

    if not is_production_environment():
        hosts.extend(LOCAL_TRUSTED_HOSTS)

    deduped = []
    for host in hosts:
        normalized = host.strip().lower()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return tuple(deduped)


def get_rate_limit_backend():
    configured_backend = (os.getenv("RATE_LIMIT_BACKEND") or "").strip().lower()
    if configured_backend:
        return configured_backend
    return "database" if is_production_environment() else "memory"


PUBLIC_BASE_URL = get_public_base_url()


class Config:
    APP_ENV = get_app_environment()
    IS_PRODUCTION = is_production_environment()
    DATA_DIR = DATA_DIR
    SECRET_KEY = get_secret_key()
    DATABASE = (
        (DATA_DIR / "app.db")
        if DATA_DIR_ENV
        else (BASE_DIR / "database" / "app.db")
    )
    SQLALCHEMY_DATABASE_URI = build_database_uri(DATABASE)
    SQLALCHEMY_ENGINE_OPTIONS = build_engine_options(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MIGRATIONS_DIR = BASE_DIR / "migrations"
    UPLOAD_FOLDER = DATA_DIR / "uploads" / "documents"
    AVATAR_UPLOAD_FOLDER = DATA_DIR / "uploads" / "avatars"
    CHAT_UPLOAD_FOLDER = DATA_DIR / "uploads" / "chat"
    PUBLIC_BASE_URL = PUBLIC_BASE_URL
    SERVER_NAME = (os.getenv("SERVER_NAME") or "").strip() or None
    TRUSTED_HOSTS = build_trusted_hosts(PUBLIC_BASE_URL)
    TRUSTED_PROXY_IPS = tuple(_split_env_list("TRUSTED_PROXY_IPS"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    LOGIN_RATE_LIMIT = get_int_env("LOGIN_RATE_LIMIT", 8)
    LOGIN_RATE_LIMIT_WINDOW_SECONDS = get_int_env("LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300)
    FORGOT_PASSWORD_IP_RATE_LIMIT = get_int_env("FORGOT_PASSWORD_IP_RATE_LIMIT", 5)
    FORGOT_PASSWORD_IP_RATE_LIMIT_WINDOW_SECONDS = get_int_env(
        "FORGOT_PASSWORD_IP_RATE_LIMIT_WINDOW_SECONDS",
        900,
    )
    FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT = get_int_env("FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT", 3)
    FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS = get_int_env(
        "FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS",
        3600,
    )
    AI_RATE_LIMIT = get_int_env("AI_RATE_LIMIT", 12)
    AI_RATE_LIMIT_WINDOW_SECONDS = get_int_env("AI_RATE_LIMIT_WINDOW_SECONDS", 60)
    CHAT_RATE_LIMIT = get_int_env("CHAT_RATE_LIMIT", 30)
    CHAT_RATE_LIMIT_WINDOW_SECONDS = get_int_env("CHAT_RATE_LIMIT_WINDOW_SECONDS", 60)
    RATE_LIMIT_BACKEND = get_rate_limit_backend()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = is_production_environment()
    USE_BUILT_ASSETS = get_bool_env(
        "USE_BUILT_ASSETS",
        default=is_production_environment(),
    )
    ASSET_MANIFEST_PATH = BASE_DIR / "static" / "dist" / "asset-manifest.json"


validate_required_production_environment()
