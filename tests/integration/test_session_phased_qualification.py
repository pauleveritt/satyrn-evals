"""Qualifying agentclinic-session-phased: the witnesses are graded, not read.

Every row here applies a witness patch over ``base/``, materializes the
grader-only modules, and runs the real oracle over the cumulative hidden
selection for a checkpoint. Nothing asserts a fixture's contents.

Checkpoint 1 is the load-bearing row. That workspace has no data module at
all, so it grades only if the phase-1 checks are independently collectable
-- which is the entire reason the depth-3 acceptance module was split.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.cli import main
from satyrn_evals.contamination import ContaminationOutcome, scan_patch
from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import OverlaySpec, load_overlay
from satyrn_evals.receipt import Receipt
from satyrn_evals.session_manifest import load_session_spec

pytestmark = pytest.mark.integration

TASK = (
    Path(__file__).resolve().parents[2]
    / "src/satyrn_evals/tasks/agentclinic-session-phased"
)

type Checkpoint = int


def _overlay() -> OverlaySpec:
    return load_overlay(TASK, load_manifest(TASK))


def _cumulative(checkpoint: Checkpoint) -> tuple[str, ...]:
    """The hidden selection in force at ``checkpoint`` (1-based)."""
    spec = load_session_spec(TASK)
    return tuple(
        selector
        for step in spec.steps[:checkpoint]
        for selector in step.new_feature_selectors
    )


def _receipt(
    tmp_path: Path, witness: str, checkpoint: Checkpoint
) -> Receipt:
    selectors = _cumulative(checkpoint)
    return grade(
        TASK,
        TASK / "fixtures" / f"{witness}.patch",
        tmp_path / f"{witness}-{checkpoint}.json",
        overlay=_overlay(),
        selectors=selectors,
        expected=selectors,
    )


def _graded_counts(
    tmp_path: Path, witness: str, checkpoint: Checkpoint
) -> tuple[int, int]:
    """(checks that passed, checks that ran) for one witness at one checkpoint."""
    receipt = _receipt(tmp_path, witness, checkpoint)
    assert receipt.evidence is not None, receipt.reason
    outcomes = receipt.evidence["outcomes"]
    passed = sum(1 for outcome in outcomes.values() if outcome == "passed")
    return passed, len(outcomes)


def _failed_check_names(
    tmp_path: Path, witness: str, checkpoint: Checkpoint
) -> set[str]:
    """The check names that did not pass, without their module prefix."""
    receipt = _receipt(tmp_path, witness, checkpoint)
    assert receipt.evidence is not None, receipt.reason
    return {
        node_id.split("::", 1)[-1]
        for node_id, outcome in receipt.evidence["outcomes"].items()
        if outcome != "passed"
    }


def _contamination(witness: str) -> ContaminationOutcome:
    base = TASK / "base"
    visible = [
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(base.rglob("*"))
        if path.is_file()
    ]
    patch_text = (TASK / "fixtures" / f"{witness}.patch").read_text()
    return scan_patch(patch_text, _overlay(), visible_texts=visible).outcome


def test_known_good_passes_cumulatively_at_every_checkpoint(tmp_path: Path) -> None:
    """4 at checkpoint 1, 10 at checkpoint 2, 13 at checkpoint 3.

    Checkpoint 1 is the load-bearing one: it has no data module, so it also
    proves the phase-1 module is independently collectable.
    """
    assert _graded_counts(tmp_path, "checkpoint-1", 1) == (4, 4)
    assert _graded_counts(tmp_path, "checkpoint-2", 2) == (10, 10)
    assert _graded_counts(tmp_path, "checkpoint-3", 3) == (13, 13)


def test_known_broken_fails_a_named_check_and_stays_failing(tmp_path: Path) -> None:
    """A witness that fails *something* is not a witness. Name it, and
    check it is not silently repaired by a later checkpoint."""
    at_two = _failed_check_names(tmp_path, "known-broken", 2)
    assert at_two == {"test_complaint_model_contract_is_preserved"}
    at_three = _failed_check_names(tmp_path, "known-broken", 3)
    assert "test_complaint_model_contract_is_preserved" in at_three


def test_a_later_checkpoint_can_regress_an_earlier_phase(tmp_path: Path) -> None:
    """The cross-phase claim, tested rather than assumed: a phase-1 check
    that passed at checkpoint 1 fails on a checkpoint-3 tree."""
    assert "test_home_html_element_declares_english_language" in _failed_check_names(
        tmp_path, "regression", 3
    )


def test_prompt_faithful_passes_every_check(tmp_path: Path) -> None:
    """The fairness gate. A failure means the prompt under-specifies --
    fix the prompt, never the checks."""
    assert _graded_counts(tmp_path, "prompt-faithful", 3) == (13, 13)


def test_prompt_faithful_scans_clean() -> None:
    assert _contamination("prompt-faithful") == "clean"


def test_the_contaminated_witness_is_flagged() -> None:
    """The positive half. A scanner that never fires would pass the
    clean-side test on its own."""
    assert _contamination("contaminated") == "flagged"


def test_bundled_known_good_patch_is_accepted_by_the_bare_grade_path(
    tmp_path: Path,
) -> None:
    """The bare ``grade`` path narrows to ``manifest.expected_test_ids``
    (grade.py:147-151), unlike the qualification rows above, which pass an
    explicit cumulative selection. F2: this task's declared fixture must
    also pass through that narrower path, or the convention stated at
    ``tests/integration/test_bundled.py:1-5,33-40`` is inverted."""
    receipt = tmp_path / "known-good.json"
    code = main(
        [
            "grade",
            "agentclinic-session-phased",
            str(TASK / "fixtures" / "known-good.patch"),
            "--receipt",
            str(receipt),
        ]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "pass"


def test_bundled_known_broken_patch_is_rejected_by_the_bare_grade_path(
    tmp_path: Path,
) -> None:
    """Sibling to the row above: the declared ``known_broken`` fixture must
    fail through the same narrow, bare path."""
    receipt = tmp_path / "known-broken.json"
    code = main(
        [
            "grade",
            "agentclinic-session-phased",
            str(TASK / "fixtures" / "known-broken.patch"),
            "--receipt",
            str(receipt),
        ]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "fail"
