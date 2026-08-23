import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

import satyrn_evals.workspace as workspace_module
from satyrn_evals.workspace import Registration, WorkspaceCode, WorkspaceResult


def _state(tmp_path: Path) -> workspace_module._WorkspaceState:
    parent = tmp_path / "owned"
    parent.mkdir(parents=True)
    repository = parent / "seed"
    repository.mkdir()
    worktree = parent / "worktree"
    worktree.mkdir()
    return workspace_module._WorkspaceState(parent, repository, worktree)


def _completed(
    returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(("git",), returncode, stdout, stderr)


def test_snapshot_enumeration_and_entry_errors_are_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workspace_module.os, "scandir", lambda _path: (_ for _ in ()).throw(OSError("scan")))
    with pytest.raises(Exception, match="cannot enumerate.*scan"):
        workspace_module.snapshot_tree(tmp_path)

    monkeypatch.undo()
    link = tmp_path / "link"
    link.symlink_to("target")
    monkeypatch.setattr(workspace_module.os, "readlink", lambda _path: (_ for _ in ()).throw(OSError("readlink")))
    with pytest.raises(Exception, match="cannot inspect.*readlink"):
        workspace_module.snapshot_tree(tmp_path)


def test_contains_path_handles_case_alias(tmp_path: Path) -> None:
    root = tmp_path / "CaseRoot"
    root.mkdir()
    alias = tmp_path / "caseroot"
    if not alias.exists():
        pytest.skip("filesystem is case-sensitive")
    assert workspace_module._contains_path(root, alias)


def test_contains_path_handles_identity_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = (tmp_path / "root").resolve()
    root.mkdir()
    alias = (tmp_path / "alias").resolve()
    alias.mkdir()
    monkeypatch.setattr(
        Path,
        "samefile",
        lambda path, other: path == alias and other == root,
    )
    assert workspace_module._contains_path(root, alias)


def test_contains_path_fails_closed_on_samefile_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setattr(
        Path,
        "samefile",
        lambda _self, _other: (_ for _ in ()).throw(OSError("samefile")),
    )
    with pytest.raises(workspace_module._WorkspaceError, match="path identity"):
        workspace_module._contains_path(root, other)


def test_safe_temp_parent_fails_closed_on_identity_stat_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protected = (tmp_path / "protected").resolve()
    protected.mkdir()
    original_stat = Path.stat

    def fail_protected_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path == protected:
            raise PermissionError("identity unavailable")
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", fail_protected_stat)
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: pytest.fail("uncertain candidate must not be allocated"),
    )

    with pytest.raises(workspace_module._WorkspaceError, match="identity unavailable"):
        workspace_module._safe_temp_parent((protected,))


def test_safe_temp_parent_exhausts_protected_roots() -> None:
    with pytest.raises(Exception, match="cannot allocate.*protected"):
        workspace_module._safe_temp_parent((Path("/"),))


def test_safe_temp_parent_retries_allocation_and_postcheck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fake_mkdtemp(*, prefix: str, dir: Path) -> str:
        nonlocal calls
        del prefix, dir
        calls += 1
        if calls == 1:
            raise OSError("full")
        candidate = tmp_path / f"candidate-{calls}"
        candidate.mkdir()
        return os.fspath(candidate)

    checks = iter((False, False, True, False, False))
    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: "/candidate-a")
    monkeypatch.setattr(workspace_module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(workspace_module, "_contains_path", lambda _root, _path: next(checks))
    monkeypatch.setattr(workspace_module.shutil, "rmtree", lambda _path: None)

    parent = workspace_module._safe_temp_parent((tmp_path / "protected",))
    assert parent == (tmp_path / "candidate-3").resolve()


def test_safe_temp_parent_reports_unsafe_candidate_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "unsafe"
    candidate.mkdir()
    checks = iter((False, True))
    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: "/candidate")
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(candidate),
    )
    monkeypatch.setattr(
        workspace_module,
        "_contains_path",
        lambda _root, _path: next(checks),
    )
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("locked")),
    )
    with pytest.raises(Exception, match="cleanup failed.*retained.*locked"):
        workspace_module._safe_temp_parent((tmp_path / "protected",))


@pytest.mark.parametrize("cleanup_error", [None, OSError("locked")])
def test_safe_temp_parent_handles_resolution_failure_after_allocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: OSError | None,
) -> None:
    root = tmp_path / "candidate-root"
    root.mkdir()
    allocated = root / "allocated"
    allocated.mkdir()
    real_resolve = Path.resolve

    def selected_resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if path == allocated:
            raise OSError("resolve")
        return real_resolve(path, *args, **kwargs)  # type: ignore[arg-type]

    def allocate(**_kwargs: object) -> str:
        allocated.mkdir(exist_ok=True)
        return os.fspath(allocated)

    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(root))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        allocate,
    )
    monkeypatch.setattr(Path, "resolve", selected_resolve)
    if cleanup_error is not None:
        monkeypatch.setattr(
            workspace_module.shutil,
            "rmtree",
            lambda _path: (_ for _ in ()).throw(cleanup_error),
        )
        with pytest.raises(workspace_module._RetainedCleanupError, match="resolution"):
            workspace_module._safe_temp_parent((tmp_path / "protected",))
    else:
        with pytest.raises(workspace_module._WorkspaceError, match="cannot resolve"):
            workspace_module._safe_temp_parent((tmp_path / "protected",))
        assert not allocated.exists()


def test_safe_temp_parent_preserves_baseexception_during_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocated = tmp_path / "allocated"
    allocated.mkdir()
    primary = KeyboardInterrupt()
    real_resolve = Path.resolve

    def selected_resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if path == allocated:
            raise primary
        return real_resolve(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(tmp_path))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(allocated),
    )
    monkeypatch.setattr(Path, "resolve", selected_resolve)
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(MemoryError("cleanup")),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module._safe_temp_parent((tmp_path / "protected",))
    assert raised.value is primary
    assert any("MemoryError" in note for note in primary.__notes__)


def test_safe_temp_parent_preserves_cleanup_baseexception_after_resolution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocated = tmp_path / "allocated"
    allocated.mkdir()
    cleanup_error = MemoryError("cleanup")
    real_resolve = Path.resolve

    def selected_resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if path == allocated:
            raise OSError("resolve")
        return real_resolve(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(tmp_path))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(allocated),
    )
    monkeypatch.setattr(Path, "resolve", selected_resolve)
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(cleanup_error),
    )

    with pytest.raises(MemoryError) as raised:
        workspace_module._safe_temp_parent((tmp_path / "protected",))

    assert raised.value is cleanup_error
    assert allocated.exists()
    assert cleanup_error.__notes__ == [
        f"temporary directory resolution failed: resolve; retained at {allocated}"
    ]


def test_safe_temp_parent_preserves_unsafe_cleanup_baseexception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocated = tmp_path / "allocated"
    allocated.mkdir()
    primary = KeyboardInterrupt()
    checks = iter((False, True))
    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(tmp_path))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(allocated),
    )
    monkeypatch.setattr(
        workspace_module, "_contains_path", lambda _root, _path: next(checks)
    )
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module._safe_temp_parent((tmp_path / "protected",))
    assert raised.value is primary
    assert any("retained" in note for note in primary.__notes__)


@pytest.mark.parametrize(
    "cleanup_error", [OSError("locked"), MemoryError("cleanup")]
)
def test_safe_temp_parent_owns_postcheck_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: BaseException,
) -> None:
    allocated = tmp_path / "allocated"
    allocated.mkdir()
    postcheck_error = workspace_module._WorkspaceError("postcheck")
    checks: list[object] = [False, postcheck_error]

    def contains(_root: Path, _path: Path) -> bool:
        value = checks.pop(0)
        if isinstance(value, BaseException):
            raise value
        return cast("bool", value)

    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(tmp_path))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(allocated),
    )
    monkeypatch.setattr(workspace_module, "_contains_path", contains)
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(cleanup_error),
    )

    if isinstance(cleanup_error, OSError):
        with pytest.raises(workspace_module._RetainedCleanupError, match="postcheck"):
            workspace_module._safe_temp_parent((tmp_path / "protected",))
    else:
        with pytest.raises(MemoryError) as raised:
            workspace_module._safe_temp_parent((tmp_path / "protected",))
        assert raised.value is cleanup_error
        assert any(
            "postcheck" in note and "retained" in note
            for note in cleanup_error.__notes__
        )
    assert allocated.exists()


def test_safe_temp_parent_discards_postcheck_failure_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocated = tmp_path / "allocated"
    allocated.mkdir()
    checks: list[object] = [
        False,
        workspace_module._WorkspaceError("postcheck"),
        True,
        True,
    ]

    def contains(_root: Path, _path: Path) -> bool:
        value = checks.pop(0)
        if isinstance(value, BaseException):
            raise value
        return cast("bool", value)

    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(tmp_path))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(allocated),
    )
    monkeypatch.setattr(workspace_module, "_contains_path", contains)

    with pytest.raises(workspace_module._WorkspaceError, match="cannot allocate"):
        workspace_module._safe_temp_parent((tmp_path / "protected",))

    assert not allocated.exists()


def test_safe_temp_parent_preserves_postcheck_baseexception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocated = tmp_path / "allocated"
    allocated.mkdir()
    primary = MemoryError("postcheck")
    checks: list[object] = [False, primary]

    def contains(_root: Path, _path: Path) -> bool:
        value = checks.pop(0)
        if isinstance(value, BaseException):
            raise value
        return cast("bool", value)

    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(tmp_path))
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: os.fspath(allocated),
    )
    monkeypatch.setattr(workspace_module, "_contains_path", contains)
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("locked")),
    )

    with pytest.raises(MemoryError) as raised:
        workspace_module._safe_temp_parent((tmp_path / "protected",))

    assert raised.value is primary
    assert allocated.exists()
    assert any("locked" in note and "retained" in note for note in primary.__notes__)


def test_safe_temp_parent_refuses_uncertain_case_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protected = tmp_path / "CaseRoot"
    protected.mkdir()
    alias = tmp_path / "caseroot"
    if not alias.exists():
        pytest.skip("filesystem is case-sensitive")
    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(alias))
    monkeypatch.setattr(
        Path,
        "samefile",
        lambda _self, _other: (_ for _ in ()).throw(OSError("samefile")),
    )
    monkeypatch.setattr(
        workspace_module.tempfile,
        "mkdtemp",
        lambda **_kwargs: pytest.fail("uncertain candidate must not be allocated"),
    )

    with pytest.raises(workspace_module._WorkspaceError, match="path identity"):
        workspace_module._safe_temp_parent((protected,))


def test_local_env_var_discovery_spawn_and_git_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workspace_module.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("spawn")),
    )
    with pytest.raises(Exception, match="cannot inspect.*spawn"):
        workspace_module._local_env_vars({})

    monkeypatch.setattr(
        workspace_module.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(1, stderr=b"bad git"),
    )
    with pytest.raises(Exception, match="cannot inspect.*bad git"):
        workspace_module._local_env_vars({})

    observed: dict[str, str] = {}

    def successful(*_args: object, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        observed.update(kwargs["env"])
        return _completed(stdout=b"GIT_DIR\n")

    monkeypatch.setattr(workspace_module.subprocess, "run", successful)
    assert workspace_module._local_env_vars(
        {"PATH": "/bin", "GIT_DIR": "/caller", "GIT_CONFIG_COUNT": "1"}
    ) == {"GIT_DIR"}
    assert observed == {"PATH": "/bin", "GIT_TERMINAL_PROMPT": "0"}


def test_owned_git_spawn_and_status_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace_module.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("spawn")),
    )
    with pytest.raises(Exception, match="cannot run git status: spawn"):
        workspace_module._git(tmp_path, ("status",), {})
    monkeypatch.setattr(
        workspace_module.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(2, stderr=b"bad status"),
    )
    with pytest.raises(Exception, match="git status failed: bad status"):
        workspace_module._git(tmp_path, ("status",), {})


def test_git_protected_paths_handles_files_missing_paths_and_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    tracked = repository / "tracked"
    tracked.write_text("x")
    admin = tmp_path / "admin"
    common = tmp_path / "common"

    def git(
        _root: Path,
        args: tuple[str, ...],
        _environment: dict[str, str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        match args:
            case ("rev-parse", "--show-toplevel"):
                return _completed(stdout=os.fsencode(repository) + b"\n")
            case ("rev-parse", "--absolute-git-dir"):
                return _completed(stdout=os.fsencode(admin) + b"\n")
            case ("rev-parse", "--git-common-dir"):
                return _completed(stdout=os.fsencode(common) + b"\n")
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(workspace_module, "_git", git)
    monkeypatch.setattr(
        workspace_module,
        "_registered_worktrees",
        lambda *_args: (repository, tmp_path / "sibling"),
    )
    protected = workspace_module._git_protected_paths(
        (tracked, repository / "missing" / "child", repository), {}
    )
    assert set(protected) == {
        repository.resolve(),
        admin.resolve(),
        common.resolve(),
        (tmp_path / "sibling").resolve(),
    }


def test_git_protected_paths_stops_at_filesystem_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def git(
        _root: Path,
        args: tuple[str, ...],
        _environment: dict[str, str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        match args:
            case ("rev-parse", "--show-toplevel"):
                return _completed(stdout=b"/\n")
            case ("rev-parse", "--absolute-git-dir") | (
                "rev-parse",
                "--git-common-dir",
            ):
                return _completed(stdout=b"/.git\n")
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(workspace_module, "_git", git)
    monkeypatch.setattr(workspace_module, "_registered_worktrees", lambda *_args: ())

    assert set(workspace_module._git_protected_paths((tmp_path,), {})) == {
        Path("/"),
        Path("/.git"),
    }

def test_registration_lookup_failure_is_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace_module,
        "_registered_worktrees",
        lambda *_args: (_ for _ in ()).throw(workspace_module._WorkspaceError("bad")),
    )
    assert workspace_module._worktree_registered(tmp_path, tmp_path / "work", {}) is None


def test_prepare_repository_wraps_copy_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "base"
    base.mkdir()
    state = _state(tmp_path)
    state.repository.rmdir()
    monkeypatch.setattr(
        workspace_module.shutil,
        "copytree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("copy")),
    )
    with pytest.raises(Exception, match="cannot copy.*copy"):
        workspace_module._prepare_repository(base, state, {})


def test_prepare_repository_wraps_directory_creation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "base"
    base.mkdir()
    state = _state(tmp_path)
    state.repository.rmdir()
    real_mkdir = Path.mkdir

    def selected_mkdir(path: Path, *args: object, **kwargs: object) -> None:
        if path == state.repository:
            raise OSError("mkdir")
        real_mkdir(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "mkdir", selected_mkdir)
    with pytest.raises(Exception, match="cannot create synthetic.*mkdir"):
        workspace_module._prepare_repository(base, state, {})


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("registration", "did not confirm"),
        ("head", "not detached"),
        ("status", "not clean"),
        ("snapshot", "does not match"),
    ],
)
@pytest.mark.integration
def test_prepare_repository_fails_closed_on_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    message: str,
) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "a").write_text("a")
    state = _state(tmp_path)
    shutil.rmtree(state.repository)
    state.worktree.rmdir()
    real_git = workspace_module._git
    real_registered = workspace_module._worktree_registered
    real_snapshot = workspace_module.snapshot_tree
    snapshot_calls = 0

    def selected_git(
        root: Path,
        args: tuple[str, ...],
        environment: dict[str, str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[bytes]:
        result = real_git(root, args, environment, **kwargs)
        if mode == "head" and args[:2] == ("rev-parse", "--verify"):
            return _completed(stdout=b"f" * 40 + b"\n")
        if mode == "status" and "status" in args:
            return _completed(stdout=b"?? dirty\0")
        return result

    def selected_snapshot(root: Path) -> tuple[workspace_module.TreeEntry, ...]:
        nonlocal snapshot_calls
        snapshot_calls += 1
        value = real_snapshot(root)
        if mode == "snapshot" and snapshot_calls == 2:
            return ()
        return value

    monkeypatch.setattr(workspace_module, "_git", selected_git)
    monkeypatch.setattr(workspace_module, "snapshot_tree", selected_snapshot)
    if mode == "registration":
        monkeypatch.setattr(workspace_module, "_worktree_registered", lambda *_args: False)
    try:
        with pytest.raises(Exception, match=message):
            workspace_module._prepare_repository(base, state, {})
    finally:
        monkeypatch.setattr(workspace_module, "_git", real_git)
        monkeypatch.setattr(workspace_module, "_worktree_registered", real_registered)
        if state.registration is not Registration.ABSENT:
            with pytest.MonkeyPatch.context() as cleanup_patch:
                cleanup_patch.setattr(workspace_module, "_git", real_git)
                cleanup_patch.setattr(workspace_module, "_worktree_registered", real_registered)
                workspace_module._cleanup_worktree(state, {})


def test_group_observation_and_wait_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        workspace_module.os,
        "killpg",
        lambda *_args: (_ for _ in ()).throw(ProcessLookupError()),
    )
    assert workspace_module._group_gone(7)
    monkeypatch.setattr(
        workspace_module.os,
        "killpg",
        lambda *_args: (_ for _ in ()).throw(PermissionError()),
    )
    assert not workspace_module._group_gone(7)
    monkeypatch.setattr(workspace_module.os, "killpg", lambda *_args: None)
    assert not workspace_module._group_gone(7)

    observations = iter((False, True))
    monkeypatch.setattr(workspace_module, "_group_gone", lambda _pid: next(observations))
    monkeypatch.setattr(workspace_module.time, "sleep", lambda _duration: None)
    times = iter((0.0, 0.0, 1.0))
    monkeypatch.setattr(workspace_module.time, "monotonic", lambda: next(times))
    assert workspace_module._wait_until_group_gone(7, 0.5)


class _FakeProcess:
    pid = 42

    def __init__(self, waits: list[int | BaseException]) -> None:
        self.waits = waits
        self.terminated = False
        self.killed = False

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        value = self.waits.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def _process(fake: _FakeProcess) -> subprocess.Popen[bytes]:
    return cast("subprocess.Popen[bytes]", fake)


def test_posix_teardown_records_signal_and_reap_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess([subprocess.TimeoutExpired("x", 1)])
    signals: list[signal.Signals] = []

    def signal_group(_pid: int, selected: signal.Signals) -> None:
        signals.append(selected)
        if selected is signal.SIGTERM:
            raise PermissionError("term")
        raise ProcessLookupError

    monkeypatch.setattr(workspace_module, "_is_posix", lambda: True)
    monkeypatch.setattr(workspace_module.os, "killpg", signal_group)
    observations = iter((False, True))
    monkeypatch.setattr(
        workspace_module, "_wait_until_group_gone", lambda *_args: next(observations)
    )
    monkeypatch.setattr(workspace_module, "_group_gone", lambda _pid: False)

    safe, detail = workspace_module._teardown_process(_process(process), 0.1)
    assert not safe
    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert detail is not None and "SIGTERM" in detail and "not reaped" in detail


def test_posix_teardown_handles_already_gone_and_kill_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess([0])
    monkeypatch.setattr(workspace_module, "_is_posix", lambda: True)
    monkeypatch.setattr(
        workspace_module.os,
        "killpg",
        lambda *_args: (_ for _ in ()).throw(ProcessLookupError()),
    )
    monkeypatch.setattr(workspace_module, "_wait_until_group_gone", lambda *_args: True)
    monkeypatch.setattr(workspace_module, "_group_gone", lambda _pid: True)
    assert workspace_module._teardown_process(_process(process), 0.1) == (True, None)

    process = _FakeProcess([0])

    def signal_group(_pid: int, selected: signal.Signals) -> None:
        if selected is signal.SIGKILL:
            raise PermissionError("kill")

    monkeypatch.setattr(workspace_module.os, "killpg", signal_group)
    observations = iter((False, True))
    monkeypatch.setattr(
        workspace_module, "_wait_until_group_gone", lambda *_args: next(observations)
    )
    monkeypatch.setattr(workspace_module, "_group_gone", lambda _pid: True)
    safe, detail = workspace_module._teardown_process(_process(process), 0.1)
    assert safe
    assert detail is not None and "SIGKILL" in detail


def test_windows_fallback_terminate_kill_and_reap_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess(
        [subprocess.TimeoutExpired("x", 1), OSError("reap")]
    )
    monkeypatch.setattr(workspace_module, "_is_posix", lambda: False)

    def bad_terminate() -> None:
        raise OSError("term")

    def bad_kill() -> None:
        raise OSError("kill")

    process.terminate = bad_terminate
    process.kill = bad_kill
    safe, detail = workspace_module._teardown_process(_process(process), 0.1)
    assert not safe
    assert detail is not None
    assert "terminate" in detail and "kill" in detail and "reap" in detail


def test_run_command_start_spool_timeout_and_unexpected_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    state.base_sha = "a" * 40
    monkeypatch.setattr(
        workspace_module.tempfile,
        "TemporaryFile",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("spool")),
    )
    result = workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert result.code is WorkspaceCode.WORKSPACE_FAILED

    monkeypatch.undo()
    state = _state(tmp_path / "start")
    state.base_sha = "a" * 40
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("start")),
    )
    result = workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert result.code is WorkspaceCode.COMMAND_UNAVAILABLE

    monkeypatch.undo()
    state = _state(tmp_path / "start-uncertain")
    state.base_sha = "a" * 40
    primary = MemoryError("start")
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(MemoryError) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert not state.process_cleanup_safe
    assert any(os.fspath(state.parent) in note for note in primary.__notes__)

    monkeypatch.undo()
    state = _state(tmp_path / "timeout")
    state.base_sha = "a" * 40
    process = _FakeProcess([subprocess.TimeoutExpired("x", 1)])
    monkeypatch.setattr(workspace_module.subprocess, "Popen", lambda *_args, **_kwargs: _process(process))
    monkeypatch.setattr(workspace_module, "_teardown_process", lambda *_args: (False, "alive"))
    result = workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert not state.process_cleanup_safe

    monkeypatch.undo()
    state = _state(tmp_path / "unexpected")
    primary = KeyboardInterrupt()
    process = _FakeProcess([primary])
    monkeypatch.setattr(workspace_module.subprocess, "Popen", lambda *_args, **_kwargs: _process(process))
    monkeypatch.setattr(workspace_module, "_teardown_process", lambda *_args: (False, "alive"))
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert any("process cleanup unconfirmed" in note for note in primary.__notes__)

    monkeypatch.undo()
    state = _state(tmp_path / "unexpected-safe")
    primary = KeyboardInterrupt()
    process = _FakeProcess([primary])
    monkeypatch.setattr(workspace_module.subprocess, "Popen", lambda *_args, **_kwargs: _process(process))
    monkeypatch.setattr(workspace_module, "_teardown_process", lambda *_args: (True, None))
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert not hasattr(primary, "__notes__")

    monkeypatch.undo()
    state = _state(tmp_path / "unexpected-teardown")
    primary = KeyboardInterrupt()
    process = _FakeProcess([primary])
    monkeypatch.setattr(workspace_module.subprocess, "Popen", lambda *_args, **_kwargs: _process(process))
    monkeypatch.setattr(
        workspace_module,
        "_teardown_process",
        lambda *_args: (_ for _ in ()).throw(MemoryError("teardown")),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert any("MemoryError" in note for note in primary.__notes__)


class _Output:
    def __init__(self, close_error: BaseException | None = None) -> None:
        self.close_error = close_error
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


def test_run_command_owns_partial_spools_and_preserves_wait_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    state.base_sha = "a" * 40
    first = _Output()
    acquisitions: list[object] = [first, OSError("second spool")]

    def acquire(**_kwargs: object) -> Any:
        value = acquisitions.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(workspace_module.tempfile, "TemporaryFile", acquire)
    result = workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert result.code is WorkspaceCode.WORKSPACE_FAILED
    assert first.close_calls == 1

    monkeypatch.undo()
    state = _state(tmp_path / "wait")
    state.base_sha = "a" * 40
    primary = OSError("wait failed")
    process = _FakeProcess([primary])
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _process(process),
    )
    monkeypatch.setattr(workspace_module, "_teardown_process", lambda *_args: (True, None))
    with pytest.raises(OSError) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert state.process_cleanup_safe


def test_run_command_close_and_teardown_failures_keep_cleanup_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    state.base_sha = "a" * 40
    outputs = iter((_Output(OSError("close")), _Output()))
    monkeypatch.setattr(
        workspace_module.tempfile, "TemporaryFile", lambda **_kwargs: next(outputs)
    )
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("start")),
    )
    result = workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert result.retained_path == os.fspath(state.parent)
    assert "close" in result.message
    assert not state.process_cleanup_safe

    monkeypatch.undo()
    state = _state(tmp_path / "teardown")
    state.base_sha = "a" * 40
    process = _FakeProcess([subprocess.TimeoutExpired("x", 1)])
    primary = MemoryError("teardown")
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _process(process),
    )
    monkeypatch.setattr(
        workspace_module,
        "_teardown_process",
        lambda *_args: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(MemoryError) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert not state.process_cleanup_safe
    assert any("retained" in note for note in primary.__notes__)


def test_run_command_multiple_close_failures_and_primary_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    state.base_sha = "a" * 40
    first = OSError("first close")
    second = OSError("second close")
    outputs = iter((_Output(first), _Output(second)))
    monkeypatch.setattr(
        workspace_module.tempfile, "TemporaryFile", lambda **_kwargs: next(outputs)
    )
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("start")),
    )
    result = workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert "second close" in result.message
    assert any("first close" in note for note in second.__notes__)

    monkeypatch.undo()
    state = _state(tmp_path / "primary")
    primary = KeyboardInterrupt()
    outputs = iter((_Output(OSError("close")), _Output()))
    monkeypatch.setattr(
        workspace_module.tempfile, "TemporaryFile", lambda **_kwargs: next(outputs)
    )
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(primary),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is primary
    assert any("output spool" in note for note in primary.__notes__)

    monkeypatch.undo()
    state = _state(tmp_path / "close-primary")
    state.base_sha = "a" * 40
    close_primary = MemoryError("close")
    outputs = iter((_Output(close_primary), _Output()))
    monkeypatch.setattr(
        workspace_module.tempfile, "TemporaryFile", lambda **_kwargs: next(outputs)
    )
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("start")),
    )
    with pytest.raises(MemoryError) as raised:
        workspace_module._run_command(("x",), state, {}, 1, 0.1)
    assert raised.value is close_primary
    assert any("retained" in note for note in close_primary.__notes__)


def test_run_command_asserts_result_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    monkeypatch.setattr(
        workspace_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("start")),
    )
    monkeypatch.setattr(workspace_module, "WorkspaceResult", lambda *_args: None)
    with pytest.raises(AssertionError, match="produced no result"):
        workspace_module._run_command(("x",), state, {}, 1, 0.1)


def test_cleanup_worktree_error_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    state.registration = Registration.PRESENT
    monkeypatch.setattr(
        workspace_module,
        "_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(workspace_module._WorkspaceError("remove")),
    )
    monkeypatch.setattr(workspace_module, "_worktree_registered", lambda *_args: False)
    workspace_module._cleanup_worktree(state, {})
    assert state.registration is Registration.ABSENT

    state.registration = Registration.PRESENT
    monkeypatch.setattr(workspace_module, "_git", lambda *_args, **_kwargs: _completed())
    monkeypatch.setattr(workspace_module, "_worktree_registered", lambda *_args: True)
    with pytest.raises(Exception, match="retained") as raised:
        workspace_module._cleanup_worktree(state, {})
    assert raised.value.__cause__ is None


def test_cleanup_result_without_pending_and_note_failure(tmp_path: Path) -> None:
    result = workspace_module._cleanup_result(None, "failed", tmp_path, None)
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert result.command_exit is None

    class NoteFailure(Exception):
        def add_note(self, note: str) -> None:
            del note
            raise MemoryError

    workspace_module._add_exception_note(NoteFailure(), "ignored")


def _patch_workspace_setup(
    monkeypatch: pytest.MonkeyPatch,
    parent: Path,
    prepare: Any,
    run: Any,
) -> None:
    monkeypatch.setattr(workspace_module, "_local_env_vars", lambda _env: set())
    monkeypatch.setattr(workspace_module, "_git_protected_paths", lambda *_args: ())
    monkeypatch.setattr(workspace_module, "_safe_temp_parent", lambda _paths: parent)
    monkeypatch.setattr(workspace_module, "_prepare_repository", prepare)
    monkeypatch.setattr(workspace_module, "_run_command", run)


def test_run_workspace_cleanup_precedence_and_exception_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "owned"
    parent.mkdir()

    def prepare(_base: Path, state: workspace_module._WorkspaceState, _env: dict[str, str]) -> None:
        state.registration = Registration.PRESENT
        state.base_sha = "a" * 40

    def run(*_args: Any) -> WorkspaceResult:
        return WorkspaceResult(WorkspaceCode.OK, "ok", 7, "a" * 40)

    _patch_workspace_setup(monkeypatch, parent, prepare, run)
    monkeypatch.setattr(
        workspace_module,
        "_cleanup_worktree",
        lambda *_args: (_ for _ in ()).throw(workspace_module._CleanupError("locked")),
    )
    result = workspace_module.run_workspace(
        base=tmp_path, protected_paths=(), command=("x",), environment={}
    )
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert result.command_exit == 7
    assert result.retained_path == os.fspath(parent)

    monkeypatch.undo()
    shutil.rmtree(parent)
    parent.mkdir()
    primary = KeyboardInterrupt()

    def interrupt(_base: Path, state: workspace_module._WorkspaceState, _env: dict[str, str]) -> None:
        state.registration = Registration.PRESENT
        raise primary

    _patch_workspace_setup(monkeypatch, parent, interrupt, run)
    monkeypatch.setattr(
        workspace_module,
        "_cleanup_worktree",
        lambda *_args: (_ for _ in ()).throw(workspace_module._CleanupError("locked")),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )
    assert raised.value is primary
    assert any("locked" in note for note in primary.__notes__)


def test_run_workspace_secondary_baseexceptions_and_parent_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "owned"
    parent.mkdir()

    def present(_base: Path, state: workspace_module._WorkspaceState, _env: dict[str, str]) -> None:
        state.registration = Registration.PRESENT

    def run(*_args: Any) -> WorkspaceResult:
        return WorkspaceResult(WorkspaceCode.OK, "ok", 0, "a" * 40)

    _patch_workspace_setup(monkeypatch, parent, present, run)
    cleanup_interrupt = KeyboardInterrupt()
    monkeypatch.setattr(
        workspace_module,
        "_cleanup_worktree",
        lambda *_args: (_ for _ in ()).throw(cleanup_interrupt),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )
    assert raised.value is cleanup_interrupt
    assert any(os.fspath(parent) in note for note in cleanup_interrupt.__notes__)

    monkeypatch.undo()
    shutil.rmtree(parent)
    parent.mkdir()
    _patch_workspace_setup(monkeypatch, parent, lambda *_args: None, run)
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("parent")),
    )
    result = workspace_module.run_workspace(
        base=tmp_path, protected_paths=(), command=("x",), environment={}
    )
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert "parent" in result.message

    monkeypatch.undo()
    parent.mkdir(exist_ok=True)
    parent_interrupt = KeyboardInterrupt()
    _patch_workspace_setup(monkeypatch, parent, lambda *_args: None, run)
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(parent_interrupt),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )
    assert raised.value is parent_interrupt
    assert any(os.fspath(parent) in note for note in parent_interrupt.__notes__)


@pytest.mark.parametrize("cleanup_error", [OSError("locked"), MemoryError("cleanup")])
def test_run_workspace_owns_parent_before_state_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: BaseException,
) -> None:
    parent = tmp_path / "owned"
    parent.mkdir()
    primary = MemoryError("state")
    monkeypatch.setattr(workspace_module, "_local_env_vars", lambda _env: set())
    monkeypatch.setattr(workspace_module, "_git_protected_paths", lambda *_args: ())
    monkeypatch.setattr(workspace_module, "_safe_temp_parent", lambda _paths: parent)
    monkeypatch.setattr(
        workspace_module,
        "_WorkspaceState",
        lambda **_kwargs: (_ for _ in ()).throw(primary),
    )
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(cleanup_error),
    )

    with pytest.raises(MemoryError) as raised:
        workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )

    assert raised.value is primary
    assert parent.exists()
    assert any(
        str(cleanup_error) in note and os.fspath(parent) in note
        for note in primary.__notes__
    )


@pytest.mark.parametrize("cleanup_error", [OSError("locked"), MemoryError("cleanup")])
def test_run_workspace_pre_state_operational_failure_keeps_cleanup_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: BaseException,
) -> None:
    parent = tmp_path / "owned"
    parent.mkdir()
    monkeypatch.setattr(workspace_module, "_local_env_vars", lambda _env: set())
    monkeypatch.setattr(workspace_module, "_git_protected_paths", lambda *_args: ())
    monkeypatch.setattr(workspace_module, "_safe_temp_parent", lambda _paths: parent)
    monkeypatch.setattr(
        workspace_module,
        "_WorkspaceState",
        lambda **_kwargs: (_ for _ in ()).throw(
            workspace_module._WorkspaceError("state")
        ),
    )
    monkeypatch.setattr(
        workspace_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(cleanup_error),
    )

    if isinstance(cleanup_error, OSError):
        result = workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )
        assert result.code is WorkspaceCode.CLEANUP_FAILED
        assert result.retained_path == os.fspath(parent)
    else:
        with pytest.raises(MemoryError) as raised:
            workspace_module.run_workspace(
                base=tmp_path, protected_paths=(), command=("x",), environment={}
            )
        assert raised.value is cleanup_error
        assert any(os.fspath(parent) in note for note in cleanup_error.__notes__)


def test_run_workspace_active_secondary_cleanup_failures_become_notes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "owned"
    parent.mkdir()
    primary = KeyboardInterrupt()

    def present_then_interrupt(
        _base: Path, state: workspace_module._WorkspaceState, _env: dict[str, str]
    ) -> None:
        state.registration = Registration.PRESENT
        raise primary

    _patch_workspace_setup(monkeypatch, parent, present_then_interrupt, lambda *_args: None)
    monkeypatch.setattr(
        workspace_module,
        "_cleanup_worktree",
        lambda *_args: (_ for _ in ()).throw(MemoryError("secondary")),
    )
    with pytest.raises(KeyboardInterrupt) as raised:
        workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )
    assert raised.value is primary
    assert any("MemoryError" in note for note in primary.__notes__)

    for cleanup_error in (OSError("parent-os"), MemoryError("parent-memory")):
        monkeypatch.undo()
        shutil.rmtree(parent)
        parent.mkdir()
        primary = KeyboardInterrupt()
        _patch_workspace_setup(
            monkeypatch,
            parent,
            lambda *_args, selected=primary: (_ for _ in ()).throw(selected),
            lambda *_args: None,
        )
        monkeypatch.setattr(
            workspace_module.shutil,
            "rmtree",
            lambda _path, selected=cleanup_error: (_ for _ in ()).throw(selected),
        )
        with pytest.raises(KeyboardInterrupt) as raised:
            workspace_module.run_workspace(
                base=tmp_path, protected_paths=(), command=("x",), environment={}
            )
        assert raised.value is primary
        assert any("parent" in note for note in primary.__notes__)


def test_run_workspace_setup_failure_before_state_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        workspace_module,
        "_local_env_vars",
        lambda _env: (_ for _ in ()).throw(workspace_module._WorkspaceError("git unavailable")),
    )
    result = workspace_module.run_workspace(
        base=tmp_path, protected_paths=(), command=("x",), environment={}
    )
    assert result.code is WorkspaceCode.WORKSPACE_FAILED
    assert result.message == "git unavailable"


def test_run_workspace_reports_pre_state_retained_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    retained = tmp_path / "retained"
    retained.mkdir()
    monkeypatch.setattr(workspace_module, "_local_env_vars", lambda _env: set())
    monkeypatch.setattr(workspace_module, "_git_protected_paths", lambda *_args: ())
    monkeypatch.setattr(
        workspace_module,
        "_safe_temp_parent",
        lambda _paths: (_ for _ in ()).throw(
            workspace_module._RetainedCleanupError("cleanup failed", retained)
        ),
    )
    result = workspace_module.run_workspace(
        base=tmp_path, protected_paths=(), command=("x",), environment={}
    )
    assert result.code is WorkspaceCode.CLEANUP_FAILED
    assert result.retained_path == os.fspath(retained)


def test_run_workspace_asserts_result_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "owned"
    parent.mkdir()
    _patch_workspace_setup(
        monkeypatch,
        parent,
        lambda *_args: None,
        lambda *_args: None,
    )
    with pytest.raises(AssertionError, match="produced no result"):
        workspace_module.run_workspace(
            base=tmp_path, protected_paths=(), command=("x",), environment={}
        )
