from uuid import UUID
from pydantic import BaseModel

from src.schemas.point import PointOut


class WeatherDataOut(BaseModel):
    id: UUID
    spatial_entity: PointOut
    data: dict


class THIDataOut(BaseModel):
    id: UUID
    spatial_entity: PointOut
    thi: float
