from typing import List, Optional

from pydantic import BaseModel, Field
from src.models.uav import FlightStatus
from src.ocsm.base import Observation, Result


class FlightConditionResult(Result):
    status: FlightStatus
    temperature: float
    precipitation: float
    windSpeed: float


class FlightConditionObservation(Observation):
    type: List[str] = Field(["Observation", "FlightCondition"], alias="@type")
    hasResult: FlightConditionResult


class UAVModel(BaseModel):
    id: str = Field(..., alias="@id")
    type: List[str] = Field(["Sensor", "UAVModel"], alias="@type")
    name: str
    model: str
    manufacturer: str
    min_operating_temp: float
    max_operating_temp: float
    max_wind_speed: float
    precipitation_tolerance: float
    notes: Optional[str] = None

