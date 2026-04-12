import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from my_env_v4.env import HospitRL_Env

app = FastAPI()
env = HospitRL_Env()

class ActionReq(BaseModel):
    action: dict

@app.get("/health")
async def health(): return {"status": "healthy"}

@app.post("/reset")
async def reset():
    obs, info = env.reset()
    return {"observation": obs, "info": info}

@app.post("/step")
async def step(req: ActionReq):
    obs, reward, done, _, info = env.step(req.action)
    return {"observation": obs, "reward": reward, "done": done, "info": info}

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()