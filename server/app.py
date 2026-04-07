import gradio as gr
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uvicorn

# --- 1. THE LOGIC ENGINE ---
class HospitalEngine:
    def __init__(self):
        # Defaulting to a realistic 100-staff scale
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
        # Sudden influx logic
        surge_amount = 15.0
        self.pressure = min(100.0, self.pressure + surge_amount)
        self.history.insert(0, f"🚨 SURGE ALERT: Mass casualty event! Stress Level +{surge_amount}%")
        self.update_trend()
        return self.pressure

    def move_staff(self, source, target, count):
        if source == target: return "Error: Select different wards."
        if self.wards[source] < count: return f"Error: Insufficient staff in {source}."
        
        # Capture "Before" state for the math breakdown
        before_src = self.wards[source]
        before_tgt = self.wards[target]
        
        # Perform Reallocation
        self.wards[source] -= count
        self.wards[target] += count
        
        # Clinical Impact: ER/ICU moves drop pressure more effectively
        reduction = 10.0 if target in ["Emergency Room", "Intensive Care"] else 4.0
        self.pressure = max(0.0, self.pressure - reduction)
        
        # GENERATE DYNAMIC MATH BREAKDOWN
        self.last_move_details = (
            f"📊 REALLOCATION MATH:\n"
            f"• {source}: {before_src} - {count} = {self.wards[source]}\n"
            f"• {target}: {before_tgt} + {count} = {self.wards[target]}"
        )
        
        self.update_trend()
        self.history.insert(0, f"Successfully moved {count} staff to {target}.")
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

# --- 2. THE UI (Dashboard) ---
def sync_ui():
    df_wards = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()])
    df_trend = pd.DataFrame(engine.pressure_trend)
    
    # Visual Triage Logic
    if engine.pressure > 80: status = [("CRITICAL OVERLOAD", "loss")]
    elif engine.pressure > 40: status = [("HIGH PATIENT VOLUME", "pending")]
    else: status = [("STABLE OPS", "pro")]
    
    return df_wards, df_trend, engine.pressure, status, engine.last_move_details, "\n".join(engine.history)

with gr.Blocks(theme=gr.themes.Default(primary_hue="blue")) as demo:
    gr.Markdown("# 🏥 HospitRL: Strategic Emergency Management System")
    
    with gr.Tab("Real-Time Operations"):
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
                amt_input = gr.Slider(1, 50, value=5, label="Number of Staff to Move", step=1)
                move_btn = gr.Button("Confirm Reallocation", variant="primary")
                
            with gr.Column():
                # DYNAMIC MATH BOX
                math_display = gr.Textbox(label="Movement Logic Breakdown", lines=3, interactive=False)
                trend_line = gr.LinePlot(value=pd.DataFrame(engine.pressure_trend), x="Step", y="Stress", title="Stress Optimization Trend")

        log_display = gr.Textbox(label="Digital Audit Trail", lines=3)

    with gr.Tab("Admin Configuration"):
        gr.Markdown("### ⚙️ Initialize Hospital Capacity")
        g_s = gr.Number(label="General Ward Start", value=50)
        e_s = gr.Number(label="ER Start", value=25)
        i_s = gr.Number(label="ICU Start", value=25)
        apply_btn = gr.Button("Apply New Baseline")

    # Wire events
    move_btn.click(lambda s,t,a: engine.move_staff(s,t,a) or sync_ui(), 
                  [src_drop, src_drop.choices[1] if src_drop == src_drop.choices[0] else tgt_drop, amt_input], 
                  [ward_chart, trend_line, stress_num, status_box, math_display, log_display])
    
    surge_btn.click(lambda: engine.trigger_surge() or sync_ui(), None, [ward_chart, trend_line, stress_num, status_box, math_display, log_display])
    apply_btn.click(lambda g,e,i: engine.reset(g,e,i) or sync_ui(), [g_s, e_s, i_s], [ward_chart, trend_line, stress_num, status_box, math_display, log_display])

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)