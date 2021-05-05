## dbide directory views.py
# dbms 내/외부 접속, 쿼리 실행(전공자 & 비전공자) 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, render_template, request, session, url_for, redirect, jsonify
from . import dbide
import mysql.connector as mysql
from ..database import Database
from ..decorate import login_check
import re

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
@dbide.route('/execute_query/<id>',methods=['GET','POST'])
def execute_query(id):
    cur = Database()
    db_info = cur.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema \
                             from dbms_info \
                             where db_id = %s', (id,))

    
    
    user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3],database = db_info[5])
    tables = user_db.excuteAll('show tables')
    if request.method == "POST":
        query = request.form.get('query')
        last_query = query.split(';')[-2]
        
    

        
        results = None
        nav  = render_template('include/table_nav.html',tables=tables)
        #select문일 경우
        if re.compile(r'(SELECT|select)+.+(FROM|from)+.+').search(last_query):

            results=user_db.excuteAll(last_query,())
            
            last_query = last_query.lower()
            start_index = last_query.find('select') + len('select')
            end_index = last_query.find('from')
            table_name = last_query[end_index+len('from'):last_query.find('where')].strip() if last_query.find('where') != -1 else last_query[end_index+len('from'):].strip()
            colums = last_query[start_index:end_index].strip()
            
            if colums == '*':
                colums = [col[0] for col in user_db.get_cursor().description]
                
            else:
                colums = [el.strip() for el in colums.split(',')]    
            print(results)
            

            html = render_template('include/query_result.html',results=results,colums=colums,range=(0,len(colums)))
            
            return jsonify({'html':html,'nav':nav})
        else:
            
            try:
                user_db.excute(last_query, ())
                user_db.commit()
                return jsonify({'msg':'쿼리실행 성공했습니다.','nav':nav})
            except Exception as e:
                return jsonify({'msg':'에러가 발생했습니다.','nav':nav})

    user_db.close()
    return render_template('execute_query.html',tables=tables,id=id)
