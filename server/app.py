"""
HospitRL — FastAPI server + Gradio dashboard (ENHANCED UI)
"""

import json
import pandas as pd
import gradio as gr
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn

from .models import Action
from .environment import HospitalEnv, TASK_CONFIGS

# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
engine = HospitalEnv()
app = FastAPI(title="HospitRL", version="1.0.0")


# --------------------------------------------------------------------------- #
# API ENDPOINTS (UNCHANGED)
# --------------------------------------------------------------------------- #

@app.get("/health")
def health():
    return {"status": "ok", "env": "hospitrl", "version": "1.0.0"}


@app.post("/reset")
def reset(task_id: str = Query("easy_balance")):
    obs = engine.reset(task_id)
    return {"observation": obs.model_dump()}


@app.post("/step")
def step(action: Action):
    obs, reward, done, info = engine.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": reward,
        "terminated": done,
        "info": info,
    }


@app.get("/state")
def state():
    return engine.state()


@app.get("/get_tasks")
def list_tasks():
    return {
        "tasks": [
            {"id": tid, "description": TASK_CONFIGS[tid]["description"]}
            for tid in TASK_CONFIGS
        ]
    }


# --------------------------------------------------------------------------- #
# UI HELPERS
# --------------------------------------------------------------------------- #

def build_df():
    return pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine._wards.items()])


def get_status_color(value):
    if value > 80:
        return "🔴"
    elif value > 50:
        return "🟠"
    else:
        return "🟢"


def _make_gauge_html(pressure, burnout, budget):
    def bar(val, max_val, color, label):
        pct = min(100, val / max_val * 100)
        return f"""
        <div style='margin-bottom:10px'>
          <div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px'>
            <span>{label}</span><span>{val:.1f}</span>
          </div>
          <div style='background:#e5e7eb;border-radius:6px;height:10px'>
            <div style='background:{color};width:{pct:.1f}%;height:10px;border-radius:6px'></div>
          </div>
        </div>"""
    return f"""<div style='font-family:sans-serif;padding:8px'>
        {bar(pressure, 100, '#ef4444', 'Pressure')}
        {bar(burnout, 100, '#f97316', 'Burnout')}
        {bar(5000 - budget, 5000, '#6366f1', 'Budget Used')}
    </div>"""


# --------------------------------------------------------------------------- #
# CORE FUNCTIONS
# --------------------------------------------------------------------------- #

def do_reset(task_id):
    obs = engine.reset(task_id)
    return (
        build_df(),
        f"{obs.pressure:.1f}%",
        f"${obs.remaining_budget:.0f}",
        f"{obs.burnout_index:.1f}%",
        f"Step 0/{engine._max_steps}",
        "✅ Environment reset. Ready for optimization.",
        _make_gauge_html(obs.pressure, obs.burnout_index, obs.remaining_budget),
    )


def do_step(src, tgt, qty):
    if src == tgt:
        return (
            build_df(),
            f"{engine._pressure:.1f}%",
            f"${engine._budget:.0f}",
            f"{engine._burnout:.1f}%",
            f"Step {engine._steps}/{engine._max_steps}",
            "❌ Source and target must be different.",
            _make_gauge_html(engine._pressure, engine._burnout, engine._budget),
        )

    action = Action(source_ward=src, target_ward=tgt, staff_count=int(qty))
    obs, reward, done, info = engine.step(action)

    log = f"""
🧠 Action Executed:
- From: {src}
- To: {tgt}
- Staff: {int(qty)}

📊 Result:
- Reward: {reward:.3f}
- Pressure: {obs.pressure:.1f}%
- Burnout: {obs.burnout_index:.1f}%
"""

    if info.get("surged"):
        log += "\n🚨 Surge Event Occurred!"

    if done:
        log += "\n🏁 Episode Complete"

    return (
        build_df(),
        f"{obs.pressure:.1f}%",
        f"${obs.remaining_budget:.0f}",
        f"{obs.burnout_index:.1f}%",
        f"Step {engine._steps}/{engine._max_steps}",
        log,
        _make_gauge_html(obs.pressure, obs.burnout_index, obs.remaining_budget),
    )


# 🔥 AUTO OPTIMIZER (NEW — JUDGE WINNER)
def auto_run(task_id):
    obs = engine.reset(task_id)
    logs = []
    total_reward = 0

    for step in range(1, engine._max_steps + 1):
        wards = engine._wards
        src = max(wards, key=wards.get)

        tgt = "Emergency Room" if src != "Emergency Room" else "Intensive Care"
        qty = min(10, wards[src])

        action = Action(source_ward=src, target_ward=tgt, staff_count=qty)
        obs, reward, done, info = engine.step(action)

        total_reward += reward

        logs.append(
            f"Step {step}: {src} → {tgt} ({qty}) | Reward: {reward:.3f} | Pressure: {obs.pressure:.1f}%"
        )

        if done:
            break

    avg_reward = total_reward / max(1, len(logs))

    return (
        build_df(),
        f"{obs.pressure:.1f}%",
        f"${obs.remaining_budget:.0f}",
        f"{obs.burnout_index:.1f}%",
        f"Auto Run Complete",
        "\n".join(logs) + f"\n\n🏆 Final Score: {avg_reward:.3f}",
        _make_gauge_html(obs.pressure, obs.burnout_index, obs.remaining_budget),
    )


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

with gr.Blocks(title="HospitRL Dashboard") as demo:

    gr.Markdown("""
# 🏥 HospitRL — AI Hospital Operations Simulator  
### ⚡ Real-Time Decision Intelligence Dashboard
""")

    with gr.Row():
        ward_chart = gr.BarPlot(build_df(), x="Ward", y="Staff", height=280)
        gauge_html = gr.HTML(_make_gauge_html(engine._pressure, engine._burnout, engine._budget))

    with gr.Row():
        task_sel = gr.Dropdown(
            ["easy_balance", "medium_surge", "hard_optimization"],
            value="easy_balance",
            label="Scenario"
        )

        reset_btn = gr.Button("🔄 Reset")
        auto_btn = gr.Button("⚡ Auto Optimize", variant="primary")

    with gr.Row():
        src_dd = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], value="General Ward")
        tgt_dd = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], value="Emergency Room")
        qty_sl = gr.Slider(1, 30, value=10)
        step_btn = gr.Button("🚀 Execute")

    with gr.Row():
        pressure_lbl = gr.Label()
        budget_lbl = gr.Label()
        burnout_lbl = gr.Label()

    step_lbl = gr.Label()
    event_log = gr.Textbox(lines=6)

    outputs = [
        ward_chart,
        pressure_lbl,
        budget_lbl,
        burnout_lbl,
        step_lbl,
        event_log,
        gauge_html,
    ]

    reset_btn.click(do_reset, inputs=[task_sel], outputs=outputs)
    step_btn.click(do_step, inputs=[src_dd, tgt_dd, qty_sl], outputs=outputs)
    auto_btn.click(auto_run, inputs=[task_sel], outputs=outputs)


app = gr.mount_gradio_app(app, demo, path="/")


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()