from solution import format_number


def test_small():
    assert format_number(1234) == "1,234"


def test_large():
    assert format_number(1234567) == "1,234,567"


def test_negative():
    assert format_number(-1234) == "-1,234"


def test_zero():
    assert format_number(0) == "0"
