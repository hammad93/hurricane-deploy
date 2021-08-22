'''
Hammad Usmani

When running this script, `python download_models.py` it will
download the hurricane artificial intelligence model files
into the /root/ directory
'''

from google.cloud import storage
import os

def download_model(dir) :
    '''
    Downloads a model based on the directory timestamp in the .pb
    TensorFlow framework format.

    Parameters
    ----------
    dir String
        The directory within the Google Cloud directory space


    Notes
    -----
    - The authentication uses the default Python Google Cloud API
    configuration JSON

    '''
    # create configuration
    storage_client = storage.Client()
    bucket = storage_client.bucket('cyclone-ai.appspot.com')

    # download model
    filename = dir + '/saved_model.pb'
    blob = bucket.blob(filename)
    dir_name = dir.split('/')[-1]
    print(f'Downloading {dir_name} . . .', end='')
    dir_save = f'/root/forecast/1'
    os.mkdir(dir_save)
    blob.download_to_filename(f'{dir_save}/{filename.split("/")[-1]}')
    print('Done!')

    # download variables
    print(f'Downloading {dir_name} variables . . .', end='')
    os.mkdir(f'{dir_save}/variables')
    for var in bucket.list_blobs(prefix=dir + '/variables') :
        filename = var.name.split('/')[-1]
        var.download_to_filename(f'{dir_save}/variables/{filename}')
    print('Done!')

config = {
    'path' : 'model_2020_11_10_07_53'
}

download_model(config['path'])