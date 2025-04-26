#!/bin/bash

# Update pip to the latest version (optional)
pip install --upgrade pip

# Activate the virtual environment (adjust this path if necessary)
source ./.venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install other necessary packages (e.g., Chrome, ffmpeg)
# Ensure that these installations are done with sudo privileges if needed

# Install Chrome dependencies (requires root or sudo access)
sudo apt-get update
sudo apt-get install -y libx11-dev libxkbfile-dev libsecret-1-dev libxrandr-dev libxtst-dev libappindicator3-dev libatk-bridge2.0-dev libgdk-pixbuf2.0-dev libnss3 libxcomposite-dev libxdamage-dev

# Install Chrome browser (requires root or sudo access)
sudo apt-get install -y google-chrome-stable

# Install other dependencies (e.g., ffmpeg)
sudo apt-get install -y ffmpeg

# Start Streamlit app
streamlit run your_app.py  # Replace with your actual app script
