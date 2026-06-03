import csv
import io
import re
from datetime import datetime

from flask import Response, abort, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from repositories import recruiter_repository, user_repository
from services.application_service import application_status_label
from services.auth_service import get_current_role
from services.constants import (
    APPLICANT_SORT_OPTIONS,
    APPLICANT_SORT_RECENT,
    APPLICANT_SORT_SKILL_MATCH,
    JAKARTA_TZ,
)
from services.scoring_service import calculate_skill_match_score


def _raise_sqlalchemy_error(exc):
    db.session.rollback()
    raise exc


def get_recruiter_opportunity_or_404(opportunity_id):
    current_role = get_current_role()
    row = recruiter_repository.find_opportunity_row(
        opportunity_id,
        current_role=current_role,
        recruiter_id=session.get("user_id"),
    )

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
    if opportunity_id is not None:
        get_recruiter_opportunity_or_404(opportunity_id)

    rows = recruiter_repository.list_applicant_rows(
        current_role=current_role,
        recruiter_id=session.get("user_id"),
        opportunity_id=opportunity_id,
    )
    return enrich_recruiter_applicant_rows(rows, normalize_applicant_sort(sort_by))


def get_recruiter_application_or_404(application_id):
    current_role = get_current_role()
    application = recruiter_repository.find_application_detail_row(
        application_id,
        current_role=current_role,
        recruiter_id=session.get("user_id"),
    )

    if application is None:
        abort(404)

    return application


def get_recruiter_summary(recruiter_id, recent_limit):
    return {
        "total_opportunities": recruiter_repository.count_opportunities_by_recruiter(
            recruiter_id
        ),
        "total_applicants": recruiter_repository.count_applicants_by_recruiter(
            recruiter_id
        ),
        "recent_opportunities": recruiter_repository.list_opportunity_rows_by_recruiter(
            recruiter_id,
            limit=recent_limit,
        ),
    }


def get_recruiter_opportunity_rows(recruiter_id):
    return recruiter_repository.list_opportunity_rows_by_recruiter(recruiter_id)


def get_applicant_document_rows(applicant_user_id):
    return recruiter_repository.list_document_rows_by_user(applicant_user_id)


def is_recruiter_email_taken(email, recruiter_id):
    return user_repository.email_exists(email, exclude_user_id=recruiter_id)


def update_recruiter_profile(user_id, fields):
    try:
        return user_repository.update_profile(user_id, fields)
    except SQLAlchemyError as exc:
        _raise_sqlalchemy_error(exc)


def bulk_update_applicant_status(
    application_ids,
    status,
    *,
    opportunity_id=None,
):
    try:
        return recruiter_repository.bulk_update_application_status(
            application_ids,
            status,
            current_role=get_current_role(),
            recruiter_id=session.get("user_id"),
            opportunity_id=opportunity_id,
        )
    except SQLAlchemyError as exc:
        _raise_sqlalchemy_error(exc)


def update_applicant_status(application_id, status):
    try:
        return recruiter_repository.update_application_status(
            application_id,
            status,
            current_role=get_current_role(),
            recruiter_id=session.get("user_id"),
        )
    except SQLAlchemyError as exc:
        _raise_sqlalchemy_error(exc)


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
