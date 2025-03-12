from datetime import datetime
from enum import Enum
from typing import Dict

from beanie import Document

from src.models.point import GeoJSON


class SprayStatus(str, Enum):
    OPTIMAL = "optimal"
    MARGINAL = "marginal"
    UNSUITABLE = "unsuitable"


class SprayForecast(Document):
    timestamp: datetime
    source: str
    location: GeoJSON
    spray_conditions: SprayStatus  # "optimal", "marginal", "unsuitable"
    detailed_status: Dict[str, str]  # Explanation for spray conditions

    class Settings:
        collection = "spray_forecasts"