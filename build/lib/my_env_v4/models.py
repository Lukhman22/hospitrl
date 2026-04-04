from pydantic import BaseModel
from typing import List

class WardState(BaseModel):
    name: str
    patient_count: int
    staff_count: int
    fatigue: float

class Observation(BaseModel):
    wards: List[WardState]
    hospital_pressure: float
    time_step: int

class Action(BaseModel):
    source_ward: int
    target_ward: int
    staff_count: int