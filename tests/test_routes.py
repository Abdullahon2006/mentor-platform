import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_browse_mentors(client):
    response = client.get('/mentors')
    assert response.status_code == 200
    assert b"Explore Experienced Mentors" in response.data
    assert b"Demir" in response.data

def test_browse_skills(client):
    response = client.get('/skills/')
    assert response.status_code == 200
    assert b"Skills Taxonomy Catalog" in response.data
    assert b"Python Backend &amp; Flask" in response.data

def test_leaderboard(client):
    response = client.get('/leaderboard')
    assert response.status_code == 200
    assert b"Mentor Leaderboard" in response.data
    assert b"Ahmet Demir" in response.data

def test_mentor_login_and_dashboard(client):
    # Login as Mentor Ahmet Demir
    response = client.post('/auth/login', data={
        'email': 'dr.demir@techcorp.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Mentor Portal" in response.data
    assert b"Ahmet Demir" in response.data

def test_mentee_login_and_dashboard(client):
    # Login as Mentee Ali Yilmaz
    response = client.post('/auth/login', data={
        'email': 'ali.yilmaz@itu.edu.tr',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Ali!" in response.data
    assert b"Smart Mentor Matches" in response.data
