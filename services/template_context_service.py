from flask import session
from sqlalchemy.exc import SQLAlchemyError

from repositories import user_repository
from services.application_service import application_status_badge_class, application_status_label
from services.asset_service import asset_url
from services.constants import RECRUITER_POSITION_OPTIONS
from services.database_service import DatabaseAccessError


def inject_template_options():
    sidebar_user = None
    if "user_id" in session:
        try:
            sidebar_user = user_repository.find_row_by_id(session["user_id"])
        except (SQLAlchemyError, DatabaseAccessError):
            sidebar_user = None

    return {
        "application_status_badge_class": application_status_badge_class,
        "application_status_label": application_status_label,
        "asset_url": asset_url,
        "recruiter_position_options": RECRUITER_POSITION_OPTIONS,
        "sidebar_user": sidebar_user,
    }
