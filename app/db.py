"""
Centralized Raw SQL Database Access Layer
BBF 302E Database Systems - Strictly No ORM Allowed

All database interactions MUST execute raw parameterized SQL statements
via mysql.connector cursors. No Object-Relational Mappers (e.g. SQLAlchemy ORM)
are utilized in this codebase.
"""

import mysql.connector
from mysql.connector import Error, pooling
from flask import current_app, g
from config import Config

_pool = None

def get_connection_pool():
    """Initializes or returns the MySQL connection pool."""
    global _pool
    if _pool is None:
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
        except Error as err:
            raise ConnectionError(
                f"Failed to connect to MySQL database at {Config.DB_HOST}:{Config.DB_PORT}. "
                f"Error: {err}. Please ensure MySQL is running and credentials in config.py are correct."
            )
    return _pool

def get_db():
    """Returns a pooled database connection stored on the Flask application context."""
    if 'db' not in g:
        pool = get_connection_pool()
        g.db = pool.get_connection()
    return g.db

def close_db(e=None):
    """Closes the current request's database connection and returns it to the pool."""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

def execute_query(sql, params=None, commit=True):
    """
    Executes a raw SQL statement (INSERT, UPDATE, DELETE).
    Returns (lastrowid, rowcount).
    """
    conn = get_db()
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

def fetch_one(sql, params=None):
    """
    Executes a raw SQL SELECT query and returns a single row dictionary (or None).
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()

def fetch_all(sql, params=None):
    """
    Executes a raw SQL SELECT query and returns all matching rows as dictionaries.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()

def init_app(app):
    """Registers the teardown handler with the Flask application."""
    app.teardown_appcontext(close_db)
