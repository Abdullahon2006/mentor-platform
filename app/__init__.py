import os
from flask import Flask, render_template, g, session
from config import Config
from app import db
from app.auth_util import get_current_user

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize raw SQL database teardown hooks
    db.init_app(app)

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.profile import profile_bp
    from app.blueprints.skills import skills_bp
    from app.blueprints.applications import applications_bp
    from app.blueprints.relations import relations_bp
    from app.blueprints.schedule import schedule_bp
    from app.blueprints.reviews import reviews_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(relations_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(admin_bp)

    # Context processors for all Jinja2 templates
    @app.context_processor
    def inject_global_data():
        current_u = None
        unread_notifs = 0
        try:
            current_u = get_current_user()
            if current_u:
                count_res = db.fetch_one(
                    "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = FALSE",
                    (current_u['id'],)
                )
                if count_res:
                    unread_notifs = count_res['cnt']
        except Exception:
            pass
        return {
            'current_user': current_u,
            'unread_notifications_count': unread_notifs
        }

    # Custom error handler for database connection failures
    @app.errorhandler(ConnectionError)
    @app.errorhandler(Exception)
    def handle_db_error(e):
        # Only catch ConnectionError or MySQL Errors for custom page
        err_msg = str(e)
        if "Can't connect to MySQL" in err_msg or "Failed to connect to MySQL" in err_msg or "2002" in err_msg:
            return render_template(
                'db_error.html',
                error_message=err_msg,
                db_host=app.config.get('DB_HOST'),
                db_port=app.config.get('DB_PORT'),
                db_name=app.config.get('DB_NAME')
            ), 500
        # Re-raise standard exceptions in debug mode
        if app.debug and not isinstance(e, ConnectionError):
            raise e
        return render_template('500.html', error=err_msg), 500

    return app
