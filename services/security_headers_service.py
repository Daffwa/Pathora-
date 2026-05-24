from flask import current_app


def build_content_security_policy():
    directives = {
        "default-src": ["'self'"],
        "base-uri": ["'self'"],
        "connect-src": ["'self'"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
        "img-src": ["'self'", "data:"],
        "object-src": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
    }

    if current_app.config.get("SESSION_COOKIE_SECURE"):
        directives["upgrade-insecure-requests"] = []

    return "; ".join(
        " ".join([name, *values]).strip()
        for name, values in directives.items()
    )


def apply_security_headers(response):
    response.headers.setdefault(
        "Content-Security-Policy",
        build_content_security_policy(),
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), geolocation=(), microphone=()",
    )
    return response


def register_security_headers(app):
    app.after_request(apply_security_headers)
