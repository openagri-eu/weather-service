import logging
from typing import Optional, Union
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# Observation Related
class MadeBySensorSchema(BaseModel):
    name: str

### **Result Schema (Used for Numeric Values)**
class QuantityValueSchema(BaseModel):
    id: str = Field(..., alias="@id")
    type: str = Field(default="QuantityValue", alias="@type")
    unit: Optional[str] = None
    numericValue: Optional[float] = None
    hasValue: Optional[str] = None  # For flight forecast, e.g., "OK"


class ObservationSchema(BaseModel):
    id: Optional[str] = Field(..., alias="@id")
    type: str = Field(default="Observation", alias="@type")
    activityType: Union[str, dict]
    title: str
    details: str
    phenomenonTime: str
    madeBySensor: Optional[MadeBySensorSchema] = None
    hasResult: QuantityValueSchema
    observedProperty: str
