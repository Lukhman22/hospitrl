"""
HospitRL — Staff Scheduling System
All OpenEnv-required endpoints: /reset, /step, /state, /health
"""
import json
import pandas as pd
import gradio as gr
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn

# --- FIXED IMPORTS ---
from .models import Action, StepResponse, ResetResponse
from .environment import HospitalEnv, TASK_CONFIGS, _squash

# --------------------------------------------------------------------------- #
# Shared engine instance (one per process)
# --------------------------------------------------------------------------- #
engine = HospitalEnv()
app = FastAPI(title="HospitRL", version="1.0.0")


# --------------------------------------------------------------------------- #
# OpenEnv-required REST endpoints
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


@app.get("/get_tasks") # Added for list_tasks functionality
def list_tasks():
    return {
        "tasks": [
            {"id": tid, "difficulty": cfg_to_difficulty(tid), "description": TASK_CONFIGS[tid]["description"]}
            for tid in TASK_CONFIGS
        ]
    }


def cfg_to_difficulty(task_id: str) -> str:
    return {"easy_balance": "easy", "medium_surge": "medium", "hard_optimization": "hard"}.get(task_id, "unknown")


# --------------------------------------------------------------------------- #
# Gradio dashboard
# --------------------------------------------------------------------------- #

CSS = """
.metric-box { border-radius: 10px; padding: 12px; text-align: center; }
"""

def build_df():
    return pd.DataFrame([{"Ward": k, "Staff": v} for k, v in engine._wards.items()])

def do_reset(task_id):
    engine.reset(task_id)
    df = build_df()
    return (
        df,
        f"{engine._pressure:.1f}%",
        f"${engine._budget:.0f}",
        f"{engine._burnout:.1f}%",
        f"Step 0/{engine._max_steps}",
        "Environment reset. Select wards and commit an action.",
        _make_gauge_html(engine._pressure, engine._burnout, engine._budget),
    )

def do_step(src, tgt, qty):
    if src == tgt:
        return (
            build_df(),
            f"{engine._pressure:.1f}%",
            f"${engine._budget:.0f}",
            f"{engine._burnout:.1f}%",
            f"Step {engine._steps}/{engine._max_steps}",
            "Error: source and target must be different.",
            _make_gauge_html(engine._pressure, engine._burnout, engine._budget),
        )

    # 🔥 CAPTURE BEFORE STATE
    before = engine._wards.copy()

    # 🔥 EXECUTE ACTION (UNCHANGED LOGIC)
    action = Action(source_ward=src, target_ward=tgt, staff_count=int(qty))
    obs, reward, done, info = engine.step(action)

    df = build_df()

    # 🔥 CAPTURE AFTER STATE
    after = engine._wards

    # 🔥 MOVEMENT CALCULATION
    movement_log = []
    for ward in before:
        diff = after[ward] - before[ward]
        if diff != 0:
            sign = "+" if diff > 0 else ""
            movement_log.append(
                f"{ward}: {before[ward]} → {after[ward]} ({sign}{diff})"
            )

    movement_text = "\n".join(movement_log)

   # 🔥 SMART REASONING BASED ON REAL STATE
reasons = []

gw = after.get("General Ward", 0)
er = after.get("Emergency Room", 0)
icu = after.get("Intensive Care", 0)

# pressure-based
if obs.pressure > 70:
    reasons.append("High pressure → urgent redistribution")
elif obs.pressure < 30:
    reasons.append("System stabilizing")

# source-based logic
if src == "General Ward" and gw > 10:
    reasons.append("General Ward has surplus staff")
elif src == "Emergency Room" and er > 10:
    reasons.append("Emergency Room overloaded")
elif src == "Intensive Care" and icu > 10:
    reasons.append("ICU redistribution needed")

# target-based logic
if tgt == "Emergency Room":
    reasons.append("Emergency Room prioritized")
elif tgt == "Intensive Care":
    reasons.append("ICU prioritized")

# transfer size logic
if int(qty) >= 15:
    reasons.append("Large transfer for faster impact")

reason_text = " | ".join(reasons) if reasons else "Balanced redistribution"

    reason_text = " | ".join(reasons)

    # 🔥 FINAL LOG (ENHANCED)
    if info.get("error"):
        log = f"Action failed: {info['error']}"
    elif info.get("surged"):
        log = f"SURGE EVENT at step {engine._steps}! Reward: {reward:.4f}"
    else:
        log = f"""
🧠 AI Decision Summary

log = f"""
### 🎯 Action
{src} → {tgt} ({int(qty)} staff)

---

### 📊 Movement
{movement_text if movement_text else "No change"}

---

### 📉 Impact
- Pressure: {obs.pressure:.1f}%
- Burnout: {obs.burnout_index:.1f}%
- Reward: {reward:.4f}

---

### 🧠 Reasoning
{reason_text}
"""

    if done:
        log += "\n\n🏁 Episode complete. Reset to start a new episode."

    status = f"Reward: {reward:.4f} | {'DONE' if done else f'Step {engine._steps}/{engine._max_steps}'}"

    return (
        df,
        f"{obs.pressure:.1f}%",
        f"${obs.remaining_budget:.0f}",
        f"{obs.burnout_index:.1f}%",
        status,
        log,
        _make_gauge_html(obs.pressure, obs.burnout_index, obs.remaining_budget),
    )

def _make_gauge_html(pressure, burnout, budget):
    def bar(val, max_val, color, label):
        pct = min(100, val / max_val * 100)
        return f"""
        <div style='margin-bottom:10px'>
          <div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px'>
            <span>{label}</span><span>{val:.1f}</span>
          </div>
          <div style='background:#e5e7eb;border-radius:6px;height:10px'>
            <div style='background:{color};width:{pct:.1f}%;height:10px;border-radius:6px;transition:width 0.4s'></div>
          </div>
        </div>"""
    return f"""<div style='font-family:sans-serif;padding:8px'>
        {bar(pressure, 100, '#ef4444', 'Pressure')}
        {bar(burnout, 100, '#f97316', 'Burnout')}
        {bar(5000 - budget, 5000, '#6366f1', 'Budget Used')}
    </div>"""
CSS = """
body { background: #0b1220; }
.gradio-container {
  background: linear-gradient(135deg,#0b1220,#111827);
  color: #e5e7eb;
}

h1,h2,h3 { color:#f9fafb; }

.card {
  background:#111827;
  border:1px solid #1f2937;
  border-radius:14px;
  padding:14px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}

.metric {
  font-size:14px; opacity:0.8;
}
.metric-val {
  font-size:26px; font-weight:700;
}

.log-box {
  background:#020617;
  border:1px solid #1f2937;
  border-radius:12px;
  padding:12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

button {
  border-radius:10px !important;
  font-weight:600 !important;
  transition: all .15s ease-in-out !important;
}
button:hover { transform: translateY(-1px) scale(1.02); }
"""
with gr.Blocks(title="HospitRL — Hospital RL Environment", css=CSS) as demo:
    gr.Markdown("""
# 🏥 HospitRL — Clinical Resource Management RL Environment
**Scaler OpenEnv Hackathon** · Real-world hospital ward staffing optimization
> Move staff between wards to reduce patient pressure while managing budget and burnout.
""")

    with gr.Row():
        with gr.Column(scale=3):
            ward_chart = gr.BarPlot(
                value=build_df(), x="Ward", y="Staff",
                title="Live Staff Distribution", y_lim=[0, 100], height=280,
            )
        with gr.Column(scale=2):
            gauge_html = gr.HTML(value=_make_gauge_html(engine._pressure, engine._burnout, engine._budget))
            with gr.Row():
                pressure_lbl = gr.Label(value=f"{engine._pressure:.1f}%", label="Pressure")
                budget_lbl   = gr.Label(value=f"${engine._budget:.0f}", label="Budget")
                burnout_lbl  = gr.Label(value=f"{engine._burnout:.1f}%", label="Burnout")

    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Reallocation Console")
            task_sel = gr.Dropdown(
                choices=["easy_balance", "medium_surge", "hard_optimization"],
                value="easy_balance", label="Select Task"
            )
            reset_btn = gr.Button("Reset Environment", variant="secondary")
            with gr.Row():
                src_dd = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="From Ward", value="General Ward")
                tgt_dd = gr.Dropdown(["General Ward", "Emergency Room", "Intensive Care"], label="To Ward", value="Emergency Room")
            qty_sl = gr.Slider(1, 30, value=10, step=1, label="Staff Count")
            step_btn = gr.Button("Commit Action", variant="primary")
        with gr.Column(scale=1):
            gr.Markdown("### Task Briefing")
            gr.Markdown("""
| Task | Difficulty | Goal |
|------|-----------|------|
| `easy_balance` | Easy | Pressure → 30% |
| `medium_surge` | Medium | Survive midday rush |
| `hard_optimization` | Hard | Crisis + tight budget |

**Reward = 1 − pressure** weighted by budget, burnout, step efficiency.
All scores strictly in **(0, 1)**.
""")

    with gr.Row():
        step_lbl = gr.Label(value=f"Step 0/{engine._max_steps}", label="Progress")
        event_log = gr.Textbox(label="Event Log", lines=4, value="Select a task and reset to begin.")

    outputs = [ward_chart, pressure_lbl, budget_lbl, burnout_lbl, step_lbl, event_log, gauge_html]

    reset_btn.click(do_reset, inputs=[task_sel], outputs=outputs)
    step_btn.click(do_step, inputs=[src_dd, tgt_dd, qty_sl], outputs=outputs)

    gr.Markdown("""---
### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/reset?task_id=easy_balance` | Reset environment |
| `POST` | `/step` | Execute action |
| `GET` | `/state` | Full state snapshot |
| `GET` | `/get_tasks` | List all tasks |
""")


app = gr.mount_gradio_app(app, demo, path="/")


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()