"""The diagnostic Summary: counts-only tally over attempt records."""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.summary import Summary, compute_summary, write_summary
from satyrn_evals.verdict import Verdict

_CODES = frozenset(code.value for code in AttemptCode)
_VERDICTS = frozenset(v.value for v in Verdict)


def make_record(
    code: AttemptCode, verdict: Verdict | None, *, command_exit: int | None = 0
) -> AttemptRecord:
    outcome = AttemptOutcome.ATTEMPTED if verdict is not None else AttemptOutcome.REFUSED
    attempted = verdict is not None
    return AttemptRecord(
        version=1,
        outcome=outcome,
        code=code,
        message="test",
        task="format_number",
        command=("fake",),
        command_exit=command_exit,
        patch_path="patch.diff" if attempted else None,
        transcript_path="transcript.txt" if attempted else None,
        patch_digest="a" * 64 if attempted else None,
        transcript_digest="b" * 64 if attempted else None,
        verdict=verdict,
        receipt_path="receipt.json" if attempted else None,
        workspace_base_sha="c" * 40,
    )


def test_summary_round_trip_and_tally(tmp_path: Path) -> None:
    summary = compute_summary([make_record(AttemptCode.OK, Verdict.PASS)])
    path = tmp_path / "summary.json"
    write_summary(path, summary)
    data = json.loads(path.read_text())
    assert data["n"] == 1 and data["attempted"] == 1 and data["refused"] == 0
    assert data["code_counts"][AttemptCode.OK.value] == 1
    assert data["verdict_counts"][Verdict.PASS.value] == 1
    assert data["timeouts"] == 0


def test_compute_summary_all_refused_is_the_sibling() -> None:
    summary = compute_summary(
        [
            make_record(AttemptCode.NO_PATCH, None),
            make_record(AttemptCode.COMMAND_TIMEOUT, None, command_exit=None),
        ]
    )
    assert summary.n == 2 and summary.attempted == 0 and summary.refused == 2
    assert summary.code_counts[AttemptCode.NO_PATCH.value] == 1
    assert summary.timeouts == 1


def test_compute_summary_tallies_verdicts_over_attempted_only() -> None:
    summary = compute_summary(
        [
            make_record(AttemptCode.OK, Verdict.PASS),
            make_record(AttemptCode.OK, Verdict.FAIL),
            make_record(AttemptCode.NO_PATCH, None),
        ]
    )
    assert summary.attempted == 2 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 1
    assert summary.verdict_counts[Verdict.FAIL.value] == 1
    assert summary.verdict_counts[Verdict.UNAVAILABLE.value] == 0


def test_summary_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Summary(n=-1, attempted=0, refused=0, code_counts={c: 0 for c in _CODES},
                verdict_counts={v: 0 for v in _VERDICTS}, timeouts=0)
    with pytest.raises(ValueError, match="attempted \\+ refused"):
        Summary(n=2, attempted=0, refused=0, code_counts={c: 0 for c in _CODES},
                verdict_counts={v: 0 for v in _VERDICTS}, timeouts=0)
    with pytest.raises(ValueError, match="one key per"):
        Summary(n=0, attempted=0, refused=0, code_counts={"NOPE": 0},
                verdict_counts={v: 0 for v in _VERDICTS}, timeouts=0)
    with pytest.raises(ValueError, match="timeouts must equal"):
        Summary(n=0, attempted=0, refused=0, code_counts={c: 0 for c in _CODES},
                verdict_counts={v: 0 for v in _VERDICTS}, timeouts=1)
