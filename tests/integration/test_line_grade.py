"""``grade_night`` against a real, tiny, bundled integration task: a real
subprocess ``satyrn-evals grade`` call through ``grade_offline``, no fake
grader. No model runs -- the "cell" is hand-built (a night directory with
one slot and one attempt record carrying a harvested ``line.diff``), which
is cheap because ``grade_night`` only needs ``slots/*.json`` and each cell's
``attempt.json`` (via ``read_slots``/``load_attempt_record``), not a full
``launch.json`` ledger or a real launcher run.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    write_attempt_record,
)
from satyrn_evals.budget import LineCrossing
from satyrn_evals.line_grade import grade_night
from satyrn_evals.run_record import RunRecord
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import LINE_PATCH_NAME

pytestmark = pytest.mark.integration

TASKS_ROOT = Path(__file__).parent / "data" / "tasks"
KNOWN_GOOD = (TASKS_ROOT / "calc-build" / "fixtures" / "known-good.patch").read_text()
KNOWN_BROKEN = (TASKS_ROOT / "calc-build" / "fixtures" / "known-broken.patch").read_text()
SHA = "0" * 40
DIGEST = "1" * 64
AT = "2026-09-19T00:00:00+00:00"


def _record(**overrides: object) -> AttemptRecord:
    fields: dict = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="attempt recorded and graded", task="calc-build", command=("pi",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt", patch_digest=DIGEST,
        transcript_digest=DIGEST, verdict=Verdict.FAIL, receipt_path="receipt.json", timeout=3000.0,
        rung=None, contract_digest=DIGEST, workspace_base_sha=SHA,
    )
    return AttemptRecord(**(fields | overrides))


def _run_record() -> RunRecord:
    return RunRecord(
        version=1, task="calc-build", task_tree_sha256=DIGEST, arm="baseline", model="omlx/m",
        condition="cold", n=1, mode="batch", max_minutes=60, stop_rule="infrastructure only",
        decision_rule="fisher", previous_result=None, token_budget=24000, turn_budget=36,
        isolation="local", purpose="development",
    )


def _write_slot(night: Path, index: int, *, arm: str, attempt_dir: str) -> None:
    (night / "slots").mkdir(parents=True, exist_ok=True)
    (night / "slots" / f"{index:02d}.json").write_text(
        json.dumps({"slot": index, "arm": arm, "attempt_dir": attempt_dir, "code": "OK"})
    )


def test_a_crossed_line_grades_pass_against_the_real_hidden_suite(tmp_path: Path) -> None:
    night = tmp_path / "night"
    cell_dir = night / "baseline" / "calc-build-1"
    cell_dir.mkdir(parents=True)
    (cell_dir / LINE_PATCH_NAME).write_text(KNOWN_GOOD)
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=10, at=AT)
    write_attempt_record(
        cell_dir / "attempt.json",
        _record(attempt_dir="calc-build-1", line_crossed=crossing, line_patch_path=LINE_PATCH_NAME),
    )
    _write_slot(night, 0, arm="baseline", attempt_dir="calc-build-1")
    report = grade_night(night, _run_record(), tmp_path / "grades", tasks_root=TASKS_ROOT)
    assert len(report.rows) == 1
    row = report.rows[0]
    assert (row.line_verdict, row.line_source) == ("pass", "harvested")


def test_a_crossed_line_grades_fail_against_the_real_hidden_suite(tmp_path: Path) -> None:
    """Sibling to the passing case above: a known-broken patch must not pass."""
    night = tmp_path / "night"
    cell_dir = night / "baseline" / "calc-build-1"
    cell_dir.mkdir(parents=True)
    (cell_dir / LINE_PATCH_NAME).write_text(KNOWN_BROKEN)
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=10, at=AT)
    write_attempt_record(
        cell_dir / "attempt.json",
        _record(attempt_dir="calc-build-1", line_crossed=crossing, line_patch_path=LINE_PATCH_NAME),
    )
    _write_slot(night, 0, arm="baseline", attempt_dir="calc-build-1")
    report = grade_night(night, _run_record(), tmp_path / "grades", tasks_root=TASKS_ROOT)
    row = report.rows[0]
    assert row.line_verdict != "pass"
