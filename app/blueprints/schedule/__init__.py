from flask import Blueprint

schedule_bp = Blueprint('schedule', __name__)

from . import routes
