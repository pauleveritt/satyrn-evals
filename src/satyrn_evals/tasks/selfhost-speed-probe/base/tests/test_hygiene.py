"""Answer-key hygiene: a grader file copied out of its task is found by content."""

import json
from pathlib import Path

from satyrn_evals.hygiene import overlay_copies, overlay_digests
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT


def _tasks(tmp_path: Path) -> Path:
    root = tmp_path / "tasks"
    hidden = root / "hidden"
    (hidden / "grader" / "overlay").mkdir(parents=True)
    (hidden / "grader" / "overlay" / "test_key.py").write_text("def test_key():\n    assert 42\n")
    (hidden / "grader" / "overlay" / "__init__.py").write_text("")
    (hidden / "manifest.json").write_text(json.dumps({"grader_overlay": "grader/overlay", "oracle_visibility": "hidden"}))
    visible = root / "visible"
    visible.mkdir()
    (visible / "manifest.json").write_text(json.dumps({"name": "visible"}))
    return root


def test_a_copied_overlay_file_is_found_under_any_name(tmp_path: Path) -> None:
    digests = overlay_digests(_tasks(tmp_path))
    assert list(digests.values()) == ["hidden/grader/overlay/test_key.py"]
    scratch = tmp_path / "pytest-of-someone" / "pytest-7" / "test_x0"
    scratch.mkdir(parents=True)
    (scratch / "renamed.py").write_text("def test_key():\n    assert 42\n")
    assert overlay_copies(tmp_path / "pytest-of-someone", digests) == [scratch / "renamed.py"]


def test_empty_files_unreadable_files_and_other_content_are_not_copies(tmp_path: Path) -> None:
    digests = overlay_digests(_tasks(tmp_path))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "__init__.py").write_text("")
    (scratch / "other.py").write_text("def test_key():\n    assert 41\n")
    locked = scratch / "locked.py"
    locked.write_text("def test_key():\n    assert 42\n")
    locked.chmod(0)
    try:
        assert overlay_copies(scratch, digests) == []
    finally:
        locked.chmod(0o644)


def test_the_bundled_hidden_tasks_have_keys_to_look_for() -> None:
    assert overlay_digests(DEFAULT_TASKS_ROOT)
