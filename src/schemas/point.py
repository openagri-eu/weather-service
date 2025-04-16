from pydantic import BaseModel

from src.models.point import GeoJSONTypeEnum


class GeoJSONOut(BaseModel):
    type: GeoJSONTypeEnum
    coordinates: list


class PointOut(BaseModel):
    location: GeoJSONOut