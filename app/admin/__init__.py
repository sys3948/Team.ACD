# admin directory __init__.py
# admin blueprint용 python module admin/views.py을 타겟

from flask import Blueprint

admin = Blueprint('admin', __name__)

from . import views