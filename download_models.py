'''
Hammad Usmani

When running this script, `python download_models.py` it will
download the hurricane artificial intelligence model files
into the /root/ directory.

It will also place a ChatGPT class for prediciting tropical storms
that can be imported like import hurricane_net_chatgpt
'''
import os
import config

def download_model(url) :
    '''
    Downloads a model based on the directory timestamp in the .pb
    TensorFlow framework format.

    Parameters
    ----------
    url String
        The public URL where we can download online the .pb file

    '''
    model_directory = config.forecast_model_dir

    # Create the model directory if it doesn't exist
    if not os.path.exists(model_directory):
        os.makedirs(model_directory)

    # Download the model using wget
    os.system(f"wget {url} -P {model_directory}")
    
if __name__ == "__main__":
    download_model(config.forecast_model)
    
    # Download ChatGPT in the same way
    os.system(f"wget {conifg.forecast_chatgpt} -P {os.path.abspath(os.path.dirname(__file__))}")

