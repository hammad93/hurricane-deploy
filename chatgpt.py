from string import Template
from datetime import timedelta
import dateutil
import concurrent.futures
import time
import requests
import pandas as pd
import openai
import json
import os
import config


def storm_forecast_prompts_sequentially(data, hours = [6, 12, 24, 48, 72, 96, 120]):
  prompt = Template('''Please provide  a forecast for $future hours in the future from the most recent time from the storm.
  This forecast should be based on historical knowledge which includes but is not limited to storms with similar tracks and
  intensities, time of year of the storm, geographical coordinates, and climate change that may have occured since your
  previous training.
  The response will be a JSON object with these attributes:
      "lat" which is the predicted latitude in decimal degrees.
      "lon" which is the predicted longitude in decimal degrees.
      "wind_speed" which is the predicted maximum sustained wind speed in knots.

  Table 1. The historical records the includes columns representing measurements for the storm.
  - The wind_speed column is in knots representing the maxiumum sustained wind speeds.
  - The lat and lon are the geographic coordinates in decimal degrees.
  - time is sorted and the most recent time is the first entry.
  $data
  ''')
  reflection_prompt = Template('''Please quality check the response. The following are requirements,
  - The responses are numbers and not ranges.
  - They align with other forecast hours provided.
  This is an aggregated forecast produced by you and included for reference,
  $forecast
  
  Response with either "True" or "False" based on the quality check. If it's False, provide a more accurate forecast for the original
  $future hours in the future. This prompt is given every time and it's possible that the original response is accurate.
  ''')
  return [
    {
      "forecast_hour" : hour,
      "prompt" : prompt.substitute(future=hour, data=data),
      "reflection" : reflection_prompt
    }
        for hour in hours
  ]

def msg_to_json(text):
  # Find the indices of the first and last curly braces in the text
  start_index = text.find('{')
  end_index = text.rfind('}')

  # Extract the JSON string from the text
  json_string = text[start_index:end_index+1]
  return json_string

def chatgpt_forecast_live(model_version = "gpt-35-turbo"):
    '''
    This will pull in the live storms across the globe and engineer
    prompts that will allow us to ingest forecasts from ChatGPT

    Returns
    -------
    list(pd.DataFrame) A list of DataFrames that have the columns
        id, time, lat, lon, and wind_speed
    '''
    # get the current live tropical storms around the globe
    live_storms = get_live_storms()
    prompts = get_prompts(live_storms)
    # capture the forecast from ChatGPT
    # do this concurrently because each prompt is independent
    with concurrent.futures.ThreadPoolExecutor() as executor:
      forecasts = list(executor.map(lambda p: chatgpt_forecast(*p),
                                    [(prompt, model_version) for prompt in prompts]))
    return forecasts

def chatgpt_forecast(prompt, model_version, retries=10):
    '''
    Given the prompt, this will pass it to the version of ChatGPT defined.
    It's meant for forecasts of global tropical storms but can have a range of options.

    Input
    -----
    prompt String
        The initial message to pass to ChatGPT
    system String
        The system message based on the current OpenAI API
    model_version String
        Which model to use

    Returns
    -------
    pd.DataFrame

    References
    ----------
    https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart?tabs=command-line&pivots=programming-language-python
    '''
    openai.api_type = "azure"
    openai.api_version = "2023-05-15" 
    openai.api_base = os.getenv('OPENAI_API_BASE')
    openai.api_key = os.getenv('OPENAI_API_KEY')
    while retries > 0 :
        response = openai.ChatCompletion.create(
            engine=model_version,
            messages=[
                    {"role": "system", "content": "Please act as a forecaster and a helpful assistant. Responses should be based on historical data and forecasts must be as accurate as possible."},
                    {"role": "user", "content": prompt},
                ]
            )
        text = response["choices"][0]["message"]["content"]
        print(text)
        # Parse the JSON string into a Python object
        try:
            json_object = json.loads(msg_to_json(text))
            # Extract the relevant information from the object
            forecasts = json_object['forecasts']
            return pd.DataFrame(forecasts)
        except Exception as e:
            retries = retries - 1
            print(f"Retries left: {retries}, error message: {e}")

def get_live_storms():
    '''
    Upon calling this function, the live tropical storms around the global
    will be returned in a JSON format. Each of the storms returned will have
    the historical records along with in.

    Returns
    -------
    df pandas.DataFrame
        The records include the columns id, time, lat, lon, wind_speed
    '''
    # make the request for live data
    response = requests.get(f"{config.api_url}live-storms")
    if response :
        data = response.json()
    else :
        print(f'There was an error getting live storms, {response.content}')
        return response
    return pd.DataFrame(data)

def get_prompts(df):
    '''
    Utilizing the current global tropical storms, we will generate prompts
    for a LLM such as ChatGPT to provide forecasts. This function will
    generate prompts for each storm

    Intput
    ------
    df pd.DataFrame
        The records include the columns id, time, lat, lon, wind_speed.
    '''
    unique_storms = set(df['id'])
    prompts = []
    # apply each storm to the prompt template
    for storm in unique_storms:
        prompt = f'''
I want you to act like a forecaster who gives a general idea of the future of the storm even though it will not be an official forecast.
Please provide forecasts for 12, 24, 36, 48, and 72 hours in the future from the most recent time in Figure 1.
The response will be JSON formatted with "forecasts" as the only key. The value of the key is a list of forecast objects.
Each forecast object has five attributes:
    "id" which identifies the storm
    "time" which is the predicted time in ISO 8601 format
    "lat" which is the predicted latitude in decimal degrees
    "lon" which is the predicted longitude in decimal degrees
    "wind_speed" which is the predicted maximum sustained wind speed in knots.
The response must be in JSON format, and the JSON characters must be at the beginning of the response.
If you wish to add additional comments, it must be after the JSON data. Avoid the following common mistakes,
- Responding with some variation of the track input.
- Not responding in the appropriate time steps.

Figure 1. The historical records include columns representing measurements for storm {storm}.
The wind_speed column is in knots representing the maximum sustained wind speeds.
The lat and lon are the geographic coordinates in decimal degrees.

In JSON,
{df[df['id'] == storm].to_json()}
        '''
        prompts.append(prompt)
        print(prompt)
    return prompts
