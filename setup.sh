#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  Deepfake Video Forensics - Auto Installer & Runner"
echo "=========================================================="

# Check if python3 is present
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[*] Python not detected. Attempting automatic installation..."
    if command -v brew &> /dev/null; then
        echo "[*] Installing Python 3 via Homebrew..."
        brew install python3
    elif command -v apt-get &> /dev/null; then
        echo "[*] Installing Python 3 via apt..."
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
    else
        echo "[ERROR] Package manager not recognized. Please install Python 3.10+ from: https://www.python.org/downloads/"
        exit 1
    fi
fi

if command -v python3 &> /dev/null; then
    exec python3 quickstart.py "$@"
else
    exec python quickstart.py "$@"
fi

