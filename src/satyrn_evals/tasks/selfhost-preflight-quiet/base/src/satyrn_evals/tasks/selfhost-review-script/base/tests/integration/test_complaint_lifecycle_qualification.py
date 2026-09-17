"""Qualifying agentclinic-complaint-lifecycle: the witnesses are graded, not read.

Sibling to test_session_phased_qualification.py, extended one phase. Every
row here applies a witness patch over ``base/``, materializes the
grader-only modules, and runs the real oracle over the cumulative hidden
selection for a checkpoint. Nothing asserts a fixture's contents.

Checkpoints 1-3 reuse agentclinic-session-phased's own witnesses verbatim
(same phases, same app) -- this file proves the new phase-4 witnesses only,
plus that phases 1-3 still discriminate correctly inside the new task.
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
    / "src/satyrn_evals/tasks/agentclinic-complaint-lifecycle"
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
    """4 at checkpoint 1, 10 at checkpoint 2, 13 at checkpoint 3, 18 at
    checkpoint 4 -- phases 1-3 reused verbatim from agentclinic-session-phased,
    phase 4 new."""
    assert _graded_counts(tmp_path, "checkpoint-1", 1) == (4, 4)
    assert _graded_counts(tmp_path, "checkpoint-2", 2) == (10, 10)
    assert _graded_counts(tmp_path, "checkpoint-3", 3) == (13, 13)
    assert _graded_counts(tmp_path, "checkpoint-4", 4) == (18, 18)
    assert _graded_counts(tmp_path, "known-good", 4) == (18, 18)


def test_known_broken_fails_the_positional_construction_check(
    tmp_path: Path,
) -> None:
    """The design's own named risk, reproduced and caught: `id` declared as
    a required positional field ahead of `agent_name` breaks the existing
    phase-2 check at checkpoint 2, stays broken (not silently repaired) at
    checkpoint 3, and the new phase-4 identity check catches the same root
    cause independently at checkpoint 4. No other check is disturbed."""
    at_two = _failed_check_names(tmp_path, "known-broken", 2)
    assert at_two == {"test_complaint_model_contract_is_preserved"}

    at_three = _failed_check_names(tmp_path, "known-broken", 3)
    assert at_three == {"test_complaint_model_contract_is_preserved"}

    at_four = _failed_check_names(tmp_path, "known-broken", 4)
    assert at_four == {
        "test_complaint_model_contract_is_preserved",
        "test_complaint_identity_is_stable_and_keyword_only",
    }


def test_resolve_reordering_fails_only_its_own_check(tmp_path: Path) -> None:
    """The regression witness: resolve moves the resolved complaint to the
    end of the list. Phases 1-3 stay green; only the new ordering check
    fails, at checkpoint 4 -- proving the check actually watches ordering,
    not just presence."""
    assert _graded_counts(tmp_path, "regression", 1) == (4, 4)
    assert _graded_counts(tmp_path, "regression", 2) == (10, 10)
    assert _graded_counts(tmp_path, "regression", 3) == (13, 13)
    assert _failed_check_names(tmp_path, "regression", 4) == {
        "test_resolve_reopen_does_not_reorder_the_board"
    }


def test_prompt_faithful_passes_every_check(tmp_path: Path) -> None:
    """The fairness gate. A failure means the prompt under-specifies --
    fix the prompt, never the checks. Deliberately a different
    implementation from known-good (different id-issuing function, a
    lookup helper instead of a loop, different template structure) to show
    the requirement is satisfiable more than one way."""
    assert _graded_counts(tmp_path, "prompt-faithful", 4) == (18, 18)


def test_prompt_faithful_scans_clean() -> None:
    assert _contamination("prompt-faithful") == "clean"


def test_the_contaminated_witness_is_flagged() -> None:
    """The positive half. A scanner that never fires would pass the
    clean-side test on its own. Same trigger as the sibling task's own
    fixture: `_contract.py`'s `_has_html5_doctype` lifted verbatim."""
    assert _contamination("contaminated") == "flagged"


def test_bundled_known_good_patch_is_accepted_by_the_bare_grade_path(
    tmp_path: Path,
) -> None:
    """The bare ``grade`` path narrows to ``manifest.expected_test_ids``,
    unlike the qualification rows above, which pass an explicit cumulative
    selection. The declared fixture must also pass through that narrower
    path."""
    receipt = tmp_path / "known-good.json"
    code = main(
        [
            "grade",
            "agentclinic-complaint-lifecycle",
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
            "agentclinic-complaint-lifecycle",
            str(TASK / "fixtures" / "known-broken.patch"),
            "--receipt",
            str(receipt),
        ]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "fail"
