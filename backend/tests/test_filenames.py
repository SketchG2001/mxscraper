from services.filenames import sanitize_filename


def test_strips_illegal_characters():
    assert sanitize_filename('A/B\\C:D*E?F"G<H>I|J') == "ABCDEFGHIJ.mp4"


def test_collapses_whitespace_and_empty():
    assert sanitize_filename("   hello    world   ") == "hello world.mp4"
    assert sanitize_filename("   ") == "mxplayer_video.mp4"
    assert sanitize_filename("") == "mxplayer_video.mp4"


def test_long_title_is_truncated():
    name = sanitize_filename("x" * 200)
    assert name.endswith(".mp4")
    assert len(name) <= 84
