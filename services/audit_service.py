import json
import sqlite3

from flask import current_app, has_request_context, request, session

from services.database_service import get_db


def _request_metadata():
    if not has_request_context():
        return "", ""
    return request.headers.get("X-Forwarded-For", request.remote_addr or ""), (
        request.headers.get("User-Agent", "")[:255]
    )


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
        get_db().execute(
            """
            INSERT INTO audit_logs
                (user_id, action, target_type, target_id, metadata, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor_id,
                action,
                target_type,
                target_id,
                json.dumps(metadata or {}, sort_keys=True),
                ip_address,
                user_agent,
            ),
        )
        if commit:
            get_db().commit()
    except sqlite3.Error as exc:
        current_app.logger.warning("Audit log write failed for %s: %s", action, exc)
