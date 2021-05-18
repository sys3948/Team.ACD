## dbide directory views.py
# dbms 내/외부 접속, 쿼리 실행(전공자 & 비전공자) 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, flash, json, render_template, request, session, url_for, redirect, jsonify
from . import dbide
from .. import socketio
from flask_socketio import emit,disconnect

import mysql.connector as mysql
from ..database import Database
from ..decorate import login_check,connect_db
from datetime import datetime
import re
import sqlparse


@dbide.route('/')
@dbide.route('/main')
@login_check
def main():
    if session.get('confirmed') == 0:
        cur = Database()
        email = cur.excuteOne('select email from user where id=%s', (session.get('id'),))[0]
        cur.close()
    else:
        email = None
        cur = Database()
        out_dbms_info = cur.excuteAll('select db_id, dbms, hostname, port_num, alias, \
                                              dbms_connect_username, dbms_schema, \
                                              stampdatetime \
                                   from dbms_info \
                                   where user_id = %s \
                                   and inner_num = 0 \
                                   order by stampdatetime desc', (session.get('id'),))
        inner_dbms_info = cur.excuteAll('select db_id, dbms \
                                   from dbms_info \
                                   where user_id = %s \
                                   and inner_num = 1', (session.get('id'),))
        cur.close()

    return render_template('main.html', email = email, out_dbms_info = out_dbms_info, \
                           inner_dbms_info = inner_dbms_info)


@login_check
@dbide.route('/connect_dbms', methods=['GET', 'POST'])
@dbide.route('/connect_dbms/edit/<id>', methods=['GET', 'UPDATE'])
def connect_edit_dbms(id=None):
    if request.method == 'POST' or request.method == 'UPDATE':
        dbms = request.form.get('dbms')
        host = request.form.get('host')
        port = request.form.get('port')
        user_id = request.form.get('user_id')
        user_pw = request.form.get('user_pw')
        alias = request.form.get('alias')
        schema = request.form.get('schema')

        try:
            if dbms == 'mysql' or dbms == 'maria':
                cur = Database(host = host, user = user_id, password = user_pw, port = port, database = schema)
                cur.close()
            elif dbms == 'oracle':
                cur = Database(host = host, user = user_id, password = user_pw, port = port, database = schema, dbms = dbms)
                cur.close()
            elif dbms == 'mongo':
                pass

            dbms_info_cur = Database()
            if id and request.method == 'UPDATE':
                dbms_info_cur.excute("update dbms_info set \
                                  dbms=%s, hostname=%s, port_num=%s, alias=%s, dbms_connect_pw=%s, \
                                  dbms_connect_username=%s, dbms_schema=%s, stampdatetime=%s \
                                  where db_id=%s", \
                                  (dbms, host, port, alias, user_pw, \
                                   user_id, schema, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),\
                                   id))
            elif not id and request.method == 'POST':
                dbms_info_cur.excute("insert into dbms_info(user_id, dbms, hostname, port_num, \
                                        alias, dbms_connect_pw, dbms_connect_username, dbms_schema, \
                                        inner_num, stampdatetime) \
                                        value(%s, %s, %s, %s, %s, %s, %s, %s, 0, %s)", \
                                        (session.get('id'), dbms, host, port, alias, \
                                        user_pw, user_id, schema, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            else:
                flash('예상치 못 한 에러로 인해 메인페이지로 넘어갑니다.')
                return redirect(url_for('dbide.main'))
            dbms_info_cur.commit()
            dbms_info_cur.close()
            return jsonify({'confirm':True})
        except mysql.Error as e:
            print(e)
            # cur.close()
            return jsonify({"confirm":False, "msg":str(e)})

    dbms_info = None

    if id:
        cur = Database()
        dbms_info = cur.excuteOne("select db_id, hostname, port_num, dbms, alias, \
                   dbms_connect_username, dbms_connect_pw, \
                   dbms_schema \
                   from dbms_info \
                   where db_id = %s and user_id = %s", \
                   (id, session.get('id')))
        cur.close()

        if not dbms_info:
            flash('정확하지 않는 정보로 인해 메인 페이지로 돌아갑니다.')
            return redirect(url_for('dbide.main'))

    return render_template('connect_edit_dbms.html', dbms_info = dbms_info)


@login_check
@dbide.route('/delete_dbms/<id>')
def delete_dbms(id):
    cur = Database()
    confirm = cur.excuteOne("select db_id, user_id \
                  from dbms_info \
                  where db_id = %s and user_id = %s", (id, session.get('id')))

    if not confirm:
        flash('해당 계정에 존재하지 않는 DBMS 입니다.')
    else:
        cur.excute("delete from dbms_info \
                    where db_id = %s", (id,))

        cur.commit()
        flash('DBMS 삭제를 성공 했습니다.')
    return redirect(url_for('dbide.main'))



@login_check
@dbide.route('/execute_query/<id>')
@connect_db
def execute_query(id,dbms_info):
    '''
        쿼리 실행화면
    '''
    #사용자가 연결한 db object
    user_db = dbms_info.get('user_db')
    #info_dbms테이블에 select 한 결과
    db_info = dbms_info.get('db_info')
    

    databases,tables = user_db.show_databases_and_tables(db_info)    

    user_db.close()
    
    return render_template('execute_query.html',tables=tables,id=id,databases=databases,db_info=db_info)
    
@login_check
@dbide.route('/execute_query_result/<id>',methods=['POST'])
@connect_db
def execute_query_result(id,dbms_info):
    '''
        쿼리 비동기 처리후 결과 반환
    '''
    user_db = dbms_info.get('user_db')
    db_info = dbms_info.get('db_info')

    query = request.form.get('query')

    json = {}
    msg_list = []
    
    for sql in sqlparse.split(query):
        try:
            #오라클에서 세미콜론 있으면 에러발생
            sql = sql.replace(';','')
            
            sql_type = sqlparse.parse(sql)[0].tokens[0].value.upper()

            #select문 경우 실행
            if sql_type == 'SELECT':
                results = user_db.excuteAll(sql)
                columns = [col[0] for col in user_db.get_cursor().description ]
                
                #전체데이터베이스 explain
                json['explain'] = user_db.show_explain(sql)
                json['dbms']   = user_db.dbms
                json['results'] = render_template('include/query_result.html',results=results,columns=columns,sql_type=sql_type)
            else:    
                results = user_db.excute(sql)
                user_db.commit()

            msg_list.append(f'{sql}<br>쿼리실행 성공')    
        except Exception as e:
            print(e)
            msg_list.append({'error_msg':f'{sql}<br>쿼리실행 실패<br>{e}'})
            break
        
    databases,tables = user_db.show_databases_and_tables(db_info)   

    user_db.close()

    json['tables']   = render_template('include/table_nav.html',tables=tables,databases=databases,db_info=db_info)
    json['msg_list'] = msg_list
    return jsonify(json)


@socketio.on('import_csv', namespace = '/dbide')
def import_csv(data):
    print(data)
    for i in range(1,10000+1):
        emit('progress',{'progress':round((i/10000)*100,2)})
    disconnect()
        

@login_check
@dbide.route('/connect_schema/<id>/<schema>')
@connect_db
def connect_schema(id,schema,dbms_info):
    
    user_db = dbms_info.get('user_db')
    db_info = dbms_info.get('db_info')
    schema  = schema.strip()
    json = {}
    try:
        
        tables = user_db.excuteAll(f'show tables from {schema}')
        
        cur = Database()
        cur.excute('UPDATE dbms_info SET dbms_schema=%s WHERE db_id=%s',(schema,id,))
        cur.commit()
        cur.close()
        user_db.close()

        json['msg'] = f"데이터베이스 <b class='text-dark'>{schema}</b>에 sql질의 실행"
    except Exception as e:
        print(e)
        json['error_msg'] = f'{schema}를 사용할수 없습니다.<br>{str(e)}'

    
    return jsonify(json)    



@login_check
@dbide.route('/execute_query_no_major/<id>')
def execute_query_no_major(id):
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema, inner_num \
                             from dbms_info \
                             where db_id = %s and user_id=%s', (id, session.get('id')))

    if not db_info:
        flash('연결하려고 한 DBMS 정보는 사용자께서 소유하고 있지 않는 DBMS 입니다.')
        return redirect(url_for('dbide.main'))

    cur.close()

    user_db = Database(dbms = db_info[0], host = db_info[1], port = db_info[2], user = db_info[4], \
                       password = db_info[3], database = db_info[5])

    databases, tables = user_db.show_databases_and_tables(db_info)

    user_db.close()

    return render_template('/no_major/main.html', id=id, databases=databases, tables=tables, db_info = db_info)


@login_check
@dbide.route('/execute_query_no_major/create_db/<id>')
def execute_query_no_major_create_db(id):
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema, inner_num \
                             from dbms_info \
                             where db_id = %s and user_id=%s', (id, session.get('id')))

    if not db_info:
        flash('연결하려고 한 DBMS 정보는 사용자께서 소유하고 있지 않는 DBMS 입니다.')
        return redirect(url_for('dbide.main'))

    cur.close()
    return render_template('/no_major/create_db.html', id=id, db_info = db_info)


@login_check
@dbide.route('/execute_query_no_major/drop_db/<id>')
def execute_query_no_major_drop_db(id):
    title = '데이터베이스'
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema, inner_num \
                             from dbms_info \
                             where db_id = %s and user_id=%s', (id, session.get('id')))

    if not db_info:
        flash('연결하려고 한 DBMS 정보는 사용자께서 소유하고 있지 않는 DBMS 입니다.')
        return redirect(url_for('dbide.main'))

    cur.close()
    return render_template('/no_major/drop_db.html', id=id, title = title, db_info = db_info)


@login_check
@dbide.route('/execute_query_no_major/create_table/<id>', methods = ['GET', 'POST'])
def execute_query_no_major_create_table(id):
    title = '생성'
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema, inner_num \
                             from dbms_info \
                             where db_id = %s and user_id=%s', (id, session.get('id')))

    if not db_info:
        flash('연결하려고 한 DBMS 정보는 사용자께서 소유하고 있지 않는 DBMS 입니다.')
        return redirect(url_for('dbide.main'))

    cur.close()

    user_db = Database(dbms = db_info[0], host = db_info[1], port = db_info[2], user = db_info[4], \
                       password = db_info[3], database = db_info[5])


    if request.method == 'POST':
        try:
            user_db.excute(request.form.get('query'))
            user_db.commit()
            flash('Table 생성을 성공했습니다.')
            user_db.close()
            return jsonify({"confirm":True})
        except Exception as e:
            user_db.close()
            return jsonify({"confirm" : False, "msg" : str(e)})

    databases, tables = user_db.show_databases_and_tables(db_info)
    user_db.close()
    return render_template('/no_major/create_table.html', id=id, title = title, databases=databases, tables = tables, db_info=db_info)


@login_check
@dbide.route('/execute_query_no_major/alter_table/<id>', methods=['GET', 'POST'])
def execute_query_no_major_alter_table(id):
    title = '수정'
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema, inner_num \
                             from dbms_info \
                             where db_id = %s and user_id=%s', (id, session.get('id')))

    if not db_info:
        flash('연결하려고 한 DBMS 정보는 사용자께서 소유하고 있지 않는 DBMS 입니다.')
        return redirect(url_for('dbide.main'))

    cur.close()

    user_db = Database(dbms = db_info[0], host = db_info[1], port = db_info[2], user = db_info[4], \
                       password = db_info[3], database = db_info[5])

    if request.method == 'POST':
        if 'table_name' in request.form:
            if db_info[0] == 'mysql' or db_info[0] == 'maria':
                table_info = user_db.excuteAll('desc ' + request.form.get('table_name'))
            if db_info[0] == 'oracle':
                table_info = user_db.excuteAll("select cname, coltype, width, nulls, defaultval from col where tname = '" +request.form.get('table_name').upper()+ "'")
            user_db.close()
            table_info = [list(i) for i in table_info]
            return jsonify({'confirm' : True, 'table_info' : str(table_info), 'dbms':db_info[0]})
        if 'query' in request.form:
            table_name = request.form.get('query').split(" ")[2].split("(")[0]

            if db_info[0] == 'mysql' or db_info[0] == 'maria':
                user_db.excute('drop table ' + table_name)
            if db_info[0] == 'oracle':
                user_db.excute('drop table ' + table_name)
                user_db.excute('purge recyclebin')
            user_db.excute(request.form.get('query'))
            user_db.commit()
            user_db.close()
            flash('Table 수정 완료했습니다.')
            return jsonify({'confirm' : True})

    databases, tables = user_db.show_databases_and_tables(db_info)
    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = tables
    user_db.close()
    return render_template('/no_major/create_table.html', id=id, title = title, databases=databases, tables = tables, t_list = t_list, db_info=db_info)


@login_check
@dbide.route('/execute_query_no_major/drop_table/<id>', methods=['GET', 'POST'])
def execute_query_no_major_drop_table(id):
    title = '테이블'
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema, inner_num \
                             from dbms_info \
                             where db_id = %s and user_id=%s', (id, session.get('id')))

    if not db_info:
        flash('연결하려고 한 DBMS 정보는 사용자께서 소유하고 있지 않는 DBMS 입니다.')
        return redirect(url_for('dbide.main'))

    cur.close()

    user_db = Database(dbms = db_info[0], host = db_info[1], port = db_info[2], user = db_info[4], \
                       password = db_info[3], database = db_info[5])

    if request.method == 'POST':
        print(request.form.get('drop_info'))
        if db_info[0] == 'mysql' or db_info[0] == 'maria':
            user_db.excute('drop table ' + request.form.get('drop_info'))
        if db_info[0] == 'oracle':
            user_db.excute('drop table ' + request.form.get('drop_info'))
            user_db.excute('purge recyclebin')
        user_db.commit()
        flash('Table 삭제 완료했습니다.')
        return redirect(url_for('.execute_query_no_major_drop_table', id=id))


    databases, tables = user_db.show_databases_and_tables(db_info)
    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = tables
    user_db.close()
    return render_template('/no_major/drop_db.html', id=id, title=title, db_info = db_info, databases = databases, tables = tables, t_list = t_list)


@login_check
@dbide.route('/execute_query_no_major/select/<id>')
def execute_query_no_major_select(id):
    return render_template('/no_major/select.html', id=id)


@login_check
@dbide.route('/execute_query_no_major/insert/<id>')
def execute_query_no_major_insert(id):

    return render_template('/no_major/insert.html', id=id)


@login_check
@dbide.route('/execute_query_no_major/update/<id>')
def execute_query_no_major_update(id):

    return render_template('/no_major/update.html', id=id)


@login_check
@dbide.route('/execute_query_no_major/delete/<id>')
def execute_query_no_major_delete(id):

    return render_template('/no_major/delete.html', id=id)

@dbide.route('/execute_test/')
def excute_test():
    db = Database()
    print(db.excuteAll("explain format=tree select * from acd.user as u,acd.dbms_info as d where u.id=d.user_id order by u.id"))
    return 'hihi'