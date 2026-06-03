from ipaddress import ip_address, ip_network
from time import monotonic, time

from flask import current_app, has_app_context, request, session
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RateLimitBucketORM


_REQUEST_BUCKETS = {}


def _normalize_ip(value):
    return (value or "").strip().strip("[]")


def _is_trusted_proxy(remote_addr):
    remote_ip = _normalize_ip(remote_addr)
    trusted_proxies = current_app.config.get("TRUSTED_PROXY_IPS", ())
    if not remote_ip or not trusted_proxies:
        return False

    try:
        parsed_remote_ip = ip_address(remote_ip)
    except ValueError:
        return False

    for trusted_proxy in trusted_proxies:
        try:
            if parsed_remote_ip in ip_network(trusted_proxy, strict=False):
                return True
        except ValueError:
            if remote_ip == trusted_proxy:
                return True
    return False


def request_ip_address():
    remote_addr = request.remote_addr or "unknown"
    if _is_trusted_proxy(remote_addr):
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        forwarded_ip = _normalize_ip(forwarded_for.split(",", 1)[0])
        try:
            ip_address(forwarded_ip)
        except ValueError:
            return remote_addr
        return forwarded_ip

    return remote_addr


def client_identifier():
    user_id = session.get("user_id")
    if user_id:
        return f"user:{user_id}"
    return f"ip:{request_ip_address()}"


def ip_identifier():
    return f"ip:{request_ip_address()}"


def account_identifier(email):
    normalized_email = (email or "").strip().lower()
    return f"account:{normalized_email or 'empty'}"


def check_rate_limit(scope, limit, window_seconds, identifier=None):
    if limit <= 0:
        return True, 0

    effective_identifier = identifier or client_identifier()
    backend = current_app.config.get("RATE_LIMIT_BACKEND", "memory")
    if backend == "database":
        return _check_database_rate_limit(
            scope,
            effective_identifier,
            limit,
            window_seconds,
        )

    return _check_memory_rate_limit(
        scope,
        effective_identifier,
        limit,
        window_seconds,
    )


def _check_memory_rate_limit(scope, identifier, limit, window_seconds):
    now = monotonic()
    key = (scope, identifier)
    bucket = [
        timestamp
        for timestamp in _REQUEST_BUCKETS.get(key, [])
        if now - timestamp < window_seconds
    ]

    if len(bucket) >= limit:
        retry_after = max(1, int(window_seconds - (now - bucket[0])))
        _REQUEST_BUCKETS[key] = bucket
        return False, retry_after

    bucket.append(now)
    _REQUEST_BUCKETS[key] = bucket
    return True, 0


def _check_database_rate_limit(scope, identifier, limit, window_seconds):
    now = time()
    cutoff = now - window_seconds
    try:
        db.session.execute(
            delete(RateLimitBucketORM).where(
                RateLimitBucketORM.scope == scope,
                RateLimitBucketORM.identifier == identifier,
                RateLimitBucketORM.created_at_epoch < cutoff,
            )
        )
        request_count = db.session.execute(
            select(func.count(RateLimitBucketORM.id)).where(
                RateLimitBucketORM.scope == scope,
                RateLimitBucketORM.identifier == identifier,
            )
        ).scalar_one()

        if request_count >= limit:
            oldest_timestamp = db.session.execute(
                select(RateLimitBucketORM.created_at_epoch)
                .where(
                    RateLimitBucketORM.scope == scope,
                    RateLimitBucketORM.identifier == identifier,
                )
                .order_by(RateLimitBucketORM.created_at_epoch.asc())
                .limit(1)
            ).scalar_one()
            db.session.commit()
            retry_after = max(1, int(window_seconds - (now - oldest_timestamp)))
            return False, retry_after

        db.session.add(
            RateLimitBucketORM(
                scope=scope,
                identifier=identifier,
                created_at_epoch=now,
            )
        )
        db.session.commit()
        return True, 0
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.warning("Rate limiter backend failed: %s", exc)
        return False, max(1, int(window_seconds))


def reset_rate_limits():
    _REQUEST_BUCKETS.clear()
    if not has_app_context():
        return

    try:
        db.session.execute(delete(RateLimitBucketORM))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
