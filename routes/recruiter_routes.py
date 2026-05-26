import sqlite3

from flask import flash, redirect, render_template, request, session, url_for

from services.audit_service import record_audit_event
from services.auth_service import (
    get_current_role,
    get_current_user,
    recruiter_or_admin_required_decorator,
    recruiter_required_decorator,
)
from services.constants import APPLICANT_SORT_RECENT, RECRUITER_APPLICATION_STATUSES
from services.database_service import get_db
from services.opportunity_service import (
    EMPTY_OPPORTUNITY_FORM,
    create_opportunity,
    delete_opportunity_with_cascade,
    get_opportunity_form_data,
    update_opportunity,
    validate_opportunity_form,
)
from services.recruiter_service import (
    get_applicant_list_url,
    get_recruiter_applicant_rows,
    get_recruiter_application_or_404,
    get_recruiter_opportunity_or_404,
    make_recruiter_applicants_csv,
    normalize_applicant_sort,
    parse_positive_int,
)


def _recruiter_opportunity_form(opportunity=None, form_title="", action_url=""):
    recruiter = get_current_user()
    company_name = recruiter["company_name"] or ""
    if opportunity is None:
        opportunity = dict(EMPTY_OPPORTUNITY_FORM)
        opportunity["provider"] = company_name

    if request.method == "POST":
        opportunity = get_opportunity_form_data()
        errors = validate_opportunity_form(opportunity)
        if errors:
            for error in errors:
                flash(error)
            return render_template(
                "recruiter/opportunity_form.html",
                opportunity=opportunity,
                form_title=form_title,
                action_url=action_url,
            ), 400

        try:
            opportunity_id = create_opportunity(opportunity, session["user_id"], company_name)
            record_audit_event(
                "opportunity.create",
                target_type="opportunity",
                target_id=opportunity_id,
                metadata={"scope": "recruiter"},
            )
            flash("Lowongan berhasil dibuat.")
            return redirect(url_for("recruiter_opportunities"))
        except sqlite3.Error:
            flash("Lowongan belum bisa dibuat. Silakan coba lagi.")

    return render_template(
        "recruiter/opportunity_form.html",
        opportunity=opportunity,
        form_title=form_title,
        action_url=action_url,
    )


def register(app):
    @app.route("/recruiter/profile")
    @recruiter_required_decorator
    def recruiter_profile():
        recruiter = get_current_user()
        total_opportunities = get_db().execute(
            "SELECT COUNT(*) FROM opportunities WHERE created_by = ?",
            (session["user_id"],),
        ).fetchone()[0]
        total_applicants = get_db().execute(
            """
            SELECT COUNT(*)
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            WHERE opportunities.created_by = ?
            """,
            (session["user_id"],),
        ).fetchone()[0]
        recent_opportunities = get_db().execute(
            """
            SELECT opportunities.*, COUNT(applications.id) AS applicant_count
            FROM opportunities
            LEFT JOIN applications ON applications.opportunity_id = opportunities.id
            WHERE opportunities.created_by = ?
            GROUP BY opportunities.id
            ORDER BY opportunities.updated_at DESC
            LIMIT 4
            """,
            (session["user_id"],),
        ).fetchall()

        return render_template(
            "recruiter/profile.html",
            recruiter=recruiter,
            total_opportunities=total_opportunities,
            total_applicants=total_applicants,
            recent_opportunities=recent_opportunities,
        )


    @app.route("/recruiter/dashboard")
    @recruiter_required_decorator
    def recruiter_dashboard():
        recruiter = get_current_user()
        total_opportunities = get_db().execute(
            "SELECT COUNT(*) FROM opportunities WHERE created_by = ?",
            (session["user_id"],),
        ).fetchone()[0]
        total_applicants = get_db().execute(
            """
            SELECT COUNT(*)
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            WHERE opportunities.created_by = ?
            """,
            (session["user_id"],),
        ).fetchone()[0]
        recent_opportunities = get_db().execute(
            """
            SELECT opportunities.*, COUNT(applications.id) AS applicant_count
            FROM opportunities
            LEFT JOIN applications ON applications.opportunity_id = opportunities.id
            WHERE opportunities.created_by = ?
            GROUP BY opportunities.id
            ORDER BY opportunities.updated_at DESC
            LIMIT 3
            """,
            (session["user_id"],),
        ).fetchall()
        recent_applicants = get_recruiter_applicant_rows()[:5]

        return render_template(
            "recruiter/dashboard.html",
            recruiter=recruiter,
            total_opportunities=total_opportunities,
            total_applicants=total_applicants,
            recent_opportunities=recent_opportunities,
            recent_applicants=recent_applicants,
        )


    @app.route("/recruiter/opportunities")
    @recruiter_required_decorator
    def recruiter_opportunities():
        rows = get_db().execute(
            """
            SELECT opportunities.*, COUNT(applications.id) AS applicant_count
            FROM opportunities
            LEFT JOIN applications ON applications.opportunity_id = opportunities.id
            WHERE opportunities.created_by = ?
            GROUP BY opportunities.id
            ORDER BY opportunities.updated_at DESC
            """,
            (session["user_id"],),
        ).fetchall()

        return render_template("recruiter/opportunities.html", opportunities=rows)


    @app.route("/recruiter/opportunities/create", methods=["GET", "POST"])
    @recruiter_required_decorator
    def recruiter_create_opportunity():
        return _recruiter_opportunity_form(
            form_title="Tambah Lowongan",
            action_url=url_for("recruiter_create_opportunity"),
        )


    @app.route("/recruiter/opportunities/<int:opportunity_id>/edit", methods=["GET", "POST"])
    @recruiter_required_decorator
    def recruiter_edit_opportunity(opportunity_id):
        row = get_recruiter_opportunity_or_404(opportunity_id)
        opportunity = dict(row)

        if request.method == "POST":
            opportunity = get_opportunity_form_data()
            errors = validate_opportunity_form(opportunity)
            if errors:
                for error in errors:
                    flash(error)
                return render_template(
                    "recruiter/opportunity_form.html",
                    opportunity=opportunity,
                    form_title="Edit Lowongan",
                    action_url=url_for("recruiter_edit_opportunity", opportunity_id=opportunity_id),
                ), 400

            try:
                update_opportunity(
                    opportunity_id, opportunity,
                    company_name=get_current_user()["company_name"] or "",
                    user_id=session["user_id"],
                )
                record_audit_event(
                    "opportunity.update",
                    target_type="opportunity",
                    target_id=opportunity_id,
                    metadata={"scope": "recruiter"},
                )
                flash("Lowongan berhasil diperbarui.")
                return redirect(url_for("recruiter_opportunities"))
            except sqlite3.Error:
                flash("Lowongan belum bisa diperbarui. Silakan coba lagi.")

        return render_template(
            "recruiter/opportunity_form.html",
            opportunity=opportunity,
            form_title="Edit Lowongan",
            action_url=url_for("recruiter_edit_opportunity", opportunity_id=opportunity_id),
        )


    @app.route("/recruiter/opportunities/<int:opportunity_id>/delete", methods=["POST"])
    @recruiter_required_decorator
    def recruiter_delete_opportunity(opportunity_id):
        get_recruiter_opportunity_or_404(opportunity_id)

        try:
            delete_opportunity_with_cascade(opportunity_id, session["user_id"])
            record_audit_event(
                "opportunity.delete",
                target_type="opportunity",
                target_id=opportunity_id,
                metadata={"scope": "recruiter"},
            )
            flash("Lowongan berhasil dihapus.")
        except sqlite3.Error:
            flash("Lowongan belum bisa dihapus. Silakan coba lagi.")

        return redirect(url_for("recruiter_opportunities"))


    @app.route("/recruiter/applicants")
    @recruiter_or_admin_required_decorator
    def recruiter_applicants():
        current_sort = normalize_applicant_sort(request.args.get("sort", APPLICANT_SORT_RECENT))
        return render_template(
            "recruiter/applicants.html",
            applicants=get_recruiter_applicant_rows(sort_by=current_sort),
            opportunity=None,
            statuses=RECRUITER_APPLICATION_STATUSES,
            current_sort=current_sort,
        )


    @app.route("/recruiter/opportunities/<int:opportunity_id>/applicants")
    @recruiter_or_admin_required_decorator
    def recruiter_opportunity_applicants(opportunity_id):
        opportunity = get_recruiter_opportunity_or_404(opportunity_id)
        current_sort = normalize_applicant_sort(request.args.get("sort", APPLICANT_SORT_RECENT))
        return render_template(
            "recruiter/applicants.html",
            applicants=get_recruiter_applicant_rows(opportunity_id, current_sort),
            opportunity=opportunity,
            statuses=RECRUITER_APPLICATION_STATUSES,
            current_sort=current_sort,
        )


    @app.route("/recruiter/applicants/export.csv")
    @recruiter_or_admin_required_decorator
    def recruiter_applicants_export():
        opportunity_id = parse_positive_int(request.args.get("opportunity_id"))
        opportunity = get_recruiter_opportunity_or_404(opportunity_id) if opportunity_id else None
        current_sort = normalize_applicant_sort(request.args.get("sort", APPLICANT_SORT_RECENT))
        applicants = get_recruiter_applicant_rows(opportunity_id, current_sort)
        return make_recruiter_applicants_csv(applicants, opportunity)


    @app.route("/recruiter/applicants/bulk-action", methods=["POST"])
    @recruiter_or_admin_required_decorator
    def recruiter_bulk_update_applicants():
        opportunity_id = parse_positive_int(request.form.get("opportunity_id"))
        if opportunity_id is not None:
            get_recruiter_opportunity_or_404(opportunity_id)

        current_sort = normalize_applicant_sort(request.form.get("sort", APPLICANT_SORT_RECENT))
        selected_ids = []
        for raw_application_id in request.form.getlist("application_ids"):
            application_id = parse_positive_int(raw_application_id)
            if application_id is not None and application_id not in selected_ids:
                selected_ids.append(application_id)

        status = request.form.get("status", "").strip()
        return_url = get_applicant_list_url(opportunity_id, current_sort)

        if not selected_ids:
            flash("Pilih minimal satu applicant untuk aksi massal.")
            return redirect(return_url)

        if status not in RECRUITER_APPLICATION_STATUSES:
            flash("Status applicant tidak valid.")
            return redirect(return_url)

        placeholders = ", ".join("?" for _ in selected_ids)
        owner_filter = ""
        params = [status, *selected_ids]
        current_role = get_current_role()

        if current_role == "recruiter":
            owner_filter += " AND opportunities.created_by = ?"
            params.append(session["user_id"])

        if opportunity_id is not None:
            owner_filter += " AND opportunities.id = ?"
            params.append(opportunity_id)

        try:
            cursor = get_db().execute(
                f"""
                UPDATE applications
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                  AND EXISTS (
                      SELECT 1
                      FROM opportunities
                      WHERE opportunities.id = applications.opportunity_id
                      {owner_filter}
                  )
                """,
                params,
            )
            get_db().commit()
            if cursor.rowcount:
                record_audit_event(
                    "application_status.bulk_update",
                    target_type="application",
                    metadata={
                        "status": status,
                        "application_ids": selected_ids,
                        "updated_count": cursor.rowcount,
                    },
                )
                flash(f"{cursor.rowcount} applicant berhasil diperbarui menjadi {status}.")
            else:
                flash("Tidak ada applicant yang dapat diperbarui.")
        except sqlite3.Error:
            flash("Aksi massal belum bisa diproses. Silakan coba lagi.")

        return redirect(return_url)


    @app.route("/recruiter/applicants/<int:application_id>")
    @recruiter_or_admin_required_decorator
    def recruiter_applicant_detail(application_id):
        application = get_recruiter_application_or_404(application_id)
        documents = get_db().execute(
            """
            SELECT doc_type, is_uploaded, updated_at
            FROM documents
            WHERE user_id = ?
            ORDER BY doc_type ASC
            """,
            (application["applicant_user_id"],),
        ).fetchall()

        return render_template(
            "recruiter/applicant_detail.html",
            application=application,
            documents=documents,
            statuses=RECRUITER_APPLICATION_STATUSES,
        )


    @app.route("/recruiter/applications/<int:application_id>/status", methods=["POST"])
    @recruiter_or_admin_required_decorator
    def recruiter_update_application_status(application_id):
        get_recruiter_application_or_404(application_id)
        status = request.form.get("status", "").strip()

        if status not in RECRUITER_APPLICATION_STATUSES:
            flash("Status applicant tidak valid.")
            return redirect(url_for("recruiter_applicant_detail", application_id=application_id))

        try:
            get_db().execute(
                """
                UPDATE applications
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, application_id),
            )
            get_db().commit()
            record_audit_event(
                "application_status.update",
                target_type="application",
                target_id=application_id,
                metadata={"status": status},
            )
            flash("Status applicant berhasil diperbarui.")
        except sqlite3.Error:
            flash("Status applicant belum bisa diperbarui. Silakan coba lagi.")

        return redirect(url_for("recruiter_applicant_detail", application_id=application_id))
