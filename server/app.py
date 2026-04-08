import gradio as gr
import pandas as pd
from fastapi import FastAPI, Query
from server.models import Action
import uvicorn

# THE SAFETY SQUISH: Guarantees everything is strictly (0.0001, 0.9999)
def squash(value):
    return float(max(0.0001, min(0.9999, value)))

class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.task_id = "easy_balance"
        self.steps = 0
        self.max_steps = 10
        self.history = []
        self.math_html = "<div style='text-align:center; padding:10px;'>System Standby.</div>"
        self.clinical_insight = "<div style='text-align:center; padding:10px;'>Awaiting first move...</div>"

    def reset(self, task_id="easy_balance"):
        self.steps = 0
        self.task_id = task_id
        if task_id == "easy_balance":
            self.wards = {"General Ward": 80, "Emergency Room": 10, "Intensive Care": 10}
            self.pressure = 70.0
        elif task_id == "medium_surge":
            self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
            self.pressure = 100.0
        else: # hard_optimization
            self.wards = {"General Ward": 35, "Emergency Room": 35, "Intensive Care": 30}
            self.pressure = 100.0
        return self.get_obs()

    def get_obs(self):
        return {"wards": self.wards, "pressure": self.pressure, "task_id": self.task_id}

    def calculate_rubric_reward(self):
        # Weighted Rubric
        safety = (100.0 - self.pressure) / 100.0
        eff = 1.0 - (sum(abs(v - 33.3) for v in self.wards.values()) / 200.0)
        sla = (self.max_steps - self.steps) / self.max_steps
        
        # We target the middle of the range to be safe
        raw_score = (safety * 0.40) + (eff * 0.30) + (sla * 0.30)
        # Final Squish before returning
        return squash(0.01 + (raw_score * 0.98))

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        
        if src in self.wards and self.wards[src] >= qty:
            before_src, before_tgt = self.wards[src], self.wards[tgt]
            self.wards[src] -= qty
            self.wards[tgt] += qty
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 5.0
            self.pressure = max(0.0, self.pressure - impact)
            
            self.math_html = f"""<div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:8px;">
                <span style="color:#ff4b4b;">▼ {src} (-{qty})</span><br>
                <span style="color:#00d26a;">▲ {tgt} (+{qty})</span>
            </div>"""
            msg = "Success"
        else:
            msg = "Invalid Action"

        reward = self.calculate_rubric_reward()
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

# --- UI (MOGUL-STYLE) ---
with gr.Blocks(theme=gr.themes.Default(primary_hue="orange", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏥 HospitRL: **Strategic Command Dashboard**")
    with gr.Row():
        p_val = gr.Number(label="System Pressure (%)", value=100)
        r_val = gr.Number(label="Validator Reward (0, 1)", value=0.01)
        s_val = gr.Number(label="Steps", value=0)
    
    with gr.Row():
        with gr.Column(scale=2):
            plot = gr.BarPlot(x="Ward", y="Staff", title="Staff Distribution", y_lim=[0,100])
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Grading Rubric\n40% Safety | 30% Efficiency | 30% SLA")
            math_ui = gr.HTML(value=engine.math_html)

    with gr.Row():
        src = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Source")
        tgt = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Target")
        qty = gr.Slider(1, 50, step=1, label="Quantity")
        btn = gr.Button("⚡ Execute", variant="primary")

    def ui_step(s, t, q):
        obs, rew, done, info = engine.step(Action(source_ward=s, target_ward=t, staff_count=q))
        df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
        return df, obs["pressure"], rew, engine.steps, engine.math_html

    btn.click(ui_step, [src, tgt, qty], [plot, p_val, r_val, s_val, math_ui])

app = gr.mount_gradio_app(app, demo, path="/")
def main(): uvicorn.run(app, host="0.0.0.0", port=7860)
if __name__ == "__main__": main()