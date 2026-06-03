from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def cleanup_orm_session(app_ctx):
    yield

    from extensions import db

    db.session.remove()
    db.engine.dispose()


def unique_email(prefix):
    return f"{prefix}-{uuid4().hex}@example.com"


def test_user_repository_create_find_and_update(app_ctx):
    from repositories import user_repository

    user = user_repository.create_user(
        name="Repository User",
        email=unique_email("repo-user"),
        password_hash="old-hash",
        skills="python,sql",
    )

    assert user.id is not None
    assert user_repository.find_by_id(user.id).email == user.email
    assert user_repository.find_by_email(user.email).id == user.id
    assert user_repository.email_exists(user.email)

    updated = user_repository.update_user_profile_basic(
        user.id,
        name="Updated Repository User",
        domicile="Bandung",
    )
    assert updated.name == "Updated Repository User"
    assert updated.domicile == "Bandung"

    password_updated = user_repository.update_user_password(user.id, "new-hash")
    assert password_updated.password_hash == "new-hash"


def test_opportunity_application_document_and_audit_repositories(app_ctx):
    from repositories import (
        application_repository,
        audit_repository,
        document_repository,
        opportunity_repository,
        user_repository,
    )

    user = user_repository.create_user(
        name="Repository Applicant",
        email=unique_email("repo-applicant"),
        password_hash="hash",
    )
    creator = user_repository.create_user(
        name="Repository Recruiter",
        email=unique_email("repo-recruiter"),
        password_hash="hash",
        role="recruiter",
        company_name="Pathora Labs",
    )

    opportunity = opportunity_repository.create_opportunity(
        {
            "title": "Repository Internship",
            "provider": "Pathora Labs",
            "type": "internship",
            "description": "A repository-layer smoke test.",
            "requirements": "Basic SQLAlchemy knowledge.",
            "official_link": "https://example.com",
            "required_skills": "python,sqlalchemy",
            "location": "Remote",
            "deadline": "2026-12-31",
            "created_by": creator.id,
            "company_name": "Pathora Labs",
        }
    )
    assert opportunity_repository.find_by_id(opportunity.id).title == "Repository Internship"
    assert opportunity in opportunity_repository.list_by_creator(creator.id)
    assert opportunity in opportunity_repository.list_all()

    updated_opportunity = opportunity_repository.update_opportunity(
        opportunity.id,
        {"title": "Updated Repository Internship"},
        creator_id=creator.id,
    )
    assert updated_opportunity.title == "Updated Repository Internship"

    application = application_repository.create_application(
        user_id=user.id,
        opportunity_id=opportunity.id,
        notes="Initial note",
    )
    assert (
        application_repository.find_by_user_and_opportunity(user.id, opportunity.id).id
        == application.id
    )
    assert application in application_repository.list_by_user(user.id)
    assert application_repository.update_status(application.id, "Interview").status == "Interview"

    document = document_repository.upsert_document(
        user_id=user.id,
        doc_type="CV",
        file_name="cv.pdf",
        file_path="uploads/documents/cv.pdf",
        is_uploaded=True,
        notes="Ready",
    )
    assert document_repository.get_by_user_and_type(user.id, "CV").id == document.id
    assert document in document_repository.list_by_user(user.id)

    audit_log = audit_repository.create_audit_log(
        user_id=user.id,
        action="repository.test",
        target_type="opportunity",
        target_id=opportunity.id,
        metadata={"source": "pytest"},
    )
    assert audit_log in audit_repository.list_recent(action="repository.test")

    assert application_repository.delete_by_user_and_id(user.id, application.id) == 1
    assert opportunity_repository.delete_opportunity(opportunity.id, creator_id=creator.id) == 1
