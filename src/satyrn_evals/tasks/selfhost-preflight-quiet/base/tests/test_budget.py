"""The attempt budget tripwire, over Pi-shaped lines. Pure: no process."""

import json

import pytest

from satyrn_evals.budget import AttemptBudget, BudgetTripwire, UsageCounter


def _turn() -> str:
    return json.dumps({"type": "turn_start"})


def _assistant(output: int, role: str = "assistant") -> str:
    return json.dumps(
        {"type": "message_end", "message": {"role": role, "usage": {"input": 9000, "output": output, "cacheRead": 50000}}}
    )


def test_usage_counts_turns_and_assistant_output_only() -> None:
    counter = UsageCounter()
    for line in (_turn(), _assistant(120), _assistant(999, role="user"), _turn(), _assistant(30), "{partial", ""):
        counter.feed(line)
    assert (counter.turns, counter.output_tokens) == (2, 150)


def test_a_line_that_puts_output_over_budget_trips_and_latches() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=100, turns=48))
    assert not wire.feed(_turn())
    assert not wire.feed(_assistant(100))  # at the budget is within it
    assert wire.feed(_assistant(1))
    assert wire.over == "output_tokens"
    assert wire.feed(_turn())  # latched
    assert wire.message() == "attempt command spent 101 output tokens, over the budget of 100"


def test_the_turn_after_the_last_budgeted_turn_trips() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=32000, turns=2))
    assert not wire.feed(_turn()) and not wire.feed(_turn())
    assert wire.feed(_turn())
    assert wire.over == "turns"
    assert wire.message() == "attempt command started turn 3, over the budget of 2 turns"


def test_a_cell_within_both_budgets_never_trips() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=32000, turns=48))
    assert not any(wire.feed(line) for _ in range(48) for line in (_turn(), _assistant(600)))
    assert wire.over is None


@pytest.mark.parametrize("values", [(0, 48), (32000, 0), (True, 48), (32000, 1.5)])
def test_a_budget_must_be_positive_integers(values: tuple[object, object]) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        AttemptBudget(output_tokens=values[0], turns=values[1])  # type: ignore[arg-type]


def test_a_length_cut_assistant_message_still_counts_its_output_tokens() -> None:
    """Design section 3.1: the tripwire still sums `usage.output` under the cap."""
    wire = BudgetTripwire(AttemptBudget(output_tokens=16000, turns=72))
    cut = json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "length", "usage": {"output": 16000}}})
    assert not wire.feed(cut)
    assert wire.usage.output_tokens == 16000
    assert wire.feed(json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "length", "usage": {"output": 1}}}))
    assert wire.over == "output_tokens"


def test_an_ordinary_turn_under_the_cap_does_not_trip() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=16000, turns=72))
    assert not wire.feed(json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "end_turn", "usage": {"output": 5999}}}))
    assert wire.over is None
