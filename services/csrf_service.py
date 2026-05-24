import hmac
import secrets

from flask import abort, jsonify, request, session
from markupsafe import Markup, escape


CSRF_FIELD_NAME = "_csrf_token"
CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER_NAMES = ("X-CSRF-Token", "X-CSRFToken")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def csrf_field():
    token = escape(get_csrf_token())
    return Markup(
        f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{token}">'
    )


def _submitted_csrf_token():
    form_token = request.form.get(CSRF_FIELD_NAME)
    if form_token:
        return form_token

    for header_name in CSRF_HEADER_NAMES:
        header_token = request.headers.get(header_name)
        if header_token:
            return header_token

    return ""


def _is_valid_csrf_token():
    expected_token = session.get(CSRF_SESSION_KEY)
    submitted_token = _submitted_csrf_token()
    return bool(
        expected_token
        and submitted_token
        and hmac.compare_digest(expected_token, submitted_token)
    )


def _wants_json_response():
    return (
        request.is_json
        or request.path.startswith("/api/")
        or request.path == "/chat/messages"
    )


def protect_csrf():
    if request.method in SAFE_METHODS:
        return None

    if _is_valid_csrf_token():
        return None

    if _wants_json_response():
        return jsonify({"error": "Token keamanan form tidak valid."}), 400

    abort(400, description="Token keamanan form tidak valid.")


def inject_csrf_helpers():
    return {
        "csrf_token": get_csrf_token,
        "csrf_field": csrf_field,
    }


def register_csrf(app):
    app.before_request(protect_csrf)
    app.context_processor(inject_csrf_helpers)
