from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from src.models.point import GeoJSONTypeEnum, PointTypeEnum


class GeoJSONOut(BaseModel):
    type: GeoJSONTypeEnum
    coordinates: list


class PointOut(BaseModel):
    id: UUID
    title: Optional[str]
    type: PointTypeEnum
    location: GeoJSONOut