# dbide directory __init__.py
# dbide blueprint용 module target은 dbide/views.py

from flask import Blueprint

dbide = Blueprint('dbide', __name__)

from . import views