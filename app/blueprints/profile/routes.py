from flask import render_template, request, redirect, url_for, flash, session
from app.blueprints.profile import profile_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, get_current_user

@profile_bp.route('/')
def home():
    if session.get('user_id'):
        return redirect(url_for('profile.dashboard'))
    return redirect(url_for('auth.login'))

@profile_bp.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    user_id = user['id']
    role = user['role']

    # 1. Fetch unread and recent notifications (Member 1 table: notifications)
    notif_sql = """
        SELECT id, title, message, is_read, created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 5
    """
    notifications = fetch_all(notif_sql, (user_id,))

    # 2. Fetch user skills (Member 2 tables: skills, user_skills)
    skills_sql = """
        SELECT us.id AS user_skill_id, s.name, s.category, us.proficiency, us.years_of_experience
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.user_id = %s
        ORDER BY s.category, s.name
    """
    user_skills = fetch_all(skills_sql, (user_id,))

    # 3. Role-specific stats and active relationships
    if role == 'MENTEE':
        # Mentee active goals (Member 3 table: mentorship_goals)
        goals_sql = """
            SELECT id, title, description, target_completion_date, status
            FROM mentorship_goals
            WHERE mentee_id = %s
            ORDER BY target_completion_date ASC
        """
        goals = fetch_all(goals_sql, (user_id,))

        # Active applications
        apps_sql = """
            SELECT ma.id, ma.status, ma.created_at, u.first_name, u.last_name, u.current_title, mg.title AS goal_title
            FROM mentorship_applications ma
            JOIN users u ON ma.mentor_id = u.id
            LEFT JOIN mentorship_goals mg ON ma.goal_id = mg.id
            WHERE ma.mentee_id = %s
            ORDER BY ma.created_at DESC
            LIMIT 5
        """
        recent_apps = fetch_all(apps_sql, (user_id,))

        # Active relationships (Member 4 table)
        rel_sql = """
            SELECT mr.id, mr.start_date, mr.status, u.first_name, u.last_name, u.current_title, u.organization
            FROM mentorship_relations mr
            JOIN users u ON mr.mentor_id = u.id
            WHERE mr.mentee_id = %s AND mr.status = 'ACTIVE'
        """
        active_relations = fetch_all(rel_sql, (user_id,))

        # Upcoming meetings (Member 5 table: meetings)
        meetings_sql = """
            SELECT m.id, m.scheduled_start, m.scheduled_end, m.meeting_link, m.agenda, m.status,
                   u.first_name, u.last_name
            FROM meetings m
            JOIN mentorship_relations mr ON m.relation_id = mr.id
            JOIN users u ON mr.mentor_id = u.id
            WHERE mr.mentee_id = %s AND m.status = 'SCHEDULED' AND m.scheduled_start >= NOW()
            ORDER BY m.scheduled_start ASC
            LIMIT 5
        """
        upcoming_meetings = fetch_all(meetings_sql, (user_id,))

        return render_template(
            'dashboard/mentee_dashboard.html',
            user=user,
            notifications=notifications,
            user_skills=user_skills,
            goals=goals,
            recent_apps=recent_apps,
            active_relations=active_relations,
            upcoming_meetings=upcoming_meetings
        )

    elif role == 'MENTOR':
        # Pending applications requiring mentor decision
        apps_sql = """
            SELECT ma.id, ma.message, ma.created_at, u.first_name, u.last_name, mg.title AS goal_title
            FROM mentorship_applications ma
            JOIN users u ON ma.mentee_id = u.id
            LEFT JOIN mentorship_goals mg ON ma.goal_id = mg.id
            WHERE ma.mentor_id = %s AND ma.status = 'PENDING'
            ORDER BY ma.created_at ASC
        """
        pending_apps = fetch_all(apps_sql, (user_id,))

        # Active relationships
        rel_sql = """
            SELECT mr.id, mr.start_date, mr.status, u.first_name, u.last_name, u.organization
            FROM mentorship_relations mr
            JOIN users u ON mr.mentee_id = u.id
            WHERE mr.mentor_id = %s AND mr.status = 'ACTIVE'
        """
        active_relations = fetch_all(rel_sql, (user_id,))

        # Upcoming meetings
        meetings_sql = """
            SELECT m.id, m.scheduled_start, m.scheduled_end, m.meeting_link, m.agenda, m.status,
                   u.first_name, u.last_name
            FROM meetings m
            JOIN mentorship_relations mr ON m.relation_id = mr.id
            JOIN users u ON mr.mentee_id = u.id
            WHERE mr.mentor_id = %s AND m.status = 'SCHEDULED' AND m.scheduled_start >= NOW()
            ORDER BY m.scheduled_start ASC
            LIMIT 5
        """
        upcoming_meetings = fetch_all(meetings_sql, (user_id,))

        # Mentor rating summary
        rating_sql = """
            SELECT COUNT(*) AS total_reviews, COALESCE(ROUND(AVG(rating), 2), 0.0) AS avg_rating
            FROM reviews_and_ratings
            WHERE reviewee_id = %s
        """
        rating_info = fetch_one(rating_sql, (user_id,))

        return render_template(
            'dashboard/mentor_dashboard.html',
            user=user,
            notifications=notifications,
            user_skills=user_skills,
            pending_apps=pending_apps,
            active_relations=active_relations,
            upcoming_meetings=upcoming_meetings,
            rating_info=rating_info
        )

    else:
        # Admin dashboard
        counts_sql = """
            SELECT 
                (SELECT COUNT(*) FROM users WHERE role = 'MENTEE') AS mentee_count,
                (SELECT COUNT(*) FROM users WHERE role = 'MENTOR') AS mentor_count,
                (SELECT COUNT(*) FROM mentorship_relations WHERE status = 'ACTIVE') AS active_relations_count,
                (SELECT COUNT(*) FROM meetings WHERE status = 'COMPLETED') AS completed_meetings_count,
                (SELECT COUNT(*) FROM skills) AS skills_count
        """
        stats = fetch_one(counts_sql)
        return render_template('dashboard/admin_dashboard.html', user=user, stats=stats, notifications=notifications)

@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = get_current_user()
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        current_title = request.form.get('current_title', '').strip()
        organization = request.form.get('organization', '').strip()
        bio = request.form.get('bio', '').strip()

        update_sql = """
            UPDATE users 
            SET first_name = %s, last_name = %s, current_title = %s, organization = %s, bio = %s
            WHERE id = %s
        """
        execute_query(update_sql, (first_name, last_name, current_title, organization, bio, user['id']))
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile.dashboard'))

    return render_template('dashboard/edit_profile.html', user=user)

@profile_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user = get_current_user()
    update_sql = "UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s"
    execute_query(update_sql, (notif_id, user['id']))
    return redirect(url_for('profile.dashboard'))
