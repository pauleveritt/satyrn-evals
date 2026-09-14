"""Usage totals count ONLY terminal `message_end` events that carry usage.

Every refusal below has a success sibling built from the same fixture shape
(`BRIEF.md` rule 6): the *only* difference between a refusing and an
accepting fixture is the one thing under test -- a missing usage object, an
empty transcript, or a malformed line.

The point of the regression witness below is the recorded review finding: a
naive walk-every-usage reader inflates output 5.5x by also counting
streaming `message_update` snapshots and the duplicate usage `turn_end`
repeats from the `message_end` it follows. The correct rule counts each
assistant response's usage exactly once, from its terminal `message_end`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from usage_totals import (  # noqa: E402  # type: ignore[missing-import]  # scripts/ added via sys.path above
    UsageError,
    compute_usage_totals,
    main,
    read_usage_totals,
)


def _lines(*events: dict) -> str:
    return "".join(json.dumps(event) + "\n" for event in events)


def _message_end(usage: dict | None) -> dict:
    """A `message_end` event for an assistant turn, optionally carrying usage."""
    message: dict = {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}
    if usage is not None:
        message["usage"] = usage
    return {"type": "message_end", "message": message}


def _message_update(usage: dict) -> dict:
    return {"type": "message_update", "usage": usage}


def _turn_end(usage: dict) -> dict:
    return {"type": "turn_end", "message": {"role": "assistant", "usage": usage}}


# --- THE KEY REGRESSION WITNESS ---------------------------------------------


def test_repeated_usage_in_message_update_and_turn_end_is_not_double_counted(
) -> None:
    """The exact inflation the review found: only the message_end usage counts.

    The same completion's usage appears three times in a real streaming
    transcript -- as a `message_update` snapshot while it streams in, again
    on the `turn_end` that closes the turn, and finally on the terminal
    `message_end`. A naive walk-every-usage reader sums all three and
    inflates output; this reader must total ONLY the `message_end` value.
    """
    usage = {"input": 1296, "output": 14}
    text = _lines(
        {"type": "turn_start", "turn": 1},
        _message_update({"input": 0, "output": 0}),
        _message_update(usage),  # the streaming snapshot repeats the final usage
        _turn_end(usage),  # turn_end repeats the same usage again
        _message_end(usage),  # the one event that should be counted
    )

    totals = read_usage_totals(text)

    assert totals.input_total == 1296
    assert totals.output_total == 14
    assert totals.counted_events == 1


def test_two_full_streamed_turns_sum_only_their_two_message_end_events() -> None:
    """A fuller shape of the same witness, matching the real transcript's pattern."""
    usage_a = {"input": 1296, "output": 14}
    usage_b = {"input": 11728, "output": 560}
    text = _lines(
        _message_update({"input": 0, "output": 0}),
        _message_update(usage_a),
        _turn_end(usage_a),
        _message_end(usage_a),
        _message_update({"input": 0, "output": 0}),
        _message_update(usage_b),
        _turn_end(usage_b),
        _message_end(usage_b),
    )

    totals = read_usage_totals(text)

    # These are the reference transcript's real, verified totals.
    assert totals.input_total == 1296 + 11728 == 13024
    assert totals.output_total == 14 + 560 == 574
    assert totals.counted_events == 2


# --- message_end without usage is skipped, not zero -------------------------


def test_a_message_end_without_usage_is_skipped_not_counted() -> None:
    usage = {"input": 500, "output": 50}
    text = _lines(
        _message_end(None),  # a user or tool-result message_end: no usage
        _message_end(usage),
    )

    totals = read_usage_totals(text)

    assert totals.input_total == 500
    assert totals.output_total == 50
    assert totals.counted_events == 1  # not 2 -- the usage-less one is skipped


def test_a_message_end_with_usage_is_counted() -> None:
    """Sibling success: the same shape, but usage present, is counted."""
    usage = {"input": 500, "output": 50}
    totals = read_usage_totals(_lines(_message_end(usage)))
    assert totals.counted_events == 1


# --- no countable event: refuse rather than report 0 ------------------------


def test_a_transcript_with_no_countable_message_end_is_refused() -> None:
    with pytest.raises(UsageError) as caught:
        read_usage_totals(
            _lines(
                {"type": "session", "id": 1},
                {"type": "agent_start"},
                {"type": "turn_start", "turn": 1},
                _message_update({"input": 0, "output": 0}),
                _message_end(None),  # present, but carries no usage
                {"type": "turn_end", "message": {"role": "user"}},
                {"type": "agent_end"},
            )
        )
    message = str(caught.value)
    assert "UNMEASURED, not zero" in message
    # it must name the event types it actually saw
    assert "agent_start" in message
    assert "turn_end" in message
    assert "message_end" in message


def test_a_transcript_with_one_countable_message_end_succeeds() -> None:
    """Sibling success: same shape, one message_end now carries usage."""
    usage = {"input": 10, "output": 2}
    totals = read_usage_totals(
        _lines(
            {"type": "session", "id": 1},
            {"type": "agent_start"},
            _message_end(usage),
            {"type": "agent_end"},
        )
    )
    assert totals.counted_events == 1
    assert totals.output_total == 2


def test_an_empty_transcript_is_refused() -> None:
    with pytest.raises(UsageError, match="UNMEASURED, not zero"):
        read_usage_totals("")


# --- malformed / non-JSON lines are skipped without crashing -----------------


def test_malformed_and_non_json_lines_are_skipped_without_crashing() -> None:
    usage = {"input": 10, "output": 2}
    text = (
        "not json at all\n"
        + "{broken json\n"
        + "\n"  # blank line
        + _lines(_message_end(usage))
    )

    totals = read_usage_totals(text)

    assert totals.counted_events == 1
    assert totals.output_total == 2


def test_a_transcript_with_only_valid_json_is_accepted() -> None:
    """Sibling success: the same content, without the noise lines, behaves the same."""
    usage = {"input": 10, "output": 2}
    totals = read_usage_totals(_lines(_message_end(usage)))
    assert totals.counted_events == 1
    assert totals.output_total == 2


# --- multiple responses sum correctly ----------------------------------------


def test_multiple_message_end_responses_sum_correctly() -> None:
    text = _lines(
        _message_end({"input": 100, "output": 10}),
        _message_end(None),  # a tool-result message_end in between
        _message_end({"input": 200, "output": 20}),
        _message_end({"input": 300, "output": 30}),
    )

    totals = read_usage_totals(text)

    assert totals.input_total == 600
    assert totals.output_total == 60
    assert totals.counted_events == 3


# --- negative usage is refused, not reported as a negative total ------------


def test_a_negative_usage_value_is_refused() -> None:
    with pytest.raises(UsageError, match="negative count"):
        read_usage_totals(_lines(_message_end({"input": -1, "output": 5})))


def test_a_nonnegative_usage_value_is_accepted() -> None:
    totals = read_usage_totals(_lines(_message_end({"input": 0, "output": 5})))
    assert totals.input_total == 0
    assert totals.output_total == 5


# --- compute_usage_totals is pure over already-parsed events ----------------


def test_compute_usage_totals_accepts_pre_parsed_events() -> None:
    usage = {"input": 10, "output": 2}
    totals = compute_usage_totals([_message_end(usage)])
    assert totals.counted_events == 1
    assert totals.input_keys_used == ("input",)
    assert totals.output_keys_used == ("output",)


# --- the CLI, both directions ------------------------------------------------


def test_cli_records_measured_totals(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text(
        _lines(_message_end({"input": 100, "output": 10})),
        encoding="utf-8",
    )
    record = tmp_path / "usage.json"
    assert main([str(transcript), "--record", str(record)]) == 0
    stored = json.loads(record.read_text(encoding="utf-8"))
    assert stored["input_total"] == 100
    assert stored["output_total"] == 10
    assert stored["counted_events"] == 1
    assert stored["terminal_event_type"] == "message_end"


def test_cli_refuses_and_writes_no_record_when_unmeasured(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text(_lines({"type": "agent_end"}), encoding="utf-8")
    record = tmp_path / "usage.json"
    assert main([str(transcript), "--record", str(record)]) == 1
    assert not record.exists()  # a refused run leaves no number behind


def test_cli_reports_a_missing_transcript_distinctly(tmp_path: Path) -> None:
    assert main([str(tmp_path / "nope.txt")]) == 2
