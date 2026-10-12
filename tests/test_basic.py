import pytest
from app import create_app
from app.auth_util import hash_password, verify_password

def test_password_hashing():
    raw_pass = "secureSecret2026!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("wrongPassword", hashed) is False

def test_flask_app_initialization():
    app = create_app()
    assert app is not None
    # Verify all expected blueprints are registered
    expected_blueprints = {'auth', 'profile', 'skills', 'applications', 'relations', 'schedule', 'reviews', 'admin'}
    for bp in expected_blueprints:
        assert bp in app.blueprints, f"Blueprint {bp} was not registered!"

def test_login_route_accessible():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b"Sign In" in response.data

def test_register_route_accessible():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b"Join MentorMatch" in response.data
