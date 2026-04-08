from pydantic import BaseModel, Field
from typing import Dict, List

class Action(BaseModel):
    source_ward: str = Field(..., description="Origin ward for staff reallocation")
    target_ward: str = Field(..., description="Destination ward for staff reallocation")
    staff_count: int = Field(..., description="Number of personnel to move")

class Observation(BaseModel):
    wards: Dict[str, int]
    pressure: float
    burnout_index: float
    remaining_budget: float
    task_id: str