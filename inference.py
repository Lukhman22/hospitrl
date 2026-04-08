import os, json, requests, time
from openai import OpenAI

API_BASE_URL = os.environ.get("API_BASE_URL")
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4") 
ENV_URL = os.environ.get("ENVIRONMENT_URL", "http://localhost:7860")

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

def run_task(task_id):
    print(f"[START] Task: {task_id}")
    try:
        obs = requests.post(f"{ENV_URL}/reset?task_id={task_id}", timeout=10).json()["observation"]
        total_reward = 0
        
        for i in range(1, 11):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": "You are a Hospital AI. Balance staff to reduce pressure. Respond ONLY with JSON: {'source_ward': str, 'target_ward': str, 'staff_count': int}"},
                          {"role": "user", "content": f"State: {obs}"}],
                response_format={"type": "json_object"}
            )
            action = json.loads(response.choices[0].message.content)
            
            step_resp = requests.post(f"{ENV_URL}/step", json=action, timeout=10).json()
            obs = step_resp["observation"]
            reward = step_resp["reward"]
            total_reward = reward # The Rubric is cumulative inside the app

            print(f"[STEP] {json.dumps({'step': i, 'reward': reward, 'pressure': obs['pressure']})}")
            if step_resp["terminated"]: break
            time.sleep(0.2)

        # FINAL SQUASHING: Strictly (0, 1)
        # We take the final step's reward and ensure it is capped.
        final_score = max(0.0001, min(0.9999, total_reward))
        print(f"[END] Task: {task_id} | Final Score: {round(final_score, 4)}")

    except Exception as e:
        print(f"[END] Task: {task_id} | Final Score: 0.0001")

if __name__ == "__main__":
    for t in ["easy_balance", "medium_surge", "hard_optimization"]:
        run_task(t)