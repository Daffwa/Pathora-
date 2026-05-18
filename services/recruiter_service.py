import csv
import io
import re
from datetime import datetime

from flask import Response, abort, session, url_for

from services.application_service import application_status_label
from services.auth_service import get_current_role
from services.constants import (
    APPLICANT_SORT_OPTIONS,
    APPLICANT_SORT_RECENT,
    APPLICANT_SORT_SKILL_MATCH,
    JAKARTA_TZ,
)
from services.database_service import get_db
from services.scoring_service import calculate_skill_match_score


def get_recruiter_opportunity_or_404(opportunity_id):
    current_role = get_current_role()
    params = [opportunity_id]
    owner_filter = ""
    if current_role == "recruiter":
        owner_filter = "AND created_by = ?"
        params.append(session["user_id"])

    row = get_db().execute(
        f"""
        SELECT * FROM opportunities
        WHERE id = ?
        {owner_filter}
        """,
        params,
    ).fetchone()

    if row is None:
        abort(404)

    return row


def normalize_applicant_sort(sort_value):
    return sort_value if sort_value in APPLICANT_SORT_OPTIONS else APPLICANT_SORT_RECENT


def get_applicant_list_url(opportunity_id=None, sort_by=None):
    route_args = {}
    if opportunity_id is not None:
        route_args["opportunity_id"] = opportunity_id
        endpoint = "recruiter_opportunity_applicants"
    else:
        endpoint = "recruiter_applicants"

    if sort_by == APPLICANT_SORT_SKILL_MATCH:
        route_args["sort"] = sort_by

    return url_for(endpoint, **route_args)


def enrich_recruiter_applicant_rows(rows, sort_by=APPLICANT_SORT_RECENT):
    applicants = []
    for row in rows:
        applicant = dict(row)
        applicant["skill_match_score"] = calculate_skill_match_score(
            applicant.get("applicant_skills", ""),
            applicant.get("required_skills", ""),
        )
        applicants.append(applicant)

    if sort_by == APPLICANT_SORT_SKILL_MATCH:
        applicants.sort(
            key=lambda applicant: (
                applicant["skill_match_score"],
                applicant.get("updated_at") or "",
                applicant["application_id"],
            ),
            reverse=True,
        )

    return applicants


def get_recruiter_applicant_rows(opportunity_id=None, sort_by=APPLICANT_SORT_RECENT):
    current_role = get_current_role()
    filters = []
    params = []

    if current_role == "recruiter":
        filters.append("opportunities.created_by = ?")
        params.append(session["user_id"])

    if opportunity_id is not None:
        get_recruiter_opportunity_or_404(opportunity_id)
        filters.append("opportunities.id = ?")
        params.append(opportunity_id)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    rows = get_db().execute(
        f"""
        SELECT
            applications.id AS application_id,
            applications.status,
            applications.notes,
            applications.applied_at,
            applications.updated_at,
            users.name AS applicant_name,
            users.email AS applicant_email,
            users.skills AS applicant_skills,
            opportunities.id AS opportunity_id,
            opportunities.title AS opportunity_title,
            opportunities.deadline AS opportunity_deadline,
            opportunities.required_skills
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        JOIN users ON users.id = applications.user_id
        {where_clause}
        ORDER BY applications.updated_at DESC
        """,
        params,
    ).fetchall()

    return enrich_recruiter_applicant_rows(rows, normalize_applicant_sort(sort_by))


def get_recruiter_application_or_404(application_id):
    current_role = get_current_role()
    params = [application_id]
    owner_filter = ""

    if current_role == "recruiter":
        owner_filter = "AND opportunities.created_by = ?"
        params.append(session["user_id"])

    application = get_db().execute(
        f"""
        SELECT
            applications.id AS application_id,
            applications.user_id AS applicant_user_id,
            applications.status,
            applications.notes,
            applications.applied_at,
            applications.updated_at,
            users.name AS applicant_name,
            users.email AS applicant_email,
            users.skills AS applicant_skills,
            opportunities.id AS opportunity_id,
            opportunities.title AS opportunity_title,
            opportunities.provider AS opportunity_provider,
            opportunities.location AS opportunity_location,
            opportunities.deadline AS opportunity_deadline
        FROM applications
        JOIN opportunities ON opportunities.id = applications.opportunity_id
        JOIN users ON users.id = applications.user_id
        WHERE applications.id = ?
        {owner_filter}
        """,
        params,
    ).fetchone()

    if application is None:
        abort(404)

    return application


def parse_positive_int(value):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None

    return parsed_value if parsed_value > 0 else None


def make_recruiter_applicants_csv(applicants, opportunity=None):
    output = io.StringIO(newline="")
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Nama Pelamar",
            "Email",
            "Lowongan",
            "Status",
            "Skill Match %",
            "Tanggal Daftar",
            "Terakhir Update",
            "Deadline Lowongan",
        ]
    )

    for applicant in applicants:
        writer.writerow(
            [
                applicant["applicant_name"],
                applicant["applicant_email"],
                applicant["opportunity_title"],
                application_status_label(applicant["status"]),
                applicant["skill_match_score"],
                applicant["applied_at"],
                applicant["updated_at"],
                applicant["opportunity_deadline"],
            ]
        )

    export_target = opportunity["title"] if opportunity else "semua-pelamar"
    filename_part = re.sub(r"[^A-Za-z0-9_-]+", "-", export_target).strip("-").lower()
    filename_part = filename_part or "pelamar"
    exported_at = datetime.now(JAKARTA_TZ).strftime("%Y%m%d")
    filename = f"pathora-{filename_part}-{exported_at}.csv"

    return Response(
        output.getvalue(),
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
