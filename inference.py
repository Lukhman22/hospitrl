"""
HospitRL Inference Script — Staff Scheduling 
"""

import os
import json
import time
import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL = os.getenv("ENVIRONMENT_URL", "http://localhost:7860")

BENCHMARK = "hospitrl"
MAX_STEPS = 8

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

TASKS = ["easy_balance", "medium_surge", "hard_optimization"]


# ---------------- SAFE CLAMP ---------------- #
def safe(v: float) -> float:
    return float(max(0.0001, min(0.9999, v)))


def _bool(v: bool) -> str:
    return "true" if v else "false"


# ---------------- HEURISTIC ENGINE ---------------- #
def heuristic_action(obs):
    wards = obs["wards"]
    pressure = obs["pressure"]

    # Sort wards by staff count
    sorted_wards = sorted(wards.items(), key=lambda x: x[1], reverse=True)

    src = sorted_wards[0][0]

    # Always prioritize ER, then ICU
    if src != "Emergency Room":
        tgt = "Emergency Room"
    else:
        tgt = "Intensive Care"

    # Dynamic movement size
    if pressure > 80:
        qty = 20
    elif pressure > 60:
        qty = 15
    else:
        qty = 8

    qty = min(qty, wards[src])

    return {
        "source_ward": src,
        "target_ward": tgt,
        "staff_count": max(1, qty)
    }


# ---------------- LLM PROMPT ---------------- #
def build_prompt(obs, task_id):
    return (
        f"You are optimizing hospital staffing.\n"
        f"Task: {task_id}\n\n"
        f"Wards: {obs['wards']}\n"
        f"Pressure: {obs['pressure']} (reduce aggressively)\n"
        f"Burnout: {obs['burnout_index']}\n"
        f"Budget: {obs['remaining_budget']}\n\n"
        "Return ONLY JSON:\n"
        '{"source_ward":"General Ward","target_ward":"Emergency Room","staff_count":10}'
    )


# ---------------- VALIDATION ---------------- #
def validate_action(action, obs):
    wards = obs["wards"]

    if not isinstance(action, dict):
        return False

    if "source_ward" not in action or "target_ward" not in action:
        return False

    if action["source_ward"] not in wards:
        return False

    if action["target_ward"] not in wards:
        return False

    if action["source_ward"] == action["target_ward"]:
        return False

    if action.get("staff_count", 0) <= 0:
        return False

    return True


# ---------------- TASK LOOP ---------------- #
def run_task(task_id):
    rewards = []
    steps_taken = 0
    success = False

    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    try:
        resp = requests.post(f"{ENV_URL}/reset", params={"task_id": task_id}, timeout=30)
        obs = resp.json()["observation"]

        for step in range(1, MAX_STEPS + 1):
            steps_taken = step
            error = None

            heuristic = heuristic_action(obs)

            # Try LLM
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "Respond ONLY with JSON."},
                        {"role": "user", "content": build_prompt(obs, task_id)},
                    ],
                    temperature=0.2,
                    max_tokens=100,
                )

                raw = completion.choices[0].message.content.strip()

                if raw.startswith("```"):
                    raw = raw.split("```")[1]

                llm_action = json.loads(raw)

                # 🔥 HYBRID DECISION
                if validate_action(llm_action, obs):
                    action = llm_action
                else:
                    action = heuristic

            except Exception as e:
                action = heuristic
                error = f"llm_error:{e}"

            action_str = json.dumps(action)

            # STEP
            try:
                resp = requests.post(f"{ENV_URL}/step", json=action, timeout=30)
                result = resp.json()

                obs = result["observation"]
                reward = safe(float(result["reward"]))
                done = bool(result["terminated"])

                if result.get("info", {}).get("error"):
                    error = result["info"]["error"]

            except Exception as e:
                reward = safe(0.05)
                done = True
                error = str(e)

            rewards.append(reward)

            print(
                f"[STEP] step={step} action={action_str} "
                f"reward={reward:.2f} done={_bool(done)} error={error if error else 'null'}",
                flush=True,
            )

            if done:
                success = obs.get("pressure", 100) < 30
                break

            time.sleep(0.05)

    except Exception:
        fallback = safe(0.05)
        print(f"[END] success=false steps=1 rewards={fallback:.2f}", flush=True)
        return

    # FINAL SCORE
    if rewards:
        mean_reward = sum(rewards) / len(rewards)
    else:
        mean_reward = 0.05

    if obs.get("pressure", 100) < 30:
        mean_reward *= 1.15

    score = safe(mean_reward)

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(
        f"[END] success={_bool(success)} steps={steps_taken} rewards={rewards_str}",
        flush=True,
    )


if __name__ == "__main__":
    for task in TASKS:
        run_task(task)
        time.sleep(1)