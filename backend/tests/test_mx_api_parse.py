"""Unit tests for MX parsing helpers. No live MX Player requests."""

from __future__ import annotations

from services.mx_api import (
    CDN_IMAGE,
    CDN_VIDEO,
    _ids_from_url,
    extract_seasons,
    format_duration,
    hero_banner_url,
    name_from_url,
    parse_item,
    parse_stream_options,
    prefer_main_if_default_is_high,
    show_id_from_episode,
    stream_url,
)

HLS_MAIN = f"{CDN_VIDEO}/hls/main.m3u8"
HLS_HIGH = f"{CDN_VIDEO}/hls/high.m3u8"
HLS_BASE = f"{CDN_VIDEO}/hls/base.m3u8"
DASH_HIGH = f"{CDN_VIDEO}/dash/high.mpd"


def _stream_block(**extra) -> dict:
    return {
        "drmProtect": False,
        "hls": {"main": "hls/main.m3u8", "high": "hls/high.m3u8", "base": "hls/base.m3u8"},
        "dash": {"high": "dash/high.mpd"},
        **extra,
    }


def _movie_item() -> dict:
    return {
        "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
        "title": "Sample Movie",
        "type": "movie",
        "description": "A film.",
        "releaseDate": "2021-06-15T00:00:00Z",
        "duration": 5400,
        "rating": "U/A 13+",
        "languages": ["Hindi", "English"],
        "languagesDetails": [
            {"id": "hi", "name": "Hindi"},
            {"id": "en", "name": "English"},
        ],
        "genres": ["Drama"],
        "shareUrl": "https://www.mxplayer.in/movie/watch-sample-online",
        "publisher": {"name": "Studio X"},
        "contributors": [
            {"name": "Jane Doe", "type": "actor"},
            {"type": "director"},
        ],
        "imageInfo": [{"url": "poster/movie.jpg"}],
        "stream": _stream_block(),
        "firstVideo": {"id": "should-not-leak-via-public"},
        "container": {"id": "parent"},
    }


def _show_detail() -> dict:
    return {
        "id": "bbbbbbbbbbbbbbbbbbbbbbbb",
        "title": "Sample Show",
        "type": "tvshow",
        "tabs": [
            {"type": "about"},
            {
                "type": "tvshowepisodes",
                "containers": [
                    {"id": "season-1", "title": "Season 1", "episodesCount": 8},
                    {"id": "season-2", "title": "Season 2", "episodesCount": 10},
                    {"title": "ignored-no-id"},
                ],
            },
        ],
        "titleContentImageInfo": [
            {"type": "other", "url": "ignore.jpg"},
            {"type": "banner_and_static_bg_desktop", "url": "hero/show.jpg"},
        ],
    }


def _episode_item() -> dict:
    return {
        "id": "cccccccccccccccccccccccc",
        "name": "Episode 3",
        "type": "episode",
        "synopsis": "Cold open.",
        "sequence": 3,
        "duration": 2400,
        "image": {"16x9": "https://cdn.example/ep.jpg"},
        "stream": {
            "drmProtect": True,
            "hls": {"high": HLS_HIGH, "main": HLS_MAIN},
        },
        "container": {
            "id": "season-1",
            "container": {"id": "bbbbbbbbbbbbbbbbbbbbbbbb", "type": "tvshow"},
        },
        "languages": ["Hindi"],
    }


class TestParseItem:
    def test_movie_normalises_fields_and_stream(self):
        parsed = parse_item(_movie_item())
        assert parsed is not None
        assert parsed["id"] == "aaaaaaaaaaaaaaaaaaaaaaaa"
        assert parsed["title"] == "Sample Movie"
        assert parsed["type"] == "movie"
        assert parsed["description"] == "A film."
        assert parsed["year"] == "2021"
        assert parsed["duration"] == 5400
        assert parsed["rating"] == "U/A 13+"
        assert parsed["image"] == f"{CDN_IMAGE}/poster/movie.jpg"
        assert parsed["publisher"] == "Studio X"
        assert parsed["shareUrl"].endswith("watch-sample-online")
        assert parsed["drm"] is False
        assert parsed["stream_url"] == HLS_MAIN
        assert parsed["stream_options"]["hls_high"] == HLS_HIGH
        assert parsed["stream_options"]["hls_main"] == HLS_MAIN
        assert parsed["stream_options"]["dash_high"] == DASH_HIGH
        assert parsed["languages_details"] == [
            {"id": "hi", "name": "Hindi"},
            {"id": "en", "name": "English"},
        ]
        assert parsed["contributors"] == [{"name": "Jane Doe", "role": "actor"}]
        assert parsed["firstVideo"]["id"] == "should-not-leak-via-public"
        assert parsed["container"]["id"] == "parent"

    def test_episode_uses_name_synopsis_and_absolute_image(self):
        parsed = parse_item(_episode_item())
        assert parsed is not None
        assert parsed["title"] == "Episode 3"
        assert parsed["description"] == "Cold open."
        assert parsed["type"] == "episode"
        assert parsed["sequence"] == 3
        assert parsed["image"] == "https://cdn.example/ep.jpg"
        assert parsed["drm"] is True
        assert parsed["languages_details"] == [{"id": "hi", "name": "Hindi"}]

    def test_rejects_junk(self):
        assert parse_item(None) is None  # type: ignore[arg-type]
        assert parse_item("x") is None  # type: ignore[arg-type]
        assert parse_item({}) is None
        assert parse_item({"id": "", "title": ""}) is None

    def test_empty_stream_is_safe(self):
        parsed = parse_item({"id": "x", "title": "T", "stream": None})
        assert parsed is not None
        assert parsed["stream_url"] == ""
        assert parsed["stream_options"] == {}
        assert parsed["drm"] is False


class TestStreamUrlAndOptions:
    def test_prefers_hls_main_over_high(self):
        assert stream_url(_stream_block()) == HLS_MAIN

    def test_falls_back_to_dash_when_hls_missing(self):
        assert stream_url({"dash": {"high": "dash/high.mpd"}}) == DASH_HIGH

    def test_absolute_urls_are_kept(self):
        url = "https://cdn.example/abs.m3u8"
        assert stream_url({"hls": {"main": url}}) == url

    def test_non_dict_stream(self):
        assert stream_url(None) == ""
        assert stream_url("nope") == ""
        assert parse_stream_options(None) == {}

    def test_options_include_all_rungs(self):
        opts = parse_stream_options(_stream_block())
        assert set(opts) == {"hls_high", "hls_main", "hls_base", "dash_high"}
        assert opts["hls_base"] == HLS_BASE


class TestPreferMainIfDefaultIsHigh:
    def test_switches_high_to_main(self):
        assert (
            prefer_main_if_default_is_high(
                HLS_HIGH,
                {"hls_high": HLS_HIGH, "hls_main": HLS_MAIN},
            )
            == HLS_MAIN
        )

    def test_leaves_main_alone(self):
        assert (
            prefer_main_if_default_is_high(
                HLS_MAIN,
                {"hls_high": HLS_HIGH, "hls_main": HLS_MAIN},
            )
            == HLS_MAIN
        )

    def test_relative_high_matches_absolute_main(self):
        assert (
            prefer_main_if_default_is_high(
                "hls/high.m3u8",
                {"hls_high": "hls/high.m3u8", "hls_main": "hls/main.m3u8"},
            )
            == HLS_MAIN
        )

    def test_missing_main_keeps_input(self):
        assert prefer_main_if_default_is_high(HLS_HIGH, {"hls_high": HLS_HIGH}) == HLS_HIGH

    def test_non_dict_options(self):
        assert prefer_main_if_default_is_high("  x  ", None) == "x"  # type: ignore[arg-type]


class TestLanguagesSeasonsEpisodes:
    def test_language_details_fallback_from_string_list(self):
        parsed = parse_item({"id": "1", "title": "T", "languages": ["Hindi", "EN"]})
        assert parsed is not None
        assert parsed["languages_details"] == [
            {"id": "hi", "name": "Hindi"},
            {"id": "en", "name": "EN"},
        ]

    def test_extract_seasons_from_tabs(self):
        seasons = extract_seasons(_show_detail())
        assert seasons == [
            {"id": "season-1", "title": "Season 1", "episodesCount": 8},
            {"id": "season-2", "title": "Season 2", "episodesCount": 10},
        ]

    def test_extract_seasons_empty(self):
        assert extract_seasons({}) == []
        assert extract_seasons({"tabs": [{"type": "about"}]}) == []

    def test_show_id_from_episode_walks_containers(self):
        parsed = parse_item(_episode_item())
        assert parsed is not None
        assert show_id_from_episode(parsed) == "bbbbbbbbbbbbbbbbbbbbbbbb"

    def test_show_id_missing_container(self):
        assert show_id_from_episode({}) == ""


class TestUrlHelpers:
    def test_ids_from_typical_mx_url(self):
        url = (
            "https://www.mxplayer.in/show/"
            "watch-sample-show-online-aaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert _ids_from_url(url) == ["aaaaaaaaaaaaaaaaaaaaaaaa"]

    def test_ids_ignore_short_hex(self):
        assert _ids_from_url("https://www.mxplayer.in/movie/watch-x-deadbeef") == []

    def test_name_from_watch_slug(self):
        url = "https://www.mxplayer.in/movie/watch-sample-movie-online-free"
        assert name_from_url(url) == "sample movie"

    def test_name_from_url_without_watch_slug(self):
        assert name_from_url("https://www.mxplayer.in/movies") == ""


class TestHeroAndDuration:
    def test_hero_banner_uses_desktop_asset(self):
        assert hero_banner_url(_show_detail()) == f"{CDN_IMAGE}/hero/show.jpg"

    def test_hero_banner_missing(self):
        assert hero_banner_url({}) == ""

    def test_format_duration(self):
        assert format_duration(5400) == "1h 30m"
        assert format_duration(120) == "2m"
        assert format_duration(0) == ""
        assert format_duration(None) == ""
        assert format_duration("bad") == ""
