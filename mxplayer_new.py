import os
import re
import json
import time
import subprocess
import streamlit as st
import tempfile
import platform
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mxplayer_downloader')

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
        logger.info(f"Starting video processing for URL: {url}")
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

        # Enhanced anti-bot detection settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Additional anti-detection measures
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")

        # Disable automation-specific features
        chrome_options.add_argument("--disable-automation")

        # Randomize user agent slightly to avoid fingerprinting
        import random
        chrome_versions = ["125.0.0.0", "124.0.0.0", "123.0.0.0"]
        random_chrome = random.choice(chrome_versions)

        # More realistic user agent
        chrome_options.add_argument(
            f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random_chrome} Safari/537.36"
        )

        # Add common headers that browsers typically send
        chrome_options.add_argument("--accept-lang=en-US,en;q=0.9")
        chrome_options.add_argument("--accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8")
        chrome_options.add_argument("--accept-encoding=gzip, deflate, br")

        # Setup performance logging
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})

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
                logger.info(f"Using pre-installed Chrome binary at: {chrome_binary_path}")
                logger.info(f"Using pre-installed Chromedriver at: {chromedriver_path}")
                chrome_options.binary_location = chrome_binary_path
                service = Service(executable_path=chromedriver_path)
            else:
                # Local development, use ChromeDriverManager
                logger.info("Chrome binary not found, using ChromeDriverManager")
                service = Service(ChromeDriverManager().install())

            driver = webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException as e:
            return None, f"Failed to start Chrome: {str(e)}"

        try:
            # Navigate to MX Player URL
            progress_callback(0.2, "Navigating to MX Player...")
            logger.info(f"Navigating to URL: {url}")
            driver.get(url)

            # Increase wait time for Render environment
            progress_callback(0.25, "Waiting for page to load (this may take longer on Render)...")
            logger.info("Waiting 15 seconds for page to load")
            time.sleep(15)  # Increased from 5 to 15 seconds

            # Check if page has loaded properly
            page_title = driver.title
            logger.info(f"Page title: {page_title}")
            page_url = driver.current_url
            logger.info(f"Current URL: {page_url}")

            # Check if we've been redirected to a login page or error page
            if "login" in page_url.lower() or "error" in page_url.lower():
                logger.warning(f"Possible redirect detected to: {page_url}")
                progress_callback(0.26, "Detected possible redirect, attempting to continue...")

            # Execute JavaScript to scroll down and trigger more content loading
            logger.info("Scrolling to trigger lazy-loaded content")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight*3/4);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Try to click on any play buttons that might be present
            try:
                logger.info("Attempting to click on play buttons if present")
                driver.execute_script("""
                    var playButtons = document.querySelectorAll('button[aria-label="Play"], .play-icon, [class*="play"], [id*="play"]');
                    for(var i = 0; i < playButtons.length; i++) {
                        playButtons[i].click();
                    }
                """)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Error clicking play buttons: {str(e)}")

            # Wait for video elements to appear
            try:
                logger.info("Checking for video elements on the page")
                video_count = driver.execute_script("return document.querySelectorAll('video').length")
                logger.info(f"Found {video_count} video elements on page")
            except Exception as e:
                logger.warning(f"Error checking video elements: {str(e)}")

            # Extract video URLs from performance logs
            progress_callback(0.3, "Extracting video information...")

            # Try multiple methods to extract video URLs
            video_urls = []

            # Method 1: Performance logs
            try:
                logger.info("Extracting video URLs from performance logs")
                logs = driver.get_log("performance")
                logger.info(f"Retrieved {len(logs)} performance log entries")

                for log in logs:
                    try:
                        message = json.loads(log["message"])
                        if "Network.responseReceived" in message["message"]["method"]:
                            request_id = message["message"]["params"]["requestId"]
                            request = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                            body = request.get("body", "")
                            if ".m3u8" in body or ".mpd" in body:
                                m3u8_urls = re.findall(r'https://[^\s\'"]+\.m3u8', body)
                                mpd_urls = re.findall(r'https://[^\s\'"]+\.mpd', body)
                                if m3u8_urls or mpd_urls:
                                    logger.info(f"Found video URLs in response: {len(m3u8_urls)} m3u8, {len(mpd_urls)} mpd")
                                video_urls.extend(m3u8_urls)
                                video_urls.extend(mpd_urls)
                    except Exception as e:
                        error_msg = f"Log processing error (non-critical): {str(e)}"
                        logger.warning(error_msg)
                        progress_callback(0.3, error_msg)
                        continue
            except Exception as e:
                error_msg = f"Performance log extraction failed: {str(e)}"
                logger.error(error_msg)
                progress_callback(0.3, error_msg)

            # Method 2: Direct page source analysis
            if not video_urls:
                progress_callback(0.35, "Trying alternative extraction method...")
                logger.info("Trying direct page source analysis for video URLs")
                page_source = driver.page_source
                page_size = len(page_source)
                logger.info(f"Retrieved page source (size: {page_size} bytes)")

                m3u8_urls = re.findall(r'https://[^\s\'"]+\.m3u8', page_source)
                mpd_urls = re.findall(r'https://[^\s\'"]+\.mpd', page_source)

                if m3u8_urls or mpd_urls:
                    logger.info(f"Found video URLs in page source: {len(m3u8_urls)} m3u8, {len(mpd_urls)} mpd")
                else:
                    logger.warning("No video URLs found in page source")

                video_urls.extend(m3u8_urls)
                video_urls.extend(mpd_urls)

            # Method 3: Execute JavaScript to find video elements
            if not video_urls:
                progress_callback(0.36, "Trying JavaScript extraction method...")
                logger.info("Trying JavaScript extraction for video elements")
                try:
                    # Try to extract from video elements
                    video_elements = driver.execute_script("""
                        var videos = [];
                        var videoElements = document.querySelectorAll('video');
                        for(var i = 0; i < videoElements.length; i++) {
                            if(videoElements[i].src) videos.push(videoElements[i].src);
                        }
                        return videos;
                    """)

                    logger.info(f"Found {len(video_elements)} video elements via JavaScript")
                    filtered_urls = [url for url in video_elements if url.endswith('.m3u8') or url.endswith('.mpd')]
                    if filtered_urls:
                        logger.info(f"Found {len(filtered_urls)} valid video URLs from video elements")
                    video_urls.extend(filtered_urls)
                except Exception as e:
                    error_msg = f"JavaScript extraction failed: {str(e)}"
                    logger.error(error_msg)
                    progress_callback(0.36, error_msg)

            # Method 4: Try to extract from video.js player if present
            if not video_urls:
                progress_callback(0.37, "Trying video.js player extraction...")
                logger.info("Attempting to extract from video.js player if present")
                try:
                    videojs_urls = driver.execute_script("""
                        var sources = [];
                        // Check if videojs is defined
                        if (typeof videojs !== 'undefined') {
                            var players = videojs.getPlayers();
                            for (var playerId in players) {
                                if (players.hasOwnProperty(playerId)) {
                                    var player = players[playerId];
                                    if (player && player.src) {
                                        sources.push(player.src());
                                    }
                                }
                            }
                        }
                        return sources;
                    """)

                    if videojs_urls and len(videojs_urls) > 0:
                        logger.info(f"Found {len(videojs_urls)} URLs from video.js player")
                        filtered_urls = [url for url in videojs_urls if url.endswith('.m3u8') or url.endswith('.mpd')]
                        if filtered_urls:
                            logger.info(f"Found {len(filtered_urls)} valid video URLs from video.js player")
                        video_urls.extend(filtered_urls)
                except Exception as e:
                    logger.warning(f"Video.js extraction failed: {str(e)}")

            # Method 5: Try to extract from network requests directly
            if not video_urls:
                progress_callback(0.38, "Analyzing network requests...")
                logger.info("Attempting to extract from network requests directly")
                try:
                    # Execute JavaScript to find network requests with video content
                    network_urls = driver.execute_script("""
                        return window.performance.getEntries()
                            .filter(entry => entry.name && (
                                entry.name.includes('.m3u8') || 
                                entry.name.includes('.mpd') || 
                                entry.name.includes('/stream/') ||
                                entry.name.includes('/video/') ||
                                entry.name.includes('/content/') ||
                                entry.name.includes('/media/')
                            ))
                            .map(entry => entry.name);
                    """)

                    if network_urls and len(network_urls) > 0:
                        logger.info(f"Found {len(network_urls)} potential video URLs from network requests")
                        for url in network_urls:
                            logger.info(f"Network request URL: {url[:100]}...")
                            if url.endswith('.m3u8') or url.endswith('.mpd'):
                                logger.info(f"Found valid streaming URL from network: {url[:50]}...")
                                video_urls.append(url)
                except Exception as e:
                    logger.warning(f"Network request extraction failed: {str(e)}")

            # Log the number of URLs found for debugging
            progress_callback(0.37, f"Found {len(video_urls)} potential video URLs")

            # If no URLs found, try refreshing the page and extracting again (up to 3 attempts)
            attempts = 1
            max_attempts = 3

            while not video_urls and attempts < max_attempts:
                attempts += 1
                progress_callback(0.4, f"No URLs found. Retrying (attempt {attempts}/{max_attempts})...")
                logger.info(f"No URLs found. Starting retry attempt {attempts}/{max_attempts}")

                # Refresh the page
                logger.info("Refreshing the page")
                driver.refresh()
                time.sleep(10)  # Wait after refresh

                # Scroll again
                logger.info("Scrolling page to trigger content loading")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight*3/4);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                # Try to click on any play buttons again
                try:
                    logger.info("Retry: Attempting to click on play buttons")
                    driver.execute_script("""
                        var playButtons = document.querySelectorAll('button[aria-label="Play"], .play-icon, [class*="play"], [id*="play"]');
                        for(var i = 0; i < playButtons.length; i++) {
                            playButtons[i].click();
                        }
                    """)
                    time.sleep(2)
                except Exception as e:
                    logger.warning(f"Retry: Error clicking play buttons: {str(e)}")

                # Try extraction methods again
                try:
                    # Method 1: Performance logs
                    logger.info("Retry: Extracting from performance logs")
                    logs = driver.get_log("performance")
                    logger.info(f"Retry: Retrieved {len(logs)} performance log entries")

                    for log in logs:
                        try:
                            message = json.loads(log["message"])
                            if "Network.responseReceived" in message["message"]["method"]:
                                request_id = message["message"]["params"]["requestId"]
                                request = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                                body = request.get("body", "")
                                if ".m3u8" in body or ".mpd" in body:
                                    m3u8_urls = re.findall(r'https://[^\s\'"]+\.m3u8', body)
                                    mpd_urls = re.findall(r'https://[^\s\'"]+\.mpd', body)
                                    if m3u8_urls or mpd_urls:
                                        logger.info(f"Retry: Found URLs in response: {len(m3u8_urls)} m3u8, {len(mpd_urls)} mpd")
                                    video_urls.extend(m3u8_urls)
                                    video_urls.extend(mpd_urls)
                        except Exception as e:
                            logger.warning(f"Retry: Log processing error: {str(e)}")
                            continue
                except Exception as e:
                    error_msg = f"Retry performance log extraction failed: {str(e)}"
                    logger.error(error_msg)
                    progress_callback(0.41, error_msg)

                # Method 2: Direct page source
                if not video_urls:
                    logger.info("Retry: Trying direct page source analysis")
                    page_source = driver.page_source
                    page_size = len(page_source)
                    logger.info(f"Retry: Retrieved page source (size: {page_size} bytes)")

                    m3u8_urls = re.findall(r'https://[^\s\'"]+\.m3u8', page_source)
                    mpd_urls = re.findall(r'https://[^\s\'"]+\.mpd', page_source)

                    if m3u8_urls or mpd_urls:
                        logger.info(f"Retry: Found URLs in page source: {len(m3u8_urls)} m3u8, {len(mpd_urls)} mpd")
                    video_urls.extend(m3u8_urls)
                    video_urls.extend(mpd_urls)

                # Method 3: JavaScript extraction
                if not video_urls:
                    logger.info("Retry: Trying JavaScript extraction for video elements")
                    try:
                        video_elements = driver.execute_script("""
                            var videos = [];
                            var videoElements = document.querySelectorAll('video');
                            for(var i = 0; i < videoElements.length; i++) {
                                if(videoElements[i].src) videos.push(videoElements[i].src);
                            }
                            return videos;
                        """)

                        logger.info(f"Retry: Found {len(video_elements)} video elements via JavaScript")
                        filtered_urls = [url for url in video_elements if url.endswith('.m3u8') or url.endswith('.mpd')]
                        if filtered_urls:
                            logger.info(f"Retry: Found {len(filtered_urls)} valid video URLs from video elements")
                        video_urls.extend(filtered_urls)
                    except Exception as e:
                        logger.warning(f"Retry: JavaScript extraction failed: {str(e)}")

                # Method 4: Video.js extraction
                if not video_urls:
                    logger.info("Retry: Attempting to extract from video.js player")
                    try:
                        videojs_urls = driver.execute_script("""
                            var sources = [];
                            if (typeof videojs !== 'undefined') {
                                var players = videojs.getPlayers();
                                for (var playerId in players) {
                                    if (players.hasOwnProperty(playerId)) {
                                        var player = players[playerId];
                                        if (player && player.src) {
                                            sources.push(player.src());
                                        }
                                    }
                                }
                            }
                            return sources;
                        """)

                        if videojs_urls and len(videojs_urls) > 0:
                            logger.info(f"Retry: Found {len(videojs_urls)} URLs from video.js player")
                            filtered_urls = [url for url in videojs_urls if url.endswith('.m3u8') or url.endswith('.mpd')]
                            if filtered_urls:
                                logger.info(f"Retry: Found {len(filtered_urls)} valid video URLs from video.js player")
                            video_urls.extend(filtered_urls)
                    except Exception as e:
                        logger.warning(f"Retry: Video.js extraction failed: {str(e)}")

                # Method 5: Network requests
                if not video_urls:
                    logger.info("Retry: Attempting to extract from network requests")
                    try:
                        network_urls = driver.execute_script("""
                            return window.performance.getEntries()
                                .filter(entry => entry.name && (
                                    entry.name.includes('.m3u8') || 
                                    entry.name.includes('.mpd') || 
                                    entry.name.includes('/stream/') ||
                                    entry.name.includes('/video/') ||
                                    entry.name.includes('/content/') ||
                                    entry.name.includes('/media/')
                                ))
                                .map(entry => entry.name);
                        """)

                        if network_urls and len(network_urls) > 0:
                            logger.info(f"Retry: Found {len(network_urls)} potential video URLs from network requests")
                            for url in network_urls:
                                logger.info(f"Retry: Network request URL: {url[:100]}...")
                                if url.endswith('.m3u8') or url.endswith('.mpd'):
                                    logger.info(f"Retry: Found valid streaming URL from network: {url[:50]}...")
                                    video_urls.append(url)
                    except Exception as e:
                        logger.warning(f"Retry: Network request extraction failed: {str(e)}")

                logger.info(f"Retry attempt {attempts} complete: Found {len(video_urls)} potential video URLs")
                progress_callback(0.42, f"Retry attempt {attempts}: Found {len(video_urls)} potential video URLs")

            # Final fallback: Try using yt-dlp's built-in extraction capabilities
            if not video_urls:
                progress_callback(0.43, "Trying direct yt-dlp extraction as last resort...")
                logger.info("Starting direct yt-dlp extraction as final fallback")
                try:
                    # First try with standard options
                    cmd = [
                        "yt-dlp",
                        "--no-warnings",
                        "--no-check-certificate",
                        "--get-url",
                        url
                    ]

                    logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True)

                    # Process the result
                    if result.returncode == 0 and result.stdout.strip():
                        logger.info("yt-dlp command executed successfully")
                        extracted_urls = result.stdout.strip().split('\n')
                        logger.info(f"yt-dlp extracted {len(extracted_urls)} raw URLs")

                        for extracted_url in extracted_urls:
                            if extracted_url.endswith('.m3u8') or extracted_url.endswith('.mpd'):
                                logger.info(f"Found valid streaming URL: {extracted_url[:50]}...")
                                video_urls.append(extracted_url)
                    else:
                        logger.warning("First yt-dlp attempt failed or returned empty output")
                        if result.stderr:
                            logger.warning(f"yt-dlp error output: {result.stderr}")

                        # Try with additional options for MX Player
                        logger.info("Trying yt-dlp with additional options for MX Player")
                        cmd = [
                            "yt-dlp",
                            "--no-warnings",
                            "--no-check-certificate",
                            "--referer", "https://www.mxplayer.in/",
                            "--add-header", "Origin:https://www.mxplayer.in",
                            "--add-header", f"User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                            "--get-url",
                            "--extractor-args", "generic:force_generic_extractor=true",
                            url
                        ]

                        logger.info(f"Running enhanced yt-dlp command: {' '.join(cmd)}")
                        result = subprocess.run(cmd, capture_output=True, text=True)

                        if result.returncode == 0 and result.stdout.strip():
                            logger.info("Enhanced yt-dlp command executed successfully")
                            extracted_urls = result.stdout.strip().split('\n')
                            logger.info(f"Enhanced yt-dlp extracted {len(extracted_urls)} raw URLs")

                            for extracted_url in extracted_urls:
                                if extracted_url.endswith('.m3u8') or extracted_url.endswith('.mpd'):
                                    logger.info(f"Found valid streaming URL: {extracted_url[:50]}...")
                                    video_urls.append(extracted_url)
                        else:
                            # Try one more time with --dump-pages to see the HTML content
                            logger.warning("Enhanced yt-dlp attempt failed or returned empty output")
                            if result.stderr:
                                logger.warning(f"Enhanced yt-dlp error output: {result.stderr}")

                            # Try to get debug info to understand the issue
                            logger.info("Trying to get debug info from yt-dlp")
                            debug_cmd = [
                                "yt-dlp",
                                "--dump-pages",
                                "--no-check-certificate",
                                "--verbose",
                                url
                            ]

                            try:
                                debug_result = subprocess.run(debug_cmd, capture_output=True, text=True, timeout=30)
                                if debug_result.stdout:
                                    # Log only the first 500 characters to avoid overwhelming the logs
                                    logger.info(f"yt-dlp debug output (truncated): {debug_result.stdout[:500]}...")
                                if debug_result.stderr:
                                    logger.info(f"yt-dlp debug errors: {debug_result.stderr}")
                            except subprocess.TimeoutExpired:
                                logger.warning("yt-dlp debug command timed out")
                            except Exception as e:
                                logger.warning(f"Error running yt-dlp debug command: {str(e)}")

                    progress_callback(0.44, f"Direct yt-dlp extraction found {len(video_urls)} URLs")
                except Exception as e:
                    error_msg = f"Direct yt-dlp extraction failed: {str(e)}"
                    logger.error(error_msg)
                    progress_callback(0.44, error_msg)

            if not video_urls:
                return None, "No video URLs found after multiple attempts. Please check the URL and try again."

            # Download video using yt-dlp
            progress_callback(0.45, "Preparing to download...")

            # yt-dlp is already installed via requirements.txt
            progress_callback(0.48, "Preparing yt-dlp...")

            # Start download
            progress_callback(0.5, "Downloading video...")

            # Command to download video
            logger.info(f"Starting video download using URL: {video_urls[0][:50]}...")
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
            logger.info(f"Download command: {' '.join(cmd)}")

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
