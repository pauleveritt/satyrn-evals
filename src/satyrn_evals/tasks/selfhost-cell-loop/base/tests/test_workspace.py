import hashlib
import os
from pathlib import Path

import pytest

import satyrn_evals.workspace as workspace_module
from satyrn_evals.workspace import (
    PreparedWorkspace,
    Registration,
    TreeEntry,
    TreeKind,
    WorkspaceCode,
    WorkspacePrepareError,
    WorkspaceResult,
    clean_environment,
    run_prepared_command,
    run_workspace,
    snapshot_tree,
)


def test_clean_environment_removes_git_routing_and_sets_safety() -> None:
    original = {
        "PATH": "/bin",
        "GIT_DIR": "/caller/.git",
        "GIT_WORK_TREE": "/caller",
        "GIT_NAMESPACE": "ns",
        "GIT_TERMINAL_PROMPT": "1",
    }

    cleaned = clean_environment(original, {"GIT_DIR", "GIT_WORK_TREE"})

    assert cleaned == {
        "PATH": "/bin",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_GRAFT_FILE": os.devnull,
    }
    assert original["GIT_DIR"] == "/caller/.git"


def test_snapshot_tree_preserves_regular_executable_and_symlink(tmp_path: Path) -> None:
    (tmp_path / "plain.txt").write_bytes(b"plain\r\n")
    executable = tmp_path / "run"
    executable.write_bytes(b"#!/bin/sh\n")
    executable.chmod(0o755)
    (tmp_path / "link").symlink_to("plain.txt")
    (tmp_path / "empty").mkdir()
    (tmp_path / ".git").write_text("gitdir: elsewhere\n")

    entries = snapshot_tree(tmp_path)

    assert entries == (
        TreeEntry("link", TreeKind.SYMLINK, "plain.txt"),
        TreeEntry(
            "plain.txt",
            TreeKind.REGULAR,
            hashlib.sha256(b"plain\r\n").hexdigest(),
        ),
        TreeEntry(
            "run",
            TreeKind.EXECUTABLE,
            hashlib.sha256(b"#!/bin/sh\n").hexdigest(),
        ),
    )


def test_snapshot_tree_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="task base is not a directory"):
        snapshot_tree(tmp_path / "missing")


@pytest.mark.skipif(os.name != "posix", reason="FIFO fixture is POSIX-only")
def test_snapshot_tree_rejects_special_file(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(Exception, match="unsupported file type: pipe"):
        snapshot_tree(tmp_path)


def test_registration_guard_is_conservative_before_add(tmp_path: Path) -> None:
    state = workspace_module._WorkspaceState(
        tmp_path, tmp_path / "seed", tmp_path / "worktree"
    )
    assert state.registration is Registration.ABSENT
    state.begin_add()
    assert state.registration is Registration.MAY_EXIST
    state.observe_registration(True)
    assert state.registration is Registration.PRESENT
    state.observe_registration(None)
    assert state.registration is Registration.MAY_EXIST
    state.observe_registration(False)
    assert state.registration is Registration.ABSENT


def test_registration_rejects_invalid_transitions(tmp_path: Path) -> None:
    state = workspace_module._WorkspaceState(
        tmp_path, tmp_path / "seed", tmp_path / "worktree"
    )
    state.begin_add()
    with pytest.raises(AssertionError, match="non-absent"):
        state.begin_add()
    with pytest.raises(AssertionError, match="unexpected registration"):
        state.observe_registration("present")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("code", "command_exit", "base_sha", "retained_path"),
    [
        (WorkspaceCode.OK, 0, "a" * 40, None),
        (WorkspaceCode.WORKSPACE_FAILED, None, None, None),
        (WorkspaceCode.COMMAND_UNAVAILABLE, None, "b" * 40, None),
        (WorkspaceCode.COMMAND_TIMEOUT, None, "c" * 64, None),
        (WorkspaceCode.CLEANUP_FAILED, None, None, "/tmp/retained"),
        (WorkspaceCode.CLEANUP_FAILED, 7, "d" * 40, "/tmp/retained"),
    ],
)
def test_workspace_result_valid_matrix(
    code: WorkspaceCode,
    command_exit: int | None,
    base_sha: str | None,
    retained_path: str | None,
) -> None:
    result = WorkspaceResult(code, "result", command_exit, base_sha, retained_path)
    assert result.code is code


def test_workspace_policy_is_complete() -> None:
    assert set(workspace_module._WORKSPACE_POLICIES) == set(WorkspaceCode)


def test_workspace_result_invariants() -> None:
    with pytest.raises(ValueError, match="requires command_exit"):
        WorkspaceResult(WorkspaceCode.OK, "ok", None, "a" * 40)
    with pytest.raises(ValueError, match="requires retained_path"):
        WorkspaceResult(WorkspaceCode.CLEANUP_FAILED, "failed", None, None)
    with pytest.raises(ValueError, match="only CLEANUP_FAILED"):
        WorkspaceResult(
            WorkspaceCode.WORKSPACE_FAILED,
            "failed",
            None,
            None,
            "/tmp/retained",
        )
    with pytest.raises(ValueError, match="WorkspaceCode"):
        WorkspaceResult("NOT_A_CODE", "failed", None, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty string"):
        WorkspaceResult(WorkspaceCode.WORKSPACE_FAILED, "", None, None)
    with pytest.raises(ValueError, match="integer or null"):
        WorkspaceResult(WorkspaceCode.WORKSPACE_FAILED, "failed", True, None)
    with pytest.raises(ValueError, match="base_sha"):
        WorkspaceResult(WorkspaceCode.WORKSPACE_FAILED, "failed", None, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Git object ID"):
        WorkspaceResult(WorkspaceCode.WORKSPACE_FAILED, "failed", None, "A" * 40)
    with pytest.raises(ValueError, match="Git object ID"):
        WorkspaceResult(WorkspaceCode.WORKSPACE_FAILED, "failed", None, "g" * 40)


@pytest.mark.parametrize(
    "code",
    [
        WorkspaceCode.WORKSPACE_FAILED,
        WorkspaceCode.COMMAND_UNAVAILABLE,
        WorkspaceCode.COMMAND_TIMEOUT,
    ],
)
def test_non_cleanup_workspace_refusal_rejects_command_exit(
    code: WorkspaceCode,
) -> None:
    with pytest.raises(ValueError, match="null command_exit"):
        WorkspaceResult(code, "failed", 7, "a" * 40)


@pytest.mark.parametrize(
    "code",
    [
        WorkspaceCode.OK,
        WorkspaceCode.COMMAND_UNAVAILABLE,
        WorkspaceCode.COMMAND_TIMEOUT,
    ],
)
def test_post_prepare_workspace_result_requires_base_sha(code: WorkspaceCode) -> None:
    command_exit = 0 if code is WorkspaceCode.OK else None
    with pytest.raises(ValueError, match="requires base_sha"):
        WorkspaceResult(code, "result", command_exit, None)


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("nan"), float("inf")])
def test_run_workspace_rejects_bad_timeout(tmp_path: Path, timeout: float) -> None:
    with pytest.raises(ValueError, match="finite number greater than zero"):
        run_workspace(
            base=tmp_path,
            protected_paths=(),
            command=("unused",),
            environment={},
            timeout=timeout,
        )


def test_run_workspace_rejects_empty_command(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="command is empty"):
        run_workspace(
            base=tmp_path,
            protected_paths=(),
            command=(),
            environment={},
        )


@pytest.mark.parametrize("grace", [0.0, -1.0, float("nan"), float("inf")])
def test_run_workspace_rejects_bad_teardown_grace(tmp_path: Path, grace: float) -> None:
    with pytest.raises(ValueError, match="finite number greater than zero"):
        run_workspace(
            base=tmp_path,
            protected_paths=(),
            command=("unused",),
            environment={},
            teardown_grace=grace,
        )


@pytest.mark.parametrize(
    ("command", "timeout", "grace", "message"),
    [
        ((), 1.0, 1.0, "command is empty"),
        (("cmd",), 0.0, 1.0, "timeout must be"),
        (("cmd",), 1.0, 0.0, "teardown grace must be"),
    ],
)
def test_prepared_command_rejects_invalid_work_before_delegating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: tuple[str, ...],
    timeout: float,
    grace: float,
    message: str,
) -> None:
    called = False

    def unexpected(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    workspace = PreparedWorkspace(
        parent=tmp_path,
        repository=tmp_path / "repo",
        worktree=tmp_path / "worktree",
        base_sha="a" * 40,
        _state=workspace_module._WorkspaceState(
            tmp_path, tmp_path / "repo", tmp_path / "worktree"
        ),
        _environment={},
    )
    monkeypatch.setattr(workspace_module, "_run_command", unexpected)
    with pytest.raises(ValueError, match=message):
        run_prepared_command(
            workspace,
            command=command,
            timeout=timeout,
            teardown_grace=grace,
        )
    assert not called


def test_prepared_workspace_wraps_a_pre_state_setup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace_module,
        "_local_env_vars",
        lambda _environment: (_ for _ in ()).throw(
            workspace_module._WorkspaceError("git probe failed")
        ),
    )
    with pytest.raises(WorkspacePrepareError, match="git probe failed"):
        workspace_module.prepare_workspace(
            base=tmp_path,
            protected_paths=(),
            environment={},
        )


def test_prepared_workspace_cleans_up_after_an_unexpected_setup_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"

    monkeypatch.setattr(workspace_module, "_local_env_vars", lambda _environment: set())
    monkeypatch.setattr(
        workspace_module, "_git_protected_paths", lambda _paths, _environment: ()
    )
    monkeypatch.setattr(
        workspace_module,
        "_safe_temp_parent",
        lambda _paths: parent.mkdir() or parent,
    )
    primary = KeyboardInterrupt()
    monkeypatch.setattr(
        workspace_module,
        "_prepare_repository",
        lambda *_args: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(KeyboardInterrupt) as caught:
        workspace_module.prepare_workspace(
            base=tmp_path,
            protected_paths=(),
            environment={},
        )
    assert caught.value is primary
    assert not parent.exists()


def test_prepared_workspace_cleans_up_if_lease_handoff_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    primary = KeyboardInterrupt()
    monkeypatch.setattr(workspace_module, "_local_env_vars", lambda _environment: set())
    monkeypatch.setattr(
        workspace_module, "_git_protected_paths", lambda _paths, _environment: ()
    )
    monkeypatch.setattr(
        workspace_module,
        "_safe_temp_parent",
        lambda _paths: parent.mkdir() or parent,
    )

    def prepared(_base: Path, state: object, _environment: object) -> None:
        state.base_sha = "a" * 40  # type: ignore[attr-defined]

    monkeypatch.setattr(workspace_module, "_prepare_repository", prepared)
    monkeypatch.setattr(
        workspace_module,
        "PreparedWorkspace",
        lambda **_kwargs: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(KeyboardInterrupt) as caught:
        workspace_module.prepare_workspace(
            base=tmp_path,
            protected_paths=(),
            environment={},
        )
    assert caught.value is primary
    assert not parent.exists()


def test_remove_parent_removes_the_tree(tmp_path: Path) -> None:
    from satyrn_evals.workspace import _remove_parent

    parent = tmp_path / "parent"
    (parent / "deep").mkdir(parents=True)
    _remove_parent(parent)
    assert not parent.exists()


def test_remove_parent_oserror_propagates(tmp_path: Path) -> None:
    from satyrn_evals.workspace import _remove_parent

    with pytest.raises(OSError):
        _remove_parent(tmp_path / "missing")
