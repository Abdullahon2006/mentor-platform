from functools import wraps
from flask import session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import fetch_one

def hash_password(password: str) -> str:
    """Hashes a raw password securely using scrypt."""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plain password against its scrypt hash."""
    return check_password_hash(password_hash, password)

def get_current_user():
    """
    Retrieves the currently logged-in user from the database via raw SQL,
    caching it on Flask's `g` request context.
    """
    if 'current_user' not in g:
        user_id = session.get('user_id')
        if user_id:
            raw_sql = """
                SELECT id, email, first_name, last_name, role, bio, current_title, organization, created_at
                FROM users 
                WHERE id = %s
            """
            g.current_user = fetch_one(raw_sql, (user_id,))
        else:
            g.current_user = None
    return g.current_user

def login_required(view_func):
    """Decorator requiring an authenticated session."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    return wrapped_view

def role_required(*allowed_roles):
    """Decorator restricting route access to specific roles (MENTEE, MENTOR, ADMIN)."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not session.get('user_id'):
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            user = get_current_user()
            if not user or user.get('role') not in allowed_roles:
                flash("You do not have permission to access this resource.", "danger")
                return redirect(url_for('profile.dashboard'))
            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator
