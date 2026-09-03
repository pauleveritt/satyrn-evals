"""The session-mechanics fixture's declared shape (default tier)."""

from pathlib import Path

from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session_manifest import load_session_spec

TASK = Path(__file__).resolve().parents[1] / "src/satyrn_evals/tasks/session-mechanics"


def test_fixture_manifest_shape() -> None:
    manifest = load_manifest(TASK)
    assert manifest.grader_overlay == "grader/overlay"
    assert manifest.engine_contract is None
    assert manifest.source_paths == ("src/textkit/__init__.py",)


def test_fixture_session_shape() -> None:
    spec = load_session_spec(TASK)
    assert [s.kind for s in spec.steps] == ["feature", "feature", "feature", "review"]
    assert spec.base_preservation_selectors


def test_fixture_overlay_is_one_module_per_milestone() -> None:
    overlay = load_overlay(TASK, load_manifest(TASK))
    assert overlay.rel_paths == (
        "tests/test_pluralize.py",
        "tests/test_slugify.py",
        "tests/test_truncate.py",
    )
