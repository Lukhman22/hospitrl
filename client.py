import requests
import json

ENV_URL = "http://localhost:7860"

with open("scenario_config.json") as f:
    scenario = json.load(f)

# RESET
resp = requests.post(f"{ENV_URL}/reset")
obs = resp.json()["observation"]

steps = 0

while steps < scenario["evaluation_rules"]["max_steps"]:
    steps += 1

    # simple heuristic
    wards = obs["wards"]
    src = max(wards, key=wards.get)
    tgt = "Emergency Room" if src != "Emergency Room" else "Intensive Care"

    action = {
        "source_ward": src,
        "target_ward": tgt,
        "staff_count": 10
    }

    resp = requests.post(f"{ENV_URL}/step", json=action)
    result = resp.json()

    obs = result["observation"]

    print(f"Step {steps} → Pressure: {obs['pressure']}")

    if obs["pressure"] < scenario["evaluation_rules"]["target_pressure"]:
        print("SUCCESS")
        break