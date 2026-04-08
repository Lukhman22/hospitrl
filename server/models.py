from pydantic import BaseModel
from typing import Dict

class Action(BaseModel):
    source_ward: str
    target_ward: str
    staff_count: int

class Observation(BaseModel):
    wards: Dict[str, int]
    pressure: float
    task_id: str