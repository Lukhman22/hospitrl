import gradio as gr
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uvicorn

# --- 1. THE ADVANCED ENGINE ---
class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 10, "Emergency Room": 10, "Intensive Care": 10}
        self.pressure = 100.0
        self.history = []
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.total_moves = 0

    def reset(self, g_staff=10, e_staff=10, i_staff=10):
        self.wards = {"General Ward": g_staff, "Emergency Room": e_staff, "Intensive Care": i_staff}
        self.pressure = 100.0
        self.history = [f"Hospital Initialized: {sum(self.wards.values())} total staff online."]
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.total_moves = 0
        return self.wards, self.pressure

    def trigger_surge(self):
        # The "Catchy" Feature: Randomly increase stress
        surge_amount = 20.0
        self.pressure = min(100.0, self.pressure + surge_amount)
        self.history.insert(0, f"🚨 SURGE ALERT: Influx of emergency patients! Stress +{surge_amount}%")
        self.update_trend()
        return self.pressure

    def move_staff(self, source, target, count):
        if source == target: return "Error: Select different wards."
        if self.wards[source] < count: return f"Error: Only {self.wards[source]} staff available."
        
        self.wards[source] -= count
        self.wards[target] += count
        self.total_moves += 1
        
        # Strategic Impact: ER and ICU moves reduce stress significantly
        reduction = 15.0 if target in ["Emergency Room", "Intensive Care"] else 5.0
        self.pressure = max(0.0, self.pressure - reduction)
        
        self.update_trend()
        self.history.insert(0, f"Action {self.total_moves}: Moved {count} to {target}. Pressure: {self.pressure}%")
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

# --- 2. THE COMMAND CENTER UI ---
def sync_ui():
    df_wards = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()])
    df_trend = pd.DataFrame(engine.pressure_trend)
    # Triage logic for the status indicator
    if engine.pressure > 80: status = [("CRITICAL SURGE", "loss")]
    elif engine.pressure > 40: status = [("WARNING: HIGH LOAD", "pending")]
    else: status = [("STABLE", "pro")]
    return df_wards, df_trend, engine.pressure, status, "\n".join(engine.history)

with gr.Blocks() as demo:
    gr.Markdown("# 🏥 HospitRL Command Center v2.0")
    
    with gr.Tab("Simulation Dashboard"):
        with gr.Row():
            with gr.Column(scale=1):
                stress_display = gr.Number(label="Hospital Stress Level (%)", value=100.0)
                status_indicator = gr.HighlightedText(value=[("CRITICAL SURGE", "loss")])
                surge_btn = gr.Button("⚠️ Trigger Patient Surge", variant="stop")
                
            with gr.Column(scale=2):
                ward_chart = gr.BarPlot(value=pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()]), 
                                       x="Ward", y="Staff", title="Real-time Staff Distribution")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🕹️ Resource Allocation")
                src_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="From Ward", value="General Ward")
                tgt_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="To Ward", value="Emergency Room")
                amt_input = gr.Number(label="Staff Count", value=1, precision=0)
                move_btn = gr.Button("Execute Reallocation", variant="primary")
                
            with gr.Column():
                trend_chart = gr.LinePlot(value=pd.DataFrame(engine.pressure_trend), x="Step", y="Stress", title="Optimization Trend")

        activity_log = gr.Textbox(label="Clinical Activity Timeline", lines=4)

    with gr.Tab("Hospital Configuration"):
        gr.Markdown("### ⚙️ Set Initial Hospital Capacity")
        g_init = gr.Slider(5, 50, value=10, label="General Ward Staff")
        e_init = gr.Slider(5, 50, value=10, label="Emergency Room Staff")
        i_init = gr.Slider(5, 50, value=10, label="Intensive Care Staff")
        config_btn = gr.Button("Apply Configuration & Reset", variant="primary")

    # Event Logic
    def handle_move(src, tgt, amt):
        engine.move_staff(src, tgt, amt)
        return sync_ui()

    def handle_reset(g, e, i):
        engine.reset(g, e, i)
        return sync_ui()

    def handle_surge():
        engine.trigger_surge()
        return sync_ui()

    move_btn.click(handle_move, [src_drop, tgt_drop, amt_input], [ward_chart, trend_chart, stress_display, status_indicator, activity_log])
    config_btn.click(handle_reset, [g_init, e_init, i_init], [ward_chart, trend_chart, stress_display, status_indicator, activity_log])
    surge_btn.click(handle_surge, None, [ward_chart, trend_chart, stress_display, status_indicator, activity_log])

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)