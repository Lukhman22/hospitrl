import os
import json
import requests
from openai import OpenAI

# 1. Set the default to your Space's V1 endpoint
API_BASE_URL = os.getenv("API_BASE_URL", "https://lukhman22-hospitrl.hf.space/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4")
HF_TOKEN = os.getenv("HF_TOKEN")

SPACE_URL = API_BASE_URL.replace("/v1", "")

# 3. Initialize Client
client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

def run_evaluation():
    # [START] Mandatory Log Tag
    print(f"[START] Starting inference for task: emergency_surge")
    
    try:
        # 1. Reset Environment
        resp = requests.post(f"{SPACE_URL}/reset", json={})
        obs = resp.json()["observation"]
        
        # 2. Run Loop (Agent testing)
        for i in range(5):
            # Baseline move: Shift staff from General (2) to ER (1)
            action = {"source_ward": 2, "target_ward": 1, "staff_count": 1}
            
            step_resp = requests.post(f"{SPACE_URL}/step", json={"action": action})
            data = step_resp.json()
            
            # [STEP] Mandatory Log Tag (Must be JSON)
            log_payload = {
                "step": i,
                "action": action,
                "reward": data["reward"],
                "pressure": data["info"]["pressure"]
            }
            print(f"[STEP] {json.dumps(log_payload)}")
            
            if data["terminated"]:
                break

        # [END] Mandatory Log Tag
        print(f"[END] Inference complete. Final Reward: {data['reward']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_evaluation()