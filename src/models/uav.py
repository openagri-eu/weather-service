from datetime import datetime
from enum import Enum
from typing import Dict

from beanie import Document

from src.models.point import GeoJSON


class FlightStatus(str, Enum):
    OK = "OK"
    NOT_OK = "NOT OK"
    MARGINALLY_OK = "Marginally OK"

class FlyStatus(Document):
    timestamp: datetime
    uav_model: str
    status: FlightStatus  # OK, NOT OK, Marginally OK
    weather_source: str
    location: GeoJSON
    weather_params: Dict[str, float]

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "timestamp": "2024-11-01T09:00:00+00:00",
                "uav_model": "DJI Mavic Air 2",
                "status": "good",
                "weather_source": "openweathermaps",
                "location": {
                    "type": "Point",
                    "coordinates": [66.33, 43.22]  # [lat, lon]
                },
                "weather_params": {
                    "temp": 13.39,
                    "pressure": 1014,
                    "humidity": 91,
                    "wind": 6,
                    "gusts": 6,
                    "precipitation": 0
                }
            }
        }

    class Settings:
        name = "fly_status"


class UAVModel(Document):
    model: str
    manufacturer: str
    min_operating_temp: float
    max_operating_temp: float
    max_wind_speed: float
    precipitation_tolerance: float
    notes: str | None = None

    class Config:
        use_enum_values = True

    class Settings:
        name = "uav_models"