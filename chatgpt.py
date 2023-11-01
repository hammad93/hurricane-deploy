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

def chatgpt_forecast_live(model_version):
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
    live_storms_cleaned = live_storms.drop(columns=['wind_speed_mph', 'wind_speed_kph'])
    prompts = get_prompts(live_storms_cleaned)
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
                    {"role": "system", "content": "Please act as an expert forecaster and a helpful assistant. Responses should be based on historical data and forecasts must be as accurate as possible. Provided are live data from official source including NOAA and NASA."},
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

def get_prompts(df, historical_limit = 5):
    '''
    Utilizing the current global tropical storms, we will generate prompts
    for a LLM such as ChatGPT to provide forecasts. This function will
    generate prompts for each storm

    Intput
    ------
    df pd.DataFrame
        The records include the columns id, time, lat, lon, wind_speed.
    historical_limit int
        When creating the prompts, this limits the historical limits.
    '''
    unique_storms = set(df['id'])
    prompts = []
    # apply each storm to the prompt template
    for storm in unique_storms:
        current_storm = df[df['id'] == storm].drop(columns=['id']).sort_values(by='time', ascending=False)
        # because it's sorted by latest, it's the first row
        current_storm_latest = current_storm.iloc[0]['time']
        forecast_times = '12, 24, 36, 48, and 72'
        prompt = f'''
Please provide forecasts for {forecast_times} hours in the future from the most recent time in Table 1.
These forecasts should be based on historical knowledge which includes but is not limited to storms with similar tracks and intensities, time of year of the storm, geographical coordinates, and climate change that may have occured since your previous training.
The response will be a list of JSON objects with these attributes:
    "forecast" which is the hour ahead you're forecasting as an integer, e.g. 12 for 12 hours in the future
    "lat" which is the predicted latitude
    "lon" which is the predicted longitude
    "wind_speed" which is the predicted maximum sustained wind speed in knots.
There should be 5 JSON objects in this list each corresponding to the forecast times {forecast_times} hours in the future.
All coordinates are decimal degrees and follow WGS 84.

Table 1.
- The wind_speed column is in knots representing the maxiumum sustained wind speeds.
- The lat and lon are the geographic coordinates
- time is sorted and the most recent time is the first entry.
- We have limited the history to {historical_limit} records.
In JSON,
{current_storm.head(historical_limit).to_json(indent=2, orient='records')}
        '''
        prompts.append((prompt, {
          'latest_time': current_storm_latest,
          'forecast_times': forecast_times
        }))
        print(prompt)
    return prompts
