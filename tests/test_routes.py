import io
import json
import re

import pytest


def csrf_token_from(response):
    match = re.search(rb'name="_csrf_token"\s+value="([^"]+)"', response.data)
    assert match, "CSRF token field was not rendered."
    return match.group(1).decode("utf-8")


def get_csrf_token(client, url):
    response = client.get(url)
    assert response.status_code == 200
    return csrf_token_from(response)


def post_form(client, url, data=None, csrf_url=None, **kwargs):
    form_data = dict(data or {})
    form_data["_csrf_token"] = get_csrf_token(client, csrf_url or url)
    return client.post(url, data=form_data, **kwargs)


def register_jobseeker(client, email, name="Test Jobseeker"):
    return post_form(
        client,
        "/register",
        data={
            "name": name,
            "email": email,
            "password": "secret1234",
            "confirm_password": "secret1234",
            "role": "jobseeker",
            "skills": "python",
        },
    )


def register_recruiter(client, email, name="Test Recruiter"):
    return post_form(
        client,
        "/register",
        data={
            "name": name,
            "email": email,
            "password": "secret1234",
            "confirm_password": "secret1234",
            "role": "recruiter",
            "company_name": "PT Test",
            "company_position": "HRD",
        },
    )


def login_user(client, email, password="secret1234"):
    return post_form(
        client,
        "/login",
        data={"email": email, "password": password},
    )


def register_approved_recruiter(client, app, email, name="Test Recruiter"):
    return register_recruiter(client, email, name)


def login_admin(client, password="admin12345"):
    return post_form(
        client,
        "/login",
        data={"email": "admin@example.com", "password": password},
    )


class TestPublicRoutes:
    def test_index_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_login_render_200(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_register_render_200(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_opportunities_200(self, client):
        resp = client.get("/opportunities")
        assert resp.status_code == 200

    def test_opportunity_detail_200(self, client):
        resp = client.get("/opportunities/1")
        assert resp.status_code == 200


class TestProtectedRoutesRedirect:
    """All protected routes should redirect to login when no session."""

    PROTECTED_URLS = [
        "/dashboard",
        "/profile",
        "/profile/edit",
        "/documents",
        "/bookmarks",
        "/applications",
        "/chat",
        "/recruiter/dashboard",
        "/recruiter/opportunities",
        "/recruiter/applicants",
        "/admin",
        "/admin/opportunities",
        "/admin/opportunities/create",
    ]

    def test_each_protected_route(self, client):
        for url in self.PROTECTED_URLS:
            resp = client.get(url, follow_redirects=False)
            assert resp.status_code in (
                302,
                401,
            ), f"{url} returned {resp.status_code}, expected 302/401"


class TestSecurityHardening:
    def test_security_headers_are_set(self, client):
        resp = client.get("/login")
        csp = resp.headers["Content-Security-Policy"]

        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers["Permissions-Policy"]
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_session_cookie_is_hardened(self, client):
        resp = client.get("/login")
        cookie_header = "; ".join(resp.headers.getlist("Set-Cookie"))

        assert "HttpOnly" in cookie_header
        assert "SameSite=Lax" in cookie_header

    def test_asset_url_uses_built_manifest(self, app, tmp_path):
        manifest_path = tmp_path / "asset-manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "assets": {
                        "css/style.css": "dist/css/style.abc123.min.css",
                    }
                }
            ),
            encoding="utf-8",
        )
        app.config["USE_BUILT_ASSETS"] = True
        app.config["ASSET_MANIFEST_PATH"] = manifest_path

        with app.test_request_context("/"):
            from services.asset_service import asset_url

            assert asset_url("css/style.css").endswith(
                "/static/dist/css/style.abc123.min.css"
            )
            assert asset_url("js/missing.js").endswith("/static/js/missing.js")

    def test_post_without_csrf_is_rejected(self, client):
        resp = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
        )
        assert resp.status_code == 400

    def test_logout_get_does_not_clear_session(self, client):
        login_admin(client)
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert client.get("/admin").status_code == 200

    def test_assistant_health_requires_login(self, client):
        resp = client.get("/api/assistant/health")
        assert resp.status_code == 401

    def test_assistant_health_requires_admin(self, client):
        register_jobseeker(client, "health-user@test.com", "Health User")
        resp = client.get("/api/assistant/health")
        assert resp.status_code == 403

    def test_admin_can_read_assistant_health(self, client):
        login_admin(client)
        resp = client.get("/api/assistant/health")
        assert resp.status_code == 200
        assert "api_key_configured" in resp.get_json()

    def test_admin_password_is_required_in_production(self, monkeypatch):
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        monkeypatch.setenv("FLASK_ENV", "production")

        from services.database_service import get_admin_seed_credentials

        with pytest.raises(RuntimeError):
            get_admin_seed_credentials()

    def test_ai_assistant_falls_back_when_google_client_missing(self, app, monkeypatch):
        from routes import ai_routes

        monkeypatch.setattr(ai_routes, "GOOGLE_API_KEY", "configured")
        monkeypatch.setattr(ai_routes, "google_client", None)

        with app.app_context():
            answer, error, status = ai_routes._validate_and_generate("cara upload dokumen")

        assert error is None
        assert status is None
        assert "Kelola Dokumen" in answer

    def test_ai_assistant_falls_back_when_google_request_fails(self, app, monkeypatch):
        from routes import ai_routes

        class BrokenModels:
            def generate_content(self, **kwargs):
                raise RuntimeError("provider down")

        class BrokenClient:
            models = BrokenModels()

        monkeypatch.setattr(ai_routes, "GOOGLE_API_KEY", "configured")
        monkeypatch.setattr(ai_routes, "google_client", BrokenClient())

        with app.app_context():
            answer, error, status = ai_routes._validate_and_generate("test")

        assert error is None
        assert status is None
        assert "Pathora" in answer


class TestAuthFlow:
    def test_register_jobseeker(self, client):
        resp = post_form(
            client,
            "/register",
            data={
                "name": "Test Jobseeker",
                "email": "jobseeker@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python, sql, flask",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_register_recruiter(self, client):
        resp = post_form(
            client,
            "/register",
            data={
                "name": "Test Recruiter",
                "email": "recruiter@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "recruiter",
                "company_name": "PT Test",
                "company_position": "HRD",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_register_validation_empty_name(self, client):
        resp = post_form(
            client,
            "/register",
            data={
                "name": "",
                "email": "test@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
            },
        )
        assert resp.status_code == 400

    def test_register_validation_password_mismatch(self, client):
        resp = post_form(
            client,
            "/register",
            data={
                "name": "Test",
                "email": "test@test.com",
                "password": "secret1234",
                "confirm_password": "different",
                "role": "jobseeker",
            },
        )
        assert resp.status_code == 400

    def test_login_admin(self, client):
        resp = post_form(
            client,
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_login_wrong_password(self, client):
        resp = post_form(
            client,
            "/login",
            data={"email": "admin@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_wrong_email(self, client):
        resp = post_form(
            client,
            "/login",
            data={"email": "nonexistent@test.com", "password": "secret1234"},
        )
        assert resp.status_code == 401

    def test_logout(self, client):
        post_form(
            client,
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
        )
        resp = post_form(
            client,
            "/logout",
            csrf_url="/admin",
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_register_duplicate_email(self, client):
        post_form(
            client,
            "/register",
            data={
                "name": "First",
                "email": "dupe@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
            },
        )
        resp = post_form(
            client,
            "/register",
            data={
                "name": "Second",
                "email": "dupe@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
            },
        )
        assert resp.status_code == 409


class TestRoleAccess:
    def test_jobseeker_cannot_access_recruiter(self, client):
        register_jobseeker(client, "js@test.com", "JS User")
        resp = client.get("/recruiter/dashboard", follow_redirects=False)
        assert resp.status_code == 403

    def test_jobseeker_cannot_access_admin(self, client):
        register_jobseeker(client, "js2@test.com", "JS User")
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 403

    def test_recruiter_cannot_access_admin(self, client, app):
        register_approved_recruiter(client, app, "rec@test.com", "Rec Test")
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 403

    def test_admin_can_access_admin_dashboard(self, client):
        login_admin(client)
        resp = client.get("/admin")
        assert resp.status_code == 200

    def test_admin_can_access_recruiter_applicants(self, client):
        login_admin(client)
        resp = client.get("/recruiter/applicants")
        assert resp.status_code == 200

    def test_new_recruiter_is_auto_approved_and_can_access_features(self, client, app):
        resp = register_recruiter(client, "auto-rec@test.com", "Auto Recruiter")
        assert resp.status_code == 302
        assert client.get("/recruiter/dashboard").status_code == 200

        with app.app_context():
            from services.database_service import get_db

            recruiter = get_db().execute(
                "SELECT account_status FROM users WHERE email = ?",
                ("auto-rec@test.com",),
            ).fetchone()
            assert recruiter["account_status"] == "approved"

    def test_admin_can_update_recruiter_status(self, client, app):
        register_recruiter(client, "status-rec@test.com", "Status Rec")
        with app.app_context():
            from services.database_service import get_db

            recruiter = get_db().execute(
                "SELECT id FROM users WHERE email = ?",
                ("status-rec@test.com",),
            ).fetchone()

        post_form(client, "/logout", csrf_url="/recruiter/dashboard")
        login_admin(client)
        resp = post_form(
            client,
            f"/admin/recruiters/{recruiter['id']}/status",
            csrf_url="/admin/recruiters",
            data={"account_status": "rejected"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            recruiter = get_db().execute(
                "SELECT account_status FROM users WHERE email = ?",
                ("status-rec@test.com",),
            ).fetchone()
            assert recruiter["account_status"] == "rejected"

    def test_recruiter_cannot_manage_other_recruiter_opportunity(self, client, app):
        register_approved_recruiter(client, app, "owner-rec@test.com", "Owner Rec")
        create_resp = post_form(
            client,
            "/recruiter/opportunities/create",
            data={
                "title": "Private Owner Role",
                "opportunity_type": "internship",
                "provider": "PT Owner",
                "location": "Jakarta",
                "deadline": "2026-08-01",
                "description": "Owner only",
                "requirements": "Owner requirements",
                "official_link": "https://example.com",
                "required_skills": "python",
            },
            follow_redirects=False,
        )
        assert create_resp.status_code == 302

        with app.app_context():
            from services.database_service import get_db

            opportunity = get_db().execute(
                "SELECT id FROM opportunities WHERE title = ?",
                ("Private Owner Role",),
            ).fetchone()

        post_form(client, "/logout", csrf_url="/recruiter/dashboard")
        register_approved_recruiter(client, app, "other-rec@test.com", "Other Rec")

        edit_resp = client.get(
            f"/recruiter/opportunities/{opportunity['id']}/edit",
            follow_redirects=False,
        )
        assert edit_resp.status_code == 404

        delete_resp = post_form(
            client,
            f"/recruiter/opportunities/{opportunity['id']}/delete",
            csrf_url="/recruiter/opportunities",
            follow_redirects=False,
        )
        assert delete_resp.status_code == 404

        with app.app_context():
            from services.database_service import get_db

            still_exists = get_db().execute(
                "SELECT id FROM opportunities WHERE id = ?",
                (opportunity["id"],),
            ).fetchone()
            assert still_exists is not None

    def test_jobseeker_cannot_remove_other_jobseeker_application(self, client, app):
        register_jobseeker(client, "owner-js@test.com", "Owner JS")
        post_form(
            client,
            "/opportunities/1/track",
            csrf_url="/opportunities/1",
            follow_redirects=False,
        )
        with app.app_context():
            from services.database_service import get_db

            application = get_db().execute(
                """
                SELECT applications.id
                FROM applications
                JOIN users ON users.id = applications.user_id
                WHERE users.email = ?
                """,
                ("owner-js@test.com",),
            ).fetchone()

        post_form(client, "/logout", csrf_url="/dashboard")
        register_jobseeker(client, "other-js@test.com", "Other JS")
        remove_resp = post_form(
            client,
            f"/applications/{application['id']}/remove",
            csrf_url="/applications",
            follow_redirects=False,
        )
        assert remove_resp.status_code == 404

    def test_jobseeker_documents_page_only_shows_own_documents(self, client, app):
        register_jobseeker(client, "doc-owner@test.com", "Doc Owner")
        with app.app_context():
            from services.database_service import get_db

            owner = get_db().execute(
                "SELECT id FROM users WHERE email = ?",
                ("doc-owner@test.com",),
            ).fetchone()
            get_db().execute(
                """
                INSERT INTO documents
                    (user_id, doc_type, file_name, file_path, is_uploaded, notes)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (owner["id"], "CV", "private-owner-cv.pdf", "owner.pdf", "private"),
            )
            get_db().commit()

        post_form(client, "/logout", csrf_url="/dashboard")
        register_jobseeker(client, "doc-other@test.com", "Doc Other")
        resp = client.get("/documents")
        assert resp.status_code == 200
        assert b"private-owner-cv.pdf" not in resp.data


class TestAuthenticatedRoutes:
    def test_dashboard_after_login(self, client):
        register_jobseeker(client, "dash@test.com", "Dash User")
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_profile_after_login(self, client):
        register_jobseeker(client, "prof@test.com", "Prof User")
        resp = client.get("/profile")
        assert resp.status_code == 200

    def test_documents_after_login(self, client):
        register_jobseeker(client, "doc@test.com", "Doc User")
        resp = client.get("/documents")
        assert resp.status_code == 200

    def test_document_upload_smoke(self, client):
        register_jobseeker(client, "upload@test.com", "Upload User")
        data = {
            "notes": "Test document",
            "document_file": (io.BytesIO(b"%PDF-1.4 test"), "test.pdf"),
        }
        resp = post_form(
            client,
            "/documents/CV/update",
            csrf_url="/documents",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_bookmarks_after_login(self, client):
        register_jobseeker(client, "bm@test.com", "BM User")
        resp = client.get("/bookmarks")
        assert resp.status_code == 200

    def test_applications_after_login(self, client):
        register_jobseeker(client, "app@test.com", "App User")
        resp = client.get("/applications")
        assert resp.status_code == 200

    def test_chat_after_login(self, client):
        register_jobseeker(client, "chat@test.com", "Chat User")
        resp = client.get("/chat")
        assert resp.status_code == 200


class TestErrorHandlers:
    def test_404(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert resp.status_code == 404

    def test_404_template(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert b"404" in resp.data or resp.status_code == 404
