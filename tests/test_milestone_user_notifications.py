import pytest

from app import create_app
import app.auth_util as auth_util
import app.blueprints.admin.routes as admin_routes
import app.blueprints.profile.routes as profile_routes


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True, SECRET_KEY="test-secret-key")
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def sign_in(client, user_id=1, role="ADMIN"):
    with client.session_transaction() as user_session:
        user_session["user_id"] = user_id
        user_session["role"] = role


def test_profile_alias_redirects_authenticated_user_to_dashboard(client):
    sign_in(client, user_id=2, role="MENTEE")

    response = client.get("/profile", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_profile_alias_requires_login(client):
    response = client.get("/profile", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_admin_cannot_delete_own_account(client, monkeypatch):
    sign_in(client, user_id=7)
    monkeypatch.setattr(auth_util, "fetch_one", lambda sql, params: {"id": 7, "role": "ADMIN"})

    def fail_if_called(*args, **kwargs):
        pytest.fail("Self-deletion must not execute a DELETE query")

    monkeypatch.setattr(admin_routes, "execute_query", fail_if_called)

    response = client.post("/admin/users/7/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/")


def test_admin_can_delete_another_user(client, monkeypatch):
    sign_in(client, user_id=7)
    monkeypatch.setattr(auth_util, "fetch_one", lambda sql, params: {"id": 7, "role": "ADMIN"})
    calls = []
    monkeypatch.setattr(
        admin_routes,
        "execute_query",
        lambda sql, params: calls.append((sql, params)) or (0, 1),
    )

    response = client.post("/admin/users/8/delete", follow_redirects=False)

    assert response.status_code == 302
    assert calls == [("DELETE FROM users WHERE id = %s", (8,))]


def test_non_admin_cannot_delete_user(client, monkeypatch):
    sign_in(client, user_id=2, role="MENTEE")
    monkeypatch.setattr(auth_util, "fetch_one", lambda sql, params: {"id": 2, "role": "MENTEE"})

    def fail_if_called(*args, **kwargs):
        pytest.fail("Unauthorized deletion must not execute a DELETE query")

    monkeypatch.setattr(admin_routes, "execute_query", fail_if_called)

    response = client.post("/admin/users/8/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_notification_delete_is_scoped_to_current_user(client, monkeypatch):
    sign_in(client, user_id=11, role="MENTEE")
    monkeypatch.setattr(auth_util, "fetch_one", lambda sql, params: {"id": 11, "role": "MENTEE"})
    calls = []
    monkeypatch.setattr(
        profile_routes,
        "execute_query",
        lambda sql, params: calls.append((sql, params)) or (0, 1),
    )

    response = client.post("/notifications/23/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert calls == [
        ("DELETE FROM notifications WHERE id = %s AND user_id = %s", (23, 11))
    ]


def test_notification_delete_requires_login(client, monkeypatch):
    def fail_if_called(*args, **kwargs):
        pytest.fail("Anonymous deletion must not execute a DELETE query")

    monkeypatch.setattr(profile_routes, "execute_query", fail_if_called)

    response = client.post("/notifications/23/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")
