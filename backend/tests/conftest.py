"""Shared fixtures. External boundaries only: MX HTTP, Chrome, proxy bind."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import dependencies
from config import settings
from dependencies import get_api
from services.download import reset_manager
from services.ffmpeg import reset_ffmpeg_status_cache


@pytest.fixture(autouse=True)
def _isolate_process_globals(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[None]:
    """No real proxy thread, no leftover API singleton."""
    monkeypatch.setattr("main.start_proxy", lambda port=None, host=None: port or 8513)
    monkeypatch.setattr("services.proxy.start_proxy", lambda port=None, host=None: port or 8513)
    monkeypatch.setattr(
        settings, "download_dir", str(tmp_path_factory.mktemp("downloads"))
    )
    monkeypatch.setattr(settings, "ffmpeg_path", "")
    monkeypatch.setattr(settings, "android_native_lib_dir", "")
    dependencies._api_instance = None
    reset_manager()
    reset_ffmpeg_status_cache()
    yield
    dependencies._api_instance = None
    reset_manager()
    reset_ffmpeg_status_cache()


@pytest.fixture
def mock_api() -> MagicMock:
    api = MagicMock()
    api.userid = "test-user-id"
    api.search.return_value = ([], None)
    api.fetch_home_banners.return_value = ([], None)
    api.fetch_home_shelves.return_value = ([], "No catalog rows returned.")
    api.resolve_url.return_value = None
    api.get_collection.return_value = (None, None)
    api.get_episode_collection_detail.return_value = None
    api.find_parsed_item_by_id.return_value = None
    api.get_episodes.return_value = ([], None)
    api.episode_collection_stream_options.return_value = {}
    return api


@pytest.fixture
def client(mock_api: MagicMock) -> Iterator[TestClient]:
    from main import app

    app.dependency_overrides[get_api] = lambda: mock_api
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
