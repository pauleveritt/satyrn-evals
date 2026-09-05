"""The token-floor reader refuses an unmeasured floor, and reads a real one.

Every refusal below has a success sibling over the same fixture shape
(`BRIEF.md` rule 6), and the pair discriminates in both directions on
transcripts drawn from the same batch (rule 8): the *only* difference between
the refusing and accepting fixtures is the presence of a usage figure.

The point of the refusal direction is the recorded silent-zero class: an
absent measurement reported as `0` would flow straight into an Envelope cap
argument. Absent must stay absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from token_floor import (  # noqa: E402  # type: ignore[missing-import]  # scripts/ added via sys.path above
    FloorError,
    main,
    read_floor,
)

_AGENT_START = {"type": "agent_start", "session": 3}
_TURN = {"type": "turn_start", "turn": 1}


def _lines(*events: dict) -> str:
    return "".join(json.dumps(event) + "\n" for event in events)


# --- refusals ------------------------------------------------------------


def test_a_transcript_with_no_usage_is_unmeasured_not_zero() -> None:
    with pytest.raises(FloorError) as caught:
        read_floor(_lines(_AGENT_START, _TURN, {"type": "agent_end"}))
    message = str(caught.value)
    assert "UNMEASURED, not zero" in message
    # it must name what it actually saw, so the first smoke teaches the shape
    assert "agent_start" in message and "agent_end" in message
    assert "input_tokens" in message  # the keys it tried


def test_an_empty_transcript_is_refused() -> None:
    with pytest.raises(FloorError, match="unmeasured, not zero"):
        read_floor("")


def test_an_all_placeholder_transcript_is_refused_rather_than_reported() -> None:
    """Every usage block zero == an unpopulated stream, not a floor of 0."""
    text = _lines(
        _AGENT_START,
        {"type": "message_update", "usage": {"input": 0, "output": 0}},
        {"type": "message_update", "usage": {"input": 0, "output": 0}},
    )
    with pytest.raises(FloorError, match="UNMEASURED, not zero"):
        read_floor(text)


def test_a_negative_usage_value_is_refused_immediately() -> None:
    text = _lines(
        {"type": "message_update", "usage": {"input": -1}},
        {"type": "message_update", "usage": {"input": 1546}},
    )
    with pytest.raises(FloorError, match="negative input tokens"):
        read_floor(text)


# --- successes -----------------------------------------------------------


def test_a_nested_usage_figure_is_read_with_its_key() -> None:
    text = _lines(
        _AGENT_START, {"type": "message_start", "usage": {"input_tokens": 686}}
    )
    assert read_floor(text) == (686, "usage.input_tokens")


def test_a_top_level_usage_figure_is_read() -> None:
    text = _lines(_AGENT_START, {"type": "message_start", "prompt_tokens": 1267})
    assert read_floor(text) == (1267, "prompt_tokens")


def test_the_first_model_call_wins_not_the_largest() -> None:
    text = _lines(
        _AGENT_START,
        {"type": "message_start", "usage": {"input_tokens": 700}},
        {"type": "message_start", "usage": {"input_tokens": 9753}},
    )
    assert read_floor(text)[0] == 700


def test_non_json_noise_between_events_is_skipped() -> None:
    text = "not json\n" + _lines(
        {"type": "message_start", "usage": {"input_tokens": 686}}
    )
    assert read_floor(text) == (686, "usage.input_tokens")


# --- the CLI, both directions -------------------------------------------


def test_cli_records_a_measured_floor(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text(
        _lines({"type": "message_start", "usage": {"input_tokens": 686}}),
        encoding="utf-8",
    )
    record = tmp_path / "floor.json"
    assert main([str(transcript), "--record", str(record)]) == 0
    stored = json.loads(record.read_text(encoding="utf-8"))
    assert stored["input_token_floor"] == 686
    assert stored["source_key"] == "usage.input_tokens"


def test_cli_refuses_and_writes_no_record_when_unmeasured(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text(_lines({"type": "agent_end"}), encoding="utf-8")
    record = tmp_path / "floor.json"
    assert main([str(transcript), "--record", str(record)]) == 1
    assert not record.exists()  # a refused run leaves no number behind


def test_cli_reports_a_missing_transcript_distinctly(tmp_path: Path) -> None:
    assert main([str(tmp_path / "nope.txt")]) == 2


# --- the shape observed in the 2026-09-05 Baseline smoke -----------------
#
# pi streams `message_update` events whose usage block is not yet populated:
# in that smoke 217 events carried usage and only 68 carried a positive
# input count. Reading the first usage event would have reported 0 -- the
# recorded silent-zero class -- so placeholders are skipped and an all-zero
# transcript is refused. The real key is `usage.input`, which this
# repository learned from the artifact rather than from recall.


def test_placeholder_zeros_are_skipped_and_the_first_real_count_wins() -> None:
    text = _lines(
        _AGENT_START,
        {
            "type": "message_update",
            "usage": {"input": 0, "output": 0, "totalTokens": 0},
        },
        {
            "type": "message_update",
            "usage": {"input": 0, "output": 0, "totalTokens": 0},
        },
        {
            "type": "message_update",
            "usage": {"input": 1546, "output": 16, "totalTokens": 1562},
        },
        {"type": "message_update", "usage": {"input": 22103, "output": 84}},
    )
    assert read_floor(text) == (1546, "usage.input")


def test_the_observed_pi_usage_key_is_tried_first() -> None:
    """`usage.input` is the observed spelling; it must not lose to a guess."""
    text = _lines(
        {"type": "message_update", "usage": {"input": 1546, "input_tokens": 99}}
    )
    assert read_floor(text) == (1546, "usage.input")
