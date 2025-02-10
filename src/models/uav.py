from datetime import datetime

from beanie import Document


class FlyStatus(Document):
    timestamp: datetime
    drone_model: str
    temperature: float
    wind_speed: float
    precipitation: float
    status: str  # OK, NOT OK, Marginally OK
    weather_source: str  # e.g., 'OpenWeather API'


class DroneModel(Document):
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
        name = "drone_models"