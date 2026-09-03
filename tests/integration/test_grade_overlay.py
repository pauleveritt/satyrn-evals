"""Overlay-aware grading: the evidence floor, named fixtures, real oracle."""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASK = Path(__file__).resolve().parents[1] / "data" / "overlay-task"
SELECTORS = (
    "test_hidden.py::test_slugify_basic",
    "test_hidden.py::test_slugify_collapses_spaces",
)


def test_known_good_passes_with_overlay(tmp_path: Path) -> None:
    spec = load_overlay(TASK, load_manifest(TASK))
    receipt = grade(
        TASK,
        TASK / "fixtures" / "known-good.patch",
        tmp_path / "receipt.json",
        overlay=spec,
        selectors=SELECTORS,
        expected=SELECTORS,
    )
    assert receipt.verdict is Verdict.PASS
    assert set(receipt.evidence["executed_test_ids"]) == set(SELECTORS)


def test_known_broken_fails_with_overlay(tmp_path: Path) -> None:
    spec = load_overlay(TASK, load_manifest(TASK))
    receipt = grade(
        TASK,
        TASK / "fixtures" / "known-broken.patch",
        tmp_path / "receipt.json",
        overlay=spec,
        selectors=SELECTORS,
        expected=SELECTORS,
    )
    assert receipt.verdict is Verdict.FAIL


def test_grading_without_overlay_is_unchanged(tmp_path: Path) -> None:
    receipt = grade(
        TASK, TASK / "fixtures" / "known-good.patch", tmp_path / "receipt.json"
    )
    assert receipt.verdict is Verdict.PASS
    assert receipt.evidence["executed_test_ids"] == ["test_solution.py::test_normalize"]
