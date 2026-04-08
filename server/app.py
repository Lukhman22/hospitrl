import gradio as gr
import pandas as pd
from fastapi import FastAPI, Query
from server.models import Action
import uvicorn

# CONSTANTS FOR SCALER COMPLIANCE
def squash(v): return float(max(0.0001, min(0.9999, v)))

class HospitalUltraEngine:
    def __init__(self):
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.burnout = 10.0
        self.budget = 5000.0
        self.steps = 0
        self.max_steps = 10
        self.history = []
        self.task_id = "easy_balance"

    def reset(self, task_id="easy_balance"):
        self.steps = 0
        self.task_id = task_id
        self.budget = 5000.0
        self.burnout = 15.0
        if task_id == "easy_balance":
            self.wards, self.pressure = {"General Ward": 80, "Emergency Room": 10, "Intensive Care": 10}, 70.0
        elif task_id == "medium_surge":
            self.wards, self.pressure = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}, 100.0
        else: # hard_optimization
            self.wards, self.pressure = {"General Ward": 40, "Emergency Room": 30, "Intensive Care": 30}, 100.0
        return self.get_obs()

    def get_obs(self):
        return {"wards": self.wards, "pressure": self.pressure, "burnout_index": self.burnout, 
                "remaining_budget": self.budget, "task_id": self.task_id}

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        
        # LOGIC: Reallocation Costs & Impacts
        move_cost = qty * 50  # Logistic overhead cost
        if src in self.wards and self.wards[src] >= qty and self.budget >= move_cost:
            self.wards[src] -= qty
            self.wards[tgt] += qty
            self.budget -= move_cost
            
            # Clinical Impact: ICU/ER moves reduce pressure but increase burnout
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 5.0
            self.pressure = max(0.0, self.pressure - impact)
            self.burnout = min(100.0, self.burnout + (qty * 0.5))
            msg = f"Operational Success: {qty} staff deployed to {tgt}."
        else:
            msg = "Operational Failure: Budget exceeded or insufficient staff."

        # SCALER RUBRIC (4-Part Score)
        # 1. Safety (Pressure) | 2. Logistics (Budget) | 3. Wellness (Burnout) | 4. SLA (Steps)
        s1 = (100 - self.pressure) / 100
        s2 = self.budget / 5000
        s3 = (100 - self.burnout) / 100
        s4 = (self.max_steps - self.steps) / self.max_steps
        
        reward = squash((s1 * 0.4) + (s2 * 0.2) + (s3 * 0.2) + (s4 * 0.2))
        done = self.pressure <= 5.0 or self.steps >= self.max_steps or self.budget <= 0
        
        self.history.insert(0, f"Step {self.steps}: {msg} | Reward: {reward:.4f}")
        return self.get_obs(), reward, done, {"info": msg}

engine = HospitalUltraEngine()
app = FastAPI()

@app.post("/reset")
def reset(task_id: str = Query("easy_balance")): return {"observation": engine.reset(task_id)}

@app.post("/step")
def step(action: Action):
    obs, rew, done, info = engine.step(action)
    return {"observation": obs, "reward": rew, "terminated": done, "info": info}

# --- PRO DASHBOARD UI ---
with gr.Blocks(theme=gr.themes.Default(primary_hue="cyan", secondary_hue="zinc")) as demo:
    gr.Markdown("# 🏥 **HospitRL: Global Clinical Command**")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Label("🚨 System Pressure", value=f"{engine.pressure}%")
            p_bar = gr.Slider(0, 100, value=100, label="Live Stress Gauge", interactive=False)
        with gr.Column(scale=1):
            gr.Label("💰 Operational Budget", value=f"${engine.budget}")
            b_bar = gr.Slider(0, 5000, value=5000, label="Budget Exhaustion", interactive=False)
        with gr.Column(scale=1):
            gr.Label("🔥 Staff Burnout", value=f"{engine.burnout}%")
            burn_bar = gr.Slider(0, 100, value=15, label="Burnout Index", interactive=False)

    with gr.Row():
        with gr.Column(scale=2):
            chart = gr.BarPlot(x="Ward", y="Staff", title="Real-Time Staff Distribution", y_lim=[0,100], height=300)
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Unified Grading Rubric")
            gr.Markdown("""| Metric | Weight | Value |
| :--- | :--- | :--- |
| **Patient Safety** | 40% | Stress Reduction |
| **Fiscal Responsibility** | 20% | Budget Retention |
| **Staff Wellness** | 20% | Burnout Prevention |
| **SLA Compliance** | 20% | Step Efficiency |""")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🕹️ Tactical Reallocation")
            src = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Source")
            tgt = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Target")
            qty = gr.Number(label="Personnel Count", value=10)
            btn = gr.Button("⚡ Commit Action", variant="primary")
        with gr.Column():
            gr.Markdown("### 📜 Command Audit Log")
            log = gr.Textbox(label="System Events", lines=6)

    def update(s, t, q):
        obs, rew, done, info = engine.step(Action(source_ward=s, target_ward=t, staff_count=q))
        df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
        return df, obs["pressure"], obs["remaining_budget"], obs["burnout_index"], "\n".join(engine.history)

    btn.click(update, [src, tgt, qty], [chart, p_bar, b_bar, burn_bar, log])

app = gr.mount_gradio_app(app, demo, path="/")
def main(): uvicorn.run(app, host="0.0.0.0", port=7860)
if __name__ == "__main__": main()