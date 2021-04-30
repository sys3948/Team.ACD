from flask import current_app
import mysql.connector as mysql

class MysqlDatabase():
    def __init__(self):
        self.conn = mysql.connect(host = current_app.config.get('DB_HOST'), 
                                  user=current_app.config.get('MYSQL_USER'), 
                                  passwd=current_app.config.get('MYSQL_PW'), 
                                  database='ACD')
        self.cur = self.conn.cursor()
    
    def excute(self, sql, args):
        self.cur.execute(sql,args)
    
    def excuteOne(self, sql, args):
        self.cur.execute(sql,args)
        return self.cur.fetchone()
    
    def excuteAll(self, sql, args):
        self.cur.execute(sql,args)
        return self.cur.fetchall()
    
    def commit(self):
        self.conn.commit()
    
    def close(self):
        self.cur.close()
        self.conn.close()
