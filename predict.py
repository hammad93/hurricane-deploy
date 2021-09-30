import update
import pickle
import numpy as np
import pandas as pd
import logging
import requests
import json
from google.cloud import storage
from datetime import timedelta
from datetime import timezone
import googleapiclient.discovery

def download_file(filename) :
    storage_client = storage.Client()
    bucket = storage_client.bucket('cyclone-ai.appspot.com')
    blob = bucket.blob(filename)
    blob.download_to_filename(f'/root/{filename.split("/")[-1]}')


def feature_extraction(timestep, previous):
    '''
    PURPOSE: Calculate the features for a machine learning model within the context of hurricane-net
    METHOD: Use the predictors and the calculation methodology defined in Knaff 2013
    INPUT:  timestep - current dictionary of features in the hurricane object format
            previous - previous timestep dictionary of features in the hurricane object format
    OUTPUT: Dictionary of features

    timestep = {
      'lat' : float,
      'long' : float,
      'max-wind' : float,
      'entry-time' : datetime
    }
    '''
    features = {
        'lat': timestep['lat'],
        'long': timestep['lon'],
        'max_wind': timestep['wind'],
        'delta_wind': (timestep['wind'] - previous[
            'wind']) /  # Calculated from track (12h)
                      ((timestep['time'] - previous[
                          'time']).total_seconds() / 43200),
        'min_pressure': timestep['pressure'],
        'zonal_speed': (timestep['lat'] - previous[
            'lat']) /  # Calculated from track (per hour)
                       ((timestep['time'] - previous[
                           'time']).total_seconds() / 3600),
        'meridonal_speed': (timestep['lon'] - previous[
            'lon']) /  # Calculated from track (per hour)
                           ((timestep['time'] - previous[
                               'time']).total_seconds() / 3600),
        'year': timestep['time'].year,
        'month': timestep['time'].month,
        'day': timestep['time'].day,
        'hour': timestep['time'].hour,
    }
    return features

def predict_json(project, model, instances, version=None):
    """Send json data to a deployed model for prediction.

    Args:
        project (str): project where the Cloud ML Engine Model is deployed.
        model (str): model name.
        instances ([Mapping[str: Any]]): Keys should be the names of Tensors
            your deployed model expects as inputs. Values should be datatypes
            convertible to Tensors, or (potentially nested) lists of datatypes
            convertible to tensors.
        version: str, version of the model to target.
    Returns:
        Mapping[str: any]: dictionary of prediction results defined by the
            model.
    """
    '''
    # Create the ML Engine service object.
    # To authenticate set the environment variable
    # GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_file>
    service = googleapiclient.discovery.build('ml', 'v1')
    name = 'projects/{}/models/{}'.format(project, model)

    if version is not None:
        name += '/versions/{}'.format(version)

    response = service.projects().predict(
        name=name,
        body={'instances': instances}
    ).execute()

    if 'error' in response:
        raise RuntimeError(response['error'])

    return response
    '''
    # make request to hurricane ai
    headers = {"content-type": "application/json"}
    data = json.dumps({"instances" : instances})
    json_response = requests.post(f'http://localhost:9000/v1/models/{model}:predict',
                  data = data,
                  headers = headers)
    print(json_response.text)

    # return results
    return json.loads(json_response.text)["predictions"]


def predict_universal(data = None) :
    # get the update
    if data :
        raw = data
    else :
        raw = update.nhc()

    # read in the scaler
    download_file('model_artifacts/universal/feature_scaler.pkl')
    with open('/root/feature_scaler.pkl', 'rb') as f :
        scaler = pickle.load(f)

    # generate predictions
    results = []
    for storm in raw :
        print(f'Processing {storm["id"]}. . . ')

        # create prescale data structure
        df = pd.DataFrame(storm['entries']).sort_values('time', ascending = False)

        # set reference time and geometric pattern recognition
        reference = df['time'].max().replace(tzinfo = timezone.utc)
        reference_count = 0
        print(f"Reference time is: {reference}")
        while reference.hour not in [0, 6, 12, 18] : # not a regular timezone
            reference_count += 1
            reference = df.iloc[reference_count]['time']
            print(f"Reference time is: {reference}")
        input = df[df['time'].isin(
            [reference - timedelta(hours = delta)
             for delta in [0, 6, 12, 18, 24, 30]])
        ].sort_values('time', ascending = False).reindex()

        # flag for if input is not long enough
        if (len(input) < 6) :
            logging.warning(
                f"{storm['id']}"
                f" does not have enough data, does not follow the input"
                f" pattern for the AI, or an unknown error. Skipping.")
            results.append({'error': f'{storm["id"]} did not have enough records'})
            continue

        # generate input
        input = [list(feature_extraction(input.iloc[i + 1], input.iloc[i]).values())
                 for i in range(5)]

        # scale our input
        input = np.expand_dims(scaler.transform(input), axis = 0)

        # get our prediction
        prediction_json = predict_json('cyclone-ai', 'hurricane', input.tolist())
        print(f'line 157: {prediction_json}')
        prediction = prediction_json[0]
        
        # inverse transform the prediction
        lat = [output[0] for output in scaler.inverse_transform(
            [[lat[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for lat in
             prediction])]
        lon = [output[1] for output in scaler.inverse_transform(
            [[0, lon[0], 0, 0, 0, 0, 0, 0, 0, 0, 0] for lon in
             prediction])]
        wind = [output[2] for output in scaler.inverse_transform(
            [[0, 0, wind[0], 0, 0, 0, 0, 0, 0, 0, 0] for wind in
             prediction])]

        output = dict()
        for index, value in enumerate([12, 18, 24, 30, 36]):
            output[reference + timedelta(hours = value)] = {
                'lat': lat[index],
                'lon': lon[index],
                'max_wind(mph)': wind[index] * 1.15078
            }
        output['id'] = storm['id']
        results.append(output)
        print(f'Done with {storm["id"]}, results:\n{output}')

    return results

def predict_singular(data = None) :
    # get the update
    if data :
        raw = data
    else :
        raw = update.nhc()

    # read in the scaler
    download_file('model_artifacts/universal/feature_scaler.pkl')
    with open('/root/feature_scaler.pkl', 'rb') as f :
        scaler = pickle.load(f)

    # generate predictions
    results = []
    for storm in raw:
        print(f'Processing {storm["id"]}. . . ')

        # create prescale data structure
        df = pd.DataFrame(storm['entries']).sort_values('time', ascending=False)
        # set reference time and geometric pattern recognition
        reference = df['time'].max().replace(tzinfo=timezone.utc)
        reference_count = 0
        print(f"Reference time is: {reference}")
        while reference.hour not in [0, 6, 12, 18]:  # not a regular timezone
            reference_count += 1
            reference = df.iloc[reference_count]['time']
            print(f"Reference time is: {reference}")
        input = df[df['time'].isin(
            [reference - timedelta(hours=delta)
             for delta in [0, 24, 48, 72, 96, 120]])
        ].sort_values('time', ascending=False).reindex()
        # if input is not long enough
        if (len(input) < 6):
            logging.warning(
                f"{storm['id']}"
                f" does not have enough data, does not follow the input"
                f" pattern for the AI, or an unknown error. Skipping.")
            continue
        input = [list(feature_extraction(input.iloc[i + 1], input.iloc[i]).values())
                 for i in range(5)]

        # scale our input
        input = np.expand_dims(scaler.transform(input), axis=0)

        # get our prediction
        prediction = predict_json(
            'cyclone-ai', 'universal', input.tolist())[
            "predictions"][0]["time_distributed"]
        print(prediction)

        # inverse transform the prediction
        lat = [output[0] for output in scaler.inverse_transform(
            [[lat[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for lat in
             prediction])]
        lon = [output[1] for output in scaler.inverse_transform(
            [[0, lon[0], 0, 0, 0, 0, 0, 0, 0, 0, 0] for lon in
             prediction])]
        wind = [output[2] for output in scaler.inverse_transform(
            [[0, 0, wind[0], 0, 0, 0, 0, 0, 0, 0, 0] for wind in
             prediction])]

        output = dict()
        for index, value in enumerate([24, 48, 72, 96, 120]):
            output[reference + timedelta(hours=value)] = {
                'lat': lat[index],
                'long': lon[index],
                'max_wind(mph)': wind[index] * 1.15078
            }
        output['id'] = storm['id']
        results.append(output)
        print(f'Done with {storm["id"]}, results:\n{output}')

    return results
