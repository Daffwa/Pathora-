import os
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def app_root():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def temp_data_dir():
    with tempfile.TemporaryDirectory(prefix="pytest_pathora_") as tmp:
        yield Path(tmp)


@pytest.fixture(scope="function")
def app(temp_data_dir, app_root):
    os.environ["APP_ENV"] = "test"
    os.environ["DATA_DIR"] = str(temp_data_dir)
    os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
    os.environ["PASSWORD_RESET_SECRET"] = "test-password-reset-secret"
    os.environ["RATE_LIMIT_BACKEND"] = "memory"

    sys.path.insert(0, str(app_root))

    from app import create_app

    application = create_app()
    application.testing = True

    with application.app_context():
        from services.database_service import init_database
        from services.rate_limit_service import reset_rate_limits

        reset_rate_limits()
        init_database()

    yield application

    for env_name in (
        "APP_ENV",
        "DATA_DIR",
        "SECRET_KEY",
        "PASSWORD_RESET_SECRET",
        "RATE_LIMIT_BACKEND",
    ):
        if env_name in os.environ:
            del os.environ[env_name]


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def app_ctx(app):
    with app.app_context():
        yield
