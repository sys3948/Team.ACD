from functools import wraps
from flask import redirect,url_for,session,flash
from .database import Database


def login_check(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if not 'id' in session and not 'confirmed' in session:
                return redirect(url_for('auth.sign_in'))

            return func(*args, **kwargs)
        except Exception as e:
            raise e

    return wrapper

#관리자 체크
def manager_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            mysql_db = Database()
            cur_user = mysql_db.excuteOne('SELECT manager FROM user WHERE id=%s',(session.get('id'),))
            mysql_db.close()
            if  cur_user:
                if cur_user[0] == 0:
                    flash('접속 권한이 없습니다.')
                    return redirect(url_for('dbide.main'))
                else:
                    return func(*args, **kwargs)
            else: 
                return redirect(url_for('dbide.main'))

        except Exception as e:
            raise e

    return wrapper




