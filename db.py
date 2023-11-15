from sqlalchemy import create_engine
import pandas as pd
import config
import redis
import os
import json
import test

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
    return f"mysql://{auth['user']}:{auth['pass']}@{auth['host']}:{int(auth['port'])}/{database}"

def get_engine(database):
    '''
    Returns a connection engine from SQLAlchemy
    '''
    return create_engine(connection_string(database))

def query(q, database = 'hurricane_live', write = False):
    '''
    Query the remote database and return as a dataframe
    '''
    if write :
        with get_engine(database).connect() as conn :
            print(q)
            result = conn.execute(*q)
            print(result)
            conn.close()
        return result
    return pd.read_sql(q, get_engine(database))
