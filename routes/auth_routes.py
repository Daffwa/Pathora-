from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from services.auth_service import normalize_role
from services.constants import PUBLIC_REGISTER_ROLES, RECRUITER_POSITION_OPTIONS
from services.database_service import get_db


def register(app):
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = get_db().execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Email atau password tidak sesuai. Silakan coba lagi.")
                return render_template("login.html"), 401

            current_role = normalize_role(user["role"])
            if current_role is None:
                flash("Role akun tidak valid. Hubungi admin sistem.")
                return render_template("login.html"), 403

            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = current_role
            flash(f"Selamat datang, {user['name']}!")
            if current_role == "admin":
                return redirect(url_for("admin_dashboard"))
            if current_role == "recruiter":
                return redirect(url_for("recruiter_dashboard"))
            return redirect(url_for("dashboard"))

        return render_template("login.html")


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

            existing_user = get_db().execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()

            if existing_user is not None:
                flash("Email sudah terdaftar. Gunakan email lain atau login.")
                return render_template("register.html", form_data=form_data), 409

            password_hash = generate_password_hash(password)
            cursor = get_db().execute(
                """
                INSERT INTO users
                (name, email, skills, password_hash, role, company_name, company_position)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    skills,
                    password_hash,
                    requested_role,
                    company_name,
                    company_position,
                ),
            )
            get_db().commit()

            session.clear()
            session["user_id"] = cursor.lastrowid
            session["user_name"] = name
            session["user_role"] = requested_role
            flash(f"Selamat datang, {name}!")
            if requested_role == "recruiter":
                return redirect(url_for("recruiter_dashboard"))
            return redirect(url_for("dashboard"))

        return render_template("register.html", form_data=form_data)


    @app.route("/logout")
    def logout():
        session.clear()
        flash("Kamu sudah logout.")
        return redirect(url_for("login"))
