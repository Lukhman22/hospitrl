"""
HospitRL Inference Script
=========================
Runs an LLM agent against all three HospitRL tasks and emits the mandatory
OpenEnv stdout format:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

All scores are strictly in (0, 1) — never 0.0 or 1.0.
"""
import os
import json
import time
import requests
from openai import OpenAI

# --------------------------------------------------------------------------- #
# Config — read from environment variables
# --------------------------------------------------------------------------- #
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL      = os.getenv("ENVIRONMENT_URL", "http://localhost:7860")
BENCHMARK    = "hospitrl"
MAX_STEPS    = 8

client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

TASKS = ["easy_balance", "medium_surge", "hard_optimization"]


def _squash(v: float) -> float:
    """Strictly clamp to open interval (0, 1)."""
    return round(float(max(0.0001, min(0.9999, v))), 4)


def _bool(v: bool) -> str:
    return "true" if v else "false"


def build_prompt(obs: dict, task_id: str) -> str:
    return (
        f"You are a hospital resource manager. Task: {task_id}.\n"
        f"Current state:\n"
        f"  Wards (staff counts): {obs['wards']}\n"
        f"  Pressure: {obs['pressure']}% (reduce this — target <30%)\n"
        f"  Burnout: {obs['burnout_index']}%\n"
        f"  Budget: ${obs['remaining_budget']}\n\n"
        "Choose one staff reallocation to reduce pressure. "
        "Move staff FROM an over-staffed ward TO Emergency Room or Intensive Care.\n"
        "Respond ONLY with valid JSON (no markdown, no explanation):\n"
        '{"source_ward": "<ward>", "target_ward": "<ward>", "staff_count": <integer 1-20>}\n'
        "Valid wards: General Ward, Emergency Room, Intensive Care"
    )


def run_task(task_id: str):
    step_rewards = []
    steps_taken = 0
    success = False
    last_error = None

    # [START]
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    try:
        # Reset environment
        resp = requests.post(f"{ENV_URL}/reset", params={"task_id": task_id}, timeout=30)
        resp.raise_for_status()
        obs = resp.json()["observation"]

        for step_num in range(1, MAX_STEPS + 1):
            steps_taken = step_num
            last_error = None

            # Ask LLM for action
            try:
                chat = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are a hospital resource optimization AI. Respond only with JSON."},
                        {"role": "user", "content": build_prompt(obs, task_id)},
                    ],
                    max_tokens=100,
                    temperature=0.3,
                )
                raw = chat.choices[0].message.content.strip()
                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                action = json.loads(raw.strip())
                action_str = json.dumps(action)
            except Exception as e:
                # Fallback: move 10 staff from General Ward to Emergency Room
                action = {"source_ward": "General Ward", "target_ward": "Emergency Room", "staff_count": 10}
                action_str = json.dumps(action)
                last_error = f"LLM parse error: {e}"

            # Execute step
            try:
                step_resp = requests.post(f"{ENV_URL}/step", json=action, timeout=30)
                step_resp.raise_for_status()
                result = step_resp.json()
                obs = result["observation"]
                raw_reward = float(result["reward"])
                reward = _squash(raw_reward)
                done = bool(result["terminated"])
                step_error = result.get("info", {}).get("error") or last_error
            except Exception as e:
                reward = _squash(0.05)
                done = True
                step_error = str(e)

            step_rewards.append(reward)

            # [STEP]
            error_str = step_error if step_error else "null"
            print(
                f"[STEP] step={step_num} action={action_str} "
                f"reward={reward:.2f} done={_bool(done)} error={error_str}",
                flush=True,
            )

            if done:
                # Success: pressure dropped enough
                pressure = obs.get("pressure", 100)
                success = pressure < 30.0
                break

            time.sleep(0.1)

    except Exception as e:
        # Catastrophic failure — emit a safe fallback [END]
        safe_score = _squash(0.05)
        rewards_str = ",".join(f"{safe_score:.2f}" for _ in range(max(1, steps_taken)))
        print(
            f"[END] success=false steps={max(1, steps_taken)} score={safe_score:.2f} "
            f"rewards={rewards_str}",
            flush=True,
        )
        return

    # Final score: mean of step rewards, strictly (0, 1)
    if step_rewards:
        mean_reward = sum(step_rewards) / len(step_rewards)
        # Boost score if task succeeded (pressure < 30%)
        pressure = obs.get("pressure", 100)
        if pressure < 30.0:
            mean_reward = _squash(mean_reward * 1.2)
        score = _squash(mean_reward)
    else:
        score = _squash(0.05)

    rewards_str = ",".join(f"{r:.2f}" for r in step_rewards) if step_rewards else f"{score:.2f}"

    # [END]
    print(
        f"[END] success={_bool(success)} steps={steps_taken} score={score:.2f} "
        f"rewards={rewards_str}",
        flush=True,
    )


if __name__ == "__main__":
    for task in TASKS:
        run_task(task)
        time.sleep(1)