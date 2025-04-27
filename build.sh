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

# Setup directories without using cache
CACHE_DIR="./.cache"
show_progress "Using cache directory: $CACHE_DIR"

# Clean up old cache if it exists to avoid using old cached data
rm -rf "$CACHE_DIR" || true

# Speed up apt operations
if [ -f /etc/apt/apt.conf.d/docker-clean ]; then
    # Remove docker-clean to keep apt cache
    show_progress "Configuring apt for fresh installs"
    # Try to create keep-cache file, but don't fail if filesystem is read-only
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache 2>/dev/null || true
fi

# Install FFmpeg and other dependencies (without cache)
show_progress "Installing system dependencies"
if ! command -v ffmpeg &> /dev/null; then
    (
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y --no-install-recommends ffmpeg -o Dpkg::Options::="--force-confold"
    )
else
    show_progress "FFmpeg already installed"
fi

# Update pip and install dependencies without cache
show_progress "Installing Python dependencies (no cache)"
(
    pip install --upgrade pip --no-cache-dir --quiet
    pip install -r requirements.txt --no-cache-dir --quiet
    # Install yt-dlp without cache
    pip install -U yt-dlp --no-cache-dir --quiet
)

# Set environment variables
show_progress "Setting up environment variables"
export CHROME_PATH="./chrome-linux/chrome"
export CHROMEDRIVER_PATH="./chromedriver/chromedriver"
export FFMPEG_PATH="./bin/ffmpeg"

# Create .env file for Streamlit to read (no cache)
show_progress "Creating .env file"
echo "CHROME_PATH=./chrome-linux/chrome" > .env
echo "CHROMEDRIVER_PATH=./chromedriver/chromedriver" >> .env
echo "FFMPEG_PATH=./bin/ffmpeg" >> .env

# Start your Streamlit app without using cache and without old configuration
show_progress "Setup complete! Starting Streamlit app without cache..."
timeout 300 streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false || {
    show_progress "Streamlit app failed to start within timeout. Retrying with minimal configuration..."
    # Retry with minimal configuration
    exec streamlit run mxplayer_new.py --server.headless=true
}
