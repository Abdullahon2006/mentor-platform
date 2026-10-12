from flask import render_template, request, redirect, url_for, flash
from app.blueprints.reviews import reviews_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, role_required, get_current_user

@reviews_bp.route('/relations/<int:relation_id>/review', methods=['POST'])
@login_required
def submit_review(relation_id):
    """Submit a 1-5 star review and feedback text for a mentorship relation (Member 5 table)."""
    user = get_current_user()
    user_id = user['id']
    rating_val = request.form.get('rating', type=int)
    review_text = request.form.get('review_text', '').strip()

    if not rating_val or rating_val < 1 or rating_val > 5:
        flash("Rating must be an integer between 1 and 5.", "danger")
        return redirect(url_for('relations.relation_detail', relation_id=relation_id))

    # Verify participation
    sql = "SELECT id, mentee_id, mentor_id FROM mentorship_relations WHERE id = %s"
    rel = fetch_one(sql, (relation_id,))
    if not rel or user_id not in (rel['mentee_id'], rel['mentor_id']):
        flash("Unauthorized.", "danger")
        return redirect(url_for('relations.list_relations'))

    reviewee_id = rel['mentor_id'] if user_id == rel['mentee_id'] else rel['mentee_id']

    # Insert review using raw SQL
    insert_sql = """
        INSERT INTO reviews_and_ratings (relation_id, reviewer_id, reviewee_id, rating, review_text)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            rating = VALUES(rating),
            review_text = VALUES(review_text)
    """
    execute_query(insert_sql, (relation_id, user_id, reviewee_id, rating_val, review_text))

    # Notify reviewee
    notif_msg = f"{user['first_name']} {user['last_name']} submitted a review for your mentorship."
    execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)", (reviewee_id, "New Review Received", notif_msg))

    flash("Thank you! Your review has been submitted.", "success")
    return redirect(url_for('relations.relation_detail', relation_id=relation_id))

@reviews_bp.route('/leaderboard')
def leaderboard():
    """
    COMPLEX QUERY 2: Mentor Leaderboard & Engagement Metrics
    Aggregates metrics across users, relations, meetings, and reviews.
    """
    complex_sql = """
        SELECT 
            u.id AS mentor_id,
            CONCAT(u.first_name, ' ', u.last_name) AS mentor_name,
            u.current_title,
            u.organization,
            COUNT(DISTINCT mr.id) AS total_mentorships,
            SUM(CASE WHEN mr.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_mentorships,
            SUM(CASE WHEN mr.status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_mentorships,
            COUNT(DISTINCT m.id) AS total_meetings_held,
            COALESCE(ROUND(AVG(rr.rating), 2), 0.0) AS avg_rating,
            COUNT(DISTINCT rr.id) AS total_reviews_received
        FROM users u
        JOIN mentorship_relations mr ON u.id = mr.mentor_id
        LEFT JOIN meetings m ON mr.id = m.relation_id AND m.status = 'COMPLETED'
        LEFT JOIN reviews_and_ratings rr ON mr.id = rr.relation_id AND rr.reviewee_id = u.id
        WHERE u.role = 'MENTOR'
        GROUP BY u.id, u.first_name, u.last_name, u.current_title, u.organization
        HAVING total_mentorships >= 1
        ORDER BY avg_rating DESC, total_meetings_held DESC
    """
    leaderboard_data = fetch_all(complex_sql)
    return render_template('reviews/leaderboard.html', leaderboard=leaderboard_data)

@reviews_bp.route('/recommendations')
@role_required('MENTEE')
def mentor_recommendations():
    """
    COMPLEX QUERY 1: Multi-Criteria Mentor Recommendation Engine
    Recommends mentors matching current mentee's declared skills and goals.
    """
    user = get_current_user()
    mentee_id = user['id']

    complex_sql = """
        SELECT 
            m.id AS mentor_id,
            CONCAT(m.first_name, ' ', m.last_name) AS mentor_name,
            m.current_title,
            m.organization,
            COUNT(DISTINCT us.skill_id) AS matched_skills_count,
            ROUND(AVG(CASE 
                WHEN us.proficiency = 'EXPERT' THEN 4
                WHEN us.proficiency = 'ADVANCED' THEN 3
                WHEN us.proficiency = 'INTERMEDIATE' THEN 2
                ELSE 1 END), 2) AS avg_skill_score,
            COALESCE(r.avg_rating, 0.0) AS mentor_rating,
            COUNT(DISTINCT rel.id) AS active_mentees_count
        FROM users m
        JOIN user_skills us ON m.id = us.user_id
        LEFT JOIN (
            SELECT reviewee_id, ROUND(AVG(rating), 2) AS avg_rating
            FROM reviews_and_ratings
            GROUP BY reviewee_id
        ) r ON m.id = r.reviewee_id
        LEFT JOIN mentorship_relations rel ON m.id = rel.mentor_id AND rel.status = 'ACTIVE'
        WHERE m.role = 'MENTOR'
          AND us.skill_id IN (
              SELECT skill_id FROM user_skills WHERE user_id = %s
          )
          AND m.id NOT IN (
              SELECT mentor_id FROM mentorship_relations 
              WHERE status = 'ACTIVE' 
              GROUP BY mentor_id HAVING COUNT(*) >= 5
          )
        GROUP BY m.id, m.first_name, m.last_name, m.current_title, m.organization, r.avg_rating
        HAVING matched_skills_count >= 1
        ORDER BY matched_skills_count DESC, avg_skill_score DESC, mentor_rating DESC
    """
    recommendations = fetch_all(complex_sql, (mentee_id,))
    return render_template('reviews/recommendations.html', recommendations=recommendations)

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
