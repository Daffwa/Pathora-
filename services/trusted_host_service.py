from urllib.parse import urlsplit

from flask import abort, current_app, request


def _normalize_hostname(host_value):
    if not host_value:
        return ""

    try:
        hostname = urlsplit(f"//{host_value}").hostname
    except ValueError:
        return ""

    return (hostname or "").strip(".").lower()


def _host_matches(hostname, trusted_host):
    trusted = trusted_host.strip().lower()
    if not trusted:
        return False
    if trusted.startswith("*."):
        suffix = trusted[2:]
        return hostname == suffix or hostname.endswith(f".{suffix}")
    if trusted.startswith("."):
        suffix = trusted[1:]
        return hostname == suffix or hostname.endswith(trusted)
    return hostname == _normalize_hostname(trusted)


def is_trusted_host(host_value, trusted_hosts):
    hostname = _normalize_hostname(host_value)
    if not hostname:
        return False

    return any(_host_matches(hostname, trusted_host) for trusted_host in trusted_hosts)


def register_trusted_hosts(app):
    @app.before_request
    def enforce_trusted_host():
        trusted_hosts = current_app.config.get("TRUSTED_HOSTS", ())
        if trusted_hosts and not is_trusted_host(request.host, trusted_hosts):
            abort(400)
