## dbide directory views.py
# dbms 내/외부 접속, 쿼리 실행(전공자 & 비전공자) 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, flash, json, render_template, request, session, url_for, redirect, jsonify,Response,send_file,after_this_request
from . import dbide
from .log import Log
import mysql.connector as mysql
from ..database import Database
from ..decorate import login_check,connect_db

from datetime import datetime
import re
import sqlparse
from app.celery import async_import_csv,async_export_csv
import os 
import io
from werkzeug.utils import secure_filename
from pymongo import MongoClient as Mongo
import pymongo





from app import database


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
        전공자 oracle,mysql,mariadb 쿼리 실행화면
    '''
    #info_dbms테이블에 select 한 결과
    db_info = dbms_info.get('db_info')
    
    user_db = dbms_info.get('user_db')
    databases,tables = user_db.show_databases_and_tables(db_info)    
    user_db.close()

    log = Log()
    logs = log.read_logs(id)
    log.close_db_connect()
    
    return render_template('execute_query.html',tables=tables,id=id,databases=databases,db_info=db_info,logs=logs)
    



@login_check
@dbide.route('/execute_query_result/<id>',methods=['POST'])
@connect_db
def execute_query_result(id,dbms_info):
    '''
        oracle,mysql,mariadb 쿼리 비동기 처리후 결과 반환
    '''
    #dbms_info 테이블 정보
    user_db = dbms_info.get('user_db')
    db_info = dbms_info.get('db_info')

    query = request.form.get('query')

    #log 객체 생성
    log = Log()

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
                
                #rdbms explain
                json['explain'] = user_db.show_explain(sql)
                json['dbms']   = user_db.dbms
                json['results'] = render_template('include/query_result.html',results=results,columns=columns,sql_type=sql_type)
            else:    
                
                results=user_db.excute(sql)
                user_db.commit()
            
            msg_list.append(f'{sql}<br>쿼리실행 성공')    

            #sql 실행성공 로깅
            log.write_log(id,sql,"성공")

        except Exception as e:
            print(e)
            msg_list.append({'error_msg':f'{sql}<br>쿼리실행 실패<br>{e}'})
            #sql 실행실패 로깅
            log.write_log(id,sql,"실패")        

            break
        
        
    databases,tables = user_db.show_databases_and_tables(db_info)   

    json['tables']   = render_template('include/table_nav.html',tables=tables,databases=databases,db_info=db_info)
    json['logs']     = render_template('include/logging.html',logs=log.read_logs(id))
    json['msg_list'] = msg_list

    user_db.close()
    log.close_db_connect()
    return jsonify(json)

@login_check
@dbide.route('/execute_mongo_query_result/<id>',methods=['POST'])
@connect_db
def execute_mongo_query_result(id,dbms_info):
    '''
        mongodb 쿼리실행
    '''
    #dbms_info 테이블 정보
    user_db = dbms_info.get('user_db')
    db_info = dbms_info.get('db_info')

    query_string = request.form.get('query')    

    context = {} # response 데이터
    converted_list = []
    msg_list = [] #성공메시지 또는 error 메시지

    #로그 객체 생성
    log = Log()

    for query in sqlparse.split(query_string):
        query = query.replace(";","")
        try:
            #쿼리 결과
            result,converted_list,explain = user_db.excute_query_mongo_to_pymongo(query)

            if explain: #실행계획 있은 실행, mongodb find()에만 실행계획 있다
                context['explain'] = explain
            context['result'] = result

            msg_list.append(f'{query}<br>쿼리실행 성공') 

            #몽고 쿼리 실행성공 로깅
            log.write_log(id,query,"성공")
               
        except Exception as e:
            error = str(e)
            for el in converted_list:
                error.replace(el[0],el[1])
            print(error)
            msg_list.append({'error_msg':f'{query}<br>쿼리실행 실패<br>{e}'})

            #몽고 쿼리 실행실패 로깅
            log.write_log(id,query,"실패")
            break
    
    databases,tables = user_db.show_databases_and_tables(db_info)
    
    
    context['tables']   = render_template('include/table_nav.html',tables=tables,databases=databases,db_info=db_info)
    context['dbms']     = "mongo"
    context['msg_list'] = msg_list
    context['logs']     = render_template('include/logging.html',logs=log.read_logs(id))

    user_db.close()
    log.close_db_connect()

    return jsonify(context)   

     

@login_check
@dbide.route('/ajax_request_tables/<id>/<database>')
@connect_db
def ajax_request_tables(id,database,dbms_info):
    '''
        외부접속시 import csv modal에서 데이터베이스
        선택시 해당 데이터베이스 테이블목록 반환 
    '''
    user_db = dbms_info.get('user_db')
    context = {}
    try:
        tables = user_db.excuteAll(f"show tables from {database}")
        print(tables)
        context['tables'] = tables
    except Exception as e:
        print(e)
        context['error'] = str(e)
        
    return jsonify(context)



@login_check
@dbide.route('/connect_schema/<id>/<schema>')
@connect_db
def connect_schema(id,schema,dbms_info):
    
    user_db = dbms_info.get('user_db')
    db_info = dbms_info.get('db_info')
    schema  = schema.strip()
    json = {}
    try:
        
        # tables = user_db.excuteAll(f'show tables from {schema}')
        
        cur = Database()
        cur.excute('UPDATE dbms_info SET dbms_schema=%s WHERE db_id=%s',(schema,id,))
        # cur.excute('select * from table_name where id=%s', (id,))
        cur.commit()
        cur.close()
        user_db.close()

        json['msg'] = f"데이터베이스 <b class='text-dark'>{schema}</b>에 sql질의 실행"
    except Exception as e:
        print(e)
        json['error_msg'] = f'{schema}를 사용할수 없습니다.<br>{str(e)}'

    
    return jsonify(json)    



#client로부터 csv 파일 받아서 비동기처리 요청
@login_check
@dbide.route('/import_csv/<id>',methods=['POST'])
@connect_db
def import_csv(id,dbms_info):
    
    db_info = dbms_info.get('db_info')

    csv_file  = request.files.get('csv_file')
    #파일명,확장자
    orgin_filename, ext = csv_file.filename.rsplit('.',1)
    filename = orgin_filename

    #같은 파일명 있으면 파일명뒤에 고유번호 부여
    unique = 1
    while os.path.exists(f"{current_app.config['UPLOAD_FOLDER_PATH']}/{filename}.{ext}"):
        filename = f"{orgin_filename}{unique}"
        unique += 1


    csv_file.save(os.path.join(current_app.config['UPLOAD_FOLDER_PATH'], secure_filename(filename+'.'+ext)))


    #비동기 작업요청
    #database_opt는 외부접속시만 있음
    task = async_import_csv.apply_async([
                    db_info,
                    filename+'.'+ext,
                    request.form.get('table_name'),
                    request.form.get('database_opt')
                ])

    return jsonify({'task_id':task.id})

#테이블 데이터를 csv 파일로 저장
@login_check
@dbide.route('/export_csv/<id>',methods=['POST'])
@connect_db
def export_csv(id,dbms_info):
    db_info = dbms_info.get('db_info')
    print("save_file_name: ",request.form.get('save_file_name'))
    print("databases: ",request.form.get('database_opt'))
    task=async_export_csv.apply_async([
                    db_info,
                    request.form.get('save_file_name'),
                    request.form.get('table_opt'),
                    request.form.get('database_opt')
                ])    

    return jsonify({'task_id':task.id})



#import,export  csv 작업진행율을 클라이언트에 전송
@dbide.route('/import_csv_progress/<import_task_id>')
@dbide.route('/export_csv_progress/<export_task_id>')
def csv_progress(import_task_id=None,export_task_id=None):

    def generate():
        if import_task_id:
            task = async_import_csv.AsyncResult(import_task_id)
        else:
            task = async_export_csv.AsyncResult(export_task_id)
        
        
        while task.state != 'SUCCESS' and task.state != 'FAILURE':
            if task.state == 'PENDING':
                yield f"data:{task.state}&&{0}\n\n"
                
            else:
                if export_task_id:
                    yield f"data:{task.state}&&{round(task.info.get('current')/task.info.get('total')*100,2)}&&{task.info.get('encryption_file_name')}&&{task.info.get('csv_file_name')}\n\n"
                else:    
                    yield f"data:{task.state}&&{round(task.info.get('current')/task.info.get('total')*100,2)}\n\n"
        
        if task.state == 'SUCCESS':
            
            if task.get().get('error'):
                yield f"data:{task.state}&&{round(task.info.get('current')/task.info.get('total')*100,2)}&&{task.get().get('error')}\n\n"
            else:
                yield f"data:{task.state}&&{round(task.info.get('current')/task.info.get('total')*100,2)}\n\n"
        
    return Response(generate(), mimetype= 'text/event-stream')



@dbide.route('/download_csv_file',methods=['POST'])
def download_csv_file():
    
    #사용자가 지정한 파일명
    csv_file_name = request.form.get('csv_file_name')
    if csv_file_name.find(".csv") == -1:
        csv_file_name = request.form.get('csv_file_name') + ".csv" 

    encryption_file_name = request.form.get('encryption_file_name')
    file_path = os.path.join(current_app.config['DOWNLOAD_FOLDER_PATH'],encryption_file_name)

    if os.path.exists(file_path):
        
        return_data = io.BytesIO()

        with open(file_path,'rb') as f:
            return_data.write(f.read())

        return_data.seek(0)

        os.remove(file_path)    

        return send_file(
            return_data,
            mimetype="text/csv",
            attachment_filename=csv_file_name,
            as_attachment=True
        )
    else:
        return "파일이 존재하지 않습니다."


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

    return render_template('/no_major/main.html', id=id, databases=databases, tables=tables, db_info = db_info, dbms_schema = db_info[5])


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
    return render_template('/no_major/create_db.html', id=id, db_info = db_info, dbms_schema = db_info[5])


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
    return render_template('/no_major/drop_db.html', id=id, title = title, db_info = db_info, dbms_schema = db_info[5])


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
    return render_template('/no_major/create_table.html', id=id, title = title, databases=databases, tables = tables, db_info=db_info, dbms_schema = db_info[5])


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
        try:
            if 'table_name' in request.form:
                if db_info[0] == 'mysql' or db_info[0] == 'maria':
                    table_info = user_db.excuteAll('desc ' + request.form.get('table_name'))
                if db_info[0] == 'oracle':
                    table_info = user_db.excuteAll(
                        "select column_info.cname, column_info.coltype, column_info.width, column_info.nulls, \
                                column_info.defaultval, column_constraints_info.constraint_type\
                        from ( \
                            select tname, cname, coltype, width, nulls, defaultval \
                            from col \
                            where tname = '" + request.form.get('table_name').upper() +"'\
                        ) column_info\
                        inner join ( \
                            select a.table_name, a.constraint_type, b.column_name \
                            from all_constraints a join all_cons_columns b \
                            on a.constraint_name = b.constraint_name \
                            where a.table_name = '" +request.form.get('table_name').upper()+ "'\
                        ) column_constraints_info \
                        on column_info.cname = column_constraints_info.column_name"
                    )
                user_db.close()
                table_info = [list(i) for i in table_info]
                return jsonify({'confirm' : True, 'table_info' : str(table_info), 'dbms':db_info[0]})
            if 'query' in request.form:
                table_name = request.form.get('query').split(" ")[2].split("(")[0]

                if db_info[0] == 'mysql' or db_info[0] == 'maria':
                    user_db.excute(f'drop table { table_name}')
                if db_info[0] == 'oracle':
                    user_db.excute(f'drop table { table_name}')
                    user_db.excute('purge recyclebin')
                user_db.excute(request.form.get('query'))
                user_db.commit()
                user_db.close()
                flash('Table 수정 완료했습니다.')
                return jsonify({'confirm' : True})
        except Exception as e:
            user_db.close()
            print(e)
            return jsonify({'confirm' : False, 'msg' : str(e)})

    databases, tables = user_db.show_databases_and_tables(db_info)
    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = user_db.excuteAll(f'show tables from {db_info[5]}')

    user_db.close()
    return render_template('/no_major/create_table.html', id=id, title = title, databases=databases, tables = tables, t_list = t_list, db_info=db_info, dbms_schema = db_info[5])


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
        user_db.close()
        flash('Table 삭제 완료했습니다.')
        return redirect(url_for('.execute_query_no_major_drop_table', id=id))


    databases, tables = user_db.show_databases_and_tables(db_info)
    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = user_db.excuteAll(f'show tables from {db_info[5]}')
    user_db.close()
    return render_template('/no_major/drop_db.html', id=id, title=title, db_info = db_info, databases = databases, tables = tables, t_list = t_list, dbms_schema = db_info[5])


@login_check
@dbide.route('/execute_query_no_major/select/<id>', methods=['GET', 'POST'])
def execute_query_no_major_select(id):
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
        try :
            if request.form.get('setting') == 'columns':
                table_colums_info = []
                for t in request.form.getlist('tables_info[]'):
                    print(t)
                    if db_info[0] == 'mysql' or db_info[0] == 'maria':
                        column_info = user_db.excuteAll('desc ' + t)
                        table_colums_info += [t + "." + c[0] for c in column_info]
                    if db_info[0] == 'oracle':
                        pass

                # table_colums_info = [ti.__next__() for ti in table_colums_info]
                print(table_colums_info)

                return jsonify({'confirm' : True, 'column_info':table_colums_info})
        except Exception as e:
            print(e)
            return jsonify({'confirm' : False})

    databases, tables = user_db.show_databases_and_tables(db_info)

    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = user_db.excuteAll(f'show tables from {db_info[5]}')

    user_db.close()

    t_list = [i[0] for i in t_list]

    return render_template('/no_major/select.html', id=id, db_info = db_info, databases = databases, tables = tables, dbms_schema = db_info[5], t_list = t_list)


@login_check
@dbide.route('/execute_query_no_major/insert/<id>', methods=['GET', 'POST'])
def execute_query_no_major_insert(id):
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
            if request.form.get('setting') == 'description':
                if db_info[0] == 'mysql' or db_info[0] == 'maria':
                    column_info = user_db.excuteAll('desc ' + request.form.get('table_name'))
                if db_info[0] == 'oracle':
                    column_info = user_db.excuteAll("select cname, coltype from col where tname = '" + request.form.get('table_name').upper() + "'")
                
                column_info = [[i[0], i[1]] for i in column_info]

                user_db.close()

                return jsonify({'confirm':True, 'column_info':str(column_info)})

            if request.form.get('setting') == 'insert':
                table_name = request.form.get('query').split(" ")[2].split("(")[0]
                user_db.excute(request.form.get('query'))
                user_db.commit()
                user_db.close()
                flash(table_name + ' 테이블에 데이터 삽입을 성공했습니다.')
                return jsonify({'confirm':True})

        except Exception as e:
            print(e)
            return jsonify({'confirm':False, 'msg':str(e)})

    databases, tables = user_db.show_databases_and_tables(db_info)

    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = user_db.excuteAll(f'show tables from {db_info[5]}')

    user_db.close()

    return render_template('/no_major/insert.html', id=id, db_info = db_info, databases = databases, tables = tables, dbms_schema = db_info[5], t_list = t_list)


@login_check
@dbide.route('/execute_query_no_major/update/<id>', methods=['GET', 'POST'])
def execute_query_no_major_update(id):
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
            if request.form.get('setting') == 'description':
                if db_info[0] == 'mysql' or db_info[0] == 'maria':
                    column_info = user_db.excuteAll('desc ' + request.form.get('table_name'))
                if db_info[0] == 'oracle':
                    column_info = user_db.excuteAll("select cname, coltype from col where tname = '" + request.form.get('table_name').upper() + "'")
                
                column_info = [[i[0], i[1]] for i in column_info]

                user_db.close()

                return jsonify({'confirm':True, 'column_info':str(column_info)})

            if request.form.get('setting') == 'update':
                user_db.excute(request.form.get('query'))
                user_db.commit()
                user_db.close()

                flash('테이블 ' + request.form.get('query').split(" ")[1] + '의 수정작업을 성공했습니다.')

                return jsonify({'confirm' : True})

        except Exception as e:
            print(e)
            return jsonify({'confirm':False, 'msg':str(e)})

    databases, tables = user_db.show_databases_and_tables(db_info)

    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = user_db.excuteAll(f'show tables from {db_info[5]}')

    user_db.close()
    return render_template('/no_major/update.html', id=id, db_info = db_info, databases = databases, tables = tables, dbms_schema = db_info[5], t_list = t_list)


@login_check
@dbide.route('/execute_query_no_major/delete/<id>', methods=['GET', 'POST'])
def execute_query_no_major_delete(id):

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
            if request.form.get('setting') == 'description':
                if db_info[0] == 'mysql' or db_info[0] == 'maria':
                    column_info = user_db.excuteAll('desc ' + request.form.get('table_name'))
                if db_info[0] == 'oracle':
                    column_info = user_db.excuteAll("select cname, coltype from col where tname = '" + request.form.get('table_name').upper() + "'")
                
                column_info = [[i[0], i[1]] for i in column_info]

                user_db.close()

                return jsonify({'confirm':True, 'column_info':str(column_info)})

            if request.form.get('setting') == 'delete':
                user_db.excute(request.form.get('query'))
                user_db.commit()
                user_db.close()

                flash('테이블 ' + request.form.get('query').split(" ")[2] + '의 삭제작업을 성공했습니다.')

                return jsonify({'confirm' : True})

        except Exception as e:
            print(e)
            return jsonify({'confirm':False, 'msg':str(e)})

    databases, tables = user_db.show_databases_and_tables(db_info)

    if db_info[0] == 'oracle':
        t_list = user_db.excuteAll('select tname from tab')
    if db_info[0] == 'mysql' or db_info[0] == 'maria':
        t_list = user_db.excuteAll(f'show tables from {db_info[5]}')

    user_db.close()

    return render_template('/no_major/delete.html', id=id, db_info = db_info, databases = databases, tables = tables, dbms_schema = db_info[5], t_list = t_list)

@dbide.route('/execute_test/')
def excute_test():
    db = Database()
    print(db.excuteAll("explain format=tree select * from acd.user as u,acd.dbms_info as d where u.id=d.user_id order by u.id"))
    return 'hihi'