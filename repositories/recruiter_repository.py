from collections.abc import Mapping

from sqlalchemy import func, select, update

from extensions import db
from models import ApplicationORM, DocumentORM, OpportunityORM, UserORM
from repositories import opportunity_repository


class RecruiterRow(Mapping):
    def __init__(self, values):
        self._values = dict(values)

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __getattr__(self, name):
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def find_opportunity_row(opportunity_id, current_role=None, recruiter_id=None):
    query = select(OpportunityORM).where(OpportunityORM.id == opportunity_id)
    if current_role == "recruiter":
        query = query.where(OpportunityORM.created_by == recruiter_id)

    opportunity = db.session.execute(query).scalar_one_or_none()
    return opportunity_repository.as_opportunity_row(opportunity)


def count_opportunities_by_recruiter(recruiter_id):
    return db.session.execute(
        select(func.count())
        .select_from(OpportunityORM)
        .where(OpportunityORM.created_by == recruiter_id)
    ).scalar_one()


def count_applicants_by_recruiter(recruiter_id):
    return db.session.execute(
        select(func.count())
        .select_from(ApplicationORM)
        .join(OpportunityORM, OpportunityORM.id == ApplicationORM.opportunity_id)
        .where(OpportunityORM.created_by == recruiter_id)
    ).scalar_one()


def list_opportunity_rows_by_recruiter(recruiter_id, limit=None):
    query = (
        select(OpportunityORM, func.count(ApplicationORM.id).label("applicant_count"))
        .outerjoin(ApplicationORM, ApplicationORM.opportunity_id == OpportunityORM.id)
        .where(OpportunityORM.created_by == recruiter_id)
        .group_by(OpportunityORM.id)
        .order_by(OpportunityORM.updated_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)

    rows = db.session.execute(query).all()
    return [
        opportunity_repository.as_opportunity_row(
            opportunity,
            applicant_count=applicant_count,
        )
        for opportunity, applicant_count in rows
    ]


def list_applicant_rows(current_role=None, recruiter_id=None, opportunity_id=None):
    query = (
        select(ApplicationORM, UserORM, OpportunityORM)
        .join(OpportunityORM, OpportunityORM.id == ApplicationORM.opportunity_id)
        .join(UserORM, UserORM.id == ApplicationORM.user_id)
        .order_by(ApplicationORM.updated_at.desc())
    )

    if current_role == "recruiter":
        query = query.where(OpportunityORM.created_by == recruiter_id)
    if opportunity_id is not None:
        query = query.where(OpportunityORM.id == opportunity_id)

    rows = db.session.execute(query).all()
    return [
        _applicant_row(application, applicant, opportunity)
        for application, applicant, opportunity in rows
    ]


def find_application_detail_row(application_id, current_role=None, recruiter_id=None):
    query = (
        select(ApplicationORM, UserORM, OpportunityORM)
        .join(OpportunityORM, OpportunityORM.id == ApplicationORM.opportunity_id)
        .join(UserORM, UserORM.id == ApplicationORM.user_id)
        .where(ApplicationORM.id == application_id)
    )

    if current_role == "recruiter":
        query = query.where(OpportunityORM.created_by == recruiter_id)

    row = db.session.execute(query).first()
    if row is None:
        return None

    application, applicant, opportunity = row
    return _applicant_row(application, applicant, opportunity)


def list_document_rows_by_user(user_id):
    documents = db.session.execute(
        select(DocumentORM)
        .where(DocumentORM.user_id == user_id)
        .order_by(DocumentORM.doc_type.asc())
    ).scalars().all()
    return [
        RecruiterRow(
            {
                "doc_type": document.doc_type,
                "is_uploaded": document.is_uploaded,
                "updated_at": document.updated_at,
            }
        )
        for document in documents
    ]


def bulk_update_application_status(
    application_ids,
    status,
    *,
    current_role=None,
    recruiter_id=None,
    opportunity_id=None,
    commit=True,
):
    if not application_ids:
        return 0

    ownership_query = select(OpportunityORM.id).where(
        OpportunityORM.id == ApplicationORM.opportunity_id
    )
    if current_role == "recruiter":
        ownership_query = ownership_query.where(OpportunityORM.created_by == recruiter_id)
    if opportunity_id is not None:
        ownership_query = ownership_query.where(OpportunityORM.id == opportunity_id)

    result = db.session.execute(
        update(ApplicationORM)
        .where(
            ApplicationORM.id.in_(application_ids),
            ownership_query.exists(),
        )
        .values(status=status, updated_at=func.current_timestamp())
    )
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return result.rowcount or 0


def update_application_status(
    application_id,
    status,
    *,
    current_role=None,
    recruiter_id=None,
    commit=True,
):
    return bulk_update_application_status(
        [application_id],
        status,
        current_role=current_role,
        recruiter_id=recruiter_id,
        commit=commit,
    )


def _applicant_row(application, applicant, opportunity):
    return RecruiterRow(
        {
            "application_id": application.id,
            "applicant_user_id": application.user_id,
            "status": application.status,
            "notes": application.notes,
            "applied_at": application.applied_at,
            "updated_at": application.updated_at,
            "applicant_name": applicant.name,
            "applicant_email": applicant.email,
            "applicant_skills": applicant.skills,
            "opportunity_id": opportunity.id,
            "opportunity_title": opportunity.title,
            "opportunity_provider": opportunity.provider,
            "opportunity_location": opportunity.location,
            "opportunity_deadline": opportunity.deadline,
            "required_skills": opportunity.required_skills,
        }
    )
