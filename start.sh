#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  Deepfake Video Forensics - Auto Launcher (Unix/macOS)"
echo "=========================================================="

if command -v python3 &> /dev/null; then
    exec python3 quickstart.py "$@"
elif command -v python &> /dev/null; then
    exec python quickstart.py "$@"
elif command -v node &> /dev/null; then
    exec node run.js
else
    echo "[ERROR] Neither Python (3.10+) nor Node.js was found on your PATH!"
    echo "Please install Python from: https://www.python.org/downloads/"
    exit 1
fi
