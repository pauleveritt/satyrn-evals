"""summarize_output/regrade_attempt: pure from-disk rebuild and re-score."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.receipt import Receipt
from satyrn_evals.rescore import regrade_attempt, summarize_output
from satyrn_evals.summary import ABORTED_NAME, SUMMARY_NAME
from satyrn_evals.verdict import Verdict

TASK = "format_number"


def record(**overrides: object) -> AttemptRecord:
    base = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="ok", task=TASK, command=("fake",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt",
        patch_digest="a" * 64, transcript_digest="b" * 64,
        verdict=Verdict.PASS, receipt_path="receipt.json",
        timeout=123.0, workspace_base_sha="c" * 40, attempt_dir="cell-1",
    )
    base.update(overrides)
    return AttemptRecord(**base)


def write_cell(
    output: Path, name: str, rec: AttemptRecord, receipt: dict | None = None
) -> None:
    """Write a complete V9 cell: record (attempt_dir == dir name) + artifacts.

    A receipt is written only when the caller passes one; summarize treats
    an attempted record that names a receipt whose file is absent as an
    operational error, so callers of this helper must keep record and
    receipt in agreement.
    """
    cell = output / name
    cell.mkdir(parents=True, exist_ok=True)
    write_attempt_record(cell / "attempt.json", replace(rec, attempt_dir=name))
    (cell / "patch.diff").write_text("diff --git a/x b/x\n")
    (cell / "transcript.txt").write_text("t\n")
    if receipt is not None:
        (cell / "receipt.json").write_text(json.dumps(receipt))


_CLEAN_RECEIPT = {"verdict": "pass", "reason": ""}


def _bundled() -> Path:
    return DEFAULT_TASKS_ROOT


def write_anchor(output: Path, *names: str) -> None:
    """A completed-run anchor: summary.json naming its cells."""
    (output / SUMMARY_NAME).write_text(json.dumps({"cells": list(names)}))


def _two_cell_run(output: Path) -> None:
    """One OK cell + one GRADE_FAILED cell, with an anchor over both."""
    write_cell(output, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(output, "format_number-2",
               record(code=AttemptCode.GRADE_FAILED, verdict=None,
                      receipt_path=None))
    write_anchor(output, "format_number-1", "format_number-2")


def test_summarize_rebuilds_counts_from_an_anchored_run(tmp_path: Path) -> None:
    out = tmp_path / "run"
    _two_cell_run(out)
    summary = summarize_output(out)
    assert summary.n == 2 and summary.attempted == 2
    assert summary.code_counts["OK"] == 1
    assert summary.code_counts["GRADE_FAILED"] == 1
    assert summary.task == TASK and summary.timeout == 123.0
    assert (out / SUMMARY_NAME).exists()
    assert json.loads((out / SUMMARY_NAME).read_text())["task"] == TASK


def test_summarize_ignores_cells_not_named_by_the_run(tmp_path: Path) -> None:
    """B2: the anchor, not the directory, is authoritative.

    A stray sibling that even carries its own attempt.json (an old partial
    run, an un-appended crash cell) must not change the rebuilt summary.
    """
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(out, "format_number-9", record())  # stray, has attempt.json
    write_anchor(out, "format_number-1")
    summary = summarize_output(out)
    assert summary.cells == ["format_number-1"]
    assert summary.n == 1 and summary.attempted == 1


def test_summarize_refuses_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="not a directory"):
        summarize_output(tmp_path / "missing", tasks_root=_bundled())


def test_summarize_refuses_a_directory_without_an_anchor(tmp_path: Path) -> None:
    """No summary.json and no abort marker: not a run output directory."""
    (tmp_path / "empty").mkdir()
    with pytest.raises(UsageError, match=SUMMARY_NAME):
        summarize_output(tmp_path / "empty", tasks_root=_bundled())


def test_summarize_refuses_an_aborted_batch(tmp_path: Path) -> None:
    """B1/B2: an aborted run has no summary.json -- summarize refuses it."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (out / ABORTED_NAME).write_text(
        json.dumps({"requested": 8, "completed": 1, "error": "OSError: boom"})
    )
    with pytest.raises(SatyrnError, match="aborted"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_an_aborted_batch_with_an_unreadable_marker(
    tmp_path: Path,
) -> None:
    """Even an unparseable aborted.json is refused, never silently rebuilt."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (out / ABORTED_NAME).write_text("{not json")
    with pytest.raises(SatyrnError, match="aborted"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_unparseable_record_and_missing_receipt(
    tmp_path: Path,
) -> None:
    out = tmp_path / "run"
    cell = out / "format_number-1"
    cell.mkdir(parents=True)
    write_anchor(out, "format_number-1")
    (cell / "attempt.json").write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        summarize_output(out, tasks_root=_bundled())
    (cell / "attempt.json").unlink()
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    (cell / "receipt.json").unlink()
    with pytest.raises(SatyrnError, match="receipt"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_an_unparseable_receipt(tmp_path: Path) -> None:
    """A receipt that exists but is corrupt is operational, not clean."""
    out = tmp_path / "run"
    cell_dir = out / "format_number-1"
    cell_dir.mkdir(parents=True)
    write_attempt_record(cell_dir / "attempt.json",
                         record(attempt_dir="format_number-1"))
    (cell_dir / "receipt.json").write_text("{not json")
    write_anchor(out, "format_number-1")
    with pytest.raises(SatyrnError, match="receipt"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_mixed_task_identity(tmp_path: Path) -> None:
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    write_cell(out, "other-task-1", record(task="other-task"),
               receipt=_CLEAN_RECEIPT)
    write_anchor(out, "format_number-1", "other-task-1")
    with pytest.raises(SatyrnError, match="mixed"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_a_moved_cell(tmp_path: Path) -> None:
    """A record whose attempt_dir disagrees with its directory is usage (2)."""
    out = tmp_path / "run"
    cell = out / "moved-1"
    cell.mkdir(parents=True)
    write_attempt_record(
        cell / "attempt.json", record(attempt_dir="format_number-1")
    )
    (cell / "receipt.json").write_text(json.dumps(_CLEAN_RECEIPT))
    write_anchor(out, "moved-1")
    with pytest.raises(UsageError, match="moved or renamed"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_a_missing_anchored_cell(tmp_path: Path) -> None:
    """A cell the run's summary names but the directory no longer holds."""
    out = tmp_path / "run"
    out.mkdir(parents=True)
    write_anchor(out, "format_number-1")
    with pytest.raises(SatyrnError, match="missing"):
        summarize_output(out, tasks_root=_bundled())


def test_summarize_refuses_an_unusable_anchor(tmp_path: Path) -> None:
    """A corrupt or cell-less summary.json is operational, never silent."""
    out = tmp_path / "run"
    out.mkdir(parents=True)
    (out / SUMMARY_NAME).write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        summarize_output(out, tasks_root=_bundled())
    (out / SUMMARY_NAME).write_text(json.dumps({"n": 0}))
    with pytest.raises(SatyrnError, match="cells"):
        summarize_output(out, tasks_root=_bundled())
    (out / SUMMARY_NAME).write_text(json.dumps({"cells": []}))
    with pytest.raises(SatyrnError, match="names no cells"):
        summarize_output(out, tasks_root=_bundled())


# --- P4b: regrade_attempt legs (default tier, grade mocked) ---


def _fake_grade(verdict: Verdict):
    """A grade double that mirrors real grade(): writes the receipt file."""

    def fake(task_dir: Path, patch_path: Path, receipt_path: Path) -> Receipt:
        receipt_path.write_text(
            json.dumps({"task": task_dir.name, "verdict": verdict.value})
        )
        return Receipt(
            task=task_dir.name,
            patch_digest="a" * 64,
            verdict=verdict,
            reason="",
            evidence=None,
        )

    return fake


def test_regrade_turns_a_grade_failed_cell_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A GRADE_FAILED cell is the reason regrade exists (success leg)."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1",
               record(code=AttemptCode.GRADE_FAILED, verdict=None,
                      receipt_path=None))
    monkeypatch.setattr(rescore_module, "grade", _fake_grade(Verdict.PASS))
    rewritten = regrade_attempt(out / "format_number-1", tasks_root=_bundled())
    assert rewritten is not None
    assert rewritten.code is AttemptCode.OK
    assert rewritten.verdict is Verdict.PASS
    assert rewritten.receipt_path == "receipt.json"
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.code is AttemptCode.OK and loaded.verdict is Verdict.PASS
    # the mock wrote the receipt exactly where the record names it
    assert (out / "format_number-1" / "receipt.json").is_file()


def test_regrade_of_a_refusal_cell_is_a_noop(tmp_path: Path) -> None:
    """A refusal code was never graded: nothing to re-score (no-op leg)."""
    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(
        code=AttemptCode.NO_PATCH, outcome=AttemptOutcome.REFUSED,
        verdict=None, receipt_path=None, patch_path=None,
        transcript_path=None, patch_digest=None, transcript_digest=None,
    ))
    assert regrade_attempt(out / "format_number-1",
                           tasks_root=_bundled()) is None


def test_regrade_rescores_an_ok_cell_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An OK cell is re-scored: the returned record carries the new verdict."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1",
               record(verdict=Verdict.FAIL, message="old"),
               receipt=_CLEAN_RECEIPT)
    monkeypatch.setattr(rescore_module, "grade", _fake_grade(Verdict.PASS))
    rewritten = regrade_attempt(out / "format_number-1",
                                tasks_root=_bundled())
    assert rewritten is not None
    assert rewritten.verdict is Verdict.PASS
    assert rewritten.message == "attempt re-graded"
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.verdict is Verdict.PASS


def test_regrade_refuses_identity_mismatch(tmp_path: Path) -> None:
    """A renamed cell must not be graded (refusal leg)."""
    cell = tmp_path / "other-1"
    cell.mkdir()
    write_attempt_record(
        cell / "attempt.json",
        replace(record(code=AttemptCode.GRADE_FAILED, verdict=None,
                       receipt_path=None), attempt_dir="format_number-1"),
    )
    with pytest.raises(UsageError, match="names"):
        regrade_attempt(cell, tasks_root=_bundled())


def test_regrade_refuses_a_non_cell_directory(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="no attempt record"):
        regrade_attempt(tmp_path / "nope", tasks_root=_bundled())


def test_regrade_refuses_an_unreadable_record(tmp_path: Path) -> None:
    """An attempt.json that exists but is corrupt is operational (3)."""
    cell = tmp_path / "format_number-1"
    cell.mkdir()
    (cell / "attempt.json").write_text("{not json")
    with pytest.raises(SatyrnError, match="cannot read"):
        regrade_attempt(cell, tasks_root=_bundled())


def test_regrade_unavailable_verdict_raises_operational(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UNAVAILABLE after a successful regrade is exit-3 class (spec §6)."""
    from satyrn_evals import rescore as rescore_module

    out = tmp_path / "run"
    write_cell(out, "format_number-1", record(), receipt=_CLEAN_RECEIPT)
    monkeypatch.setattr(rescore_module, "grade",
                        _fake_grade(Verdict.UNAVAILABLE))
    with pytest.raises(SatyrnError, match="unavailable"):
        regrade_attempt(out / "format_number-1", tasks_root=_bundled())
    # the record was still rewritten and consistent before the raise
    loaded = load_attempt_record(out / "format_number-1" / "attempt.json")
    assert loaded.code is AttemptCode.OK
    assert loaded.verdict is Verdict.UNAVAILABLE
