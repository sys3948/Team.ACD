from functools import wraps
from flask import redirect,url_for,session


def login_check(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if not 'id' in session:
                return redirect(url_for('auth.sign_in'))

            return func(*args, **kwargs)
        except Exception as e:
            raise e

    return wrapper