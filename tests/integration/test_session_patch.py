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


def test_harvest_excludes_runtime_residue_and_keeps_new_files(tmp_path: Path) -> None:
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES

    repo, base = _repo(tmp_path)
    (repo / "new_module.py").write_text("x = 1\n")
    for residue in (".pytest_cache/v/cache/lastfailed", "pkg/__pycache__/m.cpython-314.pyc", ".ruff_cache/0.1/x", ".venv/bin/python"):
        (repo / residue).parent.mkdir(parents=True, exist_ok=True)
        (repo / residue).write_text("residue\n")
    harvested = build_cumulative_patch(repo, base, exclude=RESIDUE_EXCLUDES).patch_text
    assert "new_module.py" in harvested
    assert not any(name in harvested for name in (".pytest_cache", "__pycache__", ".ruff_cache", ".venv"))
    swept = build_cumulative_patch(repo, base).patch_text
    assert ".pytest_cache" in swept  # sibling: the session path's default is unchanged


def test_harvest_excludes_the_mutators_atomic_replace_temp_file(tmp_path: Path) -> None:
    """F4: satyrn-engine's ``_atomic_replace`` (mutation.py ~623-646 at
    0a6e5df) writes each edit through ``.<name>.satyrn-<16 hex>.tmp`` before
    ``os.replace``-ing it over the real file. A harvest that lands mid-write
    must not sweep that temp file into the patch -- but an ordinary dotfile
    the model itself created is still harvested, so the exclusion must name
    this exact shape, not every dotfile."""
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES

    repo, base = _repo(tmp_path)
    (repo / "mid_write.py").write_text("x = 1\n")
    (repo / ".mid_write.py.satyrn-0123456789abcdef.tmp").write_text("partial\n")
    (repo / ".env").write_text("ORDINARY=1\n")  # an ordinary dotfile the model created
    harvested = build_cumulative_patch(repo, base, exclude=RESIDUE_EXCLUDES).patch_text
    assert "mid_write.py" in harvested
    assert ".env" in harvested
    assert ".satyrn-" not in harvested


def test_harvest_survives_a_commit_inside_the_worktree(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    (repo / "edited.txt").write_text("edited v2\n")
    (repo / "committed.txt").write_text("committed\n")
    (repo / "loose.txt").write_text("untracked\n")
    _git(repo, "add", "edited.txt", "committed.txt")
    _git(repo, "-c", "user.name=m", "-c", "user.email=m@m", "commit", "-qm", "model commit")
    assert _git(repo, "diff", "HEAD").stdout == b""  # what the old harvest saw
    capture = build_cumulative_patch(repo, base)
    assert capture.changed_paths == ("committed.txt", "edited.txt", "loose.txt")


def test_harvest_never_runs_repository_config_hooks_or_fsmonitor(tmp_path: Path) -> None:
    """F1/R10: a cell that writes fsmonitor/hooks config into the shared
    seed repository must not get the maintainer's harvest to run it."""
    repo, base = _repo(tmp_path)
    marker = tmp_path / "pwned"
    fsmonitor_script = tmp_path / "fsmonitor.sh"
    fsmonitor_script.write_text(f'#!/bin/sh\ntouch "{marker}"\nprintf "1\\n"\n')
    fsmonitor_script.chmod(0o755)
    hooks_dir = tmp_path / "evil-hooks"
    hooks_dir.mkdir()
    post_checkout = hooks_dir / "post-checkout"
    post_checkout.write_text(f'#!/bin/sh\ntouch "{marker}"\n')
    post_checkout.chmod(0o755)
    _git(repo, "config", "core.fsmonitor", str(fsmonitor_script))
    _git(repo, "config", "core.hooksPath", str(hooks_dir))
    _mutate(repo)
    capture = build_cumulative_patch(repo, base)
    assert not marker.exists(), "harvest ran repository-config hooks/fsmonitor"
    # success sibling: the harvest still reports the same changes
    assert "edited v2" in capture.patch_text
    assert capture.changed_paths == (
        "edited.txt",
        "gone.txt",
        "mode.sh",
        "untracked.txt",
    )
