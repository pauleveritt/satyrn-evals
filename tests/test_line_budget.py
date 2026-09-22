"""The declared record-level line: a non-stopping, harvest-triggering
watcher over the same Pi-shaped transcript lines the budget tripwire reads.

Pure: no process, no git. See `test_workspace_line_harvest.py` for the
harvest side and `test_attempt_record_line.py` for the record shape.
"""

import json

import pytest

from satyrn_evals.budget import LineBudget, LineCrossing, LineTripwire


def _turn() -> str:
    return json.dumps({"type": "turn_start"})


def _assistant(output: int) -> str:
    return json.dumps(
        {"type": "message_end", "message": {"role": "assistant", "usage": {"output": output}}}
    )


def test_a_line_budget_must_be_positive_integers() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        LineBudget(output_tokens=0, turns=48)
    with pytest.raises(ValueError, match="positive integer"):
        LineBudget(output_tokens=100, turns=0)
    with pytest.raises(ValueError, match="positive integer"):
        LineBudget(output_tokens=True, turns=48)  # type: ignore[arg-type]


def test_crossing_the_token_line_latches_and_reports_tokens() -> None:
    wire = LineTripwire(LineBudget(output_tokens=100, turns=48))
    assert wire.feed(_assistant(100)) is False  # at the line is within it
    assert wire.crossed is None
    assert wire.feed(_assistant(1)) is True
    crossing = wire.crossed
    assert crossing is not None
    assert crossing.by == "tokens"
    assert crossing.output_tokens == 101
    assert crossing.turn == 0
    # latched: further lines report no new crossing
    assert wire.feed(_assistant(500)) is False
    assert wire.crossed is crossing


def test_crossing_the_turn_line_latches_and_reports_turns() -> None:
    wire = LineTripwire(LineBudget(output_tokens=32000, turns=2))
    assert wire.feed(_turn()) is False
    assert wire.feed(_turn()) is False
    assert wire.feed(_turn()) is True
    crossing = wire.crossed
    assert crossing is not None
    assert crossing.by == "turns"
    assert crossing.turn == 3


def test_crossing_both_in_one_step_reports_tokens_deterministically() -> None:
    """Same order as BudgetTripwire.feed: tokens checked before turns.

    A single transcript line carries either a ``turn_start`` or a
    ``message_end``, never both, so "one step" over both lines at once means:
    turns is already over the line (fed earlier) and this line's tokens also
    put tokens over. ``by`` deterministically reports ``"tokens"``.
    """
    wire = LineTripwire(LineBudget(output_tokens=10, turns=1))
    wire.usage.turns = 5  # already over the turn line, before this feed
    event = json.dumps(
        {"type": "message_end", "message": {"role": "assistant", "usage": {"output": 11}}}
    )
    assert wire.feed(event) is True
    assert wire.crossed is not None
    assert wire.crossed.by == "tokens"


def test_never_crossing_leaves_crossed_none() -> None:
    wire = LineTripwire(LineBudget(output_tokens=32000, turns=48))
    for _ in range(10):
        assert wire.feed(_turn()) is False
        assert wire.feed(_assistant(100)) is False
    assert wire.crossed is None


def test_exactly_at_the_limit_is_not_crossed_one_over_is() -> None:
    wire = LineTripwire(LineBudget(output_tokens=100, turns=48))
    assert wire.feed(_assistant(100)) is False
    assert wire.crossed is None
    wire2 = LineTripwire(LineBudget(output_tokens=100, turns=48))
    assert wire2.feed(_assistant(101)) is True
    assert wire2.crossed is not None


def test_line_crossing_is_a_frozen_shape() -> None:
    crossing = LineCrossing(by="tokens", output_tokens=101, turn=3, at="2026-09-19T00:00:00+00:00")
    assert crossing.by == "tokens"
    with pytest.raises(AttributeError):
        crossing.by = "turns"  # type: ignore[misc]


@pytest.mark.parametrize("by", ["neither", "TOKENS", ""])
def test_line_crossing_rejects_an_unknown_by(by: str) -> None:
    with pytest.raises(ValueError):
        LineCrossing(by=by, output_tokens=1, turn=1, at="2026-09-19T00:00:00+00:00")  # type: ignore[arg-type]
