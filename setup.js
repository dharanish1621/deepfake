import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  magenta: '\x1b[35m',
};

function logStep(step, total, msg) {
  console.log(`\n${colors.cyan}[${step}/${total}]${colors.reset} ${colors.bold}${msg}${colors.reset}`);
}

function logSuccess(msg) {
  console.log(`${colors.green}✔ ${msg}${colors.reset}`);
}

function logInfo(msg) {
  console.log(`${colors.dim}  ℹ ${msg}${colors.reset}`);
}

function logError(msg) {
  console.error(`${colors.red}✖ ${msg}${colors.reset}`);
}

// ── 1. Check Node.js Dependencies ──
function setupNode() {
  logStep(1, 4, 'Installing Node.js & Frontend Dependencies…');
  try {
    logInfo('Running npm install...');
    execSync('npm install', {
      cwd: __dirname,
      stdio: 'inherit',
      shell: true,
    });
    logSuccess('Node.js packages installed.');
  } catch (err) {
    logError(`Failed to install npm dependencies: ${err.message}`);
    process.exit(1);
  }
}

// ── 2. Detect System Python & Create Virtual Environment ──
function setupPythonVenv() {
  logStep(2, 4, 'Configuring Python Environment (.venv)…');

  const venvPython = process.platform === 'win32'
    ? path.join(__dirname, '.venv', 'Scripts', 'python.exe')
    : path.join(__dirname, '.venv', 'bin', 'python');

  if (fs.existsSync(venvPython)) {
    logSuccess('Existing virtual environment found in .venv');
    return venvPython;
  }

  // Detect system Python candidate
  const candidates = process.platform === 'win32'
    ? ['py -3', 'python', 'python3']
    : ['python3', 'python'];

  let systemPython = null;
  for (const cmd of candidates) {
    try {
      const ver = execSync(`${cmd} -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"`, {
        encoding: 'utf-8',
        stdio: ['ignore', 'pipe', 'ignore'],
        shell: true,
      }).trim();
      const [major, minor] = ver.split('.').map(Number);
      if (major === 3 && minor >= 10) {
        systemPython = cmd;
        logInfo(`Detected compatible system Python: ${cmd} (Python ${ver})`);
        break;
      }
    } catch {
      // try next
    }
  }

  if (!systemPython) {
    logError('No compatible Python (3.10+) found on PATH.');
    console.log(`${colors.yellow}Please install Python 3.10+ from https://www.python.org/downloads/ and ensure 'Add Python to PATH' is checked.${colors.reset}`);
    process.exit(1);
  }

  logInfo('Creating isolated virtual environment in .venv...');
  try {
    execSync(`${systemPython} -m venv .venv`, {
      cwd: __dirname,
      stdio: 'inherit',
      shell: true,
    });
    if (fs.existsSync(venvPython)) {
      logSuccess('Virtual environment created successfully in .venv');
      return venvPython;
    }
  } catch (err) {
    logError(`Failed to create virtual environment: ${err.message}`);
  }

  logInfo('Falling back to system Python');
  return systemPython;
}

// ── 3. Install Python Dependencies ──
function setupPythonRequirements(pythonCmd) {
  logStep(3, 4, 'Installing AI & Video Processing Dependencies…');
  logInfo('Updating pip...');
  try {
    execSync(`"${pythonCmd}" -m pip install --upgrade pip`, {
      cwd: __dirname,
      stdio: 'inherit',
      shell: true,
    });
  } catch {
    // Continue even if pip upgrade had warnings
  }

  logInfo('Installing requirements from requirements.txt...');
  try {
    execSync(`"${pythonCmd}" -m pip install -r requirements.txt`, {
      cwd: __dirname,
      stdio: 'inherit',
      shell: true,
    });
    logSuccess('Python dependencies installed successfully.');
  } catch (err) {
    logError(`Failed to install requirements.txt: ${err.message}`);
    process.exit(1);
  }
}

// ── 4. Verify / Download Model Weights ──
function setupModelWeights(pythonCmd) {
  logStep(4, 4, 'Verifying Fine-Tuned VideoMAE Model Weights…');
  const modelDir = path.join(__dirname, 'models', 'videomae');
  const modelWeights = path.join(modelDir, 'model.safetensors');

  if (fs.existsSync(modelWeights) && fs.statSync(modelWeights).size > 100000000) {
    const sizeMb = (fs.statSync(modelWeights).size / (1024 * 1024)).toFixed(1);
    logSuccess(`Model weights verified (${sizeMb} MB) at models/videomae/model.safetensors`);
    return;
  }

  logInfo('Downloading fine-tuned VideoMAE weights from Hugging Face Hub (FaceForensics++ benchmark)...');
  fs.mkdirSync(modelDir, { recursive: true });

  const pyDownloadScript = [
    'import os',
    'from huggingface_hub import hf_hub_download',
    'token = os.environ.get("HF_TOKEN") or None',
    'os.environ["HF_HUB_VERBOSITY"] = "error"',
    `model_dir = r"${modelDir}"`,
    'print("  Downloading model.safetensors (~345 MB)...")',
    'hf_hub_download(repo_id="Vansh180/VideoMae-ffc23-deepfake-detector", filename="model.safetensors", local_dir=model_dir, token=token)',
    'print("  Download complete.")',
  ].join('; ');

  try {
    execSync(`"${pythonCmd}" -c "${pyDownloadScript}"`, {
      cwd: __dirname,
      stdio: 'inherit',
      shell: true,
    });
    logSuccess('Trained model weights installed successfully.');
  } catch (err) {
    logError(`Failed to download model weights: ${err.message}`);
    console.log(`${colors.yellow}You can manually place model.safetensors into models/videomae/ or set HF_TOKEN environment variable.${colors.reset}`);
    process.exit(1);
  }
}

// ── Main Execution ──
function main() {
  console.log(`\n${colors.bold}${colors.magenta}==========================================================${colors.reset}`);
  console.log(`${colors.bold}${colors.magenta}  🛡️  Deepfake Video Forensics — One-Line Project Setup${colors.reset}`);
  console.log(`${colors.bold}${colors.magenta}==========================================================${colors.reset}`);

  const startTime = Date.now();

  setupNode();
  const pythonCmd = setupPythonVenv();
  setupPythonRequirements(pythonCmd);
  setupModelWeights(pythonCmd);

  const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);

  console.log(`\n${colors.bold}${colors.green}==========================================================${colors.reset}`);
  console.log(`${colors.bold}${colors.green}  ✨ Setup Complete in ${durationSec}s! All systems ready.${colors.reset}`);
  console.log(`${colors.bold}${colors.green}==========================================================${colors.reset}`);
  console.log(`\n${colors.bold}To start the application, simply run:${colors.reset}`);
  console.log(`  ${colors.cyan}${colors.bold}npm start${colors.reset}   (or double-click ${colors.cyan}start.bat${colors.reset} / ${colors.cyan}./start.sh${colors.reset})\n`);
}

main();
