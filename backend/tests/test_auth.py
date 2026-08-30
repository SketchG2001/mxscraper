"""Stream is public (Auth0 removed)."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

MOVIE_DETAIL = {
    "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
    "title": "Sample Movie",
    "type": "movie",
    "stream": {
        "hls": {"main": "https://llvod.mxplay.com/main.m3u8"},
        "drmProtect": False,
    },
}


def test_stream_ok_without_token(client: TestClient, mock_api: MagicMock):
    mock_api.get_collection.return_value = (MOVIE_DETAIL, None)
    res = client.get(
        "/api/stream/aaaaaaaaaaaaaaaaaaaaaaaa",
        params={"type": "movie"},
    )
    assert res.status_code == 200
    assert res.json()["stream_url"] == "https://llvod.mxplay.com/main.m3u8"
    mock_api.get_collection.assert_called_once()
