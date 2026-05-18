import io


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


class TestAuthFlow:
    def test_register_jobseeker(self, client):
        resp = client.post(
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
        resp = client.post(
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
        resp = client.post(
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
        resp = client.post(
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
        resp = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/login",
            data={"email": "admin@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_wrong_email(self, client):
        resp = client.post(
            "/login",
            data={"email": "nonexistent@test.com", "password": "secret1234"},
        )
        assert resp.status_code == 401

    def test_logout(self, client):
        client.post(
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
        )
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302

    def test_register_duplicate_email(self, client):
        client.post(
            "/register",
            data={
                "name": "First",
                "email": "dupe@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
            },
        )
        resp = client.post(
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
        client.post(
            "/register",
            data={
                "name": "JS User",
                "email": "js@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/recruiter/dashboard", follow_redirects=False)
        assert resp.status_code == 403

    def test_jobseeker_cannot_access_admin(self, client):
        client.post(
            "/register",
            data={
                "name": "JS User",
                "email": "js2@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 403

    def test_recruiter_cannot_access_admin(self, client):
        client.post(
            "/register",
            data={
                "name": "Rec Test",
                "email": "rec@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "recruiter",
                "company_name": "PT Test",
                "company_position": "HRD",
            },
        )
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 403

    def test_admin_can_access_admin_dashboard(self, client):
        client.post(
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
        )
        resp = client.get("/admin")
        assert resp.status_code == 200

    def test_admin_can_access_recruiter_applicants(self, client):
        client.post(
            "/login",
            data={"email": "admin@example.com", "password": "admin12345"},
        )
        resp = client.get("/recruiter/applicants")
        assert resp.status_code == 200


class TestAuthenticatedRoutes:
    def test_dashboard_after_login(self, client):
        client.post(
            "/register",
            data={
                "name": "Dash User",
                "email": "dash@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_profile_after_login(self, client):
        client.post(
            "/register",
            data={
                "name": "Prof User",
                "email": "prof@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/profile")
        assert resp.status_code == 200

    def test_documents_after_login(self, client):
        client.post(
            "/register",
            data={
                "name": "Doc User",
                "email": "doc@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/documents")
        assert resp.status_code == 200

    def test_document_upload_smoke(self, client):
        client.post(
            "/register",
            data={
                "name": "Upload User",
                "email": "upload@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        data = {
            "notes": "Test document",
            "document_file": (io.BytesIO(b"%PDF-1.4 test"), "test.pdf"),
        }
        resp = client.post(
            "/documents/CV/update",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_bookmarks_after_login(self, client):
        client.post(
            "/register",
            data={
                "name": "BM User",
                "email": "bm@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/bookmarks")
        assert resp.status_code == 200

    def test_applications_after_login(self, client):
        client.post(
            "/register",
            data={
                "name": "App User",
                "email": "app@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/applications")
        assert resp.status_code == 200

    def test_chat_after_login(self, client):
        client.post(
            "/register",
            data={
                "name": "Chat User",
                "email": "chat@test.com",
                "password": "secret1234",
                "confirm_password": "secret1234",
                "role": "jobseeker",
                "skills": "python",
            },
        )
        resp = client.get("/chat")
        assert resp.status_code == 200


class TestErrorHandlers:
    def test_404(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert resp.status_code == 404

    def test_404_template(self, client):
        resp = client.get("/nonexistent-page-xyz")
        assert b"404" in resp.data or resp.status_code == 404
