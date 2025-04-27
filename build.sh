#!/bin/bash

# Enable exit on error
set -e

# Function to show progress
show_progress() {
    echo "===> $1"
}

# Setup cache directories
mkdir -p ./.cache/pip
mkdir -p ./.cache/chrome
mkdir -p ./.cache/chromedriver

# Update pip to the latest version with caching
show_progress "Updating pip with caching enabled"
pip install --upgrade pip --cache-dir=./.cache/pip

# Install dependencies from requirements.txt with caching
show_progress "Installing dependencies with caching enabled"
pip install -r requirements.txt --cache-dir=./.cache/pip

# Install FFmpeg if not already installed
if ! command -v ffmpeg &> /dev/null; then
    show_progress "Installing FFmpeg"
    apt-get update -qq && apt-get install -y --no-install-recommends ffmpeg
fi

# Create bin directory if it doesn't exist
mkdir -p ./bin

# Create symbolic link to FFmpeg in bin directory
if command -v ffmpeg &> /dev/null; then
    ln -sf $(which ffmpeg) ./bin/ffmpeg
fi

# Check if Chrome is already downloaded and cached
if [ ! -d "./chrome-linux" ]; then
    show_progress "Downloading and setting up Chrome"
    if [ -f "./.cache/chrome/chrome-linux.zip" ]; then
        show_progress "Using cached Chrome"
        cp ./.cache/chrome/chrome-linux.zip ./chrome-linux.zip
    else
        show_progress "Downloading Chrome"
        mkdir -p ./chrome
        curl -SL --connect-timeout 30 --retry 5 --retry-delay 2 https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chrome-linux64.zip -o chrome-linux.zip
        # Cache the download
        cp chrome-linux.zip ./.cache/chrome/
    fi

    # Extract Chrome
    unzip -q chrome-linux.zip
    mv ./chrome-linux64 ./chrome-linux
    chmod +x ./chrome-linux/chrome
    rm chrome-linux.zip
fi

# Check if ChromeDriver is already downloaded and cached
if [ ! -d "./chromedriver" ] || [ ! -f "./chromedriver/chromedriver" ]; then
    show_progress "Downloading and setting up ChromeDriver"
    if [ -f "./.cache/chromedriver/chromedriver-linux.zip" ]; then
        show_progress "Using cached ChromeDriver"
        cp ./.cache/chromedriver/chromedriver-linux.zip ./chromedriver-linux.zip
    else
        show_progress "Downloading ChromeDriver"
        mkdir -p ./chromedriver
        curl -SL --connect-timeout 30 --retry 5 --retry-delay 2 https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chromedriver-linux64.zip -o chromedriver-linux.zip
        # Cache the download
        cp chromedriver-linux.zip ./.cache/chromedriver/
    fi

    # Extract ChromeDriver
    unzip -q chromedriver-linux.zip
    mkdir -p ./chromedriver
    mv ./chromedriver-linux64/chromedriver ./chromedriver/chromedriver
    chmod +x ./chromedriver/chromedriver
    rm -rf chromedriver-linux64
    rm chromedriver-linux.zip
fi

# Set environment variables
show_progress "Setting up environment variables"
export CHROME_PATH="./chrome-linux/chrome"
export CHROMEDRIVER_PATH="./chromedriver/chromedriver"
export FFMPEG_PATH="./bin/ffmpeg"

# Create .env file for Streamlit to read
echo "CHROME_PATH=./chrome-linux/chrome" > .env
echo "CHROMEDRIVER_PATH=./chromedriver/chromedriver" >> .env
echo "FFMPEG_PATH=./bin/ffmpeg" >> .env

# Install yt-dlp with caching
show_progress "Installing yt-dlp with caching enabled"
pip install -U yt-dlp --cache-dir=./.cache/pip

show_progress "Setup complete! Starting Streamlit app..."
# Start your Streamlit app
streamlit run mxplayer_new.py
