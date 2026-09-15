"""The repeated-call tripwire: a spending rule, not a nudge.

Evidence it discriminates, replayed offline over the V11c spike's 24
retained transcripts before any of this ran live: the longest run of
identical consecutive tool calls is 1, 3 or 5 on every cell that
succeeded, and 280 on each of the seven locked Baseline cells. Nothing
falls between 5 and 280, so any limit in that gap fires on exactly the
locked cells. `BRIEF.md` rule 8 wants both directions; both are pinned
here and against the real transcripts in
`tests/integration/test_repeat_limit_replay.py`.
"""

import json

import pytest

from satyrn_evals.repeat_limit import RepeatTripwire


def _call(tool: str = "read", path: str = "app.py") -> str:
    return json.dumps({
        "type": "tool_execution_start", "toolCallId": "x",
        "toolName": tool, "args": {"path": path},
    })


def test_identical_calls_below_the_limit_do_not_trip() -> None:
    """The success sibling: a healthy cell's repeats stay under it."""
    trip = RepeatTripwire(limit=10)
    assert not any(trip.feed(_call()) for _ in range(9))
    assert trip.tripped is False


def test_the_limitth_identical_call_trips() -> None:
    """The locked-loop shape: K identical consecutive calls."""
    trip = RepeatTripwire(limit=10)
    results = [trip.feed(_call()) for _ in range(10)]
    assert results[:9] == [False] * 9
    assert results[9] is True
    assert trip.tripped is True


def test_a_different_call_resets_the_run() -> None:
    """Consecutive means consecutive: progress clears the count, which is
    why a cell that reads the same file repeatedly *while doing other
    work* is not stopped."""
    trip = RepeatTripwire(limit=3)
    assert not trip.feed(_call())
    assert not trip.feed(_call())
    assert not trip.feed(_call(path="models.py"))  # resets
    assert not trip.feed(_call())
    assert not trip.feed(_call())
    assert trip.tripped is False


def test_differing_args_are_different_calls() -> None:
    """`read app.py` and `read models.py` are not the same call."""
    trip = RepeatTripwire(limit=2)
    assert not trip.feed(_call(path="a.py"))
    assert not trip.feed(_call(path="b.py"))
    assert trip.tripped is False


def test_non_tool_events_do_not_break_a_run() -> None:
    """A transcript interleaves message and turn events with tool calls;
    only tool calls count, and the others neither add to a run nor
    reset it."""
    trip = RepeatTripwire(limit=3)
    trip.feed(_call())
    trip.feed('{"type": "message_update"}')
    trip.feed('{"type": "turn_end", "message": {"content": []}}')
    trip.feed(_call())
    assert trip.feed(_call()) is True


def test_an_unparseable_line_is_ignored_not_fatal() -> None:
    """A live transcript is being written as this reads it, and a wrapper
    can put non-JSON in the stream. The tripwire is a spending rule and
    must never take down a cell over one bad line."""
    trip = RepeatTripwire(limit=2)
    trip.feed(_call())
    assert trip.feed("not json at all") is False
    assert trip.feed(_call()) is True


def test_the_trip_latches() -> None:
    """Once tripped it stays tripped, so the caller may act on the flag
    after the fact rather than only on the returning edge."""
    trip = RepeatTripwire(limit=1)
    assert trip.feed(_call()) is True
    assert trip.feed(_call(path="other.py")) is True
    assert trip.tripped is True


def test_a_limit_below_one_is_refused() -> None:
    """A limit of 0 would stop every cell at its first tool call. That is
    a configuration error, not a spending rule."""
    with pytest.raises(ValueError, match="limit"):
        RepeatTripwire(limit=0)
