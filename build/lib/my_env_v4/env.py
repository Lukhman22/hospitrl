import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .logic import HospitalEngine
from .models import Observation, WardStatus

class HospitRL_Env(gym.Env):
    def __init__(self, task_type='hosp_basic'):
        super().__init__()
        self.engine = HospitalEngine()
        self.max_steps = 24
        self.current_step = 0
        self.action_space = spaces.Dict({
            'source_ward': spaces.Discrete(3),
            'target_ward': spaces.Discrete(3),
            'staff_count': spaces.Discrete(5)
        })

    def reset(self, seed=None, options=None):
        self.engine = HospitalEngine()
        self.current_step = 0
        return self._get_obs(), {}

    def _get_obs(self):
        wards = [WardStatus(name=w, patient_count=self.engine.patient_counts[w],
                            staff_count=self.engine.staff_assigned[w],
                            fatigue=self.engine.staff_fatigue[w]) for w in self.engine.wards]
        return {"wards": [w.dict() for w in wards], "hospital_pressure": 0.5, "time_step": self.current_step}

    def step(self, action):
        self.current_step += 1
        wards_list = ['ICU', 'ER', 'General']
        self.engine.move_staff(wards_list[action['source_ward']], 
                               wards_list[action['target_ward']], 
                               action['staff_count'])
        self.engine.update_state()
        
        reward = 1.0 # Simple reward for survival
        done = self.current_step >= self.max_steps
        return self._get_obs(), reward, done, False, {}