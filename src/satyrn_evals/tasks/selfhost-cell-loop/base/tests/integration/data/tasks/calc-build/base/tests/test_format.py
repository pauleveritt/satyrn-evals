from calc.format import render


def test_render():
    assert render(1234) == "1,234"
