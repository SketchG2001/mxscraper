"""Download manager tests. yt-dlp is mocked at the invoke boundary."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from services.download import (
    DownloadCancelled,
    DownloadManager,
    DownloadRejected,
)


def _ok_ytdlp(url: str, opts: dict) -> None:
    dest = Path(str(opts["outtmpl"]).replace(".%(ext)s", ".mp4"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"x" * 20_000)
    for hook in opts.get("progress_hooks", []):
        hook(
            {
                "status": "downloading",
                "downloaded_bytes": 10_000,
                "total_bytes": 20_000,
                "speed": 1000,
                "eta": 10,
            }
        )
        hook({"status": "finished", "filename": str(dest)})


def test_successful_download(monkeypatch, tmp_path):
    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "available")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: str(tmp_path / "ffmpeg"))
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)
    mgr = DownloadManager(ytdlp=_ok_ytdlp)
    job = mgr.create(content_id="abc", title="Sample / Movie", stream_url="https://cdn.example/a.m3u8")
    for _ in range(50):
        if job.status == "completed":
            break
        time.sleep(0.02)
    assert job.status == "completed"
    assert job.file_available is True
    assert job.filename == "Sample Movie.mp4"
    assert job.progress == 100.0
    assert Path(job.output_path).is_file()


def test_failure(monkeypatch, tmp_path):
    def boom(url, opts):
        raise RuntimeError("network boom")

    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "available")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: str(tmp_path / "ffmpeg"))
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)
    mgr = DownloadManager(ytdlp=boom)
    job = mgr.create(content_id="abc", title="X", stream_url="https://cdn.example/a.m3u8")
    for _ in range(50):
        if job.status == "failed":
            break
        time.sleep(0.02)
    assert job.status == "failed"
    assert job.error == "Network error while downloading."
    assert job.file_available is False


def test_cancellation_cleans_temp(monkeypatch, tmp_path):
    started = threading.Event()
    release = threading.Event()

    def slow(url, opts):
        started.set()
        release.wait(2)
        raise DownloadCancelled()

    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "available")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: str(tmp_path / "ffmpeg"))
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)
    mgr = DownloadManager(ytdlp=slow)
    job = mgr.create(content_id="abc", title="X", stream_url="https://cdn.example/a.m3u8")
    assert started.wait(1)
    mgr.cancel(job.job_id)
    release.set()
    for _ in range(50):
        if job.status == "cancelled":
            break
        time.sleep(0.02)
    assert job.status == "cancelled"
    assert job.work_dir is None or not Path(job.work_dir).exists()


def test_missing_ffmpeg(monkeypatch):
    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "unavailable")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: None)
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)
    mgr = DownloadManager(ytdlp=_ok_ytdlp)
    with pytest.raises(DownloadRejected) as exc:
        mgr.create(content_id="abc", title="X", stream_url="https://cdn.example/a.m3u8")
    assert exc.value.status_code == 503


def test_one_at_a_time(monkeypatch, tmp_path):
    hold = threading.Event()

    def block(url, opts):
        hold.wait(2)

    monkeypatch.setattr("services.download.ffmpeg_status", lambda: "available")
    monkeypatch.setattr("services.download.locate_ffmpeg", lambda: str(tmp_path / "ffmpeg"))
    monkeypatch.setattr("services.download.ytdlp_available", lambda: True)
    mgr = DownloadManager(ytdlp=block)
    mgr.create(content_id="a", title="A", stream_url="https://cdn.example/a.m3u8")
    with pytest.raises(DownloadRejected) as exc:
        mgr.create(content_id="b", title="B", stream_url="https://cdn.example/b.m3u8")
    assert exc.value.status_code == 409
    hold.set()
