#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  Deepfake Video Forensics - One-Click Setup (Unix/macOS)"
echo "=========================================================="

if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not found on your system PATH!"
    echo "Please download and install Node.js (v18+) from: https://nodejs.org/"
    exit 1
fi

node setup.js
