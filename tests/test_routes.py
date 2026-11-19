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

def test_mentee_goals_cq03(client):
    # Login as Mentee Ali Yilmaz
    client.post('/auth/login', data={
        'email': 'ali.yilmaz@itu.edu.tr',
        'password': 'password123'
    }, follow_redirects=True)

    # View goals (executes CQ-03)
    response = client.get('/goals/manage')
    assert response.status_code == 200
    assert b"Mentorship Learning Goals" in response.data
    assert b"Master Raw SQL &amp; Relational Normalization" in response.data or b"Master Raw SQL & Relational Normalization" in response.data

    # Create new goal
    res_create = client.post('/goals/manage', data={
        'action': 'create',
        'title': 'Learn Redis Caching Layer',
        'description': 'Study Redis key-value caching in accordance with project guidelines',
        'target_date': '2026-11-20'
    }, follow_redirects=True)
    assert res_create.status_code == 200
    assert b"Goal created successfully!" in res_create.data
    assert b"Learn Redis Caching Layer" in res_create.data

def test_application_submission_and_withdrawal(client):
    # Login as Mentee Ali Yilmaz
    client.post('/auth/login', data={
        'email': 'ali.yilmaz@itu.edu.tr',
        'password': 'password123'
    }, follow_redirects=True)

    # Submit application to Mentor Selin Kaya (id=3)
    res_apply = client.post('/apply/3', data={
        'message': 'Hello Selin, I would appreciate your guidance on modern AI pipelines.'
    }, follow_redirects=True)
    assert res_apply.status_code == 200
    assert b"Application sent successfully!" in res_apply.data

    # Check applications list
    res_list = client.get('/applications')
    assert res_list.status_code == 200
    assert b"Selin Kaya" in res_list.data
    assert b"PENDING" in res_list.data
    assert b"Withdraw" in res_list.data

def test_mentor_decide_application_capacity_and_atomic(client):
    from app.db import execute_query, fetch_one
    created_app_ids = []
    created_rel_ids = []

    try:
        with client.application.app_context():
            # Real mentee Burak Erdogan (id=8) applies to Mentor Selin Kaya (id=3)
            app_id, _ = execute_query(
                "INSERT INTO mentorship_applications (mentee_id, mentor_id, message, status) VALUES (8, 3, 'Capacity test application', 'PENDING')"
            )
            created_app_ids.append(app_id)

        # Login as Mentor Selin Kaya (id=3)
        client.post('/auth/login', data={
            'email': 'selin.kaya@ailabs.org',
            'password': 'password123'
        }, follow_redirects=True)

        # 1. Accept application normally
        res_accept = client.post(f'/applications/{app_id}/decide', data={'decision': 'ACCEPTED'}, follow_redirects=True)
        assert res_accept.status_code == 200
        assert b"Application accepted! An active mentorship relationship has been established." in res_accept.data

        with client.application.app_context():
            # Verify atomic update
            app_row = fetch_one("SELECT status FROM mentorship_applications WHERE id = %s", (app_id,))
            assert app_row['status'] == 'ACCEPTED'
            rel_row = fetch_one("SELECT id, status FROM mentorship_relations WHERE application_id = %s", (app_id,))
            assert rel_row is not None
            assert rel_row['status'] == 'ACTIVE'
            created_rel_ids.append(rel_row['id'])

        # 2. Test double-click / re-acceptance guard: second accept must be rejected
        res_double = client.post(f'/applications/{app_id}/decide', data={'decision': 'ACCEPTED'}, follow_redirects=True)
        assert b"already been processed" in res_double.data.lower()

        # 3. Test capacity check limit:
        # Selin had 1 seed relation (id=2) and 1 from step 1 (total 2).
        # Insert 3 more valid accepted applications + relations to reach the cap of 5.
        with client.application.app_context():
            # Mentee Damla Aksoy (id=9)
            for i in range(3):
                dummy_app_id, _ = execute_query(
                    "INSERT INTO mentorship_applications (mentee_id, mentor_id, message, status) VALUES (9, 3, %s, 'ACCEPTED')",
                    (f'Dummy app {i}',)
                )
                created_app_ids.append(dummy_app_id)
                dummy_rel_id, _ = execute_query(
                    "INSERT INTO mentorship_relations (application_id, mentee_id, mentor_id, start_date, status) VALUES (%s, 9, 3, '2026-11-01', 'ACTIVE')",
                    (dummy_app_id,)
                )
                created_rel_ids.append(dummy_rel_id)

            # Mentee Eren Celik (id=10) submits a 6th pending application
            over_app_id, _ = execute_query(
                "INSERT INTO mentorship_applications (mentee_id, mentor_id, message, status) VALUES (10, 3, 'Over capacity test', 'PENDING')"
            )
            created_app_ids.append(over_app_id)

        res_over = client.post(f'/applications/{over_app_id}/decide', data={'decision': 'ACCEPTED'}, follow_redirects=True)
        assert b"You already have 5 active mentees" in res_over.data

    finally:
        with client.application.app_context():
            if created_rel_ids:
                execute_query(f"DELETE FROM mentorship_relations WHERE id IN ({','.join(map(str, created_rel_ids))})")
            if created_app_ids:
                execute_query(f"DELETE FROM mentorship_applications WHERE id IN ({','.join(map(str, created_app_ids))})")
            # Clean up notifications generated during test
            execute_query("DELETE FROM notifications WHERE user_id IN (8, 9, 10) AND title = 'Application Accepted!'")


