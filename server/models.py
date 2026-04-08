from pydantic import BaseModel, Field
from typing import Dict

class Action(BaseModel):
    source_ward: str = Field(..., description="Source ward")
    target_ward: str = Field(..., description="Target ward")
    staff_count: int = Field(..., description="Count")

class Observation(BaseModel):
    wards: Dict[str, int]
    pressure: float
    task_id: str