"""
Tests for Gaffar Dulkadir's module (feature/relations-availability):
mentorship_relations (FR-10), mentor_availability (FR-11) and the CQ-04 mentor utilization query.

Every test removes the rows it creates, so the suite can run against the shared
demo/MySQL database:
- test windows are always on Sunday (the seed data has no Sunday windows),
- test applications/relations/meetings carry MARK in a text column,
- test users use an e-mail that starts with 'pytest-relations-'.
"""
import re
from datetime import date, datetime, timedelta

import pytest

from app import create_app
from app.db import execute_query, fetch_all, fetch_one
from app.blueprints.schedule.routes import CQ04_UTILIZATION_SQL, _to_time

MARK = '[pytest-relations]'
PASSWORD = 'password123'
MENTEE = 'ali.yilmaz@itu.edu.tr'     # Ali Yilmaz
MENTOR = 'dr.demir@techcorp.com'     # Ahmet Demir
OUTSIDER = 'selin.kaya@ailabs.org'   # Selin Kaya, a mentor who is not part of the test relations
ADMIN = 'admin@itu.edu.tr'
SUNDAY = 6
MAX_MENTEES = 5                      # MENTOR_CAPACITY in the relations blueprint


# ---------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        last_notification = fetch_one("SELECT COALESCE(MAX(id), 0) AS max_id FROM notifications")['max_id']
        mentor_id = fetch_one("SELECT id FROM users WHERE email = %s", (MENTOR,))['id']
    yield app
    with app.app_context():
        test_relations = (
            "SELECT mr.id FROM mentorship_relations mr "
            "JOIN mentorship_applications ma ON mr.application_id = ma.id WHERE ma.message LIKE %s"
        )
        like = f'%{MARK}%'
        execute_query(f"DELETE FROM meeting_notes WHERE meeting_id IN (SELECT id FROM meetings WHERE relation_id IN ({test_relations}))", (like,))
        execute_query(f"DELETE FROM meetings WHERE relation_id IN ({test_relations})", (like,))
        execute_query(f"DELETE FROM reviews_and_ratings WHERE relation_id IN ({test_relations})", (like,))
        execute_query(
            "DELETE FROM mentorship_relations WHERE application_id IN "
            "(SELECT id FROM mentorship_applications WHERE message LIKE %s)", (like,)
        )
        execute_query("DELETE FROM mentorship_applications WHERE message LIKE %s", (like,))
        execute_query("DELETE FROM mentor_availability WHERE mentor_id = %s AND day_of_week = %s", (mentor_id, SUNDAY))
        execute_query("DELETE FROM users WHERE email LIKE 'pytest-relations-%'")
        execute_query("DELETE FROM notifications WHERE id > %s", (last_notification,))


@pytest.fixture
def ids(app):
    with app.app_context():
        user = lambda email: fetch_one("SELECT id FROM users WHERE email = %s", (email,))['id']
        return {'mentee': user(MENTEE), 'mentor': user(MENTOR), 'outsider': user(OUTSIDER), 'admin': user(ADMIN)}


def login(app, email):
    client = app.test_client()
    client.post('/auth/login', data={'email': email, 'password': PASSWORD})
    return client


def make_relation(app, mentee_id, mentor_id, status='ACTIVE'):
    """Inserts an ACCEPTED application and a relation for it. Returns the relation id."""
    with app.app_context():
        app_id, _ = execute_query(
            "INSERT INTO mentorship_applications (mentee_id, mentor_id, message, status) VALUES (%s, %s, %s, 'ACCEPTED')",
            (mentee_id, mentor_id, MARK)
        )
        relation_id, _ = execute_query(
            "INSERT INTO mentorship_relations (application_id, mentee_id, mentor_id, start_date, status) "
            "VALUES (%s, %s, %s, %s, %s)",
            (app_id, mentee_id, mentor_id, date.today(), status)
        )
    return relation_id


def get_relation(app, relation_id):
    with app.app_context():
        return fetch_one("SELECT * FROM mentorship_relations WHERE id = %s", (relation_id,))


def add_meeting(app, relation_id, start, hours=1, status='SCHEDULED'):
    start = start.replace(microsecond=0)
    with app.app_context():
        meeting_id, _ = execute_query(
            "INSERT INTO meetings (relation_id, scheduled_start, scheduled_end, agenda, status) VALUES (%s, %s, %s, %s, %s)",
            (relation_id, start, start + timedelta(hours=hours), MARK, status)
        )
    return meeting_id


def get_meeting(app, meeting_id):
    with app.app_context():
        return fetch_one("SELECT status, cancellation_reason FROM meetings WHERE id = %s", (meeting_id,))


def set_status(client, relation_id, status, notes=''):
    return client.post(f'/relations/{relation_id}/status', data={'status': status, 'notes': notes}, follow_redirects=True)


def sunday_windows(app, mentor_id):
    """The mentor's test windows as [{'id', 'active', 'start', 'end'}] with 'HH:MM' times."""
    with app.app_context():
        rows = fetch_all(
            "SELECT id, start_time, end_time, is_active FROM mentor_availability "
            "WHERE mentor_id = %s AND day_of_week = %s ORDER BY start_time",
            (mentor_id, SUNDAY)
        )
    return [{'id': r['id'], 'active': bool(r['is_active']),
             'start': _to_time(r['start_time']).strftime('%H:%M'),
             'end': _to_time(r['end_time']).strftime('%H:%M')} for r in rows]


def add_window(client, start, end, day=SUNDAY):
    return client.post('/availability', data={'day_of_week': day, 'start_time': start, 'end_time': end},
                       follow_redirects=True)


def window_id(app, mentor_id, start):
    return next(w['id'] for w in sunday_windows(app, mentor_id) if w['start'] == start)


def cq04_row(app, mentor_id):
    with app.app_context():
        return fetch_all(CQ04_UTILIZATION_SQL, (mentor_id, mentor_id))[0]


# ---------------------------------------------------------------------
# FR-11: availability windows
# ---------------------------------------------------------------------

def test_add_window_checks_day_and_times(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00', day=9)        # no such weekday
    add_window(client, '12:00', '10:00')               # ends before it starts
    add_window(client, '10:00', '10:00')               # empty window
    add_window(client, 'abc', '12:00')                 # not a time
    assert sunday_windows(app, ids['mentor']) == []

    add_window(client, '10:00', '12:00')
    assert sunday_windows(app, ids['mentor']) == [{'id': window_id(app, ids['mentor'], '10:00'),
                                                    'active': True, 'start': '10:00', 'end': '12:00'}]


def test_overlapping_window_is_rejected_but_touching_is_allowed(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00')
    add_window(client, '11:00', '13:00')               # overlaps the first one
    add_window(client, '09:00', '10:30')               # overlaps the first one
    add_window(client, '10:30', '11:30')               # inside the first one
    assert [w['start'] for w in sunday_windows(app, ids['mentor'])] == ['10:00']

    add_window(client, '12:00', '14:00')               # starts exactly when the first one ends
    assert [w['start'] for w in sunday_windows(app, ids['mentor'])] == ['10:00', '12:00']


def test_toggle_window_off_and_on(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00')
    slot = window_id(app, ids['mentor'], '10:00')

    client.post(f'/availability/{slot}/toggle')
    assert sunday_windows(app, ids['mentor'])[0]['active'] is False
    client.post(f'/availability/{slot}/toggle')
    assert sunday_windows(app, ids['mentor'])[0]['active'] is True


def test_toggle_on_is_refused_when_it_overlaps_an_active_window(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00')
    first = window_id(app, ids['mentor'], '10:00')
    client.post(f'/availability/{first}/toggle')       # first window is now inactive
    add_window(client, '11:00', '13:00')               # allowed: it only overlaps an inactive window
    second = window_id(app, ids['mentor'], '11:00')
    assert [w['active'] for w in sunday_windows(app, ids['mentor'])] == [False, True]

    client.post(f'/availability/{first}/toggle')       # would make two active windows overlap
    assert [w['active'] for w in sunday_windows(app, ids['mentor'])] == [False, True]

    client.post(f'/availability/{second}/toggle')      # turn the other one off first
    client.post(f'/availability/{first}/toggle')
    assert [w['active'] for w in sunday_windows(app, ids['mentor'])] == [True, False]


def test_edit_window_is_checked_like_a_new_window(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00')
    add_window(client, '13:00', '15:00')
    second = window_id(app, ids['mentor'], '13:00')

    client.post(f'/availability/{second}/edit', data={'day_of_week': SUNDAY, 'start_time': '11:00', 'end_time': '14:00'})
    client.post(f'/availability/{second}/edit', data={'day_of_week': SUNDAY, 'start_time': '16:00', 'end_time': '15:00'})
    assert [(w['start'], w['end']) for w in sunday_windows(app, ids['mentor'])] == [('10:00', '12:00'), ('13:00', '15:00')]

    client.post(f'/availability/{second}/edit', data={'day_of_week': SUNDAY, 'start_time': '14:00', 'end_time': '16:00'})
    assert [(w['start'], w['end']) for w in sunday_windows(app, ids['mentor'])] == [('10:00', '12:00'), ('14:00', '16:00')]


def test_mentor_cannot_change_or_delete_another_mentors_window(app, ids):
    owner = login(app, MENTOR)
    add_window(owner, '10:00', '12:00')
    slot = window_id(app, ids['mentor'], '10:00')

    other = login(app, OUTSIDER)
    other.post(f'/availability/{slot}/toggle')
    other.post(f'/availability/{slot}/edit', data={'day_of_week': SUNDAY, 'start_time': '14:00', 'end_time': '15:00'})
    other.post(f'/availability/delete/{slot}')
    assert sunday_windows(app, ids['mentor']) == [{'id': slot, 'active': True, 'start': '10:00', 'end': '12:00'}]


def test_delete_window(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00')
    client.post(f"/availability/delete/{window_id(app, ids['mentor'], '10:00')}")
    assert sunday_windows(app, ids['mentor']) == []


def test_availability_page_is_for_mentors_only(app):
    assert login(app, MENTEE).get('/availability').status_code == 302
    assert login(app, ADMIN).get('/availability').status_code == 302
    assert login(app, MENTOR).get('/availability').status_code == 200


def test_availability_page_puts_each_windows_buttons_in_the_table(app, ids):
    client = login(app, MENTOR)
    add_window(client, '10:00', '12:00')
    html = client.get('/availability').get_data(as_text=True)

    assert html.lstrip().lower().startswith('<!doctype')                  # nothing is printed before the page
    rows = re.search(r'<tbody>(.*?)</tbody>', html, re.S).group(1)
    with app.app_context():
        windows = fetch_one("SELECT COUNT(*) AS cnt FROM mentor_availability WHERE mentor_id = %s", (ids['mentor'],))['cnt']
    assert rows.count('Turn off') == windows                                # one toggle button per window
    assert rows.count('id="editSlot') == windows                            # one edit form per window
    assert 'modal fade' not in rows                                         # modals are not inside the table
    assert html.count('{%') == 0 and html.count('{{') == 0                  # no unrendered template code


# ---------------------------------------------------------------------
# FR-10: mentorship relationship lifecycle
# ---------------------------------------------------------------------

def test_status_changes_follow_the_lifecycle(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    client = login(app, MENTOR)

    set_status(client, relation, 'PAUSED', notes='exam week')
    paused = get_relation(app, relation)
    assert paused['status'] == 'PAUSED' and paused['end_date'] is None and paused['notes'] == 'exam week'

    set_status(client, relation, 'ACTIVE')
    assert get_relation(app, relation)['status'] == 'ACTIVE'

    set_status(client, relation, 'COMPLETED')
    done = get_relation(app, relation)
    assert done['status'] == 'COMPLETED' and str(done['end_date']) == date.today().isoformat()
    assert done['notes'] == 'exam week'              # an empty note keeps the old one


def test_completed_and_terminated_are_final(app, ids):
    client = login(app, MENTOR)
    for final in ('COMPLETED', 'TERMINATED'):
        relation = make_relation(app, ids['mentee'], ids['mentor'], status=final)
        for target in ('ACTIVE', 'PAUSED', 'COMPLETED', 'TERMINATED'):
            set_status(client, relation, target)
            assert get_relation(app, relation)['status'] == final


def test_invalid_status_is_rejected(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    set_status(login(app, MENTOR), relation, 'DELETED')
    assert get_relation(app, relation)['status'] == 'ACTIVE'


def test_only_participants_and_admin_can_change_status(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    set_status(login(app, OUTSIDER), relation, 'TERMINATED')
    assert get_relation(app, relation)['status'] == 'ACTIVE'

    set_status(login(app, MENTEE), relation, 'PAUSED')       # the mentee may pause
    assert get_relation(app, relation)['status'] == 'PAUSED'
    set_status(login(app, ADMIN), relation, 'ACTIVE')        # the admin may resume
    assert get_relation(app, relation)['status'] == 'ACTIVE'


def test_leaving_active_cancels_only_upcoming_scheduled_meetings(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    now = datetime.now()
    upcoming = add_meeting(app, relation, now + timedelta(days=2))
    far_future = add_meeting(app, relation, now + timedelta(days=30))
    completed = add_meeting(app, relation, now + timedelta(days=3), status='COMPLETED')

    set_status(login(app, MENTOR), relation, 'PAUSED')
    for meeting in (upcoming, far_future):
        assert get_meeting(app, meeting) == {'status': 'CANCELLED', 'cancellation_reason': 'Mentorship was paused'}
    assert get_meeting(app, completed)['status'] == 'COMPLETED'


def test_resuming_does_not_touch_meetings(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'], status='PAUSED')
    meeting = add_meeting(app, relation, datetime.now() + timedelta(days=2))
    set_status(login(app, MENTOR), relation, 'ACTIVE')
    assert get_meeting(app, meeting)['status'] == 'SCHEDULED'


def test_other_participant_gets_a_notification(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    with app.app_context():
        before = fetch_one("SELECT COALESCE(MAX(id), 0) AS m FROM notifications")['m']

    set_status(login(app, MENTEE), relation, 'PAUSED')       # the mentee acts, so the mentor is told
    with app.app_context():
        rows = fetch_all("SELECT user_id, title, message FROM notifications WHERE id > %s", (before,))
    assert [r['user_id'] for r in rows] == [ids['mentor']]
    assert rows[0]['title'] == 'Mentorship Update' and 'paused' in rows[0]['message']


def test_resume_is_refused_when_the_mentor_is_full(app, ids):
    with app.app_context():
        active = fetch_one(
            "SELECT COUNT(*) AS cnt FROM mentorship_relations WHERE mentor_id = %s AND status = 'ACTIVE'",
            (ids['mentor'],)
        )['cnt']
    fillers = [make_relation(app, ids['mentee'], ids['mentor']) for _ in range(MAX_MENTEES - active)]
    paused = make_relation(app, ids['mentee'], ids['mentor'], status='PAUSED')
    client = login(app, MENTOR)

    set_status(client, paused, 'ACTIVE')
    assert get_relation(app, paused)['status'] == 'PAUSED'

    set_status(client, fillers[0], 'COMPLETED')              # one place is free again
    set_status(client, paused, 'ACTIVE')
    assert get_relation(app, paused)['status'] == 'ACTIVE'


def test_admin_deletes_relation_with_its_children(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    meeting = add_meeting(app, relation, datetime.now() + timedelta(days=2))
    with app.app_context():
        application = fetch_one("SELECT application_id FROM mentorship_relations WHERE id = %s", (relation,))['application_id']
        execute_query(
            "INSERT INTO reviews_and_ratings (relation_id, reviewer_id, reviewee_id, rating, review_text) VALUES (%s, %s, %s, 5, %s)",
            (relation, ids['mentee'], ids['mentor'], MARK)
        )

    login(app, MENTEE).post(f'/relations/{relation}/delete')   # a mentee is not allowed
    login(app, MENTOR).post(f'/relations/{relation}/delete')   # a mentor is not allowed
    assert get_relation(app, relation) is not None

    login(app, ADMIN).post(f'/relations/{relation}/delete')
    assert get_relation(app, relation) is None
    with app.app_context():
        assert fetch_one("SELECT id FROM meetings WHERE id = %s", (meeting,)) is None
        assert fetch_one("SELECT id FROM reviews_and_ratings WHERE relation_id = %s", (relation,)) is None
        # the application goes back to WITHDRAWN so the mentee can apply again
        assert fetch_one("SELECT status FROM mentorship_applications WHERE id = %s", (application,))['status'] == 'WITHDRAWN'


def test_relation_pages_are_limited_to_participants(app, ids):
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    assert login(app, MENTEE).get(f'/relations/{relation}').status_code == 200
    assert login(app, MENTOR).get(f'/relations/{relation}').status_code == 200
    assert login(app, ADMIN).get(f'/relations/{relation}').status_code == 200
    assert login(app, OUTSIDER).get(f'/relations/{relation}').status_code == 302


def test_admin_list_shows_mentee_and_mentor_names(app, ids):
    make_relation(app, ids['mentee'], ids['mentor'])
    html = login(app, ADMIN).get('/relations/').get_data(as_text=True)
    assert 'Ali Yilmaz' in html and 'Ahmet Demir' in html


# ---------------------------------------------------------------------
# CQ-04: mentor weekly utilization
# ---------------------------------------------------------------------

def test_cq04_counts_only_scheduled_meetings_of_the_next_7_days(app, ids):
    before = cq04_row(app, ids['mentor'])
    with app.app_context():
        execute_query(
            "INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, is_active) VALUES (%s, %s, '10:00:00', '12:00:00', TRUE)",
            (ids['mentor'], SUNDAY)
        )
        execute_query(
            "INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, is_active) VALUES (%s, %s, '14:00:00', '15:00:00', FALSE)",
            (ids['mentor'], SUNDAY)
        )
    relation = make_relation(app, ids['mentee'], ids['mentor'])
    now = datetime.now()
    add_meeting(app, relation, now + timedelta(days=2), hours=1)                       # counts
    add_meeting(app, relation, now + timedelta(days=3), hours=1.5)                     # counts
    add_meeting(app, relation, now + timedelta(days=2), hours=3, status='CANCELLED')   # not scheduled
    add_meeting(app, relation, now + timedelta(days=10), hours=2)                      # after 7 days
    add_meeting(app, relation, now - timedelta(days=1), hours=2)                       # in the past

    after = cq04_row(app, ids['mentor'])
    assert after['active_windows'] == before['active_windows'] + 1           # the inactive window is ignored
    assert float(after['weekly_available_hours']) == pytest.approx(float(before['weekly_available_hours']) + 2.0)
    assert float(after['upcoming_scheduled_hours']) == pytest.approx(float(before['upcoming_scheduled_hours']) + 2.5)
    available, booked = float(after['weekly_available_hours']), float(after['upcoming_scheduled_hours'])
    assert float(after['utilization_rate_pct']) == pytest.approx(round(booked / available * 100, 1), abs=0.05)
    assert float(after['free_hours']) == pytest.approx(max(available - booked, 0))


def test_cq04_mentor_without_windows_has_no_rate(app):
    with app.app_context():
        mentor_id, _ = execute_query(
            "INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES (%s, 'x', 'Pytest', 'Mentor', 'MENTOR')",
            ('pytest-relations-mentor@example.com',)
        )
    row = cq04_row(app, mentor_id)
    assert row['active_windows'] == 0
    assert float(row['weekly_available_hours']) == 0 and float(row['free_hours']) == 0
    assert row['utilization_rate_pct'] is None


def test_cq04_returns_every_mentor_without_a_filter(app, ids):
    with app.app_context():
        rows = fetch_all(CQ04_UTILIZATION_SQL, (None, None))
        mentors = fetch_one("SELECT COUNT(*) AS cnt FROM users WHERE role = 'MENTOR'")['cnt']
    assert len(rows) == mentors
    rates = [float(r['utilization_rate_pct']) for r in rows if r['utilization_rate_pct'] is not None]
    assert rates == sorted(rates, reverse=True)       # busiest mentor first


def test_utilization_pages(app):
    admin_page = login(app, ADMIN).get('/availability/utilization')
    assert admin_page.status_code == 200 and b'Ahmet Demir' in admin_page.data
    assert login(app, MENTEE).get('/availability/utilization').status_code == 302
    assert login(app, MENTOR).get('/availability/utilization').status_code == 302
    assert b'Booked (next 7 days)' in login(app, MENTOR).get('/availability').data
