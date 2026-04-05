"""Strip stream URLs from MX API dicts for public JSON responses."""

from __future__ import annotations

_HIDDEN = frozenset({"stream_url", "stream_options", "firstVideo", "container"})


def strip_stream_fields(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in _HIDDEN}
