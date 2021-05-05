## dbide directory views.py
# dbms 내/외부 접속, 쿼리 실행(전공자 & 비전공자) 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, render_template, request, session, url_for, redirect, jsonify
from . import dbide
import mysql.connector as mysql
from ..database import MysqlDatabase
from ..decorate import login_check

@dbide.route('/')
@dbide.route('/main')
@login_check
def main():
    if session.get('confirmed') == 0:
        email = session.get('email')
    else:
        email = None
        cur = MysqlDatabase()
        out_dbms_info = cur.excuteAll('select db_id, dbms, hostname, port_num, alias, \
                                              dbms_connect_username, dbms_schema, \
                                              stampdatetime \
                                   from dbms_info \
                                   where user_id = %s \
                                   and inner_num = 0 \
                                   order by stampdatetime', (session.get('id'),))
        inner_dbms_info = cur.excuteAll('select db_id, dbms \
                                   from dbms_info \
                                   where user_id = %s \
                                   and inner_num = 1', (session.get('id'),))
        cur.close()

        print(out_dbms_info == True)
        print(out_dbms_info)
    return render_template('main.html', email = email, out_dbms_info = out_dbms_info, \
                           inner_dbms_info = inner_dbms_info)


@login_check
@dbide.route('/connect_dbms')
def connect_dbms():
    return render_template('connect_dbms.html')


@login_check
@dbide.route('/execute_query/<id>')
def execute_query(id):
    cur = MysqlDatabase()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema \
                             from dbms_info \
                             where db_id = %s', (id,))

    if db_info[0] == 'mysql':
        db_conn = mysql.connect(host = db_info[1], port = db_info[2], user = db_info[4], passwd = db_info[3], database = db_info[6])
    elif db_info[0] == 'maria':
        pass
    elif db_info[0] == 'oracle':
        pass
    elif db_info[0] == 'mongo':
        pass

    db_cur = db_conn.cursor()
    db_cur.execute('show tables')
    t_info = db_cur.fetchone()

    return render_template('execute_query.html')