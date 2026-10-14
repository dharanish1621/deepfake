# Stage 1: Build Vite frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY frontend/ ./frontend/
COPY vite.config.js ./
RUN npx vite build

# Stage 2: Python runtime with PyTorch and VideoMAE
FROM python:3.11-slim

# Create non-root user (required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

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

# Application source and compiled frontend
COPY server.py app.py ./
COPY models/ ./models/
COPY frontend/ ./frontend/
COPY --from=frontend-builder /app/dist ./dist

# Ensure permissions
RUN chown -R user:user /app /home/user
USER user

# Hugging Face default port
EXPOSE 7860

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
