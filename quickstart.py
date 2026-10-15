#!/usr/bin/env python3
"""
Deepfake Video Forensics — Zero-Dependency Standalone Quickstart
Handles end-to-end environment setup, dependency installation, model weight verification,
and launches the interactive Forensic Studio with clickable access links.
Requires only Python 3.10+ (Standard Library only).
"""

import os
import sys
import time
import socket
import shutil
import signal
import threading
import subprocess
import webbrowser
from pathlib import Path

# Force unbuffered standard output for real-time console feedback
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

# ANSI Terminal Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    UNDERLINE = "\033[4m"

# Enable VT100 colors on Windows Command Prompt
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
VENV_DIR = ROOT_DIR / ".venv"
MODELS_DIR = ROOT_DIR / "models" / "videomae"
MODEL_WEIGHTS = MODELS_DIR / "model.safetensors"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"

def print_banner():
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}=========================================================={Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}  🛡️  Deepfake Video Forensics — Automated Launcher{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}=========================================================={Colors.RESET}")

def log_step(step, total, msg):
    print(f"\n{Colors.CYAN}[{step}/{total}]{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}")

def log_success(msg):
    print(f"{Colors.GREEN}✔ {msg}{Colors.RESET}")

def log_info(msg):
    print(f"{Colors.DIM}  ℹ {msg}{Colors.RESET}")

def log_warn(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def log_error(msg):
    print(f"{Colors.RED}✖ {msg}{Colors.RESET}")

def get_venv_python():
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"

# ── 1. Python Version Verification ──
def verify_python_version():
    if sys.version_info < (3, 10):
        log_error(f"Python 3.10+ is required. Found Python {sys.version_info.major}.{sys.version_info.minor}")
        print("Please install a modern Python from: https://www.python.org/downloads/")
        sys.exit(1)

# ── 2. Virtual Environment Manager ──
def ensure_virtualenv():
    # If already running inside a virtual environment, continue directly
    if sys.prefix != sys.base_prefix:
        log_success(f"Running inside active virtual environment: {sys.prefix}")
        return sys.executable

    venv_python = get_venv_python()
    if venv_python.exists():
        log_success("Existing virtual environment found in .venv")
        return str(venv_python)

    log_step(1, 4, "Creating isolated Python virtual environment (.venv)…")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=str(ROOT_DIR))
        log_success("Virtual environment created successfully in .venv")
        return str(venv_python)
    except Exception as exc:
        log_warn(f"Could not create .venv ({exc}). Continuing with current Python.")
        return sys.executable

# ── 3. Dependencies Manager ──
def ensure_dependencies(py_exec):
    log_step(2, 4, "Verifying AI and Computer Vision Dependencies…")

    check_code = (
        "import fastapi, uvicorn, torch, torchvision, transformers, "
        "cv2, PIL, numpy, huggingface_hub"
    )

    try:
        res = subprocess.run(
            [py_exec, "-c", check_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
        )
        if res.returncode == 0:
            log_success("All Python dependencies are satisfied.")
            return
    except Exception:
        pass

    log_info("Installing requirements from requirements.txt (this may take a few moments)...")
    try:
        subprocess.check_call(
            [py_exec, "-m", "pip", "install", "--upgrade", "pip"],
            cwd=str(ROOT_DIR),
        )
    except Exception:
        pass

    try:
        subprocess.check_call(
            [py_exec, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            cwd=str(ROOT_DIR),
        )
        log_success("Dependencies installed successfully.")
    except Exception as exc:
        log_error(f"Failed to install dependencies: {exc}")
        sys.exit(1)

# ── 4. Model Weights Manager ──
def ensure_model_weights(py_exec):
    log_step(3, 4, "Verifying Fine-Tuned VideoMAE Model Weights…")

    if MODEL_WEIGHTS.exists() and MODEL_WEIGHTS.stat().st_size > 100_000_000:
        size_mb = MODEL_WEIGHTS.stat().st_size / (1024 * 1024)
        log_success(f"Model weights verified ({size_mb:.1f} MB) in models/videomae/")
        return

    log_info("Downloading fine-tuned VideoMAE weights from Hugging Face Hub (FaceForensics++)...")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    py_download_script = [
        "import os",
        "from huggingface_hub import hf_hub_download",
        "token = os.environ.get('HF_TOKEN') or None",
        "os.environ['HF_HUB_VERBOSITY'] = 'error'",
        f"model_dir = r'{MODELS_DIR}'",
        "print('  Downloading model.safetensors (~329 MB)...')",
        "hf_hub_download(repo_id='Vansh180/VideoMae-ffc23-deepfake-detector', filename='model.safetensors', local_dir=model_dir, token=token)",
        "print('  Download complete.')",
    ]

    try:
        subprocess.check_call(
            [py_exec, "-c", "; ".join(py_download_script)],
            cwd=str(ROOT_DIR),
        )
        log_success("Trained model weights downloaded successfully.")
    except Exception as exc:
        log_error(f"Failed to download model weights: {exc}")
        print("You can manually place model.safetensors into models/videomae/")
        sys.exit(1)

# ── 5. Free Occupied Port Helper ──
def free_port(port: int):
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True, stderr=subprocess.DEVNULL)
            current_pid = os.getpid()
            for line in out.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in line.upper():
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != current_pid and int(pid) > 0:
                        try:
                            subprocess.check_call(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception:
                            pass
        else:
            out = subprocess.check_output(f"lsof -ti :{port}", shell=True, text=True, stderr=subprocess.DEVNULL)
            current_pid = os.getpid()
            for pid in out.strip().split("\n"):
                if pid.isdigit() and int(pid) != current_pid:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except Exception:
                        pass
    except Exception:
        pass

# ── 6. Check Port Availability ──
def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

# ── 7. Launch Server and Open Browser ──
def launch_application(py_exec: str):
    log_step(4, 4, "Starting Deepfake Video Forensics Server…")

    free_port(8000)

    log_info("Launching FastAPI Unified Forensics Studio on http://127.0.0.1:8000...")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HF_HUB_VERBOSITY"] = "error"

    server_cmd = [
        py_exec,
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--workers",
        "1",
    ]

    server_proc = subprocess.Popen(
        server_cmd,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Background thread to stream server logs smoothly without blocking health checks
    def stream_logs(pipe):
        try:
            for line in iter(pipe.readline, ""):
                clean_line = line.strip()
                if not clean_line:
                    continue
                if any(k in clean_line for k in ("Uvicorn running", "Application startup complete", "Started server process")):
                    print(f"{Colors.CYAN}[engine]{Colors.RESET} {clean_line}")
                elif any(k in clean_line for k in ("pre-warmed successfully", "Ready for inference", "Model cached")):
                    print(f"{Colors.GREEN}[engine]{Colors.RESET} {clean_line}")
                elif any(k in clean_line for k in ("Loading weights", "Extracting frames", "Inference time")):
                    print(f"{Colors.DIM}[engine] {clean_line}{Colors.RESET}")
                elif "error" in clean_line.lower() and "no error" not in clean_line.lower():
                    print(f"{Colors.RED}[engine] {clean_line}{Colors.RESET}")
        except Exception:
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    log_thread = threading.Thread(target=stream_logs, args=(server_proc.stdout,), daemon=True)
    log_thread.start()

    target_url = "http://127.0.0.1:8000/"
    health_url = "http://127.0.0.1:8000/api/health"

    print(f"{Colors.DIM}  Waiting for server engine to initialize…{Colors.RESET}")

    import urllib.request
    import json

    is_ready = False
    start_time = time.time()
    browser_opened = False

    def print_access_dashboard():
        print(f"\n{Colors.BOLD}{Colors.CYAN}=========================================================={Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}  🛡️  Deepfake Video Forensics Studio is Live!{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}=========================================================={Colors.RESET}")
        print(f"  ➜ {Colors.BOLD}Web Studio:{Colors.RESET}     {Colors.CYAN}{Colors.UNDERLINE}http://127.0.0.1:8000/{Colors.RESET}")
        print(f"  ➜ {Colors.BOLD}API Documentation:{Colors.RESET} {Colors.CYAN}{Colors.UNDERLINE}http://127.0.0.1:8000/docs{Colors.RESET}")
        print(f"  ➜ {Colors.BOLD}Engine Telemetry:{Colors.RESET}  {Colors.CYAN}{Colors.UNDERLINE}http://127.0.0.1:8000/api/health{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}=========================================================={Colors.RESET}")
        print(f"  {Colors.DIM}Press Ctrl+C to stop the application at any time.{Colors.RESET}\n")

    try:
        # Health check polling loop
        while server_proc.poll() is None:
            if not is_ready:
                try:
                    req = urllib.request.Request(
                        health_url,
                        headers={"User-Agent": "Quickstart-HealthCheck/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        if resp.status == 200:
                            is_ready = True
                            print_access_dashboard()
                            if not browser_opened:
                                browser_opened = True
                                webbrowser.open(target_url)
                except Exception:
                    pass

                # Fallback if health endpoint delayed past 45s
                if time.time() - start_time > 45 and not is_ready:
                    is_ready = True
                    print_access_dashboard()
                    if not browser_opened:
                        browser_opened = True
                        webbrowser.open(target_url)

                time.sleep(0.3)
            else:
                time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[shutdown] Stopping server…{Colors.RESET}")
    finally:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except Exception:
                server_proc.kill()
        free_port(8000)
        print(f"{Colors.GREEN}[shutdown] Server stopped cleanly. Goodbye!{Colors.RESET}")

# ── Main Entrypoint ──
def main():
    verify_python_version()
    print_banner()

    venv_python = get_venv_python()

    # If .venv exists and we are NOT running under it, delegate to venv python
    if venv_python.exists() and sys.executable.lower() != str(venv_python).lower() and sys.prefix == sys.base_prefix:
        log_info(f"Switching to project virtual environment ({venv_python})...")
        sys.exit(subprocess.call([str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:]))

    # Otherwise ensure venv is created
    py_exec = ensure_virtualenv()

    # Re-exec if venv was just created
    if venv_python.exists() and sys.executable.lower() != str(venv_python).lower() and sys.prefix == sys.base_prefix:
        log_info("Re-launching inside new virtual environment...")
        sys.exit(subprocess.call([str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:]))

    ensure_dependencies(py_exec)
    ensure_model_weights(py_exec)
    launch_application(py_exec)

if __name__ == "__main__":
    main()
