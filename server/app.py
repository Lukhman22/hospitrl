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
        self.math_html = "<div style='text-align:center; color:#666; padding:20px;'>Ready for first reallocation...</div>"

    def reset(self, task_id: str = "easy_balance"):
        self.steps = 0
        self.task_id = task_id
        self.history = [f"Environment Reset: Task {task_id} initiated."]
        
        # Scenarios for different difficulty levels
        if task_id == "easy_balance":
            self.wards = {"General Ward": 80, "Emergency Room": 10, "Intensive Care": 10}
            self.pressure = 70.0
        elif task_id == "medium_surge":
            self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
            self.pressure = 100.0
        elif task_id == "hard_optimization":
            self.wards = {"General Ward": 40, "Emergency Room": 30, "Intensive Care": 30}
            self.pressure = 100.0
        
        self.math_html = "<div style='text-align:center; color:#666; padding:20px;'>Environment Reset. Waiting for action...</div>"
        return self.get_observation()

    def get_observation(self):
        return {"wards": self.wards, "pressure": self.pressure, "task_id": self.task_id}

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        
        # Resource Logic with staff conservation check
        if src in self.wards and self.wards[src] >= qty:
            before_src, before_tgt = self.wards[src], self.wards.get(tgt, 0)
            
            self.wards[src] -= qty
            self.wards[tgt] = self.wards.get(tgt, 0) + qty
            
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 10.0
            self.pressure = max(0.0, self.pressure - impact)
            
            # Professional HTML Math Breakdown
            self.math_html = f"""
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid #444; font-family: sans-serif;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #ff4b4b; font-weight: bold;">▼ {src}</span>
                    <span style="font-family: monospace;">{before_src} → {self.wards[src]}</span>
                    <span style="background: #ff4b4b22; color: #ff4b4b; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">-{qty} Staff</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #00d26a; font-weight: bold;">▲ {tgt}</span>
                    <span style="font-family: monospace;">{before_tgt} → {self.wards[tgt]}</span>
                    <span style="background: #00d26a22; color: #00d26a; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">+{qty} Staff</span>
                </div>
            </div>
            """
            msg = "Success"
        else:
            self.math_html = f"<div style='color:#ff4b4b; padding:10px; border:1px solid #ff4b4b; border-radius:5px;'>⚠️ ERROR: Invalid reallocation parameters for {src}</div>"
            msg = "Invalid"

        # --- BUFFERED REWARD LOGIC (Strictly between 0 and 1) ---
        # Formula: 0.01 + (RawScore * 0.98) -> Maps [0,1] to [0.01, 0.99]
        raw_progress = (100.0 - self.pressure) / 100.0
        reward = round(0.01 + (raw_progress * 0.98), 4)
        
        done = self.pressure <= 5.0 or self.steps >= 10
        self.history.insert(0, f"Step {self.steps}: {msg} | Reward: {reward:.3f}")
        
        return self.get_observation(), reward, done, {"info": msg}

engine = HospitalEngine()
app = FastAPI()

# --- 2. OPENENV ENDPOINTS ---
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

# --- 3. GRADIO UI ---
with gr.Blocks(theme=gr.themes.Default(primary_hue="red", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏥 **HospitRL: Clinical Resource Command**")
    
    with gr.Row():
        with gr.Column(scale=1):
            press_gauge = gr.Number(label="System Pressure (%)", value=100)
            reward_gauge = gr.Number(label="Buffered Reward (0.01 - 0.99)", value=0.01)
            status_box = gr.HighlightedText(label="Triage Status", value=[("CRITICAL", "loss")])
        with gr.Column(scale=2):
            ward_plot = gr.BarPlot(x="Ward", y="Staff", title="Total Staff Registry (Capacity: 100)", y_lim=[0, 100], height=300)

    gr.Markdown("### 🕹️ Real-Time Reallocation")
    with gr.Row():
        with gr.Column():
            src_drop = gr.Dropdown(choices=["General Ward", "Emergency Room", "Intensive Care"], label="Source Ward", value="General Ward")
            tgt_drop = gr.Dropdown(choices=["General Ward", "Emergency Room", "Intensive Care"], label="Target Ward", value="Emergency Room")
            qty_input = gr.Slider(1, 50, step=1, label="Transfer Quantity", value=10)
            move_btn = gr.Button("Confirm Transfer", variant="primary")
        with gr.Column():
            gr.Markdown("#### 📊 Logic Verification")
            math_display = gr.HTML(value=engine.math_html)

    audit_log = gr.Textbox(label="Digital Audit Trail", lines=4, interactive=False)

    def ui_move(src, tgt, qty):
        obs, rew, done, info = engine.step(Action(source_ward=src, target_ward=tgt, staff_count=qty))
        df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
        
        # UI Thresholding for Status
        if obs["pressure"] >= 70: status = [("CRITICAL", "loss")]
        elif obs["pressure"] > 30: status = [("WARNING", "pending")]
        else: status = [("STABLE", "pro")]
        
        return df, obs["pressure"], rew, status, engine.math_html, "\n".join(engine.history)

    move_btn.click(ui_move, [src_drop, tgt_drop, qty_input], [ward_plot, press_gauge, reward_gauge, status_box, math_display, audit_log])

app = gr.mount_gradio_app(app, demo, path="/")

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()