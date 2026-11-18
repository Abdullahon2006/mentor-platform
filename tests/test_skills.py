
from unittest.mock import patch
import pytest
from app import create_app
from flask import url_for


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


def test_skill_search(client):
    fake_skills = [
        {
            'id': 1,
            'name': 'Python',
            'category': 'Programming',
            'description': 'Python programming',
            'user_count': 3
        }
    ]

    with patch(
        'app.blueprints.skills.routes.fetch_all'
    ) as mock_fetch:
        mock_fetch.side_effect = [
            fake_skills,
            [{'category': 'Programming'}]
        ]

        response = client.get('/skills/?search=Python')

        assert response.status_code == 200
        assert b'Python' in response.data
        assert b'Python programming' in response.data

        sql = mock_fetch.call_args_list[0].args[0]
        params = mock_fetch.call_args_list[0].args[1]

        assert 's.name LIKE %s' in sql
        assert params == ('%Python%',)


def test_skill_category_filter(client):
    fake_skills = [
        {
            'id': 2,
            'name': 'Machine Learning',
            'category': 'Artificial Intelligence',
            'description': 'Machine learning fundamentals',
            'user_count': 5
        }
    ]

    with patch(
        'app.blueprints.skills.routes.fetch_all'
    ) as mock_fetch:
        mock_fetch.side_effect = [
            fake_skills,
            [{'category': 'Artificial Intelligence'}]
        ]

        response = client.get(
            '/skills/?category=Artificial+Intelligence'
        )

        assert response.status_code == 200
        assert b'Machine Learning' in response.data

        sql = mock_fetch.call_args_list[0].args[0]
        params = mock_fetch.call_args_list[0].args[1]

        assert 's.category = %s' in sql
        assert params == ('Artificial Intelligence',)


def test_invalid_proficiency(client):
    fake_user = {'id': 1}

    with patch(
        'app.blueprints.skills.routes.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.skills.routes.execute_query'
    ) as mock_execute:

        with client.session_transaction() as session:
            session['user_id'] = 1

        response = client.post(
            '/skills/manage',
            data={
                'skill_id': '1',
                'proficiency': 'SUPER_EXPERT',
                'years_of_experience': '3'
            },
            follow_redirects=False
        )

        assert response.status_code == 302
        assert 'skills/manage' in response.headers['Location']

        with client.session_transaction() as session:
            messages = session.get('_flashes', [])

        assert any(
            'Invalid proficiency level selected.' in message
            for category, message in messages
        )

        mock_execute.assert_not_called()


def test_negative_experience(client):
    fake_user = {'id': 1}

    with patch(
        'app.blueprints.skills.routes.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.skills.routes.execute_query'
    ) as mock_execute:

        with client.session_transaction() as session:
            session['user_id'] = 1

        response = client.post(
            '/skills/manage',
            data={
                'skill_id': '1',
                'proficiency': 'ADVANCED',
                'years_of_experience': '-3'
            },
            follow_redirects=False
        )

        assert response.status_code == 302

        with client.session_transaction() as session:
            messages = session.get('_flashes', [])

        assert any(
            'Years of experience must be a non-negative integer.' in message
            for category, message in messages
        )

        mock_execute.assert_not_called()


def test_nonnumeric_experience(client):
    fake_user = {'id': 1}

    with patch(
        'app.blueprints.skills.routes.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.skills.routes.execute_query'
    ) as mock_execute:

        with client.session_transaction() as session:
            session['user_id'] = 1

        response = client.post(
            '/skills/manage',
            data={
                'skill_id': '1',
                'proficiency': 'ADVANCED',
                'years_of_experience': 'three'
            },
            follow_redirects=False
        )

        assert response.status_code == 302

        with client.session_transaction() as session:
            messages = session.get('_flashes', [])

        assert any(
            'Years of experience must be a non-negative integer.' in message
            for category, message in messages
        )

        mock_execute.assert_not_called()


def test_nonexistent_skill(client):
    fake_user = {'id': 1}

    with patch(
        'app.blueprints.skills.routes.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.skills.routes.fetch_one',
        return_value=None
    ) as mock_fetch, patch(
        'app.blueprints.skills.routes.execute_query'
    ) as mock_execute:

        with client.session_transaction() as session:
            session['user_id'] = 1

        response = client.post(
            '/skills/manage',
            data={
                'skill_id': '99999',
                'proficiency': 'ADVANCED',
                'years_of_experience': '3'
            },
            follow_redirects=False
        )

        assert response.status_code == 302

        with client.session_transaction() as session:
            messages = session.get('_flashes', [])

        assert any(
            'The selected skill does not exist.' in message
            for category, message in messages
        )

        mock_fetch.assert_called_once_with(
            "SELECT id FROM skills WHERE id = %s",
            (99999,)
        )
        mock_execute.assert_not_called()


def test_valid_skill_tagging(client):
    fake_user = {'id': 1}

    with patch(
        'app.blueprints.skills.routes.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.skills.routes.fetch_one',
        return_value={'id': 2}
    ) as mock_fetch, patch(
        'app.blueprints.skills.routes.execute_query'
    ) as mock_execute:

        with client.session_transaction() as session:
            session['user_id'] = 1

        response = client.post(
            '/skills/manage',
            data={
                'skill_id': '2',
                'proficiency': 'ADVANCED',
                'years_of_experience': '3'
            },
            follow_redirects=False
        )

        assert response.status_code == 302

        mock_fetch.assert_called_once_with(
            "SELECT id FROM skills WHERE id = %s",
            (2,)
        )

        mock_execute.assert_called_once()

        sql, params = mock_execute.call_args.args

        assert 'INSERT INTO user_skills' in sql
        assert 'ON DUPLICATE KEY UPDATE' in sql
        assert params == (1, 2, 'ADVANCED', 3)



def test_recommendations_category_filter(client):
    fake_user = {
    'id': 1,
    'role': 'MENTEE'
    }

    with patch(
        'app.auth_util.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.reviews.routes.get_current_user',
        return_value=fake_user
    ), patch(
        'app.blueprints.reviews.routes.fetch_all'
    ) as mock_fetch:

        mock_fetch.side_effect = [
            [],
            [{'category': 'Programming'}]
        ]

        with client.session_transaction() as session:
            session['user_id'] = 1
            session['role'] = 'MENTEE'

        with client.application.test_request_context():
            recommendations_url = url_for(
                'reviews.mentor_recommendations',
                category='Programming'
            )

        response = client.get(recommendations_url)

        assert response.status_code == 200

        sql, params = mock_fetch.call_args_list[0].args

        assert 'JOIN skills s ON us.skill_id = s.id' in sql
        assert 's.category = %s' in sql
        assert params == ('Programming', 'Programming', 1)
