"""The session repeat tripwire: latching, keyed on the tool_end payload."""

import pytest

from satyrn_evals.session_repeat_limit import SessionRepeatTripwire


def _call(name: str, **args) -> dict:
    """The shape the session stream actually carries the arguments in."""
    return {
        "type": "message_update",
        "assistantMessageEvent": {
            "toolCall": {"type": "toolCall", "name": name, "arguments": args}
        },
    }


def test_identical_consecutive_calls_trip_the_wire() -> None:
    wire = SessionRepeatTripwire(3)
    for _ in range(2):
        assert wire.feed(_call("read", path="app.py")) is False
    assert wire.feed(_call("read", path="app.py")) is True
    assert wire.run == 3


def test_a_differing_argument_restarts_the_run() -> None:
    """Success sibling: work that varies is not a loop, however long."""
    wire = SessionRepeatTripwire(3)
    for i in range(20):
        assert wire.feed(_call("read", path=f"f{i}.py")) is False
    assert wire.tripped is False


def test_the_wire_latches() -> None:
    wire = SessionRepeatTripwire(2)
    wire.feed(_call("bash", cmd="x"))
    assert wire.feed(_call("bash", cmd="x")) is True
    assert wire.feed(_call("read", path="other")) is True


def test_a_step_boundary_resets_the_run() -> None:
    """Steps are separate requests; a call repeated across one is not a loop."""
    wire = SessionRepeatTripwire(3)
    wire.feed(_call("read", path="a"))
    wire.feed(_call("read", path="a"))
    wire.reset()
    assert wire.feed(_call("read", path="a")) is False
    assert wire.run == 1


def test_events_without_a_tool_call_are_ignored() -> None:
    wire = SessionRepeatTripwire(2)
    for _ in range(10):
        wire.feed({"type": "turn_end", "message": {}})
    assert wire.tripped is False


def test_an_unreadable_payload_is_ignored_not_counted() -> None:
    """Refusal direction: a spending rule must not end a step on noise."""
    wire = SessionRepeatTripwire(2)
    for _ in range(10):
        wire.feed({"assistantMessageEvent": {"toolCall": "not-an-object"}})
        wire.feed(None)
    assert wire.tripped is False


def test_a_limit_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        SessionRepeatTripwire(0)


# --- The window tripwire: a rotating loop no consecutive rule can see ---

from satyrn_evals.session_repeat_limit import SessionWindowTripwire  # noqa: E402


def test_a_rotating_loop_trips_the_window_wire() -> None:
    """A-B-C-A-B-C is the shape session 11 spent 194 calls on.

    Its longest identical-consecutive run is 1, so the consecutive detector is
    blind to it by construction.
    """
    wire = SessionWindowTripwire(3, window=20)
    probes = [_call("bash", command=f"probe {i}") for i in range(3)]
    for _ in range(2):
        for p in probes:
            assert wire.feed(p) is False
    assert wire.feed(probes[0]) is True


def test_the_consecutive_wire_is_blind_to_that_same_loop() -> None:
    """The sibling that justifies adding a second detector rather than
    retuning the first: fed the identical sequence, it never fires."""
    wire = SessionRepeatTripwire(3)
    probes = [_call("bash", command=f"probe {i}") for i in range(3)]
    for _ in range(10):
        for p in probes:
            wire.feed(p)
    assert wire.tripped is False


def test_varied_work_does_not_trip_the_window_wire() -> None:
    """Success direction: distinct calls never accumulate."""
    wire = SessionWindowTripwire(3, window=20)
    for i in range(40):
        assert wire.feed(_call("bash", command=f"step {i}")) is False


def test_the_window_forgets(y_window: int = 4) -> None:
    """A key recurring slower than the window is not a loop."""
    wire = SessionWindowTripwire(2, window=y_window)
    wire.feed(_call("bash", command="target"))
    for i in range(y_window):
        wire.feed(_call("bash", command=f"filler {i}"))
    assert wire.feed(_call("bash", command="target")) is False


def test_a_step_boundary_resets_the_window() -> None:
    wire = SessionWindowTripwire(2, window=20)
    wire.feed(_call("bash", command="x"))
    wire.reset()
    assert wire.feed(_call("bash", command="x")) is False


def test_an_unreadable_payload_is_ignored_by_the_window_wire() -> None:
    """Refusal direction: noise must not end a step."""
    wire = SessionWindowTripwire(2, window=20)
    for _ in range(10):
        wire.feed({"assistantMessageEvent": {"toolCall": "not-an-object"}})
        wire.feed(None)
    assert wire.tripped is False


def test_a_window_smaller_than_the_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="cannot be smaller"):
        SessionWindowTripwire(5, window=3)
