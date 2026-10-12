from flask import render_template, request, redirect, url_for, flash, session
from app.blueprints.auth import auth_bp
from app.db import fetch_one, execute_query
from app.auth_util import hash_password, verify_password

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('profile.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', 'MENTEE')
        current_title = request.form.get('current_title', '').strip()
        organization = request.form.get('organization', '').strip()
        bio = request.form.get('bio', '').strip()

        if not email or not password or not first_name or not last_name:
            flash("All required fields must be filled.", "danger")
            return render_template('auth/register.html')

        if role not in ('MENTEE', 'MENTOR'):
            flash("Invalid role selection.", "danger")
            return render_template('auth/register.html')

        # Check existing user using parameterized raw SQL
        existing_sql = "SELECT id FROM users WHERE email = %s"
        existing = fetch_one(existing_sql, (email,))
        if existing:
            flash("An account with this email address already exists.", "warning")
            return render_template('auth/register.html')

        password_hash = hash_password(password)

        insert_sql = """
            INSERT INTO users (email, password_hash, first_name, last_name, role, current_title, organization, bio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        user_id, _ = execute_query(insert_sql, (email, password_hash, first_name, last_name, role, current_title, organization, bio))

        # Create welcome notification
        notif_sql = """
            INSERT INTO notifications (user_id, title, message)
            VALUES (%s, %s, %s)
        """
        execute_query(notif_sql, (user_id, "Welcome to the Mentorship Platform!", "Your account has been created. Start by updating your skills and browsing the platform."))

        flash("Registration successful! Please sign in with your credentials.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('profile.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Parameterized raw SQL query
        user_sql = "SELECT id, email, password_hash, first_name, last_name, role FROM users WHERE email = %s"
        user = fetch_one(user_sql, (email,))

        if user and verify_password(password, user['password_hash']):
            session.clear()
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            flash(f"Welcome back, {user['first_name']}!", "success")
            return redirect(url_for('profile.dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))
