"""The phased session task: provenance, structure, and prompt discipline."""

import ast
from pathlib import Path

from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.patch import within_source
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
SOURCE = (
    REPO
    / "src/satyrn_evals/tasks/agentclinic-repair-depth-3/overlay/test_acceptance.py"
)
GRADER = TASK / "grader/overlay/grader_tests"


def _functions(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text())
    return {
        node.name: ast.unparse(node)
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def test_every_extracted_check_is_verbatim() -> None:
    """Whole-file identity is impossible (the source imports models at
    load). Per-assertion identity is not, and it is what the provenance
    claim now rests on."""
    source = _functions(SOURCE)
    extracted: dict[str, str] = {}
    for module in sorted(GRADER.glob("test_phase*.py")):
        extracted |= _functions(module)
    assert len(extracted) == 13
    for name, body in extracted.items():
        assert name in source, f"{name} is not in the source suite"
        assert body == source[name], f"{name} was edited during extraction"


def test_phase_one_module_does_not_reach_models() -> None:
    """The whole reason for the extraction. If this fails, phase 1 cannot
    be graded at all -- collection imports before selection applies."""
    text = (GRADER / "test_phase1_home.py").read_text()
    assert "models" not in text
    assert "_seed" not in text


def test_phase_two_module_does_reach_models() -> None:
    """Sibling to the refusal above: the seed snapshot is not simply
    absent from the extraction, it moved to the phase that needs it. A
    split that dropped it would satisfy the row above and grade nothing."""
    text = (GRADER / "test_phase2_board.py").read_text()
    assert "_seed" in text
    assert "SEED_COMPLAINTS" in text


def test_base_ships_the_environment_and_no_application() -> None:
    present = sorted(p.name for p in (TASK / "base").rglob("*") if p.is_file())
    assert present == ["pyproject.toml", "uv.lock"]


def test_overlay_does_not_fall_inside_the_writable_scope() -> None:
    """load_overlay refuses this overlap (overlay.py:80); asserting it here
    names the reason rather than leaving a load error to explain it.

    ``within_source`` is the single shared rule the session scope
    classifier and the grader allowlist both use (patch.py:166-178). A
    hand-rolled prefix expression here could agree with itself and
    disagree with the real predicate.
    """
    manifest = load_manifest(TASK)
    overlay = load_overlay(TASK, manifest)
    assert overlay.rel_paths
    assert not any(
        within_source(rel, manifest.source_paths) for rel in overlay.rel_paths
    )


def test_the_overlay_loads_and_carries_every_grader_module() -> None:
    """Success sibling: the overlay is not merely outside the writable
    scope, it is loadable and complete. An empty or missing overlay would
    satisfy the row above vacuously."""
    overlay = load_overlay(TASK, load_manifest(TASK))
    assert sorted(overlay.rel_paths) == [
        "grader_tests/_contract.py",
        "grader_tests/_seed.py",
        "grader_tests/test_phase1_home.py",
        "grader_tests/test_phase2_board.py",
        "grader_tests/test_phase3_add.py",
    ]


def test_three_feature_steps_split_the_checks_four_six_three() -> None:
    spec = load_session_spec(TASK)
    assert [len(s.new_feature_selectors) for s in spec.steps] == [4, 6, 3]
    assert all(s.kind == "feature" for s in spec.steps)


def test_all_thirteen_checks_are_claimed_exactly_once() -> None:
    spec = load_session_spec(TASK)
    claimed = [s for step in spec.steps for s in step.new_feature_selectors]
    assert len(claimed) == 13 == len(set(claimed))


def test_every_claimed_selector_names_a_check_that_exists() -> None:
    """A selector naming nothing grades nothing: the oracle would run an
    empty selection and the verdict machinery would report UNAVAILABLE
    rather than a miss. Bind the two halves here, cheaply."""
    spec = load_session_spec(TASK)
    defined = {
        f"grader_tests/{module.name}::{name}"
        for module in sorted(GRADER.glob("test_phase*.py"))
        for name in _functions(module)
    }
    claimed = {s for step in spec.steps for s in step.new_feature_selectors}
    assert claimed == defined


def test_no_prompt_discloses_a_later_phase() -> None:
    """Correction 7: a phase-1 prompt disclosing later phases made a model
    build all three at once."""
    spec = load_session_spec(TASK)
    assert "Phase 2" not in spec.steps[0].prompt
    assert "Phase 3" not in spec.steps[0].prompt
    assert "Phase 3" not in spec.steps[1].prompt


def test_no_step_declares_a_budget_ceiling() -> None:
    """The first run reports raw counts. A ceiling here would be a
    judgment wearing a measurement's clothes."""
    spec = load_session_spec(TASK)
    assert all(
        getattr(step, "turn_budget", None) is None for step in spec.steps
    )
