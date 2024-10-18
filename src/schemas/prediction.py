from datetime import datetime
from pydantic import BaseModel

from src.schemas.point import PointOut

class PredictionOut(BaseModel):
    value: float
    timestamp: datetime
    source: str
    spatial_entity: PointOut
    data_type: str
    measurement_type: str