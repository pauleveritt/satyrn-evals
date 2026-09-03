"""The session workspace: prepare, drive, release — sharing the V4 lifecycle."""

import os
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.workspace import (
    prepare_session_workspace,
    release_session_workspace,
)

pytestmark = pytest.mark.integration


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    base.mkdir()
    (base / "solution.py").write_text("def existing():\n    return 1\n")
    return base


def test_prepare_gives_detached_worktree_and_base_sha(tmp_path: Path) -> None:
    workspace = prepare_session_workspace(
        base=_base(tmp_path), protected_paths=(tmp_path,)
    )
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD^{commit}"],
            cwd=workspace.worktree,
            capture_output=True,
            check=True,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        ).stdout.decode().strip()
        assert head == workspace.base_sha
        assert (workspace.worktree / "solution.py").is_file()
        assert workspace.parent.exists()  # released only by release()
    finally:
        release_session_workspace(workspace)
    assert not workspace.parent.exists()


def test_release_removes_parent_even_after_session_edits(tmp_path: Path) -> None:
    workspace = prepare_session_workspace(
        base=_base(tmp_path), protected_paths=(tmp_path,)
    )
    (workspace.worktree / "solution.py").write_text(
        "def existing():\n    return 1\n\n\ndef feature_a():\n    return 'a'\n"
    )
    (workspace.worktree / "outside.txt").write_text("forbidden\n")
    release_session_workspace(workspace)
    assert not workspace.parent.exists()
