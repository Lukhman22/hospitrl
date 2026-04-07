from pydantic import BaseModel, Field
from typing import Dict

class Action(BaseModel):
    source_ward: str = Field(..., description="The ward to take staff from")
    target_ward: str = Field(..., description="The ward to send staff to")
    staff_count: int = Field(..., description="Number of staff members to move")

class Observation(BaseModel):
    wards: Dict[str, int] = Field(..., description="Current staff distribution")
    pressure: float = Field(..., description="Current hospital stress level 0-100")
    task_id: str = Field(..., description="The identifier for the current scenario")

class State(BaseModel):
    observation: Observation
    steps_taken: int