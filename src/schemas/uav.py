from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel

from src.schemas.point import GeoJSONOut

class FlightStatusForecastResponse(BaseModel):
    timestamp: datetime
    uav_model: str
    status: str
    weather_source: str
    location: GeoJSONOut
    weather_params: Dict[str, float]

class FlightForecastListResponse(BaseModel):
    forecasts: List[FlightStatusForecastResponse]
