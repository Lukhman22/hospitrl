import gradio as gr
import pandas as pd
from fastapi import FastAPI, Query
from server.models import Action, Observation, State
import uvicorn

# --- 1. THE OPENENV ENGINE ---
class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.task_id = "easy_balance"
        self.steps = 0
        self.history = []
        self.math_log = "System Standby"

    def reset(self, task_id: str = "easy_balance"):
        self.steps = 0
        self.task_id = task_id
        self.history = [f"Environment Reset: Task {task_id} initiated."]
        
        # 3 Mandatory Tasks (Easy -> Medium -> Hard)
        if task_id == "easy_balance":
            self.wards = {"General Ward": 80, "Emergency Room": 10, "Intensive Care": 10}
            self.pressure = 70.0
        elif task_id == "medium_surge":
            self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
            self.pressure = 100.0
        elif task_id == "hard_optimization":
            self.wards = {"General Ward": 40, "Emergency Room": 30, "Intensive Care": 30}
            self.pressure = 100.0
        
        return self.get_observation()

    def get_observation(self):
        return {
            "wards": self.wards,
            "pressure": self.pressure,
            "task_id": self.task_id
        }

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        
        # Validating Action (Conservation of Staff Logic)
        if src in self.wards and self.wards[src] >= qty:
            before_src = self.wards[src]
            before_tgt = self.wards[tgt]
            
            self.wards[src] -= qty
            self.wards[tgt] += qty
            
            # Meaningful Reward Logic: Moving to ER/ICU reduces pressure most
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 10.0
            self.pressure = max(0.0, self.pressure - impact)
            
            self.math_log = f"LOGIC: {src}({before_src}-{qty}={self.wards[src]}) | {tgt}({before_tgt}+{qty}={self.wards[tgt]})"
            msg = f"Successfully moved {qty} staff."
        else:
            msg = "INVALID ACTION: Insufficient staff or invalid ward."

        # Reward Calculation: Normalized signal 0.0 to 1.0
        reward = max(0.0, min(1.0, (100.0 - self.pressure) / 100.0))
        done = self.pressure <= 5.0 or self.steps >= 10
        
        self.history.insert(0, f"Step {self.steps}: {msg} | Reward: {reward:.2f}")
        return self.get_observation(), reward, done, {"info": msg}

engine = HospitalEngine()
app = FastAPI()

# --- 2. API ENDPOINTS (OpenEnv Spec) ---
@app.post("/reset")
def reset(task_id: str = Query("easy_balance")):
    return {"observation": engine.reset(task_id)}

@app.post("/step")
def step(action: Action):
    obs, rew, done, info = engine.step(action)
    return {"observation": obs, "reward": rew, "terminated": done, "info": info}

@app.get("/state")
def state():
    return {"observation": engine.get_observation(), "steps_taken": engine.steps}

# --- 3. GRADIO UI (For the Professors) ---
def sync_ui(src, tgt, qty):
    obs, rew, done, info = engine.step(Action(source_ward=src, target_ward=tgt, staff_count=qty))
    df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
    
    # Status Indicator
    if obs["pressure"] >= 70: status = [("CRITICAL", "loss")]
    elif obs["pressure"] > 30: status = [("WARNING", "pending")]
    else: status = [("STABLE", "pro")]
    
    return df, obs["pressure"], rew, status, engine.math_log, "\n".join(engine.history)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 HospitRL Command Center\n*OpenEnv Compliant Real-World Resource Management*")
    
    with gr.Row():
        with gr.Column(scale=1):
            press_gauge = gr.Number(label="Hospital Pressure (%)", value=100)
            reward_gauge = gr.Number(label="Continuous Reward (0.0 - 1.0)", value=0.0)
            status_box = gr.HighlightedText(value=[("CRITICAL", "loss")])
        with gr.Column(scale=2):
            ward_plot = gr.BarPlot(x="Ward", y="Staff", title="Live Staff Registry", y_lim=[0, 100])

    with gr.Row():
        src_drop = gr.Dropdown(choices=["General Ward", "Emergency Room", "Intensive Care"], label="Source")
        tgt_drop = gr.Dropdown(choices=["General Ward", "Emergency Room", "Intensive Care"], label="Target")
        qty_input = gr.Slider(1, 50, step=1, label="Staff Count")

    move_btn = gr.Button("Manual Reallocation", variant="primary")
    
    with gr.Row():
        math_display = gr.Textbox(label="Movement Logic Breakdown", interactive=False)
        audit_log = gr.Textbox(label="Clinical Activity Log", lines=5)

    move_btn.click(sync_ui, [src_drop, tgt_drop, qty_input], 
                  [ward_plot, press_gauge, reward_gauge, status_box, math_display, audit_log])

app = gr.mount_gradio_app(app, demo, path="/")

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()