from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List

from src.models.point import GeoJSON

class FlightStatusForecastResponse(BaseModel):
    timestamp: datetime
    uavmodel: str
    status: str
    weather_source: str
    location: GeoJSON
    weather_params: Dict[str, float]

class FlightForecastListResponse(BaseModel):
    forecasts: List[FlightStatusForecastResponse]
