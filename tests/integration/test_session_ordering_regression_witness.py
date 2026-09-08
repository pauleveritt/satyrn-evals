"""The cross-prompt witness: a later request regresses an earlier one.

This is the demonstration the session evaluation exists for, run through the
REAL grader against retained checkpoint patches:

    checkpoint 1  feature pass, preservation pass   (summarize works)
    checkpoint 2  feature FAIL, preservation FAIL   (initials regresses both)
    checkpoint 3  feature pass, preservation pass   (the repair restores them)

Checkpoint 2 is the point. Its patch extracts a shared `_words` helper that
splits on a single space instead of any run of whitespace -- the kind of
refactor an agent plausibly makes while adding an unrelated function -- and
that quietly breaks both `summarize`, from step 1, and `normalize`, a base
behaviour. Under last-checkpoint-only preservation grading the whole session
reported one `pass` and this left no trace at all.

Integration tier: real patch application, real environment, real oracle.
"""

import shutil
from pathlib import Path

import pytest

from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.session_record import SessionCode, SessionRecord, StepRecord

pytestmark = pytest.mark.integration

TASK_NAME = "session-ordering-regression"
CHECKPOINTS = ("checkpoint-1", "checkpoint-2", "checkpoint-3")


def _record_over(session_dir: Path, task_dir: Path) -> SessionRecord:
    """A captured record whose steps point at the three checkpoint patches."""
    spec = load_session_spec(task_dir)
    steps = []
    for step, name in zip(spec.steps, CHECKPOINTS, strict=True):
        patch_name = f"{name}.patch"
        shutil.copy(task_dir / "fixtures" / patch_name, session_dir / patch_name)
        steps.append(
            StepRecord(
                step_id=step.id,
                prompt_digest="d" * 64,
                outcome="settled",
                patch_path=patch_name,
            )
        )
    return SessionRecord(
        version=1,
        task=TASK_NAME,
        adapter_command=("fixture",),
        base_commit="b" * 40,
        code=SessionCode.COMPLETE,
        steps=tuple(steps),
    )


def test_the_regression_is_visible_at_the_checkpoint_that_caused_it(
    tmp_path: Path,
) -> None:
    task_dir = resolve_task(TASK_NAME)
    manifest = load_manifest(task_dir)
    spec = load_session_spec(task_dir)
    graded = SessionGrader(task_dir=task_dir).grade_record(
        _record_over(tmp_path, task_dir),
        spec,
        load_overlay(task_dir, manifest),
        tmp_path,
    )

    assert [s.feature_verdict for s in graded.steps] == ["pass", "fail", "pass"]
    assert [s.preservation_verdict for s in graded.steps] == ["pass", "fail", "pass"]


def test_every_checkpoint_carries_both_receipts(tmp_path: Path) -> None:
    """Success sibling: the verdicts above are backed by written receipts.

    A grader that returned the right strings without grading anything would
    pass the row above and fail this one.
    """
    task_dir = resolve_task(TASK_NAME)
    manifest = load_manifest(task_dir)
    graded = SessionGrader(task_dir=task_dir).grade_record(
        _record_over(tmp_path, task_dir),
        load_session_spec(task_dir),
        load_overlay(task_dir, manifest),
        tmp_path,
    )
    for step in graded.steps:
        assert step.feature_receipt_path is not None, step.step_id
        assert step.preservation_receipt_path is not None, step.step_id
        assert (tmp_path / step.feature_receipt_path).is_file()
        assert (tmp_path / step.preservation_receipt_path).is_file()
