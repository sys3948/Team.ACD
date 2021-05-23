from flask import current_app
from . import celery
import os 
from .database import Database
import csv



@celery.task(bind=True)
def async_import_csv(self,db_info,csv_file_name,table_name,database_name):
    error=None
    user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3],database = db_info[5])
    current =0
    total = 1
    try:
        
        print(user_db)
        print(csv_file_name)
        with open(os.path.join(current_app.config['UPLOAD_FOLDER_PATH'],csv_file_name),'r',encoding="utf-8") as f:
            
            total = len(f.readlines())-1
            f.seek(0)
            
            rdr = csv.reader(f)

            header = next(rdr)
            columns = ','.join(header)
            str_format = ','.join(["%s"]*len(header))

            for i,line in enumerate(rdr):
                if database_name:
                    sql =f"""INSERT INTO {database_name}.{table_name}({columns}) values({str_format})"""
                else:   
                    sql =f"""INSERT INTO {table_name}({columns}) values({str_format})"""
                
                user_db.excute(sql,tuple(line))
                self.update_state(state='PROGRESS', meta={'current': i+1, 'total': total})
            current=i+1
            
            
            user_db.commit()
    except Exception as e:
        print(e)
        error=str(e)
        
    finally:
        user_db.close()


    context = {'current':current, 'total': total}

    if error:
        context.update({'error':error})

    return context
    
    
    #self.update_state(state='PROGRESS', meta={'current': i, 'total': total})

from celery import current_app as cur_app
@celery.task
def async_revoke_task(task_id):
    cur_app.control.revoke(task_id, terminate=True)
    return {'state':'취소 완료'}




