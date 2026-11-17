"""Pytest fixtures for the monitoring demo app."""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "ci-test-secret-key",
            "ADMIN_PASSWORD_HASH": generate_password_hash("test-pass"),
            "DATABASE": str(db_path),
        }
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"username": "admin", "password": "test-pass"})
    return client
