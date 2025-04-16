from typing import List, Optional

from pydantic import Field
from src.ocsm.base import Observation, Result


class THIResult(Result):
    hasValue: float
    unit: Optional[str] = None


class THIObservation(Observation):
    type: List[str] = Field(["Observation", "THI"], alias="@type")
    hasResult: THIResult

