"""FastAPI contract tests. MXPlayerAPI is mocked; no live MX or Chrome."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

HIDDEN = ("stream_url", "stream_options")

PARSED_MOVIE = {
    "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
    "title": "Sample Movie",
    "type": "movie",
    "description": "A film.",
    "image": "https://qqcdnpictest.mxplay.com/poster.jpg",
    "stream_url": "https://llvod.mxplay.com/secret.m3u8",
    "stream_options": {"hls_main": "https://llvod.mxplay.com/secret.m3u8"},
    "drm": False,
    "duration": 5400,
    "sequence": "",
    "year": "2021",
    "rating": "U/A 13+",
    "languages": ["Hindi"],
    "languages_details": [{"id": "hi", "name": "Hindi"}],
    "genres": ["Drama"],
    "shareUrl": "https://www.mxplayer.in/movie/watch-sample",
    "publisher": "Studio X",
    "contributors": [{"name": "Jane", "role": "actor"}],
    "firstVideo": {"id": "fv"},
    "container": {"id": "c"},
}

RAW_SHOW_DETAIL = {
    "id": "bbbbbbbbbbbbbbbbbbbbbbbb",
    "title": "Sample Show",
    "type": "tvshow",
    "description": "A series.",
    "stream": {
        "hls": {"main": "https://llvod.mxplay.com/show.m3u8"},
        "drmProtect": False,
    },
    "tabs": [
        {
            "type": "tvshowepisodes",
            "containers": [
                {"id": "season-1", "title": "Season 1", "episodesCount": 8},
            ],
        }
    ],
}

PARSED_EPISODE = {
    "id": "cccccccccccccccccccccccc",
    "title": "Episode 1",
    "type": "episode",
    "description": "Pilot.",
    "image": "https://qqcdnpictest.mxplay.com/ep.jpg",
    "stream_url": "https://llvod.mxplay.com/high.m3u8",
    "stream_options": {
        "hls_high": "https://llvod.mxplay.com/high.m3u8",
        "hls_main": "https://llvod.mxplay.com/main.m3u8",
    },
    "drm": False,
    "duration": 2400,
    "sequence": 1,
    "year": "",
    "rating": "",
    "languages": ["Hindi"],
    "languages_details": [{"id": "hi", "name": "Hindi"}],
    "genres": [],
    "shareUrl": "",
    "publisher": "",
    "contributors": [],
}


def _assert_no_stream_fields(obj) -> None:
    if isinstance(obj, dict):
        for key in HIDDEN:
            assert key not in obj
        for value in obj.values():
            _assert_no_stream_fields(value)
    elif isinstance(obj, list):
        for item in obj:
            _assert_no_stream_fields(item)


class TestHealth:
    def test_health_ok(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["proxy_port"] == 8513
        assert body["ffmpeg"] in ("available", "unavailable")


class TestSearch:
    def test_search_requires_query(self, client: TestClient):
        assert client.get("/api/search").status_code == 422

    def test_search_returns_items_without_stream_fields(
        self, client: TestClient, mock_api: MagicMock
    ):
        mock_api.search.return_value = ([dict(PARSED_MOVIE)], None)
        res = client.get("/api/search", params={"q": "sample"})
        assert res.status_code == 200
        body = res.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == PARSED_MOVIE["id"]
        assert body["items"][0]["title"] == "Sample Movie"
        _assert_no_stream_fields(body)
        mock_api.search.assert_called_once()

    def test_search_upstream_error(self, client: TestClient, mock_api: MagicMock):
        mock_api.search.return_value = ([], "Network error — could not reach MX Player API.")
        res = client.get("/api/search", params={"q": "x"})
        assert res.status_code == 502
        assert "Network error" in res.json()["detail"]


class TestBannersAndShelves:
    def test_banners_ok(self, client: TestClient, mock_api: MagicMock):
        mock_api.fetch_home_banners.return_value = (
            [
                {
                    "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
                    "title": "Featured",
                    "type": "tvshow",
                    "image": "https://img.example/p.jpg",
                    "backdrop": "https://img.example/b.jpg",
                    "description": "Hi",
                    "genres": ["Drama"],
                    "languages": ["Hindi"],
                    "rating": "U/A 16+",
                }
            ],
            None,
        )
        res = client.get("/api/banners", params={"limit": 12})
        assert res.status_code == 200
        body = res.json()
        assert body["items"][0]["title"] == "Featured"
        assert body["error"] is None
        _assert_no_stream_fields(body)

    def test_shelves_ok(self, client: TestClient, mock_api: MagicMock):
        mock_api.fetch_home_shelves.return_value = (
            [
                {
                    "id": "movies",
                    "title": "Popular movies",
                    "items": [
                        {
                            "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
                            "title": "Film",
                            "type": "movie",
                            "image": "https://img.example/p.jpg",
                        }
                    ],
                }
            ],
            None,
        )
        res = client.get("/api/home/shelves")
        assert res.status_code == 200
        body = res.json()
        assert body["shelves"][0]["id"] == "movies"
        _assert_no_stream_fields(body)


class TestResolve:
    def test_resolve_404(self, client: TestClient, mock_api: MagicMock):
        mock_api.resolve_url.return_value = None
        res = client.post("/api/resolve", json={"url": "https://www.mxplayer.in/movie/x"})
        assert res.status_code == 404

    def test_resolve_tvshow_strips_streams(self, client: TestClient, mock_api: MagicMock):
        mock_api.resolve_url.return_value = {
            "type": "tvshow",
            "parsed": dict(PARSED_MOVIE, type="tvshow", title="Sample Show"),
            "detail": RAW_SHOW_DETAIL,
        }
        res = client.post(
            "/api/resolve",
            json={"url": "https://www.mxplayer.in/show/watch-sample-online-bbbbbbbbbbbbbbbbbbbbbbbb"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["type"] == "tvshow"
        assert body["item"]["title"] == "Sample Show"
        assert body["seasons"][0]["id"] == "season-1"
        _assert_no_stream_fields(body)


class TestContent:
    def test_content_404(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_collection.return_value = (None, None)
        res = client.get("/api/content/missing", params={"type": "movie"})
        assert res.status_code == 404

    def test_content_502(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_collection.return_value = (None, "Network error — could not reach MX Player API.")
        res = client.get("/api/content/missing", params={"type": "movie"})
        assert res.status_code == 502

    def test_content_ok_strips_streams(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_collection.return_value = (RAW_SHOW_DETAIL, None)
        res = client.get(
            "/api/content/bbbbbbbbbbbbbbbbbbbbbbbb",
            params={"type": "tvshow"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["item"]["id"] == "bbbbbbbbbbbbbbbbbbbbbbbb"
        assert body["seasons"][0]["episodesCount"] == 8
        _assert_no_stream_fields(body)

    def test_content_ref_title_fallback(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_collection.return_value = (None, None)
        mock_api.find_parsed_item_by_id.return_value = dict(PARSED_MOVIE)
        res = client.get(
            "/api/content/aaaaaaaaaaaaaaaaaaaaaaaa",
            params={"type": "movie", "ref_title": "Sample Movie"},
        )
        assert res.status_code == 200
        _assert_no_stream_fields(res.json())

    def test_seasons_ok(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_collection.return_value = (RAW_SHOW_DETAIL, None)
        res = client.get("/api/content/bbbbbbbbbbbbbbbbbbbbbbbb/seasons")
        assert res.status_code == 200
        assert res.json()["seasons"][0]["id"] == "season-1"

    def test_seasons_404(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_collection.return_value = (None, None)
        res = client.get("/api/content/missing/seasons")
        assert res.status_code == 404


class TestEpisodes:
    def test_episodes_ok_strips_streams(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_episodes.return_value = ([dict(PARSED_EPISODE)], None)
        res = client.get("/api/seasons/season-1/episodes")
        assert res.status_code == 200
        body = res.json()
        assert body["episodes"][0]["id"] == PARSED_EPISODE["id"]
        _assert_no_stream_fields(body)

    def test_episodes_502_when_empty_and_error(self, client: TestClient, mock_api: MagicMock):
        mock_api.get_episodes.return_value = ([], "Failed to load episodes: timeout")
        res = client.get("/api/seasons/season-1/episodes")
        assert res.status_code == 502


class TestExtractBrowser:
    def test_extract_success_without_chrome(self, client: TestClient, monkeypatch):
        def fake_extract(url: str, userid: str) -> dict:
            assert "mxplayer.in" in url
            assert userid == "test-user-id"
            return {
                "type": "video",
                "parsed": dict(PARSED_MOVIE, id="", title="Extracted"),
                "direct_stream_url": "https://llvod.mxplay.com/page.m3u8",
                "seasons": [],
                "episodes": [],
            }

        monkeypatch.setattr("routers.extract.extract_and_resolve", fake_extract)
        res = client.post(
            "/api/extract-browser",
            json={"url": "https://www.mxplayer.in/movie/watch-x"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["direct_stream_url"] == "https://llvod.mxplay.com/page.m3u8"
        assert body["item"]["title"] == "Extracted"
        assert "stream_url" not in (body["item"] or {})

    def test_extract_error_is_502(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(
            "routers.extract.extract_and_resolve",
            lambda url, userid: {"error": "Could not start Chrome: missing driver"},
        )
        res = client.post(
            "/api/extract-browser",
            json={"url": "https://www.mxplayer.in/movie/watch-x"},
        )
        assert res.status_code == 502
        assert "Chrome" in res.json()["detail"]


class TestStream:
    def test_stream_movie_ok(
        self,
        client: TestClient,
        mock_api: MagicMock,
    ):
        mock_api.get_collection.return_value = (
            {
                "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
                "title": "Sample Movie",
                "type": "movie",
                "stream": {
                    "hls": {
                        "main": "https://llvod.mxplay.com/main.m3u8",
                        "high": "https://llvod.mxplay.com/high.m3u8",
                    },
                    "drmProtect": False,
                },
                "languagesDetails": [{"id": "hi", "name": "Hindi"}],
            },
            None,
        )
        res = client.get(
            "/api/stream/aaaaaaaaaaaaaaaaaaaaaaaa",
            params={"type": "movie"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["stream_url"] == "https://llvod.mxplay.com/main.m3u8"
        keys = {o["key"] for o in body["options"]}
        assert "hls_main" in keys
        assert "hls_high" in keys
        assert body["drm"] is False
        assert body["languages"][0]["id"] == "hi"

    def test_stream_episode_prefers_main(
        self,
        client: TestClient,
        mock_api: MagicMock,
    ):
        mock_api.get_episodes.return_value = ([dict(PARSED_EPISODE)], None)
        res = client.get(
            "/api/stream/cccccccccccccccccccccccc",
            params={"type": "episode", "season_id": "season-1"},
        )
        assert res.status_code == 200
        assert res.json()["stream_url"] == "https://llvod.mxplay.com/main.m3u8"

    def test_stream_episode_missing_season_id(
        self,
        client: TestClient,
        mock_api: MagicMock,
    ):
        res = client.get(
            "/api/stream/cccccccccccccccccccccccc",
            params={"type": "episode"},
        )
        assert res.status_code == 400
        assert "season_id" in res.json()["detail"]

    def test_stream_not_found(
        self,
        client: TestClient,
        mock_api: MagicMock,
    ):
        res = client.get(
            "/api/stream/missing",
            params={"type": "movie"},
        )
        assert res.status_code == 404
