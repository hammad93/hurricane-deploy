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

  # https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps
  os.environ['AZURE_CLIENT_ID'] = passwords[passwords['user'] == 'azure_client'].iloc[0]['pass']
  os.environ['AZURE_TENANT_ID'] = passwords[passwords['user'] == 'azure_tenant'].iloc[0]['pass']
  os.environ['AZURE_CLIENT_SECRET'] = passwords[passwords['user'] == 'azure_key'].iloc[0]['pass']
  os.environ['AZURE_CONTAINER_REGISTRY_PWD'] = passwords[passwords['user'] == 'acr_key'].iloc[0]['pass']


def chatgpt_reflection_forecast_concurrent(model='gpt-3.5-turbo'):
  # get the live storms first
  live_storms = get_live_storms()
  # validate the live data
  if len(live_storms) < 1 :
    return 'No storms currently around the world.'

  # generate prompts for one of the storms
  # some storms have long history so we have to set a threshold
  max_historical_track = 4 * 7 # days, approx if 6 hour interval
  tag = int(time.time()) # a unique tag to track the data
  final_results = []
  for storm in set(live_storms['id']):
    # get the storm from the live data and sort by time
    storm_data = live_storms.query(f"id == '{storm}'").sort_values(by='time', ascending=False).iloc[:max_historical_track]
    # clean the data to prepare to use it for the prompt
    storm_data_input = storm_data.drop(columns=['id', 'wind_speed_mph', 'wind_speed_kph']).to_json(indent=2, orient='records')
    print(storm_data_input)
    prompts = storm_forecast_prompts_sequentially(storm_data_input)

    # execute prompts concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
      results = list(executor.map(
          lambda p: chatgpt(*p),
            [
              (prompt["prompt"],
                model,
                5,
                f"{tag}_{storm}_{index}",
                {
                  'forecast_hour': prompt['forecast_hour']
                })
              for index, prompt in enumerate(prompts)
              ]
          )
      )
    # execute reflection prompts
    forecast_string = pd.DataFrame([{**result['json'],
                                    'forecast_hour': result['metadata']['forecast_hour']
                                   } for result in results]).to_json(indent=2, orient='records')
    with concurrent.futures.ThreadPoolExecutor() as executor:
      results_reflection = list(executor.map(
          lambda p: chatgpt(*p),
            [
              (prompt["reflection"].substitute(future=prompt['forecast_hour'], forecast=forecast_string),
                model,
                5,
                f"{tag}_{storm}_{index}",
                {
                  'forecast_hour': prompt['forecast_hour']
                })
              for index, prompt in enumerate(prompts)
              ]
          )
      )

    # add iteration to final results
    base_time = list(storm_data['time'])[0] # sorted desc this is the most recent
    final_results.append([{
          **result['json'], # dictionary unpacking
          'id': storm,
          'time': dateutil.parser.parse(base_time) + timedelta(hours=result['metadata']['forecast_hour']),
          'metadata': result['metadata']
      } for result in results_reflection if result['json']]
    )

  # return the forecast after reflection
  return final_results

def chatgpt(prompt, model_version="gpt-3.5-turbo", retries=5, id=None, metadata=False):
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
    id String
        The thread id, will be created if none exist.
    retries int
        The amount of times to try the prompt again

    Returns
    -------
    pd.DataFrame
    '''
    global config
    openai.api_key = os.environ.get('OPENAI_API_KEY')

    # generate chat or message
    basic = [{"role": "system", "content": "Please act as a weather forecaster and a helpful assistant. Data provided are real time and from official sources including NOAA."},
      {"role": "user", "content": prompt}
    ]
    if id :
      print(id)
      # create chats object if it doesn't exist
      if not config.get('chats', False):
        config['chats'] = {}
      # create id if it doesn't exist
      if not config['chats'].get(id, False) :
        print(f'Adding id, {id} to chat.')
        config['chats'][id] = basic
      chat = config['chats'][id]
    else :
      chat = basic

    json_object = False
    
    # we retry until we get a parsable json
    while json_object is False and retries > 1:
      response = openai.ChatCompletion.create(
          model=model_version,
          messages=chat
      )
      text = response["choices"][0]["message"]["content"]
      print(text)

      json_string = msg_to_json(text)
      print(json_string)
      # Parse the JSON string into a Python object
      try :
        json_object = json.loads(json_string)
      except Exception as e :
        # this could be a QA check that results in True so we flag it here,
        if config['chats'].get(id, False) and text[:4].lower() == 'true':
          # get the previous message response, if there is one
          prev = config['chats'][id][-1]['content']
          # set it as a json_object
          try :
            json_object = json.loads(msg_to_json(prev))
          except :
            print(f"Couldn't parse JSON even though it passed, {prev}")
        print(f"Couldn't parse JSON in the response. Retries: {retries}, {e}")
      retries = retries - 1

    if id and config['chats'].get(id, False) :
      print(f"Adding response to chat history {id}.")
      config['chats'][id] += [{"role": "user", "content": prompt},
      {"role": "assistant", "content": text}]

    # update metadata with model run version
    version = {'model': model_version}
    return {
        "text" : text,
        "json" : json_object,
        "metadata" : version if not metadata else {**metadata, **version}
    }
setup()
