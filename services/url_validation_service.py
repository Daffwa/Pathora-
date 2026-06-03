from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit


SAFE_URL_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost"}


def normalize_public_url(value, field_label, allowed_domains=None):
    raw_value = (value or "").strip()
    if not raw_value:
        return "", ""

    if any(character.isspace() for character in raw_value):
        return raw_value, f"{field_label} tidak boleh mengandung spasi."

    candidate = raw_value if "://" in raw_value else f"https://{raw_value}"

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return raw_value, f"{field_label} tidak valid."

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").strip(".").lower()
    if scheme not in SAFE_URL_SCHEMES:
        return raw_value, f"{field_label} hanya boleh memakai http atau https."
    if not hostname:
        return raw_value, f"{field_label} harus berisi host/domain."
    if parsed.username or parsed.password:
        return raw_value, f"{field_label} tidak boleh berisi kredensial."
    if _is_blocked_host(hostname):
        return raw_value, f"{field_label} tidak boleh memakai host lokal atau privat."
    if allowed_domains and not _host_matches_allowed_domain(hostname, allowed_domains):
        allowed_text = ", ".join(allowed_domains)
        return raw_value, f"{field_label} harus memakai domain {allowed_text}."

    netloc = hostname
    if port is not None:
        netloc = f"{netloc}:{port}"

    normalized = urlunsplit(
        (
            scheme,
            netloc,
            parsed.path or "",
            parsed.query or "",
            "",
        )
    )
    return normalized, ""


def normalize_profile_urls(form_data):
    errors = []
    field_rules = (
        ("linkedin", "LinkedIn", ("linkedin.com",)),
        ("github", "GitHub", ("github.com",)),
        ("portfolio_url", "Portfolio URL", None),
    )
    for field_name, label, allowed_domains in field_rules:
        if field_name not in form_data:
            continue
        normalized, error = normalize_public_url(
            form_data[field_name],
            label,
            allowed_domains,
        )
        form_data[field_name] = normalized
        if error:
            errors.append(error)
    return errors


def _is_blocked_host(hostname):
    if hostname in BLOCKED_HOSTS or hostname.endswith(".localhost"):
        return True

    try:
        parsed_ip = ip_address(hostname)
    except ValueError:
        return False

    return (
        parsed_ip.is_loopback
        or parsed_ip.is_private
        or parsed_ip.is_link_local
        or parsed_ip.is_multicast
        or parsed_ip.is_reserved
        or parsed_ip.is_unspecified
    )


def _host_matches_allowed_domain(hostname, allowed_domains):
    for allowed_domain in allowed_domains:
        domain = allowed_domain.lower()
        if hostname == domain or hostname.endswith(f".{domain}"):
            return True
    return False
