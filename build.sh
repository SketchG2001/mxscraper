#!/bin/bash
set -e

echo "=== MX Player API — Ubuntu (FastAPI) ==="

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg chromium-browser chromium-chromedriver

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "Verifying ffmpeg..."
ffmpeg -version | head -1

export CHROMEDRIVER_PATH=$(which chromedriver 2>/dev/null || echo "/usr/bin/chromedriver")

PORT="${PORT:-8000}"
echo "Starting API on port $PORT (cd backend for imports)..."
cd "$(dirname "$0")/backend"
exec ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port "$PORT"
