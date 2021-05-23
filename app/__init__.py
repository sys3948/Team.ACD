# __init__.py
# application factory python module

from flask import Flask
from flask_mail import Mail
from config import config, DevelopmentConfig,Config
from celery import Celery


mail = Mail()


celery = Celery(__name__,broker=Config.CELERY_BROKER_URL,backend=Config.CELERY_RESULT_BACKEND)

def create_app(config_name):
    app = Flask(__name__)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    mail.init_app(app)

    
    celery.conf.update(app.config)
    
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .dbide import dbide as dbide_blueprint
    app.register_blueprint(dbide_blueprint)
    

    return app

