from flask import render_template, request, redirect, url_for, flash
from flask import g
from app.blueprints.skills import skills_bp
from app.db import fetch_one, fetch_all, execute_query, get_db
from app.auth_util import login_required, role_required, get_current_user

@skills_bp.route('/')
def list_skills():
    """Lists skills with optional name search and category filtering."""

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    sql = """
        SELECT s.id, s.name, s.category, s.description,
               COUNT(us.id) AS user_count
        FROM skills s
        LEFT JOIN user_skills us ON s.id = us.skill_id
        WHERE 1 = 1
    """
    params = []

    if search:
        sql += " AND s.name LIKE %s"
        params.append(f"%{search}%")

    if category:
        sql += " AND s.category = %s"
        params.append(category)

    sql += """
        GROUP BY s.id, s.name, s.category, s.description
        ORDER BY s.category, s.name
    """

    skills = fetch_all(sql, tuple(params))

    categories = fetch_all(
        "SELECT DISTINCT category FROM skills ORDER BY category"
    )

    return render_template(
        'skills/index.html',
        skills=skills,
        categories=categories,
        selected_category=category,
        search=search
    )

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


        valid_proficiencies = {
            'BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT'
        }

        if proficiency not in valid_proficiencies:
            flash("Invalid proficiency level selected.", "danger")
            return redirect(url_for('skills.manage_user_skills'))

        try:
            years_exp = int(years_of_experience)
            if years_exp < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Years of experience must be a non-negative integer.", "danger")
            return redirect(url_for('skills.manage_user_skills'))


        if not skill_id:
            flash("Please select a skill.", "warning")
            return redirect(url_for('skills.manage_user_skills'))


        try:
            skill_id = int(skill_id)
            if skill_id <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Invalid skill selected.", "danger")
            return redirect(url_for('skills.manage_user_skills'))

        skill = fetch_one(
            "SELECT id FROM skills WHERE id = %s",
            (skill_id,)
        )

        if skill is None:
            flash("The selected skill does not exist.", "danger")
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

@skills_bp.route('/recommendations')
@role_required('MENTEE')
def mentor_recommendations():
    """
    COMPLEX QUERY 2 (CQ-02): Multi-Criteria Mentor Recommendation Engine
    Recommends mentors matching current mentee's declared skills and goals.
    """
    user = get_current_user()
    mentee_id = user['id']

    category = request.args.get('category', '').strip()

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
        JOIN skills s ON us.skill_id = s.id
        LEFT JOIN (
            SELECT reviewee_id, ROUND(AVG(rating), 2) AS avg_rating
            FROM reviews_and_ratings
            GROUP BY reviewee_id
        ) r ON m.id = r.reviewee_id
        LEFT JOIN mentorship_relations rel ON m.id = rel.mentor_id AND rel.status = 'ACTIVE'
        WHERE m.role = 'MENTOR'
        AND (%s = '' OR s.category = %s)
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

    recommendations = fetch_all(
        complex_sql,
        (category, category, mentee_id)
    )

    categories = fetch_all(
        "SELECT DISTINCT category FROM skills ORDER BY category"
    )

    return render_template(
        'reviews/recommendations.html',
        recommendations=recommendations,
        categories=categories,
        selected_category=category
    )

@skills_bp.route('/admin/<int:skill_id>/edit', methods=['POST'])
@role_required('ADMIN')
def admin_edit_skill(skill_id):
    """Allows admins to edit an existing skill."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    if not name or not category:
        flash("Skill name and category are required.", "danger")
        return redirect(url_for('skills.list_skills'))
    skill = fetch_one(
        "SELECT id FROM skills WHERE id = %s",
        (skill_id,)
    )
    if skill is None:
        flash("The selected skill does not exist.", "danger")
        return redirect(url_for('skills.list_skills'))
    update_sql = """
        UPDATE skills
        SET name = %s, category = %s, description = %s
        WHERE id = %s
    """

    try:
        execute_query(update_sql, (name, category, description, skill_id))
        flash(f"Skill '{name}' successfully updated.", "success")
    except Exception:
        flash("Could not update skill. The skill name may already exist.", "danger")

    return redirect(url_for('skills.list_skills'))

@skills_bp.route('/admin/<int:skill_id>/delete', methods=['POST'])
@role_required('ADMIN')
def admin_delete_skill(skill_id):
    """Allows admins to delete a skill from the taxonomy."""
    conn = get_db()
    mode = g.db_mode

    try:
        if mode == 'DEMO_SQLITE':
            conn.execute("BEGIN IMMEDIATE")

        skill = fetch_one(
            "SELECT id, name FROM skills WHERE id = %s"
            + (" FOR UPDATE" if mode == 'MYSQL' else ""),
            (skill_id,)
        )

        if skill is None:
            conn.rollback()
            flash("The selected skill does not exist.", "danger")
            return redirect(url_for('skills.list_skills'))

        assigned_users = fetch_one(
            "SELECT COUNT(*) AS total FROM user_skills WHERE skill_id = %s",
            (skill_id,)
        )

        if assigned_users['total'] > 0:
            conn.rollback()
            flash(
                "Cannot delete this skill because it is assigned to users.",
                "danger"
            )
            return redirect(url_for('skills.list_skills'))

        execute_query(
            "DELETE FROM skills WHERE id = %s",
            (skill_id,),
            commit=False
        )

        conn.commit()
        flash(f"Skill '{skill['name']}' successfully deleted.", "success")

    except Exception:
        conn.rollback()
        flash("Could not delete the skill.", "danger")

    return redirect(url_for('skills.list_skills'))
