import os
import json
import requests
import time
from openai import OpenAI

# 1. Mandatory Scaler Environment Variables
API_BASE_URL = os.environ.get("API_BASE_URL")
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4") # The "Brain"
ENV_URL = os.environ.get("ENVIRONMENT_URL", "http://localhost:7860")

# 2. Initialize the OpenAI Client per Spec
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def run_task(task_id):
    """
    Runs the full clinical evaluation for a specific hospital scenario.
    """
    # [START] Mandatory Log Tag
    print(f"[START] Task: {task_id}")
    
    try:
        # Initial Reset to get the starting 100-staff observation
        reset_resp = requests.post(f"{ENV_URL}/reset?task_id={task_id}", timeout=10)
        obs = reset_resp.json()["observation"]
        
        total_accumulated_reward = 0
        
        # We run up to 10 steps to give the AI time to stabilize the hospital
        for i in range(1, 11):
            # --- THE CLINICAL BRAIN (Prompt Engineering) ---
            # We explicitly tell the AI about the 100-staff total and the wards
            system_instruction = (
                "You are the HospitRL AI Medical Coordinator. Your goal is to reduce Hospital Pressure to 0%.\n"
                "RULES:\n"
                "1. You manage 100 total staff across: General Ward, Emergency Room, Intensive Care.\n"
                "2. Moving staff TO the 'Emergency Room' or 'Intensive Care' reduces pressure most effectively.\n"
                "3. You must maintain the 100-staff total balance.\n"
                "4. Output MUST be a single JSON object."
            )
            
            user_input = (
                f"CURRENT STATE:\n"
                f"- Task ID: {obs['task_id']}\n"
                f"- Hospital Pressure: {obs['pressure']}%\n"
                f"- Ward Distribution: {obs['wards']}\n\n"
                f"Identify the most critical ward and move staff from a stable ward to help."
            )

            # --- THE API CALL (LiteLLM Proxy) ---
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the AI's "Thought"
            action = json.loads(response.choices[0].message.content)
            
            # --- THE ENVIRONMENT STEP ---
            step_resp = requests.post(f"{ENV_URL}/step", json={"action": action}, timeout=10).json()
            
            obs = step_resp["observation"]
            reward = step_resp["reward"]
            total_accumulated_reward += reward

            # [STEP] Mandatory Log Tag (Grader parses this JSON)
            log_data = {
                "step": i,
                "action": action,
                "reward": reward,
                "pressure": obs["pressure"],
                "total_reward": total_accumulated_reward
            }
            print(f"[STEP] {json.dumps(log_data)}")
            
            # Termination Check (If pressure is low enough, we win)
            if step_resp["terminated"]:
                print(f"Goal Met: Hospital Stabilized at {obs['pressure']}% pressure.")
                break
                
            time.sleep(0.5) # Prevent rate-limiting

        # [END] Mandatory Log Tag
        # The score is typically normalized between 0.0 and 1.0
        final_score = max(0.0, min(1.0, total_accumulated_reward / 10))
        print(f"[END] Task: {task_id} | Final Score: {final_score}")

    except Exception as e:
        print(f"[ERROR] Task {task_id} failed: {e}")
        print(f"[END] Task: {task_id} | Final Score: 0.0")

if __name__ == "__main__":
    # Scaler requires 3 tasks: Easy, Medium, Hard
    tasks = ["easy_balance", "medium_surge", "hard_optimization"]
    for t in tasks:
        run_task(t)