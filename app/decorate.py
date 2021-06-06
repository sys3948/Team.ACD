from functools import wraps
from flask import redirect,url_for,session,flash
from .database import Database
from app import database


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


def connect_db(func):
    '''
    user_info 테이블 정보 조회후,
    해당 정보로 db 연결
    '''

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            cur = Database()

            db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema,inner_num \
                             from dbms_info \
                             where db_id = %s', (kwargs.get('id'),))

            if db_info[0] == 'mongo':
                user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3], database = '')
            else:
                user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3],database = db_info[5])
            
            kwargs['dbms_info'] = {'user_db':user_db,'db_info':db_info}
            cur.close()                 
            return func(*args,**kwargs)

        except Exception as e:
            raise e

    return wrapper



