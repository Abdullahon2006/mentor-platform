from flask import render_template, request, redirect, url_for, flash
from app.blueprints.admin import admin_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import role_required, get_current_user

@admin_bp.route('/')
@role_required('ADMIN')
def index():
    """Admin dashboard with high-level statistics and recent user registrations."""
    stats_sql = """
        SELECT 
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM users WHERE role = 'MENTEE') AS mentees_count,
            (SELECT COUNT(*) FROM users WHERE role = 'MENTOR') AS mentors_count,
            (SELECT COUNT(*) FROM mentorship_relations WHERE status = 'ACTIVE') AS active_relations_count,
            (SELECT COUNT(*) FROM meetings WHERE status = 'COMPLETED') AS completed_meetings_count,
            (SELECT COUNT(*) FROM reviews_and_ratings) AS total_reviews_count
    """
    stats = fetch_one(stats_sql)

    users_sql = """
        SELECT id, email, first_name, last_name, role, current_title, organization, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 15
    """
    recent_users = fetch_all(users_sql)

    return render_template('admin/index.html', stats=stats, recent_users=recent_users)

@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@role_required('ADMIN')
def change_user_role(user_id):
    """Admin endpoint to modify user role."""
    new_role = request.form.get('role')
    if new_role in ('MENTEE', 'MENTOR', 'ADMIN'):
        execute_query("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        flash("User role updated successfully.", "success")
    return redirect(url_for('admin.index'))
