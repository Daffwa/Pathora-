from flask import abort, session

from services.constants import (
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_BADGE_CLASSES,
    LEGACY_APPLICATION_STATUS_LABELS,
)
from services.database_service import get_db


def get_application_for_user_or_404(application_id):
    application = get_db().execute(
        """
        SELECT id FROM applications
        WHERE id = ? AND user_id = ?
        """,
        (application_id, session["user_id"]),
    ).fetchone()

    if application is None:
        abort(404)

    return application


def application_status_label(status):
    return LEGACY_APPLICATION_STATUS_LABELS.get(status, status or APPLICATION_STATUS_APPLIED)


def application_status_badge_class(status):
    normalized_status = application_status_label(status)
    return APPLICATION_STATUS_BADGE_CLASSES.get(normalized_status, "status-unknown")
