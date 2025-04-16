from datetime import datetime
from typing import Dict

from pydantic import BaseModel

from src.models.spray import SprayStatus
from src.schemas.point import GeoJSONOut


class SprayForecastResponse(BaseModel):
    timestamp: datetime
    spray_conditions: SprayStatus
    source: str
    location: GeoJSONOut
    detailed_status: Dict[str, str]
