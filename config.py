import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bbf302e-mentor-platform-secret-key-2026')
    
    # Relational Database Connection (MySQL 8.0)
    # Strictly Raw SQL - No ORM Allowed
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'mentor_platform')
    
    # Connection Pool Settings
    DB_POOL_NAME = 'mentor_pool'
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))
    
    # Application Mode
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1')
