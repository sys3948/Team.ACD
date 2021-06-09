from flask import current_app
from . import celery
import os 
from .database import Database
import csv
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import time
from bson import ObjectId


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
            
            if db_info[0] != "mongo":
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
            else:
                if database_name:
                    db = user_db.mongo_client[database_name]
                else:
                    db = user_db.get_mongo_client()

                collection = db.get_collection(table_name) 

                for i,line in enumerate(rdr):
                    collection.insert(dict(zip(header,line)))
                    self.update_state(state='PROGRESS', meta={'current': i+1, 'total': total})
            
            
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
    

@celery.task(bind=True)
def async_export_csv(self,db_info,csv_file_name,table_name,database_name):
    error   = None
    current = 0
    total   = 1
    user_db = Database(dbms=db_info[0],host=db_info[1],port = db_info[2],user = db_info[4],password=db_info[3],database = db_info[5])
    encryption_file_name = secure_filename(str(generate_password_hash(str(time.time())))+".csv")
    try:
        if db_info[0] != "mongo":
            if database_name and db_info[0] != 'oracle':
                total = int(user_db.excuteOne(f"""SELECT COUNT(*) FROM {database_name}.{table_name}""")[0])    
                rows = user_db.excuteAll(f"""SELECT * FROM {database_name}.{table_name}""")
            else:
                total = int(user_db.excuteOne(f"""SELECT COUNT(*) FROM {table_name}""")[0])
                rows = user_db.excuteAll(f"""SELECT * FROM {table_name}""")
        
            columns = [col[0] for col in user_db.get_cursor().description ]

            with open(os.path.join(current_app.config['DOWNLOAD_FOLDER_PATH'],encryption_file_name),'w',encoding="utf-8",newline="") as f:
                
                wr = csv.writer(f)
                print(columns)
                wr.writerow(columns)
                for row in rows:
                    
                    wr.writerow(row)
                    current += 1
                    self.update_state(state='PROGRESS', meta={'current': current, 
                                                            'total': total,
                                                            'encryption_file_name':encryption_file_name,
                                                            'csv_file_name':csv_file_name})
            
        else:
            if database_name:
                db = user_db.mongo_client[database_name]
            else:
                db = user_db.get_mongo_client()
            collection = db.get_collection(table_name) 
            total      = collection.find().count()
            header     = set([])
            for doc in collection.find():
                header.update(list(doc.keys()))
            
            header = list(header)

            with open(os.path.join(current_app.config['DOWNLOAD_FOLDER_PATH'],encryption_file_name),'w',encoding="utf-8",newline="") as f:
                wr = csv.writer(f)
                print(header)
                wr.writerow(header)
                print(list(collection.find()))
                for doc in collection.find():
                    values = ["" for _ in range(len(header))]
                    for key,value in doc.items():
                        
                        values[header.index(key)] = str(value)
                    print("values: ",values)
                    wr.writerow(values) 
                    current += 1
                    self.update_state(state='PROGRESS', meta={'current': current, 
                                                            'total': total,
                                                            'encryption_file_name':encryption_file_name,
                                                            'csv_file_name':csv_file_name})
                
    
    except Exception as e:
        print(e)
        error = str(e)
    finally:
        user_db.close()
        
    if not error and current==0 : current=1
    context = {'current':current, 'total': total,'encryption_file_name':encryption_file_name,'csv_file_name':csv_file_name}

    if error:
        context.update({'error':error})

    return context







