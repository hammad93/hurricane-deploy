from typing import Union, List
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import db

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


class StormData(BaseModel):
    id: str = Field(..., description="Storm ID")
    time: str = Field(..., description="ISO8601 timestamp")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    wind_speed: int = Field(..., description="Maximum sustained wind speed in knots")

@app.get("/live-storms", response_model=List[StormData])
async def get_live_storms() -> List[StormData]:
    """
    Retrieve live tropical storm data.

    Returns:
        list: A list of dictionaries containing the current live tropical storms
              with keys: id, time, lat, lon, and int.
    """
    try:
        df = db.query("SELECT * FROM hurricane_live")
        storms = df.to_dict(orient="records")
        return storms
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while fetching storm data.")


if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=1337, reload=True)
