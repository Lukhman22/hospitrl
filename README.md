---
title: HospitRL
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# HospitRL: AI-Driven Hospital Resource Allocation

**Developed for the Scaler OpenEnv Hackathon** **Team:** Mohammed Lukhmaan, Iyaad, and Hamdaan

HospitRL is a high-fidelity Reinforcement Learning (RL) environment designed to simulate real-world hospital ward management. The environment challenges AI agents to dynamic resource allocation tasks, balancing patient safety, staff fatigue, and sudden emergency surges.

---

## 🚀 Project Overview

In a modern healthcare setting, staff distribution is often reactive rather than proactive. **HospitRL** provides a "Gymnasium-style" environment where an agent must manage three critical wards:
* **ICU (Intensive Care Unit):** High-stakes, high-sensitivity ward.
* **ER (Emergency Room):** The primary entry point for patient surges.
* **General Ward:** The high-capacity buffer zone.

The core objective is to minimize **Hospital Pressure** by moving staff members between wards to meet fluctuating patient demands.

---

## 🧠 Core Mechanics

### 1. The Surge Logic (Novel Feature)
Unlike static environments, HospitRL simulates **non-stationary dynamics**. Every 10 steps, the environment triggers a "Crisis Event," introducing a massive influx of 15–25 patients into the ER. Agents must learn to redistribute staff *before* the surge hits to avoid system collapse.

### 2. Staff Fatigue & Burnout
Staff efficiency is not infinite. We modeled a **Fatigue Metric**:
* If a ward is understaffed (high patient-to-staff ratio), fatigue increases.
* High fatigue levels act as a penalty to the overall hospital performance, simulating the real-world impact of healthcare burnout.

### 3. Scoring & Reward Function
The reward is tied directly to the **Operational Pressure ($P$)**:
$$Reward = 1.0 - P$$
Where $P$ is a normalized value ($0.0$ to $1.0$) representing the ratio of patients to the hospital's current staffing capacity.

---

## 🛠 Tech Stack

* **Logic:** Python 3.10+ / Gymnasium
* **API Framework:** FastAPI (Uvicorn)
* **Deployment:** Docker (Containerized for reproducibility)
* **Hosting:** Hugging Face Spaces
* **LLM Integration:** OpenAI Client (OpenEnv Compliant)

---

## 📊 Task Curriculum

We have defined three distinct tasks in `openenv.yaml` to evaluate agent performance:

| Task ID | Name | Difficulty | Objective |
| :--- | :--- | :--- | :--- |
| `stable_wards` | Quiet Shift | Easy | Maintain low pressure during normal operations. |
| `midday_rush` | Midday Rush | Medium | Handle steady arrivals without increasing fatigue. |
| `emergency_surge`| Crisis Management | Hard | Survive the Step 10 surge without exceeding 0.9 pressure. |

---

## 💻 Technical Setup & Compliance

### Environment Endpoints
* `GET /health`: System heartbeat.
* `POST /reset`: Initializes the hospital state.
* `POST /step`: Executes a staff movement action.

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the local server
uvicorn server.app:app --host 0.0.0.0 --port 7860