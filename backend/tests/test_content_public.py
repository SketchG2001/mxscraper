"""Public JSON must not expose playable stream fields."""

from __future__ import annotations

from content_public import strip_stream_fields
from services.mx_api import parse_item

HIDDEN = ("stream_url", "stream_options", "firstVideo", "container")


def test_strips_top_level_stream_fields():
    cleaned = strip_stream_fields(
        {
            "id": "1",
            "title": "Public",
            "stream_url": "https://secret.example/a.m3u8",
            "stream_options": {"hls_high": "https://secret.example/h.m3u8"},
            "firstVideo": {"id": "inner"},
            "container": {"id": "c"},
            "drm": False,
        }
    )
    assert cleaned == {"id": "1", "title": "Public", "drm": False}
    for key in HIDDEN:
        assert key not in cleaned


def test_parse_item_then_strip_matches_router_path():
    raw = {
        "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Movie",
        "type": "movie",
        "stream": {
            "hls": {"main": "https://llvod.mxplay.com/main.m3u8"},
            "drmProtect": False,
        },
        "firstVideo": {"id": "fv"},
        "container": {"id": "box"},
    }
    parsed = parse_item(raw)
    assert parsed is not None
    assert parsed["stream_url"]
    assert parsed["stream_options"]

    public = strip_stream_fields(parsed)
    assert "stream_url" not in public
    assert "stream_options" not in public
    assert "firstVideo" not in public
    assert "container" not in public
    assert public["id"] == "aaaaaaaaaaaaaaaaaaaaaaaa"
    assert public["title"] == "Movie"


def test_nested_stream_url_is_not_walked():
    """Current helper is shallow. Routers only pass flat parse_item dicts."""
    cleaned = strip_stream_fields(
        {
            "id": "1",
            "nested": {"stream_url": "https://secret.example/nested.m3u8"},
        }
    )
    assert cleaned["nested"]["stream_url"] == "https://secret.example/nested.m3u8"


def test_does_not_mutate_input():
    original = {"id": "1", "stream_url": "https://secret.example/a.m3u8"}
    strip_stream_fields(original)
    assert original["stream_url"] == "https://secret.example/a.m3u8"
