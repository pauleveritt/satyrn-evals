"""The power calculator, checked in both directions.

A power function that always returned a large number would justify any design,
and a review reading only the design would never catch it -- so the pair below
is the point: a **null** alternative must come back at or under alpha, and a
**large** one must come back high. One without the other proves nothing.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from power import (  # noqa: E402  # type: ignore[missing-import]  # scripts/ added via sys.path above
    fisher_one_sided,
    power,
)


def test_no_effect_gives_power_at_or_below_alpha() -> None:
    """The refusal direction: with both arms identical, rejecting is an error,
    and a conservative exact test sits at or under its nominal rate."""
    assert power(36, 0.50, 0.50, 0.05) <= 0.05


def test_a_large_effect_is_detected_almost_always() -> None:
    """The sibling success: the same function must not be uniformly small."""
    assert power(36, 0.10, 0.95, 0.05) > 0.95


def test_power_is_monotone_in_sample_size() -> None:
    values = [power(n, 0.50, 0.80, 0.05) for n in (12, 24, 36)]
    assert values == sorted(values)


def test_the_designs_two_stated_figures() -> None:
    """The exact figures the R1 comparison design records, so a change to this
    file cannot silently move a number the spec cites."""
    assert round(power(36, 0.50, 0.80, 0.05), 3) == 0.809
    assert round(power(36, 0.50, 0.75, 0.05), 3) == 0.651


def test_a_full_margin_table_is_certain() -> None:
    """Hand-checkable: every attempt succeeding in both arms leaves one table."""
    assert fisher_one_sided(2, 2, 2) == pytest.approx(1.0)


def test_rejects_an_empty_arm() -> None:
    with pytest.raises(ValueError, match="at least one attempt"):
        power(0, 0.5, 0.8)


def test_rejects_a_probability_outside_the_unit_interval() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        power(4, 0.5, 1.5)
