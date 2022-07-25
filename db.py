from sqlalchemy import create_engine
import pandas as pd


def connection_string(database):
    '''
    Creates the connection string to the specified database
    '''
    credentials_df = pd.read_csv('/root/credentials.csv')
    config = credentials_df.iloc[1]
    return f"'mysql://{config['user']}:{config['pass']}@{config['host']}:{config['port']}/{database}"
def query(q, database):
    '''
    Query the remote database and return as a dataframe
    '''
    engine = create_engine(connection_string(database))
    return pd.read_sql(q, engine)

