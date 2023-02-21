'''
Hammad Usmani

When running this script, `python download_models.py` it will
download the hurricane artificial intelligence model files
into the /root/ directory
'''
import os

def download_model(url) :
    '''
    Downloads a model based on the directory timestamp in the .pb
    TensorFlow framework format.

    Parameters
    ----------
    url String
        The public URL where we can download online the .pb file


    Notes
    -----
    - The authentication uses the default Python Google Cloud API
    configuration JSON

    '''
    model_directory = config.forecast_model_dir

    # Create the model directory if it doesn't exist
    if not os.path.exists(model_directory):
        os.makedirs(model_directory)

    # Download the model using wget
    os.system(f"wget {url} -P {model_directory}")

download_model(config.forecast_model)
