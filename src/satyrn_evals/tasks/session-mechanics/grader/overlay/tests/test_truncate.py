from textkit import truncate


def test_truncate_short_unchanged():
    assert truncate("hi", 10) == "hi"


def test_truncate_cuts_with_marker():
    assert truncate("hello world", 8) == "hello w…"
