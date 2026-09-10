from textkit import summarize


def test_summarize_cuts_with_marker():
    assert summarize("Hello world. Second sentence.", 8) == "Hello w…"


def test_summarize_collapses_internal_whitespace():
    assert summarize("Hello   world. Next.", 20) == "Hello world"
