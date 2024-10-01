from sqlalchemy import create_engine, text
import pandas as pd
import config
import redis
import os
import json
import test
import boto3


def download_file_s3(file_name, bucket, path):
  '''
  Parameters
  ----------
  path string
    In order to have space, we check if we have already downloaded it in this path
   
  '''
  # check if we have already downloaded it and can pass the data
  
  full_path = path + file_name
  if os.path.exists(full_path):
     print('The file exists already')
  else:
     # download the file
     s3 = boto3.client('s3')
     s3.download_file(bucket, file_name, full_path)

def redis_client():
    '''
    Returns the client based on current configurations
    '''
    test.setup()
    return redis.StrictRedis(host = os.environ['AZURE_REDIS_HOST'],
                          password = os.environ['AZURE_REDIS_KEY'],
                          port = os.environ['AZURE_REDIS_PORT'],
                          ssl = True)

def connection_string(database):
    '''
    Creates the connection string to the specified database
    '''
    credentials_df = pd.read_csv(config.credentials_dir)
    auth = credentials_df.iloc[1]
    return f"postgresql://{auth['user']}:{auth['pass']}@{auth['host']}:{int(auth['port'])}/{database}"

def get_engine(database):
    '''
    Returns a connection engine from SQLAlchemy
    '''
    # echo and echo_pool enable direct logging
    return create_engine(connection_string(database), echo=True, echo_pool="debug")

def query(q, database = 'hurricane_live', write = False):
    '''
    Query the remote database and return as a dataframe
    '''
    if write :
        with get_engine(database).connect() as conn :
            print(q)
            # check to see if query was a string
            if type(q[0]) == str:
                result = conn.execute(text(*q))
            else:
                result = conn.execute(*q)
            print(result)
            conn.commit()
        return result
    return pd.read_sql(q, get_engine(database))
