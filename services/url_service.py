from urllib.parse import urljoin

from flask import current_app, url_for


def build_public_url(endpoint, **values):
    public_base_url = current_app.config.get("PUBLIC_BASE_URL")
    if public_base_url:
        path = url_for(endpoint, _external=False, **values)
        return urljoin(f"{public_base_url.rstrip('/')}/", path.lstrip("/"))

    return url_for(endpoint, _external=True, **values)
