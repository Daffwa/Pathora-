import hmac

from flask import current_app, flash, redirect, render_template, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash

from repositories import user_repository
from services.audit_service import record_audit_event
from services.auth_service import (
    get_inactive_account_message,
    is_user_account_active,
    normalize_account_status,
    normalize_role,
)
from services.constants import (
    ACCOUNT_STATUS_APPROVED,
    PUBLIC_REGISTER_ROLES,
    RECRUITER_POSITION_OPTIONS,
)
from services.database_service import is_production_environment
from services.email_service import (
    get_mail_configuration_error,
    send_password_reset_email,
)
from services.password_reset_service import (
    PASSWORD_RESET_SALT,
    _parse_token_payload,
    _password_hash_fingerprint,
    _serializer,
    generate_password_reset_token,
    get_password_reset_max_age_seconds,
    get_password_reset_secret,
    normalize_email,
)
from services.rate_limit_service import account_identifier, check_rate_limit, ip_identifier
from services.url_service import build_public_url


PASSWORD_RESET_NEUTRAL_MESSAGE = (
    "Jika email terdaftar, link reset password akan dikirim."
)
PASSWORD_RESET_INVALID_MESSAGE = (
    "Link reset password tidak valid atau sudah kedaluwarsa. Silakan minta link baru."
)
LOCAL_MAIL_CONFIGURATION_MESSAGE = (
    "Konfigurasi email lokal belum lengkap; link reset tidak dapat dikirim "
    "sampai MAIL_* diisi."
)


USER_ROW_FIELDS = (
    "id",
    "name",
    "email",
    "password_hash",
    "role",
    "account_status",
    "skills",
    "company_name",
    "company_position",
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
    "avatar_path",
    "updated_at",
    "created_at",
)


class UserRowAdapter:
    def __init__(self, user):
        self.user = user

    def __getitem__(self, key):
        if key not in USER_ROW_FIELDS:
            raise KeyError(key)
        return getattr(self.user, key)

    def keys(self):
        return USER_ROW_FIELDS


def _as_user_row(user):
    if user is None:
        return None
    return UserRowAdapter(user)


def _find_password_reset_user(email):
    if not email:
        return None

    return _as_user_row(user_repository.find_by_email(email))


def _load_password_reset_user(token):
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

    user = user_repository.find_by_id_and_email(
        payload["user_id"],
        payload["email"],
    )
    if user is None:
        return None

    expected_fingerprint = _password_hash_fingerprint(user.password_hash, secret)
    if not hmac.compare_digest(payload["password_fingerprint"], expected_fingerprint):
        return None

    return _as_user_row(user)


def _build_password_reset_url(user):
    try:
        reset_token = generate_password_reset_token(user)
    except RuntimeError:
        current_app.logger.error(
            "Password reset token configuration is unavailable."
        )
        return None

    return build_public_url(
        "reset_password",
        token=reset_token,
    )


def _forgot_password_retry_after(email):
    retry_after_values = []
    checks = (
        (
            "forgot_password:ip",
            current_app.config["FORGOT_PASSWORD_IP_RATE_LIMIT"],
            current_app.config["FORGOT_PASSWORD_IP_RATE_LIMIT_WINDOW_SECONDS"],
            ip_identifier(),
        ),
        (
            "forgot_password:account",
            current_app.config["FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT"],
            current_app.config["FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS"],
            account_identifier(email),
        ),
    )

    for scope, limit, window_seconds, identifier in checks:
        allowed, retry_after = check_rate_limit(
            scope,
            limit,
            window_seconds,
            identifier=identifier,
        )
        if not allowed:
            retry_after_values.append(retry_after)

    return max(retry_after_values) if retry_after_values else 0


def _send_password_reset_link(user, reset_url, max_age_seconds):
    try:
        send_password_reset_email(
            user["email"],
            user["name"],
            reset_url,
            max_age_seconds,
        )
    except Exception as exc:
        current_app.logger.warning(
            "Password reset email could not be sent: %s",
            exc.__class__.__name__,
        )


def _handle_mail_configuration_error(configuration_error):
    if configuration_error is None:
        return

    if is_production_environment():
        current_app.logger.error("Password reset email configuration is incomplete.")
        return

    flash(LOCAL_MAIL_CONFIGURATION_MESSAGE)


def register(app):
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            allowed, retry_after = check_rate_limit(
                "login",
                current_app.config["LOGIN_RATE_LIMIT"],
                current_app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"],
            )
            if not allowed:
                flash(
                    "Terlalu banyak percobaan login. "
                    f"Coba lagi dalam {retry_after} detik."
                )
                return render_template("login.html"), 429

            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = user_repository.find_by_email(email)
            user_row = _as_user_row(user)

            if user is None or not check_password_hash(user.password_hash, password):
                flash("Email atau password tidak sesuai. Silakan coba lagi.")
                return render_template("login.html"), 401

            current_role = normalize_role(user.role)
            if current_role is None:
                flash("Role akun tidak valid. Hubungi admin sistem.")
                return render_template("login.html"), 403

            account_status = normalize_account_status(user.account_status or ACCOUNT_STATUS_APPROVED)
            if not is_user_account_active(user_row):
                record_audit_event(
                    "auth.login_blocked",
                    target_type="user",
                    target_id=user.id,
                    metadata={"role": current_role, "account_status": account_status},
                    user_id=user.id,
                )
                flash(get_inactive_account_message(user_row))
                return render_template("login.html"), 403

            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_role"] = current_role
            session["account_status"] = account_status
            record_audit_event(
                "auth.login",
                target_type="user",
                target_id=user.id,
                metadata={"role": current_role},
                user_id=user.id,
            )
            flash(f"Selamat datang, {user.name}!")
            if current_role == "admin":
                return redirect(url_for("admin_dashboard"))
            if current_role == "recruiter":
                return redirect(url_for("recruiter_dashboard"))
            return redirect(url_for("dashboard"))

        return render_template("login.html")


    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = normalize_email(request.form.get("email"))
            retry_after = _forgot_password_retry_after(email)
            if retry_after:
                flash(PASSWORD_RESET_NEUTRAL_MESSAGE)
                response = current_app.make_response(
                    (render_template("forgot_password.html", email=email), 429)
                )
                response.headers["Retry-After"] = str(retry_after)
                return response

            mail_configuration_error = get_mail_configuration_error()
            user = _find_password_reset_user(email)
            max_age_seconds = get_password_reset_max_age_seconds()
            reset_url = _build_password_reset_url(user) if user is not None else None

            if user is not None and reset_url and mail_configuration_error is None:
                _send_password_reset_link(user, reset_url, max_age_seconds)

            _handle_mail_configuration_error(mail_configuration_error)

            flash(PASSWORD_RESET_NEUTRAL_MESSAGE)
            return render_template("forgot_password.html", email=email)

        return render_template("forgot_password.html", email="")


    @app.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        user = _load_password_reset_user(token)
        if user is None:
            flash(PASSWORD_RESET_INVALID_MESSAGE)
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if len(password) < 8:
                flash("Password baru minimal 8 karakter.")
                return render_template("reset_password.html"), 400

            if password != confirm_password:
                flash("Konfirmasi password belum sama. Silakan cek kembali.")
                return render_template("reset_password.html"), 400

            user_repository.update_user_password(
                user["id"],
                generate_password_hash(password),
            )

            session.clear()
            flash("Password berhasil diperbarui. Silakan login kembali.")
            return redirect(url_for("login"))

        return render_template("reset_password.html")


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

            if user_repository.email_exists(email):
                flash("Email sudah terdaftar. Gunakan email lain atau login.")
                return render_template("register.html", form_data=form_data), 409

            password_hash = generate_password_hash(password)
            account_status = ACCOUNT_STATUS_APPROVED
            user = user_repository.create_user(
                name=name,
                email=email,
                skills=skills,
                password_hash=password_hash,
                role=requested_role,
                account_status=account_status,
                company_name=company_name,
                company_position=company_position,
            )
            user_id = user.id
            record_audit_event(
                "account.register",
                target_type="user",
                target_id=user_id,
                metadata={"role": requested_role, "account_status": account_status},
                user_id=user_id,
            )

            session.clear()
            session["user_id"] = user_id
            session["user_name"] = name
            session["user_role"] = requested_role
            session["account_status"] = account_status
            flash(f"Selamat datang, {name}!")
            if requested_role == "recruiter":
                return redirect(url_for("recruiter_dashboard"))
            return redirect(url_for("dashboard"))

        return render_template("register.html", form_data=form_data)


    @app.get("/logout")
    def logout_get():
        return redirect(url_for("login"))


    @app.post("/logout")
    def logout():
        session.clear()
        flash("Kamu sudah logout.")
        return redirect(url_for("login"))
