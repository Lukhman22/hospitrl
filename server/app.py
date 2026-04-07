import gradio as gr
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uvicorn

# --- 1. THE LOGIC ENGINE (Enhanced Functionality) ---
class HospitalEngine:
    def __init__(self):
        self.wards = {"General Ward": 10, "Emergency Room": 5, "Intensive Care": 8}
        self.pressure = 50
        self.history = []

    def reset(self):
        self.__init__()
        return self.wards, self.pressure

    def move_staff(self, source, target, count):
        if source not in self.wards or target not in self.wards:
            return "Error: Invalid Ward ID"
        if self.wards[source] < count:
            return f"Error: Only {self.wards[source]} staff available in {source}"
        
        self.wards[source] -= count
        self.wards[target] += count
        # Logic: Moving staff to ER or ICU reduces pressure faster
        reduction = 10 if target in ["Emergency Room", "Intensive Care"] else 5
        self.pressure = max(0, self.pressure - reduction)
        self.history.append(f"Moved {count} from {source} to {target}")
        return f"Successfully reallocated {count} staff to {target}."

engine = HospitalEngine()

# --- 2. THE API (For the Grader) ---
app = FastAPI()

class ActionRequest(BaseModel):
    action: Dict # Expecting {"source_ward": str, "target_ward": str, "staff_count": int}

@app.post("/reset")
def api_reset():
    wards, press = engine.reset()
    return {"observation": {"wards": wards, "pressure": press}}

@app.post("/step")
def api_step(req: ActionRequest):
    res = engine.move_staff(req.action["source_ward"], req.action["target_ward"], req.action["staff_count"])
    return {
        "observation": {"wards": engine.wards, "pressure": engine.pressure},
        "reward": 100 if "Success" in res else -50,
        "terminated": engine.pressure <= 0,
        "info": {"log": res, "pressure": engine.pressure}
    }

# --- 3. THE "MOGUL" UI (For the Humans) ---
with gr.Blocks(theme=gr.themes.Soft(primary_hue="cyan", secondary_hue="slate")) as demo:
    gr.Markdown("# 🏥 HospitRL Dashboard\n*Real-time Resource & Surge Management System*")
    
    with gr.Row():
        with gr.Column(scale=1):
            pressure_val = gr.Number(label="Hospital Stress Level (%)", value=engine.pressure, interactive=False)
            status_light = gr.HighlightedText(value=[("SYSTEM ONLINE", "OK")], color_map={"OK": "green"})
            
        with gr.Column(scale=2):
            ward_chart = gr.JSON(label="Live Staff Registry", value=engine.wards)

    with gr.Group():
        gr.Markdown("### 🕹️ Manual Resource Allocation")
        with gr.Row():
            src_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="Source Ward")
            tgt_drop = gr.Dropdown(choices=list(engine.wards.keys()), label="Target Ward")
            amt_slide = gr.Slider(minimum=1, maximum=5, step=1, label="Staff to Reallocate")
        
        move_btn = gr.Button("Execute Reallocation", variant="primary")
        reset_btn = gr.Button("Emergency System Reset", variant="stop")
        output_msg = gr.Textbox(label="System Response")

    # Button Functionality
    def manual_move(src, tgt, amt):
        msg = engine.move_staff(src, tgt, amt)
        return engine.pressure, engine.wards, msg

    def manual_reset():
        w, p = engine.reset()
        return p, w, "System Initialized."

    move_btn.click(manual_move, [src_drop, tgt_drop, amt_slide], [pressure_val, ward_chart, output_msg])
    reset_btn.click(manual_reset, None, [pressure_val, ward_chart, output_msg])

# Mount Gradio to FastAPI
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)