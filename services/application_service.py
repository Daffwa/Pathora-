from flask import abort, session

from repositories import application_repository
from services.constants import (
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_BADGE_CLASSES,
    LEGACY_APPLICATION_STATUS_LABELS,
)


def get_application_for_user_or_404(application_id):
    application = application_repository.find_row_by_user_and_id(
        session["user_id"],
        application_id,
    )

    if application is None:
        abort(404)

    return application


def application_status_label(status):
    return LEGACY_APPLICATION_STATUS_LABELS.get(status, status or APPLICATION_STATUS_APPLIED)


def application_status_badge_class(status):
    normalized_status = application_status_label(status)
    return APPLICATION_STATUS_BADGE_CLASSES.get(normalized_status, "status-unknown")
