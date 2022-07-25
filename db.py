from sqlalchemy import create_engine
import pandas as pd


def connection_string(database):
    '''
    Creates the connection string to the specified database
    '''
    credentials_df = pd.read_csv('/root/credentials.csv')
    config = credentials_df.iloc[1]
    return f"mysql://{config['user']}:{config['pass']}@{config['host']}:{config['port']}/{database}"

def get_engine(database):
    '''
    Returns a connection engine from SQLAlchemy
    '''
    return create_engine(connection_string(database))

def query(q, database):
    '''
    Query the remote database and return as a dataframe
    '''
    return pd.read_sql(q, get_engine(database))