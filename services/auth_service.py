import sqlite3
from functools import wraps

from flask import abort, flash, redirect, session, url_for

from services.constants import (
    ACCOUNT_STATUS_APPROVED,
    ROLE_PERMISSION_MATRIX,
    VALID_ACCOUNT_STATUSES,
    VALID_ROLES,
)
from services.database_service import DatabaseAccessError, build_database_error_message, get_db


def normalize_role(role):
    normalized_role = (role or "").strip().lower()
    if normalized_role == "student":
        return "jobseeker"
    if normalized_role in VALID_ROLES:
        return normalized_role
    return None


def normalize_account_status(status):
    normalized_status = (status or "").strip().lower()
    if normalized_status in VALID_ACCOUNT_STATUSES:
        return normalized_status
    return ACCOUNT_STATUS_APPROVED


def _row_value(row, key, default=""):
    return row[key] if key in row.keys() else default


def _sync_session_user(user):
    current_role = normalize_role(user["role"])
    if current_role is None:
        session.clear()
        return None

    account_status = normalize_account_status(
        _row_value(user, "account_status", ACCOUNT_STATUS_APPROVED)
    )
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_role"] = current_role
    session["account_status"] = account_status
    return current_role


def get_current_user():
    if "user_id" not in session:
        return None

    try:
        user = get_db().execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        if user is None:
            session.clear()
            return None
        if _sync_session_user(user) is None:
            return None
        return user
    except sqlite3.Error as exc:
        raise DatabaseAccessError(
            build_database_error_message("Data user tidak bisa dibaca dari database.")
        ) from exc


def get_current_role(refresh=True):
    if refresh and "user_id" in session:
        user = get_current_user()
        if user is None:
            return None
    return session.get("user_role")


def role_has_permission(role, permission):
    current_role = normalize_role(role)
    if current_role is None:
        return False
    return permission in ROLE_PERMISSION_MATRIX.get(current_role, set())


def user_has_any_permission(user, permissions):
    current_role = normalize_role(user["role"])
    return any(role_has_permission(current_role, permission) for permission in permissions)


def is_user_account_active(user):
    current_role = normalize_role(user["role"])
    account_status = normalize_account_status(
        _row_value(user, "account_status", ACCOUNT_STATUS_APPROVED)
    )
    return current_role != "recruiter" or account_status == ACCOUNT_STATUS_APPROVED


def get_inactive_account_message(user):
    account_status = normalize_account_status(
        _row_value(user, "account_status", ACCOUNT_STATUS_APPROVED)
    )
    if account_status == "pending":
        return "Akun recruiter kamu sedang ditahan sementara oleh admin."
    if account_status == "rejected":
        return "Akun recruiter kamu belum disetujui. Hubungi admin sistem."
    return "Akun kamu belum aktif."


def require_login(message="Silakan login terlebih dahulu.", require_active=True):
    if "user_id" not in session:
        flash(message)
        return redirect(url_for("login"))

    user = get_current_user()
    if user is None:
        flash(message)
        return redirect(url_for("login"))

    if require_active and not is_user_account_active(user):
        flash(get_inactive_account_message(user))
        abort(403)
    return None


def role_required(*roles, message="Silakan login terlebih dahulu."):
    login_redirect = require_login(message)
    if login_redirect is not None:
        return login_redirect

    allowed_roles = {normalize_role(role) for role in roles}
    current_role = get_current_role(refresh=False)

    if current_role not in allowed_roles:
        flash("Akses ditolak. Role akun kamu tidak memiliki izin untuk halaman ini.")
        abort(403)
    return None


def permissions_required(*permissions, message="Silakan login terlebih dahulu."):
    login_redirect = require_login(message)
    if login_redirect is not None:
        return login_redirect

    user = get_current_user()
    if user is None or not user_has_any_permission(user, permissions):
        flash("Akses ditolak. Akun kamu tidak memiliki izin untuk aksi ini.")
        abort(403)
    return None


def jobseeker_required():
    return permissions_required(
        "jobseeker.access",
        message="Silakan login sebagai jobseeker.",
    )


def recruiter_required():
    return permissions_required(
        "recruiter.access",
        message="Silakan login sebagai recruiter.",
    )


def recruiter_or_admin_required():
    return permissions_required(
        "recruiter.access",
        "admin.access",
        message="Silakan login sebagai recruiter atau admin.",
    )


def admin_required():
    return permissions_required("admin.access", message="Silakan login sebagai admin.")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        result = require_login()
        if result is not None:
            return result
        return f(*args, **kwargs)

    return wrapper


def _permission_decorator(*permissions):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = permissions_required(*permissions)
            if result is not None:
                return result
            return f(*args, **kwargs)

        return wrapper

    return decorator


def jobseeker_required_decorator(f):
    return _permission_decorator("jobseeker.access")(f)


def recruiter_required_decorator(f):
    return _permission_decorator("recruiter.access")(f)


def recruiter_or_admin_required_decorator(f):
    return _permission_decorator("recruiter.access", "admin.access")(f)


def admin_required_decorator(f):
    return _permission_decorator("admin.access")(f)
