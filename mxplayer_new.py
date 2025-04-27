import os
import re
import json
import time
import subprocess
import streamlit as st
import tempfile
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Page configuration
st.set_page_config(page_title="MX Player Video Downloader", page_icon="🎥")

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .download-btn {
        text-align: center;
        margin-top: 1rem;
    }
    .stProgress > div > div > div {
        background-color: #4CAF50;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #888888;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("<h1 class='main-header'>MX Player Video Downloader</h1>", unsafe_allow_html=True)

# Instructions
with st.expander("How to use"):
    st.markdown("""
    ### Instructions
    1. Enter a valid MX Player video URL (e.g., https://www.mxplayer.in/...)
    2. Click the "Download" button
    3. Wait for the video to be processed
    4. Download the video to your device

    ### Requirements
    - Internet connection
    - Chrome browser (installed automatically)
    - FFmpeg (detected automatically)
    """)

# Input for MX Player URL
mx_url = st.text_input("Enter MX Player video URL:", placeholder="https://www.mxplayer.in/...")

# Function to find FFmpeg path
def find_ffmpeg_path():
    try:
        # Try to find ffmpeg in PATH
        if platform.system() == "Windows":
            result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True, check=True)
            return result.stdout.strip().split("\n")[0]
        else:  # Linux/Mac
            result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Check common installation paths
        common_paths = []
        if platform.system() == "Windows":
            common_paths = [
                "ffmpeg.exe"
            ]
        else:  # Linux/Mac
            common_paths = [
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/opt/homebrew/bin/ffmpeg"
            ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

# Function to extract and download video
def process_video(url, progress_callback):
    try:
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-gpu-compositing")
        chrome_options.add_argument("--disable-gpu-rasterization")
        chrome_options.add_argument("--disable-gpu-sandbox")
        chrome_options.add_argument("--disable-gl-drawing-for-tests")
        chrome_options.add_argument("--disable-webgl")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Setup performance logging
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        # Create temp directory for download
        temp_dir = tempfile.mkdtemp()
        output_file = os.path.join(temp_dir, f"mxplayer_video_{int(time.time())}.mp4")

        # Find FFmpeg path
        ffmpeg_path = find_ffmpeg_path()
        if not ffmpeg_path:
            return None, "FFmpeg not found. Please install FFmpeg and try again."

        # Update progress
        progress_callback(0.1, "Starting Chrome...")

        # Initialize Chrome driver
        try:
            # Check if running on Render (look for Chrome binary installed by build.sh)
            chrome_binary_path = "./chrome/chrome-linux64/chrome"
            chromedriver_path = "./chromedriver/chromedriver"

            if os.path.exists(chrome_binary_path) and os.path.exists(chromedriver_path):
                # Running on Render, use pre-installed binaries
                chrome_options.binary_location = chrome_binary_path
                service = Service(executable_path=chromedriver_path)
            else:
                # Local development, use ChromeDriverManager
                service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException as e:
            return None, f"Failed to start Chrome: {str(e)}"

        try:
            # Navigate to MX Player URL
            progress_callback(0.2, "Navigating to MX Player...")
            driver.get(url)
            time.sleep(5)  # Wait for page to load

            # Extract video URLs from performance logs
            progress_callback(0.3, "Extracting video information...")
            logs = driver.get_log("performance")
            video_urls = []

            for log in logs:
                try:
                    message = json.loads(log["message"])
                    if "Network.responseReceived" in message["message"]["method"]:
                        request_id = message["message"]["params"]["requestId"]
                        request = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                        body = request.get("body", "")
                        if ".m3u8" in body or ".mpd" in body:
                            video_urls.extend(re.findall(r'https://[^\s\'"]+\.m3u8', body))
                            video_urls.extend(re.findall(r'https://[^\s\'"]+\.mpd', body))
                except Exception:
                    continue

            if not video_urls:
                return None, "No video URLs found. Please check the URL and try again."

            # Download video using yt-dlp
            progress_callback(0.4, "Preparing to download...")

            # yt-dlp is already installed via requirements.txt
            progress_callback(0.45, "Preparing yt-dlp...")

            # Start download
            progress_callback(0.5, "Downloading video...")

            # Command to download video
            cmd = [
                "yt-dlp",
                "--ffmpeg-location", ffmpeg_path,
                "--no-warnings",
                "--no-part",
                "--force-generic-extractor",
                "--no-check-certificate",
                "-o", output_file,
                video_urls[0]  # Use the first URL found
            ]

            # Execute download process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Monitor download progress
            for line in iter(process.stdout.readline, ''):
                if '[download]' in line:
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        percent = float(match.group(1))
                        # Map download percentage to overall progress (50% to 90%)
                        normalized_progress = 0.5 + (percent / 100) * 0.4
                        progress_callback(normalized_progress, f"Downloading: {percent:.1f}%")

            # Wait for process to complete
            process.wait()

            # Check if download was successful
            if process.returncode != 0:
                return None, "Download failed. Please try again."

            # Check if file exists and has content
            if not os.path.exists(output_file) or os.path.getsize(output_file) < 10000:  # Less than 10KB
                return None, "Downloaded file is invalid or too small."

            # Complete
            progress_callback(1.0, "Download complete!")
            return output_file, None

        finally:
            # Clean up
            driver.quit()

    except Exception as e:
        return None, f"Error: {str(e)}"

# Main download button
if st.button("Download Video"):
    if not mx_url or not re.match(r"https://www\.mxplayer\.in/.*", mx_url):
        st.error("Please enter a valid MX Player URL")
    else:
        # Setup progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Progress callback function
        def update_progress(progress, status):
            progress_bar.progress(progress)
            status_text.text(status)

        # Process video
        with st.spinner("Processing video..."):
            output_file, error = process_video(mx_url, update_progress)

        # Handle result
        if error:
            st.error(error)
        elif output_file and os.path.exists(output_file):
            st.success("Video downloaded successfully!")

            # Read video file
            with open(output_file, "rb") as file:
                video_bytes = file.read()

                # Get file size
                file_size_mb = len(video_bytes) / (1024 * 1024)

                # Display video info
                st.markdown(f"<h2 class='sub-header'>Your Video is Ready!</h2>", unsafe_allow_html=True)
                st.info(f"File Size: {file_size_mb:.1f} MB")

                # Download button
                st.markdown("<div class='download-btn'>", unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ Download Video",
                    data=video_bytes,
                    file_name=f"mxplayer_video_{int(time.time())}.mp4",
                    mime="video/mp4"
                )
                st.markdown("</div>", unsafe_allow_html=True)

                # Video preview
                st.video(video_bytes)

                # Clean up
                try:
                    os.remove(output_file)
                except:
                    pass

# Footer
st.markdown("<div class='footer'>Made with ❤️ by Sketch😘</div>", unsafe_allow_html=True)
