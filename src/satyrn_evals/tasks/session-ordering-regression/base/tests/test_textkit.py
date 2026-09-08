from textkit import normalize, wrap


def test_normalize():
    assert normalize("  a  b ") == "a b"


def test_wrap():
    assert wrap("aa bb cc", 5) == "aa bb\ncc"
