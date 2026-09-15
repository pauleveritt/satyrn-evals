"""Cumulative patch capture against a real Git worktree."""

import os
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.session_patch import build_cumulative_patch

pytestmark = pytest.mark.integration


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
    )


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "wt"
    repo.mkdir()
    (repo / "kept.txt").write_text("kept v1\n")
    (repo / "edited.txt").write_text("edited v1\n")
    (repo / "mode.sh").write_text("#!/bin/sh\n")
    (repo / "mode.sh").chmod(0o644)
    (repo / "gone.txt").write_text("delete me\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    head = _git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    return repo, head


def _mutate(repo: Path) -> None:
    (repo / "edited.txt").write_text("edited v2\n")
    (repo / "untracked.txt").write_text("brand new\n")
    (repo / "gone.txt").unlink()
    (repo / "mode.sh").chmod(0o755)


def test_capture_includes_every_change_class(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _mutate(repo)
    capture = build_cumulative_patch(repo, base)
    assert "edited v2" in capture.patch_text
    assert "new file mode" in capture.patch_text and "untracked.txt" in capture.patch_text
    assert "deleted file mode" in capture.patch_text and "gone.txt" in capture.patch_text
    assert "old mode" in capture.patch_text and "new mode" in capture.patch_text
    assert capture.changed_paths == (
        "edited.txt",
        "gone.txt",
        "mode.sh",
        "untracked.txt",
    )


def test_capture_is_idempotent_and_leaves_the_real_index_alone(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _mutate(repo)
    first = build_cumulative_patch(repo, base)
    second = build_cumulative_patch(repo, base)
    assert first == second
    status = _git(repo, "status", "--porcelain", "--untracked-files=all")
    lines = status.stdout.decode().splitlines()
    assert any(line.startswith("?? ") for line in lines)  # still untracked, not added
    assert not any(line.startswith("A ") for line in lines)


def test_capture_of_an_unchanged_tree_is_empty_but_present(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    capture = build_cumulative_patch(repo, base)
    assert capture.patch_text == ""
    assert capture.changed_paths == ()
    assert capture.status_lines == ()


def test_capture_reports_renames_as_delete_plus_add(tmp_path: Path) -> None:
    """The alt-index view never shows R/C: base-seeded index, so a rename
    in the worktree is a delete plus an untracked file — both captured."""
    repo, base = _repo(tmp_path)
    _git(repo, "mv", "kept.txt", "renamed.txt")
    capture = build_cumulative_patch(repo, base)
    assert {"renamed.txt", "kept.txt"} <= set(capture.changed_paths)
    assert any(line.startswith("D ") for line in capture.status_lines)
    assert any(line.startswith(" A") for line in capture.status_lines)
