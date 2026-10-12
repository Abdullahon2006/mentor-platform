from flask import render_template, request, redirect, url_for, flash
from app.blueprints.skills import skills_bp
from app.db import fetch_one, fetch_all, execute_query
from app.auth_util import login_required, role_required, get_current_user

@skills_bp.route('/')
def list_skills():
    """Lists all skills categorized in the taxonomy."""
    sql = """
        SELECT s.id, s.name, s.category, s.description, COUNT(us.id) AS user_count
        FROM skills s
        LEFT JOIN user_skills us ON s.id = us.skill_id
        GROUP BY s.id, s.name, s.category, s.description
        ORDER BY s.category, s.name
    """
    skills = fetch_all(sql)
    return render_template('skills/index.html', skills=skills)

@skills_bp.route('/manage', methods=['GET', 'POST'])
@login_required
def manage_user_skills():
    """Allows current user to add or update skills on their profile."""
    user = get_current_user()
    user_id = user['id']

    if request.method == 'POST':
        skill_id = request.form.get('skill_id')
        proficiency = request.form.get('proficiency', 'INTERMEDIATE')
        years_of_experience = request.form.get('years_of_experience', 0)

        try:
            years_exp = max(0, int(years_of_experience))
        except ValueError:
            years_exp = 0

        if not skill_id:
            flash("Please select a skill.", "warning")
            return redirect(url_for('skills.manage_user_skills'))

        # Insert or update using raw SQL
        upsert_sql = """
            INSERT INTO user_skills (user_id, skill_id, proficiency, years_of_experience)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                proficiency = VALUES(proficiency),
                years_of_experience = VALUES(years_of_experience)
        """
        execute_query(upsert_sql, (user_id, skill_id, proficiency, years_exp))
        flash("Skill successfully updated on your profile!", "success")
        return redirect(url_for('skills.manage_user_skills'))

    # Fetch available skills not yet chosen, or all skills
    all_skills_sql = "SELECT id, name, category FROM skills ORDER BY category, name"
    all_skills = fetch_all(all_skills_sql)

    user_skills_sql = """
        SELECT us.id, s.name, s.category, us.proficiency, us.years_of_experience
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        WHERE us.user_id = %s
        ORDER BY s.category, s.name
    """
    current_skills = fetch_all(user_skills_sql, (user_id,))

    return render_template(
        'skills/manage.html',
        all_skills=all_skills,
        current_skills=current_skills,
        user=user
    )

@skills_bp.route('/remove/<int:user_skill_id>', methods=['POST'])
@login_required
def remove_user_skill(user_skill_id):
    """Deletes a skill endorsement from user's profile."""
    user = get_current_user()
    delete_sql = "DELETE FROM user_skills WHERE id = %s AND user_id = %s"
    execute_query(delete_sql, (user_skill_id, user['id']))
    flash("Skill removed from your profile.", "info")
    return redirect(url_for('skills.manage_user_skills'))

@skills_bp.route('/admin/create', methods=['POST'])
@role_required('ADMIN')
def admin_create_skill():
    """Admin-only endpoint to add a new skill to the platform catalog."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()

    if not name or not category:
        flash("Skill name and category are required.", "danger")
        return redirect(url_for('skills.list_skills'))

    insert_sql = "INSERT INTO skills (name, category, description) VALUES (%s, %s, %s)"
    try:
        execute_query(insert_sql, (name, category, description))
        flash(f"Skill '{name}' successfully created in taxonomy.", "success")
    except Exception as err:
        flash(f"Could not create skill: {err}", "danger")

    return redirect(url_for('skills.list_skills'))
