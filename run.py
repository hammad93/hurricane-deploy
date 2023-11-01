from typing import Union, List
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import config
import db
import chatgpt
import pandas as pd
import traceback
import os

app = FastAPI(
    title="fluids API",
    description="A 100% independent and non-profit weather API providing accurate, global weather data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
cache = {}

@app.get("/")
def read_root():
    return {"Hello": "World"}


class StormData(BaseModel):
    id: str = Field(..., description="Storm ID")
    time: str = Field(..., description="ISO8601 timestamp")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    wind_speed: int = Field(..., description="Maximum sustained wind speed in knots")
    wind_speed_mph: float = Field(..., description="Maximum sustained wind speed in miles per hour")
    wind_speed_kph: float = Field(..., description="Maximum sustained wind speed in kilometers per hour")

@app.get("/live-storms", response_model=List[StormData])
async def get_live_storms() -> List[StormData]:
    """
    Retrieve live tropical storm data.

    Returns:
        list: A list of dictionaries containing the current live tropical storms
              with keys: id, time, lat, lon, and int.
    """
    data = db.query("SELECT * FROM hurricane_live")
    data['time'] = data['time'].astype(str)  # Convert 'time' column to string
    data = data.rename(columns={'int': 'wind_speed'})  # Rename 'int' column to 'wind_speed'
    storms = data.to_dict(orient="records")
    for storm in storms:
        # wind speed is in knots
        storm['wind_speed_mph'] = int(storm['wind_speed']) * 1.852
        storm['wind_speed_kph'] = int(storm['wind_speed']) * 1.15078
    return storms

@app.get("/forecast-live-storms")
def forecast_live_storms(model='all'):
    """
    Get a weather storm forecast using different versions of OpenAI's GPT models.

    This FastAPI endpoint uses the chat completion feature from OpenAI to forecast weather storms.
    It can either use a single specified model or a list of pre-defined models to get multiple forecasts.

    Parameters:
    -----------
    model : str, optional
        The specific GPT model to use for the forecast. 
        Default is 'all', which uses all available models ['gpt-3.5-turbo', 'gpt-4'].
    
    Returns:
    --------
    list[dict]
        A list of forecast data as dictionaries. Each dictionary contains the forecast information and
        the model used for that particular forecast. 

    Raises:
    -------
    HTTPException:
        If an error occurs while fetching or processing the forecast data.
        
    Notes:
    ------
    - Uses a global `cache` dictionary to store the forecast data.
    - Fetches current live storms to feed into the language models for forecasting.
    """
    global cache
    # Generate all available forecasts from the framework
    if model == 'all' :
        #available_models = ['gpt-35-turbo', 'gpt-4']
        available_models = ['live']
    else :
        available_models = [model]
    forecast = []
    for _model in available_models :
        try:
            # We use the script to get current live storms and feed it into the LLM
            preprocessed = chatgpt.chatgpt_forecast_live(model_version=_model)
            if _model == 'live' :
                preprocessed['model'] = 'gpt-35-turbo'
            else:    
                preprocessed['model'] = _model
            print(preprocessed.head())
            # finish prepropossing by transforming to final data structure
            # list of dict's
            processed = preprocessed.to_dict(orient="records")
            # note that we use extend to reduce dimensionality of data model
            forecast.extend(processed)
        except Exception as e:
            return traceback.print_exc()
    cache['forecasts'] = forecast
    return cache['forecasts']


@app.get('/forecasts')
def forecasts():
    '''
    Provides the last generated forecast in the cache.
    '''
    global cache
    return cache['forecasts']

if __name__ == "__main__":
    # Set ChatGPT password
    passwords = pd.read_csv(config.credentials_dir)
    os.environ["OPENAI_API_KEY"] = passwords[passwords['user'] == 'openai'].iloc[0]['pass']
    os.environ["OPENAI_API_BASE"] = passwords[passwords['user'] == 'openai'].iloc[0]['host']
    uvicorn.run("run:app", host="0.0.0.0", port=1337, reload=True)
