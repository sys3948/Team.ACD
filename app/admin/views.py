# admin directory views.py
# 관리자 로그인, 등록, 사용자 목록, 사용자 권한 조정, 사용자 삭제 페이지의 url을 라우팅 하는 뷰함수 python module

#from flask import ...
from . import admin
from flask import current_app, render_template, request, session, url_for, redirect,flash
from ..decorate import login_check,manager_check
from ..database import MysqlDatabase
from ..email import send_email


@admin.route('/')
@login_check
@manager_check
def admin_main():
    
    mysql_db = MysqlDatabase()
    delete_users =  mysql_db.excuteAll('SELECT * FROM delete_user')
    users = mysql_db.excuteAll('SELECT * FROM user')
    mysql_db.close()      

    return render_template('admin/admin_main.html',users=users,delete_users=delete_users)

#사용자 삭제
@admin.route('/delete_user/<id>',methods=['GET','POST'])
@login_check
@manager_check
def delete_user(id):
    mysql_db = MysqlDatabase()
    user = mysql_db.excuteOne('SELECT user_id,email,grant_num FROM user WHERE id=%s',(id,))
    if request.method == "POST":
        mysql_db.excute('DELETE FROM user WHERE id=%s', (id,))
        mysql_db.commit()
        mysql_db.close()
        send_email(to = user[1], \
                   title = 'Team A C D 계정 삭제 알림입니다.', \
                   templates = 'email/delete_user', \
                   user = user[0], \
                   reason=request.form.get('reason'))
        flash(f'이메일이 {user[1]}로 발송되었습니다.')           
        return redirect(url_for('admin.admin_main'))

    
    mysql_db.close()
    return render_template('admin/delete_user.html',user=user)

#사용자 권한 변경
@admin.route('/edit_user/<id>',methods=['GET','POST'])
@login_check
@manager_check
def edit_user(id):
    mysql_db = MysqlDatabase()
    user = mysql_db.excuteOne('SELECT user_id,email,grant_num FROM user WHERE id=%s',(id,))
    if request.method == "POST":
        grant_dict = {'0':'일반','1':'내부 DB사용불가','2':'로그인 불가'}

        mysql_db.excute('UPDATE user SET grant_num=%s', (request.form.get('grant'),))
        mysql_db.commit()
        mysql_db.close()

        send_email(to = user[1], \
                   title = 'Team A C D 권한변경 알림입니다.', \
                   templates = 'email/change_grant', \
                   user = user[0], \
                   grant = grant_dict.get(request.form.get('grant')),
                   reason=request.form.get('reason'))
        flash(f'이메일이 {user[1]}로 발송되었습니다.')           
        return redirect(url_for('admin.admin_main'))

    mysql_db.close()
    return render_template('admin/edit_user.html',user=user)