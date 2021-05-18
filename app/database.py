from re import split
from flask import current_app
import mysql.connector as mysql
import cx_Oracle as oracle



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
    
        #mysql, mariadb 연결
        if dbms == 'mysql' or dbms =='maria':
            # self.defaults.pop('password') if dbms == 'mysql' else self.defaults.pop('passwd')
            #kargs 값이 있으면 defaults values 덮어쓰게 된다
            self.defaults.update(kargs)
            self.conn = mysql.connect(**self.defaults)
            

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
        else:
            raise Exception('dbms가 존재하지 않습니다.')
        
        self.cur = self.conn.cursor()
        
    
    def excute(self, sql, args=()):
        self.cur.execute(sql,args)
    
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
        self.cur.close()
        self.conn.close()
    
    
    
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
        explain = None
        if self.dbms == 'oracle':
            
            self.excute(f"explain plan for {sql}")
            explain = self.excuteAll("select * from table(dbms_xplan.display)")[5:-1]
            explain = [el[0].split('|')[2:] for el in explain]
            print(explain)

        else:
            explain=self.excuteOne(f"explain format=json {sql}")
        return explain



