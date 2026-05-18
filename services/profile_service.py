from flask import session

from models.opportunity import Opportunity
from services.constants import PROFILE_COMPLETION_FIELDS, PROFILE_FORM_FIELDS
from services.database_service import get_db
from services.opportunity_service import apply_priority_score, get_user_scoring_context


def get_current_user_profile():
    return get_db().execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()


def profile_form_data_from_user(user):
    return {field: (user[field] or "") for field in PROFILE_FORM_FIELDS}


def split_profile_list(value):
    if not value:
        return []

    normalized = value.replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def get_saved_profile_opportunities(user_id):
    rows = get_db().execute(
        """
        SELECT
            opportunities.*,
            bookmarks.saved_at,
            applications.status AS application_status
        FROM bookmarks
        JOIN opportunities ON opportunities.id = bookmarks.opportunity_id
        LEFT JOIN applications
            ON applications.opportunity_id = opportunities.id
           AND applications.user_id = bookmarks.user_id
        WHERE bookmarks.user_id = ?
        ORDER BY bookmarks.saved_at DESC
        """,
        (user_id,),
    ).fetchall()

    scoring_context = get_user_scoring_context()
    saved_opportunities = []
    for row in rows:
        opportunity = Opportunity.from_row(row)
        opportunity.saved_at = row["saved_at"]
        opportunity.application_status = row["application_status"] or ""
        apply_priority_score(opportunity, scoring_context)
        saved_opportunities.append(opportunity)

    return saved_opportunities


def get_profile_completion(user, document_progress):
    completed_fields = sum(
        1 for field in PROFILE_COMPLETION_FIELDS if (user[field] or "").strip()
    )
    total_items = len(PROFILE_COMPLETION_FIELDS) + 1
    completed_items = completed_fields

    if document_progress["complete_count"] > 0:
        completed_items += 1

    percent = round((completed_items / total_items) * 100) if total_items else 0

    return {
        "completed": completed_items,
        "total": total_items,
        "percent": percent,
    }
