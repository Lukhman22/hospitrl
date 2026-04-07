import os
import json
import requests
import time
from openai import OpenAI

# 1. Mandatory Scaler Environment Variables
API_BASE_URL = os.environ.get("API_BASE_URL")
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4") 
ENV_URL = os.environ.get("ENVIRONMENT_URL", "http://localhost:7860")

# 2. Initialize the OpenAI Client per Spec
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def run_task(task_id):
    """
    Runs evaluation for a specific hospital task with buffered scoring.
    """
    # [START] Mandatory Log Tag
    print(f"[START] Task: {task_id}")
    
    try:
        # Initial Reset
        reset_resp = requests.post(f"{ENV_URL}/reset?task_id={task_id}", timeout=10)
        obs = reset_resp.json()["observation"]
        
        total_reward = 0
        step_count = 0
        
        # Standard evaluation loop (Max 10 steps)
        for i in range(1, 11):
            step_count += 1
            
            # --- THE LLM PROXY CALL ---
            system_instruction = (
                "You are the HospitRL AI Coordinator. Manage 100 staff to reduce pressure.\n"
                "Prioritize Emergency Room and Intensive Care for max reduction.\n"
                "Output ONLY a JSON object with: source_ward, target_ward, staff_count."
            )
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Current State: {obs}"}
                ],
                response_format={"type": "json_object"}
            )
            
            action = json.loads(response.choices[0].message.content)
            
            # --- THE ENVIRONMENT STEP ---
            step_resp = requests.post(f"{ENV_URL}/step", json=action, timeout=10).json()
            
            obs = step_resp["observation"]
            reward = step_resp["reward"]
            total_reward += reward

            # [STEP] Mandatory Log Tag
            log_data = {
                "step": i,
                "action": action,
                "reward": reward,
                "pressure": obs["pressure"]
            }
            print(f"[STEP] {json.dumps(log_data)}")
            
            if step_resp["terminated"]:
                break
                
            time.sleep(0.2) # Small delay for stability

        # --- THE (0, 1) BUFFERED SCORING LOGIC ---
        # We calculate the raw average reward (which is already 0.01 - 0.99 from app.py)
        avg_reward = total_reward / step_count
        
        # Safety Buffer: Ensure the final score is strictly 0.01 to 0.99
        # Formula: 0.01 + (avg_reward * 0.98) if we weren't already buffered, 
        # but since app.py is buffered, we just round to be safe.
        final_score = round(float(avg_reward), 4)
        
        # Double-check boundary protection
        if final_score >= 1.0: final_score = 0.9999
        if final_score <= 0.0: final_score = 0.0001

        # [END] Mandatory Log Tag
        print(f"[END] Task: {task_id} | Final Score: {final_score}")

    except Exception as e:
        # Emergency fallback score in the valid (0, 1) range
        print(f"[ERROR] Task {task_id} failed: {e}")
        print(f"[END] Task: {task_id} | Final Score: 0.0101")

if __name__ == "__main__":
    # Scenarios defined in openenv.yaml
    tasks = ["easy_balance", "medium_surge", "hard_optimization"]
    for t in tasks:
        run_task(t)