from collections.abc import Mapping

from sqlalchemy import case, func, or_, select

from extensions import db
from models import AuditLogORM, OpportunityORM, UserORM


class AdminRow(Mapping):
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


def count_opportunities(opportunity_type=None):
    query = select(func.count()).select_from(OpportunityORM)
    if opportunity_type:
        query = query.where(OpportunityORM.type == opportunity_type)
    return db.session.execute(query).scalar_one()


def count_recruiters(account_status=None):
    query = select(func.count()).select_from(UserORM).where(UserORM.role == "recruiter")
    if account_status:
        query = query.where(UserORM.account_status == account_status)
    return db.session.execute(query).scalar_one()


def list_recent_activity(limit=6):
    rows = db.session.execute(
        select(AuditLogORM, UserORM.name.label("actor_name"))
        .outerjoin(UserORM, UserORM.id == AuditLogORM.user_id)
        .order_by(AuditLogORM.created_at.desc(), AuditLogORM.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminRow(
            {
                "action": audit_log.action,
                "target_type": audit_log.target_type,
                "target_id": audit_log.target_id,
                "created_at": audit_log.created_at,
                "actor_name": actor_name,
            }
        )
        for audit_log, actor_name in rows
    ]


def list_audit_logs(action="", query_text="", limit=100):
    query = (
        select(
            AuditLogORM,
            UserORM.name.label("actor_name"),
            UserORM.email.label("actor_email"),
        )
        .outerjoin(UserORM, UserORM.id == AuditLogORM.user_id)
        .order_by(AuditLogORM.created_at.desc(), AuditLogORM.id.desc())
        .limit(limit)
    )

    if action:
        query = query.where(AuditLogORM.action == action)

    if query_text:
        like_query = f"%{query_text}%"
        query = query.where(
            or_(
                AuditLogORM.action.like(like_query),
                AuditLogORM.target_type.like(like_query),
                UserORM.name.like(like_query),
                UserORM.email.like(like_query),
            )
        )

    rows = db.session.execute(query).all()
    return [
        AdminRow(
            {
                "id": audit_log.id,
                "action": audit_log.action,
                "target_type": audit_log.target_type,
                "target_id": audit_log.target_id,
                "metadata": audit_log.metadata_json,
                "ip_address": audit_log.ip_address,
                "created_at": audit_log.created_at,
                "actor_name": actor_name,
                "actor_email": actor_email,
            }
        )
        for audit_log, actor_name, actor_email in rows
    ]


def list_audit_actions():
    return db.session.execute(
        select(AuditLogORM.action)
        .distinct()
        .order_by(AuditLogORM.action.asc())
    ).scalars().all()


def list_recruiter_rows():
    status_order = case(
        (UserORM.account_status == "pending", 0),
        (UserORM.account_status == "approved", 1),
        else_=2,
    )
    recruiters = db.session.execute(
        select(UserORM)
        .where(UserORM.role == "recruiter")
        .order_by(status_order, UserORM.created_at.desc())
    ).scalars().all()
    return [
        AdminRow(
            {
                "id": recruiter.id,
                "name": recruiter.name,
                "email": recruiter.email,
                "company_name": recruiter.company_name,
                "company_position": recruiter.company_position,
                "account_status": recruiter.account_status,
                "created_at": recruiter.created_at,
            }
        )
        for recruiter in recruiters
    ]


def find_recruiter_status_row(user_id):
    recruiter = db.session.execute(
        select(UserORM.id, UserORM.account_status).where(
            UserORM.id == user_id,
            UserORM.role == "recruiter",
        )
    ).first()
    if recruiter is None:
        return None
    return AdminRow({"id": recruiter.id, "account_status": recruiter.account_status})


def update_recruiter_status(user_id, account_status, commit=True):
    recruiter = db.session.execute(
        select(UserORM).where(
            UserORM.id == user_id,
            UserORM.role == "recruiter",
        )
    ).scalar_one_or_none()
    if recruiter is None:
        return None

    recruiter.account_status = account_status
    recruiter.updated_at = func.current_timestamp()
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return recruiter
