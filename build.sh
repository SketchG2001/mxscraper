#!/bin/bash

# Enable exit on error
set -e

# Function to show progress
show_progress() {
    echo "===> $1"
}

# Setup cache directories - use Render's persistent storage if available
CACHE_DIR="${RENDER_CACHE_DIR:-$PWD/.cache}"
show_progress "Using cache directory: $CACHE_DIR"

mkdir -p "$CACHE_DIR/pip"
mkdir -p "$CACHE_DIR/chrome"
mkdir -p "$CACHE_DIR/chromedriver"
mkdir -p "$CACHE_DIR/apt"

# Speed up apt operations
if [ -f /etc/apt/apt.conf.d/docker-clean ]; then
    # Remove docker-clean to keep apt cache
    show_progress "Configuring apt for caching"
    rm -f /etc/apt/apt.conf.d/docker-clean
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
fi

# Install FFmpeg and other dependencies in parallel
show_progress "Installing system dependencies"
if ! command -v ffmpeg &> /dev/null; then
    (
        export DEBIAN_FRONTEND=noninteractive
        if [ -d "$CACHE_DIR/apt" ]; then
            mkdir -p /var/cache/apt/archives
            cp -a "$CACHE_DIR/apt/"* /var/cache/apt/archives/ 2>/dev/null || true
        fi
        apt-get update -qq
        apt-get install -y --no-install-recommends ffmpeg -o Dpkg::Options::="--force-confold"
        cp -a /var/cache/apt/archives/*deb "$CACHE_DIR/apt/" 2>/dev/null || true
    ) &
    FFMPEG_PID=$!
else
    show_progress "FFmpeg already installed"
fi

# Update pip and install dependencies in parallel
show_progress "Installing Python dependencies"
(
    pip install --upgrade pip --cache-dir="$CACHE_DIR/pip" --quiet
    pip install -r requirements.txt --cache-dir="$CACHE_DIR/pip" --quiet
    # Install yt-dlp with caching (moved here to parallelize)
    pip install -U yt-dlp --cache-dir="$CACHE_DIR/pip" --quiet
) &
PIP_PID=$!

# Create bin directory if it doesn't exist
mkdir -p ./bin

# Wait for FFmpeg installation if it was started
if [ -n "$FFMPEG_PID" ]; then
    wait $FFMPEG_PID
    show_progress "FFmpeg installation completed"
fi

# Create symbolic link to FFmpeg in bin directory
if command -v ffmpeg &> /dev/null; then
    ln -sf $(which ffmpeg) ./bin/ffmpeg
fi

# Download and setup Chrome and ChromeDriver in parallel
show_progress "Setting up Chrome and ChromeDriver"

# Function to download and extract Chrome
setup_chrome() {
    if [ -d "./chrome-linux" ] && [ -x "./chrome-linux/chrome" ]; then
        show_progress "Chrome already installed"
        return 0
    fi

    show_progress "Setting up Chrome"
    local chrome_zip="chrome-linux.zip"
    local chrome_cache="$CACHE_DIR/chrome/$chrome_zip"

    # Download Chrome if not in cache
    if [ ! -f "$chrome_cache" ]; then
        show_progress "Downloading Chrome"
        mkdir -p "$CACHE_DIR/chrome"
        curl -SL --connect-timeout 30 --retry 5 --retry-delay 2 \
            https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chrome-linux64.zip \
            -o "$chrome_cache" || return 1
    else
        show_progress "Using cached Chrome"
    fi

    # Extract Chrome
    cp "$chrome_cache" ./$chrome_zip
    unzip -q ./$chrome_zip || return 1
    mv ./chrome-linux64 ./chrome-linux
    chmod +x ./chrome-linux/chrome
    rm ./$chrome_zip
    show_progress "Chrome setup completed"
    return 0
}

# Function to download and extract ChromeDriver
setup_chromedriver() {
    if [ -d "./chromedriver" ] && [ -x "./chromedriver/chromedriver" ]; then
        show_progress "ChromeDriver already installed"
        return 0
    fi

    show_progress "Setting up ChromeDriver"
    local driver_zip="chromedriver-linux.zip"
    local driver_cache="$CACHE_DIR/chromedriver/$driver_zip"

    # Download ChromeDriver if not in cache
    if [ ! -f "$driver_cache" ]; then
        show_progress "Downloading ChromeDriver"
        mkdir -p "$CACHE_DIR/chromedriver"
        curl -SL --connect-timeout 30 --retry 5 --retry-delay 2 \
            https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.78/linux64/chromedriver-linux64.zip \
            -o "$driver_cache" || return 1
    else
        show_progress "Using cached ChromeDriver"
    fi

    # Extract ChromeDriver
    cp "$driver_cache" ./$driver_zip
    unzip -q ./$driver_zip || return 1
    mkdir -p ./chromedriver
    mv ./chromedriver-linux64/chromedriver ./chromedriver/chromedriver
    chmod +x ./chromedriver/chromedriver
    rm -rf ./chromedriver-linux64
    rm ./$driver_zip
    show_progress "ChromeDriver setup completed"
    return 0
}

# Run Chrome and ChromeDriver setup in parallel
setup_chrome &
CHROME_PID=$!

setup_chromedriver &
DRIVER_PID=$!

# Wait for pip installation to complete
if [ -n "$PIP_PID" ]; then
    wait $PIP_PID
    show_progress "Python dependencies installation completed"
fi

# Wait for Chrome and ChromeDriver setup to complete
if [ -n "$CHROME_PID" ]; then
    wait $CHROME_PID || { show_progress "Chrome setup failed"; exit 1; }
fi

if [ -n "$DRIVER_PID" ]; then
    wait $DRIVER_PID || { show_progress "ChromeDriver setup failed"; exit 1; }
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

# Cleanup to reduce image size
show_progress "Cleaning up to reduce image size"
if [ -z "$RENDER_CACHE_DIR" ]; then
    # Only clean local cache if not using Render's persistent storage
    rm -rf ./.cache/pip/http
    rm -rf ./.cache/pip/selfcheck
fi

# Remove unnecessary files
apt-get clean -y 2>/dev/null || true
rm -rf /var/lib/apt/lists/* 2>/dev/null || true
rm -rf /tmp/* 2>/dev/null || true
rm -rf /var/tmp/* 2>/dev/null || true

# Optimize for Render
if [ -n "$RENDER" ]; then
    show_progress "Applying Render-specific optimizations"
    # Reduce logging verbosity for Streamlit
    mkdir -p ~/.streamlit
    echo "[logger]" > ~/.streamlit/config.toml
    echo "level = \"error\"" >> ~/.streamlit/config.toml

    # Set low-resource mode for Streamlit
    echo "[server]" >> ~/.streamlit/config.toml
    echo "headless = true" >> ~/.streamlit/config.toml
    echo "enableCORS = false" >> ~/.streamlit/config.toml
    echo "enableXsrfProtection = false" >> ~/.streamlit/config.toml

    # Set memory management
    echo "[runner]" >> ~/.streamlit/config.toml
    echo "memory_threshold = 400" >> ~/.streamlit/config.toml
fi

show_progress "Setup complete! Starting Streamlit app..."
# Start your Streamlit app with reduced verbosity
exec streamlit run mxplayer_new.py --server.headless=true
