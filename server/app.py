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
        self.math_html = "<div style='text-align:center; padding:20px; color:#666;'>Ready for reallocation...</div>"
        self.clinical_insight = "<div style='text-align:center; padding:20px; color:#666;'>Awaiting data...</div>"

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
        self.math_html = "<div style='text-align:center; padding:10px;'>System Reset.</div>"
        return self.get_obs()

    def get_obs(self):
        return {"wards": self.wards, "pressure": self.pressure, "task_id": self.task_id}

    def get_clinical_feedback(self, target, qty):
        if target in ["Emergency Room", "Intensive Care"]:
            return f"""<div style="background:#00d26a11; border-left:4px solid #00d26a; padding:10px;">
                <h4 style="margin:0; color:#00d26a;">🏥 High-Impact Stabilization</h4>
                <p style="margin:5px 0 0 0; font-size:0.85em;">Adding {qty} staff to {target} directly reduces the critical triage backlog.</p>
            </div>"""
        return f"""<div style="background:#3b82f611; border-left:4px solid #3b82f6; padding:10px;">
                <h4 style="margin:0; color:#3b82f6;">ℹ️ Maintenance Reallocation</h4>
                <p style="margin:5px 0 0 0; font-size:0.85em;">Staff moved to {target} helps with bed turnover but has lower surge impact.</p>
            </div>"""

    def calculate_strict_reward(self):
        # 40% Safety, 30% Efficiency, 30% SLA
        safety = (100.0 - self.pressure) / 100.0
        eff = 1.0 - (sum(abs(v - 33.3) for v in self.wards.values()) / 200.0)
        sla = (self.max_steps - self.steps) / self.max_steps
        raw_score = (safety * 0.40) + (eff * 0.30) + (sla * 0.30)
        return round(0.0001 + (raw_score * 0.9998), 4) # (0, 1) Buffer

    def step(self, action: Action):
        self.steps += 1
        src, tgt, qty = action.source_ward, action.target_ward, action.staff_count
        if src in self.wards and self.wards[src] >= qty:
            before_src, before_tgt = self.wards[src], self.wards[tgt]
            self.wards[src] -= qty
            self.wards[tgt] += qty
            impact = 25.0 if tgt in ["Emergency Room", "Intensive Care"] else 5.0
            self.pressure = max(0.0, self.pressure - impact)
            self.math_html = f"""<div style="background:rgba(255,255,255,0.05); padding:10px; border-radius:8px; border:1px solid #444;">
                <span style="color:#ff4b4b;">▼ {src} ({before_src}→{self.wards[src]})</span><br>
                <span style="color:#00d26a;">▲ {tgt} ({before_tgt}→{self.wards[tgt]})</span>
            </div>"""
            self.clinical_insight = self.get_clinical_feedback(tgt, qty)
            msg = "Success"
        else:
            msg = "Invalid"
        reward = self.calculate_strict_reward()
        done = self.pressure <= 5.0 or self.steps >= self.max_steps
        self.history.insert(0, f"Step {self.steps}: {msg} | Reward: {reward}")
        return self.get_obs(), reward, done, {"info": msg}

engine = HospitalEngine()
app = FastAPI()

@app.post("/reset")
def reset(task_id: str = Query("easy_balance")): return {"observation": engine.reset(task_id)}

@app.post("/step")
def step(action: Action):
    obs, rew, done, info = engine.step(action)
    return {"observation": obs, "reward": rew, "terminated": done, "info": info}

@app.get("/state")
def get_state(): return {"observation": engine.get_obs(), "steps": engine.steps}

with gr.Blocks(theme=gr.themes.Default(primary_hue="orange", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏥 HospitRL: **Strategic Command Dashboard**")
    
    with gr.Row():
        with gr.Column(scale=1):
            p_gauge = gr.Number(label="System Pressure (%)", value=100)
            r_gauge = gr.Number(label="Rubric Reward (0-1)", value=0.0001)
            s_gauge = gr.Number(label="SLA Steps", value=0)
            status = gr.HighlightedText(value=[("CRITICAL", "loss")])
        with gr.Column(scale=2):
            plot = gr.BarPlot(x="Ward", y="Staff", title="Staff registry (Total: 100)", y_lim=[0,100], height=280)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🕹️ Command Controls")
            src = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Source")
            tgt = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="Target")
            qty = gr.Slider(1, 50, step=1, label="Quantity")
            btn = gr.Button("⚡ Execute Reallocation", variant="primary")
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Grading Rubric")
            gr.Markdown("""| Component | Weight | Formula |\n| :--- | :--- | :--- |\n| **Patient Safety** | 40% | (100-Pressure)/100 |\n| **Resource Eff.** | 30% | 1-Deviation |\n| **SLA Compliance** | 30% | (MaxSteps-Step)/Max |""")
            math_ui = gr.HTML(value=engine.math_html)
            insight_ui = gr.HTML(value=engine.clinical_insight)

    log = gr.Textbox(label="Digital Audit Trail", lines=3)

    def ui_step(s, t, q):
        obs, rew, done, info = engine.step(Action(source_ward=s, target_ward=t, staff_count=q))
        df = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in obs["wards"].items()])
        st = [("STABLE", "pro")] if obs["pressure"] < 30 else [("CRITICAL", "loss")]
        return df, obs["pressure"], rew, engine.steps, st, engine.math_html, engine.clinical_insight, "\n".join(engine.history)

    btn.click(ui_step, [src, tgt, qty], [plot, p_gauge, r_gauge, s_gauge, status, math_ui, insight_ui, log])

app = gr.mount_gradio_app(app, demo, path="/")
def main(): uvicorn.run(app, host="0.0.0.0", port=7860)
if __name__ == "__main__": main()