
from ..database import Database
from datetime import datetime


class Log():
    def __init__(self):
        self.mysql_conn = Database()

    def write_log(self,id,query,status):
        '''
            쿼리 query 로그 기록
            Args
                id    : dbms_info 테이블 id
                query : rdms & mongo query
        '''
        query += ';'
        #sql 실행성공 로깅
        self.mysql_conn.excute('''
                                INSERT INTO sql_log(dbms_info_id,sql_text,status,stampdatetime) 
                                VALUES(%s,%s,%s,%s)
                                ''',
                                (id,query,status,datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.mysql_conn.commit()                        
    def read_logs(self,id):
        '''
            쿼리 로그 조회
            Arg
                id : dbms_info 테이블 id
            returns
                select 결과 반환
        '''
        return self.mysql_conn.excuteAll('''
                                SELECT stampdatetime,status,sql_text 
                                FROM sql_log 
                                WHERE dbms_info_id=%s 
                                ORDER BY stampdatetime desc
                                ''',(id,))

    def close_db_connect(self):
        self.mysql_conn.close()   