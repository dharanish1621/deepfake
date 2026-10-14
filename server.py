"""
Deepfake Video Forensics — FastAPI Backend
Handles video upload, frame extraction, and VideoMAE inference.
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
import io
import base64
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from transformers import (
    VideoMAEForVideoClassification,
    VideoMAEImageProcessor,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_ID = str(
    Path(__file__).resolve().parent / "models" / "videomae"
)
NUM_FRAMES = 16

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Deepfake Video Forensics",
    description="Deepfake detection API powered by Deepfake Video Forensics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Model loading (singleton)
# ---------------------------------------------------------------------------

_model_cache: dict = {}


def ensure_model_weights():
    """Ensure fine-tuned VideoMAE weights exist locally, downloading if absent."""
    weights_path = Path(MODEL_ID) / "model.safetensors"
    if not weights_path.exists():
        print("[setup] Model weights not found. Downloading fine-tuned VideoMAE (FaceForensics++)...")
        from huggingface_hub import hf_hub_download
        import shutil

        Path(MODEL_ID).mkdir(parents=True, exist_ok=True)
        downloaded = hf_hub_download(
            repo_id="Vansh180/VideoMae-ffc23-deepfake-detector",
            filename="model.safetensors",
        )
        shutil.copy(downloaded, str(weights_path))
        print("[setup] Trained model weights downloaded successfully.")


def get_model():
    """Load model, processor, and device once and cache them."""
    if not _model_cache:
        ensure_model_weights()
        device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        processor = VideoMAEImageProcessor.from_pretrained(
            MODEL_ID,
            local_files_only=True,
        )

        model = VideoMAEForVideoClassification.from_pretrained(
            MODEL_ID,
            local_files_only=True,
        )

        model = model.to(device)
        model.eval()

        _model_cache["processor"] = processor
        _model_cache["model"] = model
        _model_cache["device"] = device

    return (
        _model_cache["processor"],
        _model_cache["model"],
        _model_cache["device"],
    )


# ---------------------------------------------------------------------------
# Video processing helpers
# ---------------------------------------------------------------------------


def extract_frames(video_path: str) -> list[Image.Image]:
    """Extract NUM_FRAMES evenly spaced frames from a video file."""
    cap = cv2.VideoCapture(video_path)

    try:
        if not cap.isOpened():
            raise ValueError(
                "Could not open this video. Try an MP4 file."
            )

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frames: list[Image.Image] = []

        # If frame count is valid and positive, sample evenly across timeline
        if total >= NUM_FRAMES:
            indices = np.linspace(0, total - 1, NUM_FRAMES).astype(int)
            for index in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
                ok, frame = cap.read()
                if ok:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(Image.fromarray(frame))

        # Fallback if frame count is unreadable (common with mobile/WhatsApp VFR videos)
        if not frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            step = max(1, total // NUM_FRAMES) if total > NUM_FRAMES else 1
            frame_idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_idx % step == 0:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(Image.fromarray(frame))
                    if len(frames) == NUM_FRAMES:
                        break
                frame_idx += 1

        if not frames:
            raise ValueError("Could not extract any readable frames from the video.")

        # Pad with last frame if video is shorter than NUM_FRAMES
        while len(frames) < NUM_FRAMES:
            frames.append(frames[-1])

        return frames[:NUM_FRAMES]

    finally:
        cap.release()


def frames_to_base64(frames: list[Image.Image]) -> list[str]:
    """Convert PIL frames to base64-encoded JPEG strings."""
    encoded = []
    for frame in frames:
        buf = io.BytesIO()
        if frame.mode != "RGB":
            frame = frame.convert("RGB")
        frame.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        encoded.append(f"data:image/jpeg;base64,{b64}")
    return encoded


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Server health and device info."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return {
        "status": "ok",
        "device": device,
        "model_path": MODEL_ID,
        "model_ready": bool(_model_cache),
    }




@spaces.GPU
def run_inference(processor, model, device, frames):
    """Run model forward pass on GPU when available."""
    inputs = processor(frames, return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        outputs = model(**inputs)
        probabilities = torch.softmax(outputs.logits, dim=-1)[0]
    return probabilities


@app.post("/api/analyze")
async def analyze_video(file: UploadFile = File(...)):
    """Upload a video and get deepfake classification results."""

    # Validate file type
    allowed = {".mp4", ".mov", ".webm"}
    ext = os.path.splitext(file.filename or "video.mp4")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Use MP4, MOV, or WebM.",
        )

    temp_path = None

    try:
        # Create temporary file using mkstemp to avoid Windows file-locking conflicts (Errno 22)
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, "wb") as tmp:
            while chunk := await file.read(1024 * 1024):
                tmp.write(chunk)

        # Load model and run inference
        processor, model, device = get_model()
        frames = extract_frames(temp_path)
        probabilities = run_inference(processor, model, device, frames)

        # Build results
        results = []
        for index, score in enumerate(probabilities.tolist()):
            label = model.config.id2label.get(
                index, f"Class {index}"
            )
            results.append({
                "label": str(label),
                "score": round(float(score), 4),
            })

        results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        # Encode sampled frames as base64 for the frontend
        frame_images = frames_to_base64(frames)

        return {
            "results": results,
            "frames": frame_images,
            "device": str(device),
            "frames_sampled": len(frames),
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}",
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass



# ---------------------------------------------------------------------------
# Serve frontend & static assets (with no-cache headers for instant updates)
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
DIST_DIR = Path(__file__).resolve().parent / "dist"

# Ensure directories exist safely at runtime
try:
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


@app.middleware("http")
async def add_cache_control_header(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/" or request.url.path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/", tags=["General"])
async def root():
    """Root endpoint: serves index.html if available, or API health status."""
    for candidate in [DIST_DIR / "index.html", FRONTEND_DIR / "index.html"]:
        if candidate.is_file():
            return FileResponse(str(candidate), headers={"Cache-Control": "no-cache"})
    return {
        "status": "online",
        "service": "Deepfake Video Analysis API",
        "version": "1.0.0",
        "health": "/health",
        "docs": "/docs",
        "model_ready": bool(_model_cache),
    }


@app.get("/style.css", include_in_schema=False)
async def get_css():
    file_path = FRONTEND_DIR / "style.css"
    if file_path.is_file():
        return FileResponse(str(file_path), media_type="text/css")
    raise HTTPException(status_code=404)


@app.get("/app.js", include_in_schema=False)
async def get_js():
    file_path = FRONTEND_DIR / "app.js"
    if file_path.is_file():
        return FileResponse(str(file_path), media_type="application/javascript")
    raise HTTPException(status_code=404)


@app.get("/ai-robot.png", include_in_schema=False)
async def get_robot():
    file_path = FRONTEND_DIR / "ai-robot.png"
    if file_path.is_file():
        return FileResponse(str(file_path), media_type="image/png")
    raise HTTPException(status_code=404)


def mount_static_and_root(target_app=app):
    """Mount frontend static files safely without crashing if directories are missing."""
    target_app.router.routes = [
        r for r in target_app.router.routes
        if getattr(r, "name", None) not in ("root_frontend", "static", "assets")
    ]
    try:
        if FRONTEND_DIR.is_dir() and any(FRONTEND_DIR.iterdir()):
            target_app.mount(
                "/static",
                StaticFiles(directory=str(FRONTEND_DIR)),
                name="static",
            )
    except Exception as exc:
        pass

    try:
        assets_dir = DIST_DIR / "assets"
        if assets_dir.is_dir():
            target_app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="assets",
            )
    except Exception as exc:
        pass

    return target_app


mount_static_and_root(app)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("server:app", host=host, port=port, reload=False)


