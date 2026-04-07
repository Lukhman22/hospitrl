import gradio as gr
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uvicorn

# --- 1. THE LOGIC ENGINE ---
class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.history = []
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.last_move_details = "System Initialized. Total Staff: 100"

    def reset(self, g_staff=50, e_staff=25, i_staff=25):
        self.wards = {"General Ward": g_staff, "Emergency Room": e_staff, "Intensive Care": i_staff}
        self.pressure = 100.0
        self.history = [f"Hospital Rebooted: {sum(self.wards.values())} staff distributed."]
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.last_move_details = "Registry Reset."
        return self.wards, self.pressure

    def trigger_surge(self):
        surge_amount = 15.0
        self.pressure = min(100.0, self.pressure + surge_amount)
        self.history.insert(0, f"🚨 SURGE ALERT: Pressure spikes to {self.pressure}%")
        self.update_trend()
        return self.pressure

    def move_staff(self, source, target, count):
        if source == target: return "Error: Select different wards."
        if self.wards[source] < count: return f"Error: Insufficient staff in {source}."
        
        before_src, before_tgt = self.wards[source], self.wards[target]
        self.wards[source] -= count
        self.wards[target] += count
        
        reduction = 10.0 if target in ["Emergency Room", "Intensive Care"] else 4.0
        self.pressure = max(0.0, self.pressure - reduction)
        
        self.last_move_details = (
            f"📊 REALLOCATION MATH:\n"
            f"• {source}: {before_src} - {count} = {self.wards[source]}\n"
            f"• {target}: {before_tgt} + {count} = {self.wards[target]}"
        )
        self.update_trend()
        self.history.insert(0, f"Success: Moved {count} staff to {target}.")
        return "Success"

    def update_trend(self):
        self.pressure_trend.append({"Step": len(self.pressure_trend), "Stress": self.pressure})

engine = HospitalEngine()
app = FastAPI()

class ActionRequest(BaseModel):
    action: Dict

@app.post("/reset")
def api_reset():
    engine.reset()
    return {"observation": {"wards": engine.wards, "pressure": engine.pressure}}

@app.post("/step")
def api_step(req: ActionRequest):
    res = engine.move_staff(req.action["source_ward"], req.action["target_ward"], req.action["staff_count"])
    return {
        "observation": {"wards": engine.wards, "pressure": engine.pressure},
        "reward": 100 if res == "Success" else -50,
        "terminated": engine.pressure <= 0,
        "info": {"pressure": engine.pressure}
    }

# --- 2. THE UI LOGIC (Fixed for Gradio Output) ---
def sync_ui(error_msg=None):
    df_wards = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()])
    df_trend = pd.DataFrame(engine.pressure_trend)
    
    if engine.pressure > 80: status = [("CRITICAL OVERLOAD", "loss")]
    elif engine.pressure > 40: status = [("HIGH VOLUME", "pending")]
    else: status = [("STABLE OPS", "pro")]
    
    # If there's an error, show it in the Math box instead of crashing
    math_val = error_msg if error_msg else engine.last_move_details
    
    return df_wards, df_trend, engine.pressure, status, math_val, "\n".join(engine.history)

with gr.Blocks() as demo:
    gr.Markdown("# 🏥 HospitRL: Strategic Emergency Management System")
    
    with gr.Row():
        with gr.Column(scale=1):
            stress_num = gr.Number(label="System Stress Level (%)", value=100.0)
            status_box = gr.HighlightedText(value=[("CRITICAL OVERLOAD", "loss")])
            surge_btn = gr.Button("🚨 Trigger Emergency Surge", variant="stop")
            
        with gr.Column(scale=2):
            ward_chart = gr.BarPlot(
                value=pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()]), 
                x="Ward", y="Staff", title="Current Staff Registry (Total: 100)",
                y_lim=[0, 100]
            )

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🕹️ Resource Controls")
            src_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="From Ward", value="General Ward")
            tgt_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="To Ward", value="Emergency Room")
            amt_input = gr.Number(label="Number of Staff to Move", value=5, precision=0)
            move_btn = gr.Button("Confirm Reallocation", variant="primary")
            
        with gr.Column():
            math_display = gr.Textbox(label="Movement Logic Breakdown", lines=3, interactive=False)
            trend_line = gr.LinePlot(value=pd.DataFrame(engine.pressure_trend), x="Step", y="Stress", title="Stress Optimization Trend")

    log_display = gr.Textbox(label="Digital Audit Trail", lines=3)

    # --- FIXED EVENT HANDLERS ---
    def handle_move(s, t, a):
        result = engine.move_staff(s, t, a)
        if result.startswith("Error"):
            return sync_ui(error_msg=result)
        return sync_ui()

    def handle_reset():
        engine.reset()
        return sync_ui()

    def handle_surge():
        engine.trigger_surge()
        return sync_ui()

    move_btn.click(handle_move, [src_drop, tgt_drop, amt_input], [ward_chart, trend_line, stress_num, status_box, math_display, log_display])
    surge_btn.click(handle_surge, None, [ward_chart, trend_line, stress_num, status_box, math_display, log_display])

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)