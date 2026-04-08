from pydantic import BaseModel, Field
from typing import Dict, Optional


class Action(BaseModel):
    source_ward: str = Field(..., description="Origin ward to move staff from")
    target_ward: str = Field(..., description="Destination ward to move staff to")
    staff_count: int = Field(..., ge=1, description="Number of staff to move")


class Observation(BaseModel):
    wards: Dict[str, int] = Field(..., description="Staff count per ward")
    pressure: float = Field(..., description="Hospital pressure 0–100 (lower is better)")
    burnout_index: float = Field(..., description="Staff burnout 0–100 (lower is better)")
    remaining_budget: float = Field(..., description="Budget remaining in dollars")
    task_id: str = Field(..., description="Active task identifier")


class StepResponse(BaseModel):
    observation: Observation
    reward: float = Field(..., description="Step reward strictly in (0, 1)")
    terminated: bool
    info: dict


class ResetResponse(BaseModel):
    observation: Observation