from fastapi import FastAPI
from pydantic import BaseModel
from my_env_v4.logic import HospitalEngine

app = FastAPI()
engine = HospitalEngine()

class ActionRequest(BaseModel):
    action: dict

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/reset")
def reset():
    engine.__init__() # Reset to starting values
    return {
        "observation": {
            "wards": engine.wards,
            "hospital_pressure": 0.5,
            "time_step": 0
        },
        "info": {}
    }

@app.post("/step")
def step(req: ActionRequest):
    wards, reward, term, press = engine.step(req.action)
    return {
        "observation": {"wards": wards, "hospital_pressure": press, "time_step": engine.time_step},
        "reward": reward,
        "terminated": term,
        "truncated": False,
        "info": {"task_score": reward, "pressure": press}
    }