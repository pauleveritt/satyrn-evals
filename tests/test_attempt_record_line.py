"""`line_crossed` / `line_patch_path` / `line_harvest_error` on an attempt
record: the declared-line harvest, additive on top of every generation.

Default tier: pure round-trips, built by hand, no process.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.budget import LineCrossing
from satyrn_evals.verdict import Verdict

SHA = "0" * 40
DIGEST = "1" * 64
AT = "2026-09-19T00:00:00+00:00"


def _record(**overrides: object) -> AttemptRecord:
    fields: dict = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="attempt recorded and graded", task="t", command=("pi",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt", patch_digest=DIGEST,
        transcript_digest=DIGEST, verdict=Verdict.PASS, receipt_path="receipt.json", timeout=3000.0,
        rung="R1", contract_digest=DIGEST, workspace_base_sha=SHA, attempt_dir="t-1",
    )
    return AttemptRecord(**(fields | overrides))


def test_a_record_with_no_crossing_round_trips_with_no_line_fields(tmp_path: Path) -> None:
    write_attempt_record(tmp_path / "attempt.json", _record())
    body = json.loads((tmp_path / "attempt.json").read_text())
    assert "line_crossed" not in body
    assert "line_patch_path" not in body
    assert "line_harvest_error" not in body
    loaded = load_attempt_record(tmp_path / "attempt.json")
    assert loaded.line_crossed is None
    assert loaded.line_patch_path is None
    assert loaded.line_harvest_error is None


def test_a_crossing_with_a_harvested_patch_round_trips(tmp_path: Path) -> None:
    crossing = LineCrossing(by="tokens", output_tokens=32001, turn=40, at=AT)
    record = _record(line_crossed=crossing, line_patch_path="line.diff")
    write_attempt_record(tmp_path / "attempt.json", record)
    body = json.loads((tmp_path / "attempt.json").read_text())
    assert body["line_crossed"] == {"by": "tokens", "output_tokens": 32001, "turn": 40, "at": AT}
    assert body["line_patch_path"] == "line.diff"
    assert "line_harvest_error" not in body
    loaded = load_attempt_record(tmp_path / "attempt.json")
    assert loaded.line_crossed == crossing
    assert loaded.line_patch_path == "line.diff"
    assert loaded.line_harvest_error is None


def test_a_crossing_with_a_harvest_error_round_trips(tmp_path: Path) -> None:
    crossing = LineCrossing(by="turns", output_tokens=100, turn=49, at=AT)
    record = _record(line_crossed=crossing, line_harvest_error="OSError: git is wedged")
    write_attempt_record(tmp_path / "attempt.json", record)
    loaded = load_attempt_record(tmp_path / "attempt.json")
    assert loaded.line_crossed == crossing
    assert loaded.line_patch_path is None
    assert loaded.line_harvest_error == "OSError: git is wedged"


def test_a_crossing_that_wrote_nothing_and_had_no_error_round_trips(tmp_path: Path) -> None:
    """A blank cumulative diff at the crossing: crossed, but no patch, no error."""
    crossing = LineCrossing(by="tokens", output_tokens=101, turn=1, at=AT)
    record = _record(line_crossed=crossing)
    write_attempt_record(tmp_path / "attempt.json", record)
    loaded = load_attempt_record(tmp_path / "attempt.json")
    assert loaded.line_crossed == crossing
    assert loaded.line_patch_path is None
    assert loaded.line_harvest_error is None


def test_a_line_patch_path_requires_a_crossing() -> None:
    with pytest.raises(ValueError, match="line_patch_path"):
        _record(line_patch_path="line.diff")


def test_a_line_harvest_error_requires_a_crossing() -> None:
    with pytest.raises(ValueError, match="line_harvest_error"):
        _record(line_harvest_error="boom")


def test_a_line_patch_path_and_harvest_error_are_mutually_exclusive() -> None:
    crossing = LineCrossing(by="tokens", output_tokens=101, turn=1, at=AT)
    with pytest.raises(ValueError, match="cannot both"):
        _record(line_crossed=crossing, line_patch_path="line.diff", line_harvest_error="boom")


def test_a_line_patch_path_must_be_non_empty() -> None:
    crossing = LineCrossing(by="tokens", output_tokens=101, turn=1, at=AT)
    with pytest.raises(ValueError, match="non-empty"):
        _record(line_crossed=crossing, line_patch_path="")


def test_a_refused_cell_may_still_carry_a_line_crossing(tmp_path: Path) -> None:
    """A cell can cross the line and still end at any outcome (spec: 'A cell
    that ends before crossing either line has line_crossed: null ... its
    final verdict IS its verdict at the line' -- implying the converse: a
    cell that DID cross keeps its own final code/verdict too)."""
    crossing = LineCrossing(by="turns", output_tokens=10, turn=5, at=AT)
    record = _record(
        outcome=AttemptOutcome.REFUSED, code=AttemptCode.NO_PATCH, verdict=None,
        receipt_path=None, patch_path=None, transcript_path="transcript.txt",
        patch_digest=None, line_crossed=crossing, line_patch_path="line.diff",
    )
    assert record.code is AttemptCode.NO_PATCH
    assert record.line_crossed == crossing


def test_line_crossed_must_be_a_line_crossing_or_null() -> None:
    with pytest.raises(ValueError, match="LineCrossing"):
        _record(line_crossed={"by": "tokens", "output_tokens": 1, "turn": 1, "at": AT})  # type: ignore[arg-type]
