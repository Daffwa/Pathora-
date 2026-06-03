from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from dto.opportunity import Opportunity
from repositories import opportunity_repository
from services.auth_service import get_current_role, jobseeker_required_decorator
from services.database_service import DatabaseAccessError, build_database_error_message
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

        opportunity_rows = opportunity_repository.search_opportunities(
            search_query=search_query,
            opportunity_type=opportunity_type,
            location=location,
        )
        opportunity_list = [
            Opportunity.from_row(opportunity_repository.as_opportunity_row(row))
            for row in opportunity_rows
        ]
        current_role = get_current_role() if "user_id" in session else None
        scoring_context = get_user_scoring_context()

        for opportunity in opportunity_list:
            apply_priority_score(opportunity, scoring_context)

        if sort_by == "priority" and scoring_context is not None:
            opportunity_list.sort(
                key=lambda opportunity: opportunity.priority_score or 0,
                reverse=True,
            )

        locations = opportunity_repository.list_distinct_locations()

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
    @jobseeker_required_decorator
    def bookmark_opportunity(opportunity_id):
        get_opportunity_or_404(opportunity_id)

        try:
            opportunity_repository.add_bookmark(session["user_id"], opportunity_id)
            flash("Peluang berhasil disimpan.")
        except IntegrityError:
            db.session.rollback()
            flash("Peluang ini sudah ada di Bookmark.")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Peluang belum bisa disimpan. Silakan coba lagi.")

        return redirect(request.referrer or url_for("opportunities"))


    @app.route("/bookmarks/<int:opportunity_id>/remove", methods=["POST"])
    @jobseeker_required_decorator
    def remove_bookmark(opportunity_id):
        try:
            opportunity_repository.remove_bookmark(session["user_id"], opportunity_id)
            flash("Peluang dihapus dari Bookmark.")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Peluang belum bisa dihapus. Silakan coba lagi.")

        return redirect(request.referrer or url_for("bookmarks"))


    @app.route("/bookmarks")
    @jobseeker_required_decorator
    def bookmarks():
        try:
            saved_opportunities = get_saved_profile_opportunities(session["user_id"])
        except DatabaseAccessError:
            raise
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise DatabaseAccessError(
                build_database_error_message("Halaman Bookmark tidak bisa membaca database.")
            ) from exc

        return render_template(
            "bookmarks.html",
            opportunities=saved_opportunities,
        )
