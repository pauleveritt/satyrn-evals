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


@pytest.fixture
def overlay_task(tmp_path: Path) -> Path:
    return _make_task(
        tmp_path,
        {"tests/test_x.py": b"def test_x():\n    pass\n"},
    )


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
                "oracle_visibility": "hidden",
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
        texts={"../escape.py": ""},
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


def test_materialize_verifies_the_recorded_digests(tmp_path: Path) -> None:
    """Overlay digests are load-bearing: a file that changes between
    load_overlay and materialize_overlay is refused, not silently graded."""
    task_dir = _make_task(tmp_path, {"tests/a.py": b"first\n"})
    spec = load_overlay(task_dir, load_manifest(task_dir))
    (task_dir / "grader" / "overlay" / "tests" / "a.py").write_bytes(b"tampered\n")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    with pytest.raises(OverlayError, match="digest mismatch"):
        materialize_overlay(spec, workspace)
    # the honest copy still materializes cleanly (the sibling direction)
    fresh = load_overlay(task_dir, load_manifest(task_dir))
    materialize_overlay(fresh, workspace)
    assert (workspace / "tests" / "a.py").read_bytes() == b"tampered\n"


def test_overlay_spec_carries_texts(overlay_task: Path) -> None:
    manifest = load_manifest(overlay_task)
    spec = load_overlay(overlay_task, manifest)
    assert set(spec.texts) == set(spec.rel_paths)
    assert "def test_x" in spec.texts[spec.rel_paths[0]]


def test_overlay_spec_refuses_non_utf8_file(overlay_task: Path) -> None:
    bad = overlay_task / "grader" / "overlay" / "tests" / "bad.py"
    bad.write_bytes(b"\xff\xfe not utf-8")
    manifest = load_manifest(overlay_task)
    with pytest.raises(OverlayError, match="must be UTF-8 text"):
        load_overlay(overlay_task, manifest)


def test_load_overlay_accepts_writable_checkout_modes(overlay_task: Path) -> None:
    """T6 correction: group/other-writable stored files are no longer refused.

    Supersedes the V7 stored-file refusal (V9 spec §4 T6, V7 spec §5
    note): git stores regular files as 100644/100755, so the on-disk mode
    at load is a property of the checkout umask (002 on Debian/Ubuntu
    yields 664/666 for a clean store), not of the store. Materialization
    still chmods 0o444, and the genuine stored-file refusals (symlink,
    non-regular, non-UTF-8, source-path overlap) still fire.
    """
    bad = overlay_task / "grader" / "overlay" / "tests" / "test_x.py"
    bad.chmod(0o666)
    assert load_overlay(overlay_task, load_manifest(overlay_task)).rel_paths


def test_overlay_load_accepts_umask_002_checkout_modes(overlay_task: Path) -> None:
    """T6: a 664 tree (Debian/Ubuntu checkout) loads and digests."""
    for path in (overlay_task / "grader" / "overlay").rglob("*"):
        if path.is_file():
            path.chmod(0o664)
    spec = load_overlay(overlay_task, load_manifest(overlay_task))
    assert spec.rel_paths  # loaded, digests recorded


def test_overlay_materialization_still_read_only(
    overlay_task: Path, tmp_path: Path,
) -> None:
    """The 0o444 materialization is unchanged: defense in depth remains."""
    spec = load_overlay(overlay_task, load_manifest(overlay_task))
    materialize_overlay(spec, tmp_path / "work")
    for rel in spec.rel_paths:
        mode = (tmp_path / "work" / rel).stat().st_mode & 0o777
        assert mode == 0o444


def test_load_overlay_accepts_git_default_modes(overlay_task: Path) -> None:
    (overlay_task / "grader" / "overlay" / "tests" / "test_x.py").chmod(0o644)
    manifest = load_manifest(overlay_task)
    assert load_overlay(overlay_task, manifest).rel_paths  # does not raise
