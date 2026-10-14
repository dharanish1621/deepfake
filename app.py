"""
Deepfake Video Forensics — Hugging Face Space & Production Entrypoint
Serves the custom glassmorphic dark-mode web application at `/`
with ZeroGPU hardware acceleration, powered by VideoMAE Spatio-Temporal Forensics.
"""

try:
    import spaces
except ImportError:
    class spaces:
        @staticmethod
        def GPU(func=None, **kwargs):
            if func is None:
                return lambda f: f
            return func

import os
import sys
from pathlib import Path
import gradio as gr
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.routing import Route

# Ensure local imports resolve
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from server import (
    analyze_video,
    health_check,
    run_inference,
    get_model,
    extract_frames,
    MODEL_ID,
    NUM_FRAMES,
)

FRONTEND_DIR = BASE_DIR / "frontend"

# ---------------------------------------------------------------------------
# Hugging Face ZeroGPU inference handler
# ---------------------------------------------------------------------------
@spaces.GPU(duration=120)
def predict_video(video_path):
    """ZeroGPU inference handler connected directly to Gradio queue."""
    if not video_path:
        return None, "⚠️ Please upload or record a video first.", []

    try:
        processor, model, device = get_model()
        frames = extract_frames(video_path)
        if not frames:
            return None, "❌ Could not extract readable frames.", []

        probabilities = run_inference(processor, model, device, frames)

        confidences = {}
        for idx, score in enumerate(probabilities.tolist()):
            label = model.config.id2label.get(idx, f"Class {idx}").upper()
            confidences[label] = float(score)

        fake_score = confidences.get("FAKE", 0.0)
        real_score = confidences.get("REAL", 0.0)

        if fake_score >= 0.5:
            verdict = f"🚨 **SYNTHETIC / DEEPFAKE DETECTED** ({fake_score * 100:.2f}%)"
        else:
            verdict = f"✅ **AUTHENTIC / REAL MEDIA** ({real_score * 100:.2f}%)"

        report = f"""
### Forensic Verdict Report
{verdict}

* **Inference Device**: `{str(device).upper()}`
* **Frames Sampled**: `{len(frames)} frames`
* **Custom Studio**: The full interactive dark-mode dashboard is live at [/](/)
        """
        return confidences, report, frames

    except Exception as e:
        return None, f"❌ Error: {str(e)}", []


# ---------------------------------------------------------------------------
# Gradio Blocks setup (Satisfies ZeroGPU startup & provides backend API)
# ---------------------------------------------------------------------------
with gr.Blocks(title="Deepfake Video Forensics Backend") as demo:
    gr.Markdown(
        """
        # 🛡️ Deepfake Video Forensics — Engine Backend
        > **Primary Interface:** The full custom glassmorphic dashboard is actively served at **[Root Studio (/)](/)**.
        """
    )
    with gr.Row():
        with gr.Column():
            video_in = gr.Video(label="Input Video", sources=["upload"])
            btn_run = gr.Button("🔍 Run Forensic Check", variant="primary")
        with gr.Column():
            lbl_out = gr.Label(label="Authenticity Probability", num_top_classes=2)
            rep_out = gr.Markdown()
    with gr.Row():
        gal_out = gr.Gallery(label="Sampled Timeline Frames", columns=8, rows=2, height=240)

    btn_run.click(
        fn=predict_video,
        inputs=[video_in],
        outputs=[lbl_out, rep_out, gal_out],
    )

# Enable queue for ZeroGPU event routing
demo.queue()

# ---------------------------------------------------------------------------
# Mount FastAPI backend endpoints onto Gradio's internal FastAPI app
# ---------------------------------------------------------------------------
demo.app.add_api_route("/api/health", health_check, methods=["GET"])
demo.app.add_api_route("/api/analyze", analyze_video, methods=["POST"])

# Mount static asset routes
if FRONTEND_DIR.exists():
    demo.app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="custom_static")

async def serve_index(request):
    return FileResponse(str(FRONTEND_DIR / "index.html"), headers={"Cache-Control": "no-cache"})

async def serve_css(request):
    return FileResponse(str(FRONTEND_DIR / "style.css"), headers={"Cache-Control": "no-cache"})

async def serve_js(request):
    return FileResponse(str(FRONTEND_DIR / "app.js"), headers={"Cache-Control": "no-cache"})

async def serve_robot(request):
    return FileResponse(str(FRONTEND_DIR / "ai-robot.png"))

# Prepend routes to ensure custom frontend takes priority at /
demo.app.router.routes.insert(0, Route("/", endpoint=serve_index, methods=["GET"]))
demo.app.router.routes.insert(1, Route("/style.css", endpoint=serve_css, methods=["GET"]))
demo.app.router.routes.insert(2, Route("/app.js", endpoint=serve_js, methods=["GET"]))
demo.app.router.routes.insert(3, Route("/ai-robot.png", endpoint=serve_robot, methods=["GET"]))

# Expose app for ASGI compatibility
app = demo.app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[app] Launching Deepfake Video Forensics with ZeroGPU on http://{host}:{port}")
    demo.launch(server_name=host, server_port=port, ssr_mode=False)
