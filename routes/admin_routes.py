import sqlite3

from flask import flash, redirect, render_template, url_for

from services.auth_service import admin_required
from services.database_service import get_db
from services.opportunity_service import (
    get_opportunity_form_data,
    get_opportunity_or_404,
    validate_opportunity_form,
)


def register(app):
    @app.route("/admin")
    def admin_dashboard():
        admin_redirect = admin_required()
        if admin_redirect is not None:
            return admin_redirect

        total_opportunities = get_db().execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()[0]
        total_internship = get_db().execute(
            "SELECT COUNT(*) FROM opportunities WHERE type = ?", ("internship",)
        ).fetchone()[0]
        total_scholarship = get_db().execute(
            "SELECT COUNT(*) FROM opportunities WHERE type = ?", ("scholarship",)
        ).fetchone()[0]

        return render_template(
            "admin/dashboard.html",
            total_opportunities=total_opportunities,
            total_internship=total_internship,
            total_scholarship=total_scholarship,
        )


    @app.route("/admin/opportunities")
    def admin_opportunities():
        admin_redirect = admin_required()
        if admin_redirect is not None:
            return admin_redirect

        rows = get_db().execute(
            "SELECT * FROM opportunities ORDER BY deadline ASC"
        ).fetchall()
        return render_template("admin/opportunities.html", opportunities=rows)


    @app.route("/admin/opportunities/create", methods=["GET", "POST"])
    def admin_create_opportunity():
        admin_redirect = admin_required()
        if admin_redirect is not None:
            return admin_redirect

        opportunity = {
            "title": "",
            "type": "internship",
            "provider": "",
            "location": "",
            "deadline": "",
            "description": "",
            "requirements": "",
            "official_link": "",
            "required_skills": "",
        }

        if request.method == "POST":
            opportunity = get_opportunity_form_data()
            errors = validate_opportunity_form(opportunity)
            if errors:
                for error in errors:
                    flash(error)
                return render_template(
                    "admin/opportunity_form.html",
                    opportunity=opportunity,
                    form_title="Tambah Peluang",
                    action_url=url_for("admin_create_opportunity"),
                ), 400

            try:
                get_db().execute(
                    """
                    INSERT INTO opportunities
                    (title, provider, type, description, requirements, official_link,
                     required_skills, location, deadline)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity["title"],
                        opportunity["provider"],
                        opportunity["type"],
                        opportunity["description"],
                        opportunity["requirements"],
                        opportunity["official_link"],
                        opportunity["required_skills"],
                        opportunity["location"],
                        opportunity["deadline"],
                    ),
                )
                get_db().commit()
                flash("Peluang berhasil ditambahkan.")
                return redirect(url_for("admin_opportunities"))
            except sqlite3.Error:
                flash("Peluang belum bisa ditambahkan. Silakan coba lagi.")

        return render_template(
            "admin/opportunity_form.html",
            opportunity=opportunity,
            form_title="Tambah Peluang",
            action_url=url_for("admin_create_opportunity"),
        )


    @app.route("/admin/opportunities/<int:opportunity_id>/edit", methods=["GET", "POST"])
    def admin_edit_opportunity(opportunity_id):
        admin_redirect = admin_required()
        if admin_redirect is not None:
            return admin_redirect

        row = get_opportunity_or_404(opportunity_id)
        opportunity = dict(row)

        if request.method == "POST":
            opportunity = get_opportunity_form_data()
            errors = validate_opportunity_form(opportunity)
            if errors:
                for error in errors:
                    flash(error)
                return render_template(
                    "admin/opportunity_form.html",
                    opportunity=opportunity,
                    form_title="Edit Peluang",
                    action_url=url_for("admin_edit_opportunity", opportunity_id=opportunity_id),
                ), 400

            try:
                get_db().execute(
                    """
                    UPDATE opportunities
                    SET title = ?, provider = ?, type = ?, description = ?,
                        requirements = ?, official_link = ?, required_skills = ?,
                        location = ?, deadline = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        opportunity["title"],
                        opportunity["provider"],
                        opportunity["type"],
                        opportunity["description"],
                        opportunity["requirements"],
                        opportunity["official_link"],
                        opportunity["required_skills"],
                        opportunity["location"],
                        opportunity["deadline"],
                        opportunity_id,
                    ),
                )
                get_db().commit()
                flash("Peluang berhasil diperbarui.")
                return redirect(url_for("admin_opportunities"))
            except sqlite3.Error:
                flash("Peluang belum bisa diperbarui. Silakan coba lagi.")

        return render_template(
            "admin/opportunity_form.html",
            opportunity=opportunity,
            form_title="Edit Peluang",
            action_url=url_for("admin_edit_opportunity", opportunity_id=opportunity_id),
        )


    @app.route("/admin/opportunities/<int:opportunity_id>/delete", methods=["POST"])
    def admin_delete_opportunity(opportunity_id):
        admin_redirect = admin_required()
        if admin_redirect is not None:
            return admin_redirect

        get_opportunity_or_404(opportunity_id)

        try:
            get_db().execute(
                "DELETE FROM bookmarks WHERE opportunity_id = ?", (opportunity_id,)
            )
            get_db().execute(
                "DELETE FROM applications WHERE opportunity_id = ?", (opportunity_id,)
            )
            get_db().execute(
                "DELETE FROM opportunities WHERE id = ?", (opportunity_id,)
            )
            get_db().commit()
            flash("Peluang berhasil dihapus.")
        except sqlite3.Error:
            flash("Peluang belum bisa dihapus. Silakan coba lagi.")

        return redirect(url_for("admin_opportunities"))
