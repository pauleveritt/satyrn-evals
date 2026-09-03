"""The session-mechanics fixture's evidence floor, named fixtures, real oracle."""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASK = Path(__file__).resolve().parents[2] / "src/satyrn_evals/tasks/session-mechanics"


def _cumulative(spec, index: int) -> tuple[str, ...]:
    return tuple(
        s for step in spec.steps[: index + 1] for s in step.new_feature_selectors
    )


def test_known_good_passes_every_cumulative_milestone(tmp_path: Path) -> None:
    spec, overlay = load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK))
    features = [i for i, s in enumerate(spec.steps) if s.kind == "feature"]
    for index in features:
        selectors = _cumulative(spec, index)
        receipt = grade(
            TASK,
            TASK / "fixtures/known-good.patch",
            tmp_path / f"good-{index}.json",
            overlay=overlay,
            selectors=selectors,
            expected=selectors,
        )
        assert receipt.verdict is Verdict.PASS, (index, receipt.reason)


def test_known_broken_fails_milestones_two_and_three(tmp_path: Path) -> None:
    spec, overlay = load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK))
    for index in (1, 2):
        selectors = _cumulative(spec, index)
        receipt = grade(
            TASK,
            TASK / "fixtures/known-broken.patch",
            tmp_path / f"broken-{index}.json",
            overlay=overlay,
            selectors=selectors,
            expected=selectors,
        )
        assert receipt.verdict is Verdict.FAIL, (index, receipt.reason)


def test_known_broken_preserves_base(tmp_path: Path) -> None:
    spec = load_session_spec(TASK)
    receipt = grade(
        TASK,
        TASK / "fixtures/known-broken.patch",
        tmp_path / "pres.json",
        selectors=spec.base_preservation_selectors,
        expected=spec.base_preservation_selectors,
    )
    assert receipt.verdict is Verdict.PASS


def test_known_broken_passes_milestone_one(tmp_path: Path) -> None:
    spec, overlay = load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK))
    selectors = _cumulative(spec, 0)
    receipt = grade(
        TASK,
        TASK / "fixtures/known-broken.patch",
        tmp_path / "m1.json",
        overlay=overlay,
        selectors=selectors,
        expected=selectors,
    )
    assert receipt.verdict is Verdict.PASS
