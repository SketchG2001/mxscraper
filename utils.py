"""Utility functions — ffmpeg detection, formatting, session state helpers."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path

import streamlit as st

from config import SESSION_DEFAULTS


def find_ffmpeg() -> str | None:
    """Locate an ffmpeg binary on the system."""
    env = os.getenv("FFMPEG_PATH")
    if env and os.path.exists(env):
        return env
    try:
        cmd = "where" if platform.system() == "Windows" else "which"
        return (
            subprocess.run([cmd, "ffmpeg"], capture_output=True, text=True, check=True)
            .stdout.strip()
            .split("\n")[0]
        )
    except subprocess.CalledProcessError:
        candidates = (
            ["ffmpeg.exe", str(Path(__file__).parent / "ffmpeg.exe")]
            if platform.system() == "Windows"
            else [
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/opt/homebrew/bin/ffmpeg",
                "/app/bin/ffmpeg",
            ]
        )
        return next((p for p in candidates if os.path.exists(p)), None)


def format_duration(seconds) -> str:
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return ""
    if s <= 0:
        return ""
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def type_from_url(url: str) -> str:
    low = url.lower()
    if "/movie/" in low:
        return "movie"
    if "/show/" in low:
        return "tvshow"
    return "video"


def name_from_url(url: str) -> str:
    """Extract a human-readable name from a MX Player URL slug."""
    for part in url.rstrip("/").split("/"):
        if "watch-" in part:
            clean = re.sub(
                r"-(online|free|full|hd|episodes?|season|all)\b", "", part.replace("watch-", "")
            )
            return clean.replace("-", " ").strip()
    return ""


# ── Session state helpers ─────────────────────────────────


def reset_download():
    for key in ("dl_status", "dl_progress", "dl_file", "dl_title", "dl_error", "dl_pid", "dl_proc", "dl_log"):
        st.session_state[key] = SESSION_DEFAULTS[key]


def go_home():
    st.session_state.page = "home"
    st.session_state.selected_content = None
    st.session_state.show_detail = None
    st.session_state.seasons = []
    st.session_state.episodes = []
    st.session_state.sel_season_idx = 0
    st.session_state.episodes_season_id = None
    st.session_state.playing_episode_id = None


def is_pid_alive(pid: int) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
