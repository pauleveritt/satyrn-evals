"""Preservation is graded at EVERY checkpoint, not only the last.

Why this exists (2026-09-08). The session grader ran base-preservation
selectors against the final checkpoint alone. A base behaviour broken mid
session and repaired before the end was therefore invisible, and one broken
mid session and left broken was reported only as a final-state fact, with no
record of *when* it broke. Cumulative feature selectors already catch a later
prompt regressing an earlier prompt's feature; base preservation was the
remaining hole, and a session evaluation exists to see exactly that.

No model, no network, no subprocess: `SessionGrader._grade` is the seam, and
it is the seam these tests inject at.
"""

from pathlib import Path

from satyrn_evals.receipt import Receipt
from satyrn_evals.session_grader import PRESERVATION_INVALID, SessionGrader
from satyrn_evals.session_manifest import SessionSpec, SessionStep
from satyrn_evals.session_record import SessionCode, SessionRecord, StepRecord
from satyrn_evals.verdict import Verdict

SPEC = SessionSpec(
    steps=(
        SessionStep("add-a", "feature", "Add a.", ("t_a.py::t_one",)),
        SessionStep("add-b", "feature", "Add b.", ("t_b.py::t_one",)),
        SessionStep("repair", "feature", "Repair.", ()),
    ),
    base_preservation_selectors=("tests/t_base.py::t_keep",),
)


def _step(step_id: str, *, patch: str | None = "p.diff", violations: tuple = ()) -> StepRecord:
    return StepRecord(
        step_id=step_id,
        prompt_digest="d",
        outcome="ok",
        patch_path=patch,
        scope_violations=violations,
    )


def _record(*steps: StepRecord) -> SessionRecord:
    return SessionRecord(
        version=1,
        task="t",
        adapter_command=("adapter",),
        base_commit="b" * 40,
        code=SessionCode.COMPLETE,
        steps=steps,
    )


class _Recorder(SessionGrader):
    """Captures every grading call and answers from a scripted verdict map."""

    def __init__(self, task_dir: Path, verdicts: dict[str, Verdict]) -> None:
        super().__init__(task_dir=task_dir)
        object.__setattr__(self, "_verdicts", verdicts)
        object.__setattr__(self, "calls", [])

    def _grade(self, patch_path, receipt_path, overlay, selectors, **kwargs):  # type: ignore[override]
        kind = "preservation" if overlay is None else "feature"
        self.calls.append((kind, receipt_path.name, tuple(selectors)))
        verdict = self._verdicts.get(receipt_path.name, Verdict.PASS)
        receipt_path.write_text("{}")
        return Receipt(
            task="t",
            patch_digest="0" * 64,
            verdict=verdict,
            reason="",
            evidence={"counts": {}, "outcomes": {}},
        )


def _grade(tmp_path: Path, record: SessionRecord, verdicts: dict[str, Verdict] | None = None):
    grader = _Recorder(tmp_path, verdicts or {})
    graded = grader.grade_record(record, SPEC, overlay=object(), session_dir=tmp_path)
    return grader, graded


def test_every_checkpoint_with_a_patch_gets_a_preservation_verdict(tmp_path: Path) -> None:
    """The success direction: three checkpoints, three preservation verdicts."""
    _, graded = _grade(tmp_path, _record(_step("add-a"), _step("add-b"), _step("repair")))
    assert [s.preservation_verdict for s in graded.steps] == ["pass", "pass", "pass"]
    assert all(s.preservation_receipt_path is not None for s in graded.steps)


def test_a_mid_session_regression_is_visible_at_the_checkpoint_that_caused_it(
    tmp_path: Path,
) -> None:
    """The whole point: broken at step 2, repaired by step 3.

    Under last-checkpoint-only grading this session reported a single 'pass'
    and the regression left no trace at all.
    """
    _, graded = _grade(
        tmp_path,
        _record(_step("add-a"), _step("add-b"), _step("repair")),
        {"preservation-add-b.json": Verdict.FAIL},
    )
    assert [s.preservation_verdict for s in graded.steps] == ["pass", "fail", "pass"]


def test_preservation_runs_the_declared_base_selectors_without_the_overlay(
    tmp_path: Path,
) -> None:
    grader, _ = _grade(tmp_path, _record(_step("add-a")))
    preservation = [c for c in grader.calls if c[0] == "preservation"]
    assert len(preservation) == 1
    assert preservation[0][2] == SPEC.base_preservation_selectors


def test_a_checkpoint_without_a_patch_is_not_graded_for_preservation(
    tmp_path: Path,
) -> None:
    """Refusal sibling: no captured patch, nothing to grade, no verdict.

    The sibling success is the row above -- a step WITH a patch is graded --
    so a grader that silently stopped grading anything would fail there.
    """
    _, graded = _grade(tmp_path, _record(_step("add-a", patch=None), _step("add-b")))
    assert graded.steps[0].preservation_verdict is None
    assert graded.steps[0].preservation_receipt_path is None
    assert graded.steps[1].preservation_verdict == "pass"


def test_editing_a_protected_public_test_invalidates_that_checkpoint_only(
    tmp_path: Path,
) -> None:
    """Circularity is refused per checkpoint, and does not poison the others.

    Grading preservation against a test the model itself edited would let a
    passing receipt stand in for preserved behaviour.
    """
    _, graded = _grade(
        tmp_path,
        _record(
            _step("add-a"),
            _step("add-b", violations=("tests/t_base.py",)),
            _step("repair"),
        ),
    )
    assert graded.steps[0].preservation_verdict == "pass"
    assert graded.steps[1].preservation_verdict == PRESERVATION_INVALID
    assert graded.steps[1].preservation_receipt_path is None
    assert graded.steps[2].preservation_verdict == "pass"


def test_feature_grading_still_uses_cumulative_selectors(tmp_path: Path) -> None:
    """Unchanged behaviour, pinned here because the loop was restructured."""
    grader, _ = _grade(tmp_path, _record(_step("add-a"), _step("add-b"), _step("repair")))
    feature = [c for c in grader.calls if c[0] == "feature"]
    assert [c[2] for c in feature] == [
        ("t_a.py::t_one",),
        ("t_a.py::t_one", "t_b.py::t_one"),
        ("t_a.py::t_one", "t_b.py::t_one"),
    ]


# --- Preservation unavailability, both directions (2026-09-08) ---
#
# Added after a review mutation: returning `(step, False)` unconditionally from
# `_grade_preservation` -- i.e. never recording a verdict and never reporting
# unavailability -- passed every row above. Nothing exercised the two failure
# paths of preservation grading, so a grader that quietly stopped propagating
# them was indistinguishable from one that worked.


class _FailingPreservation(_Recorder):
    """Preservation grading raises through to a None return; features grade."""

    def _grade(self, patch_path, receipt_path, overlay, selectors, **kwargs):  # type: ignore[override]
        if overlay is None:
            self.calls.append(("preservation", receipt_path.name, tuple(selectors)))
            return None
        return super()._grade(patch_path, receipt_path, overlay, selectors, **kwargs)


def test_a_preservation_grading_failure_marks_the_session_unavailable(
    tmp_path: Path,
) -> None:
    """Refusal direction: grading that could not run must not read as a pass."""
    grader = _FailingPreservation(tmp_path, {})
    graded = grader.grade_record(
        _record(_step("add-a"), _step("add-b")), SPEC, object(), tmp_path
    )
    assert graded.code is SessionCode.GRADE_UNAVAILABLE
    assert [s.preservation_verdict for s in graded.steps] == [None, None]


def test_an_unavailable_preservation_verdict_marks_the_session_unavailable(
    tmp_path: Path,
) -> None:
    """A receipt that came back UNAVAILABLE propagates, per checkpoint."""
    _, graded = _grade(
        tmp_path,
        _record(_step("add-a"), _step("add-b")),
        {"preservation-add-a.json": Verdict.UNAVAILABLE},
    )
    assert graded.code is SessionCode.GRADE_UNAVAILABLE
    assert graded.steps[0].preservation_verdict == "unavailable"


def test_preservation_grading_that_works_leaves_the_code_alone(tmp_path: Path) -> None:
    """The sibling success: nothing failed, so nothing is marked unavailable.

    Without this row the two above are satisfied by a grader that reports
    GRADE_UNAVAILABLE unconditionally.
    """
    _, graded = _grade(tmp_path, _record(_step("add-a"), _step("add-b")))
    assert graded.code is SessionCode.COMPLETE
    assert [s.preservation_verdict for s in graded.steps] == ["pass", "pass"]
