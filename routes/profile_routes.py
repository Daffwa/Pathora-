import sqlite3
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from services.auth_service import jobseeker_required
from services.constants import PROFILE_FORM_FIELDS
from services.database_service import get_db
from services.document_service import get_document_progress_for_user
from services.opportunity_service import is_valid_date
from services.profile_service import (
    get_current_user_profile,
    get_profile_completion,
    get_saved_profile_opportunities,
    profile_form_data_from_user,
    split_profile_list,
)
from services.storage_service import (
    delete_file_if_exists,
    is_safe_stored_filename,
    make_avatar_filename,
    save_uploaded_file,
    secure_upload_filename,
    validate_image_upload,
)


def register(app):
    @app.route("/uploads/avatars/<path:filename>")
    def profile_avatar(filename):
        if "user_id" not in session:
            abort(404)

        if not is_safe_stored_filename(filename):
            abort(404)
        safe_filename = secure_upload_filename(filename)

        return send_from_directory(app.config["AVATAR_UPLOAD_FOLDER"], safe_filename)


    @app.route("/profile")
    def profile():
        login_redirect = jobseeker_required()
        if login_redirect is not None:
            return login_redirect

        user = get_current_user_profile()
        document_progress = get_document_progress_for_user(session["user_id"])
        profile_completion = get_profile_completion(user, document_progress)

        return render_template(
            "profile.html",
            user=user,
            skills=split_profile_list(user["skills"]),
            interests=split_profile_list(user["interests"]),
            desired_positions=split_profile_list(user["desired_positions"]),
            saved_opportunities=get_saved_profile_opportunities(session["user_id"]),
            document_progress=document_progress,
            profile_completion=profile_completion,
        )


    @app.route("/profile/edit", methods=["GET", "POST"])
    def edit_profile():
        login_redirect = jobseeker_required()
        if login_redirect is not None:
            return login_redirect

        user = get_current_user_profile()
        if user is None:
            abort(404)

        document_progress = get_document_progress_for_user(session["user_id"])

        if request.method == "POST":
            form_data = {
                field: request.form.get(field, "").strip()
                for field in PROFILE_FORM_FIELDS
            }
            old_password = request.form.get("old_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            validation_errors = []

            if not form_data["name"]:
                validation_errors.append("Nama lengkap wajib diisi.")
            if not form_data["email"]:
                validation_errors.append("Email wajib diisi.")

            if form_data["email"]:
                existing_user = get_db().execute(
                    """
                    SELECT id FROM users
                    WHERE email = ? AND id != ?
                    """,
                    (form_data["email"].lower(), session["user_id"]),
                ).fetchone()
                if existing_user is not None:
                    validation_errors.append("Email sudah digunakan akun lain.")
                form_data["email"] = form_data["email"].lower()

            if form_data["birth_date"] and not is_valid_date(form_data["birth_date"]):
                validation_errors.append("Tanggal lahir harus memakai format YYYY-MM-DD.")

            if form_data["gpa"]:
                try:
                    gpa_value = float(form_data["gpa"])
                except ValueError:
                    validation_errors.append("IPK harus berupa angka antara 0.00 sampai 4.00.")
                else:
                    if gpa_value < 0 or gpa_value > 4:
                        validation_errors.append("IPK harus berada di antara 0.00 sampai 4.00.")
                    else:
                        form_data["gpa"] = f"{gpa_value:.2f}".rstrip("0").rstrip(".")

            if form_data["semester"]:
                try:
                    semester_value = int(form_data["semester"])
                except ValueError:
                    validation_errors.append("Semester harus berupa angka.")
                else:
                    if semester_value < 1 or semester_value > 14:
                        validation_errors.append("Semester harus berada di rentang 1 sampai 14.")

            if form_data["entry_year"]:
                current_year = datetime.now().year
                try:
                    entry_year_value = int(form_data["entry_year"])
                except ValueError:
                    validation_errors.append("Tahun masuk harus berupa angka.")
                else:
                    if entry_year_value < 1900 or entry_year_value > current_year + 1:
                        validation_errors.append("Tahun masuk tidak valid.")

            wants_password_change = any([old_password, new_password, confirm_password])
            password_hash = user["password_hash"]
            if wants_password_change:
                if not old_password:
                    validation_errors.append("Kata sandi lama wajib diisi untuk mengganti password.")
                if not new_password:
                    validation_errors.append("Kata sandi baru wajib diisi.")
                if new_password and len(new_password) < 8:
                    validation_errors.append("Kata sandi baru minimal 8 karakter.")
                if new_password != confirm_password:
                    validation_errors.append("Konfirmasi kata sandi baru belum sama.")
                if old_password and not check_password_hash(user["password_hash"], old_password):
                    validation_errors.append("Kata sandi lama tidak sesuai.")
                if not validation_errors:
                    password_hash = generate_password_hash(new_password)

            uploaded_avatar = request.files.get("avatar_file")
            if uploaded_avatar and uploaded_avatar.filename:
                if not validate_image_upload(uploaded_avatar):
                    validation_errors.append("Foto profil harus berupa JPG, JPEG, atau PNG.")

            if validation_errors:
                for error in validation_errors:
                    flash(error)
                return (
                    render_template(
                        "profile_edit.html",
                        user=user,
                        form_data=form_data,
                        document_progress=document_progress,
                        profile_completion=get_profile_completion(form_data, document_progress),
                    ),
                    400,
                )

            avatar_path = user["avatar_path"] or ""
            if request.form.get("remove_avatar") == "1":
                delete_file_if_exists(app.config["AVATAR_UPLOAD_FOLDER"], avatar_path)
                avatar_path = ""

            if uploaded_avatar and uploaded_avatar.filename:
                avatar_filename = make_avatar_filename(session["user_id"], uploaded_avatar.filename)
                if avatar_path and avatar_path != avatar_filename:
                    delete_file_if_exists(app.config["AVATAR_UPLOAD_FOLDER"], avatar_path)
                save_uploaded_file(
                    uploaded_avatar,
                    app.config["AVATAR_UPLOAD_FOLDER"],
                    avatar_filename,
                )
                avatar_path = avatar_filename

            update_fields = PROFILE_FORM_FIELDS + ["avatar_path", "password_hash"]
            set_clause = ", ".join(f"{field} = ?" for field in update_fields)
            update_values = [form_data[field] for field in PROFILE_FORM_FIELDS]
            update_values.extend([avatar_path, password_hash, session["user_id"]])

            try:
                get_db().execute(
                    f"""
                    UPDATE users
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    update_values,
                )
                get_db().commit()
            except sqlite3.Error:
                flash("Profil belum bisa disimpan. Silakan coba lagi.")
                return redirect(url_for("edit_profile"))

            session["user_name"] = form_data["name"]
            flash("Profil berhasil diperbarui.")
            return redirect(url_for("profile"))

        form_data = profile_form_data_from_user(user)
        return render_template(
            "profile_edit.html",
            user=user,
            form_data=form_data,
            document_progress=document_progress,
            profile_completion=get_profile_completion(user, document_progress),
        )
