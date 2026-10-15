FROM python:3.11-slim

# Create non-root user (required by Hugging Face Spaces & security best practices)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_VERBOSITY=error \
    HF_HUB_ENABLE_HF_TRANSFER=0

# Optional HF Token for higher rate limits (passed via Railway/Docker build args or env)
ARG HF_TOKEN=""
ENV HF_TOKEN=${HF_TOKEN}

WORKDIR /app

# System dependencies for OpenCV & video frame processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir opencv-python-headless

# Pre-create all application directories
RUN mkdir -p /app/frontend /app/dist /app/models/videomae

# Application source and static frontend
COPY server.py app.py ./
COPY models/ ./models/
COPY frontend/ ./frontend/

# Pre-download fine-tuned VideoMAE model weights directly into target directory (no duplicate cache)
RUN python -c "import os; from huggingface_hub import hf_hub_download; token = os.environ.get('HF_TOKEN') or None; hf_hub_download(repo_id='Vansh180/VideoMae-ffc23-deepfake-detector', filename='model.safetensors', local_dir='/app/models/videomae', token=token)" && \
    rm -rf /root/.cache/huggingface

# Ensure permissions
RUN chown -R user:user /app /home/user
USER user

# Clean single exposed port for Railway routing
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

