from services.url_validation_service import normalize_profile_urls, normalize_public_url


def test_normalize_public_url_accepts_https_url():
    normalized, error = normalize_public_url(
        "https://example.com/path?x=1",
        "URL",
    )

    assert error == ""
    assert normalized == "https://example.com/path?x=1"


def test_normalize_public_url_rejects_javascript_scheme():
    normalized, error = normalize_public_url("javascript:alert(1)", "URL")

    assert normalized == "javascript:alert(1)"
    assert "tidak valid" in error


def test_normalize_public_url_rejects_localhost():
    _normalized, error = normalize_public_url("https://localhost/admin", "URL")

    assert "host lokal atau privat" in error


def test_normalize_public_url_rejects_private_ip():
    _normalized, error = normalize_public_url("http://192.168.1.10/admin", "URL")

    assert "host lokal atau privat" in error


def test_normalize_profile_urls_normalizes_bare_social_urls():
    form_data = {
        "linkedin": "linkedin.com/in/example",
        "github": "github.com/example",
        "portfolio_url": "portfolio.example.com",
    }

    errors = normalize_profile_urls(form_data)

    assert errors == []
    assert form_data["linkedin"] == "https://linkedin.com/in/example"
    assert form_data["github"] == "https://github.com/example"
    assert form_data["portfolio_url"] == "https://portfolio.example.com"


def test_normalize_profile_urls_rejects_wrong_social_domain():
    form_data = {
        "linkedin": "github.com/not-linkedin",
        "github": "",
        "portfolio_url": "",
    }

    errors = normalize_profile_urls(form_data)

    assert errors == ["LinkedIn harus memakai domain linkedin.com."]
