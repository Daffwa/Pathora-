from datetime import datetime

from flask import abort, request, session

from models.opportunity import Opportunity
from services.auth_service import get_current_role
from services.constants import DOCUMENT_TYPES
from services.database_service import get_db
from services.scoring_service import (
    calculate_days_left,
    calculate_deadline_score,
    calculate_document_score,
    calculate_priority_score,
    calculate_skill_match_score,
    get_priority_label,
)


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
    row = get_db().execute(
        "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
    ).fetchone()

    if row is None:
        abort(404)

    return row


def get_user_scoring_context():
    if "user_id" not in session:
        return None
    if get_current_role() != "jobseeker":
        return None

    user = get_db().execute(
        "SELECT skills FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    completed_documents = get_db().execute(
        """
        SELECT COUNT(*) FROM documents
        WHERE user_id = ? AND is_uploaded = 1
        """,
        (session["user_id"],),
    ).fetchone()[0]

    return {
        "skills": user["skills"] if user else "",
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
    total_saved = get_db().execute(
        "SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    total_applications = get_db().execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    completed_documents = get_db().execute(
        """
        SELECT COUNT(*) FROM documents
        WHERE user_id = ? AND is_uploaded = 1
        """,
        (user_id,),
    ).fetchone()[0]

    return {
        "total_saved": total_saved,
        "total_applications": total_applications,
        "completed_documents": completed_documents,
        "total_documents": len(DOCUMENT_TYPES),
    }


def get_recent_saved_opportunities(user_id):
    return get_db().execute(
        """
        SELECT opportunities.id, opportunities.title, opportunities.provider,
               opportunities.deadline
        FROM bookmarks
        JOIN opportunities ON opportunities.id = bookmarks.opportunity_id
        WHERE bookmarks.user_id = ?
        ORDER BY bookmarks.saved_at DESC
        LIMIT 3
        """,
        (user_id,),
    ).fetchall()


def get_recent_applications(user_id):
    return get_db().execute(
        """
        SELECT applications.status, applications.notes, applications.updated_at,
               opportunities.title
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        WHERE applications.user_id = ?
        ORDER BY applications.updated_at DESC
        LIMIT 3
        """,
        (user_id,),
    ).fetchall()


def get_urgent_deadlines(user_id):
    rows = get_db().execute(
        """
        SELECT DISTINCT opportunities.*
        FROM opportunities
        LEFT JOIN bookmarks ON bookmarks.opportunity_id = opportunities.id
        LEFT JOIN applications ON applications.opportunity_id = opportunities.id
        WHERE bookmarks.user_id = ? OR applications.user_id = ?
        """,
        (user_id, user_id),
    ).fetchall()

    urgent_opportunities = []
    scoring_context = get_user_scoring_context()
    for row in rows:
        opportunity = Opportunity.from_row(row)
        apply_priority_score(opportunity, scoring_context)
        if opportunity.days_left is not None and 0 <= opportunity.days_left <= 7:
            urgent_opportunities.append(opportunity)

    return sorted(urgent_opportunities, key=lambda opportunity: opportunity.days_left)


def get_top_priority_opportunity():
    scoring_context = get_user_scoring_context()
    if scoring_context is None:
        return None

    rows = get_db().execute("SELECT * FROM opportunities").fetchall()
    opportunities = []
    for row in rows:
        opportunity = Opportunity.from_row(row)
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
    query = "SELECT * FROM opportunities"
    params = []
    if user_id is not None:
        query += " WHERE created_by = ?"
        params.append(user_id)
    query += " ORDER BY deadline ASC"
    return get_db().execute(query, params).fetchall()


def create_opportunity(opportunity, user_id=None, company_name=None):
    cursor = get_db().execute(
        """
        INSERT INTO opportunities
        (title, provider, type, description, requirements, official_link,
         required_skills, location, deadline, created_by, company_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opportunity["title"], opportunity["provider"], opportunity["type"],
            opportunity["description"], opportunity["requirements"],
            opportunity["official_link"], opportunity["required_skills"],
            opportunity["location"], opportunity["deadline"],
            user_id, company_name or "",
        ),
    )
    get_db().commit()
    return cursor.lastrowid


def update_opportunity(opportunity_id, opportunity, company_name=None, user_id=None):
    params = [
        opportunity["title"], opportunity["provider"], opportunity["type"],
        opportunity["description"], opportunity["requirements"],
        opportunity["official_link"], opportunity["required_skills"],
        opportunity["location"], opportunity["deadline"],
        company_name or "", opportunity_id,
    ]
    owner_check = ""
    if user_id is not None:
        owner_check = " AND created_by = ?"
        params.append(user_id)

    cursor = get_db().execute(
        f"""
        UPDATE opportunities
        SET title = ?, provider = ?, type = ?, description = ?,
            requirements = ?, official_link = ?, required_skills = ?,
            location = ?, deadline = ?, company_name = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        {owner_check}
        """,
        params,
    )
    get_db().commit()
    return cursor.rowcount


def delete_opportunity_with_cascade(opportunity_id, user_id=None):
    if user_id is not None:
        owned_opportunity = get_db().execute(
            """
            SELECT id
            FROM opportunities
            WHERE id = ? AND created_by = ?
            """,
            (opportunity_id, user_id),
        ).fetchone()
        if owned_opportunity is None:
            return 0

    get_db().execute("DELETE FROM bookmarks WHERE opportunity_id = ?", (opportunity_id,))
    get_db().execute("DELETE FROM applications WHERE opportunity_id = ?", (opportunity_id,))
    cursor = get_db().execute(
        "DELETE FROM opportunities WHERE id = ?",
        (opportunity_id,),
    )
    get_db().commit()
    return cursor.rowcount


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

    return errors
