from flask import Blueprint

relations_bp = Blueprint('relations', __name__, url_prefix='/relations')

from . import routes
