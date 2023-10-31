import config
import pandas as pd
import os

def setup():
  '''
  Setup environment variables and other conditions similar to
  production
  '''
  passwords = pd.read_csv(config.credentials_dir)
  os.environ["OPENAI_API_KEY"] = passwords[passwords['user'] == 'openai'].iloc[0]['pass']
  os.environ["OPENAI_API_BASE"] = passwords[passwords['user'] == 'openai'].iloc[0]['host']

setup()
