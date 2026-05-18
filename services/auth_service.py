import sqlite3

from flask import abort, flash, redirect, session, url_for

from services.constants import VALID_ROLES
from services.database_service import DatabaseAccessError, build_database_error_message, get_db


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
