#!/bin/bash

# Update pip to the latest version (optional)
pip install --upgrade pip

# Activate the virtual environment (adjust this path if necessary)
source ./.venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install necessary system dependencies for Chrome (without sudo)
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
  wget

# Install Chrome browser
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome-stable_current_amd64.deb
apt-get install -f

# Install ffmpeg (needed for video processing)
apt-get install -y ffmpeg

# Start Streamlit app (make sure to use the Render port environment variable)
streamlit run mxplayer_new.py --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false --browser.gatherUsageStats=false --server.port=$PORT
