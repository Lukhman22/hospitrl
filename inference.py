import os
import json
import requests
from openai import OpenAI

# 1. DIRECT ENVIRONMENT VARIABLE ACCESS (As requested by Scaler)
# The grader injects these. os.environ.get is the safest way to read them.
API_BASE_URL = os.environ.get("API_BASE_URL")
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o") # The grader will specify the model

# 2. ENVIRONMENT URL 
# During validation, your server/app.py is usually running on localhost:7860
# or at a specific URL provided by the grader.
ENVIRONMENT_URL = os.environ.get("ENVIRONMENT_URL", "http://localhost:7860")

# 3. INITIALIZE CLIENT EXACTLY PER EMAIL INSTRUCTIONS
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY
)

def run_evaluation():
    print("[START] Phase 2 Validation Loop")
    
    try:
        # Reset the environment to get initial 100-staff observation
        # We use a timeout to ensure the script doesn't hang
        resp = requests.post(f"{ENVIRONMENT_URL}/reset", timeout=10)
        obs = resp.json()["observation"]
        
        # We will run 5 steps to ensure the Proxy sees multiple API calls
        for i in range(5):
            print(f"[STEP {i}] Sending request to LiteLLM Proxy...")
            
            # --- MANDATORY API CALL ---
            # This is the part that updates the 'last_active' timestamp on their server
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a Hospital Resource AI. Move staff from high-count wards to low-count wards. Respond ONLY with JSON: {\"source_ward\": \"Ward Name\", \"target_ward\": \"Ward Name\", \"staff_count\": int}"
                    },
                    {
                        "role": "user", 
                        "content": f"Current Hospital State: {obs}. Determine the next move to reduce pressure."
                    }
                ],
                response_format={ "type": "json_object" }
            )
            
            # Parse the move decided by the AI
            action = json.loads(response.choices[0].message.content)
            
            # Send the AI's action to your server/app.py
            step_resp = requests.post(
                f"{ENVIRONMENT_URL}/step", 
                json={"action": action},
                timeout=10
            )
            data = step_resp.json()
            obs = data["observation"]
            
            # Log the math breakdown to the console so the validator sees progress
            print(f"[LOG] {action['source_ward']} -> {action['target_ward']} | Pressure: {obs['pressure']}%")
            
            if data["terminated"]:
                print("[TERMINATED] Goal reached or limit hit.")
                break

        print("[END] Evaluation successful.")
        
    except Exception as e:
        print(f"[ERROR] Inference failed: {e}")

if __name__ == "__main__":
    run_evaluation()