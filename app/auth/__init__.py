# auth directory __init__.py
# auth blueprint용 python module auth/views.py을 타겟

from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views