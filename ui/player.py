"""Ad-free video player using Video.js, served as a static file.

The player is loaded via components.iframe() which grants
``allow-same-origin``, and all HLS requests are routed through our
local CORS proxy so the CDN's missing CORS headers are irrelevant.
"""

from __future__ import annotations

import base64
import json
import urllib.parse

import streamlit as st
import streamlit.components.v1 as components

from proxy import PROXY_PORT


def render_player(
    stream_url: str,
    title: str = "",
    height: int = 560,
    playlist: dict | None = None,
):
    """Embed the Video.js player in an iframe.

    *playlist* is an optional dict with structure::

        {
            "current": 0,          # index of the episode being played
            "episodes": [
                {"title": "...", "url": "https://...", "seq": 1},
                ...
            ]
        }

    It is base64-encoded and appended as a URL hash fragment so the
    player can support "next episode" auto-advance without parent
    communication.
    """
    params = urllib.parse.urlencode({
        "url": stream_url,
        "title": title,
        "proxy": str(PROXY_PORT),
    })
    url = f"/app/static/player.html?{params}"

    if playlist and playlist.get("episodes"):
        payload = base64.b64encode(json.dumps(playlist).encode()).decode()
        url += f"#{payload}"

    components.iframe(url, height=height, scrolling=False)


def render_external_player_link(stream_url: str, title: str = ""):
    """Copyable stream URL + open-in-browser fallback."""
    col1, col2 = st.columns(2)
    with col1:
        st.link_button(
            "🌐 Open stream in browser",
            stream_url,
            use_container_width=True,
        )
    with col2:
        st.code(stream_url, language=None)
        st.caption("Copy URL → open in VLC / mpv")
