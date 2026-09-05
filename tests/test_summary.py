"""The diagnostic Summary: counts-only tally over attempt cells.

A cell is (attempt directory name, record, parsed receipt dict or None).
Visible-task summaries carry cells + oracle_visibility but no contamination
section; hidden-task summaries additionally tally contamination outcomes
beside the verdict counts, with graded = flagged + clean + unmeasured.
"""

import dataclasses
import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.summary import Summary, compute_summary, write_summary
from satyrn_evals.verdict import Verdict

_CODES = frozenset(code.value for code in AttemptCode)
_VERDICTS = frozenset(v.value for v in Verdict)


def make_record(
    code: AttemptCode,
    verdict: Verdict | None,
    *,
    command_exit: int | None = 0,
    timeout: float = 123.0,
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
        timeout=timeout,
        workspace_base_sha="c" * 40,
    )


def _cell(
    name: str,
    code: AttemptCode = AttemptCode.OK,
    verdict: Verdict | None = Verdict.PASS,
    receipt: dict | None = None,
) -> tuple[str, AttemptRecord, dict | None]:
    record = make_record(code=code, verdict=verdict)
    return (name, record, receipt)


def _receipt_dict(
    checks: tuple[tuple[str, str], ...] = (("grader_content_in_patch", "clean"),),
) -> dict:
    return {
        "contamination": {
            "visibility": "hidden",
            "checks": [
                {"check": c, "outcome": o, "evidence": []} for c, o in checks
            ],
        }
    }


def test_summary_round_trip_and_tally(tmp_path: Path) -> None:
    summary = compute_summary(
        [("task-1", make_record(AttemptCode.OK, Verdict.PASS), None)],
        oracle_visibility="visible",
    )
    path = tmp_path / "summary.json"
    write_summary(path, summary)
    data = json.loads(path.read_text())
    assert data["n"] == 1 and data["attempted"] == 1 and data["refused"] == 0
    assert data["code_counts"][AttemptCode.OK.value] == 1
    assert data["verdict_counts"][Verdict.PASS.value] == 1
    assert data["timeouts"] == 0
    assert data["cells"] == ["task-1"]
    assert data["oracle_visibility"] == "visible"
    assert "contamination" not in data


def test_compute_summary_all_refused_is_the_sibling() -> None:
    summary = compute_summary(
        [
            ("task-1", make_record(AttemptCode.NO_PATCH, None), None),
            (
                "task-2",
                make_record(AttemptCode.COMMAND_TIMEOUT, None, command_exit=None),
                None,
            ),
        ],
        oracle_visibility="visible",
    )
    assert summary.n == 2 and summary.attempted == 0 and summary.refused == 2
    assert summary.code_counts[AttemptCode.NO_PATCH.value] == 1
    assert summary.timeouts == 1


def test_compute_summary_tallies_verdicts_over_attempted_only() -> None:
    summary = compute_summary(
        [
            ("task-1", make_record(AttemptCode.OK, Verdict.PASS), None),
            ("task-2", make_record(AttemptCode.OK, Verdict.FAIL), None),
            ("task-3", make_record(AttemptCode.NO_PATCH, None), None),
        ],
        oracle_visibility="visible",
    )
    assert summary.attempted == 2 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 1
    assert summary.verdict_counts[Verdict.FAIL.value] == 1
    assert summary.verdict_counts[Verdict.UNAVAILABLE.value] == 0


def test_summary_names_cells_and_visibility() -> None:
    summary = compute_summary(
        [_cell("task-1"), _cell("task-2")], oracle_visibility="visible"
    )
    assert summary.cells == ["task-1", "task-2"]
    assert summary.oracle_visibility == "visible"
    assert summary.contamination is None


def test_hidden_summary_counts_and_invariant() -> None:
    cells = [
        _cell("task-1", receipt=_receipt_dict()),
        _cell(
            "task-2",
            verdict=Verdict.FAIL,
            receipt=_receipt_dict((("grader_content_in_patch", "flagged"),)),
        ),
        _cell("task-3", receipt={}),  # pre-V7 receipt: no key
        _cell("task-4", code=AttemptCode.NO_PATCH, verdict=None, receipt=None),  # refused
    ]
    summary = compute_summary(cells, oracle_visibility="hidden")
    assert summary.contamination == {
        "graded": 3,
        "flagged": 1,
        "clean": 1,
        "unmeasured": 1,
    }
    assert summary.n == 4 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 2  # denominators untouched


def test_denominators_unchanged_by_contamination_outcomes() -> None:
    verdicts = [Verdict.PASS, Verdict.FAIL, Verdict.UNAVAILABLE]
    clean = [_cell(f"t-{i}", verdict=v) for i, v in enumerate(verdicts)]
    flagged = [
        _cell(
            f"t-{i}",
            verdict=v,
            receipt=_receipt_dict((("grader_content_in_patch", "flagged"),)),
        )
        for i, v in enumerate(verdicts)
    ]
    a = compute_summary(clean, oracle_visibility="visible")
    b = compute_summary(flagged, oracle_visibility="hidden")
    assert (
        a.n,
        a.attempted,
        a.refused,
        a.code_counts,
        a.verdict_counts,
        a.timeouts,
    ) == (
        b.n,
        b.attempted,
        b.refused,
        b.code_counts,
        b.verdict_counts,
        b.timeouts,
    )


def test_summary_invariant_refuses_bad_tally() -> None:
    with pytest.raises(ValueError, match="flagged \\+ clean \\+ unmeasured"):
        Summary(
            n=1,
            attempted=1,
            refused=0,
            code_counts={c.value: 0 for c in AttemptCode},
            verdict_counts={v.value: 0 for v in Verdict},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="hidden",
            cells=["t-1"],
            contamination={"graded": 2, "flagged": 1, "clean": 1, "unmeasured": 1},
        )


def test_summary_invariant_refuses_bad_key_set() -> None:
    with pytest.raises(ValueError, match="exactly graded/flagged/clean/unmeasured"):
        Summary(
            n=1,
            attempted=1,
            refused=0,
            code_counts={c.value: 0 for c in AttemptCode},
            verdict_counts={v.value: 0 for v in Verdict},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="hidden",
            cells=["t-1"],
            contamination={"graded": 1, "flagged": 1, "clean": 0, "bogus": 0},
        )


def test_write_summary_omits_contamination_when_visible(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    write_summary(path, compute_summary([_cell("task-1")], oracle_visibility="visible"))
    data = json.loads(path.read_text())
    assert "contamination" not in data
    assert data["task"] == "format_number"
    assert data["command"] == ["fake"]
    assert data["timeout"] == 123.0


def test_write_summary_includes_contamination_when_hidden(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    summary = compute_summary(
        [_cell("task-1", receipt=_receipt_dict())], oracle_visibility="hidden"
    )
    write_summary(path, summary)
    data = json.loads(path.read_text())
    assert data["contamination"] == {
        "graded": 1,
        "flagged": 0,
        "clean": 1,
        "unmeasured": 0,
    }


def test_summary_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Summary(
            n=-1,
            attempted=0,
            refused=0,
            code_counts={c: 0 for c in _CODES},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            contamination=None,
        )
    with pytest.raises(ValueError, match="attempted \\+ refused"):
        Summary(
            n=2,
            attempted=0,
            refused=0,
            code_counts={c: 0 for c in _CODES},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            contamination=None,
        )
    with pytest.raises(ValueError, match="one key per"):
        Summary(
            n=0,
            attempted=0,
            refused=0,
            code_counts={"NOPE": 0},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            contamination=None,
        )
    with pytest.raises(ValueError, match="timeouts must equal"):
        Summary(
            n=0,
            attempted=0,
            refused=0,
            code_counts={c: 0 for c in _CODES},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=1,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            contamination=None,
        )


def test_summary_names_its_arm_from_the_records() -> None:
    cells = [
        ("t-1", make_record(AttemptCode.OK, Verdict.PASS), None),
        ("t-2", make_record(AttemptCode.OK, Verdict.FAIL), None),
    ]
    summary = compute_summary(cells, oracle_visibility="visible")
    assert summary.task == "format_number"
    assert summary.command == ["fake"]
    assert summary.timeout == 123.0


def test_compute_summary_refuses_cells_without_a_timeout() -> None:
    record = dataclasses.replace(make_record(AttemptCode.OK, Verdict.PASS), timeout=None)
    with pytest.raises(ValueError, match="timeout"):
        compute_summary([("t-1", record, None)], oracle_visibility="visible")


def test_compute_summary_refuses_empty_cells() -> None:
    with pytest.raises(ValueError, match="at least one cell"):
        compute_summary([], oracle_visibility="visible")


def test_compute_summary_refuses_mixed_identity() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, command=("other",))
    with pytest.raises(ValueError, match="command"):
        compute_summary([("t-1", a, None), ("t-2", b, None)], oracle_visibility="visible")


def test_compute_summary_refuses_mixed_task_on_a_later_cell() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, task="other-task")
    with pytest.raises(ValueError, match="mixed tasks"):
        compute_summary([("t-1", a, None), ("t-2", b, None)],
                        oracle_visibility="visible")


def test_compute_summary_refuses_a_later_cell_without_a_timeout() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, timeout=None)
    with pytest.raises(ValueError, match="has no recorded timeout"):
        compute_summary([("t-1", a, None), ("t-2", b, None)],
                        oracle_visibility="visible")


def test_compute_summary_refuses_mixed_timeouts() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, timeout=456.0)
    with pytest.raises(ValueError, match="mixed timeouts"):
        compute_summary([("t-1", a, None), ("t-2", b, None)],
                        oracle_visibility="visible")
