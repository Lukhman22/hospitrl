import uvicorn
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
    engine.__init__() 
    return {
        "observation": {
            "wards": engine.wards,
            "hospital_pressure": 0.5,
            "time_step": 0
        },
        "info": {}
    }
from fastapi import HTTPException

@app.post("/step")
def step(req: ActionRequest):
    try:
        # Attempt the logic shift
        wards, reward, term, press = engine.step(req.action)
        
        return {
            "observation": {
                "wards": wards, 
                "hospital_pressure": press, 
                "time_step": engine.time_step
            },
            "reward": reward,
            "terminated": term,
            "truncated": False,
            "info": {"task_score": reward, "pressure": press}
        }
        
    except KeyError as e:
        # Triggered if the Ward ID or Action format is wrong
        raise HTTPException(
            status_code=400,
            detail=f"Clinical Registry Error: Ward ID {e} not found in the hospital database. Action aborted."
        )
    except Exception as e:
        # Catch-all for any other simulation glitches
        raise HTTPException(
            status_code=500,
            detail="Hospital Systems Alert: An internal resource allocation error occurred. Please re-initialize the environment."
        )

# This is what the validator is looking for!


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()