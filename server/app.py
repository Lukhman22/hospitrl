import gradio as gr
import pandas as pd
from fastapi import FastAPI, Query
from server.models import Action
import uvicorn

class HospitalEngine:
    def __init__(self):
        # The Core State
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.task_id = "easy_balance"
        self.steps = 0
        self.max_steps = 10
        self.history = []
        
        # UI State
        self.math_html = "<div style='text-align:center; padding:20px; color:#666;'>Ready for first reallocation...</div>"
        self.clinical_insight = "<div style='text-align:center; padding:20px; color:#666;'>Awaiting clinical data...</div>"

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
        
        self.history = [f"Environment Reset: {task_id.replace('_', ' ').title()} active."]
        self.math_html = "<div style='text-align:center; padding:20px; color:#666;'>Environment Reset.</div>"
        self.clinical_insight = "<div style='text-align:center; padding:20px; color:#666;'>New task initialized.</div>"
        return self.get_obs()

    def get_obs(self):
        return {"wards": self.wards, "pressure": self.pressure, "task_id": self.task_id}

    def get_clinical_feedback(self, target, qty):
        # New Feedback Logic for ER/ICU
        if target == "Emergency Room":
            return f"""<div style="background:#00d26a11; border-left:4px solid #00d26a; padding:15px; border-radius:4px;">
                <h4 style="margin:0; color:#00d26a;">🏥 ER Bottleneck Resolved</h4>
                <p style="margin:5px 0 0 0; font-size:0.9em;">Reallocating {qty} staff to the ER improves Triage velocity. 
                This directly reduces the "Arrival-to-Bed" lag, which is the primary driver of system stress.</p>
            </div>"""
        elif target == "Intensive Care":
            return f"""<div style="background:#00d26a11; border-left:4px solid #00d26a; padding:15px; border-radius:4px;">
                <h4 style="margin:0; color:#00d26a;">⚡ ICU Critical Stabilization</h4>
                <p style="margin:5px 0 0 0; font-size:0.9em;">Increasing ICU headcount allows for better patient-to-nurse ratios. 
                High-acuity monitoring reduces secondary complications, lowering total hospital pressure.</p>
            </div>"""
        else:
            return f"""<div style="background:#3b82f611; border-left:4px solid #3b82f6; padding:15px; border-radius:4px;">
                <h4 style="margin:0; color:#3b82f6;">ℹ️ General Maintenance</h4>
                <p style="margin:5px 0 0 0; font-size:0.9em;">Staff moved to the General Ward helps with discharge planning, 
                but has lower immediate impact on critical surge pressure.</p>
            </div>"""

    def calculate_strict_reward(self):
        # RUBRIC: 40% Safety, 30% Efficiency (Balance), 30% SLA (Steps)
        safety = (100.0 - self.pressure) / 100.0
        eff = 1.0 - (sum(abs(v - 33.3) for v in self.wards.values()) / 200.0)
        sla = (self.max_steps - self.steps) / self.max_steps
        
        raw_score = (safety * 0.40) + (eff * 0.30) + (sla * 0.30)
        # THE SHIELD: Guaranteed (0, 1)
        return round(0.0001 + (raw_score * 0.9998), 4)

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        
        if src in self.wards and self.wards[src] >= qty:
            before_src, before_tgt = self.wards[src], self.wards.get(tgt, 0)
            self.wards[src] -= qty
            self.wards[tgt] = self.wards.get(tgt, 0) + qty
            
            # Clinical Reduction Impact
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 5.0
            self.pressure = max(0.0, self.pressure - impact)
            
            # Update HTML UI Components
            self.math_html = f"""
            <div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:8px; border:1px solid #444;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="color:#ff4b4b;">▼ {src}</span> <span>{before_src} → {self.wards[src]} (-{qty})</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#00d26a;">▲ {tgt}</span> <span>{before_tgt} → {self.wards[tgt]} (+{qty})</span>
                </div>
            </div>"""
            self.clinical_insight = self.get_clinical_feedback(tgt, qty)
            msg = "Success"
        else:
            msg = "Invalid"
            self.math_html = "<div style='color:#ff4b4b; border:1px solid #ff4b4b; padding:10px;'>Invalid Move</div>"

        reward = self.calculate_strict_reward()
        done = self.pressure <= 5.0 or self.steps >= self.max_steps
        self.history.insert(0, f"Step {self.steps}: {msg} | Reward: {reward}")
        
        return self.get_obs(), reward, done, {"info": msg}

engine = HospitalEngine()
app = FastAPI()

# --- API ---
@app.post("/reset")
def reset(task_id: str = Query("easy_balance")): return {"observation": engine.reset(task_id)}

@app.post("/step")
def step(action: Action):
    obs, rew, done, info = engine.step(action)
    return {"observation": obs, "reward": rew, "terminated": done, "info": info}

# --- UI ---
with gr.Blocks(theme=gr.themes.Default(primary_hue="orange", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏥 HospitRL: **Strategic Command Dashboard**")
    
    with gr.Row():
        with gr.Column(scale=1):
            press_num = gr.Number(label="System Pressure (%)", value=100)
            rew_num = gr.Number(label="Aggregated Reward (0-1)", value=0.0001)
            step_num = gr.Number(label="SLA Steps Taken", value=0)
            status = gr.HighlightedText(value=[("CRITICAL OVERLOAD", "loss")])
        with gr.Column(scale=2):
            ward_plot = gr.BarPlot(x="Ward", y="Staff", title="Live Staff Allocation (Total: 100)", y_lim=[0,100], height=320)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🕹️ Command Controls")
            src_d = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Source")
            tgt_d = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Target")
            qty_s = gr.Slider(1, 50, step=1, label="Quantity")
            move_btn = gr.Button("⚡ Execute Reallocation", variant="primary")
        with gr.Column(scale=1):
            gr.Markdown("### 📊 Logic Verification")
            math_ui = gr.HTML(value=engine.math_html)
            gr.Markdown("### 🧠 Clinical Intelligence")
            insight_ui = gr.HTML(value=engine.clinical_insight)

    log_box = gr.Textbox(label="Digital Audit Trail", lines=3)

    def ui_step(s, t, q):
        obs, rew, done, info = engine.step(Action(source_ward=s, target_ward=t, staff_count=q))
        df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
        st = [("STABLE", "pro")] if obs["pressure"] < 30 else [("CRITICAL", "loss")]
        return df, obs["pressure"], rew, engine.steps, st, engine.math_html, engine.clinical_insight, "\n".join(engine.history)

    move_btn.click(ui_step, [src_d, tgt_d, qty_s], [ward_plot, press_num, rew_num, step_num, status, math_ui, insight_ui, log_box])

app = gr.mount_gradio_app(app, demo, path="/")
def main(): uvicorn.run(app, host="0.0.0.0", port=7860)
if __name__ == "__main__": main()