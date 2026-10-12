from flask import Blueprint

skills_bp = Blueprint('skills', __name__, url_prefix='/skills')

from . import routes
