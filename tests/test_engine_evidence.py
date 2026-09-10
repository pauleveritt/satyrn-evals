"""Git-backed evidence for the engine-composed route: mutation kinds and
candidate content read from commits, never from a directory snapshot --
the isolated worktree that produced them is gone by the time this runs
(delivery.py deletes it on success; see the HP3 composition design doc).

Integration tier: every test here spawns real git.
"""

import subprocess
from pathlib import Path

import pytest

from satyrn_evals.attribution import Mutation
from satyrn_evals.engine_evidence import git_diff_mutations, git_show_content

pytestmark = pytest.mark.integration


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _make_repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "--quiet", "--initial-branch=main")
    _git(path, "config", "user.name", "Engine Evidence Test")
    _git(path, "config", "user.email", "evidence@example.invalid")
    (path / "base.txt").write_text("base\n")
    _git(path, "add", "-A")
    _git(path, "commit", "--quiet", "-m", "base")
    return path


def test_git_diff_mutations_classifies_created_and_modified(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "base.txt").write_text("changed\n")
    (repo / "new.txt").write_text("new\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "phase 1")
    candidate = _git(repo, "rev-parse", "HEAD").strip()

    mutations = git_diff_mutations(repo, base, candidate)

    assert Mutation("base.txt", "modified") in mutations
    assert Mutation("new.txt", "created") in mutations


def test_git_diff_mutations_classifies_a_real_deletion(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "base.txt").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "delete it")
    candidate = _git(repo, "rev-parse", "HEAD").strip()

    mutations = git_diff_mutations(repo, base, candidate)

    assert mutations == (Mutation("base.txt", "deleted"),)


def test_git_diff_mutations_is_empty_between_identical_commits(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    commit = _git(repo, "rev-parse", "HEAD").strip()
    assert git_diff_mutations(repo, commit, commit) == ()


def test_git_show_content_reads_a_file_at_a_commit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    commit = _git(repo, "rev-parse", "HEAD").strip()
    assert git_show_content(repo, commit, "base.txt") == "base\n"


def test_git_show_content_is_none_for_a_path_absent_at_that_commit(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    commit = _git(repo, "rev-parse", "HEAD").strip()
    assert git_show_content(repo, commit, "never-existed.txt") is None
