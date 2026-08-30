"""Thin Android bootstrap: start the existing FastAPI app on loopback.

No MX Player / scraper logic lives here. Environment must be set before
``main`` / ``config`` are imported so Settings picks up Android values.
"""

from __future__ import annotations

import logging
import os

_log = logging.getLogger("android_server")


_server = None


def start(
    port: int,
    download_dir: str = "",
    ffmpeg_path: str = "",
    native_lib_dir: str = "",
) -> None:
    """Block the calling thread with uvicorn (run from a Java background thread)."""
    global _server
    listen_port = int(port)
    os.environ["ANDROID_RUNTIME"] = "1"
    os.environ["PROXY_BIND_HOST"] = "127.0.0.1"
    os.environ["ANDROID_API_PORT"] = str(listen_port)
    if download_dir:
        os.environ["DOWNLOAD_DIR"] = str(download_dir)
    if ffmpeg_path:
        os.environ["FFMPEG_PATH"] = str(ffmpeg_path)
    if native_lib_dir:
        os.environ["ANDROID_NATIVE_LIB_DIR"] = str(native_lib_dir)

    logging.basicConfig(level=logging.INFO)

    if _server is not None and getattr(_server, "started", False):
        _log.info("uvicorn already running on 127.0.0.1:%s", listen_port)
        return

    import uvicorn
    from main import app

    _log.info("Starting uvicorn on 127.0.0.1:%s", listen_port)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=listen_port,
        log_level="info",
        access_log=False,
    )
    _server = uvicorn.Server(config)
    _server.run()
    _log.info("uvicorn stopped on 127.0.0.1:%s", listen_port)


def stop() -> None:
    """Ask uvicorn to exit. Process death also stops the server."""
    if _server is not None:
        _log.info("Stopping uvicorn")
        _server.should_exit = True
