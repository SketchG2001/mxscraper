#!/bin/bash

# Enable exit on error
set -e

# This script has been modified to handle read-only filesystems (like on Render)
# All file operations that might fail due to read-only filesystems have been
# updated with error handling to ensure the script continues execution.

# Function to show progress
show_progress() {
    echo "===> $1"
}

# Setup cache directories - use Render's persistent storage if available
CACHE_DIR="${RENDER_CACHE_DIR:-$PWD/.cache}"
show_progress "Using cache directory: $CACHE_DIR"

# Use error handling for potential read-only parent directories
mkdir -p "$CACHE_DIR/pip" 2>/dev/null || true
mkdir -p "$CACHE_DIR/chrome" 2>/dev/null || true
mkdir -p "$CACHE_DIR/chromedriver" 2>/dev/null || true
mkdir -p "$CACHE_DIR/apt" 2>/dev/null || true

# Speed up apt operations
if [ -f /etc/apt/apt.conf.d/docker-clean ]; then
    # Remove docker-clean to keep apt cache
    show_progress "Configuring apt for caching"
    # Use || true to prevent failure on read-only filesystem
    rm -f /etc/apt/apt.conf.d/docker-clean 2>/dev/null || true
    # Try to create keep-cache file, but don't fail if filesystem is read-only
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache 2>/dev/null || true
fi

# Install FFmpeg and other dependencies in parallel
show_progress "Installing system dependencies"
if ! command -v ffmpeg &> /dev/null; then
    (
        export DEBIAN_FRONTEND=noninteractive
        if [ -d "$CACHE_DIR/apt" ]; then
            mkdir -p /var/cache/apt/archives
            cp -a "$CACHE_DIR/apt/"* /var/cache/apt/archives/ 2>/dev/null || true
        fi
        apt-get update -qq
        apt-get install -y --no-install-recommends ffmpeg -o Dpkg::Options::="--force-confold"
        cp -a /var/cache/apt/archives/*deb "$CACHE_DIR/apt/" 2>/dev/null || true
    ) &
    FFMPEG_PID=$!
else
    show_progress "FFmpeg already installed"
fi

# Update pip and install dependencies in parallel
show_progress "Installing Python dependencies"
(
    pip install --upgrade pip --cache-dir="$CACHE_DIR/pip" --quiet
    pip install -r requirements.txt --cache-dir="$CACHE_DIR/pip" --quiet
    # Install yt-dlp with caching (moved here to parallelize)
    pip install -U yt-dlp --cache-dir="$CACHE_DIR/pip" --quiet
) &
PIP_PID=$!

# Wait for FFmpeg installation if it was started
if [ -n "$FFMPEG_PID" ]; then
    wait $FFMPEG_PID
    show_progress "FFmpeg installation completed"
fi

# Wait for pip installation to complete
if [ -n "$PIP_PID" ]; then
    wait $PIP_PID
    show_progress "Python dependencies installation completed"
fi

# Set environment variables
show_progress "Setting up environment variables"
export CHROME_PATH="./chrome-linux/chrome"
export CHROMEDRIVER_PATH="./chromedriver/chromedriver"
export FFMPEG_PATH="./bin/ffmpeg"

# Create .env file for Streamlit to read
# Use error handling for potential read-only current directory
echo "CHROME_PATH=./chrome-linux/chrome" > .env 2>/dev/null || true
echo "CHROMEDRIVER_PATH=./chromedriver/chromedriver" >> .env 2>/dev/null || true
echo "FFMPEG_PATH=./bin/ffmpeg" >> .env 2>/dev/null || true

# Start your Streamlit app with reduced verbosity and timeout
show_progress "Setup complete! Starting Streamlit app with optimized settings for free instance..."
timeout 300 streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false || {
    show_progress "Streamlit app failed to start within timeout. Retrying with minimal configuration..."
    # Retry with minimal configuration
    exec streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false
}
