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



class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

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

        #몽고 디비 
        self.mongo_to_pymongo = {
            'get_collection_names' : 'collection_names',

        }
    
        #mysql, mariadb 연결
        if dbms == 'mysql' or dbms =='maria':
            # self.defaults.pop('password') if dbms == 'mysql' else self.defaults.pop('passwd')
            #kargs 값이 있으면 defaults values 덮어쓰게 된다
            self.defaults.update(kargs)
            self.conn = mysql.connect(**self.defaults)
            self.cur = self.conn.cursor()    

        #오라클 연결    
        elif dbms == 'oracle':
            #kargs 값이 있으면 oracle_defaults values 덮어쓰게 된다
            self.oracle_defaults.update(kargs)
            self.conn = oracle.connect(
                self.oracle_defaults.get('user'),
                self.oracle_defaults.get('password'),
                self.oracle_defaults.get('host') + ":" + str(self.oracle_defaults.get('port')),
                encoding='UTF-8'
            )
            self.cur = self.conn.cursor()
        elif dbms == "mongo":
            uri = "mongodb://%s:%s@%s:%s/%s" % (
                kargs.get('user'),kargs.get('password'),kargs.get('host'),kargs.get('port'),kargs.get('database'))
                
            self.mongo_client = MongoClient(uri)
            
        else:
            raise Exception('dbms가 존재하지 않습니다.')
        
        
        
    
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
        tokens = query.split('.')
        result = None
        
        for i,token in enumerate(tokens):
            
            if i == 0:
                if token != 'db':
                    raise Exception(f'{token} is not defined')
                result = self.get_mongo_client()
            
            #함수면 실행
            elif re.compile("^\w+\(.*\)$").match(token):
                #함수명, 함수argument로 split
                func_name,args = token.split('(')

                #함수명 리스트로 변환 
                new_func_name = list(func_name)
                
                args = args.replace(')','').strip()
                #pymongo function params
                params = []
                print("args: ",args)
                if args != "":
                    #argument json 있으면
                    if re.compile('\{(.|\n)*\}').match(args):
                        json_match = re.compile('\{(.|\n)*\}').match(args)
                        params.append(json.loads(json_match.group().replace("'","\"")))#json append
                        option_args = args[json_match.end():].split(',') #json 제외한 args
                        #json 제외한 args 리스트에 추가
                        for option in option_args[1:]:
                            params.append(option)
                    else:
                        #args 리스트에 추가
                        for option in args.split(","):
                            params.append(option)   

                # 함수명 스타일 변경
                #ex) findOne -> find_one
                for m in re.compile("[A-Z]").finditer(func_name):
                    new_func_name[m.start()] = '_'+m.group().lower()

                new_func_name = "".join(new_func_name)
                new_func_name = self.mongo_to_pymongo.get(new_func_name) if self.mongo_to_pymongo.get(new_func_name) else new_func_name
                converted_list.append([new_func_name,func_name])
                
                result = getattr(result,new_func_name)(*params)
            elif i == 1: #collection_name이면 실행
                result = getattr(result,'get_collection')(token)


        explain = None
        if type(result) == pymongo.cursor.Cursor: # find() 실행시
            explain = getattr(result,'explain')()
            explain = explain['queryPlanner'] 
            result = JSONEncoder().encode(list(result))


        if type(result) == dict: # result 타입이 dictionary 일때
            result = JSONEncoder().encode([result])
        
        if type(result) == pymongo.database.Database:
            result = JSONEncoder().encode([{"db_name":result.name}])
        
        if type(result) == pymongo.collection.Collection:
            result = JSONEncoder().encode([{"collection_name":result.name}])

        print("mongo_result_type: ",type(result))
        print("mongo_result: ", result)
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
            print(explain)

        else:
            explain=self.excuteOne(f"explain format=json {sql}")
        return explain




