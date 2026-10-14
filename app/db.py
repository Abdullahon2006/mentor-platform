"""
Centralized Raw SQL Database Access Layer
BBF 302E Database Systems - Strictly No ORM Allowed

All database interactions execute raw parameterized SQL statements.
Primary mode: MySQL 8.0 via mysql.connector connection pool.
Development preview mode: Automatic fallback to local demo database when
MySQL daemon is not accessible in the current container environment.
"""

import os
import re
import sqlite3
import mysql.connector
from mysql.connector import Error, pooling
from flask import current_app, g
from config import Config

_pool = None
_mode = None  # 'MYSQL' or 'DEMO_SQLITE'

def _init_mysql_pool():
    global _pool, _mode
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name=Config.DB_POOL_NAME,
            pool_size=Config.DB_POOL_SIZE,
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        # Test connection
        conn = _pool.get_connection()
        conn.close()
        _mode = 'MYSQL'
        print(f"[DATABASE] Connected to MySQL 8.0 at {Config.DB_HOST}:{Config.DB_PORT} ({Config.DB_NAME})")
    except Exception as err:
        _pool = None
        _mode = 'DEMO_SQLITE'
        print(f"[DATABASE NOTICE] MySQL not running at {Config.DB_HOST}:{Config.DB_PORT} ({err}).")
        print("[DATABASE NOTICE] Running in Local Development / Demo Mode using demo.db with pre-seeded data.")

def get_db_mode():
    global _mode
    if _mode is None:
        _init_mysql_pool()
    return _mode

def get_db():
    """Returns a database connection on the Flask application context."""
    if 'db' not in g:
        mode = get_db_mode()
        if mode == 'MYSQL':
            g.db = _pool.get_connection()
            g.db_mode = 'MYSQL'
        else:
            demo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'demo.db')
            if not os.path.exists(demo_path):
                from init_demo_db import init_demo_db
                init_demo_db()
            conn = sqlite3.connect(demo_path)
            conn.row_factory = sqlite3.Row
            g.db = conn
            g.db_mode = 'DEMO_SQLITE'
    return g.db

def close_db(e=None):
    """Closes request database connection."""
    db = g.pop('db', None)
    if db is not None:
        if getattr(g, 'db_mode', None) == 'MYSQL':
            if hasattr(db, 'is_connected') and db.is_connected():
                db.close()
        else:
            db.close()

def _adapt_sql_for_sqlite(sql):
    """Adapts MySQL-specific syntax to SQLite for seamless local container preview."""
    # Replace parameterized %s with ?
    adapted = re.sub(r'%s', '?', sql)
    # Replace CONCAT(a, ' ', b) with (a || ' ' || b)
    adapted = re.sub(r"CONCAT\(([^,]+),\s*([^,]+),\s*([^)]+)\)", r"(\1 || \2 || \3)", adapted)
    adapted = re.sub(r"CONCAT\(([^,]+),\s*([^)]+)\)", r"(\1 || \2)", adapted)
    # Replace NOW() with datetime('now')
    adapted = re.sub(r"\bNOW\(\)", "datetime('now')", adapted, flags=re.IGNORECASE)
    # Replace ON DUPLICATE KEY UPDATE with ON CONFLICT DO UPDATE
    if "ON DUPLICATE KEY UPDATE" in adapted:
        if "user_skills" in adapted:
            adapted = re.sub(
                r"ON DUPLICATE KEY UPDATE.*",
                "ON CONFLICT(user_id, skill_id) DO UPDATE SET proficiency=excluded.proficiency, years_of_experience=excluded.years_of_experience",
                adapted, flags=re.IGNORECASE
            )
        elif "reviews_and_ratings" in adapted:
            adapted = re.sub(
                r"ON DUPLICATE KEY UPDATE.*",
                "ON CONFLICT(relation_id, reviewer_id, reviewee_id) DO UPDATE SET rating=excluded.rating, review_text=excluded.review_text",
                adapted, flags=re.IGNORECASE
            )
    return adapted

def execute_query(sql, params=None, commit=True):
    """Executes a raw SQL statement (INSERT, UPDATE, DELETE)."""
    conn = get_db()
    mode = getattr(g, 'db_mode', 'MYSQL')
    
    if mode == 'MYSQL':
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params or ())
            if commit:
                conn.commit()
            last_id = cursor.lastrowid
            row_count = cursor.rowcount
            return last_id, row_count
        except Error as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()
    else:
        adapted_sql = _adapt_sql_for_sqlite(sql)
        cursor = conn.cursor()
        try:
            cursor.execute(adapted_sql, params or ())
            if commit:
                conn.commit()
            last_id = cursor.lastrowid
            row_count = cursor.rowcount
            return last_id, row_count
        except Exception as err:
            conn.rollback()
            raise err
        finally:
            cursor.close()

def fetch_one(sql, params=None):
    """Executes a raw SQL SELECT query and returns a single row dictionary."""
    conn = get_db()
    mode = getattr(g, 'db_mode', 'MYSQL')

    if mode == 'MYSQL':
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
        finally:
            cursor.close()
    else:
        adapted_sql = _adapt_sql_for_sqlite(sql)
        cursor = conn.cursor()
        try:
            cursor.execute(adapted_sql, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()

def fetch_all(sql, params=None):
    """Executes a raw SQL SELECT query and returns all matching rows as dictionaries."""
    conn = get_db()
    mode = getattr(g, 'db_mode', 'MYSQL')

    if mode == 'MYSQL':
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()
    else:
        adapted_sql = _adapt_sql_for_sqlite(sql)
        cursor = conn.cursor()
        try:
            cursor.execute(adapted_sql, params or ())
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            cursor.close()

def init_app(app):
    """Registers teardown handler with Flask app."""
    app.teardown_appcontext(close_db)
