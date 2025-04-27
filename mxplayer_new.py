import os
import re
import json
import time
import random
import subprocess
import streamlit as st
import tempfile
import platform
import threading
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

# Initialize session state for download control
if 'download_process' not in st.session_state:
    st.session_state.download_process = None
if 'download_status' not in st.session_state:
    st.session_state.download_status = "idle"  # idle, downloading, paused, cancelled, completed
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = 0.0
if 'download_output_file' not in st.session_state:
    st.session_state.download_output_file = None

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
    # First check environment variable
    ffmpeg_env = os.getenv("FFMPEG_PATH")
    if ffmpeg_env and os.path.exists(ffmpeg_env):
        return ffmpeg_env

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
                "ffmpeg.exe",
                str(Path(__file__).parent / "ffmpeg.exe")
            ]
        else:  # Linux/Mac
            common_paths = [
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/opt/homebrew/bin/ffmpeg",
                "/app/bin/ffmpeg"  # Common path in containerized environments like Render
            ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

# Function to get Chrome and ChromeDriver paths for Render deployment
def get_chrome_paths():
    # Check environment variables first
    chrome_path = os.getenv("CHROME_PATH")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")

    # If not set, use default paths based on environment
    if not chrome_path:
        if platform.system() == "Windows":
            # Default Windows paths
            chrome_path = None  # Let webdriver-manager handle it
        else:
            # Check Render paths from build.sh
            render_chrome = "./chrome-linux/chrome"
            if os.path.exists(render_chrome):
                chrome_path = render_chrome

    if not chromedriver_path:
        if platform.system() == "Windows":
            # Default Windows paths
            chromedriver_path = None  # Let webdriver-manager handle it
        else:
            # Check Render paths from build.sh
            render_driver = "./chromedriver/chromedriver"
            if os.path.exists(render_driver):
                chromedriver_path = render_driver

    return chrome_path, chromedriver_path

# Function to get a random user agent
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ]
    return random.choice(user_agents)


# Function to extract and download video
def process_video(url, progress_callback):
    # Update session state
    st.session_state.download_status = "downloading"
    st.session_state.download_progress = 0.0
    st.session_state.download_output_file = None

    # Store the thread reference for cancellation
    download_thread = threading.current_thread()
    st.session_state.download_thread = download_thread

    try:
        # Setup Chrome options with anti-bot measures
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")

        # Anti-bot detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Use random user agent
        user_agent = get_random_user_agent()
        chrome_options.add_argument(f"user-agent={user_agent}")

        # Add window size randomization for more human-like behavior
        window_width = random.randint(1024, 1920)
        window_height = random.randint(768, 1080)
        chrome_options.add_argument(f"--window-size={window_width},{window_height}")

        # Setup performance logging
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        # Create temp directory for download
        temp_dir = tempfile.mkdtemp()
        output_file = os.path.join(temp_dir, f"mxplayer_video_{int(time.time())}.mp4")
        st.session_state.download_output_file = output_file

        # Find FFmpeg path
        ffmpeg_path = find_ffmpeg_path()
        if not ffmpeg_path:
            st.session_state.download_status = "idle"
            return None, "FFmpeg not found. Please install FFmpeg and try again."

        # Update progress
        progress_callback(0.1, "Starting Chrome...")

        # Check if download was cancelled
        if st.session_state.download_status == "cancelled":
            return None, "Download cancelled by user."

        # Get Chrome and ChromeDriver paths
        chrome_path, chromedriver_path = get_chrome_paths()

        # Initialize Chrome driver
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException as e:
            st.session_state.download_status = "idle"
            return None, f"Failed to start Chrome: {str(e)}"

        try:
            # Navigate to MX Player URL with human-like behavior
            progress_callback(0.2, "Navigating to MX Player...")
            driver.get(url)

            # Random wait time to simulate human behavior
            wait_time = random.uniform(3, 7)
            time.sleep(wait_time)

            # Check if download was cancelled
            if st.session_state.download_status == "cancelled":
                return None, "Download cancelled by user."

            # Scroll down a bit to simulate human behavior
            driver.execute_script(f"window.scrollTo(0, {random.randint(100, 300)});")
            time.sleep(random.uniform(1, 2))

            # Extract video URLs from performance logs
            progress_callback(0.3, "Extracting video information...")
            logs = driver.get_log("performance")
            video_urls = []

            for log in logs:
                # Check if download was cancelled
                if st.session_state.download_status == "cancelled":
                    return None, "Download cancelled by user."

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
                st.session_state.download_status = "idle"
                return None, "No video URLs found. Please check the URL and try again."

            # Download video using yt-dlp
            progress_callback(0.4, "Preparing to download...")

            # Check if download was cancelled
            if st.session_state.download_status == "cancelled":
                return None, "Download cancelled by user."

            # Check if yt-dlp is installed
            try:
                subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
            except FileNotFoundError:
                progress_callback(0.45, "Installing yt-dlp...")
                subprocess.run(["pip", "install", "-U", "yt-dlp"], check=True)

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

            # Store process for pause/cancel functionality
            st.session_state.download_process = process

            # Monitor download progress
            for line in iter(process.stdout.readline, ''):
                # Check if download was cancelled
                if st.session_state.download_status == "cancelled":
                    if process.poll() is None:  # If process is still running
                        process.terminate()
                        process.wait()
                    return None, "Download cancelled by user."

                # Check if download was paused
                while st.session_state.download_status == "paused":
                    time.sleep(0.5)
                    # If resumed, continue
                    if st.session_state.download_status == "downloading":
                        progress_callback(st.session_state.download_progress, "Download resumed...")
                        break
                    # If cancelled while paused
                    if st.session_state.download_status == "cancelled":
                        if process.poll() is None:  # If process is still running
                            process.terminate()
                            process.wait()
                        return None, "Download cancelled by user."

                if '[download]' in line:
                    match = re.search(r'(\d+\.\d+)%', line)
                    if match:
                        percent = float(match.group(1))
                        # Map download percentage to overall progress (50% to 90%)
                        normalized_progress = 0.5 + (percent / 100) * 0.4
                        st.session_state.download_progress = normalized_progress
                        progress_callback(normalized_progress, f"Downloading: {percent:.1f}%")

            # Wait for process to complete
            process.wait()

            # Reset process reference
            st.session_state.download_process = None

            # Check if download was cancelled
            if st.session_state.download_status == "cancelled":
                return None, "Download cancelled by user."

            # Check if download was successful
            if process.returncode != 0:
                st.session_state.download_status = "idle"
                return None, "Download failed. Please try again."

            # Check if file exists and has content
            if not os.path.exists(output_file) or os.path.getsize(output_file) < 10000:  # Less than 10KB
                st.session_state.download_status = "idle"
                return None, "Downloaded file is invalid or too small."

            # Complete
            st.session_state.download_status = "completed"
            progress_callback(1.0, "Download complete!")
            return output_file, None

        finally:
            # Clean up
            driver.quit()

    except Exception as e:
        st.session_state.download_status = "idle"
        return None, f"Error: {str(e)}"


# Function to cancel download
def cancel_download():
    if st.session_state.download_status in ["downloading", "paused"]:
        st.session_state.download_status = "cancelled"
        if st.session_state.download_process and st.session_state.download_process.poll() is None:
            st.session_state.download_process.terminate()
            st.session_state.download_process = None
        st.session_state.download_progress = 0.0
        st.rerun()

# Function to pause download
def pause_download():
    if st.session_state.download_status == "downloading":
        st.session_state.download_status = "paused"
        st.rerun()

# Function to resume download
def resume_download():
    if st.session_state.download_status == "paused":
        st.session_state.download_status = "downloading"
        st.rerun()

# Progress callback function
def update_progress(progress, status):
    if 'progress_bar' in st.session_state and 'status_text' in st.session_state:
        st.session_state.progress_bar.progress(progress)
        st.session_state.status_text.text(status)

# Main download section
download_col1, download_col2 = st.columns([3, 1])

with download_col1:
    # Main download button
    if st.button("Download Video", key="download_btn", disabled=st.session_state.download_status in ["downloading", "paused"]):
        if not mx_url or not re.match(r"https://www\.mxplayer\.in/.*", mx_url):
            st.error("Please enter a valid MX Player URL")
        else:
            # Start a new download
            st.session_state.download_status = "downloading"
            st.rerun()

with download_col2:
    # Control buttons layout
    control_cols = st.columns(3)

    with control_cols[0]:
        if st.button("⏸️ Pause", key="pause_btn", disabled=st.session_state.download_status != "downloading"):
            pause_download()

    with control_cols[1]:
        if st.button("▶️ Resume", key="resume_btn", disabled=st.session_state.download_status != "paused"):
            resume_download()

    with control_cols[2]:
        if st.button("❌ Cancel", key="cancel_btn", disabled=st.session_state.download_status not in ["downloading", "paused"]):
            cancel_download()

# Display download status
if st.session_state.download_status in ["downloading", "paused"]:
    # Setup progress tracking if not already set
    if 'progress_bar' not in st.session_state:
        st.session_state.progress_bar = st.progress(st.session_state.download_progress)
    if 'status_text' not in st.session_state:
        st.session_state.status_text = st.empty()

    # Update progress display
    st.session_state.progress_bar.progress(st.session_state.download_progress)

    # Show status message
    if st.session_state.download_status == "downloading":
        st.session_state.status_text.text(f"Downloading: {st.session_state.download_progress*100:.1f}%")
    elif st.session_state.download_status == "paused":
        st.session_state.status_text.text(f"Paused at: {st.session_state.download_progress*100:.1f}%")

    # Process video if status is downloading and no process is running
    if st.session_state.download_status == "downloading" and not st.session_state.download_process:
        # Process video in a separate thread
        with st.spinner("Processing video..."):
            output_file, error = process_video(mx_url, update_progress)

            # Handle result
            if error:
                st.error(error)
                st.session_state.download_status = "idle"
                st.rerun()
            elif output_file and os.path.exists(output_file):
                st.session_state.download_output_file = output_file
                st.session_state.download_status = "completed"
                st.rerun()

# Display completed download
if st.session_state.download_status == "completed" and st.session_state.download_output_file:
    output_file = st.session_state.download_output_file

    if os.path.exists(output_file):
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
                st.session_state.download_output_file = None
                st.session_state.download_status = "idle"
                st.session_state.download_progress = 0.0
            except:
                pass
    else:
        st.error("Downloaded file not found. Please try again.")
        st.session_state.download_status = "idle"
        st.session_state.download_output_file = None

# Footer
st.markdown("<div class='footer'>Made with ❤️ by Sketch😘</div>", unsafe_allow_html=True)
