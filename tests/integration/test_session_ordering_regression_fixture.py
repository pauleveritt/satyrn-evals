"""The session-ordering-regression fixture's evidence floor, real oracle.

The witness test beside this one drives `SessionGrader` over the three
checkpoint patches. This file grades the two NAMED fixtures directly, the way
`test_session_mechanics_fixture.py` does for the older task, so the task's
floor does not depend on the session grader being correct.

The pair that matters is the last two rows: `known-broken` must fail the
feature axis while leaving base preservation intact. Without that, a single
signal could be wearing two names and the two axes would not be shown to move
independently.
"""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASK = (
    Path(__file__).resolve().parents[2]
    / "src/satyrn_evals/tasks/session-ordering-regression"
)


def _cumulative(spec, index: int) -> tuple[str, ...]:
    return tuple(
        s for step in spec.steps[: index + 1] for s in step.new_feature_selectors
    )


def _feature(tmp_path: Path, patch: str, index: int, name: str):
    spec, overlay = load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK))
    selectors = _cumulative(spec, index)
    return grade(
        TASK,
        TASK / "fixtures" / patch,
        tmp_path / f"{name}.json",
        overlay=overlay,
        selectors=selectors,
        expected=selectors,
    )


def _preservation(tmp_path: Path, patch: str, name: str):
    spec = load_session_spec(TASK)
    return grade(
        TASK,
        TASK / "fixtures" / patch,
        tmp_path / f"{name}.json",
        selectors=spec.base_preservation_selectors,
        expected=spec.base_preservation_selectors,
    )


def test_known_good_passes_every_cumulative_milestone(tmp_path: Path) -> None:
    spec = load_session_spec(TASK)
    for index, step in enumerate(spec.steps):
        if step.kind != "feature":
            continue
        receipt = _feature(tmp_path, "known-good.patch", index, f"good-{index}")
        assert receipt.verdict is Verdict.PASS, (index, receipt.reason)


def test_known_good_preserves_base(tmp_path: Path) -> None:
    assert _preservation(tmp_path, "known-good.patch", "good-pres").verdict is (
        Verdict.PASS
    )


def test_known_broken_fails_the_feature_axis(tmp_path: Path) -> None:
    """A plausible wrong repair: the features do not all work together."""
    receipt = _feature(tmp_path, "known-broken.patch", 1, "broken-1")
    assert receipt.verdict is Verdict.FAIL, receipt.reason


def test_known_broken_still_preserves_base(tmp_path: Path) -> None:
    """The discriminating half: the two axes move independently.

    `known-broken` fails the feature axis while base behaviour survives, so a
    feature failure cannot be mistaken for a preservation failure, or the
    reverse.
    """
    assert _preservation(tmp_path, "known-broken.patch", "broken-pres").verdict is (
        Verdict.PASS
    )
