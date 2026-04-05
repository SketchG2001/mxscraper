"""CORS proxy for HLS streams.

Runs a lightweight HTTP server that fetches HLS manifests and segments
from the CDN, adds CORS headers, and rewrites m3u8 URLs so that all
subsequent requests also route through the proxy.

URL scheme (path-based):
    http://{HOST}:{PORT}/https://cdn.example.com/path/manifest.m3u8
"""

from __future__ import annotations

import re
import socket
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests as _req

from config import settings

PROXY_PORT = settings.proxy_port

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class _Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header(
            "Access-Control-Expose-Headers",
            "Content-Length, Content-Range, Content-Type",
        )

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_HEAD(self):
        self._proxy("HEAD")

    def do_GET(self):
        self._proxy("GET")

    def _proxy(self, method: str):
        target = self.path.lstrip("/")
        if not target.startswith("http"):
            self.send_error(400, "Path must be a full http(s):// URL")
            return

        try:
            headers = {"User-Agent": _UA}
            rng = self.headers.get("Range")
            if rng:
                headers["Range"] = rng

            resp = _req.request(
                method, target,
                headers=headers,
                timeout=30,
                stream=False,
                allow_redirects=True,
            )

            body = resp.content
            ct = resp.headers.get("Content-Type", "application/octet-stream")

            if "mpegurl" in ct.lower() or target.endswith(".m3u8"):
                host = self.headers.get("Host", f"127.0.0.1:{PROXY_PORT}")
                body = _rewrite_m3u8(
                    body.decode("utf-8", errors="replace"), target, host
                ).encode("utf-8")
                ct = "application/vnd.apple.mpegurl"

            self.send_response(resp.status_code)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(body)))
            cr = resp.headers.get("Content-Range")
            if cr:
                self.send_header("Content-Range", cr)
            self._cors()
            self.end_headers()
            if method == "GET":
                self.wfile.write(body)

        except Exception as exc:
            msg = f"Proxy error: {exc}".encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self._cors()
            self.end_headers()
            if method == "GET":
                self.wfile.write(msg)


def _rewrite_m3u8(content: str, manifest_url: str, host: str = "") -> str:
    """Rewrite every URL in an m3u8 manifest to route through the proxy."""
    proxy_base = f"http://{host or f'127.0.0.1:{PROXY_PORT}'}/"
    lines = content.splitlines()
    out: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append(line)
        elif stripped.startswith("#"):
            if "URI=" in stripped:
                line = re.sub(
                    r'URI="([^"]+)"',
                    lambda m: 'URI="{}{}"'.format(
                        proxy_base,
                        m.group(1)
                        if m.group(1).startswith("http")
                        else urllib.parse.urljoin(manifest_url, m.group(1)),
                    ),
                    line,
                )
            out.append(line)
        else:
            abs_url = (
                stripped
                if stripped.startswith("http")
                else urllib.parse.urljoin(manifest_url, stripped)
            )
            out.append(proxy_base + abs_url)

    return "\n".join(out)


_started = False


def start_proxy(port: int | None = None) -> int:
    """Start the CORS proxy in a daemon thread.

    Safe to call multiple times; only the first call starts the server.
    """
    global _started
    port = port or PROXY_PORT
    if _started:
        return port

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", port))
        sock.close()
    except OSError:
        _started = True
        return port

    server = HTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _started = True
    return port
