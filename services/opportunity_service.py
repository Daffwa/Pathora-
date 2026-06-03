from datetime import datetime

from flask import abort, request, session
from sqlalchemy.exc import SQLAlchemyError

from dto.opportunity import Opportunity
from extensions import db
from repositories import (
    application_repository,
    document_repository,
    opportunity_repository,
    user_repository,
)
from services.auth_service import get_current_role
from services.constants import DOCUMENT_TYPES
from services.scoring_service import (
    calculate_days_left,
    calculate_deadline_score,
    calculate_document_score,
    calculate_priority_score,
    calculate_skill_match_score,
    get_priority_label,
)
from services.url_validation_service import normalize_public_url


def _opportunity_from_orm(opportunity):
    return Opportunity.from_row(opportunity_repository.as_opportunity_row(opportunity))


def _raise_sqlalchemy_error(exc):
    db.session.rollback()
    raise exc


def get_deadline_info(deadline_text):
    days_left = calculate_days_left(deadline_text)

    if days_left is None:
        return {"days_left": None, "status": "Unknown"}

    if days_left < 0:
        status = "Closed"
    elif days_left <= 7:
        status = "Urgent"
    else:
        status = "Open"

    return {"days_left": days_left, "status": status}


def get_opportunity_or_404(opportunity_id):
    row = opportunity_repository.find_row_by_id(opportunity_id)

    if row is None:
        abort(404)

    return row


def get_user_scoring_context():
    if "user_id" not in session:
        return None
    if get_current_role() != "jobseeker":
        return None

    user = user_repository.find_by_id(session["user_id"])
    completed_documents = document_repository.count_completed_by_user(session["user_id"])

    return {
        "skills": user.skills if user else "",
        "completed_documents": completed_documents,
        "total_documents": len(DOCUMENT_TYPES),
    }


def apply_priority_score(opportunity, scoring_context):
    deadline_info = get_deadline_info(opportunity.deadline)
    opportunity.days_left = deadline_info["days_left"]
    opportunity.deadline_status = deadline_info["status"]

    if scoring_context is None:
        return opportunity

    deadline_score = calculate_deadline_score(opportunity.days_left)
    skill_score = calculate_skill_match_score(
        scoring_context["skills"], opportunity.required_skills
    )
    document_score = calculate_document_score(
        scoring_context["completed_documents"],
        scoring_context["total_documents"],
    )
    priority_score = calculate_priority_score(
        deadline_score, skill_score, document_score
    )
    is_closed = opportunity.days_left is not None and opportunity.days_left < 0

    opportunity.deadline_score = deadline_score
    opportunity.skill_match_score = skill_score
    opportunity.document_score = document_score
    opportunity.priority_score = priority_score
    opportunity.priority_label = get_priority_label(priority_score, is_closed)
    return opportunity


def get_dashboard_summary(user_id):
    total_saved = opportunity_repository.count_bookmarks_by_user(user_id)
    total_applications = application_repository.count_by_user(user_id)
    completed_documents = document_repository.count_completed_by_user(user_id)

    return {
        "total_saved": total_saved,
        "total_applications": total_applications,
        "completed_documents": completed_documents,
        "total_documents": len(DOCUMENT_TYPES),
    }


def get_recent_saved_opportunities(user_id):
    return opportunity_repository.list_recent_saved_rows_by_user(user_id)


def get_recent_applications(user_id):
    return application_repository.list_recent_with_opportunity_by_user(user_id)


def get_urgent_deadlines(user_id):
    urgent_opportunities = []
    scoring_context = get_user_scoring_context()
    for opportunity_row in opportunity_repository.list_related_to_user(user_id):
        opportunity = _opportunity_from_orm(opportunity_row)
        apply_priority_score(opportunity, scoring_context)
        if opportunity.days_left is not None and 0 <= opportunity.days_left <= 7:
            urgent_opportunities.append(opportunity)

    return sorted(urgent_opportunities, key=lambda opportunity: opportunity.days_left)


def get_top_priority_opportunity():
    scoring_context = get_user_scoring_context()
    if scoring_context is None:
        return None

    opportunities = []
    for opportunity_row in opportunity_repository.list_all():
        opportunity = _opportunity_from_orm(opportunity_row)
        apply_priority_score(opportunity, scoring_context)
        if opportunity.priority_label != "Closed":
            opportunities.append(opportunity)

    if not opportunities:
        return None

    return max(opportunities, key=lambda opportunity: opportunity.priority_score or 0)


def is_valid_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False

    return True


# ── Shared CRUD helpers (used by both admin & recruiter routes) ──

EMPTY_OPPORTUNITY_FORM = {
    "title": "", "type": "internship", "provider": "", "location": "",
    "deadline": "", "description": "", "requirements": "",
    "official_link": "", "required_skills": "",
}


def list_role_opportunities(user_id=None):
    if user_id is None:
        return opportunity_repository.list_all_rows()
    return opportunity_repository.list_rows_by_creator(user_id)


def create_opportunity(opportunity, user_id=None, company_name=None):
    try:
        created_opportunity = opportunity_repository.create_opportunity(
            opportunity,
            created_by=user_id,
            company_name=company_name or "",
        )
    except SQLAlchemyError as exc:
        _raise_sqlalchemy_error(exc)
    return created_opportunity.id


def update_opportunity(opportunity_id, opportunity, company_name=None, user_id=None):
    try:
        updated_opportunity = opportunity_repository.update_opportunity(
            opportunity_id,
            opportunity,
            creator_id=user_id,
            company_name=company_name or "",
        )
    except SQLAlchemyError as exc:
        _raise_sqlalchemy_error(exc)
    return 1 if updated_opportunity is not None else 0


def delete_opportunity_with_cascade(opportunity_id, user_id=None):
    try:
        return opportunity_repository.delete_opportunity(
            opportunity_id,
            creator_id=user_id,
        )
    except SQLAlchemyError as exc:
        _raise_sqlalchemy_error(exc)


def get_opportunity_form_data():
    opportunity_type = request.form.get(
        "opportunity_type", request.form.get("type", "")
    ).strip().lower()
    return {
        "title": request.form.get("title", "").strip(),
        "type": opportunity_type,
        "provider": request.form.get("provider", "").strip(),
        "location": request.form.get("location", "").strip(),
        "deadline": request.form.get("deadline", "").strip(),
        "description": request.form.get("description", "").strip(),
        "requirements": request.form.get("requirements", "").strip(),
        "official_link": request.form.get("official_link", "").strip(),
        "required_skills": request.form.get("required_skills", "").strip(),
    }


def validate_opportunity_form(data):
    errors = []

    if not data["title"]:
        errors.append("Title wajib diisi.")
    if data["type"] not in {"internship", "scholarship"}:
        errors.append("Opportunity type harus internship atau scholarship.")
    if not data["provider"]:
        errors.append("Organizer wajib diisi.")
    if not data["location"]:
        errors.append("Location wajib diisi.")
    if not data["deadline"] or not is_valid_date(data["deadline"]):
        errors.append("Deadline wajib diisi dengan format YYYY-MM-DD.")
    normalized_link, link_error = normalize_public_url(
        data.get("official_link", ""),
        "Tautan resmi",
    )
    data["official_link"] = normalized_link
    if link_error:
        errors.append(link_error)

    return errors
