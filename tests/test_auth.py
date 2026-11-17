"""Authentication route tests for registration validation and sessions."""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
import app.blueprints.auth.routes as auth_routes


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True, SECRET_KEY="test-secret-key")
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_registration_rejects_missing_required_fields(client):
    response = client.post(
        "/auth/register",
        data={
            "email": "",
            "password": "",
            "first_name": "",
            "last_name": "",
            "role": "MENTEE",
        },
    )

    assert response.status_code == 200
    assert b"All required fields must be filled." in response.data


def test_registration_rejects_invalid_role(client):
    response = client.post(
        "/auth/register",
        data={
            "email": "new.user@example.com",
            "password": "password123",
            "first_name": "New",
            "last_name": "User",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 200
    assert b"Invalid role selection." in response.data


def test_registration_rejects_existing_email(client, monkeypatch):
    monkeypatch.setattr(auth_routes, "fetch_one", lambda sql, params: {"id": 7})

    response = client.post(
        "/auth/register",
        data={
            "email": "existing@example.com",
            "password": "password123",
            "first_name": "Existing",
            "last_name": "User",
            "role": "MENTEE",
        },
    )

    assert response.status_code == 200
    assert b"An account with this email address already exists." in response.data


def test_successful_login_creates_user_session(client, monkeypatch):
    user = {
        "id": 42,
        "email": "ravan@example.com",
        "password_hash": generate_password_hash("password123"),
        "first_name": "Ravan",
        "last_name": "Seyfullayev",
        "role": "MENTEE",
    }
    monkeypatch.setattr(auth_routes, "fetch_one", lambda sql, params: user)

    response = client.post(
        "/auth/login",
        data={"email": "ravan@example.com", "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    with client.session_transaction() as user_session:
        assert user_session["user_id"] == 42
        assert user_session["role"] == "MENTEE"
        assert user_session["user_name"] == "Ravan Seyfullayev"


def test_failed_login_does_not_create_user_session(client, monkeypatch):
    monkeypatch.setattr(auth_routes, "fetch_one", lambda sql, params: None)

    response = client.post(
        "/auth/login",
        data={"email": "missing@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Invalid email or password. Please try again." in response.data
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session
        assert "role" not in user_session
        assert "user_name" not in user_session


def test_logout_clears_user_session(client):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 42
        user_session["role"] = "MENTEE"
        user_session["user_name"] = "Ravan Seyfullayev"

    response = client.get("/auth/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session
        assert "role" not in user_session
        assert "user_name" not in user_session


def test_dashboard_redirects_user_without_session_to_login(client):
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")
