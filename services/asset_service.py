import json
from pathlib import Path

from flask import current_app, url_for


_MANIFEST_CACHE = {
    "path": None,
    "mtime": None,
    "assets": {},
}


def _manifest_path():
    return Path(current_app.config["ASSET_MANIFEST_PATH"])


def _read_manifest():
    path = _manifest_path()
    if not path.exists():
        return {}

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}

    if _MANIFEST_CACHE["path"] == path and _MANIFEST_CACHE["mtime"] == mtime:
        return _MANIFEST_CACHE["assets"]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        assets = {}
    else:
        assets = payload.get("assets", {})

    _MANIFEST_CACHE.update({"path": path, "mtime": mtime, "assets": assets})
    return assets


def asset_url(filename):
    asset_filename = filename
    if current_app.config.get("USE_BUILT_ASSETS"):
        asset_filename = _read_manifest().get(filename, filename)

    return url_for("static", filename=asset_filename)
