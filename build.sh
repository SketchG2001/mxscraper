#!/bin/bash

# Update pip to the latest version (optional)
pip install --upgrade pip

# Activate the virtual environment (adjust this path if necessary)
source ./.venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install necessary dependencies (Chrome, ffmpeg)
apt-get update
apt-get install -y \
  libx11-dev \
  libxkbfile-dev \
  libsecret-1-dev \
  libxrandr-dev \
  libxtst-dev \
  libappindicator3-dev \
  libatk-bridge2.0-dev \
  libgdk-pixbuf2.0-dev \
  libnss3 \
  libxcomposite-dev \
  libxdamage-dev \
  wget \
  ffmpeg

# Install Google Chrome in user-space (without root privileges)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.tar.gz
tar -xvzf google-chrome-stable_current_amd64.tar.gz -C $HOME/google-chrome

# Set environment variable for Chrome binary path
export PATH=$HOME/google-chrome/google-chrome-stable:$PATH

# Start Streamlit app
streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false --server.port=$PORT
