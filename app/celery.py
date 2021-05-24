from flask import current_app
from . import celery
import os 
from .database import Database
import csv
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import time



@celery.task(bind=True)
def async_import_csv(self,db_info,csv_file_name,table_name,database_name):
    error=None
    current =0
    total = 1

    user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3],database = db_info[5])

    
    try:
        
        with open(os.path.join(current_app.config['UPLOAD_FOLDER_PATH'],csv_file_name),'r',encoding="utf-8") as f:
            
            total = len(f.readlines())-1
            f.seek(0)
            
            rdr = csv.reader(f)

            header = next(rdr)
            columns = ','.join(header)
            
            
            if db_info[0] == 'oracle':
                bind_format = ','.join([':'+str(i) for i in range(1,len(header)+1)])
            else:
                bind_format = ','.join(["%s"]*len(header))

            
            for i,line in enumerate(rdr):
                
                if database_name and db_info[0] != 'oracle':

                    sql =f"""INSERT INTO {database_name}.{table_name}({columns}) values({bind_format})"""
                else:   
                    sql =f"""INSERT INTO {table_name}({columns}) values({bind_format})"""
                
                print(sql)
                user_db.excute(sql,tuple(line))
                self.update_state(state='PROGRESS', meta={'current': i+1, 'total': total})
            current=i+1
            
            
            user_db.commit()
    except Exception as e:
        print(e)
        error=str(e)
        
    finally:
        user_db.close()
        
        if os.path.isfile(os.path.join(current_app.config['UPLOAD_FOLDER_PATH'],csv_file_name)):
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER_PATH'],csv_file_name))


    context = {'current':current, 'total': total}

    if error:
        context.update({'error':error})

    return context
    
    
    #self.update_state(state='PROGRESS', meta={'current': i, 'total': total})



@celery.task(bind=True)
def async_export_csv(self,db_info,csv_file_name,table_name,database_name):
    error   = None
    current = 0
    total   = 1
    user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3],database = db_info[5])
    encryption_file_name = secure_filename(str(generate_password_hash(str(time.time())))+".csv")
    try:
        rows = user_db.excuteAll(f"""SELECT * FROM {table_name}""")
        
        columns = [col[0] for col in user_db.get_cursor().description ]
        total = int(user_db.excuteOne(f"""SELECT COUNT(*) FROM {table_name}""")[0])

        with open(os.path.join(current_app.config['DOWNLOAD_FOLDER_PATH'],encryption_file_name),'w',encoding="utf-8",newline="") as f:
            
            wr = csv.writer(f)
            print(columns)
            wr.writerow(columns)
            for row in rows:
                
                wr.writerow(row)
                current += 1
                self.update_state(state='PROGRESS', meta={'current': current, 'total': total})

    except Exception as e:
        print(e)
        error = str(e)
    finally:
        user_db.close()
        

    context = {'current':current, 'total': total}

    if error:
        context.update({'error':error})

    return context





