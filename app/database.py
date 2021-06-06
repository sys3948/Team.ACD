import re
from typing import KeysView
from flask import current_app
from flask.helpers import get_template_attribute
from flask.json import jsonify
import mysql.connector as mysql
import cx_Oracle as oracle
from pymongo import MongoClient
import pymongo
import json
from bson import ObjectId
import urllib.parse



class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        else:
            return str(o)    
        

class Database():
    def __init__(self,dbms='mysql',**kargs):

        self.dbms = dbms
        
        #mysql, mariadb 용 설정
        self.defaults = {
            'host'     : current_app.config.get('DB_HOST'), 
            'user'     : current_app.config.get('MYSQL_USER'), 
            'password' : current_app.config.get('MYSQL_PW'), 
            'port'     : 3306,
            'database' : 'ACD'
        }
        #오라클용 설정
        self.oracle_defaults = {
            'user' : current_app.config.get('ORACLE_USER'),
            'password' : current_app.config.get('ORACLE_PW'),
            'host' : current_app.config.get('DB_HOST'),
            'port' : current_app.config.get('ORACLE_PORT'),
            'database' : 'system'
        }

        #몽고용 설정
        self.mongo_defauls = {
            'user' : None,
            'password' : None,
            'host' : None,
            'port' : 27017,
            'database': None
        }

        #몽고 디비 
        self.mongo_to_pymongo = {
            'get_collection_names' : 'collection_names',

        }

        if not self.dbms in ('mysql','maria','oracle','mongo'):
            raise Exception('dbms가 존재하지 않습니다.')

        if self.dbms != 'mongo': #rdbms 연결
            self.connect_rdbms(**kargs)
        else: #mongo 연결
            
            self.connect_mongo(**kargs)
            

        
    def connect_rdbms(self,**kargs):
        
        #mysql, mariadb 연결
        if self.dbms == 'mysql' or self.dbms =='maria':
            # self.defaults.pop('password') if dbms == 'mysql' else self.defaults.pop('passwd')
            #kargs 값이 있으면 defaults values 덮어쓰게 된다
            self.defaults.update(kargs)
            self.conn = mysql.connect(**self.defaults)
        elif self.dbms == 'oracle':
            #kargs 값이 있으면 oracle_defaults values 덮어쓰게 된다
            self.oracle_defaults.update(kargs)
            self.conn = oracle.connect(
                self.oracle_defaults.get('user'),
                self.oracle_defaults.get('password'),
                self.oracle_defaults.get('host') + ":" + str(self.oracle_defaults.get('port')),
                encoding='UTF-8'
            )    

        self.cur = self.conn.cursor()   

    def connect_mongo(self,**kargs):
        self.mongo_defauls.update(kargs)
        uri = "mongodb://%s:%s@%s:%s/%s" % (
                urllib.parse.quote_plus(self.mongo_defauls.get('user')),
                urllib.parse.quote_plus(self.mongo_defauls.get('password')),
                self.mongo_defauls.get('host'),
                self.mongo_defauls.get('port'),
                self.mongo_defauls.get('database'))

        self.mongo_client = MongoClient(uri)

    def reconnect(self,id,**kargs):
        '''
        데이터베이스 재연결 및 acd.dbms_info 테이블 dbms_schema컬럼 업데이트
        Args
            id : dbms_info테이블 db_id 컴럼값
            kargs : 데이터베이스 연결정보
        Returns
            dbms_info테이블 조회결과 반환    
        '''

        self.connect_rdbms(**kargs)
                
        mysql_conn = Database()
        #update 선택한 데이터베이스
        mysql_conn.excute("UPDATE dbms_info SET dbms_schema=%s WHERE db_id=%s",(kargs.get('database'),id))
        mysql_conn.commit()
                
        db_info = mysql_conn.excuteOne('select dbms, hostname, port_num, dbms_connect_pw, \
                             dbms_connect_username, dbms_schema,inner_num \
                             from dbms_info \
                             where db_id = %s', (id,))
        mysql_conn.close()

        return db_info                     


    
    def excute(self, sql, args=()):
        self.cur.execute(sql,args)

    
    def excute_query_mongo_to_pymongo(self,query):
        '''
            몽고디비 쿼리를 pymongo쿼리로 변환
            Arg:
                query : 몽고디비 쿼리
            Returns:
                result : 쿼리실행결과
                converted_list : 몽고디비 함수를 pymongo함수로 변환한 기록
                explain : find()일때만 실행계획 반환 아니면 None 반환
        '''
        
        converted_list = []
        query += "."
        tokens = re.compile('[^\d]\.').finditer(query)
        result = None
        start = 0
        for i,matched_obj in enumerate(tokens):
            end = matched_obj.start()+1 
            token = query[start:end]
            start = matched_obj.end()

            #print("is_match: ",re.compile("\w+\((.|\n)*\)").match(token))
            if i == 0:
                if token != 'db':
                    raise Exception(f'{token} is not defined')
                result = self.get_mongo_client()
            
            #함수면 실행
            elif re.compile("\w+\((.|\n)*\)").match(token):
                print("hihihihihi")
                #함수명, 함수argument로 split
                func_name,args = token.split('(')
                

                #함수명 리스트로 변환 
                new_func_name = list(func_name)
                
                args = args.replace(')','').strip()
                #pymongo function params
                params = []
                print("args: ",args)

                
            
                args_reg = '(\{(.|\n)*\}|\[(.|\n)*\]|[a-zA-Z0-9]*)' #함수 argument 자르기 위한 정규식
                for arg in re.compile(args_reg).finditer(args):
                    print("arg: ",arg.group())
                    if re.compile('[^a-zA-Z0-9]').match(arg.group()): #json 이면
                        json_arr = json.loads("["+arg.group().replace("'","\"")+"]")
                        for doc in json_arr:
                            params.append(doc)
                    elif arg.group() != "": #json 아닌 인자면 
                        number_re = re.compile('\d+').match(arg.group())
                        param =  int(arg.group()[number_re.start():number_re.end()]) if number_re  else arg.group() #인자가 숫자면 형변환
                        params.append(param)


                # 함수명 스타일 변경
                #ex) findOne -> find_one
                for m in re.compile("[A-Z]").finditer(func_name):
                    new_func_name[m.start()] = '_'+m.group().lower()

                new_func_name = "".join(new_func_name)
                print("new_func: ", new_func_name)
                new_func_name = self.mongo_to_pymongo.get(new_func_name) if self.mongo_to_pymongo.get(new_func_name) else new_func_name
                converted_list.append([new_func_name,func_name])
                
                result = getattr(result,new_func_name)(*params)
            elif i == 1: #collection_name이면 실행
                result = getattr(result,'get_collection')(token)


        explain = None
        print(result)
        print("mongo_result_type: ",type(result))
        print("mongo_result: ", result)
        if type(result) == pymongo.cursor.Cursor: # find() 실행시
            explain = getattr(result,'explain')()
            explain = explain['queryPlanner'] 
            result = JSONEncoder().encode(list(result))
        
        elif type(result) == dict: # result 타입이 dictionary 일때
            result = JSONEncoder().encode([result])
        elif type(result) == str:
            result = [result]
        elif type(result) == pymongo.database.Database:
            result = JSONEncoder().encode([{"db_name":result.name}])
        
        elif type(result) == pymongo.collection.Collection:
            result = JSONEncoder().encode([{"collection_name":result.name}])
        else:
            result = None
        
        
        return result,converted_list,explain


    def get_cursor(self):
        return self.cur
    
    def excuteOne(self, sql, args=()):
        self.cur.execute(sql,args)
        return self.cur.fetchone()
    
    def excuteAll(self, sql, args=()):
        self.cur.execute(sql,args)
        return self.cur.fetchall()
    
    def commit(self):
        self.conn.commit()
    
    def close(self):
        if self.dbms != "mongo":
            self.cur.close()
            self.conn.close()
        else:
            self.mongo_client.close()    
    
    #몽고db 연결 객체 반환
    def get_mongo_client(self):
        return self.mongo_client.get_default_database()

    # def get_client(self):
    #     return self.mongo_client

    def show_databases_and_tables(self,db_info):
        '''
            연결된 데이터베이스 스키마 및  테이블 조회
            Args:
                db_info : dbms_info테이블 fetchone()한 정보
            Returns:
                조회된 database와 table
        '''
        databases = None
        if self.dbms == 'oracle':
            # tables = self.excuteAll(f"SELECT default_tablespace FROM user_users")
            tables = self.excuteAll("SELECT * FROM tab")
        elif self.dbms == 'mongo':
            #외부 접속시만 database list 가져오기
            databases = self.mongo_client.list_database_names() if db_info[6] == 0 else None
            if databases:
                tables = {}
                for db in databases:
                    tables[db] = [self.mongo_client[db].list_collection_names()]
          
            else:
                tables = []
                #uri 지정한 db_name
                db = self.mongo_client.get_default_database().name
                tables.append(self.mongo_client[db].list_collection_names()) 
        
        else:
            databases = [db[0] for db in self.excuteAll('show databases') if db[0] != 'information_schema' ] if db_info[6] == 0 else None
            #외부db 연결시
            if databases:
                tables = {}
                for db in databases:
                    tables[db] = self.excuteAll(f'show tables from {db}')
            else:
                tables = self.excuteAll('show tables')

        return databases,tables  
    
    
    def show_explain(self,sql):
        '''
            db 실행계획 보여주기
            Args:
                sql: sql 질의(string)
            Returns:
                실행계획    
        '''
        explain = None
        if self.dbms == 'oracle':
            
            self.excute(f"explain plan for {sql}")
            explain = self.excuteAll("select * from table(dbms_xplan.display)")[5:-1]
            explain = [el[0].split('|')[2:] for el in explain]

        else:
            explain=self.excuteOne(f"explain format=json {sql}")
        return explain




