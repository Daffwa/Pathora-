import json

from sqlalchemy import select

from extensions import db
from models import AuditLogORM


def create_audit_log(
    *,
    action,
    target_type="",
    target_id=None,
    metadata=None,
    user_id=None,
    ip_address="",
    user_agent="",
    commit=True,
):
    audit_log = AuditLogORM(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=_serialize_metadata(metadata),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:255],
    )
    db.session.add(audit_log)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return audit_log


def list_recent(limit=50, action=None):
    query = select(AuditLogORM).order_by(AuditLogORM.created_at.desc(), AuditLogORM.id.desc())
    if action:
        query = query.where(AuditLogORM.action == action)
    return db.session.execute(query.limit(limit)).scalars().all()


def _serialize_metadata(metadata):
    if metadata is None:
        return "{}"
    if isinstance(metadata, str):
        return metadata
    return json.dumps(metadata, sort_keys=True)
