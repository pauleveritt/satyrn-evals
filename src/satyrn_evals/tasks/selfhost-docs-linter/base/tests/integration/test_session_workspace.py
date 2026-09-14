"""The session workspace: prepare, drive, release — sharing the V4 lifecycle."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from satyrn_evals.errors import OverlayError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.overlay import assert_overlay_absent, load_overlay
from satyrn_evals.workspace import (
    prepare_session_workspace,
    prepare_workspace,
    release_session_workspace,
    release_workspace,
    run_prepared_command,
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
        head = (
            subprocess.run(
                ["git", "rev-parse", "HEAD^{commit}"],
                cwd=workspace.worktree,
                capture_output=True,
                check=True,
                env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
            )
            .stdout.decode()
            .strip()
        )
        assert head == workspace.base_sha
        assert (workspace.worktree / "solution.py").is_file()
        assert workspace.parent.exists()  # released only by release()
    finally:
        release_session_workspace(workspace)
    assert not workspace.parent.exists()


def test_prepared_workspace_preserves_artifacts_until_explicit_release(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifact.txt"
    workspace = prepare_workspace(
        base=_base(tmp_path),
        protected_paths=(tmp_path,),
        environment={
            **os.environ,
            "GIT_DIR": "/must-not-reach-workspace",
            "SATYRN_TEST_ARTIFACT": str(artifact),
        },
    )
    try:
        assert "GIT_DIR" not in workspace._environment
        assert workspace._environment["SATYRN_TEST_ARTIFACT"] == str(artifact)
        result = run_prepared_command(
            workspace,
            command=[
                sys.executable,
                "-c",
                "from pathlib import Path; import os; Path(os.environ['SATYRN_TEST_ARTIFACT']).write_text('kept')",
            ],
            timeout=5.0,
        )
        assert result.code.value == "OK"
        assert artifact.read_text() == "kept"
        assert workspace.parent.exists()
    finally:
        release_workspace(workspace)
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


def test_neutral_release_returns_the_parent_when_cleanup_is_unsafe(
    tmp_path: Path,
) -> None:
    workspace = prepare_workspace(
        base=_base(tmp_path), protected_paths=(tmp_path,), environment=os.environ
    )
    workspace._state.process_cleanup_safe = False
    assert release_workspace(workspace) == str(workspace.parent)
    assert workspace.parent.exists()
    assert workspace.worktree.exists()
    shutil.rmtree(workspace.parent, ignore_errors=True)


def test_hidden_overlay_absent_from_executor_worktree() -> None:
    """A hidden task's reconstructed worktree must not carry overlay content."""
    task_dir = DEFAULT_TASKS_ROOT / "agentclinic-complaint-lifecycle"
    manifest = load_manifest(task_dir)
    spec = load_overlay(task_dir, manifest)
    workspace = prepare_session_workspace(
        base=task_dir / "base",
        protected_paths=(task_dir,),
        overlay=spec,
    )
    try:
        assert_overlay_absent(workspace.worktree, spec)  # does not raise
    finally:
        release_session_workspace(workspace)


def test_overlay_content_in_base_refuses_the_build(tmp_path: Path) -> None:
    """An overlay file's bytes copied into base are the authoring defect caught."""
    task_dir = tmp_path / "agentclinic-complaint-lifecycle"
    shutil.copytree(DEFAULT_TASKS_ROOT / "agentclinic-complaint-lifecycle", task_dir)
    # an overlay file's bytes inside base are exactly the authoring defect
    # the invariant catches (digest hit, whatever the path is named)
    shutil.copy(
        task_dir / "grader" / "overlay" / "grader_tests" / "test_phase1_home.py",
        task_dir / "base" / "test_phase1_home.py",
    )
    manifest = load_manifest(task_dir)
    spec = load_overlay(task_dir, manifest)
    # prepare_session_workspace propagates the OverlayError directly (exit-2
    # authoring signal) after removing its fresh parent; not WorkspacePrepareError.
    with pytest.raises(OverlayError, match="overlay"):
        prepare_session_workspace(
            base=task_dir / "base", protected_paths=(task_dir,), overlay=spec
        )
