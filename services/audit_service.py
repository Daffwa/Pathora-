from flask import current_app, has_request_context, request, session
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from repositories import audit_repository
from services.rate_limit_service import request_ip_address


def _request_metadata():
    if not has_request_context():
        return "", ""
    return request_ip_address(), request.headers.get("User-Agent", "")[:255]


def record_audit_event(
    action,
    target_type="",
    target_id=None,
    metadata=None,
    user_id=None,
    commit=True,
):
    actor_id = user_id if user_id is not None else session.get("user_id")
    ip_address, user_agent = _request_metadata()
    try:
        audit_repository.create_audit_log(
            user_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            commit=commit,
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.warning("Audit log write failed for %s: %s", action, exc)
