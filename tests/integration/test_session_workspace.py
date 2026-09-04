"""The session workspace: prepare, drive, release — sharing the V4 lifecycle."""

import os
import shutil
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


def test_prepare_refuses_a_base_with_git_metadata(tmp_path: Path) -> None:
    from satyrn_evals.workspace import WorkspacePrepareError

    base = _base(tmp_path)
    (base / ".git").mkdir()
    with pytest.raises(WorkspacePrepareError):
        prepare_session_workspace(base=base, protected_paths=(tmp_path,))


def test_release_failure_names_the_retained_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from satyrn_evals import workspace as workspace_module
    from satyrn_evals.workspace import WorkspaceReleaseError

    workspace = prepare_session_workspace(
        base=_base(tmp_path), protected_paths=(tmp_path,)
    )
    (workspace.worktree / "solution.py").write_text("x = 1\n")

    def failing_cleanup(state: object, environment: object) -> None:
        raise workspace_module._CleanupError("unconfirmed removal")

    monkeypatch.setattr(workspace_module, "_cleanup_worktree", failing_cleanup)
    with pytest.raises(WorkspaceReleaseError) as excinfo:
        release_session_workspace(workspace)
    assert "unconfirmed" in str(excinfo.value)
    assert excinfo.value.retained_path == str(workspace.parent)
    # the parent survives for recovery; clean it up for the test run
    shutil.rmtree(workspace.parent, ignore_errors=True)


def test_release_failure_when_the_parent_cannot_be_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals import workspace as workspace_module
    from satyrn_evals.workspace import WorkspaceReleaseError

    workspace = prepare_session_workspace(
        base=_base(tmp_path), protected_paths=(tmp_path,)
    )
    (workspace.worktree / "solution.py").write_text("x = 1\n")

    def failing_rmtree(path: object, **kw: object) -> None:
        raise OSError("parent locked by another process")

    monkeypatch.setattr(workspace_module.shutil, "rmtree", failing_rmtree)
    with pytest.raises(WorkspaceReleaseError) as excinfo:
        release_session_workspace(workspace)
    assert "cannot remove session workspace parent" in str(excinfo.value)
    assert excinfo.value.retained_path == str(workspace.parent)
    monkeypatch.undo()
    shutil.rmtree(workspace.parent, ignore_errors=True)


def test_release_skips_removal_when_cleanup_is_unsafe(tmp_path: Path) -> None:
    """process_cleanup_safe False: the parent is retained for recovery."""
    import shutil as _shutil

    workspace = prepare_session_workspace(
        base=_base(tmp_path), protected_paths=(tmp_path,)
    )
    (workspace.worktree / "solution.py").write_text("x = 1\n")
    workspace._state.process_cleanup_safe = False
    release_session_workspace(workspace)
    assert workspace.parent.exists()  # retained, not removed
    _shutil.rmtree(workspace.parent, ignore_errors=True)
