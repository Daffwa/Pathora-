import sqlite3

from flask import abort, flash, redirect, render_template, request, url_for

from services.audit_service import record_audit_event
from services.auth_service import admin_required_decorator
from services.constants import ACCOUNT_STATUS_LABELS, VALID_ACCOUNT_STATUSES
from services.database_service import get_db
from services.opportunity_service import (
    EMPTY_OPPORTUNITY_FORM,
    create_opportunity,
    delete_opportunity_with_cascade,
    get_opportunity_form_data,
    get_opportunity_or_404,
    list_role_opportunities,
    update_opportunity,
    validate_opportunity_form,
)


def _handle_form(submit_label, form_title, action_url, opportunity=None):
    if request.method == "POST":
        opportunity = get_opportunity_form_data()
        errors = validate_opportunity_form(opportunity)
        if errors:
            for error in errors:
                flash(error)
            return render_template(
                "admin/opportunity_form.html",
                opportunity=opportunity,
                form_title=form_title,
                action_url=action_url,
            ), 400

        try:
            opportunity_id = create_opportunity(opportunity)
            record_audit_event(
                "opportunity.create",
                target_type="opportunity",
                target_id=opportunity_id,
                metadata={"scope": "admin"},
            )
            flash(f"Peluang berhasil {submit_label}.")
        except sqlite3.Error:
            flash(f"Peluang belum bisa di-{submit_label}. Silakan coba lagi.")
        else:
            return redirect(url_for("admin_opportunities"))

    return render_template(
        "admin/opportunity_form.html",
        opportunity=opportunity or EMPTY_OPPORTUNITY_FORM,
        form_title=form_title,
        action_url=action_url,
    )


def register(app):
    @app.route("/admin")
    @admin_required_decorator
    def admin_dashboard():
        total_opportunities = get_db().execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()[0]
        total_internship = get_db().execute(
            "SELECT COUNT(*) FROM opportunities WHERE type = ?", ("internship",)
        ).fetchone()[0]
        total_scholarship = get_db().execute(
            "SELECT COUNT(*) FROM opportunities WHERE type = ?", ("scholarship",)
        ).fetchone()[0]
        total_recruiters = get_db().execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE role = ?
            """,
            ("recruiter",),
        ).fetchone()[0]

        return render_template(
            "admin/dashboard.html",
            total_opportunities=total_opportunities,
            total_internship=total_internship,
            total_scholarship=total_scholarship,
            total_recruiters=total_recruiters,
        )


    @app.route("/admin/recruiters")
    @admin_required_decorator
    def admin_recruiters():
        recruiters = get_db().execute(
            """
            SELECT id, name, email, company_name, company_position,
                   account_status, created_at
            FROM users
            WHERE role = ?
            ORDER BY
                CASE account_status
                    WHEN 'pending' THEN 0
                    WHEN 'approved' THEN 1
                    ELSE 2
                END,
                created_at DESC
            """,
            ("recruiter",),
        ).fetchall()
        return render_template(
            "admin/recruiters.html",
            recruiters=recruiters,
            account_status_labels=ACCOUNT_STATUS_LABELS,
        )


    @app.route("/admin/recruiters/<int:user_id>/status", methods=["POST"])
    @admin_required_decorator
    def admin_update_recruiter_status(user_id):
        account_status = request.form.get("account_status", "").strip().lower()
        if account_status not in VALID_ACCOUNT_STATUSES:
            flash("Status akun recruiter tidak valid.")
            return redirect(url_for("admin_recruiters"))

        recruiter = get_db().execute(
            """
            SELECT id, account_status
            FROM users
            WHERE id = ? AND role = ?
            """,
            (user_id, "recruiter"),
        ).fetchone()
        if recruiter is None:
            abort(404)

        try:
            get_db().execute(
                """
                UPDATE users
                SET account_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND role = ?
                """,
                (account_status, user_id, "recruiter"),
            )
            get_db().commit()
            record_audit_event(
                "recruiter_account.status_update",
                target_type="user",
                target_id=user_id,
                metadata={
                    "old_status": recruiter["account_status"],
                    "new_status": account_status,
                },
            )
            flash("Status akun recruiter berhasil diperbarui.")
        except sqlite3.Error:
            flash("Status akun recruiter belum bisa diperbarui. Silakan coba lagi.")

        return redirect(url_for("admin_recruiters"))


    @app.route("/admin/opportunities")
    @admin_required_decorator
    def admin_opportunities():
        rows = list_role_opportunities()
        return render_template("admin/opportunities.html", opportunities=rows)


    @app.route("/admin/opportunities/create", methods=["GET", "POST"])
    @admin_required_decorator
    def admin_create_opportunity():
        return _handle_form(
            "ditambahkan", "Tambah Peluang", url_for("admin_create_opportunity")
        )


    @app.route("/admin/opportunities/<int:opportunity_id>/edit", methods=["GET", "POST"])
    @admin_required_decorator
    def admin_edit_opportunity(opportunity_id):
        row = get_opportunity_or_404(opportunity_id)
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
                update_opportunity(opportunity_id, opportunity)
                record_audit_event(
                    "opportunity.update",
                    target_type="opportunity",
                    target_id=opportunity_id,
                    metadata={"scope": "admin"},
                )
                flash("Peluang berhasil diperbarui.")
                return redirect(url_for("admin_opportunities"))
            except sqlite3.Error:
                flash("Peluang belum bisa diperbarui. Silakan coba lagi.")
        else:
            opportunity = dict(row)

        return render_template(
            "admin/opportunity_form.html",
            opportunity=opportunity,
            form_title="Edit Peluang",
            action_url=url_for("admin_edit_opportunity", opportunity_id=opportunity_id),
        )


    @app.route("/admin/opportunities/<int:opportunity_id>/delete", methods=["POST"])
    @admin_required_decorator
    def admin_delete_opportunity(opportunity_id):
        get_opportunity_or_404(opportunity_id)

        try:
            delete_opportunity_with_cascade(opportunity_id)
            record_audit_event(
                "opportunity.delete",
                target_type="opportunity",
                target_id=opportunity_id,
                metadata={"scope": "admin"},
            )
            flash("Peluang berhasil dihapus.")
        except sqlite3.Error:
            flash("Peluang belum bisa dihapus. Silakan coba lagi.")

        return redirect(url_for("admin_opportunities"))
