"""Download pipeline — background yt-dlp subprocess + Selenium fallback."""

from __future__ import annotations

import json
import os
import platform
import random
import re
import signal
import subprocess
import tempfile
import time

import streamlit as st

from api import MXPlayerAPI, extract_seasons, stream_url as parse_stream_url
from config import USER_AGENTS
from utils import find_ffmpeg, is_pid_alive, name_from_url, reset_download


def start_download(
    stream_url: str,
    title: str,
    audio_lang: str | None = None,
    quality: str | None = None,
):
    """Launch yt-dlp in background, store Popen object for tracking.

    Args:
        stream_url: HLS/DASH URL.
        title: Display title for progress bar.
        audio_lang: Optional ISO language code (e.g. "hi", "en") to prefer.
        quality: Optional stream option key (e.g. "hls_high") — if provided
                 and it looks like a full URL, it overrides stream_url.
    """
    if quality and quality.startswith("http"):
        stream_url = quality

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        st.session_state.dl_status = "error"
        st.session_state.dl_error = "FFmpeg not found. Please install FFmpeg and try again."
        return

    safe = re.sub(r"[^\w\s-]", "", title)[:60] or "mxplayer_video"
    tmp = tempfile.mkdtemp()
    out_path = os.path.join(tmp, safe + f"_{int(time.time())}.mp4")
    log_path = os.path.join(tmp, "dl.log")

    cmd = [
        "yt-dlp",
        "--ffmpeg-location", ffmpeg,
        "--no-warnings", "--no-part", "--no-check-certificate",
        "--newline",
        "-o", out_path,
    ]

    if audio_lang:
        cmd.extend(["--audio-multistreams", "--format",
                     f"bv*+ba[language={audio_lang}]/bv*+ba/best"])

    cmd.append(stream_url)

    log_fd = open(log_path, "w")
    proc = subprocess.Popen(cmd, stdout=log_fd, stderr=subprocess.STDOUT)

    st.session_state.dl_pid = proc.pid
    st.session_state.dl_proc = proc
    st.session_state.dl_log = log_path
    st.session_state.dl_file = out_path
    st.session_state.dl_status = "downloading"
    st.session_state.dl_title = title
    st.session_state.dl_progress = 0.0
    st.session_state.dl_error = None


def poll_download() -> bool:
    """Read log for progress, check if process still alive. Returns True if running."""
    proc: subprocess.Popen | None = st.session_state.get("dl_proc")
    pid = st.session_state.get("dl_pid")
    if not proc and not pid:
        return False

    if proc is not None:
        alive = proc.poll() is None
    else:
        alive = is_pid_alive(pid)

    log_path = st.session_state.get("dl_log", "")
    if log_path and os.path.exists(log_path):
        try:
            with open(log_path) as f:
                for line in f:
                    m = re.search(r"(\d+\.?\d*)%", line)
                    if m:
                        st.session_state.dl_progress = min(float(m.group(1)), 100.0)
        except Exception:
            pass

    if not alive:
        out_path = st.session_state.get("dl_file", "")
        if out_path and not os.path.exists(out_path):
            out_dir = os.path.dirname(out_path)
            base = os.path.splitext(os.path.basename(out_path))[0]
            for fname in os.listdir(out_dir):
                if fname.startswith(base) and not fname.endswith(".log"):
                    out_path = os.path.join(out_dir, fname)
                    st.session_state.dl_file = out_path
                    break
        if out_path and os.path.exists(out_path) and os.path.getsize(out_path) > 10_000:
            st.session_state.dl_status = "completed"
            st.session_state.dl_progress = 100.0
        else:
            st.session_state.dl_status = "error"
            error_msg = "Download failed."
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path) as f:
                        for line in f:
                            if "ERROR" in line:
                                error_msg = line.strip()
                except Exception:
                    pass
            st.session_state.dl_error = error_msg

    return alive


def cancel_download():
    pid = st.session_state.get("dl_pid")
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    reset_download()


def pause_download():
    pid = st.session_state.get("dl_pid")
    if pid and platform.system() != "Windows":
        try:
            os.kill(pid, signal.SIGSTOP)
            st.session_state.dl_status = "paused"
        except (ProcessLookupError, PermissionError):
            pass


def resume_download():
    pid = st.session_state.get("dl_pid")
    if pid and platform.system() != "Windows":
        try:
            os.kill(pid, signal.SIGCONT)
            st.session_state.dl_status = "downloading"
        except (ProcessLookupError, PermissionError):
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Selenium fallback
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def selenium_extract_and_resolve(url: str, api: MXPlayerAPI):
    """Extract stream URL via Selenium, then resolve URL to show related content.

    Never auto-downloads — always shows content details first so the user
    can choose what to download.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    with st.status("Extracting video from page...", expanded=True) as status:
        progress = st.progress(0.0, text="Starting browser...")

        opts = Options()
        for flag in (
            "--headless", "--no-sandbox", "--disable-dev-shm-usage",
            "--disable-gpu", "--disable-blink-features=AutomationControlled",
        ):
            opts.add_argument(flag)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        drv_path = os.getenv("CHROMEDRIVER_PATH")
        if not drv_path:
            render = "./chromedriver/chromedriver"
            if os.path.exists(render):
                drv_path = render
        svc = (
            Service(drv_path) if drv_path
            else Service(ChromeDriverManager().install())
        )

        try:
            driver = webdriver.Chrome(service=svc, options=opts)
        except Exception as e:
            status.update(label="Browser failed to start", state="error")
            st.error(f"Could not start Chrome: {e}")
            return

        found_stream = None
        try:
            progress.progress(0.15, text="Loading page...")
            driver.get(url)
            time.sleep(random.uniform(4, 7))
            driver.execute_script(f"window.scrollTo(0, {random.randint(100, 300)});")
            time.sleep(random.uniform(1, 2))
            progress.progress(0.35, text="Scanning network logs...")

            urls: list[str] = []
            for entry in driver.get_log("performance"):
                try:
                    msg = json.loads(entry["message"])
                    if "Network.responseReceived" in msg["message"]["method"]:
                        rid = msg["message"]["params"]["requestId"]
                        body = driver.execute_cdp_cmd(
                            "Network.getResponseBody", {"requestId": rid}
                        ).get("body", "")
                        urls.extend(re.findall(r'https://[^\s\'"]+\.m3u8', body))
                        urls.extend(re.findall(r'https://[^\s\'"]+\.mpd', body))
                except Exception:
                    continue

            if urls:
                found_stream = urls[0]
                progress.progress(0.50, text="Stream found!")
            else:
                status.update(label="No video stream found", state="error")
                st.error("Could not find any video stream on this page.")
                return
        finally:
            driver.quit()

        progress.progress(0.60, text="Looking up related content...")
        resolved = api.resolve_url(url)

        if resolved and resolved.get("parsed"):
            st.session_state.selected_content = resolved["parsed"]
            if resolved["type"] == "tvshow" and resolved.get("detail"):
                st.session_state.show_detail = resolved["detail"]
                st.session_state.seasons = extract_seasons(resolved["detail"])
            st.session_state.page = "detail"
            status.update(label="Content loaded — browse & download below!", state="complete")
            st.rerun()
        elif found_stream:
            title_guess = name_from_url(url) or "MX Player Video"
            st.session_state.selected_content = {
                "id": "", "title": title_guess, "type": "video",
                "description": f"Extracted from: {url}",
                "image": "", "stream_url": found_stream, "drm": False,
                "duration": 0, "sequence": "", "year": "", "rating": "",
                "languages": [], "genres": [], "shareUrl": "",
                "firstVideo": None, "container": {},
                "publisher": "", "contributors": [],
            }
            st.session_state.page = "detail"
            status.update(label="Video found — click download below!", state="complete")
            st.rerun()
