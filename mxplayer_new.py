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

# Load environment variables - with timeout to prevent hanging
try:
    # Set a short timeout for environment loading
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Environment loading timed out")

    # Set 5 second timeout for environment loading
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)

    # Load environment variables
    load_dotenv()

    # Cancel the alarm
    signal.alarm(0)
except (ImportError, AttributeError):
    # If signal module is not available (e.g., on Windows), just load normally
    load_dotenv()
except TimeoutError:
    # If loading times out, continue without it
    st.warning("Environment loading timed out, continuing with defaults")
except Exception as e:
    # If any other error occurs, log it and continue
    print(f"Error loading environment: {str(e)}")

# Initialize session state for download control
if 'download_process' not in st.session_state:
    st.session_state.download_process = None
if 'download_status' not in st.session_state:
    st.session_state.download_status = "idle"  # idle, downloading, paused, cancelled, completed, error
if 'download_progress' not in st.session_state:
    st.session_state.download_progress = 0.0
if 'download_output_file' not in st.session_state:
    st.session_state.download_output_file = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None
if 'ui_needs_update' not in st.session_state:
    st.session_state.ui_needs_update = False
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()

# Function to check if UI needs update without full rerun
def check_ui_update():
    # Only update UI at most once per second to reduce resource usage
    current_time = time.time()
    if st.session_state.ui_needs_update and (current_time - st.session_state.last_update_time) > 1.0:
        st.session_state.ui_needs_update = False
        st.session_state.last_update_time = current_time
        return True
    return False

# Page configuration
st.set_page_config(page_title="MX Player Video Downloader", page_icon="🎥", layout="centered")

# Check if UI needs update and handle accordingly
if check_ui_update():
    # If UI needs update, we'll just let the normal rendering happen
    # This is more efficient than using st.rerun() which reloads the entire app
    pass

# Custom CSS for a cleaner look
st.markdown("""
<style>
    /* Main layout and typography */
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
        color: #1E88E5;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    .sub-header {
        font-size: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #424242;
    }
    .download-btn {
        text-align: center;
        margin-top: 1rem;
    }

    /* Progress bar styling */
    .stProgress > div > div > div {
        background-color: #4CAF50;
        border-radius: 10px;
    }
    .stProgress {
        height: 10px;
    }

    /* Footer styling */
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #888888;
        font-size: 0.9rem;
        padding: 1rem;
        border-top: 1px solid #eeeeee;
    }

    /* Button styling for better visibility */
    .stButton button {
        font-weight: bold;
        transition: all 0.3s ease;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    }

    /* Specific button styles */
    .stButton.pause-btn button {
        background-color: #FFA500;
        color: white;
    }

    .stButton.pause-btn button:hover {
        background-color: #FF8C00;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }

    .stButton.resume-btn button {
        background-color: #4CAF50;
        color: white;
    }

    .stButton.resume-btn button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }

    .stButton.cancel-btn button {
        background-color: #f44336;
        color: white;
    }

    .stButton.cancel-btn button:hover {
        background-color: #d32f2f;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }

    /* Disabled button styles */
    .stButton button:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
        transform: none !important;
    }

    /* Status indicators */
    .status-downloading {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-paused {
        color: #FFA500;
        font-weight: bold;
    }
    .status-error {
        color: #FF0000;
        font-weight: bold;
    }

    /* Input field styling */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #dddddd;
        padding: 0.5rem;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4CAF50;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
    }

    /* Card-like containers */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("<h1 class='main-header'>MX Player Video Downloader</h1>", unsafe_allow_html=True)

# Create a card-like container for the main content
st.markdown("<div class='card'>", unsafe_allow_html=True)

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


# Function to find FFmpeg path with timeout
def find_ffmpeg_path():
    # First check environment variable
    ffmpeg_env = os.getenv("FFMPEG_PATH")
    if ffmpeg_env and os.path.exists(ffmpeg_env):
        return ffmpeg_env

    # Import timeout handling if available
    try:
        import signal
        has_signal = True
    except (ImportError, AttributeError):
        has_signal = False

    # Define timeout handler
    if has_signal:
        def timeout_handler(signum, frame):
            raise TimeoutError("FFmpeg path search timed out")

        # Set 5 second timeout for FFmpeg search
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)

    try:
        # Try to find ffmpeg in PATH
        if platform.system() == "Windows":
            result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True, check=True, timeout=5)
            return result.stdout.strip().split("\n")[0]
        else:  # Linux/Mac
            result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True, check=True, timeout=5)
            return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, TimeoutError):
        # Check common installation paths
        common_paths = []
        if platform.system() == "Windows":
            common_paths = [
                "ffmpeg.exe",
                str(Path(__file__).parent / "ffmpeg.exe"),
                "./bin/ffmpeg.exe"
            ]
        else:  # Linux/Mac
            common_paths = [
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/opt/homebrew/bin/ffmpeg",
                "/app/bin/ffmpeg",  # Common path in containerized environments like Render
                "./bin/ffmpeg"      # Path from build.sh
            ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None
    finally:
        # Ensure alarm is canceled even if an exception occurs
        if has_signal:
            signal.alarm(0)

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

# Cache for Chrome driver to avoid repeated initialization
chrome_driver_cache = None

# Function to get Chrome driver with caching and timeout
def get_chrome_driver(options):
    global chrome_driver_cache

    # Return cached driver if available and not closed
    if chrome_driver_cache:
        try:
            # Check if driver is still active
            chrome_driver_cache.current_url
            return chrome_driver_cache
        except:
            # Driver is closed or crashed, create a new one
            chrome_driver_cache = None

    # Import timeout handling if available
    try:
        import signal
        has_signal = True
    except (ImportError, AttributeError):
        has_signal = False

    # Define timeout handler
    if has_signal:
        def timeout_handler(signum, frame):
            raise TimeoutError("Chrome driver initialization timed out")

        # Set 30 second timeout for driver initialization
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)

    try:
        # Get Chrome and ChromeDriver paths
        chrome_path, chromedriver_path = get_chrome_paths()

        # Initialize Chrome driver
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

        # Cache the driver
        chrome_driver_cache = driver

        # Cancel the alarm if it was set
        if has_signal:
            signal.alarm(0)

        return driver
    except TimeoutError:
        raise Exception("Chrome driver initialization timed out")
    except WebDriverException as e:
        raise Exception(f"Failed to start Chrome: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to initialize Chrome: {str(e)}")
    finally:
        # Ensure alarm is canceled even if an exception occurs
        if has_signal:
            signal.alarm(0)

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
        # Setup Chrome options with anti-bot measures and low-resource optimizations
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")

        # Memory optimization flags
        chrome_options.add_argument("--js-flags=--expose-gc")  # Enable JavaScript garbage collection
        chrome_options.add_argument("--single-process")  # Use single process to reduce overhead
        chrome_options.add_argument("--disable-application-cache")  # Disable application cache
        chrome_options.add_argument("--disable-infobars")  # Disable info bars
        chrome_options.add_argument("--disable-notifications")  # Disable notifications
        chrome_options.add_argument("--disable-popup-blocking")  # Disable popup blocking
        chrome_options.add_argument("--disable-save-password-bubble")  # Disable save password
        chrome_options.add_argument("--disable-translate")  # Disable translate
        chrome_options.add_argument("--disable-web-security")  # Disable web security
        chrome_options.add_argument("--disable-client-side-phishing-detection")  # Disable phishing detection
        chrome_options.add_argument("--disable-component-update")  # Disable component updates
        chrome_options.add_argument("--disable-default-apps")  # Disable default apps
        chrome_options.add_argument("--disable-domain-reliability")  # Disable domain reliability
        chrome_options.add_argument("--disable-hang-monitor")  # Disable hang monitor
        chrome_options.add_argument("--disable-prompt-on-repost")  # Disable prompt on repost
        chrome_options.add_argument("--disable-sync")  # Disable sync
        chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")  # Disable specific features
        chrome_options.add_argument("--disable-ipc-flooding-protection")  # Disable IPC flooding protection
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")  # Disable backgrounding occluded windows
        chrome_options.add_argument("--memory-pressure-off")  # Disable memory pressure
        chrome_options.add_argument("--force-fieldtrials=*BackgroundTracing/default/")  # Disable background tracing

        # Set low memory limits
        chrome_options.add_argument("--renderer-process-limit=1")  # Limit renderer processes
        chrome_options.add_argument("--disk-cache-size=1")  # Minimal disk cache

        # Use smaller window size to reduce memory usage
        window_width = 800
        window_height = 600
        chrome_options.add_argument(f"--window-size={window_width},{window_height}")

        # Anti-bot detection measures (simplified)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Use a single user agent instead of random to reduce complexity
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Setup minimal performance logging
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

        # Initialize Chrome driver using the cached driver function
        try:
            driver = get_chrome_driver(chrome_options)
        except Exception as e:
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

            # Command to download video with resource optimization
            cmd = [
                "yt-dlp",
                "--ffmpeg-location", ffmpeg_path,
                "--no-warnings",
                "--no-part",
                "--force-generic-extractor",
                "--no-check-certificate",
                "--no-playlist",  # Don't process playlists
                "--no-simulate",  # Don't simulate, actually download
                "--no-progress",  # Disable progress to reduce CPU usage
                "--quiet",  # Reduce output verbosity
                "--no-cache-dir",  # Don't use cache directory
                "--no-sponsorblock",  # Disable sponsorblock
                "--no-write-thumbnail",  # Don't write thumbnails
                "--no-write-description",  # Don't write descriptions
                "--no-write-info-json",  # Don't write info JSON
                "--no-write-annotations",  # Don't write annotations
                "--no-write-playlist-metafiles",  # Don't write playlist metafiles
                "--no-embed-metadata",  # Don't embed metadata
                "--no-embed-chapters",  # Don't embed chapters
                "--no-embed-thumbnail",  # Don't embed thumbnails
                "--no-embed-subs",  # Don't embed subtitles
                "--no-embed-info-json",  # Don't embed info JSON
                "--no-mtime",  # Don't use mtime
                "--no-update",  # Don't update
                "--no-post-overwrites",  # Don't post overwrites
                "--no-keep-fragments",  # Don't keep fragments
                "--no-hls-use-mpegts",  # Don't use MPEG-TS for HLS
                "--downloader-args", "ffmpeg:-nostats -loglevel 0",  # Reduce FFmpeg verbosity
                "--retries", "3",  # Limit retries to save resources
                "--fragment-retries", "3",  # Limit fragment retries
                "--buffer-size", "1024",  # Smaller buffer size to reduce memory usage
                "--throttled-rate", "100K",  # Throttle download rate to reduce CPU/network usage
                "-f", "worst[ext=mp4]/worst",  # Use lowest quality to save resources
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
                if st.session_state.download_status == "paused":
                    # Log the pause with appropriate styling
                    progress_callback(st.session_state.download_progress, f"Paused at: {st.session_state.download_progress*100:.1f}%")

                    # Wait while paused
                    while st.session_state.download_status == "paused":
                        time.sleep(0.1)  # Shorter sleep time for more responsive resume

                        # If cancelled while paused
                        if st.session_state.download_status == "cancelled":
                            if process.poll() is None:  # If process is still running
                                process.terminate()
                                process.wait()
                            return None, "Download cancelled by user."

                    # If we got here, we've resumed
                    if st.session_state.download_status == "downloading":
                        # Update progress with resume message and appropriate styling
                        progress_callback(st.session_state.download_progress, f"Resuming download from: {st.session_state.download_progress*100:.1f}%")
                        # Short delay to ensure UI updates before continuing
                        time.sleep(0.2)

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
        st.session_state.ui_needs_update = True

        # Force garbage collection
        import gc
        gc.collect()

# Function to reset download state (for error recovery)
def reset_download():
    st.session_state.download_status = "idle"
    st.session_state.download_progress = 0.0
    st.session_state.download_process = None
    if 'download_output_file' in st.session_state:
        st.session_state.download_output_file = None
    if 'progress_bar' in st.session_state:
        del st.session_state.progress_bar
    if 'status_text' in st.session_state:
        del st.session_state.status_text
    st.session_state.ui_needs_update = True

    # Force garbage collection
    import gc
    gc.collect()

# Function to pause download
def pause_download():
    if st.session_state.download_status == "downloading":
        st.session_state.download_status = "paused"
        # Ensure the UI updates immediately with styled text
        if 'status_text' in st.session_state:
            st.session_state.status_text.markdown(f"<span class='status-paused'>Paused at: {st.session_state.download_progress*100:.1f}%</span>", unsafe_allow_html=True)
        st.session_state.ui_needs_update = True

# Function to resume download
def resume_download():
    if st.session_state.download_status == "paused":
        st.session_state.download_status = "downloading"
        # Ensure the UI updates immediately with styled text
        if 'status_text' in st.session_state:
            st.session_state.status_text.markdown(f"<span class='status-downloading'>Resuming download from: {st.session_state.download_progress*100:.1f}%</span>", unsafe_allow_html=True)
        st.session_state.ui_needs_update = True

# Progress callback function
def update_progress(progress, status):
    if 'progress_bar' in st.session_state and 'status_text' in st.session_state:
        st.session_state.progress_bar.progress(progress)

        # Apply appropriate styling based on status content
        if "Paused" in status:
            st.session_state.status_text.markdown(f"<span class='status-paused'>{status}</span>", unsafe_allow_html=True)
        elif "Error" in status or "failed" in status:
            st.session_state.status_text.markdown(f"<span class='status-error'>{status}</span>", unsafe_allow_html=True)
        elif "Download" in status or "Downloading" in status:
            st.session_state.status_text.markdown(f"<span class='status-downloading'>{status}</span>", unsafe_allow_html=True)
        else:
            st.session_state.status_text.text(status)

# Main download section
download_col1, download_col2 = st.columns([3, 1])

with download_col1:
    # Main download button - disabled during download, pause, or error states
    download_disabled = st.session_state.download_status in ["downloading", "paused", "error"]
    if st.button("Download Video", key="download_btn", disabled=download_disabled):
        if not mx_url or not re.match(r"https://www\.mxplayer\.in/.*", mx_url):
            st.error("Please enter a valid MX Player URL")
            st.session_state.error_message = "Please enter a valid MX Player URL"
        else:
            # Start a new download
            st.session_state.download_status = "downloading"
            st.session_state.error_message = None
            st.session_state.ui_needs_update = True

            # Force garbage collection before starting new download
            import gc
            gc.collect()

with download_col2:
    # Control buttons layout with better spacing
    st.markdown("<div style='padding: 10px 0;'></div>", unsafe_allow_html=True)

    # Create a container for the buttons
    control_container = st.container()

    # Use columns for button layout
    control_cols = control_container.columns(3)

    # Pause button with enhanced styling
    with control_cols[0]:
        pause_disabled = st.session_state.download_status != "downloading"
        if st.button("⏸️ Pause", 
                    key="pause_btn", 
                    disabled=pause_disabled,
                    help="Pause the current download"):
            pause_download()

    # Resume button with enhanced styling
    with control_cols[1]:
        resume_disabled = st.session_state.download_status != "paused"
        if st.button("▶️ Resume", 
                    key="resume_btn", 
                    disabled=resume_disabled,
                    help="Resume the paused download"):
            resume_download()

    # Cancel button with enhanced styling
    with control_cols[2]:
        cancel_disabled = st.session_state.download_status not in ["downloading", "paused"]
        if st.button("❌ Cancel", 
                    key="cancel_btn", 
                    disabled=cancel_disabled,
                    help="Cancel the current download"):
            cancel_download()

# Display download status
if st.session_state.download_status in ["downloading", "paused", "error"]:
    # Add a status indicator
    status_indicator = ""
    if st.session_state.download_status == "downloading":
        status_indicator = "🟢 Active"
        status_class = "status-downloading"
    elif st.session_state.download_status == "paused":
        status_indicator = "🟠 Paused"
        status_class = "status-paused"
    elif st.session_state.download_status == "error":
        status_indicator = "🔴 Error"
        status_class = "status-error"

    # Display status indicator
    st.markdown(f"<div style='text-align: center; margin-bottom: 10px;'><span class='{status_class}'><strong>{status_indicator}</strong></span></div>", unsafe_allow_html=True)

    # Display error message if in error state
    if st.session_state.download_status == "error" and st.session_state.error_message:
        st.markdown(f"<div style='text-align: center; margin-bottom: 15px;'><span class='status-error'>{st.session_state.error_message}</span></div>", unsafe_allow_html=True)

        # Add a retry button in the center
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Retry Download", key="retry_main"):
                reset_download()

    # Only show progress for downloading and paused states
    if st.session_state.download_status in ["downloading", "paused"]:
        # Setup progress tracking if not already set
        if 'progress_bar' not in st.session_state:
            st.session_state.progress_bar = st.progress(st.session_state.download_progress)
        if 'status_text' not in st.session_state:
            st.session_state.status_text = st.empty()

        # Update progress display
        st.session_state.progress_bar.progress(st.session_state.download_progress)

        # Show status message with styled text
        if st.session_state.download_status == "downloading":
            st.session_state.status_text.markdown(f"<span class='status-downloading'>Downloading: {st.session_state.download_progress*100:.1f}%</span>", unsafe_allow_html=True)
        elif st.session_state.download_status == "paused":
            st.session_state.status_text.markdown(f"<span class='status-paused'>Paused at: {st.session_state.download_progress*100:.1f}%</span>", unsafe_allow_html=True)

    # Process video if status is downloading and no process is running
    if st.session_state.download_status == "downloading" and not st.session_state.download_process:
        # Create a placeholder for the spinner
        spinner_placeholder = st.empty()

        # Define a function to process the video in a separate thread
        def process_video_thread():
            try:
                # Show spinner in the UI
                spinner_placeholder.spinner(text="Processing video...")

                # Process the video
                output_file, error = process_video(mx_url, update_progress)

                # Handle result
                if error:
                    st.session_state.error_message = error
                    st.session_state.download_status = "error"
                    # Use session state to trigger UI update instead of rerun
                    st.session_state.ui_needs_update = True
                elif output_file and os.path.exists(output_file):
                    st.session_state.download_output_file = output_file
                    st.session_state.download_status = "completed"
                    # Use session state to trigger UI update instead of rerun
                    st.session_state.ui_needs_update = True
            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                st.session_state.error_message = error_msg
                st.session_state.download_status = "error"
                st.session_state.download_process = None
                # Use session state to trigger UI update instead of rerun
                st.session_state.ui_needs_update = True

            # Force garbage collection after processing
            import gc
            gc.collect()

        # Start the processing in a separate thread to avoid blocking the UI
        processing_thread = threading.Thread(target=process_video_thread)
        processing_thread.daemon = True  # Allow the thread to be terminated when the main program exits
        processing_thread.start()

# Display completed download
if st.session_state.download_status == "completed" and st.session_state.download_output_file:
    output_file = st.session_state.download_output_file

    if os.path.exists(output_file):
        st.success("Video downloaded successfully!")

        # Get file size without loading the entire file into memory
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)

        # Display video info
        st.markdown(f"<h2 class='sub-header'>Your Video is Ready!</h2>", unsafe_allow_html=True)
        st.info(f"File Size: {file_size_mb:.1f} MB")

        # Download button - use file path instead of loading into memory
        st.markdown("<div class='download-btn'>", unsafe_allow_html=True)

        # Create a temporary copy with a user-friendly name for download
        download_filename = f"mxplayer_video_{int(time.time())}.mp4"
        download_path = os.path.join(os.path.dirname(output_file), download_filename)

        try:
            # Copy file instead of loading into memory
            import shutil
            shutil.copy2(output_file, download_path)

            # Use the file path for download button
            with open(download_path, "rb") as file:
                # Only read a small chunk for the download button
                # The full file will be streamed when downloaded
                file_header = file.read(1024 * 1024)  # Read just 1MB for the button

                st.download_button(
                    label="⬇️ Download Video",
                    data=file,  # This will stream the file instead of loading it all at once
                    file_name=download_filename,
                    mime="video/mp4"
                )
        except Exception as e:
            st.error(f"Error preparing download: {str(e)}")

        st.markdown("</div>", unsafe_allow_html=True)

        # Video preview - use file path instead of loading into memory
        # This uses HTML5 video tag with direct file path to avoid loading into memory
        try:
            # Create a small thumbnail for preview instead of loading the full video
            import subprocess

            # Extract a thumbnail from the video
            thumbnail_path = os.path.join(os.path.dirname(output_file), "thumbnail.jpg")
            ffmpeg_path = find_ffmpeg_path()

            if ffmpeg_path:
                try:
                    # Extract a frame at 1 second for thumbnail
                    subprocess.run([
                        ffmpeg_path, 
                        "-i", output_file, 
                        "-ss", "00:00:01.000", 
                        "-vframes", "1", 
                        "-q:v", "2", 
                        thumbnail_path
                    ], check=True, capture_output=True)

                    # Display thumbnail instead of full video
                    if os.path.exists(thumbnail_path):
                        st.image(thumbnail_path, caption="Video Preview (Thumbnail)")
                        st.info("Download the video to view the full content")
                    else:
                        st.warning("Video preview not available - download to view")
                except:
                    st.warning("Video preview not available - download to view")
            else:
                st.warning("Video preview not available - download to view")
        except:
            st.warning("Video preview not available - download to view")

        # Clean up
        try:
            # Clean up all temporary files
            os.remove(output_file)
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)

            # Clean up session state
            st.session_state.download_output_file = None
            st.session_state.download_status = "idle"
            st.session_state.download_progress = 0.0

            # Force garbage collection to free memory
            import gc
            gc.collect()
        except Exception as e:
            st.warning(f"Cleanup warning: {str(e)}")
            pass
    else:
        st.error("Downloaded file not found. Please try again.")
        st.session_state.download_status = "idle"
        st.session_state.download_output_file = None

# Close the card container
st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("<div class='footer'>Made with ❤️ by Sketch😘</div>", unsafe_allow_html=True)
