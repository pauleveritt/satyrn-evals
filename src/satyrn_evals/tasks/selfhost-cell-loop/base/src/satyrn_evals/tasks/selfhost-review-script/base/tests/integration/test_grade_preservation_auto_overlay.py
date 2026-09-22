"""T5: preservation grading must not trigger V7's auto-overlay."""

from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

SPEC = Path(__file__).resolve().parent / "data" / "mini-session-divergent"
PRESERVATION = ("test_solution.py::test_existing_preserved",)


def test_preservation_with_auto_overlay_hijack_is_unavailable(tmp_path: Path) -> None:
    """The old call shape (default auto_overlay=True) breaks preservation.

    Auto-overlay swaps selectors to manifest.expected_test_ids (which now
    include the hidden feature test), while the verdict's expected set is
    the public preservation selector -- executed ids land outside the
    expected set, so the verdict is UNAVAILABLE. This pins the hazard the
    fix removes.
    """
    receipt = grade(
        SPEC, SPEC / "fixtures" / "known-good.patch", tmp_path / "r.json",
        overlay=None, selectors=PRESERVATION, expected=PRESERVATION,
    )
    assert receipt.verdict is Verdict.UNAVAILABLE


def test_preservation_without_auto_overlay_passes_known_good(
    tmp_path: Path,
) -> None:
    """auto_overlay=False runs the public selectors with no overlay."""
    receipt = grade(
        SPEC, SPEC / "fixtures" / "known-good.patch", tmp_path / "r.json",
        overlay=None, selectors=PRESERVATION, expected=PRESERVATION,
        auto_overlay=False,
    )
    assert receipt.verdict is Verdict.PASS
    assert receipt.contamination is None  # no overlay materialized, no scan


def test_bare_grade_still_auto_overlays_and_annotates(tmp_path: Path) -> None:
    """The default behavior -- bare grade on a hidden task -- is unchanged."""
    receipt = grade(SPEC, SPEC / "fixtures" / "known-good.patch",
                    tmp_path / "r.json")
    assert receipt.verdict is Verdict.PASS
    assert receipt.contamination is not None
    assert receipt.contamination["visibility"] == "hidden"
