import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from my_env_v4.env import HospitRL_Env
from my_env_v4.models import Action

app = FastAPI(title="HospitRL API")
env = HospitRL_Env()

class StepRequest(BaseModel):
    action: Action

@app.post("/reset")
async def reset():
    obs, info = env.reset()
    return {"observation": obs, "info": info}

@app.post("/step")
async def step(req: StepRequest):
    try:
        obs, reward, terminated, truncated, info = env.step(req.action)
        return {
            "observation": obs,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()