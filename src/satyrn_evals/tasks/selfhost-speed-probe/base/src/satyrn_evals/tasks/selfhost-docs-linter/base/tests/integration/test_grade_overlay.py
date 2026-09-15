"""Overlay-aware grading: the evidence floor, named fixtures, real oracle."""

import json
from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest, resolve_task
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
    assert receipt.evidence is not None
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
    assert receipt.evidence is not None
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


def _grade_auto(task_dir: Path, patch_text: str, tmp_path: Path) -> dict:
    """Bare grade on a hidden task (auto-overlay path), returning the receipt."""
    patch_path = tmp_path / "patch.diff"
    patch_path.write_text(patch_text)
    receipt_path = tmp_path / "receipt.json"
    grade(task_dir, patch_path, receipt_path)  # overlay=None -> auto-overlay
    return json.loads(receipt_path.read_text())


def test_grade_subtracts_visible_public_test_idiom(tmp_path: Path) -> None:
    """A patch re-adding the shared redirect idiom (present in the task's own
    vendored public test) grades clean on the contamination check: content in
    base/ is not evidence of having seen the hidden overlay."""
    task_dir = resolve_task("agentclinic-repair-misleading-locus")
    public = (task_dir / "base" / "tests" / "test_app.py").read_text()
    assert "follow_redirects=False" in public  # precondition: the idiom is visible
    lines = public.splitlines()
    start = next(i for i, ln in enumerate(lines) if "follow_redirects=False" in ln)
    idiom = lines[start : start + 4]  # the shared 4-line window, verbatim
    patch = (
        "--- a/tests/test_new.py\n+++ b/tests/test_new.py\n@@ -0,0 +1,4 @@\n"
        + "".join(f"+{line}\n" for line in idiom)
    )
    receipt = _grade_auto(task_dir, patch, tmp_path)
    finding = receipt["contamination"]["checks"][0]
    assert finding["check"] == "grader_content_in_patch"
    assert finding["outcome"] == "clean"
