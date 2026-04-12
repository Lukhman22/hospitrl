from pydantic import BaseModel
from typing import Dict, List, Optional

class Action(BaseModel):
    source_ward: int  # 0: ICU, 1: ER, 2: General
    target_ward: int
    staff_count: int

class WardStatus(BaseModel):
    name: str
    patient_count: int
    staff_count: int
    fatigue: float

class Observation(BaseModel):
    wards: List[WardStatus]
    hospital_pressure: float
    time_step: int

class Reward(BaseModel):
    value: float
    done: bool
    info: Dict