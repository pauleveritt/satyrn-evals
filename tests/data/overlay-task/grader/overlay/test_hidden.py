from solution import slugify


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_collapses_spaces():
    assert slugify("  a   b  ") == "a-b"
