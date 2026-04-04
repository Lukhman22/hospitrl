import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional, Union, List, Tuple, Dict

from .logic import HospitalEngine, Ward
from .models import Observation, Action, WardState

class HospitRL_Env(gym.Env):
    metadata = {"render_modes": ["human"], "version": "0.1.0"}

    def __init__(self):
        super().__init__()
        
        self.action_space = spaces.Dict({
            "source_ward": spaces.Discrete(3),
            "target_ward": spaces.Discrete(3),
            "staff_count": spaces.Discrete(10)
        })

        self.observation_space = spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        
        self.engine = HospitalEngine()
        self.current_step = 0
        self.max_steps = 50

    def _get_obs(self) -> Observation:
        wards_data = []
        for name, ward in self.engine.wards.items():
            wards_data.append(WardState(
                name=name,
                patient_count=ward.patient_count,
                staff_count=ward.staff_count,
                fatigue=ward.fatigue
            ))
        
        return Observation(
            wards=wards_data,
            hospital_pressure=self.engine.hospital_pressure,
            time_step=self.current_step
        )

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[Observation, dict]:
        super().reset(seed=seed)
        
        self.engine = HospitalEngine()
        self.current_step = 0
        
        observation = self._get_obs()
        return observation, {}

    def get_task_score(self) -> float:
        score = 1.0 - self.engine.hospital_pressure
        return max(0.0, min(1.0, float(score)))

    def step(self, action: Union[Action, Dict]) -> Tuple[Observation, float, bool, bool, dict]:
        if isinstance(action, dict):
            src_idx = action.get("source_ward", 0)
            tgt_idx = action.get("target_ward", 0)
            count = action.get("staff_count", 0)
        else:
            src_idx = action.source_ward
            tgt_idx = action.target_ward
            count = action.staff_count

        ward_names = list(self.engine.wards.keys())
        source_name = ward_names[src_idx]
        target_name = ward_names[tgt_idx]
        
        self.engine.move_staff(source_name, target_name, count)
        self.engine.update()
        
        self.current_step += 1
        
        reward = 1.0 - self.engine.hospital_pressure
        
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        if self.engine.hospital_pressure > 0.9:
            terminated = True
            reward = -1.0

        obs = self._get_obs()
        info = {
            "task_score": self.get_task_score(),
            "pressure": self.engine.hospital_pressure
        }
        
        return obs, float(reward), terminated, truncated, info

    def render(self):
        print(f"Step: {self.current_step} | Pressure: {self.engine.hospital_pressure:.2f}")

    def state(self) -> dict:
        return self._get_obs().model_dump()