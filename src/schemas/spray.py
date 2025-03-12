from datetime import datetime
from typing import Dict

from pydantic import BaseModel

from src.models.point import GeoJSON
from src.models.spray import SprayStatus


class SprayForecastResponse(BaseModel):
    timestamp: datetime
    spray_conditions: SprayStatus
    weather_source: str
    location: GeoJSON
    detailed_status: Dict[str, str]
