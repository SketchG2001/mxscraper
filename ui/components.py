"""Reusable UI components — download bar, banners, header, footer."""

from __future__ import annotations

import os
import re
import time

import streamlit as st

from downloader import cancel_download, pause_download, poll_download, resume_download
from utils import reset_download


def render_header():
    st.markdown(
        '<div class="app-header">'
        "<h1>🎬 MX Player Scraper</h1>"
        "<p>Search, browse seasons &amp; episodes, and download content</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        '<div class="app-footer">Made with ❤️ by Sketch</div>',
        unsafe_allow_html=True,
    )


def render_download_bar():
    """Show active download progress with pause / resume / cancel controls."""
    if st.session_state.dl_status not in ("downloading", "paused"):
        return

    still_running = poll_download()

    if st.session_state.dl_status in ("downloading", "paused"):
        pct = st.session_state.dl_progress
        label = "⏸️ Paused" if st.session_state.dl_status == "paused" else "⬇️ Downloading"
        st.markdown(f"### {label}: {st.session_state.dl_title}")
        st.progress(pct / 100, text=f"{pct:.1f}%")

        c1, c2, c3, _ = st.columns([1, 1, 1, 4])
        with c1:
            if st.session_state.dl_status == "downloading":
                if st.button("⏸️ Pause", use_container_width=True):
                    pause_download()
                    st.rerun()
            else:
                if st.button("▶️ Resume", use_container_width=True):
                    resume_download()
                    st.rerun()
        with c2:
            if st.button("❌ Cancel", use_container_width=True):
                cancel_download()
                st.rerun()
        with c3:
            st.caption(f"PID: {st.session_state.dl_pid}")

        st.divider()

        if still_running:
            time.sleep(2)
            st.rerun()


def render_download_complete():
    """Show completed-download banner with Save button."""
    if st.session_state.dl_status != "completed" or not st.session_state.dl_file:
        return

    out = st.session_state.dl_file
    if os.path.exists(out):
        st.success(f"**{st.session_state.dl_title}** is ready!")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            size_mb = os.path.getsize(out) / (1024 * 1024)
            st.metric("File Size", f"{size_mb:.1f} MB")
        with c2:
            safe_name = re.sub(r"[^\w\s-]", "", st.session_state.dl_title)[:50] + ".mp4"
            with open(out, "rb") as fh:
                st.download_button(
                    "⬇️  Save to Device",
                    data=fh.read(),
                    file_name=safe_name,
                    mime="video/mp4",
                    use_container_width=True,
                )
        with c3:
            if st.button("✕  Dismiss", use_container_width=True):
                try:
                    os.remove(out)
                except OSError:
                    pass
                reset_download()
                st.rerun()
        st.divider()
    else:
        reset_download()


def render_download_error():
    """Show error banner if download failed."""
    if st.session_state.dl_status != "error":
        return
    st.error(st.session_state.dl_error or "An error occurred during download.")
    if st.button("🔄  Dismiss Error"):
        reset_download()
        st.rerun()
    st.divider()
