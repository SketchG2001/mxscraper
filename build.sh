#!/bin/bash

# Update pip to the latest version (optional)
pip install --upgrade pip

# Activate the virtual environment (adjust this path if necessary)
source ./.venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install necessary dependencies (Chrome, ffmpeg) in user space

# Download and install ffmpeg
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz
tar -xf ffmpeg-release-i686-static.tar.xz -C $HOME/ffmpeg

# Set environment variable for ffmpeg binary path
export PATH=$HOME/ffmpeg/ffmpeg-*/bin:$PATH

# Install Google Chrome in user-space (without root privileges)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.tar.gz
tar -xvzf google-chrome-stable_current_amd64.tar.gz -C $HOME/google-chrome

# Set environment variable for Chrome binary path
export PATH=$HOME/google-chrome/google-chrome-stable:$PATH

# Start Streamlit app
streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false --server.port=$PORT
