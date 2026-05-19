import sqlite3

from flask import flash, redirect, render_template, request, session, url_for

from services.application_service import get_application_for_user_or_404
from services.auth_service import jobseeker_required_decorator
from services.constants import APPLICATION_STATUS_APPLIED
from services.database_service import get_db
from services.opportunity_service import get_opportunity_or_404


def register(app):
    @app.route("/opportunities/<int:opportunity_id>/track", methods=["POST"])
    @jobseeker_required_decorator
    def track_opportunity(opportunity_id):
        get_opportunity_or_404(opportunity_id)

        try:
            get_db().execute(
                """
                INSERT INTO applications (user_id, opportunity_id, status, notes)
                VALUES (?, ?, ?, ?)
                """,
                (session["user_id"], opportunity_id, APPLICATION_STATUS_APPLIED, ""),
            )
            get_db().commit()
            flash("Lamaran berhasil dikirim.")
            return redirect(url_for("applications"))
        except sqlite3.IntegrityError:
            flash("Kamu sudah mendaftar pada peluang ini.")
            return redirect(url_for("applications"))
        except sqlite3.Error:
            flash("Tracker belum bisa ditambahkan. Silakan coba lagi.")
            return redirect(request.referrer or url_for("opportunities"))


    @app.route("/applications")
    @jobseeker_required_decorator
    def applications():
        rows = get_db().execute(
            """
            SELECT
                applications.id AS application_id,
                applications.status,
                applications.notes,
                applications.applied_at,
                applications.updated_at,
                opportunities.id AS opportunity_id,
                opportunities.title,
                opportunities.provider,
                opportunities.type,
                opportunities.location,
                opportunities.deadline
            FROM applications
            JOIN opportunities ON opportunities.id = applications.opportunity_id
            WHERE applications.user_id = ?
            ORDER BY applications.updated_at DESC
            """,
            (session["user_id"],),
        ).fetchall()

        return render_template(
            "applications.html",
            applications=rows,
        )


    @app.route("/applications/<int:application_id>/remove", methods=["POST"])
    @jobseeker_required_decorator
    def remove_application(application_id):
        get_application_for_user_or_404(application_id)

        try:
            get_db().execute(
                """
                DELETE FROM applications
                WHERE id = ? AND user_id = ?
                """,
                (application_id, session["user_id"]),
            )
            get_db().commit()
            flash("Tracker lamaran berhasil dihapus.")
        except sqlite3.Error:
            flash("Tracker belum bisa dihapus. Silakan coba lagi.")

        return redirect(url_for("applications"))
