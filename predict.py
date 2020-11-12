import update
import pickle
import pandas as pd
import sklearn
from google.cloud import storage
from datetime import timedelta
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
        df = pd.DataFrame(storm['entries'])
        df.set_index('time')
        input = df[df['time'].isin(
            [df['time'].max() - timedelta(hours = delta)
             for delta in [0,24,48,72,96,120]])
        ].sort_values('time', ascending = False)
        input = [list(feature_extraction(input.iloc[i + 1], input.iloc[i]).values())
                 for i in range(5)]

        # scale our input
        input = np.expand_dims(scaler.transform(input), axis = 0)

        # get our prediction
        prediction = list(predict_json('cyclone-ai', 'universal', 
                                       input)[0].values())[0]
        
        # inverse transform the prediction
        lat = [output[0] for output in scaler.inverse_transform(
            [[lat[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] for lat in
             prediction])]
        long = [output[1] for output in scaler.inverse_transform(
            [[0, long[0], 0, 0, 0, 0, 0, 0, 0, 0, 0] for long in
             prediction])]
        wind = [output[2] for output in scaler.inverse_transform(
            [[0, 0, wind[0], 0, 0, 0, 0, 0, 0, 0, 0] for wind in
             prediction])]

        output = dict()
        for index, value in enumerate([24, 48, 72, 96, 120]):
            output[value] = {
                'lat': lat[index],
                'long': long[index],
                'max_wind': wind[index] * 1.15078
            }

        results.append(output)
        print(f'Done with {storm["id"]}')

    return results