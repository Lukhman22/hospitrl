import os
import json
import requests
import time
from openai import OpenAI

# 1. Scaler Mandatory Environment Variables
API_BASE_URL = os.environ.get("API_BASE_URL")
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4") 
ENV_URL = os.environ.get("ENVIRONMENT_URL", "http://localhost:7860")

# 2. Initialize Client
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def run_task(task_id):
    """
    Evaluates the hospital environment using the Hospital Coordinator Brain 
    while enforcing the strict (0, 1) score range.
    """
    # [START] Mandatory Log Tag
    print(f"[START] Task: {task_id}")
    
    try:
        # Reset the environment for the specific task
        reset_resp = requests.post(f"{ENV_URL}/reset?task_id={task_id}", timeout=10)
        obs = reset_resp.json()["observation"]
        
        total_reward = 0
        step_count = 0
        
        # Hospital Management Loop (Max 10 steps)
        for i in range(1, 11):
            step_count += 1
            
            # --- THE CLINICAL BRAIN (Logic from earlier version) ---
            system_instruction = (
                "You are the HospitRL AI Medical Coordinator. Your goal is to reduce Hospital Pressure to 0%.\n"
                "RULES:\n"
                "1. You manage 100 total staff across: General Ward, Emergency Room, Intensive Care.\n"
                "2. Moving staff TO the 'Emergency Room' or 'Intensive Care' reduces pressure most effectively.\n"
                "3. You must maintain the 100-staff total balance.\n"
                "4. Output MUST be a single JSON object."
            )
            
            user_input = f"CURRENT STATE: Pressure {obs['pressure']}%, Wards {obs['wards']}. Identify move."

            # Mandatory Proxy Call
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_input}
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
            print(f"[STEP] {json.dumps({'step': i, 'action': action, 'reward': reward, 'pressure': obs['pressure']})}")
            
            if step_resp["terminated"]:
                break
                
            time.sleep(0.1) # Stability delay

        # --- THE HARD-CLIPPED SCORING (The Shield) ---
        # 1. Calculate the average reward
        avg_reward = total_reward / step_count
        
        # 2. Apply Hard Clipping to force the score strictly into the (0, 1) interval
        # Formula: 0.0001 + (avg_reward * 0.9998)
        # Result: If raw is 0.0 -> 0.0001 | If raw is 1.0 -> 0.9999
        final_score = 0.0001 + (avg_reward * 0.9998)
        final_score = round(float(final_score), 4)

        # [END] Mandatory Log Tag
        print(f"[END] Task: {task_id} | Final Score: {final_score}")

    except Exception as e:
        # Emergency fallback score strictly within (0, 1)
        print(f"[ERROR] Task {task_id} failed: {e}")
        print(f"[END] Task: {task_id} | Final Score: 0.0001")

if __name__ == "__main__":
    # Ensure tasks match your openenv.yaml and app.py logic
    tasks = ["easy_balance", "medium_surge", "hard_optimization"]
    for t in tasks:
        run_task(t)