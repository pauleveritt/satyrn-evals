"""The turn ledger: counting model turns the same way on both routes.

Default tier throughout -- pure functions over already-parsed event
dicts, nothing spawns.
"""

import json
from pathlib import Path

from satyrn_evals.adapters.pi_session import _SESSION_KINDS
from satyrn_evals.turn_ledger import (
    TurnOutcome,
    count_turns,
    events_from_pi_stdout,
    events_from_session_transcript,
)

REAL_TRANSCRIPT = (
    Path(__file__).parent / "data" / "real-session-phased-verify-transcript.jsonl"
)


def _turn_start() -> dict[str, object]:
    return {"type": "turn_start"}


def _turn_end(stop_reason: str | None, *, with_usage: bool = True) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant"}
    if stop_reason is not None:
        message["stopReason"] = stop_reason
    if with_usage:
        message["usage"] = {"input": 10, "output": 5}
    return {"type": "turn_end", "message": message, "toolResults": []}


def _message_update() -> dict[str, object]:
    return {"type": "message_update", "usage": {"input": 0, "output": 0}}


def test_a_simple_stream_reports_one_started_and_one_ended_normal_turn() -> None:
    ledger = count_turns([_turn_start(), _turn_end("stop")])
    assert ledger.observed_starts == 1
    assert ledger.open_at_capture_end == 0
    assert ledger.ended == (TurnOutcome("normal", "stop"),)


def test_one_invocation_can_hold_more_than_one_turn() -> None:
    """The thing the original 'one Pi turn per invocation' assumption got
    wrong: tool execution inside one process can trigger another
    generation, each with its own start/end pair."""
    ledger = count_turns(
        [_turn_start(), _turn_end("toolUse"), _turn_start(), _turn_end("stop")]
    )
    assert ledger.observed_starts == 2
    assert ledger.open_at_capture_end == 0
    assert [o.kind for o in ledger.ended] == ["normal", "normal"]


def test_tooluse_is_a_normal_outcome_not_an_anomaly() -> None:
    ledger = count_turns([_turn_start(), _turn_end("toolUse")])
    assert ledger.ended[0].kind == "normal"
    assert ledger.ended[0].stop_reason == "toolUse"


def test_error_and_aborted_are_their_own_distinct_outcomes() -> None:
    ledger = count_turns(
        [
            _turn_start(), _turn_end("error"),
            _turn_start(), _turn_end("aborted"),
        ]
    )
    assert [o.kind for o in ledger.ended] == ["error", "aborted"]


def test_an_unrecognized_stop_reason_defaults_to_normal_not_a_guessed_error() -> None:
    ledger = count_turns([_turn_start(), _turn_end("length")])
    assert ledger.ended[0].kind == "normal"
    assert ledger.ended[0].stop_reason == "length"


def test_a_turn_end_with_no_message_is_unknown_not_dropped() -> None:
    ledger = count_turns([_turn_start(), {"type": "turn_end"}])
    assert ledger.ended[0].kind == "unknown"
    assert ledger.ended[0].stop_reason is None
    assert ledger.unresolvable


def test_an_unmatched_start_is_open_not_ended_and_not_aborted() -> None:
    """Proves the function stays pure over the event stream: an open turn
    is retained as open, never silently reclassified as terminal. One
    turn closes normally; a second start never gets a matching end --
    a truncated trace, the last event this stream happens to have."""
    ledger = count_turns([_turn_start(), _turn_end("stop"), _turn_start()])
    assert ledger.observed_starts == 2
    assert ledger.open_at_capture_end == 1
    assert len(ledger.ended) == 1


def test_duplicate_message_updates_never_inflate_the_turn_count() -> None:
    """The same class of bug usage_totals.py had to guard token totals
    against, now proven for turn counting."""
    events = [_turn_start()] + [_message_update()] * 50 + [_turn_end("stop")]
    ledger = count_turns(events)
    assert ledger.observed_starts == 1
    assert len(ledger.ended) == 1


def test_a_turn_end_with_no_usage_still_counts_and_classifies() -> None:
    ledger = count_turns([_turn_start(), _turn_end("stop", with_usage=False)])
    assert ledger.ended[0].kind == "normal"


def test_starts_not_retained_reports_none_never_a_fabricated_zero() -> None:
    ledger = count_turns([_turn_end("stop")], starts_retained=False)
    assert ledger.observed_starts is None
    assert ledger.open_at_capture_end is None
    assert ledger.unresolvable
    # The ended-turn count is still answerable even when starts are not:
    assert len(ledger.ended) == 1


def test_retries_are_counted_but_never_change_the_turn_count() -> None:
    events = [
        _turn_start(),
        {"type": "auto_retry_start", "attempt": 1},
        {"type": "auto_retry_end", "success": True, "attempt": 2},
        _turn_end("stop"),
    ]
    ledger = count_turns(events)
    assert ledger.observed_starts == 1
    assert len(ledger.ended) == 1
    assert ledger.retries_observed == 1


# --- events_from_pi_stdout ---------------------------------------------------


def test_events_from_pi_stdout_parses_real_pi_event_lines() -> None:
    text = (
        json.dumps({"type": "turn_start"}) + "\n"
        + json.dumps({"type": "turn_end", "message": {"stopReason": "stop"}}) + "\n"
    )
    events = events_from_pi_stdout(text)
    assert [e["type"] for e in events] == ["turn_start", "turn_end"]


def test_events_from_pi_stdout_skips_the_adapters_own_marker_lines() -> None:
    """pi_implementer.py writes {"adapter_marker": "turn_start", "index": N}
    into the same file ahead of each phase's real pi output -- an
    unfortunate name collision with pi's genuine turn_start event, resolved
    because the marker carries no "type" key at all."""
    text = (
        json.dumps({"adapter_marker": "turn_start", "index": 0}) + "\n"
        + json.dumps({"type": "turn_start"}) + "\n"
        + json.dumps({"type": "turn_end", "message": {"stopReason": "stop"}}) + "\n"
    )
    events = events_from_pi_stdout(text)
    assert len(events) == 2
    assert all("type" in e for e in events)


def test_events_from_pi_stdout_skips_unparseable_lines() -> None:
    text = "not json\n" + json.dumps({"type": "turn_start"}) + "\n"
    events = events_from_pi_stdout(text)
    assert len(events) == 1


def test_events_from_pi_stdout_skips_blank_lines() -> None:
    text = "\n" + json.dumps({"type": "turn_start"}) + "\n\n"
    events = events_from_pi_stdout(text)
    assert len(events) == 1


# --- events_from_session_transcript -------------------------------------------


def test_events_from_session_transcript_unwraps_the_payload() -> None:
    text = (
        json.dumps({"type": "session_started", "conversation_id": "x"}) + "\n"
        + json.dumps(
            {
                "type": "event",
                "step_id": "phase-1-home",
                "kind": "turn_end",
                "payload": {"type": "turn_end", "message": {"stopReason": "stop"}},
            }
        )
        + "\n"
    )
    events, starts_retained = events_from_session_transcript(text)
    assert events == [{"type": "turn_end", "message": {"stopReason": "stop"}}]


def test_starts_retained_reflects_the_real_session_kinds_policy() -> None:
    """Not hand-copied: read from pi_session's own dict, so this stays
    correct if that policy ever changes."""
    _, starts_retained = events_from_session_transcript("")
    assert starts_retained == ("turn_start" in _SESSION_KINDS)


def test_the_real_transcript_reports_twenty_normal_turns_with_starts_unknown() -> None:
    """Acceptance criteria 1 and 8 together: the real transcript this
    design was verified against, read through this module rather than a
    one-off script."""
    events, starts_retained = events_from_session_transcript(
        REAL_TRANSCRIPT.read_text()
    )
    assert starts_retained is False
    ledger = count_turns(events, starts_retained=starts_retained)
    assert ledger.observed_starts is None
    assert ledger.open_at_capture_end is None
    assert ledger.unresolvable
    assert len(ledger.ended) == 20
    assert all(o.kind == "normal" for o in ledger.ended)
    tool_use = sum(1 for o in ledger.ended if o.stop_reason == "toolUse")
    stop = sum(1 for o in ledger.ended if o.stop_reason == "stop")
    assert (tool_use, stop) == (17, 3)
