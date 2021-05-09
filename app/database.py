from flask import current_app
import mysql.connector as mysql
import cx_Oracle as oracle



class Database():
    def __init__(self,dbms='mysql',**kargs):
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
            'host' : current_app.config.get('DB_HOST') + ':' + current_app.config.get('ORACLE_PORT'),
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
            print(self.oracle_defaults)
            self.conn = oracle.connect(*self.oracle_defaults.values())
        else:
            raise Exception('dbms가 존재하지 않습니다.')
        
        self.cur = self.conn.cursor()
    
    
    def excute(self, sql, args):
        self.cur.execute(sql,args)
    
    def get_cursor(self):
        return self.cur
    
    def excuteOne(self, sql, args):
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
