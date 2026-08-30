"""Locate a usable FFmpeg binary. Never the repo Linux ``bin/ffmpeg`` ELFs."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from config import settings

_log = logging.getLogger("mx.ffmpeg")

# Linux AArch64 desktop binaries in this repo — not Android Bionic. Never use.
_REPO_BIN_BLOCKLIST = frozenset(
    {
        Path("bin/ffmpeg").as_posix(),
        Path("bin/ffprobe").as_posix(),
        Path("bin\\ffmpeg").as_posix(),
        Path("bin\\ffprobe").as_posix(),
    }
)


class FfmpegUnavailable(Exception):
    """No verified FFmpeg executable for this runtime."""


def _is_blocked_repo_binary(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    parts = resolved.parts
    if len(parts) >= 2 and parts[-2] == "bin" and parts[-1] in {"ffmpeg", "ffprobe", "ffmpeg.exe"}:
        # Only block the project-root bin/ pair, not a user FFMPEG_PATH named ffmpeg.
        if "mxscraper" in resolved.as_posix() and resolved.parent.name == "bin":
            parent_parent = resolved.parent.parent
            if (parent_parent / "backend").is_dir() and (parent_parent / "frontend").is_dir():
                return True
    posix = path.as_posix()
    return posix in _REPO_BIN_BLOCKLIST or posix.endswith("/bin/ffmpeg") and "mxscraper" in posix


def _candidate_paths() -> list[Path]:
    raw: list[str] = []
    if settings.ffmpeg_path:
        raw.append(settings.ffmpeg_path)
    env = os.environ.get("FFMPEG_PATH") or os.environ.get("ANDROID_FFMPEG_PATH")
    if env:
        raw.append(env)
    native = settings.android_native_lib_dir or os.environ.get("ANDROID_NATIVE_LIB_DIR")
    if native:
        raw.append(str(Path(native) / "libffmpeg.so"))
    out: list[Path] = []
    seen: set[str] = set()
    for item in raw:
        p = Path(item)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def locate_ffmpeg() -> str | None:
    """Return an absolute path to an existing FFmpeg file, or None.

    Does not run the binary. Does not search PATH / which / where.
    """
    for path in _candidate_paths():
        if _is_blocked_repo_binary(path):
            _log.warning("Ignoring repo Linux FFmpeg at %s", path)
            continue
        if path.is_file():
            return str(path.resolve())
    return None


def verify_ffmpeg(path: str | None = None, *, run_version: bool = True) -> bool:
    """True if the binary exists and, when requested, ``ffmpeg -version`` succeeds."""
    resolved = path or locate_ffmpeg()
    if not resolved:
        return False
    p = Path(resolved)
    if not p.is_file() or _is_blocked_repo_binary(p):
        return False
    if not run_version:
        return True
    try:
        proc = subprocess.run(
            [resolved, "-version"],
            capture_output=True,
            timeout=8,
            check=False,
            shell=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


_status_cache: str | None = None


def reset_ffmpeg_status_cache() -> None:
    """Clear cached ``/health`` FFmpeg status (tests / locator refresh)."""
    global _status_cache
    _status_cache = None


def ffmpeg_status(*, refresh: bool = False) -> str:
    """``available`` or ``unavailable`` — no command output leaked.

    Result is cached so Android ``/health`` polling does not spawn
    ``ffmpeg -version`` on every request. Pass ``refresh=True`` to re-check.
    """
    global _status_cache
    if _status_cache is not None and not refresh:
        return _status_cache
    _status_cache = "available" if verify_ffmpeg() else "unavailable"
    return _status_cache
