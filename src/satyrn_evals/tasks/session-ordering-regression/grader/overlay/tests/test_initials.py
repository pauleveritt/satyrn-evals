from textkit import initials


def test_initials_basic():
    assert initials("ada lovelace") == "AL"


def test_initials_ignores_extra_spaces():
    assert initials("  ada   lovelace  ") == "AL"
