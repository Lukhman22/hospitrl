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
        for i in range(1, 11):
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": "Hospital AI: Manage 100 staff to reduce pressure. Output JSON ONLY."},
                          {"role": "user", "content": f"State: {obs}"}],
                response_format={"type": "json_object"}
            )
            action = json.loads(response.choices[0].message.content)
            res = requests.post(f"{ENV_URL}/step", json=action, timeout=10).json()
            obs, rew = res["observation"], res["reward"]
            print(f"[STEP] {json.dumps({'step': i, 'reward': rew, 'pressure': obs['pressure']})}")
            if res["terminated"]: break
            time.sleep(0.1)
        final_score = max(0.0001, min(0.9999, rew))
        print(f"[END] Task: {task_id} | Final Score: {round(final_score, 4)}")
    except Exception as e:
        print(f"[END] Task: {task_id} | Final Score: 0.0001")

if __name__ == "__main__":
    for t in ["easy_balance", "medium_surge", "hard_optimization"]:
        run_task(t)