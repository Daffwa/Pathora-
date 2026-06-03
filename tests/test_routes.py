import io
import json
import re

import pytest


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
PASSWORD_RESET_NEUTRAL_MESSAGE_BYTES = (
    b"Jika email terdaftar, link reset password akan dikirim."
)


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
        "/recruiter/profile",
        "/recruiter/profile/edit",
        "/recruiter/opportunities",
        "/recruiter/applicants",
        "/admin",
        "/admin/audit-logs",
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

    def test_ownership_and_audit_indexes_exist(self, app):
        expected_indexes = {
            "users": {
                "idx_users_role_account_status",
                "idx_users_account_status",
            },
            "opportunities": {
                "idx_opportunities_created_by_updated_at",
                "idx_opportunities_type",
            },
            "bookmarks": {
                "idx_bookmarks_user_saved_at",
                "idx_bookmarks_opportunity_id",
            },
            "applications": {
                "idx_applications_user_updated_at",
                "idx_applications_opportunity_id",
            },
            "documents": {
                "idx_documents_user_uploaded",
            },
            "chat_threads": {
                "idx_chat_threads_participant_one",
                "idx_chat_threads_participant_two",
            },
            "chat_messages": {
                "idx_chat_messages_thread_created_at",
                "idx_chat_messages_sender_id",
            },
            "audit_logs": {
                "idx_audit_logs_user_created_at",
                "idx_audit_logs_created_at_id",
                "idx_audit_logs_action_created_at",
                "idx_audit_logs_target",
            },
        }

        with app.app_context():
            from sqlalchemy import inspect

            from extensions import db

            for table_name, index_names in expected_indexes.items():
                actual_index_names = {
                    index["name"]
                    for index in inspect(db.engine).get_indexes(table_name)
                }
                assert index_names <= actual_index_names

    def test_database_initialization_creates_orm_schema(self, app):
        with app.app_context():
            from sqlalchemy import inspect

            from extensions import db

            inspector = inspect(db.engine)
            opportunity_columns = {
                column["name"]
                for column in inspector.get_columns("opportunities")
            }
            audit_indexes = {
                index["name"]
                for index in inspector.get_indexes("audit_logs")
            }

        assert {"created_by", "company_name", "official_link"} <= opportunity_columns
        assert {
            "idx_audit_logs_created_at_id",
            "idx_audit_logs_action_created_at",
            "idx_audit_logs_target",
        } <= audit_indexes

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

    def test_untrusted_host_is_rejected_before_routing(self, client, app):
        app.config["TRUSTED_HOSTS"] = ("pathora.example",)

        resp = client.get("/login", base_url="http://evil.example")

        assert resp.status_code == 400

    def test_forgot_password_reset_url_uses_public_base_url(self, client, app, monkeypatch):
        register_jobseeker(client, "reset-url@test.com", "Reset URL")
        app.config["PUBLIC_BASE_URL"] = "https://pathora.example"
        sent_urls = []

        from controllers import auth_controller

        monkeypatch.setattr(auth_controller, "get_mail_configuration_error", lambda: None)
        monkeypatch.setattr(
            auth_controller,
            "send_password_reset_email",
            lambda _email, _name, reset_url, _max_age: sent_urls.append(reset_url),
        )

        resp = post_form(
            client,
            "/forgot-password",
            data={"email": "reset-url@test.com"},
            csrf_url="/forgot-password",
        )

        assert resp.status_code == 200
        assert len(sent_urls) == 1
        assert sent_urls[0].startswith("https://pathora.example/reset-password/")
        assert "localhost" not in sent_urls[0]

    def test_forgot_password_rate_limits_per_account(self, client, app, monkeypatch):
        register_jobseeker(client, "limited-reset@test.com", "Limited Reset")
        app.config["FORGOT_PASSWORD_IP_RATE_LIMIT"] = 10
        app.config["FORGOT_PASSWORD_ACCOUNT_RATE_LIMIT"] = 1
        sent_urls = []

        from controllers import auth_controller

        monkeypatch.setattr(auth_controller, "get_mail_configuration_error", lambda: None)
        monkeypatch.setattr(
            auth_controller,
            "send_password_reset_email",
            lambda _email, _name, reset_url, _max_age: sent_urls.append(reset_url),
        )

        first = post_form(
            client,
            "/forgot-password",
            data={"email": "limited-reset@test.com"},
            csrf_url="/forgot-password",
            environ_overrides={"REMOTE_ADDR": "192.0.2.10"},
        )
        second = post_form(
            client,
            "/forgot-password",
            data={"email": "limited-reset@test.com"},
            csrf_url="/forgot-password",
            environ_overrides={"REMOTE_ADDR": "192.0.2.11"},
        )

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["Retry-After"]
        assert len(sent_urls) == 1
        assert PASSWORD_RESET_NEUTRAL_MESSAGE_BYTES in second.data

    def test_database_rate_limit_backend_blocks_second_request(self, app):
        app.config["RATE_LIMIT_BACKEND"] = "database"

        from services.rate_limit_service import check_rate_limit
        from extensions import db
        from models import RateLimitBucketORM
        from sqlalchemy import select, func

        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.0.2.20"}):
            allowed, retry_after = check_rate_limit("unit-test", 1, 300)
            assert allowed is True
            assert retry_after == 0

        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.0.2.20"}):
            allowed, retry_after = check_rate_limit("unit-test", 1, 300)
            assert allowed is False
            assert retry_after > 0

        with app.app_context():
            count = db.session.execute(
                select(func.count(RateLimitBucketORM.id)).where(
                    RateLimitBucketORM.scope == "unit-test"
                )
            ).scalar_one()
            assert count == 1

    def test_forwarded_for_only_used_for_trusted_proxy(self, app):
        from services.rate_limit_service import ip_identifier

        headers = {"X-Forwarded-For": "198.51.100.25, 10.0.0.5"}
        with app.test_request_context(
            "/",
            headers=headers,
            environ_base={"REMOTE_ADDR": "10.0.0.5"},
        ):
            app.config["TRUSTED_PROXY_IPS"] = ()
            assert ip_identifier() == "ip:10.0.0.5"

            app.config["TRUSTED_PROXY_IPS"] = ("10.0.0.0/8",)
            assert ip_identifier() == "ip:198.51.100.25"

    def test_non_local_environment_requires_security_env(self, monkeypatch):
        from config import PRODUCTION_REQUIRED_ENV_VARS, validate_required_production_environment

        monkeypatch.setenv("APP_ENV", "production")
        for env_name in PRODUCTION_REQUIRED_ENV_VARS:
            monkeypatch.delenv(env_name, raising=False)
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
        monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)

        with pytest.raises(RuntimeError, match="Missing required production"):
            validate_required_production_environment()

    def test_railway_public_domain_satisfies_public_base_url(self, monkeypatch):
        from config import (
            PRODUCTION_REQUIRED_ENV_VARS,
            build_trusted_hosts,
            get_public_base_url,
            validate_required_production_environment,
        )

        monkeypatch.setenv("APP_ENV", "production")
        for env_name in PRODUCTION_REQUIRED_ENV_VARS:
            monkeypatch.setenv(env_name, f"test-{env_name.lower()}")
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
        monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "pathora.up.railway.app")

        validate_required_production_environment()
        public_base_url = get_public_base_url()
        assert public_base_url == "https://pathora.up.railway.app"
        assert "pathora.up.railway.app" in build_trusted_hosts(public_base_url)

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

    def test_jobseeker_cannot_access_recruiter_profile(self, client):
        register_jobseeker(client, "js-profile@test.com", "JS Profile")
        resp = client.get("/recruiter/profile", follow_redirects=False)
        assert resp.status_code == 403

    def test_jobseeker_cannot_access_recruiter_edit_profile(self, client):
        register_jobseeker(client, "js-edit-rec-profile@test.com", "JS Edit Profile")
        resp = client.get("/recruiter/profile/edit", follow_redirects=False)
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

    def test_admin_dashboard_shows_actionable_overview(self, client):
        login_admin(client)
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert b"Dashboard Admin" in resp.data
        assert b"Kelola Recruiter" in resp.data
        assert b"/admin/recruiters" in resp.data
        assert b"/admin/audit-logs" in resp.data
        assert b"Aktivitas Terbaru" in resp.data
        assert b"Fokus Admin" in resp.data

    def test_admin_can_view_audit_logs(self, client):
        login_admin(client)
        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        assert b"Audit Log" in resp.data
        assert b"auth.login" in resp.data

    def test_jobseeker_cannot_access_audit_logs(self, client):
        register_jobseeker(client, "audit-js@test.com", "Audit JS")
        resp = client.get("/admin/audit-logs", follow_redirects=False)
        assert resp.status_code == 403

    def test_admin_can_access_recruiter_applicants(self, client):
        login_admin(client)
        resp = client.get("/recruiter/applicants")
        assert resp.status_code == 200

    def test_recruiter_can_view_profile_from_avatar_menu(self, client, app):
        register_approved_recruiter(client, app, "profile-rec@test.com", "Profile Rec")

        dashboard_resp = client.get("/recruiter/dashboard")
        assert dashboard_resp.status_code == 200
        assert b"/recruiter/profile" in dashboard_resp.data
        assert b"Lihat Profil" in dashboard_resp.data

        profile_resp = client.get("/recruiter/profile")
        assert profile_resp.status_code == 200
        assert b"Profil Recruiter" in profile_resp.data
        assert b"/recruiter/profile/edit" in profile_resp.data
        assert b"PT Test" in profile_resp.data

    def test_recruiter_can_edit_profile(self, client, app):
        register_approved_recruiter(client, app, "edit-rec@test.com", "Edit Rec")

        edit_resp = client.get("/recruiter/profile/edit")
        assert edit_resp.status_code == 200
        assert b"Edit Profil Recruiter" in edit_resp.data

        resp = post_form(
            client,
            "/recruiter/profile/edit",
            data={
                "name": "Edited Recruiter",
                "email": "edited-rec@test.com",
                "phone": "08123456789",
                "domicile": "Jakarta",
                "bio": "Recruiter aktif di Pathora.",
                "linkedin": "linkedin.com/in/edited-rec",
                "portfolio_url": "https://company.example.com",
                "company_name": "PT Updated",
                "company_position": "Other",
                "company_position_other": "People Lead",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/recruiter/profile")

        with app.app_context():
            from repositories import user_repository

            recruiter = user_repository.find_by_email("edited-rec@test.com")
            assert recruiter.name == "Edited Recruiter"
            assert recruiter.phone == "08123456789"
            assert recruiter.domicile == "Jakarta"
            assert recruiter.company_name == "PT Updated"
            assert recruiter.company_position == "People Lead"
            assert recruiter.linkedin == "https://linkedin.com/in/edited-rec"

    def test_recruiter_profile_rejects_unsafe_urls(self, client, app):
        register_approved_recruiter(client, app, "unsafe-rec@test.com", "Unsafe Rec")

        resp = post_form(
            client,
            "/recruiter/profile/edit",
            data={
                "name": "Unsafe Recruiter",
                "email": "unsafe-rec@test.com",
                "company_name": "PT Unsafe",
                "company_position": "HRD",
                "linkedin": "javascript:alert(1)",
                "portfolio_url": "https://company.example.com",
            },
        )

        assert resp.status_code == 400
        assert b"LinkedIn" in resp.data

    def test_new_recruiter_is_auto_approved_and_can_access_features(self, client, app):
        resp = register_recruiter(client, "auto-rec@test.com", "Auto Recruiter")
        assert resp.status_code == 302
        assert client.get("/recruiter/dashboard").status_code == 200

        with app.app_context():
            from repositories import user_repository

            recruiter = user_repository.find_by_email("auto-rec@test.com")
            assert recruiter.account_status == "approved"

    def test_admin_can_update_recruiter_status(self, client, app):
        register_recruiter(client, "status-rec@test.com", "Status Rec")
        with app.app_context():
            from repositories import user_repository

            recruiter = user_repository.find_by_email("status-rec@test.com")

        post_form(client, "/logout", csrf_url="/recruiter/dashboard")
        login_admin(client)
        resp = post_form(
            client,
            f"/admin/recruiters/{recruiter.id}/status",
            csrf_url="/admin/recruiters",
            data={"account_status": "rejected"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        with app.app_context():
            from repositories import user_repository

            recruiter = user_repository.find_by_email("status-rec@test.com")
            assert recruiter.account_status == "rejected"

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
            from sqlalchemy import select

            from extensions import db
            from models import OpportunityORM

            opportunity = db.session.execute(
                select(OpportunityORM).where(OpportunityORM.title == "Private Owner Role")
            ).scalar_one()

        post_form(client, "/logout", csrf_url="/recruiter/dashboard")
        register_approved_recruiter(client, app, "other-rec@test.com", "Other Rec")

        edit_resp = client.get(
            f"/recruiter/opportunities/{opportunity.id}/edit",
            follow_redirects=False,
        )
        assert edit_resp.status_code == 404

        delete_resp = post_form(
            client,
            f"/recruiter/opportunities/{opportunity.id}/delete",
            csrf_url="/recruiter/opportunities",
            follow_redirects=False,
        )
        assert delete_resp.status_code == 404

        with app.app_context():
            from extensions import db
            from models import OpportunityORM

            still_exists = db.session.get(OpportunityORM, opportunity.id)
            assert still_exists is not None

    def test_opportunity_form_rejects_unsafe_official_link(self, client, app):
        register_approved_recruiter(client, app, "unsafe-link-rec@test.com", "Unsafe Link")

        resp = post_form(
            client,
            "/recruiter/opportunities/create",
            data={
                "title": "Unsafe Link Role",
                "opportunity_type": "internship",
                "provider": "PT Unsafe",
                "location": "Jakarta",
                "deadline": "2026-08-01",
                "description": "Unsafe link test",
                "requirements": "Safe applicants only",
                "official_link": "file:///etc/passwd",
                "required_skills": "python",
            },
        )

        assert resp.status_code == 400
        assert b"Tautan resmi" in resp.data

    def test_profile_edit_normalizes_safe_social_urls(self, client, app):
        register_jobseeker(client, "social-js@test.com", "Social JS")

        resp = post_form(
            client,
            "/profile/edit",
            data={
                "name": "Social JS",
                "email": "social-js@test.com",
                "linkedin": "linkedin.com/in/social-js",
                "github": "github.com/social-js",
                "portfolio_url": "portfolio.example.com",
            },
            follow_redirects=False,
        )

        assert resp.status_code == 302
        with app.app_context():
            from repositories import user_repository

            user = user_repository.find_by_email("social-js@test.com")
            assert user.linkedin == "https://linkedin.com/in/social-js"
            assert user.github == "https://github.com/social-js"
            assert user.portfolio_url == "https://portfolio.example.com"

    def test_profile_edit_rejects_local_portfolio_url(self, client):
        register_jobseeker(client, "local-url-js@test.com", "Local URL")

        resp = post_form(
            client,
            "/profile/edit",
            data={
                "name": "Local URL",
                "email": "local-url-js@test.com",
                "portfolio_url": "http://127.0.0.1:5000/admin",
            },
        )

        assert resp.status_code == 400
        assert b"Portfolio URL" in resp.data

    def test_jobseeker_cannot_remove_other_jobseeker_application(self, client, app):
        register_jobseeker(client, "owner-js@test.com", "Owner JS")
        post_form(
            client,
            "/opportunities/1/track",
            csrf_url="/opportunities/1",
            follow_redirects=False,
        )
        with app.app_context():
            from sqlalchemy import select

            from extensions import db
            from models import ApplicationORM, UserORM

            application = db.session.execute(
                select(ApplicationORM)
                .join(UserORM, UserORM.id == ApplicationORM.user_id)
                .where(UserORM.email == "owner-js@test.com")
            ).scalar_one()

        post_form(client, "/logout", csrf_url="/dashboard")
        register_jobseeker(client, "other-js@test.com", "Other JS")
        remove_resp = post_form(
            client,
            f"/applications/{application.id}/remove",
            csrf_url="/applications",
            follow_redirects=False,
        )
        assert remove_resp.status_code == 404

    def test_jobseeker_documents_page_only_shows_own_documents(self, client, app):
        register_jobseeker(client, "doc-owner@test.com", "Doc Owner")
        with app.app_context():
            from repositories import document_repository, user_repository

            owner = user_repository.find_by_email("doc-owner@test.com")
            document_repository.upsert_document(
                user_id=owner.id,
                doc_type="CV",
                file_name="private-owner-cv.pdf",
                file_path="owner.pdf",
                is_uploaded=True,
                notes="private",
            )

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
            "document_file": (io.BytesIO(PDF_BYTES), "test.pdf", "application/pdf"),
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

    def test_document_download_forces_attachment(self, client):
        register_jobseeker(client, "download@test.com", "Download User")
        post_form(
            client,
            "/documents/CV/update",
            csrf_url="/documents",
            data={
                "notes": "Test document",
                "document_file": (io.BytesIO(PDF_BYTES), "test.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        resp = client.get("/documents/CV/download")

        assert resp.status_code == 200
        assert resp.headers["Content-Disposition"].startswith("attachment;")

    def test_avatar_file_requires_owner(self, client, app):
        register_jobseeker(client, "avatar-owner@test.com", "Avatar Owner")
        post_form(
            client,
            "/profile/edit",
            csrf_url="/profile/edit",
            data={
                "name": "Avatar Owner",
                "email": "avatar-owner@test.com",
                "avatar_file": (io.BytesIO(PNG_BYTES), "avatar.png", "image/png"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        with app.app_context():
            from repositories import user_repository

            owner = user_repository.find_by_email("avatar-owner@test.com")
            avatar_path = owner.avatar_path

        assert avatar_path
        assert client.get(f"/uploads/avatars/{avatar_path}").status_code == 200

        post_form(client, "/logout", csrf_url="/profile")
        register_jobseeker(client, "avatar-other@test.com", "Avatar Other")

        resp = client.get(f"/uploads/avatars/{avatar_path}")

        assert resp.status_code == 404

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


class TestHelpVisibility:
    def test_jobseeker_help_hides_recruiter_and_admin_sections(self, client):
        register_jobseeker(client, "help-js@test.com", "Help JS")

        resp = client.get("/help?category=Recruiter&context=recruiter")

        assert resp.status_code == 200
        assert b"Recruiter melihat applicant" not in resp.data
        assert b"Recruiter mengubah status applicant" not in resp.data
        assert b"Admin mengelola peluang" not in resp.data
        assert b"category=Recruiter" not in resp.data
        assert b"category=Admin" not in resp.data
        assert b"/recruiter/applicants" not in resp.data
        assert b"Konteks: Recruiter" not in resp.data

    def test_recruiter_help_hides_admin_sections(self, client, app):
        register_approved_recruiter(client, app, "help-rec@test.com", "Help Rec")

        resp = client.get("/help?category=Admin&context=admin")

        assert resp.status_code == 200
        assert b"Admin mengelola peluang" not in resp.data
        assert b"category=Admin" not in resp.data
        assert b"Konteks: Admin" not in resp.data
        assert b"Recruiter melihat applicant" in resp.data

    def test_admin_help_keeps_admin_sections(self, client):
        login_admin(client)

        resp = client.get("/help?category=Admin&context=admin")

        assert resp.status_code == 200
        assert b"Admin mengelola peluang" in resp.data
        assert b"Konteks: Admin" in resp.data


class TestErrorHandlers:
    def test_404(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert resp.status_code == 404

    def test_404_template(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert b"404" in resp.data or resp.status_code == 404
