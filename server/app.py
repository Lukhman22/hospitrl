import gradio as gr
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
import uvicorn

# --- 1. THE LOGIC ENGINE (100 Staff Scale) ---
class HospitalEngine:
    def __init__(self):
        # Starting with a realistic 100-staff baseline
        self.wards = {"General Ward": 50, "Emergency Room": 25, "Intensive Care": 25}
        self.pressure = 100.0
        self.history = []import gradio as gr
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
        self.last_move_details = "System Initialized. Status: CRITICAL."

    def reset(self, g_staff=50, e_staff=25, i_staff=25):
        self.wards = {"General Ward": g_staff, "Emergency Room": e_staff, "Intensive Care": i_staff}
        self.pressure = 100.0
        self.history = [f"Hospital Rebooted: {sum(self.wards.values())} staff online."]
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.last_move_details = "System Reset to baseline."
        return self.wards, self.pressure

    def trigger_surge(self):
        # Spikes the pressure
        self.pressure = min(100.0, self.pressure + 30.0)
        self.history.insert(0, "🚨 EMERGENCY SURGE: Massive patient influx detected!")
        self.update_trend()
        return "Surge Processed"

    def move_staff(self, source, target, count):
        if source == target: return "Error: Select different wards."
        if self.wards[source] < count: return f"Error: Insufficient staff in {source}."
        
        before_src, before_tgt = self.wards[source], self.wards[target]
        self.wards[source] -= count
        self.wards[target] += count
        
        # High-Impact Logic
        reduction = 25.0 if target in ["Emergency Room", "Intensive Care"] else 10.0
        self.pressure = max(0.0, self.pressure - reduction)
        
        self.last_move_details = (
            f"🔄 TRANSFER LOGIC:\n"
            f"• {source}: {before_src} - {count} = {self.wards[source]}\n"
            f"• {target}: {before_tgt} + {count} = {self.wards[target]}"
        )
        self.update_trend()
        self.history.insert(0, f"Optimized {target}. Stress reduced.")
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

# --- 2. UI SYNC LOGIC ---
def sync_ui(custom_msg=None):
    df_wards = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()])
    df_trend = pd.DataFrame(engine.pressure_trend)
    
    if engine.pressure >= 70:
        status = [("CRITICAL OVERLOAD", "loss")]
    elif engine.pressure > 30:
        status = [("ACTIVE SURGE", "pending")]
    else:
        status = [("STABLE OPERATIONS", "pro")]
    
    # Show error messages or movement details
    display_msg = custom_msg if custom_msg else engine.last_move_details
    return df_wards, df_trend, engine.pressure, status, display_msg, "\n".join(engine.history)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 HospitRL: Strategic Command Center")
    
    with gr.Row():
        with gr.Column(scale=1):
            stress_num = gr.Number(label="System Stress (%)", value=100.0)
            status_box = gr.HighlightedText(value=[("CRITICAL OVERLOAD", "loss")])
            surge_btn = gr.Button("🚨 Trigger Emergency Surge", variant="stop")
            
        with gr.Column(scale=2):
            ward_chart = gr.BarPlot(
                value=pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()]), 
                x="Ward", y="Staff", title="Global Staff Registry (Capacity: 100)",
                y_lim=[0, 100]
            )

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🕹️ Resource Controls")
            src_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="From Ward", value="General Ward")
            tgt_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="To Ward", value="Emergency Room")
            amt_input = gr.Number(label="Staff to Reallocate", value=10, precision=0)
            move_btn = gr.Button("Confirm Reallocation", variant="primary")
            
        with gr.Column():
            math_display = gr.Textbox(label="Movement Logic Breakdown", lines=3, interactive=False)
            trend_line = gr.LinePlot(value=pd.DataFrame(engine.pressure_trend), x="Step", y="Stress", title="Pressure Optimization Curve")

    log_display = gr.Textbox(label="Clinical Activity Timeline", lines=3)

    # --- THE SAFETY WRAPPERS (No more 'or' logic crashes!) ---
    def handle_move(s, t, a):
        result = engine.move_staff(s, t, a)
        if result.startswith("Error"):
            return sync_ui(custom_msg=result)
        return sync_ui()

    def handle_surge_event():
        engine.trigger_surge()
        return sync_ui() # This guarantees 6 outputs are returned

    move_btn.click(handle_move, [src_drop, tgt_drop, amt_input], [ward_chart, trend_line, stress_num, status_box, math_display, log_display])
    surge_btn.click(handle_surge_event, None, [ward_chart, trend_line, stress_num, status_box, math_display, log_display])

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.last_move_details = "System Initialized. Status: CRITICAL."

    def reset(self, g_staff=50, e_staff=25, i_staff=25):
        self.wards = {"General Ward": g_staff, "Emergency Room": e_staff, "Intensive Care": i_staff}
        self.pressure = 100.0
        self.history = [f"Hospital Rebooted: {sum(self.wards.values())} staff online."]
        self.pressure_trend = [{"Step": 0, "Stress": 100.0}]
        self.last_move_details = "System Reset to baseline."
        return self.wards, self.pressure

    def trigger_surge(self):
        # Spikes the pressure to demonstrate crisis management
        self.pressure = min(100.0, self.pressure + 30.0)
        self.history.insert(0, "🚨 EMERGENCY SURGE: Massive patient influx detected!")
        self.update_trend()
        return self.pressure

    def move_staff(self, source, target, count):
        if source == target: return "Error: Select different wards."
        if self.wards[source] < count: return f"Error: Insufficient staff in {source}."
        
        # Capture Math for the Breakdown Box
        before_src, before_tgt = self.wards[source], self.wards[target]
        
        # Execute Reallocation
        self.wards[source] -= count
        self.wards[target] += count
        
        # --- LOGIC: High-Impact vs Low-Impact moves ---
        if target in ["Emergency Room", "Intensive Care"]:
            reduction = 25.0  # High Impact Move
        else:
            reduction = 10.0  # Maintenance Move
            
        self.pressure = max(0.0, self.pressure - reduction)
        
        # Format the Math Breakdown logic you requested
        self.last_move_details = (
            f"🔄 TRANSFER LOGIC:\n"
            f"• {source}: {before_src} - {count} = {self.wards[source]}\n"
            f"• {target}: {before_tgt} + {count} = {self.wards[target]}"
        )
        
        self.update_trend()
        self.history.insert(0, f"Optimized {target}. Total Hospital Headcount: {sum(self.wards.values())}")
        return "Success"

    def update_trend(self):
        self.pressure_trend.append({"Step": len(self.pressure_trend), "Stress": self.pressure})

engine = HospitalEngine()
app = FastAPI()

# --- API ENDPOINTS (For Scaler Grader) ---
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

# --- 2. UI SYNC LOGIC (Safety-Wrapped) ---
def sync_ui(error_msg=None):
    df_wards = pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()])
    df_trend = pd.DataFrame(engine.pressure_trend)
    
    # Color Thresholds
    if engine.pressure >= 70:
        status = [("CRITICAL OVERLOAD", "loss")] # Red
    elif engine.pressure > 30:
        status = [("ACTIVE SURGE", "pending")]   # Yellow
    else:
        status = [("STABLE OPERATIONS", "pro")]   # Green
    
    math_val = error_msg if error_msg else engine.last_move_details
    return df_wards, df_trend, engine.pressure, status, math_val, "\n".join(engine.history)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 HospitRL: Strategic Command Center")
    
    with gr.Row():
        with gr.Column(scale=1):
            stress_num = gr.Number(label="System Stress (%)", value=100.0)
            status_box = gr.HighlightedText(value=[("CRITICAL OVERLOAD", "loss")])
            surge_btn = gr.Button("🚨 Trigger Emergency Surge", variant="stop")
            
        with gr.Column(scale=2):
            ward_chart = gr.BarPlot(
                value=pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine.wards.items()]), 
                x="Ward", y="Staff", title="Global Staff Registry (Capacity: 100)",
                y_lim=[0, 100]
            )

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🕹️ Resource Controls")
            src_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="From Ward", value="General Ward")
            tgt_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="To Ward", value="Emergency Room")
            amt_input = gr.Number(label="Staff to Reallocate", value=10, precision=0)
            move_btn = gr.Button("Confirm Reallocation", variant="primary")
            
        with gr.Column():
            # This is the "Before -> After" math breakdown you asked for
            math_display = gr.Textbox(label="Movement Logic Breakdown", lines=3, interactive=False)
            trend_line = gr.LinePlot(value=pd.DataFrame(engine.pressure_trend), x="Step", y="Stress", title="Pressure Optimization Curve")

    log_display = gr.Textbox(label="Clinical Activity Timeline", lines=3)

    # Event Handlers
    def handle_move(s, t, a):
        result = engine.move_staff(s, t, a)
        if result.startswith("Error"):
            return sync_ui(error_msg=result)
        return sync_ui()

    move_btn.click(handle_move, [src_drop, tgt_drop, amt_input], [ward_chart, trend_line, stress_num, status_box, math_display, log_display])
    surge_btn.click(lambda: engine.trigger_surge() or sync_ui(), None, [ward_chart, trend_line, stress_num, status_box, math_display, log_display])

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)