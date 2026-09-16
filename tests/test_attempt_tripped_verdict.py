"""`tripped_verdict` on a BUDGET_EXCEEDED record: the declared secondary.

Default tier: `_grade_tripped` is called directly with a fake grader, and the
record shapes are built by hand. Design section 3.2's two fixtures are the two
directions -- a tripped worktree holding a passing state, and one with no patch.
"""

from pathlib import Path

import pytest

from satyrn_evals.attempt import TRIPPED_RECEIPT_NAME, _grade_tripped
from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict

SHA = "0" * 40
DIGEST = "1" * 64


def _record(**overrides: object) -> AttemptRecord:
    fields: dict = dict(
        version=1, outcome=AttemptOutcome.REFUSED, code=AttemptCode.BUDGET_EXCEEDED,
        message="attempt command spent 48001 output tokens, over the budget of 48000",
        task="t", command=("pi",), command_exit=None, patch_path=None, transcript_path="transcript.txt",
        patch_digest=None, transcript_digest=DIGEST, verdict=None, receipt_path=None, timeout=3000.0,
        rung="R1", contract_digest=DIGEST, workspace_base_sha=SHA, attempt_dir="t-1",
    )
    return AttemptRecord(**(fields | overrides))


def test_a_tripped_worktree_holding_a_passing_state_grades_pass_with_verdict_still_null(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch = tmp_path / "tripped.diff"
    patch.write_text("diff --git a/src/app.py b/src/app.py\n")
    monkeypatch.setattr(
        "satyrn_evals.attempt.grade",
        lambda task_dir, patch_path, receipt_path, **kw: Receipt("t", DIGEST, Verdict.PASS, "ok", None),
    )
    verdict, name = _grade_tripped(tmp_path, tmp_path, patch, deadline=None)
    assert (verdict, name) == (Verdict.PASS, "tripped.diff")
    record = _record(tripped_verdict=verdict, tripped_patch_path=name)
    assert record.verdict is None
    write_attempt_record(tmp_path / "attempt.json", record)
    assert load_attempt_record(tmp_path / "attempt.json").tripped_verdict is Verdict.PASS


def test_a_tripped_worktree_with_no_patch_grades_unavailable(tmp_path: Path) -> None:
    verdict, name = _grade_tripped(tmp_path, tmp_path, tmp_path / "absent.diff", deadline=None)
    assert (verdict, name) == (Verdict.UNAVAILABLE, None)


def test_an_empty_tripped_patch_grades_unavailable(tmp_path: Path) -> None:
    patch = tmp_path / "tripped.diff"
    patch.write_text("   \n")
    assert _grade_tripped(tmp_path, tmp_path, patch, deadline=None) == (Verdict.UNAVAILABLE, None)


def test_a_grader_failure_is_unavailable_and_keeps_the_patch_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from satyrn_evals.errors import SatyrnError

    patch = tmp_path / "tripped.diff"
    patch.write_text("diff --git a/x b/x\n")

    def boom(*args: object, **kwargs: object) -> Receipt:
        raise SatyrnError("oracle exploded")

    monkeypatch.setattr("satyrn_evals.attempt.grade", boom)
    assert _grade_tripped(tmp_path, tmp_path, patch, deadline=None) == (Verdict.UNAVAILABLE, "tripped.diff")


def test_a_record_that_is_not_budget_exceeded_may_not_carry_a_tripped_verdict() -> None:
    with pytest.raises(ValueError, match="tripped_verdict"):
        _record(code=AttemptCode.COMMAND_TIMEOUT, tripped_verdict=Verdict.PASS, tripped_patch_path="tripped.diff")


def test_a_record_without_a_tripped_verdict_writes_the_older_field_set(tmp_path: Path) -> None:
    """Ruling 13: every committed result's cells must keep loading."""
    import json

    write_attempt_record(tmp_path / "attempt.json", _record())
    body = json.loads((tmp_path / "attempt.json").read_text())
    assert "tripped_verdict" not in body and "tripped_patch_path" not in body
    assert load_attempt_record(tmp_path / "attempt.json").tripped_verdict is None


def test_the_receipt_name_is_not_the_delivered_one() -> None:
    assert TRIPPED_RECEIPT_NAME == "tripped-receipt.json"
