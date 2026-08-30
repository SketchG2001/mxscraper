"""Download API contracts. MX and yt-dlp are mocked."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

def _ready(monkeypatch, tmp_path):
    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "available")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: str(tmp_path / "ff"))
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)

    def fake(url, opts):
        dest = Path(str(opts["outtmpl"]).replace(".%(ext)s", ".mp4"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x" * 20_000)
        for hook in opts.get("progress_hooks", []):
            hook({"status": "downloading", "downloaded_bytes": 20_000, "total_bytes": 20_000})
            hook({"status": "finished"})

    monkeypatch.setattr("services.download.invoke_ytdlp", fake)
    monkeypatch.setattr("routers.download.get_manager", lambda: __import__(
        "services.download", fromlist=["DownloadManager"]
    ).DownloadManager(ytdlp=fake))


def test_drm_rejected(
    client: TestClient,
    mock_api: MagicMock,
    monkeypatch,
    tmp_path,
):
    _ready(monkeypatch, tmp_path)
    mock_api.get_collection.return_value = (
        {
            "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
            "title": "Protected",
            "type": "movie",
            "stream": {
                "hls": {"main": "https://llvod.mxplay.com/main.m3u8"},
                "drmProtect": True,
            },
        },
        None,
    )
    res = client.post(
        "/api/downloads",
        json={"content_id": "aaaaaaaaaaaaaaaaaaaaaaaa", "type": "movie", "title": "Protected"},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "This content is protected and cannot be downloaded."


def test_create_get_cancel(
    client: TestClient,
    mock_api: MagicMock,
    monkeypatch,
    tmp_path,
):
    hold = __import__("threading").Event()

    def block(url, opts):
        hold.wait(2)
        from services.download import DownloadCancelled

        raise DownloadCancelled()

    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "available")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: str(tmp_path / "ff"))
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)
    from services.download import DownloadManager, reset_manager

    reset_manager()
    mgr = DownloadManager(ytdlp=block)
    monkeypatch.setattr("routers.download.get_manager", lambda: mgr)
    mock_api.get_collection.return_value = (
        {
            "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
            "title": "Sample Movie",
            "type": "movie",
            "stream": {
                "hls": {"main": "https://llvod.mxplay.com/main.m3u8"},
                "drmProtect": False,
            },
        },
        None,
    )
    created = client.post(
        "/api/downloads",
        json={"content_id": "aaaaaaaaaaaaaaaaaaaaaaaa", "type": "movie", "title": "Sample Movie"},
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]
    assert created.json()["status"] in {"queued", "downloading"}

    got = client.get(f"/api/downloads/{job_id}")
    assert got.status_code == 200
    assert got.json()["job_id"] == job_id
    assert "output_path" not in got.json()

    cancelled = client.post(f"/api/downloads/{job_id}/cancel")
    assert cancelled.status_code == 200
    hold.set()
    for _ in range(50):
        body = client.get(f"/api/downloads/{job_id}").json()
        if body["status"] == "cancelled":
            break
        time.sleep(0.02)
    assert body["status"] == "cancelled"


def test_rejects_arbitrary_url_field(client: TestClient):
    res = client.post(
        "/api/downloads",
        json={"url": "https://example.com/secret.m3u8"},
    )
    assert res.status_code == 422
