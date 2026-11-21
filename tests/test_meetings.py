"""
Tests for Raimbek Erik's module (feature/meetings-reviews):
meetings (FR-12, FR-13), meeting_notes (FR-14), reviews_and_ratings (FR-15)
and the CQ-05 mentor leaderboard.

Every test cleans up the rows it creates, so the suite can be run against the
shared demo/MySQL database without leaving test data behind.
"""
import re
import threading
from datetime import date, datetime, timedelta

import pytest

from app import create_app
from app.db import execute_query, fetch_all, fetch_one
from app.blueprints.reviews.routes import CQ05_LEADERBOARD_SQL
from app.blueprints.schedule.routes import _to_datetime, _to_time

MARK = '[pytest-meetings]'          # tag put into every row these tests create
LIKE_MARK = f'%{MARK}%'
PASSWORD = 'password123'
MENTEE = 'ali.yilmaz@itu.edu.tr'     # Ali Yilmaz
MENTOR = 'dr.demir@techcorp.com'     # Ahmet Demir, Ali's mentor
OUTSIDER = 'selin.kaya@ailabs.org'   # Selin Kaya, not part of Ali's mentorship
SECOND_MENTEE = 'ayse.can@itu.edu.tr'  # Ayse Can, temporarily given Ahmet as a second mentor


# ---------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        last_notification = fetch_one("SELECT COALESCE(MAX(id), 0) AS max_id FROM notifications")['max_id']
    yield app
    with app.app_context():
        execute_query(
            "DELETE FROM meeting_notes WHERE summary LIKE %s "
            "OR meeting_id IN (SELECT id FROM meetings WHERE agenda LIKE %s)",
            (LIKE_MARK, LIKE_MARK)
        )
        execute_query("DELETE FROM meetings WHERE agenda LIKE %s", (LIKE_MARK,))
        execute_query("DELETE FROM notifications WHERE id > %s", (last_notification,))


@pytest.fixture
def ids(app):
    """Looks up the ids of the demo users and of Ali & Ahmet's active mentorship."""
    with app.app_context():
        mentee = fetch_one("SELECT id FROM users WHERE email = %s", (MENTEE,))['id']
        mentor = fetch_one("SELECT id FROM users WHERE email = %s", (MENTOR,))['id']
        relation = fetch_one(
            "SELECT id FROM mentorship_relations WHERE mentee_id = %s AND mentor_id = %s AND status = 'ACTIVE'",
            (mentee, mentor)
        )['id']
    return {'mentee': mentee, 'mentor': mentor, 'relation': relation}


@pytest.fixture
def no_existing_review(app, ids):
    """Temporarily removes Ali's existing review of this mentorship, restores it afterwards."""
    with app.app_context():
        original = fetch_one(
            "SELECT * FROM reviews_and_ratings WHERE relation_id = %s AND reviewer_id = %s",
            (ids['relation'], ids['mentee'])
        )
        execute_query("DELETE FROM reviews_and_ratings WHERE relation_id = %s AND reviewer_id = %s",
                      (ids['relation'], ids['mentee']))
    yield
    with app.app_context():
        execute_query("DELETE FROM reviews_and_ratings WHERE relation_id = %s AND reviewer_id = %s",
                      (ids['relation'], ids['mentee']))
        if original:
            execute_query(
                "INSERT INTO reviews_and_ratings (id, relation_id, reviewer_id, reviewee_id, rating, review_text, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (original['id'], original['relation_id'], original['reviewer_id'], original['reviewee_id'],
                 original['rating'], original['review_text'], original['created_at'])
            )


def login(app, email):
    client = app.test_client()
    client.post('/auth/login', data={'email': email, 'password': PASSWORD})
    return client


def free_slots(client, relation_id):
    html = client.get(f'/relations/{relation_id}/meetings/book').get_data(as_text=True)
    return re.findall(r'<option value="(\d+\|\d{4}-\d{2}-\d{2})"\s*>', html)


def book(client, relation_id, slot, agenda=MARK):
    return client.post(f'/relations/{relation_id}/meetings/book',
                       data={'slot': slot, 'agenda': agenda}, follow_redirects=True)


def book_completed_meeting(app, client, relation_id):
    """Books the first free slot and marks it COMPLETED directly (time travel is not possible in a test)."""
    slot = free_slots(client, relation_id)[0]
    book(client, relation_id, slot)
    with app.app_context():
        meeting = fetch_one("SELECT id FROM meetings WHERE agenda = %s ORDER BY id DESC", (MARK,))
        execute_query("UPDATE meetings SET status = 'COMPLETED' WHERE id = %s", (meeting['id'],))
    return meeting['id']


# ---------------------------------------------------------------------
# FR-12: meeting scheduling
# ---------------------------------------------------------------------

def test_booking_page_only_offers_mentor_windows(app, ids):
    client = login(app, MENTEE)
    response = client.get(f"/relations/{ids['relation']}/meetings/book")
    assert response.status_code == 200
    assert b'datetime-local' not in response.data  # no free-typed dates any more

    with app.app_context():
        windows = {w['id']: w for w in fetch_all(
            "SELECT id, day_of_week FROM mentor_availability WHERE mentor_id = %s AND is_active = TRUE",
            (ids['mentor'],))}
    slots = free_slots(client, ids['relation'])
    assert slots, "the mentor has active windows, so some slots must be offered"
    for slot in slots:
        window_id, day = slot.split('|')
        assert int(window_id) in windows
        assert date.fromisoformat(day).weekday() == windows[int(window_id)]['day_of_week']


def test_booking_creates_meeting_with_the_window_times(app, ids):
    client = login(app, MENTEE)
    slot = free_slots(client, ids['relation'])[0]
    response = book(client, ids['relation'], slot)
    assert b'Meeting successfully scheduled!' in response.data

    window_id, day = slot.split('|')
    with app.app_context():
        window = fetch_one("SELECT start_time, end_time FROM mentor_availability WHERE id = %s", (window_id,))
        meeting = fetch_one("SELECT * FROM meetings WHERE agenda = %s", (MARK,))
    assert meeting['status'] == 'SCHEDULED'
    assert meeting['relation_id'] == ids['relation']
    assert _to_datetime(meeting['scheduled_start']) == datetime.combine(date.fromisoformat(day), _to_time(window['start_time']))
    assert _to_datetime(meeting['scheduled_end']) == datetime.combine(date.fromisoformat(day), _to_time(window['end_time']))


def test_booking_rejects_taken_wrong_day_and_past_slots(app, ids):
    client = login(app, MENTEE)
    slot = free_slots(client, ids['relation'])[0]
    book(client, ids['relation'], slot)

    # the same slot is now shown as booked and cannot be booked again
    assert slot not in free_slots(client, ids['relation'])
    assert b'already booked' in book(client, ids['relation'], slot).data

    window_id, day = slot.split('|')
    wrong_day = date.fromisoformat(day) + timedelta(days=1)
    assert b'does not fall on the mentor' in book(client, ids['relation'], f'{window_id}|{wrong_day}').data

    past_day = date.fromisoformat(day) - timedelta(weeks=4)
    assert b'not bookable' in book(client, ids['relation'], f'{window_id}|{past_day}').data

    assert b'choose one of the mentor' in book(client, ids['relation'], 'not-a-slot').data

    with app.app_context():
        count = fetch_one("SELECT COUNT(*) AS n FROM meetings WHERE agenda = %s", (MARK,))['n']
    assert count == 1


def test_outsider_cannot_book(app, ids):
    client = login(app, OUTSIDER)
    response = client.get(f"/relations/{ids['relation']}/meetings/book", follow_redirects=True)
    assert b'Unauthorized' in response.data


@pytest.fixture
def second_relation(app, ids):
    """A temporary second ACTIVE mentorship for the same mentor (Ayse -> Ahmet), removed afterwards."""
    with app.app_context():
        mentee2 = fetch_one("SELECT id FROM users WHERE email = %s", (SECOND_MENTEE,))['id']
        app_id, _ = execute_query(
            "INSERT INTO mentorship_applications (mentee_id, mentor_id, message, status) "
            "VALUES (%s, %s, %s, 'ACCEPTED')",
            (mentee2, ids['mentor'], MARK)
        )
        relation_id, _ = execute_query(
            "INSERT INTO mentorship_relations (application_id, mentee_id, mentor_id, start_date, status) "
            "VALUES (%s, %s, %s, %s, 'ACTIVE')",
            (app_id, mentee2, ids['mentor'], date.today())
        )
    yield relation_id
    with app.app_context():
        execute_query("DELETE FROM meetings WHERE relation_id = %s", (relation_id,))
        execute_query("DELETE FROM mentorship_relations WHERE id = %s", (relation_id,))
        execute_query("DELETE FROM mentorship_applications WHERE id = %s", (app_id,))


def test_concurrent_booking_of_same_slot_only_one_succeeds(app, ids, second_relation):
    """
    NFR-05: two mentees of the same mentor submit the same slot at the same moment.
    The SELECT ... FOR UPDATE lock on the mentor row must let exactly one booking through.
    """
    ali = login(app, MENTEE)
    ayse = login(app, SECOND_MENTEE)
    slot = free_slots(ali, ids['relation'])[0]
    assert slot in free_slots(ayse, second_relation)  # same mentor, so the same slot is offered to both

    start_together = threading.Barrier(2)
    results = {}

    def attempt(name, client, relation_id):
        start_together.wait()  # release both requests at the same instant
        results[name] = book(client, relation_id, slot, agenda=f'{MARK} {name}').get_data(as_text=True)

    threads = [threading.Thread(target=attempt, args=('ali', ali, ids['relation'])),
               threading.Thread(target=attempt, args=('ayse', ayse, second_relation))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    succeeded = [n for n, html in results.items() if 'Meeting successfully scheduled!' in html]
    refused = [n for n, html in results.items() if 'already booked' in html]
    assert len(succeeded) == 1, results.keys()
    assert len(refused) == 1

    window_id, day = slot.split('|')
    with app.app_context():
        window = fetch_one("SELECT start_time FROM mentor_availability WHERE id = %s", (window_id,))
        start_dt = datetime.combine(date.fromisoformat(day), _to_time(window['start_time']))
        booked = fetch_one(
            "SELECT COUNT(*) AS n FROM meetings m JOIN mentorship_relations mr ON m.relation_id = mr.id "
            "WHERE mr.mentor_id = %s AND m.status = 'SCHEDULED' AND m.scheduled_start = %s",
            (ids['mentor'], start_dt)
        )['n']
    assert booked == 1


# ---------------------------------------------------------------------
# FR-13: meeting status and cancellation
# ---------------------------------------------------------------------

def test_cancellation_requires_reason(app, ids):
    client = login(app, MENTEE)
    book(client, ids['relation'], free_slots(client, ids['relation'])[0])
    with app.app_context():
        meeting_id = fetch_one("SELECT id FROM meetings WHERE agenda = %s", (MARK,))['id']

    response = client.post(f'/meetings/{meeting_id}/status',
                           data={'status': 'CANCELLED', 'cancellation_reason': '  '}, follow_redirects=True)
    assert b'provide a reason' in response.data

    # the booked slot is in the future, so it cannot be "completed" yet
    response = client.post(f'/meetings/{meeting_id}/status', data={'status': 'COMPLETED'}, follow_redirects=True)
    assert b'has not started yet' in response.data

    client.post(f'/meetings/{meeting_id}/status', data={'status': 'CANCELLED', 'cancellation_reason': 'Exam week'})
    with app.app_context():
        meeting = fetch_one("SELECT status, cancellation_reason FROM meetings WHERE id = %s", (meeting_id,))
    assert meeting['status'] == 'CANCELLED'
    assert meeting['cancellation_reason'] == 'Exam week'

    # a finished meeting cannot be changed again
    response = client.post(f'/meetings/{meeting_id}/status', data={'status': 'COMPLETED'}, follow_redirects=True)
    assert b'can no longer be changed' in response.data


# ---------------------------------------------------------------------
# FR-14: meeting notes CRUD
# ---------------------------------------------------------------------

def test_meeting_notes_crud(app, ids):
    mentee = login(app, MENTEE)
    meeting_id = book_completed_meeting(app, mentee, ids['relation'])

    # CREATE
    response = mentee.post(f'/meetings/{meeting_id}/notes',
                           data={'summary': f'{MARK} covered 3NF', 'action_items': 'read chapter 14'},
                           follow_redirects=True)
    assert b'Meeting notes and action items saved!' in response.data
    with app.app_context():
        note = fetch_one("SELECT * FROM meeting_notes WHERE meeting_id = %s", (meeting_id,))
    assert note['author_id'] == ids['mentee']

    # READ: shown on the mentorship page with the author's name
    page = mentee.get(f"/relations/{ids['relation']}").get_data(as_text=True)
    assert 'covered 3NF' in page and 'Session Minutes by Ali Yilmaz' in page

    # UPDATE: only the author
    mentor = login(app, MENTOR)
    mentor.post(f"/notes/{note['id']}/edit", data={'summary': 'hijacked'})
    mentee.post(f"/notes/{note['id']}/edit", data={'summary': f'{MARK} covered BCNF', 'action_items': ''})
    with app.app_context():
        assert fetch_one("SELECT summary FROM meeting_notes WHERE id = %s", (note['id'],))['summary'] == f'{MARK} covered BCNF'

    # DELETE: not by the other participant, yes by the author
    mentor.post(f"/notes/{note['id']}/delete")
    with app.app_context():
        assert fetch_one("SELECT id FROM meeting_notes WHERE id = %s", (note['id'],)) is not None
    mentee.post(f"/notes/{note['id']}/delete")
    with app.app_context():
        assert fetch_one("SELECT id FROM meeting_notes WHERE id = %s", (note['id'],)) is None


def test_notes_need_completed_meeting_and_summary(app, ids):
    client = login(app, MENTEE)
    book(client, ids['relation'], free_slots(client, ids['relation'])[0])
    with app.app_context():
        meeting_id = fetch_one("SELECT id FROM meetings WHERE agenda = %s", (MARK,))['id']

    response = client.post(f'/meetings/{meeting_id}/notes', data={'summary': f'{MARK} too early'}, follow_redirects=True)
    assert b'only be added to completed meetings' in response.data

    with app.app_context():
        execute_query("UPDATE meetings SET status = 'COMPLETED' WHERE id = %s", (meeting_id,))
    response = client.post(f'/meetings/{meeting_id}/notes', data={'summary': ''}, follow_redirects=True)
    assert b'Summary is required' in response.data


def test_meeting_with_two_notes_is_listed_once(app, ids):
    mentee = login(app, MENTEE)
    mentor = login(app, MENTOR)
    meeting_id = book_completed_meeting(app, mentee, ids['relation'])
    mentee.post(f'/meetings/{meeting_id}/notes', data={'summary': f'{MARK} mentee view'})
    mentor.post(f'/meetings/{meeting_id}/notes', data={'summary': f'{MARK} mentor view'})

    page = mentee.get(f"/relations/{ids['relation']}").get_data(as_text=True)
    assert page.count(f'<strong>Agenda:</strong> {MARK}') == 1  # meeting card not duplicated
    assert 'mentee view' in page and 'mentor view' in page


# ---------------------------------------------------------------------
# FR-15: reviews and ratings
# ---------------------------------------------------------------------

def test_review_submit_edit_delete(app, ids, no_existing_review):
    client = login(app, MENTEE)

    # CREATE
    response = client.post(f"/relations/{ids['relation']}/review",
                           data={'rating': '4', 'review_text': 'clear explanations'}, follow_redirects=True)
    assert b'Your review has been submitted' in response.data
    with app.app_context():
        review = fetch_one("SELECT * FROM reviews_and_ratings WHERE relation_id = %s AND reviewer_id = %s",
                           (ids['relation'], ids['mentee']))
    assert review['rating'] == 4
    assert review['reviewee_id'] == ids['mentor']  # mentee reviews the mentor

    # a second review of the same mentorship is refused
    response = client.post(f"/relations/{ids['relation']}/review", data={'rating': '1'}, follow_redirects=True)
    assert b'already reviewed' in response.data

    # UPDATE
    client.post(f"/reviews/{review['id']}/edit", data={'rating': '5', 'review_text': 'even better'})
    with app.app_context():
        updated = fetch_one("SELECT rating, review_text FROM reviews_and_ratings WHERE id = %s", (review['id'],))
    assert (updated['rating'], updated['review_text']) == (5, 'even better')

    # DELETE
    client.post(f"/reviews/{review['id']}/delete")
    with app.app_context():
        assert fetch_one("SELECT id FROM reviews_and_ratings WHERE id = %s", (review['id'],)) is None


def test_review_validation_and_permissions(app, ids, no_existing_review):
    client = login(app, MENTEE)
    for bad_rating in ('0', '6', 'abc', ''):
        response = client.post(f"/relations/{ids['relation']}/review", data={'rating': bad_rating}, follow_redirects=True)
        assert b'between 1 and 5' in response.data

    client.post(f"/relations/{ids['relation']}/review", data={'rating': '3'})
    with app.app_context():
        review_id = fetch_one("SELECT id FROM reviews_and_ratings WHERE relation_id = %s AND reviewer_id = %s",
                              (ids['relation'], ids['mentee']))['id']

    outsider = login(app, OUTSIDER)
    response = outsider.post(f"/relations/{ids['relation']}/review", data={'rating': '1'}, follow_redirects=True)
    assert b'Unauthorized' in response.data
    outsider.post(f'/reviews/{review_id}/edit', data={'rating': '1'})
    outsider.post(f'/reviews/{review_id}/delete')
    with app.app_context():
        assert fetch_one("SELECT rating FROM reviews_and_ratings WHERE id = %s", (review_id,))['rating'] == 3


# ---------------------------------------------------------------------
# CQ-05: mentor leaderboard
# ---------------------------------------------------------------------

def _leaderboard(app):
    with app.app_context():
        return {row['mentor_id']: row for row in fetch_all(CQ05_LEADERBOARD_SQL)}


def test_cq05_matches_simple_independent_counts(app):
    rows = _leaderboard(app)
    assert rows
    with app.app_context():
        for mentor_id, row in rows.items():
            relations = fetch_one(
                "SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active "
                "FROM mentorship_relations WHERE mentor_id = %s", (mentor_id,))
            meetings = fetch_one(
                "SELECT COUNT(*) AS n FROM meetings m JOIN mentorship_relations mr ON m.relation_id = mr.id "
                "WHERE mr.mentor_id = %s AND m.status = 'COMPLETED'", (mentor_id,))
            reviews = fetch_one(
                "SELECT COUNT(*) AS n, AVG(rating) AS avg_rating FROM reviews_and_ratings rr "
                "JOIN mentorship_relations mr ON rr.relation_id = mr.id "
                "WHERE mr.mentor_id = %s AND rr.reviewee_id = %s", (mentor_id, mentor_id))
            assert row['total_mentorships'] == relations['n']
            assert row['active_mentorships'] == relations['active']
            assert row['total_meetings_held'] == meetings['n']
            assert row['total_reviews_received'] == reviews['n']
            assert float(row['avg_rating']) == pytest.approx(float(reviews['avg_rating'] or 0), abs=0.01)


def test_cq05_extra_meeting_does_not_inflate_other_metrics(app, ids):
    """Regression test for the fan-out bug: one more meeting must change ONLY the meeting count."""
    before = _leaderboard(app)[ids['mentor']]
    with app.app_context():
        execute_query(
            "INSERT INTO meetings (relation_id, scheduled_start, scheduled_end, agenda, status) "
            "VALUES (%s, %s, %s, %s, 'COMPLETED')",
            (ids['relation'], datetime(2026, 10, 10, 17), datetime(2026, 10, 10, 18), MARK)
        )
    after = _leaderboard(app)[ids['mentor']]
    assert after['total_meetings_held'] == before['total_meetings_held'] + 1
    for metric in ('total_mentorships', 'active_mentorships', 'completed_mentorships',
                   'total_reviews_received', 'avg_rating'):
        assert after[metric] == before[metric], metric


def test_leaderboard_page_is_public(app):
    response = app.test_client().get('/leaderboard')
    assert response.status_code == 200
    assert b'CQ-05' in response.data
