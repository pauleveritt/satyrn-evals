from solution import normalize


def test_normalize():
    assert normalize("  a  b ") == "a b"
