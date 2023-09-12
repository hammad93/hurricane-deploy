from typing import Union, List
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import config
import db
import hurricane_net_chatgpt as chatgpt
import pandas as pd
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

@app.get("/chatgpt_forecast_storm_live")
def chatgpt_forecast_storm_live(model='all'):
    '''
    We utilize the chat completion from OpenAI and prompt for forecasts
    one storm at a time.
    '''
    global cache
    # Generate all available forecasts from the framework
    if model == 'all' :
        available_models = ['gpt-3.5-turbo', 'gpt-4']
        forecast = []
        for _model in available_models :
            try:
                # We use the script to get current live storms and feed it into the LLM
                preprocessed = chatgpt.chatgpt_forecast_live(model_version=_model)
                processed = [f.update({'model': _model}) for f in preprocessed]
                forecast.extend(processed)
            except Exception as e:
                return str(e)
    else :
        try:
            preprocessed = chatgpt.chatgpt_forecast_live(model_version=model)
            processed = [f.updated({'mode': modell}) for f in preprocessed]
            forecast = processed
        except Exception as e:
            return str(e)
    forecast = pd.concat(forecast)
    cache['forecasts'] = forecast.to_dict(orient="records")
    return cache['forecasts']

@app.get("/chatgpt_forecast_live_singular")
def chatgpt_forecast_live_singular(model='gpt-3.5-turbo'):
    '''
    Ask the LLM to forecast for a single forecast time.
    '''
    global cache
    try :
        result = chatgpt.chatgpt_reflection_forecast_concurrent(model=model)
    except Exception as e :
        result = e
    cache['forecasts'] = result
    print(result)
    return result

@app.get('/forecasts')
def forecasts():
    global cache
    return cache['forecasts']

if __name__ == "__main__":
    # Set ChatGPT password
    passwords = pd.read_csv(config.credentials_dir)
    os.environ["OPENAI_API_KEY"] = passwords[passwords['user'] == 'openai'].iloc[0]['pass']
    uvicorn.run("run:app", host="0.0.0.0", port=1337, reload=True)
