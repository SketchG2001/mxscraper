#!/usr/bin/env bash
# Exit on error
set -o errexit

# Skip apt-get commands on Render's free tier (read-only filesystem)
# Check if required commands are available
echo "Checking for required system dependencies..."
command -v ffmpeg >/dev/null 2>&1 || echo "Warning: ffmpeg not found, some functionality may be limited"
command -v unzip >/dev/null 2>&1 || echo "Warning: unzip not found, installing Chrome may fail"
command -v curl >/dev/null 2>&1 || echo "Warning: curl not found, installing Chrome may fail"

# Update pip to the latest version
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Download Chrome
mkdir -p ./chrome
curl -SL https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chrome-linux64.zip -o chrome-linux.zip
unzip chrome-linux.zip -d ./chrome
mv ./chrome/chrome-linux64 ./chrome-linux
rm chrome-linux.zip

# Download Chromedriver
mkdir -p ./chromedriver
curl -SL https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chromedriver-linux64.zip -o chromedriver-linux.zip
unzip chromedriver-linux.zip -d ./chromedriver
mv ./chromedriver/chromedriver-linux64/chromedriver ./chromedriver/chromedriver
rm chromedriver-linux.zip

# Make chromedriver executable
chmod +x ./chromedriver/chromedriver

echo "Build completed successfully!"

# Note: For Render deployment, the actual app startup command should be specified
# in the Render dashboard as: streamlit run mxplayer_new.py
