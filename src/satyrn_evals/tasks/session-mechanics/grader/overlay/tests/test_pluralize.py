from textkit import pluralize


def test_pluralize_regular():
    assert pluralize("cat") == "cats"


def test_pluralize_s_ending():
    assert pluralize("bus") == "buses"
