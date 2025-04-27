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

# Install Google Chrome in user-space (without root privileges)
echo "Downloading and installing Google Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.tar.gz

# Extract the tarball to $HOME
echo "Extracting Google Chrome..."
tar -xvzf google-chrome-stable_current_amd64.tar.gz -C $HOME/google-chrome

# Set environment variable for Chrome binary path
echo "Setting up Chrome environment variable..."
export PATH=$HOME/google-chrome/google-chrome:$PATH

# Ensure Google Chrome is in the path
echo "Verifying Google Chrome installation..."
if [ -f "$HOME/google-chrome/google-chrome" ]; then
    echo "Google Chrome is installed."
else
    echo "Google Chrome installation failed!"
    exit 1
fi

# Verify FFmpeg installation
echo "Verifying FFmpeg installation..."
ffmpeg -version

# Verify Chrome installation
echo "Verifying Chrome installation..."
google-chrome --version

# Start Streamlit app
echo "Starting Streamlit app..."
streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false --server.port=$PORT
