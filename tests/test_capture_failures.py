import subprocess
from pathlib import Path
from typing import Never, cast

import pytest

import satyrn_evals.capture as capture_module
from satyrn_evals.capture import (
    _cleanup_worktree,
    _git,
    _local_env_vars,
    _Registration,
    _run_oracle,
    _safe_temp_parent,
    _worktree_registered,
    _WorktreeState,
    capture,
)
from satyrn_evals.capture_record import CaptureCode, CaptureOutcome
from satyrn_evals.errors import (
    ArtifactFailed,
    CaptureUsageError,
    CleanupFailed,
    GitFailed,
    HookError,
    OracleEnv,
)
from satyrn_evals.verdict import HookResult, Outcome

TEST_ID = "test_solution.py::test_solution"


def _hook(outcome: Outcome) -> HookResult:
    counts = {name: 0 for name in ("passed", "failed", "error", "skipped")}
    counts[outcome] = 1
    return HookResult(
        executed_test_ids=(TEST_ID,),
        outcomes={TEST_ID: outcome},
        counts=counts,
    )


def _arrange_successful_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path, Path]:
    """Install a subprocess-free successful capture seam for failure injection."""
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "tasks"
    task = output / "task"
    parent = tmp_path / "capture-parent"
    worktree = parent / "worktree"
    worktree.mkdir(parents=True)
    (worktree / "solution.py").write_text("VALUE = 1\n")
    (worktree / "test_solution.py").write_text("def test_solution(): pass\n")

    fix_sha = "f" * 40
    base_sha = "b" * 40

    def fake_git(
        _root: Path, args: list[str], *, input_text: str | None = None
    ) -> str:
        if args == ["rev-parse", "--show-toplevel"]:
            return f"{repo}\n"
        if args[-1:] == ["HEAD^{commit}"]:
            return f"{'h' * 40}\n"
        if args == ["rev-parse", "--absolute-git-dir"]:
            return f"{repo / '.git'}\n"
        if args == ["rev-parse", "--git-common-dir"]:
            return ".git\n"
        if args[-1:] == ["fix^{commit}"]:
            return f"{fix_sha}\n"
        if args[:4] == ["rev-list", "--parents", "-n", "1"]:
            return f"{fix_sha} {base_sha}\n"
        if args[:3] == ["log", "-1", "--format=%s"]:
            return "fix subject\n"
        if "ls-files" in args or "status" in args:
            return ""
        if "--name-status" in args:
            return "M\0solution.py\0"
        if "diff" in args:
            return (
                "diff --git a/solution.py b/solution.py\n"
                "--- a/solution.py\n"
                "+++ b/solution.py\n"
                "@@ -1 +1 @@\n"
                "-VALUE = 1\n"
                "+VALUE = 2\n"
            )
        if "worktree" in args:
            command = args.index("worktree")
            if args[command : command + 2] in (
                ["worktree", "add"],
                ["worktree", "remove"],
            ):
                return ""
        if args == ["apply", "-"]:
            assert input_text is not None
            return ""
        raise AssertionError((args, input_text))

    registrations = iter((True, False))
    hooks = iter((_hook("failed"), _hook("passed"), _hook("passed")))
    monkeypatch.setattr(capture_module, "_git", fake_git)
    monkeypatch.setattr(capture_module, "_safe_temp_parent", lambda _root: parent)
    monkeypatch.setattr(
        capture_module,
        "_worktree_registered",
        lambda _root, _worktree: next(registrations),
    )
    monkeypatch.setattr(
        capture_module,
        "_run_oracle",
        lambda _worktree, _cmd, _parent: next(hooks),
    )
    return repo, output, task, parent


def _arrange_refusal_before_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path, Path]:
    arranged = _arrange_successful_capture(tmp_path, monkeypatch)

    def fail_status_pathspec(_root: Path, _relative_output: str | None) -> list[str]:
        raise GitFailed("cannot inspect tracked output")

    monkeypatch.setattr(
        capture_module, "_source_status_pathspec", fail_status_pathspec
    )
    return arranged


def test_registration_state_distinguishes_absent_present_and_unknown(
    tmp_path: Path,
) -> None:
    state = _WorktreeState(tmp_path, tmp_path / "worktree")

    state.begin_add()
    assert state.registration is _Registration.MAY_EXIST
    state.observe_registration(True)
    assert state.registration is _Registration.PRESENT
    state.observe_registration(False)
    assert state.registration is _Registration.ABSENT
    state.observe_registration(None)
    assert state.registration is _Registration.MAY_EXIST
    with pytest.raises(AssertionError, match="unexpected registration state"):
        state.observe_registration(cast("bool | None", object()))


def test_registration_lookup_failure_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_root: Path) -> tuple[Path, ...]:
        raise GitFailed("cannot list")

    monkeypatch.setattr(capture_module, "_registered_worktrees", fail)
    assert _worktree_registered(tmp_path, tmp_path / "worktree") is None


def test_safe_temp_refuses_when_every_candidate_is_inside_a_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        capture_module, "_registered_worktrees", lambda _root: (Path("/"),)
    )

    with pytest.raises(GitFailed, match="inside a registered worktree"):
        _safe_temp_parent(tmp_path)


def test_safe_temp_reports_all_allocation_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(capture_module, "_registered_worktrees", lambda _root: ())
    monkeypatch.setattr(capture_module.tempfile, "gettempdir", lambda: str(tmp_path))

    def fail_mkdtemp(*, prefix: str, dir: Path) -> str:
        raise OSError(f"no space under {dir} for {prefix}")

    monkeypatch.setattr(capture_module.tempfile, "mkdtemp", fail_mkdtemp)
    with pytest.raises(GitFailed, match="cannot allocate a safe temporary directory"):
        _safe_temp_parent(tmp_path)


def test_safe_temp_discards_a_raced_into_worktree_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    registered = candidate / "registered"
    candidate.mkdir()
    monkeypatch.setattr(
        capture_module, "_registered_worktrees", lambda _root: (registered,)
    )
    monkeypatch.setattr(capture_module.tempfile, "gettempdir", lambda: str(candidate))
    calls = 0

    def allocate(*, prefix: str, dir: Path) -> str:
        nonlocal calls
        calls += 1
        path = registered if calls == 1 else tmp_path / "safe"
        path.mkdir()
        return str(path)

    monkeypatch.setattr(capture_module.tempfile, "mkdtemp", allocate)
    parent = _safe_temp_parent(tmp_path)

    assert parent == tmp_path / "safe"
    assert not registered.exists()


def test_oracle_start_failure_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        raise OSError("cannot execute")

    monkeypatch.setattr(capture_module.subprocess, "run", fail_run)
    monkeypatch.setattr(capture_module, "_clean_env", lambda: {})

    with pytest.raises(OracleEnv, match="cannot execute"):
        _run_oracle(tmp_path, ("oracle",), tmp_path)


def test_oracle_result_path_failure_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_mkstemp(*_args, **_kwargs) -> tuple[int, str]:
        raise OSError("no file descriptors")

    monkeypatch.setattr(capture_module.tempfile, "mkstemp", fail_mkstemp)
    with pytest.raises(OracleEnv, match="cannot prepare oracle result path"):
        _run_oracle(tmp_path, ("oracle",), tmp_path)


def test_oracle_result_setup_closes_fd_and_unlinks_reserved_path_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook_path = tmp_path / "reserved.json"
    hook_path.write_text("reserved\n")
    close_calls: list[int] = []

    monkeypatch.setattr(
        capture_module.tempfile,
        "mkstemp",
        lambda *_args, **_kwargs: (91, str(hook_path)),
    )

    def fail_first_close(fd: int) -> None:
        close_calls.append(fd)
        if len(close_calls) == 1:
            raise OSError("close interrupted")

    monkeypatch.setattr(capture_module.os, "close", fail_first_close)

    with pytest.raises(OracleEnv, match="close interrupted"):
        _run_oracle(tmp_path, ("oracle",), tmp_path)

    assert close_calls == [91, 91]
    assert not hook_path.exists()


def test_git_spawn_failure_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        raise OSError("git missing")

    monkeypatch.setattr(capture_module, "_clean_env", lambda: {})
    monkeypatch.setattr(capture_module.subprocess, "run", fail_run)
    with pytest.raises(GitFailed, match="cannot run git status"):
        _git(tmp_path, ["status"])


def test_git_environment_discovery_failure_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        raise OSError("git missing")

    monkeypatch.setattr(capture_module.subprocess, "run", fail_run)
    with pytest.raises(GitFailed, match="cannot inspect Git environment"):
        _local_env_vars()


def test_invalid_hook_result_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def completed(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0)

    def bad_result(_path: Path, _started: float) -> Never:
        raise HookError("bad hook result")

    monkeypatch.setattr(capture_module.subprocess, "run", completed)
    monkeypatch.setattr(capture_module, "_clean_env", lambda: {})
    monkeypatch.setattr(capture_module, "load_hook_result", bad_result)

    with pytest.raises(OracleEnv, match="bad hook result"):
        _run_oracle(tmp_path, ("oracle",), tmp_path)


def test_cleanup_accepts_failed_remove_after_git_confirms_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _WorktreeState(tmp_path, tmp_path / "worktree", _Registration.MAY_EXIST)

    def fail_remove(
        _root: Path, _args: list[str], *, input_text: str | None = None
    ) -> str:
        raise GitFailed(f"remove failed: {input_text}")

    monkeypatch.setattr(capture_module, "_git", fail_remove)
    monkeypatch.setattr(capture_module, "_worktree_registered", lambda *_args: False)

    _cleanup_worktree(tmp_path, state)
    assert state.registration is _Registration.ABSENT


@pytest.mark.parametrize("registered", [True, None], ids=["present", "unknown"])
def test_cleanup_retains_unconfirmed_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, registered: bool | None
) -> None:
    state = _WorktreeState(tmp_path, tmp_path / "worktree", _Registration.MAY_EXIST)
    monkeypatch.setattr(capture_module, "_git", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        capture_module, "_worktree_registered", lambda *_args: registered
    )

    with pytest.raises(CleanupFailed, match="retained"):
        _cleanup_worktree(tmp_path, state)


def test_capture_maps_bad_diff_metadata_to_refusal_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    def fake_git(_root: Path, args: list[str], *, input_text: str | None = None) -> str:
        if args == ["rev-parse", "--show-toplevel"]:
            return str(repo)
        if args[-1:] == ["HEAD^{commit}"]:
            return "h" * 40
        if args[-1:] == ["fix^{commit}"]:
            return "f" * 40
        if args[:4] == ["rev-list", "--parents", "-n", "1"]:
            return f"{'f' * 40} {'b' * 40}\n"
        if args[:3] == ["log", "-1", "--format=%s"]:
            return "fix subject"
        if args == ["rev-parse", "--absolute-git-dir"]:
            return str(repo / ".git")
        if args == ["rev-parse", "--git-common-dir"]:
            return ".git"
        if "ls-files" in args:
            return ""
        if "status" in args:
            return ""
        if "--name-status" in args:
            return "M\0unterminated"
        raise AssertionError((args, input_text))

    monkeypatch.setattr(capture_module, "_git", fake_git)
    record = capture(
        repo=repo,
        fix_sha="fix",
        name="bad-metadata",
        contract=None,
        output=tmp_path / "tasks",
    )

    assert record.outcome is CaptureOutcome.REFUSED
    assert record.code is CaptureCode.GIT_FAILED
    assert "NUL-terminated" in record.message


@pytest.mark.parametrize(
    "failure_at",
    [
        "repo",
        "head",
        "admin",
        "fix",
        "parent",
        "parent-empty",
        "parent-mismatch",
        "subject",
    ],
    ids=[
        "not-repo",
        "unborn",
        "admin-dir",
        "bad-fix",
        "parent",
        "empty-parent-output",
        "mismatched-parent-output",
        "subject",
    ],
)
def test_capture_pin_failures_are_usage_without_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_at: str
) -> None:
    repo = tmp_path / "repo"
    output = tmp_path / "tasks"

    def fake_git(_root: Path, args: list[str], *, input_text: str | None = None) -> str:
        if (
            failure_at == "repo"
            or (failure_at == "head" and args[-1:] == ["HEAD^{commit}"])
            or (
                failure_at == "admin"
                and args == ["rev-parse", "--absolute-git-dir"]
            )
            or (failure_at == "fix" and args[-1:] == ["fix^{commit}"])
            or (
                failure_at == "parent"
                and args[:4] == ["rev-list", "--parents", "-n", "1"]
            )
            or (
                failure_at == "subject"
                and args[:3] == ["log", "-1", "--format=%s"]
            )
        ):
            raise GitFailed(f"failed {failure_at}: {input_text}")
        if args == ["rev-parse", "--show-toplevel"]:
            return str(repo)
        if args[:4] == ["rev-list", "--parents", "-n", "1"]:
            if failure_at == "parent-empty":
                return ""
            if failure_at == "parent-mismatch":
                return f"{'x' * 40} {'b' * 40}\n"
            return f"{'h' * 40} {'b' * 40}\n"
        return "h" * 40

    monkeypatch.setattr(capture_module, "_git", fake_git)
    with pytest.raises(CaptureUsageError):
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )
    assert not output.exists()


def test_outer_exception_does_not_hide_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    caller_error = ValueError("handled by caller")

    def fail_cleanup(_root: Path, _state: _WorktreeState) -> Never:
        raise CleanupFailed(f"worktree retained at {parent / 'worktree'}")

    monkeypatch.setattr(capture_module, "_cleanup_worktree", fail_cleanup)
    try:
        raise caller_error
    except ValueError:
        record = capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert record.code is CaptureCode.CLEANUP_FAILED
    assert "worktree retained" in record.message
    assert not hasattr(caller_error, "__notes__")
    assert parent.exists()


def test_outer_exception_does_not_absorb_cleanup_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    caller_error = ValueError("handled by caller")
    interrupted = KeyboardInterrupt("cleanup interrupted")

    def interrupt_cleanup(_root: Path, _state: _WorktreeState) -> Never:
        raise interrupted

    monkeypatch.setattr(capture_module, "_cleanup_worktree", interrupt_cleanup)
    try:
        raise caller_error
    except ValueError:
        with pytest.raises(KeyboardInterrupt) as raised:
            capture(
                repo=repo,
                fix_sha="fix",
                name="task",
                contract=None,
                output=output,
            )

    assert raised.value is interrupted
    assert not hasattr(caller_error, "__notes__")
    assert parent.exists()


def test_refusal_record_construction_preserves_unexpected_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, _parent = _arrange_refusal_before_task(
        tmp_path, monkeypatch
    )
    interrupted = MemoryError("cannot construct refusal record")

    def interrupt_record(*_args: object, **_kwargs: object) -> Never:
        raise interrupted

    monkeypatch.setattr(capture_module, "CaptureRecord", interrupt_record)
    with pytest.raises(MemoryError) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted


def test_output_alias_without_lexical_containment_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "canonical-root"
    output = tmp_path / "casing-alias" / "tasks"
    root.mkdir()
    monkeypatch.setattr(capture_module, "_contains_path", lambda *_args: True)

    with pytest.raises(CaptureUsageError, match="canonical path spelling"):
        capture_module._output_relative_path(root, output, ())


def test_underivable_implicit_name_is_usage_without_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    monkeypatch.setattr(capture_module, "slugify_subject", lambda _subject: None)

    with pytest.raises(CaptureUsageError, match="cannot derive"):
        capture(
            repo=repo,
            fix_sha="fix",
            name=None,
            contract=None,
            output=output,
        )

    assert not output.exists()


def test_output_directory_creation_failure_is_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    real_mkdir = Path.mkdir

    def fail_output_mkdir(path: Path, *args, **kwargs) -> None:
        if path == output:
            raise OSError("output is read-only")
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_output_mkdir)
    with pytest.raises(CaptureUsageError, match="cannot create output directory"):
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )


def test_task_directory_write_failure_before_ownership_is_a_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    real_mkdir = Path.mkdir

    def fail_task_mkdir(path: Path, *args, **kwargs) -> None:
        if path == task:
            raise OSError("task filesystem unavailable")
        real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_task_mkdir)
    record = capture(
        repo=repo,
        fix_sha="fix",
        name="task",
        contract=None,
        output=output,
    )

    assert record.code is CaptureCode.ARTIFACT_FAILED
    assert "task filesystem unavailable" in record.message
    assert not task.exists()


@pytest.mark.parametrize(
    "cleanup_error",
    [OSError("task rollback blocked"), MemoryError("task rollback allocation failed")],
    ids=["os-error", "memory-error"],
)
def test_unexpected_task_write_and_rollback_failures_preserve_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: BaseException,
) -> None:
    repo, output, task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    interrupted = KeyboardInterrupt("stop task publication")
    real_write_bytes = Path.write_bytes
    real_rmtree = capture_module.shutil.rmtree

    def interrupt_patch(path: Path, data: bytes, *args, **kwargs) -> int:
        if path.name == "known-good.patch":
            raise interrupted
        return real_write_bytes(path, data, *args, **kwargs)

    def fail_task_rollback(path: Path) -> None:
        if Path(path) == task:
            raise cleanup_error
        real_rmtree(path)

    monkeypatch.setattr(Path, "write_bytes", interrupt_patch)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_task_rollback)

    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert any(str(cleanup_error) in note for note in interrupted.__notes__)
    assert task.exists()


def test_unexpected_capture_error_notes_worktree_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    interrupted = KeyboardInterrupt("stop materialization")

    def interrupt_copy(*_args, **_kwargs) -> Never:
        raise interrupted

    def fail_cleanup(_root: Path, _state: object) -> Never:
        raise CleanupFailed("worktree retained at /recovery/worktree")

    monkeypatch.setattr(capture_module.shutil, "copytree", interrupt_copy)
    monkeypatch.setattr(capture_module, "_cleanup_worktree", fail_cleanup)

    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert interrupted.__notes__ == ["worktree retained at /recovery/worktree"]


def test_unexpected_capture_error_notes_parent_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    interrupted = KeyboardInterrupt("stop materialization")
    real_rmtree = capture_module.shutil.rmtree

    def interrupt_copy(*_args, **_kwargs) -> Never:
        raise interrupted

    def fail_parent_cleanup(path: Path) -> None:
        if Path(path) == parent:
            raise OSError("parent cleanup blocked")
        real_rmtree(path)

    monkeypatch.setattr(capture_module.shutil, "copytree", interrupt_copy)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_parent_cleanup)

    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert any("parent cleanup blocked" in note for note in interrupted.__notes__)


def test_primary_exception_survives_secondary_worktree_cleanup_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    primary = KeyboardInterrupt("stop materialization")

    def interrupt_copy(*_args: object, **_kwargs: object) -> Never:
        raise primary

    def interrupt_cleanup(_root: Path, _state: _WorktreeState) -> Never:
        raise MemoryError("cleanup allocation failed")

    monkeypatch.setattr(capture_module.shutil, "copytree", interrupt_copy)
    monkeypatch.setattr(capture_module, "_cleanup_worktree", interrupt_cleanup)

    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is primary
    assert any("MemoryError" in note for note in primary.__notes__)
    assert parent.exists()


def test_primary_exception_survives_secondary_parent_cleanup_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    primary = MemoryError("materialization allocation failed")
    real_rmtree = capture_module.shutil.rmtree

    def interrupt_copy(*_args: object, **_kwargs: object) -> Never:
        raise primary

    def interrupt_parent(path: Path) -> None:
        if Path(path) == parent:
            raise KeyboardInterrupt("stop parent cleanup")
        real_rmtree(path)

    monkeypatch.setattr(capture_module.shutil, "copytree", interrupt_copy)
    monkeypatch.setattr(capture_module.shutil, "rmtree", interrupt_parent)

    with pytest.raises(MemoryError) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is primary
    assert any("KeyboardInterrupt" in note for note in primary.__notes__)
    assert parent.exists()


def test_result_does_not_hide_primary_exception_during_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    primary = KeyboardInterrupt("stop task publication")
    real_write_bytes = Path.write_bytes

    def interrupt_patch(
        path: Path, data: bytes, *_args: object, **_kwargs: object
    ) -> int:
        if path.name == "known-good.patch":
            raise primary
        return real_write_bytes(path, data)

    def fail_cleanup(_root: Path, _state: _WorktreeState) -> Never:
        raise CleanupFailed(f"worktree retained at {parent / 'worktree'}")

    monkeypatch.setattr(Path, "write_bytes", interrupt_patch)
    monkeypatch.setattr(capture_module, "_cleanup_worktree", fail_cleanup)

    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is primary
    assert any("worktree retained" in note for note in primary.__notes__)
    assert parent.exists()


def test_unexpected_worktree_cleanup_exception_is_not_converted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    interrupted = SystemExit("cleanup interrupted")

    def interrupt_cleanup(_root: Path, _state: _WorktreeState) -> Never:
        raise interrupted

    monkeypatch.setattr(capture_module, "_cleanup_worktree", interrupt_cleanup)
    with pytest.raises(SystemExit) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert parent.exists()


def test_unexpected_parent_cleanup_exception_is_not_converted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, parent = _arrange_successful_capture(tmp_path, monkeypatch)
    interrupted = KeyboardInterrupt("parent cleanup interrupted")
    real_rmtree = capture_module.shutil.rmtree

    def interrupt_parent(path: Path) -> None:
        if Path(path) == parent:
            raise interrupted
        real_rmtree(path)

    monkeypatch.setattr(capture_module.shutil, "rmtree", interrupt_parent)
    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert parent.exists()


def test_parent_cleanup_failure_displaces_task_collision_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    real_mkdir = Path.mkdir
    real_rmtree = capture_module.shutil.rmtree

    def collide_task(path: Path, *args, **kwargs) -> None:
        if path == task:
            raise FileExistsError("another capture won")
        real_mkdir(path, *args, **kwargs)

    def fail_parent_cleanup(path: Path) -> None:
        if Path(path) == parent:
            raise OSError("parent cleanup blocked")
        real_rmtree(path)

    monkeypatch.setattr(Path, "mkdir", collide_task)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_parent_cleanup)
    record = capture(
        repo=repo,
        fix_sha="fix",
        name="task",
        contract=None,
        output=output,
    )

    assert record.code is CaptureCode.CLEANUP_FAILED
    assert "displaced usage error" in record.message
    assert "parent cleanup blocked" in record.message
    assert record.task_dir is None


def test_cleanup_result_precedes_record_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, _task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )

    def fail_cleanup(_root: Path, _state: object) -> Never:
        raise CleanupFailed("worktree retained at /recovery/worktree")

    def collide_record(*_args, **_kwargs) -> Never:
        raise FileExistsError("record appeared")

    monkeypatch.setattr(capture_module, "_cleanup_worktree", fail_cleanup)
    monkeypatch.setattr(capture_module, "write_capture_record", collide_record)

    with pytest.raises(CleanupFailed, match="publication also failed") as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert "/recovery/worktree" in str(raised.value)


def test_record_collision_after_refusal_does_not_attempt_task_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, _parent = _arrange_refusal_before_task(
        tmp_path, monkeypatch
    )

    def collide_record(*_args, **_kwargs) -> Never:
        raise FileExistsError("record appeared")

    monkeypatch.setattr(capture_module, "write_capture_record", collide_record)
    with pytest.raises(CaptureUsageError, match="task already exists"):
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert not task.exists()


def test_record_transport_and_task_rollback_failures_report_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    real_rmtree = capture_module.shutil.rmtree

    def fail_record(*_args, **_kwargs) -> Never:
        raise OSError("record transport failed")

    def fail_task_rollback(path: Path) -> None:
        if Path(path) == task:
            raise OSError("task rollback blocked")
        real_rmtree(path)

    monkeypatch.setattr(capture_module, "write_capture_record", fail_record)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_task_rollback)

    with pytest.raises(CleanupFailed, match="task retained") as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert "task rollback blocked" in str(raised.value)
    assert task.exists()


def test_record_transport_failure_after_refusal_is_artifact_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, _parent = _arrange_refusal_before_task(
        tmp_path, monkeypatch
    )

    def fail_record(*_args, **_kwargs) -> Never:
        raise OSError("record transport failed")

    monkeypatch.setattr(capture_module, "write_capture_record", fail_record)
    with pytest.raises(ArtifactFailed, match="cannot publish capture record"):
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert not task.exists()


def test_unexpected_record_error_and_rollback_failure_preserve_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, _parent = _arrange_successful_capture(
        tmp_path, monkeypatch
    )
    interrupted = MemoryError("stop record publication")
    rollback_interrupted = KeyboardInterrupt("stop task rollback")
    real_rmtree = capture_module.shutil.rmtree

    def interrupt_record(*_args, **_kwargs) -> Never:
        raise interrupted

    def fail_task_rollback(path: Path) -> None:
        if Path(path) == task:
            raise rollback_interrupted
        real_rmtree(path)

    monkeypatch.setattr(capture_module, "write_capture_record", interrupt_record)
    monkeypatch.setattr(capture_module.shutil, "rmtree", fail_task_rollback)

    with pytest.raises(MemoryError) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert any("KeyboardInterrupt" in note for note in interrupted.__notes__)
    assert task.exists()


def test_unexpected_record_error_after_refusal_skips_task_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, output, task, _parent = _arrange_refusal_before_task(
        tmp_path, monkeypatch
    )
    interrupted = KeyboardInterrupt("stop refusal record")

    def interrupt_record(*_args, **_kwargs) -> Never:
        raise interrupted

    monkeypatch.setattr(capture_module, "write_capture_record", interrupt_record)
    with pytest.raises(KeyboardInterrupt) as raised:
        capture(
            repo=repo,
            fix_sha="fix",
            name="task",
            contract=None,
            output=output,
        )

    assert raised.value is interrupted
    assert not task.exists()
