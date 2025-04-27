#!/bin/bash

# Update pip to the latest version (optional)
echo "Updating pip..."
pip install --upgrade pip

# Activate the virtual environment (adjust this path if necessary)
echo "Activating virtual environment..."
source ./.venv/bin/activate

# Install dependencies from requirements.txt
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install necessary dependencies (Chrome, ffmpeg) in user space

# Download and install ffmpeg
echo "Downloading and installing FFmpeg..."
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz
tar -xf ffmpeg-release-i686-static.tar.xz -C $HOME/ffmpeg

# Set environment variable for ffmpeg binary path
echo "Setting up FFmpeg environment variable..."
export PATH=$HOME/ffmpeg/ffmpeg-*/bin:$PATH

# Install Headless Chromium (No root required)
echo "Downloading and installing Headless Chromium..."
wget https://github.com/ellisonleao/chromix-too/releases/download/v1.0.1/chromium-linux-x64.tar.gz

# Extract the Chromium tarball to $HOME
echo "Extracting Chromium..."
tar -xvzf chromium-linux-x64.tar.gz -C $HOME/chromium

# Set environment variable for Chrome binary path
echo "Setting up Chromium environment variable..."
export PATH=$HOME/chromium/chromium-linux-x64:$PATH

# Ensure Chromium is in the path
echo "Verifying Chromium installation..."
if [ -f "$HOME/chromium/chromium-linux-x64/chrome" ]; then
    echo "Chromium is installed."
else
    echo "Chromium installation failed!"
    exit 1
fi

# Verify FFmpeg installation
echo "Verifying FFmpeg installation..."
ffmpeg -version

# Verify Chromium installation
echo "Verifying Chromium installation..."
chromium --version

# Start Streamlit app
echo "Starting Streamlit app..."
streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false --server.port=$PORT
