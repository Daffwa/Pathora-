from time import monotonic

from flask import request, session


_REQUEST_BUCKETS = {}


def client_identifier():
    user_id = session.get("user_id")
    if user_id:
        return f"user:{user_id}"
    return f"ip:{request.remote_addr or 'unknown'}"


def check_rate_limit(scope, limit, window_seconds):
    now = monotonic()
    key = (scope, client_identifier())
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


def reset_rate_limits():
    _REQUEST_BUCKETS.clear()
