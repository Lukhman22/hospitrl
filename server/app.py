import gradio as gr
import os
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uvicorn

# --- 1. THE LOGIC ENGINE ---
class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 10, "Emergency Room": 5, "Intensive Care": 8}
        self.pressure = 50
        self.history = [] # For the log
        self.pressure_trend = [{"Step": 0, "Stress": 50}] # For the chart

    def reset(self):
        self.__init__()
        return self.wards, self.pressure

    def move_staff(self, source, target, count):
        if source == target:
            return "Error: Source and Target wards must be different."
        if self.wards[source] < count:
            return f"Error: Insufficient staff in {source}."
        
        self.wards[source] -= count
        self.wards[target] += count
        
        # Logic: Impact on pressure
        reduction = 8 if target in ["Emergency Room", "Intensive Care"] else 3
        self.pressure = max(0, self.pressure - reduction)
        
        # Update Trend Data
        new_step = len(self.pressure_trend)
        self.pressure_trend.append({"Step": new_step, "Stress": self.pressure})
        
        log_entry = f"Step {new_step}: Reallocated {count} staff from {source} to {target}."
        self.history.insert(0, log_entry)
        return "Success"

engine = HospitalEngine()

# --- 2. THE API (For Scaler Grader) ---
app = FastAPI()

class ActionRequest(BaseModel):
    action: Dict

@app.post("/reset")
def api_reset():
    wards, press = engine.reset()
    return {"observation": {"wards": wards, "pressure": press}}

@app.post("/step")
def api_step(req: ActionRequest):
    res = engine.move_staff(req.action["source_ward"], req.action["target_ward"], req.action["staff_count"])
    return {
        "observation": {"wards": engine.wards, "pressure": engine.pressure},
        "reward": 100 if res == "Success" else -50,
        "terminated": engine.pressure <= 0,
        "info": {"log": res, "pressure": engine.pressure}
    }

# --- 3. THE UI (Aesthetic & Functional) ---
def get_plot_data():
    # Format data for BarPlot
    df_wards = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()])
    # Format data for LinePlot
    df_trend = pd.DataFrame(engine.pressure_trend)
    return df_wards, df_trend, engine.pressure, "\n".join(engine.history)

with gr.Blocks(theme=gr.themes.Default(primary_hue="blue", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏥 HospitRL Dashboard: Advanced Command Center")
    
    with gr.Row():
        with gr.Column(scale=1):
            pressure_gauge = gr.Number(label="Hospital Stress Level (%)", value=50, interactive=False)
            status_ind = gr.HighlightedText(value=[("SYSTEM ACTIVE", "OK")], color_map={"OK": "green"})
            
        with gr.Column(scale=2):
            # Replacing JSON with a proper Bar Plot for better visuals
            ward_plot = gr.BarPlot(
                value=pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()]),
                x="Ward", y="Staff", title="Staff Registry Distribution",
                vertical=False, width=500, height=250, tooltip=["Ward", "Staff"]
            )

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🕹️ Action Console")
            src_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="Source Ward", value="General Ward")
            tgt_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="Target Ward", value="Emergency Room")
            amt_slide = gr.Slider(minimum=1, maximum=5, step=1, label="Staff Count", value=1)
            with gr.Row():
                move_btn = gr.Button("Execute Reallocation", variant="primary")
                reset_btn = gr.Button("Emergency Reset", variant="stop")
        
        with gr.Column():
            gr.Markdown("### 📈 Stress Trend Analysis")
            trend_plot = gr.LinePlot(
                value=pd.DataFrame(engine.pressure_trend),
                x="Step", y="Stress", title="Pressure Optimization Curve",
                width=500, height=250
            )

    history_log = gr.Textbox(label="Clinical Activity Timeline", lines=5, placeholder="Waiting for logs...")

    # Logic functions
    def ui_move(src, tgt, amt):
        res = engine.move_staff(src, tgt, amt)
        d_ward, d_trend, press, logs = get_plot_data()
        return d_ward, d_trend, press, logs

    def ui_reset():
        engine.reset()
        d_ward, d_trend, press, logs = get_plot_data()
        return d_ward, d_trend, press, "System Reset: Values restored to baseline."

    move_btn.click(ui_move, [src_drop, tgt_drop, amt_slide], [ward_plot, trend_plot, pressure_gauge, history_log])
    reset_btn.click(ui_reset, None, [ward_plot, trend_plot, pressure_gauge, history_log])

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)