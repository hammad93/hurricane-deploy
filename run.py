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

app = FastAPI()

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
def chatgpt_forecast_storm_live():
    '''
    '''
    global cache
    try:
        forecast = chatgpt.chatgpt_forecast_live(model_version='gpt-4')
    except Exception as e:
        return str(e)
    forecast = pd.concat(forecast)
    cache['chatgpt'] = forecast.to_dict(orient="records")
    return cache['chatgpt']

@app.get("/chatgpt_forecast_live_singular")
def chatgpt_forecast_live_singular():
    '''
    Ask the LLM to forecast for a single forecast time.
    '''
    global cache
    try :
        result = chatgpt.chatgpt_reflection_forecast_concurrent(model='gpt-4)
    except Exception as e :
        result = e
    cache['chatgpt'] = result
    print(result)
    return result

@app.get('/forecasts')
def forecasts():
    global cache
    return cache['chatgpt']

if __name__ == "__main__":
    # Set ChatGPT password
    passwords = pd.read_csv(config.credentials_dir)
    os.environ["OPENAI_API_KEY"] = passwords[passwords['user'] == 'openai'].iloc[0]['pass']
    uvicorn.run("run:app", host="0.0.0.0", port=1337, reload=True)
