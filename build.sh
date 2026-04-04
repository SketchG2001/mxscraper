#!/bin/bash
set -e

echo "=== MX Player Scraper — Ubuntu Deployment ==="

# ── System packages ──────────────────────────────────────
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg chromium-browser chromium-chromedriver

# ── Python venv ──────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# ── Verify installations ────────────────────────────────
echo "Verifying ffmpeg..."
ffmpeg -version | head -1

echo "Verifying chromium..."
chromium-browser --version 2>/dev/null || chromium --version 2>/dev/null || echo "Chromium installed (could not print version)"

echo "Verifying yt-dlp..."
.venv/bin/yt-dlp --version

# ── Set Chrome path for Selenium ─────────────────────────
export CHROMEDRIVER_PATH=$(which chromedriver 2>/dev/null || echo "/usr/bin/chromedriver")

# ── Start Streamlit ──────────────────────────────────────
PORT="${PORT:-8510}"
echo "Starting Streamlit on port $PORT..."
exec .venv/bin/streamlit run mxplayer_new.py \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false \
    --server.port="$PORT"
