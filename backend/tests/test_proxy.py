"""HLS proxy helpers — no live CDN."""

from socketserver import ThreadingMixIn

from services.proxy import ThreadingHTTPServer, _rewrite_m3u8


def test_proxy_server_is_threaded():
    assert issubclass(ThreadingHTTPServer, ThreadingMixIn)
    assert ThreadingHTTPServer.daemon_threads is True
    assert ThreadingHTTPServer.allow_reuse_address is True


def test_rewrite_m3u8_prefixes_segment_urls():
    src = (
        "#EXTM3U\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=800000\n"
        "media.m3u8\n"
        "https://cdn.example/seg.ts\n"
    )
    out = _rewrite_m3u8(
        src,
        "https://cdn.example/master.m3u8",
        "http://127.0.0.1:8513/",
    )
    assert "http://127.0.0.1:8513/https://cdn.example/media.m3u8" in out
    assert "http://127.0.0.1:8513/https://cdn.example/seg.ts" in out
    assert "https://localhost/hls/" not in out
