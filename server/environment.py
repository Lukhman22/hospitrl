"""
HospitRL Core Environment
Implements the hospital ward management simulation.
"""
import random
from typing import Dict, Tuple, Any

# --- FIXED IMPORT ---
from .models import Action, Observation


def _squash(v: float) -> float:
    """Strictly clamp reward to open interval (0, 1) — never 0.0 or 1.0."""
    return float(round(max(0.0001, min(0.9999, v)), 4))


TASK_CONFIGS = {
    "easy_balance": {
        "wards": {"General Ward": 80, "Emergency Room": 10, "Intensive Care": 10},
        "pressure": 65.0,
        "burnout": 10.0,
        "budget": 5000.0,
        "max_steps": 10,
        "surge_at": None,
        "description": "Redistribute staff to bring pressure below 30%.",
    },
    "medium_surge": {
        "wards": {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25},
        "pressure": 85.0,
        "burnout": 20.0,
        "budget": 4000.0,
        "max_steps": 12,
        "surge_at": 6,  # patient surge at step 6
        "description": "Manage a midday patient surge without exceeding budget.",
    },
    "hard_optimization": {
        "wards": {"General Ward": 40, "Emergency Room": 30, "Intensive Care": 30},
        "pressure": 95.0,
        "burnout": 35.0,
        "budget": 3000.0,
        "max_steps": 15,
        "surge_at": 5,  # earlier surge + higher starting pressure
        "description": "Survive crisis surge while keeping burnout under 70% and budget above 500.",
    },
}

VALID_WARDS = {"General Ward", "Emergency Room", "Intensive Care"}


class HospitalEnv:
    def __init__(self):
        self._task_id = "easy_balance"
        self._wards: Dict[str, int] = {}
        self._pressure = 0.0
        self._burnout = 0.0
        self._budget = 0.0
        self._steps = 0
        self._max_steps = 10
        self._surge_at = None
        self._surged = False
        self._step_rewards: list = []
        self._last_error: str = ""
        self.reset("easy_balance")

    def reset(self, task_id: str = "easy_balance") -> Observation:
        if task_id not in TASK_CONFIGS:
            task_id = "easy_balance"
        cfg = TASK_CONFIGS[task_id]
        self._task_id = task_id
        self._wards = dict(cfg["wards"])
        self._pressure = float(cfg["pressure"])
        self._burnout = float(cfg["burnout"])
        self._budget = float(cfg["budget"])
        self._max_steps = cfg["max_steps"]
        self._surge_at = cfg["surge_at"]
        self._surged = False
        self._steps = 0
        self._step_rewards = []
        self._last_error = ""
        return self._make_obs()

    def state(self) -> dict:
        return {
            "task_id": self._task_id,
            "wards": dict(self._wards),
            "pressure": round(self._pressure, 2),
            "burnout_index": round(self._burnout, 2),
            "remaining_budget": round(self._budget, 2),
            "steps": self._steps,
            "max_steps": self._max_steps,
            "surged": self._surged,
        }

    def step(self, action: Action) -> Tuple[Observation, float, bool, dict]:
        self._steps += 1
        self._last_error = ""
        src = action.source_ward
        tgt = action.target_ward
        qty = max(0, int(action.staff_count))

        # Inject surge event
        if self._surge_at and self._steps == self._surge_at and not self._surged:
            surge = random.randint(15, 25)
            self._pressure = min(100.0, self._pressure + surge)
            self._burnout = min(100.0, self._burnout + 10.0)
            self._surged = True

        # Validate and apply action
        move_cost = qty * 50.0
        if src not in VALID_WARDS or tgt not in VALID_WARDS:
            self._last_error = f"Invalid ward name: '{src}' or '{tgt}'"
        elif src == tgt:
            self._last_error = "Source and target ward must differ"
        elif qty <= 0:
            self._last_error = "staff_count must be > 0"
        elif self._wards.get(src, 0) < qty:
            self._last_error = f"Insufficient staff in {src} (have {self._wards.get(src,0)}, need {qty})"
        elif self._budget < move_cost:
            self._last_error = f"Budget too low (need ${move_cost:.0f}, have ${self._budget:.0f})"
        else:
            self._wards[src] -= qty
            self._wards[tgt] += qty
            self._budget -= move_cost

            # Clinical pressure reduction
            if tgt in ("Emergency Room", "Intensive Care"):
                relief = qty * 3.5
            else:
                relief = qty * 1.0
            self._pressure = max(0.0, self._pressure - relief)
            # Burnout creep from overloading staff
            self._burnout = min(100.0, self._burnout + qty * 0.4)

        # Pressure naturally rises each step (patients keep arriving)
        self._pressure = min(100.0, self._pressure + 2.5)

        # Reward: weighted composite, strictly (0, 1)
        s_safety   = (100.0 - self._pressure) / 100.0          # pressure down = good
        s_budget   = self._budget / TASK_CONFIGS[self._task_id]["budget"]  # spend less = good
        s_wellness = (100.0 - self._burnout) / 100.0            # burnout down = good
        s_progress = 1.0 - (self._steps / self._max_steps)      # earlier = good

        raw = (s_safety * 0.45) + (s_budget * 0.20) + (s_wellness * 0.20) + (s_progress * 0.15)
        reward = _squash(raw)
        self._step_rewards.append(reward)

        done = (
            self._pressure <= 5.0
            or self._steps >= self._max_steps
            or self._budget <= 0
        )

        info = {
            "error": self._last_error or None,
            "surged": self._surged,
            "pressure": round(self._pressure, 2),
            "steps": self._steps,
        }
        return self._make_obs(), reward, done, info

    def _make_obs(self) -> Observation:
        return Observation(
            wards=dict(self._wards),
            pressure=round(self._pressure, 2),
            burnout_index=round(self._burnout, 2),
            remaining_budget=round(self._budget, 2),
            task_id=self._task_id,
        )