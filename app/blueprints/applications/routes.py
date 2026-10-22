from datetime import date
from flask import render_template, request, redirect, url_for, flash
from app.blueprints.applications import applications_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, role_required, get_current_user

@applications_bp.route('/mentors')
def browse_mentors():
    """Mentees and visitors can search & filter mentors by skill, keyword, or rating."""
    skill_filter = request.args.get('skill_id', type=int)
    search_query = request.args.get('q', '').strip()

    base_sql = """
        SELECT 
            m.id, m.first_name, m.last_name, m.current_title, m.organization, m.bio,
            COALESCE(r.avg_rating, 0.0) AS avg_rating,
            COALESCE(r.total_reviews, 0) AS total_reviews,
            COUNT(DISTINCT rel.id) AS active_mentees
        FROM users m
        LEFT JOIN (
            SELECT reviewee_id, ROUND(AVG(rating), 2) AS avg_rating, COUNT(id) AS total_reviews
            FROM reviews_and_ratings
            GROUP BY reviewee_id
        ) r ON m.id = r.reviewee_id
        LEFT JOIN mentorship_relations rel ON m.id = rel.mentor_id AND rel.status = 'ACTIVE'
    """
    
    where_clauses = ["m.role = 'MENTOR'"]
    params = []

    if skill_filter:
        base_sql += " JOIN user_skills us ON m.id = us.user_id"
        where_clauses.append("us.skill_id = %s")
        params.append(skill_filter)

    if search_query:
        where_clauses.append("(m.first_name LIKE %s OR m.last_name LIKE %s OR m.current_title LIKE %s OR m.organization LIKE %s)")
        like_pattern = f"%{search_query}%"
        params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

    base_sql += " WHERE " + " AND ".join(where_clauses)
    base_sql += " GROUP BY m.id, m.first_name, m.last_name, m.current_title, m.organization, m.bio, r.avg_rating, r.total_reviews"
    base_sql += " ORDER BY avg_rating DESC, m.first_name ASC"

    mentors = fetch_all(base_sql, tuple(params) if params else None)

    # Fetch all skills for filter dropdown
    skills = fetch_all("SELECT id, name, category FROM skills ORDER BY category, name")

    return render_template('mentors/browse.html', mentors=mentors, skills=skills, selected_skill=skill_filter, search_query=search_query)

@applications_bp.route('/mentors/<int:mentor_id>')
def mentor_detail(mentor_id):
    """View mentor profile details, their skills, availability slots, and reviews."""
    mentor_sql = """
        SELECT id, first_name, last_name, current_title, organization, bio, created_at
        FROM users 
        WHERE id = %s AND role = 'MENTOR'
    """
    mentor = fetch_one(mentor_sql, (mentor_id,))
    if not mentor:
        flash("Mentor not found.", "warning")
        return redirect(url_for('applications.browse_mentors'))

    # Skills of this mentor
    skills_sql = """
        SELECT s.name, s.category, us.proficiency, us.years_of_experience
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.user_id = %s
        ORDER BY s.category, s.name
    """
    mentor_skills = fetch_all(skills_sql, (mentor_id,))

    # Availability blocks
    avail_sql = """
        SELECT day_of_week, start_time, end_time
        FROM mentor_availability
        WHERE mentor_id = %s AND is_active = TRUE
        ORDER BY day_of_week, start_time
    """
    availability = fetch_all(avail_sql, (mentor_id,))

    # Past reviews
    reviews_sql = """
        SELECT rr.rating, rr.review_text, rr.created_at, u.first_name, u.last_name
        FROM reviews_and_ratings rr
        JOIN users u ON rr.reviewer_id = u.id
        WHERE rr.reviewee_id = %s
        ORDER BY rr.created_at DESC
    """
    reviews = fetch_all(reviews_sql, (mentor_id,))

    # Check if current mentee already has an active or pending application
    user = get_current_user()
    existing_app = None
    if user and user['role'] == 'MENTEE':
        existing_sql = """
            SELECT id, status FROM mentorship_applications
            WHERE mentee_id = %s AND mentor_id = %s AND status IN ('PENDING', 'ACCEPTED')
            ORDER BY created_at DESC LIMIT 1
        """
        existing_app = fetch_one(existing_sql, (user['id'], mentor_id))

    return render_template(
        'mentors/detail.html',
        mentor=mentor,
        mentor_skills=mentor_skills,
        availability=availability,
        reviews=reviews,
        existing_app=existing_app
    )

@applications_bp.route('/goals/manage', methods=['GET', 'POST'])
@role_required('MENTEE')
def manage_goals():
    """Mentee management of milestone goals (Member 3 table: mentorship_goals)."""
    user = get_current_user()
    user_id = user['id']

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            target_date = request.form.get('target_date') or None

            if not title:
                flash("Goal title is required.", "danger")
            else:
                insert_sql = """
                    INSERT INTO mentorship_goals (mentee_id, title, description, target_completion_date)
                    VALUES (%s, %s, %s, %s)
                """
                execute_query(insert_sql, (user_id, title, description, target_date))
                flash("Goal created successfully!", "success")
        
        elif action == 'update_status':
            goal_id = request.form.get('goal_id')
            new_status = request.form.get('status')
            if new_status in ('ACTIVE', 'ACHIEVED', 'ABANDONED'):
                update_sql = "UPDATE mentorship_goals SET status = %s WHERE id = %s AND mentee_id = %s"
                execute_query(update_sql, (new_status, goal_id, user_id))
                flash("Goal status updated.", "info")

        elif action == 'delete':
            goal_id = request.form.get('goal_id')
            delete_sql = "DELETE FROM mentorship_goals WHERE id = %s AND mentee_id = %s"
            execute_query(delete_sql, (goal_id, user_id))
            flash("Goal removed.", "info")

        return redirect(url_for('applications.manage_goals'))

    # Complex Query 3: Mentee Goal Progress & Activity Correlation
    goals_sql = """
        SELECT 
            g.id, g.title, g.description, g.target_completion_date, g.status, g.created_at,
            COALESCE(CONCAT(m.first_name, ' ', m.last_name), 'No Mentor Assigned') AS assigned_mentor,
            m.id AS mentor_id,
            COUNT(DISTINCT mt.id) AS total_completed_sessions,
            MAX(mt.scheduled_start) AS latest_session_date
        FROM mentorship_goals g
        LEFT JOIN mentorship_applications ma 
            ON g.id = ma.goal_id AND ma.status = 'ACCEPTED'
        LEFT JOIN mentorship_relations mr 
            ON ma.id = mr.application_id
        LEFT JOIN users m 
            ON mr.mentor_id = m.id
        LEFT JOIN meetings mt 
            ON mr.id = mt.relation_id AND mt.status = 'COMPLETED'
        WHERE g.mentee_id = %s
        GROUP BY 
            g.id, g.title, g.description, g.target_completion_date, g.status, g.created_at,
            m.id, m.first_name, m.last_name
        ORDER BY g.created_at DESC
    """
    goals = fetch_all(goals_sql, (user_id,))
    return render_template('applications/goals.html', goals=goals)

@applications_bp.route('/apply/<int:mentor_id>', methods=['GET', 'POST'])
@role_required('MENTEE')
def apply_to_mentor(mentor_id):
    """Mentee submits an application to a mentor referencing an active goal."""
    user = get_current_user()
    mentee_id = user['id']

    mentor = fetch_one("SELECT id, first_name, last_name, current_title, organization FROM users WHERE id = %s AND role = 'MENTOR'", (mentor_id,))
    if not mentor:
        flash("Invalid mentor.", "danger")
        return redirect(url_for('applications.browse_mentors'))

    if request.method == 'POST':
        goal_id = request.form.get('goal_id') or None
        message = request.form.get('message', '').strip()

        if not message:
            flash("Please write a brief motivation note.", "warning")
            return redirect(url_for('applications.apply_to_mentor', mentor_id=mentor_id))

        insert_sql = """
            INSERT INTO mentorship_applications (mentee_id, mentor_id, goal_id, message, status)
            VALUES (%s, %s, %s, %s, 'PENDING')
        """
        app_id, _ = execute_query(insert_sql, (mentee_id, mentor_id, goal_id, message))

        # Notify mentor
        notif_sql = """
            INSERT INTO notifications (user_id, title, message)
            VALUES (%s, %s, %s)
        """
        notif_msg = f"You received a new mentorship application from {user['first_name']} {user['last_name']}."
        execute_query(notif_sql, (mentor_id, "New Mentorship Application", notif_msg))

        flash("Application sent successfully! You will be notified when the mentor responds.", "success")
        return redirect(url_for('applications.list_applications'))

    # Fetch mentee active goals
    goals = fetch_all("SELECT id, title FROM mentorship_goals WHERE mentee_id = %s AND status = 'ACTIVE'", (mentee_id,))
    return render_template('applications/apply.html', mentor=mentor, goals=goals)

@applications_bp.route('/applications')
@login_required
def list_applications():
    """List applications for either mentee or mentor."""
    user = get_current_user()
    user_id = user['id']
    role = user['role']

    if role == 'MENTEE':
        sql = """
            SELECT ma.id, ma.status, ma.message, ma.created_at, ma.decided_at,
                   m.id AS mentor_id, m.first_name AS mentor_first, m.last_name AS mentor_last, m.current_title,
                   mg.title AS goal_title
            FROM mentorship_applications ma
            JOIN users m ON ma.mentor_id = m.id
            LEFT JOIN mentorship_goals mg ON ma.goal_id = mg.id
            WHERE ma.mentee_id = %s
            ORDER BY ma.created_at DESC
        """
        apps = fetch_all(sql, (user_id,))
        return render_template('applications/mentee_applications.html', applications=apps)

    elif role == 'MENTOR':
        sql = """
            SELECT ma.id, ma.status, ma.message, ma.created_at, ma.decided_at,
                   u.id AS mentee_id, u.first_name AS mentee_first, u.last_name AS mentee_last, u.organization,
                   mg.title AS goal_title, mg.description AS goal_desc
            FROM mentorship_applications ma
            JOIN users u ON ma.mentee_id = u.id
            LEFT JOIN mentorship_goals mg ON ma.goal_id = mg.id
            WHERE ma.mentor_id = %s
            ORDER BY (ma.status = 'PENDING') DESC, ma.created_at DESC
        """
        apps = fetch_all(sql, (user_id,))
        return render_template('applications/mentor_applications.html', applications=apps)

    else:
        # Admin view of all applications
        sql = """
            SELECT ma.id, ma.status, ma.created_at,
                   mentee.first_name AS mentee_first, mentee.last_name AS mentee_last,
                   mentor.first_name AS mentor_first, mentor.last_name AS mentor_last
            FROM mentorship_applications ma
            JOIN users mentee ON ma.mentee_id = mentee.id
            JOIN users mentor ON ma.mentor_id = mentor.id
            ORDER BY ma.created_at DESC
        """
        apps = fetch_all(sql)
        return render_template('applications/admin_applications.html', applications=apps)

@applications_bp.route('/applications/<int:app_id>/decide', methods=['POST'])
@role_required('MENTOR')
def decide_application(app_id):
    """Mentor accepts or rejects a pending application."""
    user = get_current_user()
    mentor_id = user['id']
    decision = request.form.get('decision')  # 'ACCEPTED' or 'REJECTED'

    if decision not in ('ACCEPTED', 'REJECTED'):
        flash("Invalid decision.", "danger")
        return redirect(url_for('applications.list_applications'))

    # Verify application belongs to this mentor and is PENDING
    app_sql = "SELECT id, mentee_id, status FROM mentorship_applications WHERE id = %s AND mentor_id = %s"
    application = fetch_one(app_sql, (app_id, mentor_id))

    if not application:
        flash("Application not found or unauthorized.", "danger")
        return redirect(url_for('applications.list_applications'))

    if application['status'] != 'PENDING':
        flash("This application has already been processed.", "warning")
        return redirect(url_for('applications.list_applications'))

    # Update application status
    update_sql = """
        UPDATE mentorship_applications 
        SET status = %s, decided_at = NOW()
        WHERE id = %s
    """
    execute_query(update_sql, (decision, app_id))

    mentee_id = application['mentee_id']

    if decision == 'ACCEPTED':
        # Create active mentorship relationship in mentorship_relations (Member 4 table)
        rel_sql = """
            INSERT INTO mentorship_relations (application_id, mentee_id, mentor_id, start_date, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
        """
        execute_query(rel_sql, (app_id, mentee_id, mentor_id, date.today()))

        # Send notification to mentee
        notif_msg = f"{user['first_name']} {user['last_name']} accepted your mentorship application! You can now schedule meetings."
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)", (mentee_id, "Application Accepted!", notif_msg))
        flash("Application accepted! An active mentorship relationship has been established.", "success")
    else:
        notif_msg = f"{user['first_name']} {user['last_name']} was unable to accept your application at this time."
        execute_query("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)", (mentee_id, "Application Update", notif_msg))
        flash("Application declined.", "info")

    return redirect(url_for('applications.list_applications'))

@applications_bp.route('/applications/<int:app_id>/withdraw', methods=['POST'])
@role_required('MENTEE')
def withdraw_application(app_id):
    """Mentee withdraws a pending application."""
    user = get_current_user()
    mentee_id = user['id']

    app_record = fetch_one(
        "SELECT id, mentor_id, status FROM mentorship_applications WHERE id = %s AND mentee_id = %s",
        (app_id, mentee_id)
    )
    if not app_record:
        flash("Application not found or unauthorized.", "danger")
        return redirect(url_for('applications.list_applications'))

    if app_record['status'] != 'PENDING':
        flash("Only pending applications can be withdrawn.", "warning")
        return redirect(url_for('applications.list_applications'))

    execute_query(
        "UPDATE mentorship_applications SET status = 'WITHDRAWN', decided_at = NOW() WHERE id = %s",
        (app_id,)
    )

    notif_msg = f"{user['first_name']} {user['last_name']} withdrew their mentorship application."
    execute_query(
        "INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
        (app_record['mentor_id'], "Application Withdrawn", notif_msg)
    )

    flash("Application withdrawn successfully.", "info")
    return redirect(url_for('applications.list_applications'))
