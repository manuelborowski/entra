from flask import Blueprint

logging = Blueprint('logging', __name__)

from . import views
