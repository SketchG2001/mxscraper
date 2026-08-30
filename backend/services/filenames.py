"""Filesystem-safe output names. One sanitizer for the download pipeline."""

from __future__ import annotations

import re

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_SPACES = re.compile(r"\s+")
_MAX_STEM = 80


def sanitize_filename(title: str, ext: str = "mp4") -> str:
    """Turn a content title into a single path segment: ``<safe-title>.mp4``."""
    raw = (title or "").strip() or "mxplayer_video"
    cleaned = _UNSAFE.sub("", raw)
    cleaned = _SPACES.sub(" ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "mxplayer_video"
    cleaned = cleaned[:_MAX_STEM].rstrip(" .")
    suffix = ext.lstrip(".")
    return f"{cleaned}.{suffix}"
