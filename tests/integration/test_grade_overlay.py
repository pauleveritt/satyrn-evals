"""Overlay-aware grading: the evidence floor, named fixtures, real oracle."""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay, materialize_overlay
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


def test_bare_grade_on_hidden_task_narrows_to_expected_ids(tmp_path: Path) -> None:
    """A bare grade on a hidden task auto-overlays but stays closed.

    overlay=None triggers the auto-overlay path: grade loads the overlay and
    narrows selectors to manifest.expected_test_ids, so the hidden overlay
    tests are NOT executed and only the public base node runs. The verdict
    is PASS and the receipt still carries the contamination finding with
    visibility hidden. This is V7's auto-overlay behavior, not V6's
    no-overlay path.
    """
    receipt = grade(
        TASK, TASK / "fixtures" / "known-good.patch", tmp_path / "receipt.json"
    )
    assert receipt.verdict is Verdict.PASS
    assert receipt.evidence["executed_test_ids"] == ["test_solution.py::test_normalize"]
    assert receipt.contamination is not None
    assert receipt.contamination["visibility"] == "hidden"


def test_materialized_overlay_files_are_read_only(
    tmp_path: Path, tmp_hidden_task: Path
) -> None:
    manifest = load_manifest(tmp_hidden_task)
    spec = load_overlay(tmp_hidden_task, manifest)
    work = tmp_path / "work"
    work.mkdir()
    materialize_overlay(spec, work)
    for rel in spec.rel_paths:
        assert (work / rel).stat().st_mode & 0o222 == 0
        with pytest.raises(PermissionError):
            (work / rel).write_text("overwrite")
