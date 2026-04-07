import os
import json
import requests
from openai import OpenAI

# 1. Mandatory Variables for Proxy
API_BASE_URL = os.getenv("API_BASE_URL", "https://lukhman22-hospitrl.hf.space/v1")
API_KEY = os.getenv("API_KEY") # CRITICAL: Grader injects this
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4")
SPACE_URL = API_BASE_URL.replace("/v1", "")

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def run_evaluation():
    print("[START]")
    try:
        # Initial Reset
        resp = requests.post(f"{SPACE_URL}/reset")
        obs = resp.json()["observation"]
        
        for i in range(5):
            # MANDATORY TELEMETRY: This call registers your activity with the LiteLLM proxy
            chat = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{
                    "role": "user", 
                    "content": f"Wards: {obs['wards']}. Move 1 staff to help. Return JSON: {{\"source_ward\": \"Name\", \"target_ward\": \"Name\", \"staff_count\": 1}}"
                }],
                response_format={"type": "json_object"}
            )
            
            action = json.loads(chat.choices[0].message.content)
            
            # Step the environment
            step_resp = requests.post(f"{SPACE_URL}/step", json={"action": action})
            data = step_resp.json()
            
            print(f"[STEP] {i} | Action: {action} | Pressure: {data['observation']['pressure']}%")
            obs = data["observation"]
            
            if data["terminated"]: break
            
        print(f"[END] Final Pressure: {obs['pressure']}%")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_evaluation()