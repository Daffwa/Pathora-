import json
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


ADMIN_AUDIT_ACTION_LABELS = {
    "auth.login": "Login",
    "auth.login_blocked": "Login ditolak",
    "account.register": "Akun baru",
    "document.upload": "Upload dokumen",
    "opportunity.create": "Lowongan dibuat",
    "opportunity.update": "Lowongan diperbarui",
    "opportunity.delete": "Lowongan dihapus",
    "application_status.update": "Status applicant diubah",
    "application_status.bulk_update": "Status applicant massal",
    "recruiter_account.status_update": "Status recruiter diubah",
    "recruiter.profile_update": "Profil recruiter diubah",
}


def _label_admin_activity(row):
    return {
        "actor_name": row["actor_name"] or "Sistem",
        "action_label": ADMIN_AUDIT_ACTION_LABELS.get(row["action"], row["action"]),
        "target_type": row["target_type"] or "aktivitas",
        "target_id": row["target_id"],
        "created_at": row["created_at"],
    }


def _audit_metadata_summary(metadata):
    if not metadata:
        return "-"

    try:
        payload = json.loads(metadata)
    except (TypeError, json.JSONDecodeError):
        return str(metadata)

    if not payload:
        return "-"

    parts = []
    for key, value in payload.items():
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(item) for item in value[:4])
        elif isinstance(value, dict):
            value = ", ".join(f"{child_key}: {child_value}" for child_key, child_value in value.items())
        parts.append(f"{key}: {value}")
    return "; ".join(parts)


def _audit_log_payload(row):
    return {
        "id": row["id"],
        "actor_name": row["actor_name"] or "Sistem",
        "actor_email": row["actor_email"] or "",
        "action": row["action"],
        "action_label": ADMIN_AUDIT_ACTION_LABELS.get(row["action"], row["action"]),
        "target_type": row["target_type"] or "-",
        "target_id": row["target_id"],
        "metadata_summary": _audit_metadata_summary(row["metadata"]),
        "ip_address": row["ip_address"] or "-",
        "created_at": row["created_at"],
    }


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
        pending_recruiters = get_db().execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE role = ? AND account_status = ?
            """,
            ("recruiter", "pending"),
        ).fetchone()[0]
        recent_activity = get_db().execute(
            """
            SELECT
                audit_logs.action,
                audit_logs.target_type,
                audit_logs.target_id,
                audit_logs.created_at,
                users.name AS actor_name
            FROM audit_logs
            LEFT JOIN users ON users.id = audit_logs.user_id
            ORDER BY audit_logs.created_at DESC, audit_logs.id DESC
            LIMIT 6
            """
        ).fetchall()

        return render_template(
            "admin/dashboard.html",
            total_opportunities=total_opportunities,
            total_internship=total_internship,
            total_scholarship=total_scholarship,
            total_recruiters=total_recruiters,
            pending_recruiters=pending_recruiters,
            recent_activity=[_label_admin_activity(row) for row in recent_activity],
        )


    @app.route("/admin/audit-logs")
    @admin_required_decorator
    def admin_audit_logs():
        selected_action = request.args.get("action", "").strip()
        query_text = request.args.get("q", "").strip()
        where_clauses = []
        params = []

        if selected_action:
            where_clauses.append("audit_logs.action = ?")
            params.append(selected_action)

        if query_text:
            where_clauses.append(
                """
                (
                    audit_logs.action LIKE ?
                    OR audit_logs.target_type LIKE ?
                    OR users.name LIKE ?
                    OR users.email LIKE ?
                )
                """
            )
            like_query = f"%{query_text}%"
            params.extend([like_query, like_query, like_query, like_query])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        logs = get_db().execute(
            f"""
            SELECT
                audit_logs.id,
                audit_logs.action,
                audit_logs.target_type,
                audit_logs.target_id,
                audit_logs.metadata,
                audit_logs.ip_address,
                audit_logs.created_at,
                users.name AS actor_name,
                users.email AS actor_email
            FROM audit_logs
            LEFT JOIN users ON users.id = audit_logs.user_id
            {where_sql}
            ORDER BY audit_logs.created_at DESC, audit_logs.id DESC
            LIMIT 100
            """,
            params,
        ).fetchall()
        action_rows = get_db().execute(
            "SELECT DISTINCT action FROM audit_logs ORDER BY action"
        ).fetchall()

        return render_template(
            "admin/audit_logs.html",
            audit_logs=[_audit_log_payload(row) for row in logs],
            action_options=[row["action"] for row in action_rows],
            selected_action=selected_action,
            query_text=query_text,
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
