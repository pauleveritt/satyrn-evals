"""Grader-overlay validation and materialization."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from satyrn_evals.errors import OverlayError
from satyrn_evals.manifest import TaskManifest, load_manifest
from satyrn_evals.overlay import OverlaySpec, load_overlay, materialize_overlay


def _make_task(
    tmp_path: Path,
    files: dict[str, bytes],
    *,
    source_paths: tuple[str, ...] = ("solution.py",),
    overlay_dir: str = "grader/overlay",
) -> Path:
    task_dir = tmp_path / "t"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "fixtures" / "known-good.patch").parent.mkdir(parents=True)
    (task_dir / "fixtures" / "known-good.patch").write_text("ok")
    for rel, content in files.items():
        target = task_dir / overlay_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t",
                "contract": "Fix it.",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["test_solution.py::test_one"],
                "source_paths": list(source_paths),
                "fixtures": {"known_good": "fixtures/known-good.patch"},
                "grader_overlay": overlay_dir,
            }
        )
    )
    return task_dir


def test_load_overlay_records_sorted_paths_and_digests(tmp_path: Path) -> None:
    task_dir = _make_task(
        tmp_path,
        {"tests/b.py": b"second\n", "tests/a.py": b"first\n"},
    )
    spec = load_overlay(task_dir, load_manifest(task_dir))
    assert spec.rel_paths == ("tests/a.py", "tests/b.py")
    assert spec.digests["tests/a.py"] == hashlib.sha256(b"first\n").hexdigest()


def test_load_overlay_refuses_symlink_under_root(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"tests/test_hidden.py": b"x = 1\n"})
    (task_dir / "grader" / "overlay" / "tests" / "link.py").symlink_to("test_hidden.py")
    with pytest.raises(OverlayError, match="symbolic link"):
        load_overlay(task_dir, load_manifest(task_dir))


def test_load_overlay_refuses_symlinked_root_component(tmp_path: Path) -> None:
    # load_manifest already refuses this shape (manifest-level gate); construct
    # the manifest directly to cover load_overlay's own TOCTOU-window check.
    task_dir = _make_task(tmp_path, {"tests/a.py": b"x = 1\n"})
    real = task_dir / "elsewhere"
    real.mkdir()
    real.joinpath("tests").mkdir()
    real.joinpath("tests/a.py").write_bytes(b"x = 1\n")
    shutil.rmtree(task_dir / "grader" / "overlay")
    (task_dir / "grader" / "overlay").symlink_to(real)
    manifest = TaskManifest(
        name="t",
        contract="Fix it.",
        oracle=("python", "-m", "pytest"),
        expected_test_ids=("test_solution.py::test_one",),
        source_paths=("solution.py",),
        fixtures={"known_good": "fixtures/known-good.patch"},
        grader_overlay="grader/overlay",
    )
    with pytest.raises(OverlayError, match="symbolic link"):
        load_overlay(task_dir, manifest)


def test_load_overlay_refuses_non_regular_file(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"tests/a.py": b"x = 1\n"})
    os.mkfifo(task_dir / "grader" / "overlay" / "tests" / "pipe")
    with pytest.raises(OverlayError, match="regular file"):
        load_overlay(task_dir, load_manifest(task_dir))


def test_load_overlay_refuses_overlap_with_source_paths(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"solution.py": b"NOWHERE\n"})
    with pytest.raises(OverlayError, match="source_paths"):
        load_overlay(task_dir, load_manifest(task_dir))


def test_load_overlay_refuses_empty_directory(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {})
    (task_dir / "grader" / "overlay").mkdir(parents=True)
    with pytest.raises(OverlayError, match="empty"):
        load_overlay(task_dir, load_manifest(task_dir))


def test_materialize_overlay_copies_files_creating_parents(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"tests/a.py": b"first\n", "x/y.py": b"deep\n"})
    spec = load_overlay(task_dir, load_manifest(task_dir))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    materialize_overlay(spec, workspace)
    assert (workspace / "tests" / "a.py").read_bytes() == b"first\n"
    assert (workspace / "x" / "y.py").read_bytes() == b"deep\n"


def test_materialize_overlay_refuses_paths_outside_workspace(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"tests/a.py": b"first\n"})
    spec = load_overlay(task_dir, load_manifest(task_dir))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    forged = OverlaySpec(
        root=spec.root,
        rel_paths=("../escape.py",),
        digests={"../escape.py": "0" * 64},
    )
    with pytest.raises(OverlayError, match="escapes"):
        materialize_overlay(forged, workspace)


def test_load_overlay_refuses_manifest_without_overlay(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"tests/a.py": b"x = 1\n"})
    manifest = TaskManifest(
        name="t",
        contract="Fix it.",
        oracle=("python", "-m", "pytest"),
        expected_test_ids=("test_solution.py::test_one",),
        source_paths=("solution.py",),
        fixtures={"known_good": "fixtures/known-good.patch"},
    )
    with pytest.raises(OverlayError, match="declares no grader_overlay"):
        load_overlay(task_dir, manifest)


def test_load_overlay_refuses_root_that_is_a_file(tmp_path: Path) -> None:
    task_dir = _make_task(tmp_path, {"tests/a.py": b"x = 1\n"})
    shutil.rmtree(task_dir / "grader" / "overlay")
    (task_dir / "grader" / "overlay").write_text("a file, not a directory")
    manifest = TaskManifest(
        name="t",
        contract="Fix it.",
        oracle=("python", "-m", "pytest"),
        expected_test_ids=("test_solution.py::test_one",),
        source_paths=("solution.py",),
        fixtures={"known_good": "fixtures/known-good.patch"},
        grader_overlay="grader/overlay",
    )
    with pytest.raises(OverlayError, match="must name a directory"):
        load_overlay(task_dir, manifest)
