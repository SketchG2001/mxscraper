"""In-process download manager: one active job, yt-dlp Python API, FFmpeg remux."""

from __future__ import annotations

import logging
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from config import settings
from services.ffmpeg import ffmpeg_status, locate_ffmpeg
from services.filenames import sanitize_filename

_log = logging.getLogger("mx.download")

STATUSES = ("queued", "downloading", "completed", "failed", "cancelled")

YtdlpRunner = Callable[[str, dict[str, Any]], None]


def ytdlp_available() -> bool:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return False
    return True


class DownloadCancelled(Exception):
    """Cooperative abort from a progress hook."""


class DownloadRejected(Exception):
    """Pre-flight rejection (DRM, busy, missing tools, space)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class DownloadJob:
    job_id: str
    content_id: str
    title: str
    status: str = "queued"
    progress: float = 0.0
    bytes_downloaded: int | None = None
    total_bytes: int | None = None
    speed: float | None = None
    eta: int | None = None
    filename: str | None = None
    file_available: bool = False
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    cancel_requested: bool = False
    output_path: str | None = field(default=None, repr=False)
    work_dir: str | None = field(default=None, repr=False)


def downloads_root() -> Path:
    raw = (settings.download_dir or "").strip()
    if raw:
        root = Path(raw)
    else:
        root = Path.cwd() / ".downloads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _enough_disk(root: Path) -> bool:
    try:
        free = shutil.disk_usage(root).free
    except OSError:
        return True
    return free >= settings.min_download_free_bytes


def _public_error(exc: BaseException) -> str:
    if isinstance(exc, DownloadCancelled):
        return "Download cancelled."
    text = str(exc).strip() or exc.__class__.__name__
    lowered = text.lower()
    if "drm" in lowered:
        return "This content is protected and cannot be downloaded."
    if "no space" in lowered or "enospc" in lowered or "disk" in lowered:
        return "Not enough storage to finish this download."
    if "ffmpeg" in lowered:
        return "FFmpeg is not available."
    if "unsupported" in lowered or "format" in lowered:
        return "This format cannot be downloaded."
    if "network" in lowered or "timed out" in lowered or "connection" in lowered:
        return "Network error while downloading."
    return "Download failed."


def _format_selector(language: str | None) -> str:
    if language:
        return f"bv*+ba[language={language}]/bv*+ba/best"
    return "bv*+ba/best"


def invoke_ytdlp(url: str, opts: dict[str, Any]) -> None:
    """External boundary. Tests patch this — do not call YoutubeDL elsewhere."""
    from yt_dlp import YoutubeDL

    with YoutubeDL(opts) as ydl:
        ydl.download([url])


def _cleanup_tree(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        _log.warning("Could not remove %s", path)


class DownloadManager:
    def __init__(self, ytdlp: YtdlpRunner | None = None) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, DownloadJob] = {}
        self._ytdlp = ytdlp or invoke_ytdlp

    def get(self, job_id: str) -> DownloadJob | None:
        return self._jobs.get(job_id)

    def active_job(self) -> DownloadJob | None:
        for job in self._jobs.values():
            if job.status in ("queued", "downloading"):
                return job
        return None

    def create(
        self,
        *,
        content_id: str,
        title: str,
        stream_url: str,
        language: str | None = None,
    ) -> DownloadJob:
        if ffmpeg_status() != "available" or not locate_ffmpeg():
            raise DownloadRejected("FFmpeg is not available.", 503)
        if not ytdlp_available():
            raise DownloadRejected("yt-dlp is not available.", 503)

        root = downloads_root()
        if not _enough_disk(root):
            raise DownloadRejected("Not enough storage for a new download.", 507)

        with self._lock:
            if self.active_job() is not None:
                raise DownloadRejected("A download is already in progress.", 409)
            job = DownloadJob(
                job_id=str(uuid.uuid4()),
                content_id=content_id,
                title=title,
                filename=sanitize_filename(title),
            )
            self._jobs[job.job_id] = job

        thread = threading.Thread(
            target=self._run,
            args=(job.job_id, stream_url, language),
            name=f"mx-dl-{job.job_id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def cancel(self, job_id: str) -> DownloadJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.status in ("completed", "failed", "cancelled"):
            return job
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.error = "Download cancelled."
            job.completed_at = time.time()
            _cleanup_tree(Path(job.work_dir) if job.work_dir else None)
        return job

    def _run(self, job_id: str, stream_url: str, language: str | None) -> None:
        job = self._jobs[job_id]
        work = downloads_root() / job_id
        work.mkdir(parents=True, exist_ok=True)
        job.work_dir = str(work)
        tmp_tmpl = str(work / "media.%(ext)s")
        ffmpeg = locate_ffmpeg()
        if not ffmpeg:
            job.status = "failed"
            job.error = "FFmpeg is not available."
            job.completed_at = time.time()
            _cleanup_tree(work)
            return

        def hook(info: dict[str, Any]) -> None:
            if job.cancel_requested:
                raise DownloadCancelled()
            status = info.get("status")
            if status == "downloading":
                job.status = "downloading"
                total = info.get("total_bytes") or info.get("total_bytes_estimate")
                done = info.get("downloaded_bytes")
                if isinstance(done, (int, float)):
                    job.bytes_downloaded = int(done)
                if isinstance(total, (int, float)) and total:
                    job.total_bytes = int(total)
                    job.progress = min(100.0, float(done or 0) * 100.0 / float(total))
                elif isinstance(info.get("_percent_str"), str):
                    try:
                        job.progress = min(100.0, float(info["_percent_str"].strip("%")))
                    except ValueError:
                        pass
                spd = info.get("speed")
                eta = info.get("eta")
                if isinstance(spd, (int, float)):
                    job.speed = float(spd)
                if isinstance(eta, (int, float)):
                    job.eta = int(eta)
            elif status == "finished":
                job.progress = max(job.progress, 99.0)

        opts: dict[str, Any] = {
            "outtmpl": tmp_tmpl,
            "ffmpeg_location": str(Path(ffmpeg).parent),
            "nopart": True,
            "nocheckcertificate": True,
            "no_warnings": True,
            "quiet": True,
            "progress_hooks": [hook],
            "format": _format_selector(language),
            "merge_output_format": "mp4",
            "postprocessor_args": {"ffmpeg": ["-c", "copy"]},
        }

        job.status = "downloading"
        try:
            self._ytdlp(stream_url, opts)
            if job.cancel_requested:
                raise DownloadCancelled()
            produced = _find_media_file(work)
            if produced is None or produced.stat().st_size < 10_000:
                raise RuntimeError("Download produced no usable file.")
            final_name = sanitize_filename(job.title)
            dest = downloads_root() / final_name
            if dest.exists():
                dest = downloads_root() / f"{dest.stem}_{job.job_id[:8]}{dest.suffix}"
                final_name = dest.name
            shutil.move(str(produced), dest)
            job.filename = final_name
            job.output_path = str(dest)
            job.file_available = True
            job.progress = 100.0
            job.status = "completed"
            job.completed_at = time.time()
            _cleanup_tree(work)
        except DownloadCancelled:
            job.status = "cancelled"
            job.error = "Download cancelled."
            job.completed_at = time.time()
            job.file_available = False
            _cleanup_tree(work)
            if job.output_path:
                _cleanup_tree(Path(job.output_path))
                job.output_path = None
        except Exception as exc:
            _log.exception("Download %s failed", job_id)
            job.status = "failed"
            job.error = _public_error(exc)
            job.completed_at = time.time()
            job.file_available = False
            _cleanup_tree(work)


def _find_media_file(work: Path) -> Path | None:
    candidates = [
        p
        for p in work.iterdir()
        if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".m4a", ".ts"}
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_size)


_manager: DownloadManager | None = None


def get_manager() -> DownloadManager:
    global _manager
    if _manager is None:
        _manager = DownloadManager()
    return _manager


def reset_manager() -> None:
    global _manager
    _manager = None
