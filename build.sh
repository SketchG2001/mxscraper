#!/bin/bash

# Update pip to the latest version
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install FFmpeg if not already installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    apt-get update && apt-get install -y ffmpeg
fi

# Create bin directory if it doesn't exist
mkdir -p ./bin

# Create symbolic link to FFmpeg in bin directory
if command -v ffmpeg &> /dev/null; then
    ln -sf $(which ffmpeg) ./bin/ffmpeg
fi

# Download Chrome
mkdir -p ./chrome
curl -SL https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chrome-linux64.zip -o chrome-linux.zip
unzip chrome-linux.zip -d ./chrome
mv ./chrome/chrome-linux64 ./chrome-linux
chmod +x ./chrome-linux/chrome
rm chrome-linux.zip

# Download Chromedriver
mkdir -p ./chromedriver
curl -SL https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chromedriver-linux64.zip -o chromedriver-linux.zip
unzip chromedriver-linux.zip -d ./chromedriver
mv ./chromedriver/chromedriver-linux64/chromedriver ./chromedriver/chromedriver
chmod +x ./chromedriver/chromedriver
rm chromedriver-linux.zip

# Set environment variables
export CHROME_PATH="./chrome-linux/chrome"
export CHROMEDRIVER_PATH="./chromedriver/chromedriver"
export FFMPEG_PATH="./bin/ffmpeg"

# Create .env file for Streamlit to read
echo "CHROME_PATH=./chrome-linux/chrome" > .env
echo "CHROMEDRIVER_PATH=./chromedriver/chromedriver" >> .env
echo "FFMPEG_PATH=./bin/ffmpeg" >> .env

# Install yt-dlp
pip install -U yt-dlp

# Start your Streamlit app
streamlit run mxplayer_new.py
