from config import settings
from services.ffmpeg import ffmpeg_status, locate_ffmpeg, verify_ffmpeg


def test_unavailable_when_no_binary(monkeypatch):
    monkeypatch.setattr(settings, "ffmpeg_path", "")
    monkeypatch.delenv("FFMPEG_PATH", raising=False)
    monkeypatch.delenv("ANDROID_FFMPEG_PATH", raising=False)
    assert locate_ffmpeg() is None
    assert ffmpeg_status() == "unavailable"


def test_locate_valid_file_without_running(tmp_path, monkeypatch):
    binary = tmp_path / "ffmpeg"
    binary.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(settings, "ffmpeg_path", str(binary))
    assert locate_ffmpeg() == str(binary.resolve())
    assert verify_ffmpeg(str(binary), run_version=False) is True


def test_ignores_missing_path(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ffmpeg_path", str(tmp_path / "missing"))
    assert locate_ffmpeg() is None
