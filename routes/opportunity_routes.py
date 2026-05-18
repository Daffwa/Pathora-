import sqlite3

from flask import flash, redirect, render_template, request, session, url_for

from models.opportunity import Opportunity
from services.auth_service import get_current_role, jobseeker_required
from services.database_service import DatabaseAccessError, build_database_error_message, get_db
from services.opportunity_service import (
    apply_priority_score,
    get_opportunity_or_404,
    get_user_scoring_context,
)
from services.profile_service import get_saved_profile_opportunities


def register(app):
    @app.route("/opportunities")
    def opportunities():
        search_query = request.args.get("q", "").strip()
        opportunity_type = request.args.get("type", "").strip().lower()
        location = request.args.get("location", "").strip()
        sort_by = request.args.get("sort", "deadline").strip().lower()

        filters = []
        params = []

        if search_query:
            filters.append(
                "(title LIKE ? OR provider LIKE ? OR location LIKE ? OR description LIKE ?)"
            )
            keyword = f"%{search_query}%"
            params.extend([keyword, keyword, keyword, keyword])

        if opportunity_type in {"internship", "scholarship"}:
            filters.append("type = ?")
            params.append(opportunity_type)

        if location:
            filters.append("location LIKE ?")
            params.append(f"%{location}%")

        query = "SELECT * FROM opportunities"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY deadline ASC"

        rows = get_db().execute(query, params).fetchall()
        opportunity_list = [Opportunity.from_row(row) for row in rows]
        current_role = get_current_role() if "user_id" in session else None
        scoring_context = get_user_scoring_context()

        for opportunity in opportunity_list:
            apply_priority_score(opportunity, scoring_context)

        if sort_by == "priority" and scoring_context is not None:
            opportunity_list.sort(
                key=lambda opportunity: opportunity.priority_score or 0,
                reverse=True,
            )

        location_rows = get_db().execute(
            "SELECT DISTINCT location FROM opportunities ORDER BY location ASC"
        ).fetchall()
        locations = [row["location"] for row in location_rows]

        return render_template(
            "opportunities.html",
            opportunities=opportunity_list,
            filters={
                "q": search_query,
                "type": opportunity_type,
                "location": location,
                "sort": sort_by,
            },
            locations=locations,
            is_logged_in="user_id" in session,
            can_use_jobseeker_actions=current_role == "jobseeker",
        )


    @app.route("/opportunities/<int:opportunity_id>")
    def opportunity_detail(opportunity_id):
        row = get_opportunity_or_404(opportunity_id)
        opportunity = Opportunity.from_row(row)
        current_role = get_current_role() if "user_id" in session else None
        scoring_context = get_user_scoring_context()
        apply_priority_score(opportunity, scoring_context)
        return render_template(
            "opportunity_detail.html",
            opportunity=opportunity,
            is_logged_in="user_id" in session,
            can_use_jobseeker_actions=current_role == "jobseeker",
        )


    @app.route("/opportunities/<int:opportunity_id>/bookmark", methods=["POST"])
    def bookmark_opportunity(opportunity_id):
        login_redirect = jobseeker_required()
        if login_redirect is not None:
            return login_redirect

        get_opportunity_or_404(opportunity_id)

        try:
            get_db().execute(
                """
                INSERT INTO bookmarks (user_id, opportunity_id)
                VALUES (?, ?)
                """,
                (session["user_id"], opportunity_id),
            )
            get_db().commit()
            flash("Peluang berhasil disimpan.")
        except sqlite3.IntegrityError:
            flash("Peluang ini sudah ada di Bookmark.")
        except sqlite3.Error:
            flash("Peluang belum bisa disimpan. Silakan coba lagi.")

        return redirect(request.referrer or url_for("opportunities"))


    @app.route("/bookmarks/<int:opportunity_id>/remove", methods=["POST"])
    def remove_bookmark(opportunity_id):
        login_redirect = jobseeker_required()
        if login_redirect is not None:
            return login_redirect

        try:
            get_db().execute(
                """
                DELETE FROM bookmarks
                WHERE user_id = ? AND opportunity_id = ?
                """,
                (session["user_id"], opportunity_id),
            )
            get_db().commit()
            flash("Peluang dihapus dari Bookmark.")
        except sqlite3.Error:
            flash("Peluang belum bisa dihapus. Silakan coba lagi.")

        return redirect(request.referrer or url_for("bookmarks"))


    @app.route("/bookmarks")
    def bookmarks():
        try:
            login_redirect = jobseeker_required()
            if login_redirect is not None:
                return login_redirect

            saved_opportunities = get_saved_profile_opportunities(session["user_id"])
        except DatabaseAccessError:
            raise
        except sqlite3.Error as exc:
            raise DatabaseAccessError(
                build_database_error_message("Halaman Bookmark tidak bisa membaca database.")
            ) from exc

        return render_template(
            "bookmarks.html",
            opportunities=saved_opportunities,
        )
