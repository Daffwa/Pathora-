from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from repositories import application_repository
from services.auth_service import jobseeker_required_decorator
from services.constants import APPLICATION_STATUS_APPLIED
from services.opportunity_service import get_opportunity_or_404


bp = Blueprint("application", __name__)

@bp.route("/opportunities/<int:opportunity_id>/track", methods=["POST"], endpoint="track_opportunity")
@jobseeker_required_decorator
def track_opportunity(opportunity_id):
    get_opportunity_or_404(opportunity_id)

    try:
        application_repository.create_application(
            user_id=session["user_id"],
            opportunity_id=opportunity_id,
            status=APPLICATION_STATUS_APPLIED,
            notes="",
        )
        flash("Lamaran berhasil dikirim.")
        return redirect(url_for("applications"))
    except IntegrityError:
        db.session.rollback()
        flash("Kamu sudah mendaftar pada peluang ini.")
        return redirect(url_for("applications"))
    except SQLAlchemyError:
        db.session.rollback()
        flash("Tracker belum bisa ditambahkan. Silakan coba lagi.")
        return redirect(request.referrer or url_for("opportunities"))


@bp.route("/applications", endpoint="applications")
@jobseeker_required_decorator
def applications():
    rows = application_repository.list_with_opportunity_by_user(session["user_id"])

    return render_template(
        "applications.html",
        applications=rows,
    )


@bp.route("/applications/<int:application_id>/remove", methods=["POST"], endpoint="remove_application")
@jobseeker_required_decorator
def remove_application(application_id):
    if application_repository.find_by_user_and_id(session["user_id"], application_id) is None:
        abort(404)

    try:
        application_repository.delete_by_user_and_id(session["user_id"], application_id)
        flash("Tracker lamaran berhasil dihapus.")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Tracker belum bisa dihapus. Silakan coba lagi.")

    return redirect(url_for("applications"))
