# auth directory views.py
# user 등록, 로그인, 아이디 찾기, 비밀번호 찾기, 비밀번호 변경 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, render_template, request, session, url_for, redirect, jsonify
from flask import flash,abort
from werkzeug.security import generate_password_hash, check_password_hash
import cx_Oracle as oracle
import mariadb
import mysql.connector as mysql
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from . import auth
from ..email import send_email
from ..database import MysqlDatabase
from ..decorate import login_check

@auth.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        user_conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='ACD')
        user_cur = user_conn.cursor()

        user_cur.execute('select id, user_id, password_hash, confirmed from user where user_id = %s', (request.form.get('user_id'),))
        user_data = user_cur.fetchone()
        user_cur.close()
        user_conn.close()

        if not user_data:
            flash('옳바르지 않는 계정 또는 비밀번호입니다.')
        else:
            print("test")
            if check_password_hash(user_data[2], request.form.get('user_pw')):
                print("test")
                session['id'] = user_data[0]
                session['confirmed'] = user_data[3]
                return redirect(url_for('dbide.main'))
    return render_template('sign_in.html')
    

@auth.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        user_conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='ACD')
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

        # user_cur.execute('create database %s' %(request.form.get('user_id')))
        # user_cur.execute('create user %s@"%" identified by %s', (request.form.get('user_id'), request.form.get('user_pw')))
        # user_cur.execute('grant all on %s.* to %s@%', (request.form.get('user_id'), request.form.get('user_id')))

        user_conn.commit()
        user_cur.execute('select id from user where user_id = %s',(request.form.get('user_id'),))
        token_id = user_cur.fetchone()
        user_cur.close()
        user_conn.close()

        # oracle_conn = oracle.connect(current_app.config.get('ORACLE_USER'), \
        #                              current_app.config.get('ORACLE_PW'), \
        #                              '192.168.111.133:1521')
        # oracle_cur = oracle_conn.cursor()
        # oracle_cur.execute('create user %s identified by %s', (request.form.get('user_id'), request.form.get('user_pw')))
        # oracle_cur.execute('grant create session, create table, create view, create sequence to %s', (request.form.get('user_id'),))
        # oracle_cur.execute('create tablespace %s datafile "/home/sys3948/oracle/%s.dbf size 10m"', (request.form.get('user_id'), request.form.get('user_id')))
        # oracle_cur.execute('alter user %s quota 10m on %s', (request.form.get('user_id'), request.form.get('user_id')))

        # oracle_conn.commit()
        # oracle_cur.close()
        # oracle_conn.close()

        s = Serializer(current_app.config.get('SECRET_KEY'), 3600)
        token = s.dumps({'confirm':token_id[0]})

        send_email(to = request.form.get('user_email'), \
                   title = '저희 Team A C D의 DB IDE Web App의 회원 가입을 해준 것에 감사합니다.', \
                   templates = 'email/confirm', \
                   user = request.form.get('user_id'), \
                   token = token)
        
        flash('회원 가입 성공했습니다. 회원 인증 절차에 관한 것은 등록하신 메일 : '+request.form.get('user_email')+ ' 로 전송했습니다. 메일에서 확인해주세요.')
        return jsonify({'confirm':True, 'target':'', 'msg':''})

    return render_template('sign_up.html')


@auth.route('/confirm/<token>')
def confirm(token):
    s = Serializer(current_app.config.get('SECRET_KEY'))

    try:
        data = s.loads(token)
    except:
        flash('인증 토근 오류가 발생했습니다.')
        return redirect(url_for('.sign_in'))

    user_conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='ACD')
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


@auth.route('/re_send_email')
def re_send_email():
    cur = MysqlDatabase()
    email = cur.excuteOne('select email from user where id=%s', (session.get('id'),))

    s = Serializer(current_app.config.get('SECRET_KEY'), 3600)
    token = s.dumps({'confirm':session.get('id')})

    send_email(to = email[0], \
               title = '저희 Team A C D의 DB IDE Web App의 회원 가입을 해준 것에 감사합니다.', \
               templates = 'email/confirm', \
               user = request.form.get('user_id'), \
               token = token)

    return redirect(url_for('dbide.main'))



@auth.route('/sign_out')
def sign_out():
    session.clear()
    return redirect(url_for('auth.sign_in'))
    

@auth.route('/find_id',methods=['GET', 'POST'])
def find_id():
    if request.method == "POST":
        mysql_db = MysqlDatabase()

        row = mysql_db.excuteOne(
                '''
                 SELECT user_id 
                 FROM user 
                 WHERE email=%s
                ''',
                (request.form.get('email'),)
            )

        mysql_db.close()

        if row:
            send_email(to = request.form.get('email'), \
                    title = 'Team A C D 아이디 찾기', \
                    templates = 'email/find_id_msg', \
                    user_id = row[0])
            flash("이메일  '" + request.form.get('email') + "'에 발송되었습니다.")        
            return redirect(url_for('auth.sign_in'))
                    
        else:
            flash("'" + request.form.get('email') + "'은 존재하지 않는 이메일입니다.")
                

    return render_template('find_id.html')

@auth.route('/find_pw',methods=['GET', 'POST'])
def find_pw():
    if request.method == "POST":
        mysql_db = MysqlDatabase()
        row = mysql_db.excuteOne(
            '''
                SELECT id 
                FROM user
                WHERE user_id=%s AND email=%s
            ''',
            (request.form.get('id'), request.form.get('email'),)
        )
        mysql_db.close()
        if row:
            s = Serializer(current_app.config.get('SECRET_KEY'), 3600)
            token = s.dumps({'id':row[0]})
            send_email(to = request.form.get('email'), \
                   title = 'Team ACD 비밀번호 찾기', \
                   templates = 'email/find_pw_msg', \
                   token = token)
            flash("이메일  '" + request.form.get('email') + "'에 발송되었습니다.")
            return redirect(url_for('auth.sign_in'))
        else:
            flash("'" + request.form.get('id') + "' 또는 '" + request.form.get('email') + "'가 등록되어 있지 않습니다.")                   
        
    return render_template('find_pw.html')


@auth.route('/reset_pw/<token>',methods=['GET', 'POST'])
def reset_pw(token):
    
    if request.method == "POST":
        s = Serializer(current_app.config.get('SECRET_KEY'))
        try:
            data = s.loads(token)
        except Exception as e:
            return "<script> alert('토큰 오류'); history.back();</script>"

        mysql_db = MysqlDatabase()

        mysql_db.excute(
            '''
                UPDATE user
                SET password_hash=%s
                WHERE id=%s
            ''',
            (
             generate_password_hash(request.form.get('pw')),\
             data.get('id')
             )
        )
        mysql_db.commit()
        mysql_db.close()
        return redirect(url_for('auth.sign_out'))
        
    return render_template('rset_pw.html')

@auth.route('/confirm_pw',methods=['POST'])
@login_check
def confirm_pw():
    mysql_db = MysqlDatabase()
    
    row = mysql_db.excuteOne(
           '''
           SELECT id,password_hash
           FROM user
           WHERE id=%s
           ''',
           (session['id'],)
         )
   
    mysql_db.close()     
    
    if check_password_hash(row[1],request.form.get('pw')):
        s = Serializer(current_app.config.get('SECRET_KEY'), 3600)
        token = s.dumps({'id':row[0]})
        return redirect(url_for('auth.reset_pw',token=token))
    else:
        return "<script>alert('비밀번호가 일치하지 않습니다.'); history.back();</script>"

    






