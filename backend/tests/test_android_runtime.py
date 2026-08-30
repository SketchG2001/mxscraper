"""Android runtime flags must not change the default web configuration."""

from __future__ import annotations

from config import cors_allow_credentials, cors_allow_origins, settings


def test_web_cors_defaults():
    assert settings.android_runtime is False
    assert cors_allow_origins() == ["*"]
    assert cors_allow_credentials() is True


def test_android_cors_is_localhost_only(monkeypatch):
    monkeypatch.setattr(settings, "android_runtime", True)
    assert cors_allow_origins() == ["https://localhost", "http://localhost"]
    assert cors_allow_credentials() is False


def test_android_api_port_matches_frontend_json():
    import json
    from pathlib import Path

    spec_path = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "lib"
        / "androidLocalApi.json"
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert settings.android_api_port == spec["port"]
    assert spec["host"] == "127.0.0.1"
