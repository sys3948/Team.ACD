# auth directory views.py
# user 등록, 로그인, 아이디 찾기, 비밀번호 찾기, 비밀번호 변경 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, render_template, request, session, url_for, redirect, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import cx_Oracle as oracle
import mariadb
import mysql.connector as mysql
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from . import auth
from ..email import send_email

@auth.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        user_conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='CAD')
        user_cur = user_conn.cursor()

        user_cur.execute('select id, password_hash, confirmed from user where user_id = %s', (request.form.get('user_id'),))
        user_data = user_cur.fetchone()

        if check_password_hash(user_data[1], request.form.get('user_pw')):
            session['id'] = user_data[0]
            session['confirmed'] = user_data[2]
            return redirect(url_for('dbide.main'))
    return render_template('sign_in.html')
    # function_name은 개발자가 지정하기.
    

@auth.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        user_conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='CAD')
        user_cur = user_conn.cursor()
        user_cur.execute('select user_id from user where user_id = %s', (request.form.get('user_id'),))

        if user_cur.fetchone():
            return jsonify({'confirm':False, 'target':'id', 'msg':'이미 존재하는 ID 입니다.'})

        user_cur.execute('select email from user where email = %s', (request.form.get('user_email'),))
        if user_cur.fetchone():
            return jsonify({'confirm':False, 'target':'email', 'msg':'이미 존재하는 Email 입니다.'})

        user_cur.execute('insert into user(user_id, password_hash, email, stampdate) \
                          value(%s, %s, %s, %s)', \
                          (request.form.get('user_id'), \
                           generate_password_hash(request.form.get('user_pw')), \
                           request.form.get('user_email'), \
                           datetime.now().strftime('%Y-%m-%d %H:%M:%S')\
                          )\
                        )

        user_conn.commit()
        user_cur.execute('select id from user where user_id = %s',(request.form.get('user_id'),))
        token_id = user_cur.fetchone()
        user_cur.close()
        user_conn.close()

        s = Serializer(current_app.config.get('SECRET_KEY'), 3600)
        token = s.dumps({'confirm':token_id[0]})

        send_email(to = request.form.get('user_email'), \
                   title = '저희 Team A C D의 DB IDE Web App의 회원 가입을 해준 것에 감사합니다.', \
                   templates = 'email/confirm', \
                   user = request.form.get('user_id'), \
                   token = token)
        
        return jsonify({'confirm':True, 'target':'', 'msg':''})

    return render_template('sign_up.html')


@auth.route('/confirm/<token>')
def confirm(token):
    s = Serializer(current_app.config.get('SECRET_KEY'))

    try:
        data = s.loads(token)
    except:
        return False

    user_conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='CAD')
    user_cur = user_conn.cursor()

    user_cur.execute('select id from user where id = %s',(data.get('confirm'),))

    if user_cur.fetchone():
        user_cur.execute('update user set confirmed = 1 where id = %s', (data.get('confirm'),))
        user_conn.commit()
        user_cur.close()
        user_conn.close()

        session['id'] = data.get('confirm')
        session['confirmed'] = '1'

    return redirect(url_for('dbide.main'))


@auth.route('/sign_out')
def sign_out():
    session.clear()
    return redirect(url_for('auth.sign_in'))
    