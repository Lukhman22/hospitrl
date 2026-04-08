import gradio as gr
import pandas as pd
from fastapi import FastAPI, Query
from server.models import Action
import uvicorn

class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.task_id = "easy_balance"
        self.steps = 0
        self.max_steps = 10
        self.history = []

    def reset(self, task_id="easy_balance"):
        self.steps = 0
        self.task_id = task_id
        if task_id == "easy_balance":
            self.wards = {"General Ward": 75, "Emergency Room": 15, "Intensive Care": 10}
            self.pressure = 80.0
        elif task_id == "medium_surge":
            self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
            self.pressure = 100.0
        else: # hard_optimization
            self.wards = {"General Ward": 35, "Emergency Room": 35, "Intensive Care": 30}
            self.pressure = 100.0
        return self.get_obs()

    def get_obs(self):
        return {"wards": self.wards, "pressure": self.pressure, "task_id": self.task_id}

    def calculate_strict_reward(self):
        # MOGUL-STYLE RUBRIC (Weighted components)
        # Component 1: Safety (Inverse of pressure)
        safety_score = (100.0 - self.pressure) / 100.0
        
        # Component 2: Efficiency (Staff Balance)
        # Perfectly balanced is 33/33/34. We measure deviation.
        ideal = 33.3
        dev = sum(abs(v - ideal) for v in self.wards.values()) / 200.0
        eff_score = 1.0 - dev

        # Component 3: SLA (Steps remaining)
        sla_score = (self.max_steps - self.steps) / self.max_steps

        # Final Weighted Rubric
        # We add 0.0001 and multiply by 0.9998 to FORCE (0, 1) range
        raw_total = (safety_score * 0.40) + (eff_score * 0.30) + (sla_score * 0.30)
        return 0.0001 + (raw_total * 0.9998)

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        
        if src in self.wards and self.wards[src] >= qty:
            self.wards[src] -= qty
            self.wards[tgt] = self.wards.get(tgt, 0) + qty
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 5.0
            self.pressure = max(0.0, self.pressure - impact)
            msg = "Success"
        else:
            msg = "Invalid Action"

        reward = round(self.calculate_strict_reward(), 4)
        done = self.pressure <= 5.0 or self.steps >= self.max_steps
        self.history.insert(0, f"Step {self.steps}: {msg} | Reward: {reward}")
        
        return self.get_obs(), reward, done, {"info": msg}

engine = HospitalEngine()
app = FastAPI()

@app.post("/reset")
def reset(task_id: str = Query("easy_balance")):
    return {"observation": engine.reset(task_id)}

@app.post("/step")
def step(action: Action):
    obs, rew, done, info = engine.step(action)
    return {"observation": obs, "reward": rew, "terminated": done, "info": info}

# --- CUSTOM CSS FOR MOGUL LOOK ---
custom_css = """
#dashboard-container { background-color: #0b0f19; border-radius: 10px; padding: 20px; color: white; }
.stat-card { border: 1px solid #1e293b; background: #111827; padding: 15px; border-radius: 8px; text-align: center; }
"""

with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:
    gr.Markdown("# 🏥 HospitRL: Strategic Command Center")
    gr.Markdown("### Clinical Resource Optimization — RL Environment")
    
    with gr.Row():
        with gr.Column(scale=1, elem_classes="stat-card"):
            gr.Markdown("● **System Stress**")
            stress_disp = gr.Number(value=100.0, label="Pressure %", interactive=False)
        with gr.Column(scale=1, elem_classes="stat-card"):
            gr.Markdown("● **Evaluation Score**")
            reward_disp = gr.Number(value=0.0001, label="Reward (0,1)", interactive=False)
        with gr.Column(scale=1, elem_classes="stat-card"):
            gr.Markdown("● **Steps Taken**")
            step_disp = gr.Number(value=0, label="Step Count", interactive=False)

    with gr.Row():
        with gr.Column(scale=2):
            ward_plot = gr.BarPlot(x="Ward", y="Staff", title="Global Staff Registry", y_lim=[0,100], height=300)
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Grading Rubric")
            gr.Markdown("""
            | Component | Weight |
            | :--- | :--- |
            | Patient Safety | 40% |
            | Resource Eff. | 30% |
            | SLA Compliance | 30% |
            """)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🎮 Manual Control")
            src_drop = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Source Ward")
            tgt_drop = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Target Ward")
            qty_sld = gr.Slider(1, 50, step=1, label="Staff Count")
            move_btn = gr.Button("⚡ Execute Step", variant="primary")
        with gr.Column():
            gr.Markdown("### 🎬 Action Log")
            log_box = gr.Textbox(label="System Feedback", lines=6)

    def ui_step(s, t, q):
        obs, rew, done, info = engine.step(Action(source_ward=s, target_ward=t, staff_count=q))
        df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
        return df, obs["pressure"], rew, engine.steps, "\n".join(engine.history)

    move_btn.click(ui_step, [src_drop, tgt_drop, qty_sld], [ward_plot, stress_disp, reward_disp, step_disp, log_box])

app = gr.mount_gradio_app(app, demo, path="/")

def main(): uvicorn.run(app, host="0.0.0.0", port=7860)
if __name__ == "__main__": main()