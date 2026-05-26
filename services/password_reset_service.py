import hashlib
import hmac
import os

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from services.database_service import is_production_environment


PASSWORD_RESET_SALT = "pathora-password-reset"
DEFAULT_PASSWORD_RESET_MAX_AGE_SECONDS = 3600


def normalize_email(email):
    return (email or "").strip().lower()


def get_password_reset_secret():
    secret = os.getenv("PASSWORD_RESET_SECRET")
    if secret:
        return secret

    if is_production_environment():
        raise RuntimeError("PASSWORD_RESET_SECRET environment variable is required.")

    return current_app.config["SECRET_KEY"]


def get_password_reset_max_age_seconds():
    try:
        return int(
            os.getenv(
                "PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS",
                str(DEFAULT_PASSWORD_RESET_MAX_AGE_SECONDS),
            )
        )
    except (TypeError, ValueError):
        return DEFAULT_PASSWORD_RESET_MAX_AGE_SECONDS


def generate_password_reset_token(user):
    secret = get_password_reset_secret()
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "pwd": _password_hash_fingerprint(user["password_hash"], secret),
    }
    return _serializer(secret).dumps(payload, salt=PASSWORD_RESET_SALT)


def load_password_reset_user(db, token):
    try:
        secret = get_password_reset_secret()
        data = _serializer(secret).loads(
            token,
            salt=PASSWORD_RESET_SALT,
            max_age=get_password_reset_max_age_seconds(),
        )
    except SignatureExpired:
        return None
    except (BadSignature, RuntimeError, TypeError, ValueError):
        return None

    payload = _parse_token_payload(data)
    if payload is None:
        return None

    user = db.execute(
        "SELECT id, name, email, password_hash FROM users WHERE id = ? AND email = ?",
        (payload["user_id"], payload["email"]),
    ).fetchone()
    if user is None:
        return None

    expected_fingerprint = _password_hash_fingerprint(user["password_hash"], secret)
    if not hmac.compare_digest(payload["password_fingerprint"], expected_fingerprint):
        return None

    return user


def _serializer(secret):
    return URLSafeTimedSerializer(secret_key=secret)


def _password_hash_fingerprint(password_hash, secret):
    signing_secret = str(secret).encode("utf-8")
    return hmac.new(
        signing_secret,
        str(password_hash).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _parse_token_payload(data):
    if not isinstance(data, dict):
        return None

    user_id = data.get("user_id")
    email = normalize_email(data.get("email"))
    password_fingerprint = data.get("pwd")

    if not user_id or not email or not password_fingerprint:
        return None

    return {
        "user_id": user_id,
        "email": email,
        "password_fingerprint": str(password_fingerprint),
    }
