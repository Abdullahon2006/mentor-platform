from flask import render_template, request, redirect, url_for, flash
from app.blueprints.reviews import reviews_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, role_required, get_current_user

def _parse_rating(raw):
    """Returns an int rating 1..5, or None if the input is invalid."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 5 else None


@reviews_bp.route('/relations/<int:relation_id>/review', methods=['POST'])
@login_required
def submit_review(relation_id):
    """CREATE: submit a 1-5 star review for the other party of a mentorship (FR-15)."""
    user = get_current_user()
    user_id = user['id']
    rating_val = _parse_rating(request.form.get('rating'))
    review_text = request.form.get('review_text', '').strip()

    if rating_val is None:
        flash("Rating must be an integer between 1 and 5.", "danger")
        return redirect(url_for('relations.relation_detail', relation_id=relation_id))

    # Only the two participants of the relation may review each other
    rel = fetch_one("SELECT id, mentee_id, mentor_id FROM mentorship_relations WHERE id = %s", (relation_id,))
    if not rel or user_id not in (rel['mentee_id'], rel['mentor_id']):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    reviewee_id = rel['mentor_id'] if user_id == rel['mentee_id'] else rel['mentee_id']

    # One review per reviewer per relation (also enforced by the UNIQUE constraint uq_review_per_party)
    existing = fetch_one(
        "SELECT id FROM reviews_and_ratings WHERE relation_id = %s AND reviewer_id = %s AND reviewee_id = %s",
        (relation_id, user_id, reviewee_id)
    )
    if existing:
        flash("You already reviewed this mentorship. Use Edit to change your review.", "warning")
        return redirect(url_for('relations.relation_detail', relation_id=relation_id))

    execute_query(
        """
        INSERT INTO reviews_and_ratings (relation_id, reviewer_id, reviewee_id, rating, review_text)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            rating = VALUES(rating),
            review_text = VALUES(review_text)
        """,
        (relation_id, user_id, reviewee_id, rating_val, review_text)
    )

    notif_msg = f"{user['first_name']} {user['last_name']} submitted a review for your mentorship."
    execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                  (reviewee_id, "New Review Received", notif_msg))

    flash("Thank you! Your review has been submitted.", "success")
    return redirect(url_for('relations.relation_detail', relation_id=relation_id))


@reviews_bp.route('/reviews/<int:review_id>/edit', methods=['POST'])
@login_required
def edit_review(review_id):
    """UPDATE: the author of a review changes its rating or text (FR-15)."""
    user = get_current_user()
    review = fetch_one("SELECT id, relation_id, reviewer_id FROM reviews_and_ratings WHERE id = %s", (review_id,))
    if not review or review['reviewer_id'] != user['id']:
        flash("You can only edit your own reviews.", "danger")
        return redirect(url_for('relations.list_relations'))

    rating_val = _parse_rating(request.form.get('rating'))
    review_text = request.form.get('review_text', '').strip()
    if rating_val is None:
        flash("Rating must be an integer between 1 and 5.", "danger")
        return redirect(url_for('relations.relation_detail', relation_id=review['relation_id']))

    execute_query(
        "UPDATE reviews_and_ratings SET rating = %s, review_text = %s WHERE id = %s AND reviewer_id = %s",
        (rating_val, review_text, review_id, user['id'])
    )
    flash("Your review has been updated.", "success")
    return redirect(url_for('relations.relation_detail', relation_id=review['relation_id']))


@reviews_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    """DELETE: the author (or an admin) removes a review (FR-15)."""
    user = get_current_user()
    review = fetch_one("SELECT id, relation_id, reviewer_id FROM reviews_and_ratings WHERE id = %s", (review_id,))
    if not review or (review['reviewer_id'] != user['id'] and user['role'] != 'ADMIN'):
        flash("You can only delete your own reviews.", "danger")
        return redirect(url_for('relations.list_relations'))

    execute_query("DELETE FROM reviews_and_ratings WHERE id = %s", (review_id,))
    flash("Review deleted.", "info")
    return redirect(url_for('relations.relation_detail', relation_id=review['relation_id']))


# CQ-05: Mentor Leaderboard & Engagement Metrics (Raimbek Erik). Kept as a
# module constant so tests/test_meetings.py can run the exact same SQL.
CQ05_LEADERBOARD_SQL = """
    SELECT
        u.id AS mentor_id,
        CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
        u.current_title,
        u.organization,
        rel.total_mentorships,
        rel.completed_mentorships,
        rel.active_mentorships,
        COALESCE(mt.meetings_held, 0) AS total_meetings_held,
        COALESCE(rv.avg_rating, 0.0) AS avg_rating,
        COALESCE(rv.review_count, 0) AS total_reviews_received
    FROM users u
    -- (1) one row per mentor: how many mentorships, and in which state
    JOIN (
        SELECT mentor_id,
               COUNT(*) AS total_mentorships,
               SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_mentorships,
               SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_mentorships
        FROM mentorship_relations
        GROUP BY mentor_id
    ) rel ON rel.mentor_id = u.id
    -- (2) one row per mentor: completed meetings across all of their mentorships
    LEFT JOIN (
        SELECT mr.mentor_id, COUNT(*) AS meetings_held
        FROM meetings m
        JOIN mentorship_relations mr ON m.relation_id = mr.id
        WHERE m.status = 'COMPLETED'
        GROUP BY mr.mentor_id
    ) mt ON mt.mentor_id = u.id
    -- (3) one row per mentor: reviews written ABOUT the mentor
    LEFT JOIN (
        SELECT mr.mentor_id, ROUND(AVG(rr.rating), 2) AS avg_rating, COUNT(*) AS review_count
        FROM reviews_and_ratings rr
        JOIN mentorship_relations mr ON rr.relation_id = mr.id AND rr.reviewee_id = mr.mentor_id
        GROUP BY mr.mentor_id
    ) rv ON rv.mentor_id = u.id
    WHERE u.role = 'MENTOR'
    ORDER BY avg_rating DESC, total_meetings_held DESC, total_reviews_received DESC
"""


@reviews_bp.route('/leaderboard')
def leaderboard():
    """
    CQ-05: Mentor Leaderboard & Engagement Metrics (Raimbek Erik)
    Each metric is aggregated in its own derived table (one row per mentor)
    BEFORE joining, so meetings and reviews cannot multiply each other's rows
    (the "fan-out" problem of joining two one-to-many tables at once).
    """
    leaderboard_data = fetch_all(CQ05_LEADERBOARD_SQL)
    return render_template('reviews/leaderboard.html', leaderboard=leaderboard_data)


@reviews_bp.route('/recommendations')
@role_required('MENTEE')
def mentor_recommendations():
    return redirect(url_for('skills.mentor_recommendations'))

@reviews_bp.route('/analytics/goals')
@role_required('MENTEE')
def goal_analytics():
    """
    COMPLEX QUERY 3: Mentee Goal Progress & Activity Correlation
    Correlates target goals with scheduled and completed meetings.
    """
    user = get_current_user()
    mentee_id = user['id']

    complex_sql = """
        SELECT
            g.id AS goal_id,
            g.title AS goal_title,
            g.status AS goal_status,
            g.target_completion_date,
            DATEDIFF(g.target_completion_date, CURRENT_DATE) AS days_until_target,
            COALESCE(CONCAT(mentor.first_name, ' ', mentor.last_name), 'No Mentor Yet') AS assigned_mentor,
            COUNT(DISTINCT mt.id) AS total_completed_sessions,
            MAX(mt.scheduled_start) AS latest_session_date
        FROM mentorship_goals g
        LEFT JOIN mentorship_applications ma ON g.id = ma.goal_id AND ma.status = 'ACCEPTED'
        LEFT JOIN mentorship_relations mr ON ma.id = mr.application_id
        LEFT JOIN users mentor ON mr.mentor_id = mentor.id
        LEFT JOIN meetings mt ON mr.id = mt.relation_id AND mt.status = 'COMPLETED'
        WHERE g.mentee_id = %s
        GROUP BY g.id, g.title, g.status, g.target_completion_date, mentor.first_name, mentor.last_name
        ORDER BY g.target_completion_date ASC
    """
    goals_progress = fetch_all(complex_sql, (mentee_id,))
    return render_template('reviews/goal_analytics.html', goals_progress=goals_progress)
