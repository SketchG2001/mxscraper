#!/bin/bash

# Ensure that we use the correct version of Python
echo "Setting up environment..."

# Update and install necessary system packages
apt-get update
apt-get install -y python3-pip python3-dev libpq-dev curl wget

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Chrome browser and necessary dependencies
echo "Installing Chrome..."
curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o google-chrome-stable_current_amd64.deb
dpkg -i google-chrome-stable_current_amd64.deb
apt-get -f install

# Install necessary libraries for Chrome and Selenium
echo "Installing Chrome dependencies..."
apt-get install -y libxss1 libappindicator3-1 libasound2 libnss3 libgconf-2-4

# Install webdriver-manager for Selenium
pip install webdriver-manager

# If you need to install ffmpeg for video processing
echo "Installing ffmpeg..."
apt-get install -y ffmpeg

# Set up the app and run it
echo "App setup complete. Starting Streamlit..."
streamlit run mxplayer_new.py --server.port $PORT
