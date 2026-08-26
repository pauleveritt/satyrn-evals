"""Eval-owned synthetic repository and detached attempt worktree.

The task base is persisted as files, not as a Git repository.  V4 rebuilds a
private repository for one attempt, runs the trusted command once in a
detached linked worktree, and removes both only after Git confirms that the
registration is gone.
"""

import contextlib
import hashlib
import math
import os
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from pathlib import Path
from typing import BinaryIO

DEFAULT_TIMEOUT = 30.0
DEFAULT_TEARDOWN_GRACE = 0.25

_GIT_SAFETY_CONFIG = (
    "--no-replace-objects",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.symlinks=true",
)
_FIXED_GIT_ENV = {
    "GIT_AUTHOR_NAME": "satyrn-evals",
    "GIT_AUTHOR_EMAIL": "satyrn-evals@localhost",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
    "GIT_COMMITTER_NAME": "satyrn-evals",
    "GIT_COMMITTER_EMAIL": "satyrn-evals@localhost",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
}


class WorkspaceCode(StrEnum):
    """Typed outcomes from the workspace boundary."""

    OK = "OK"
    WORKSPACE_FAILED = "WORKSPACE_FAILED"
    COMMAND_UNAVAILABLE = "COMMAND_UNAVAILABLE"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    CLEANUP_FAILED = "CLEANUP_FAILED"


class Registration(Enum):
    """Whether the synthetic repository may retain a linked worktree."""

    ABSENT = auto()
    MAY_EXIST = auto()
    PRESENT = auto()


class TreeKind(StrEnum):
    """Git-representable filesystem entry kinds used by base verification."""

    REGULAR = "regular"
    EXECUTABLE = "executable"
    SYMLINK = "symlink"


class _Presence(Enum):
    REQUIRED = auto()
    FORBIDDEN = auto()
    OPTIONAL = auto()


@dataclass(frozen=True, slots=True)
class _WorkspacePolicy:
    command_exit: _Presence
    base_sha: _Presence
    retained_path: _Presence


_WORKSPACE_POLICIES: dict[WorkspaceCode, _WorkspacePolicy] = {
    WorkspaceCode.OK: _WorkspacePolicy(
        _Presence.REQUIRED, _Presence.REQUIRED, _Presence.FORBIDDEN
    ),
    WorkspaceCode.WORKSPACE_FAILED: _WorkspacePolicy(
        _Presence.FORBIDDEN, _Presence.OPTIONAL, _Presence.FORBIDDEN
    ),
    WorkspaceCode.COMMAND_UNAVAILABLE: _WorkspacePolicy(
        _Presence.FORBIDDEN, _Presence.REQUIRED, _Presence.FORBIDDEN
    ),
    WorkspaceCode.COMMAND_TIMEOUT: _WorkspacePolicy(
        _Presence.FORBIDDEN, _Presence.REQUIRED, _Presence.FORBIDDEN
    ),
    WorkspaceCode.CLEANUP_FAILED: _WorkspacePolicy(
        _Presence.OPTIONAL, _Presence.OPTIONAL, _Presence.REQUIRED
    ),
}


@dataclass(frozen=True, slots=True, order=True)
class TreeEntry:
    """One task-base entry, compared before the command can run."""

    path: str
    kind: TreeKind
    value: str


@dataclass(frozen=True, slots=True)
class WorkspaceResult:
    """One workspace attempt result; command exit is absent before normal exit."""

    code: WorkspaceCode
    message: str
    command_exit: int | None
    base_sha: str | None
    retained_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", WorkspaceCode(self.code))
        policy = _WORKSPACE_POLICIES[self.code]
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("workspace result message must be a non-empty string")
        if self.command_exit is not None and type(self.command_exit) is not int:
            raise ValueError("workspace command_exit must be an integer or null")
        for name, value in (
            ("base_sha", self.base_sha),
            ("retained_path", self.retained_path),
        ):
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"workspace {name} must be a non-empty string or null")
        if self.base_sha is not None and not (
            _hex_object_id(self.base_sha, 40) or _hex_object_id(self.base_sha, 64)
        ):
            raise ValueError("workspace base_sha must be a Git object ID or null")
        if policy.command_exit is _Presence.REQUIRED and self.command_exit is None:
            raise ValueError(f"{self.code} workspace result requires command_exit")
        if policy.command_exit is _Presence.FORBIDDEN and self.command_exit is not None:
            raise ValueError(f"{self.code} workspace result requires null command_exit")
        if policy.base_sha is _Presence.REQUIRED and self.base_sha is None:
            raise ValueError(f"{self.code} workspace result requires base_sha")
        if policy.retained_path is _Presence.REQUIRED and self.retained_path is None:
            raise ValueError(f"{self.code} requires retained_path")
        if policy.retained_path is _Presence.FORBIDDEN and self.retained_path is not None:
            raise ValueError("only CLEANUP_FAILED may retain a path")


def _hex_object_id(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


@dataclass(slots=True)
class _WorkspaceState:
    parent: Path
    repository: Path
    worktree: Path
    registration: Registration = Registration.ABSENT
    process_cleanup_safe: bool = True
    base_sha: str | None = None

    def begin_add(self) -> None:
        if self.registration is not Registration.ABSENT:
            raise AssertionError("worktree add started from a non-absent state")
        self.registration = Registration.MAY_EXIST

    def observe_registration(self, registered: bool | None) -> None:
        match registered:
            case True:
                self.registration = Registration.PRESENT
            case False:
                self.registration = Registration.ABSENT
            case None:
                self.registration = Registration.MAY_EXIST
            case _:
                raise AssertionError(f"unexpected registration state: {registered!r}")


class _WorkspaceError(Exception):
    """Predictable setup failure converted to WORKSPACE_FAILED."""


class _CleanupError(Exception):
    """Cleanup could not prove that recursive deletion is safe."""


def _retained_workspace(state: _WorkspaceState) -> str:
    """Describe the retained parent and the command worktree it contains."""
    return f"workspace parent retained at {state.parent}; command worktree {state.worktree}"


class _RetainedCleanupError(_CleanupError):
    """Cleanup failed before workspace state existed; retain the named path."""

    def __init__(self, message: str, retained_path: Path) -> None:
        super().__init__(message)
        self.retained_path = retained_path


def clean_environment(
    environment: Mapping[str, str], routing_names: Iterable[str]
) -> dict[str, str]:
    """Copy an environment while removing Git's repository-routing state."""
    cleaned = dict(environment)
    for name in routing_names:
        cleaned.pop(name, None)
    cleaned.pop("GIT_NAMESPACE", None)
    cleaned["GIT_TERMINAL_PROMPT"] = "0"
    cleaned["GIT_NO_REPLACE_OBJECTS"] = "1"
    cleaned["GIT_GRAFT_FILE"] = os.devnull
    return cleaned


def snapshot_tree(root: Path) -> tuple[TreeEntry, ...]:
    """Return Git-representable entries without following symbolic links."""
    root = root.resolve()
    if not root.is_dir():
        raise _WorkspaceError(f"task base is not a directory: {root}")
    entries: list[TreeEntry] = []

    def visit(directory: Path) -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda entry: os.fsencode(entry.name))
        except OSError as exc:
            raise _WorkspaceError(f"cannot enumerate task base {directory}: {exc}") from exc
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(root)
            if relative.parts == (".git",):
                continue
            try:
                mode = child.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    value = os.readlink(path)
                    entries.append(TreeEntry(relative.as_posix(), TreeKind.SYMLINK, value))
                elif stat.S_ISDIR(mode):
                    visit(path)
                elif stat.S_ISREG(mode):
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    kind = TreeKind.EXECUTABLE if mode & 0o111 else TreeKind.REGULAR
                    entries.append(TreeEntry(relative.as_posix(), kind, digest))
                else:
                    raise _WorkspaceError(
                        f"task base contains unsupported file type: {relative.as_posix()}"
                    )
            except OSError as exc:
                raise _WorkspaceError(f"cannot inspect task base entry {relative}: {exc}") from exc
    visit(root)
    return tuple(entries)


def _contains_path(root: Path, path: Path) -> bool:
    """Whether path is root/descendant, including existing casing aliases."""

    def strictly_exists(candidate: Path) -> bool:
        try:
            candidate.stat()
        except FileNotFoundError:
            return False
        return True

    try:
        root_resolved = root.resolve()
        cursor = path.resolve()
        if cursor.is_relative_to(root_resolved):
            return True
        root_exists = strictly_exists(root_resolved)
        while cursor != cursor.parent:
            if root_exists and strictly_exists(cursor) and cursor.samefile(root_resolved):
                return True
            cursor = cursor.parent
        return False
    except (OSError, ValueError) as exc:
        raise _WorkspaceError(
            f"cannot compare path identity for {path} against {root}: {exc}"
        ) from exc


def _safe_temp_parent(protected: Sequence[Path]) -> Path:
    """Allocate outside task/output roots without trusting inherited TMPDIR."""
    candidate_roots = dict.fromkeys(
        (Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"))
    )
    failures: list[str] = []
    protected_roots = tuple(path.resolve() for path in protected)
    for candidate_root in candidate_roots:
        candidate_root = candidate_root.resolve()
        if any(_contains_path(root, candidate_root) for root in protected_roots):
            failures.append(f"{candidate_root}: inside a protected path")
            continue
        try:
            allocated = Path(
                tempfile.mkdtemp(prefix="satyrn-attempt-", dir=candidate_root)
            )
        except OSError as exc:
            failures.append(f"{candidate_root}: {exc}")
            continue
        try:
            parent = allocated.resolve()
        except OSError as exc:
            try:
                shutil.rmtree(allocated)
            except OSError as cleanup_error:
                raise _RetainedCleanupError(
                    "temporary directory resolution and cleanup failed: "
                    f"{exc}; retained at {allocated}: {cleanup_error}",
                    allocated,
                ) from cleanup_error
            except BaseException as cleanup_error:
                _add_exception_note(
                    cleanup_error,
                    "temporary directory resolution failed: "
                    f"{exc}; retained at {allocated}",
                )
                raise
            failures.append(f"{candidate_root}: cannot resolve allocation: {exc}")
            continue
        except BaseException as exc:
            try:
                shutil.rmtree(allocated)
            except BaseException as cleanup_error:
                _add_exception_note(
                    exc,
                    "temporary directory cleanup raised "
                    f"{type(cleanup_error).__name__}: {cleanup_error}; "
                    f"retained at {allocated}",
                )
            raise
        try:
            unsafe = any(_contains_path(root, parent) for root in protected_roots)
        except (OSError, _WorkspaceError) as exc:
            try:
                shutil.rmtree(parent)
            except OSError as cleanup_error:
                raise _RetainedCleanupError(
                    "temporary directory validation and cleanup failed: "
                    f"{exc}; retained at {parent}: {cleanup_error}",
                    parent,
                ) from cleanup_error
            except BaseException as cleanup_error:
                _add_exception_note(
                    cleanup_error,
                    f"temporary directory validation failed: {exc}; retained at {parent}",
                )
                raise
            failures.append(f"{candidate_root}: cannot validate allocation: {exc}")
            continue
        except BaseException as exc:
            try:
                shutil.rmtree(parent)
            except BaseException as cleanup_error:
                _add_exception_note(
                    exc,
                    "temporary directory cleanup raised "
                    f"{type(cleanup_error).__name__}: {cleanup_error}; "
                    f"retained at {parent}",
                )
            raise
        if unsafe:
            try:
                shutil.rmtree(parent)
            except OSError as exc:
                raise _RetainedCleanupError(
                    f"unsafe temporary directory cleanup failed; retained at {parent}: {exc}",
                    parent,
                ) from exc
            except BaseException as exc:
                _add_exception_note(
                    exc,
                    f"unsafe temporary directory retained at {parent}",
                )
                raise
            failures.append(f"{candidate_root}: inside a protected path")
            continue
        return parent
    detail = "; ".join(failures) or "no candidate temporary directory"
    raise _WorkspaceError(f"cannot allocate a safe temporary directory: {detail}")


def _local_env_vars(environment: Mapping[str, str]) -> set[str]:
    """Ask Git which variables can redirect repository discovery."""
    probe_environment = {
        name: value for name, value in environment.items() if not name.startswith("GIT_")
    }
    probe_environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            ["git", *_GIT_SAFETY_CONFIG, "rev-parse", "--local-env-vars"],
            env=probe_environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise _WorkspaceError(f"cannot inspect Git environment variables: {exc}") from exc
    if completed.returncode != 0:
        detail = os.fsdecode(completed.stderr).strip()
        raise _WorkspaceError(f"cannot inspect Git environment variables: {detail}")
    return set(os.fsdecode(completed.stdout).split())


def _git(
    root: Path,
    args: Sequence[str],
    environment: Mapping[str, str],
    *,
    input_bytes: bytes | None = None,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    """Run one eval-owned Git command with the shared safety boundary."""
    try:
        completed = subprocess.run(
            ["git", *_GIT_SAFETY_CONFIG, *args],
            cwd=root,
            env=dict(environment),
            stdin=subprocess.DEVNULL if input_bytes is None else None,
            input=input_bytes,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise _WorkspaceError(f"cannot run git {' '.join(args)}: {exc}") from exc
    if completed.returncode not in allowed:
        detail = os.fsdecode(completed.stderr).strip()
        raise _WorkspaceError(f"git {' '.join(args)} failed: {detail}")
    return completed


def _registered_worktrees(
    repository: Path, environment: Mapping[str, str]
) -> tuple[Path, ...]:
    output = _git(
        repository,
        ("worktree", "list", "--porcelain", "-z"),
        environment,
    ).stdout
    fields = os.fsdecode(output).split("\0")
    return tuple(
        Path(field.removeprefix("worktree ")).resolve()
        for field in fields
        if field.startswith("worktree ")
    )


def _git_protected_paths(
    paths: Sequence[Path], environment: Mapping[str, str]
) -> tuple[Path, ...]:
    """Discover enclosing Git worktrees and administration directories."""
    protected: dict[Path, None] = {}
    inspected: set[Path] = set()
    repositories: set[Path] = set()
    for path in paths:
        cursor = path.resolve()
        while not cursor.exists() and cursor != cursor.parent:
            cursor = cursor.parent
        if cursor.exists() and not cursor.is_dir():
            cursor = cursor.parent
        if cursor in inspected:
            continue
        inspected.add(cursor)
        while True:
            top_result = _git(
                cursor,
                ("rev-parse", "--show-toplevel"),
                environment,
                allowed=(0, 128),
            )
            top = (
                Path(os.fsdecode(top_result.stdout).removesuffix("\n")).resolve()
                if top_result.returncode == 0
                else None
            )
            git_dir_result = _git(
                cursor,
                ("rev-parse", "--absolute-git-dir"),
                environment,
                allowed=(0, 128),
            )
            if git_dir_result.returncode != 0:
                break
            git_dir = Path(
                os.fsdecode(git_dir_result.stdout).removesuffix("\n")
            ).resolve()
            repository = top if top is not None else git_dir
            if repository in repositories:
                break
            repositories.add(repository)
            if top is not None:
                protected[top] = None
            protected[git_dir] = None
            raw_common = Path(
                os.fsdecode(
                    _git(cursor, ("rev-parse", "--git-common-dir"), environment).stdout
                ).removesuffix("\n")
            )
            common = (
                raw_common.resolve()
                if raw_common.is_absolute()
                else (cursor / raw_common).resolve()
            )
            protected[common] = None
            for worktree in _registered_worktrees(repository, environment):
                protected[worktree] = None
            if repository == repository.parent:
                break
            cursor = repository.parent
    return tuple(protected)


def _worktree_registered(
    repository: Path, worktree: Path, environment: Mapping[str, str]
) -> bool | None:
    try:
        registered = _registered_worktrees(repository, environment)
    except _WorkspaceError:
        return None
    return worktree.resolve() in registered


def _prepare_repository(
    base: Path,
    state: _WorkspaceState,
    environment: Mapping[str, str],
) -> None:
    if os.path.lexists(base / ".git"):
        raise _WorkspaceError("task base must not contain top-level .git metadata")
    expected = snapshot_tree(base)
    try:
        state.repository.mkdir()
    except OSError as exc:
        raise _WorkspaceError(
            f"cannot create synthetic repository directory: {exc}"
        ) from exc
    try:
        shutil.copytree(base, state.repository, symlinks=True, dirs_exist_ok=True)
    except OSError as exc:
        raise _WorkspaceError(f"cannot copy task base into synthetic repository: {exc}") from exc
    _git(state.repository, ("init", "-q"), environment)
    _git(state.repository, ("config", "commit.gpgSign", "false"), environment)
    _git(state.repository, ("config", "core.hooksPath", os.devnull), environment)
    _git(state.repository, ("config", "core.fsmonitor", "false"), environment)
    _git(state.repository, ("config", "core.symlinks", "true"), environment)
    _git(state.repository, ("add", "--force", "--all"), environment)
    tree = os.fsdecode(_git(state.repository, ("write-tree",), environment).stdout).removesuffix("\n")
    commit_env = dict(environment)
    commit_env.update(_FIXED_GIT_ENV)
    commit = os.fsdecode(
        _git(
            state.repository,
            ("commit-tree", tree),
            commit_env,
            input_bytes=b"satyrn-evals synthetic base\n",
        ).stdout
    ).removesuffix("\n")
    _git(
        state.repository,
        ("symbolic-ref", "HEAD", "refs/heads/satyrn-base"),
        environment,
    )
    _git(
        state.repository,
        ("update-ref", "refs/heads/satyrn-base", commit),
        environment,
    )
    state.base_sha = commit
    state.begin_add()
    _git(
        state.repository,
        (
            "-c",
            "core.sparseCheckout=false",
            "worktree",
            "add",
            "--detach",
            os.fspath(state.worktree),
            commit,
        ),
        environment,
    )
    state.observe_registration(
        _worktree_registered(state.repository, state.worktree, environment)
    )
    if state.registration is not Registration.PRESENT:
        raise _WorkspaceError("Git did not confirm the attempt worktree registration")
    head = os.fsdecode(
        _git(state.worktree, ("rev-parse", "--verify", "HEAD^{commit}"), environment).stdout
    ).removesuffix("\n")
    symbolic = _git(
        state.worktree,
        ("symbolic-ref", "--quiet", "HEAD"),
        environment,
        allowed=(0, 1),
    )
    if head != commit or symbolic.returncode != 1:
        raise _WorkspaceError("attempt worktree is not detached at the synthetic base")
    status_result = _git(
        state.worktree,
        (
            "--no-optional-locks",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        ),
        environment,
    )
    if status_result.stdout:
        raise _WorkspaceError("attempt worktree is not clean at the synthetic base")
    actual = snapshot_tree(state.worktree)
    if actual != expected:
        raise _WorkspaceError("Git materialization does not match the persisted task base")


def _group_gone(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def _is_posix() -> bool:
    return os.name == "posix"


def _wait_until_group_gone(process_group: int, deadline: float) -> bool:
    while time.monotonic() < deadline:
        if _group_gone(process_group):
            return True
        time.sleep(0.01)
    return _group_gone(process_group)


def _teardown_process(
    process: subprocess.Popen[bytes], grace: float
) -> tuple[bool, str | None]:
    """Best-effort bounded teardown; safe means child reaped and group gone."""
    details: list[str] = []
    if _is_posix():
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as exc:
            details.append(f"cannot signal process group with SIGTERM: {exc}")
        gone = _wait_until_group_gone(process.pid, time.monotonic() + grace)
        if not gone:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as exc:
                details.append(f"cannot signal process group with SIGKILL: {exc}")
    else:  # Windows is a direct-child fallback, not part of V4's proof.
        try:
            process.terminate()
        except OSError as exc:
            details.append(f"cannot terminate command: {exc}")
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError as exc:
                details.append(f"cannot kill command: {exc}")
    reaped = True
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        reaped = False
        details.append("direct child was not reaped")
    except OSError as exc:
        reaped = False
        details.append(f"cannot reap direct child: {exc}")
    gone = (
        _wait_until_group_gone(process.pid, time.monotonic() + grace)
        if _is_posix()
        else reaped
    )
    if not gone:
        details.append("process group disappearance is unconfirmed")
    return reaped and gone, "; ".join(details) or None


def _run_command(
    command: Sequence[str],
    state: _WorkspaceState,
    environment: Mapping[str, str],
    timeout: float,
    teardown_grace: float,
) -> WorkspaceResult:
    outputs: list[BinaryIO] = []
    pending: WorkspaceResult | None = None
    active_exception: BaseException | None = None
    try:
        for _ in range(2):
            outputs.append(
                tempfile.TemporaryFile(  # noqa: SIM115 - explicit cleanup is required
                    dir=state.parent
                )
            )
        state.process_cleanup_safe = False
        try:
            process = subprocess.Popen(
                command,
                cwd=state.worktree,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=outputs[0],
                stderr=outputs[1],
                start_new_session=_is_posix(),
            )
        except OSError as exc:
            state.process_cleanup_safe = True
            pending = WorkspaceResult(
                WorkspaceCode.COMMAND_UNAVAILABLE,
                f"attempt command cannot start: {exc}",
                None,
                state.base_sha,
            )
        except BaseException as exc:
            _add_exception_note(
                exc,
                f"command start is unconfirmed; {_retained_workspace(state)}",
            )
            raise
        else:
            try:
                command_exit = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    safe, detail = _teardown_process(process, teardown_grace)
                except BaseException as exc:
                    active_exception = exc
                    _add_exception_note(
                        exc,
                        f"process cleanup is unconfirmed; {_retained_workspace(state)}",
                    )
                    raise
                state.process_cleanup_safe = safe
                pending = (
                    WorkspaceResult(
                        WorkspaceCode.COMMAND_TIMEOUT,
                        f"attempt command exceeded {timeout:g} seconds",
                        None,
                        state.base_sha,
                    )
                    if safe
                    else WorkspaceResult(
                        WorkspaceCode.CLEANUP_FAILED,
                        f"command timeout cleanup is unconfirmed: {detail}",
                        None,
                        state.base_sha,
                        os.fspath(state.parent),
                    )
                )
            except BaseException as exc:
                active_exception = exc
                try:
                    safe, detail = _teardown_process(process, teardown_grace)
                except BaseException as cleanup_error:
                    _add_exception_note(
                        exc,
                        "process cleanup raised "
                        f"{type(cleanup_error).__name__}: {cleanup_error}; "
                        f"{_retained_workspace(state)}",
                    )
                else:
                    state.process_cleanup_safe = safe
                    if not safe:
                        _add_exception_note(
                            exc,
                            f"process cleanup unconfirmed: {detail}; {_retained_workspace(state)}",
                        )
                raise
            else:
                # COMMAND is explicitly synchronous at this V4 boundary.
                state.process_cleanup_safe = True
                pending = WorkspaceResult(
                    WorkspaceCode.OK,
                    "attempt command completed",
                    command_exit,
                    state.base_sha,
                )
    except OSError as exc:
        if active_exception is exc:
            raise
        pending = WorkspaceResult(
            WorkspaceCode.WORKSPACE_FAILED,
            f"cannot prepare command output spool: {exc}",
            None,
            state.base_sha,
        )
    except BaseException as exc:
        active_exception = exc
        raise
    finally:
        close_error: BaseException | None = None
        while outputs:
            output = outputs.pop()
            try:
                output.close()
            except BaseException as exc:
                if close_error is None:
                    close_error = exc
                else:
                    _add_exception_note(
                        close_error,
                        f"additional output spool close failure: {type(exc).__name__}: {exc}",
                    )
        if close_error is not None:
            state.process_cleanup_safe = False
            detail = (
                "cannot close command output spool: "
                f"{type(close_error).__name__}: {close_error}; "
                f"{_retained_workspace(state)}"
            )
            if active_exception is not None:
                _add_exception_note(active_exception, detail)
            elif isinstance(close_error, OSError):
                pending = _cleanup_result(
                    pending,
                    detail,
                    state.parent,
                    state.base_sha,
                )
            else:
                _add_exception_note(close_error, detail)
                raise close_error
    if pending is None:
        raise AssertionError("command execution produced no result")
    return pending


def _cleanup_worktree(
    state: _WorkspaceState, environment: Mapping[str, str]
) -> None:
    remove_error: _WorkspaceError | None = None
    try:
        _git(
            state.repository,
            ("worktree", "remove", "--force", os.fspath(state.worktree)),
            environment,
        )
    except _WorkspaceError as exc:
        remove_error = exc
    state.observe_registration(
        _worktree_registered(state.repository, state.worktree, environment)
    )
    if state.registration is not Registration.ABSENT:
        detail = f": {remove_error}" if remove_error is not None else ""
        raise _CleanupError(
            f"worktree cleanup unconfirmed for {state.worktree}; "
            f"{_retained_workspace(state)}{detail}"
        ) from remove_error


def _cleanup_result(
    pending: WorkspaceResult | None,
    detail: str,
    retained_path: Path,
    base_sha: str | None,
) -> WorkspaceResult:
    prior = f" after {pending.code}" if pending is not None else ""
    command_exit = pending.command_exit if pending is not None else None
    return WorkspaceResult(
        WorkspaceCode.CLEANUP_FAILED,
        f"cleanup failed{prior}: {detail}",
        command_exit,
        base_sha,
        os.fspath(retained_path),
    )


def _add_exception_note(error: BaseException, note: str) -> None:
    with contextlib.suppress(BaseException):
        error.add_note(note)


def run_workspace(
    *,
    base: Path,
    protected_paths: Sequence[Path],
    command: Sequence[str],
    environment: Mapping[str, str],
    timeout: float = DEFAULT_TIMEOUT,
    teardown_grace: float = DEFAULT_TEARDOWN_GRACE,
) -> WorkspaceResult:
    """Run ``command`` once in a reconstructed detached Git worktree."""
    if not command:
        raise ValueError("workspace command is empty")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("workspace timeout must be a finite number greater than zero")
    if not math.isfinite(teardown_grace) or teardown_grace <= 0:
        raise ValueError(
            "workspace teardown grace must be a finite number greater than zero"
        )
    pending: WorkspaceResult | None = None
    active_exception: BaseException | None = None
    state: _WorkspaceState | None = None
    parent: Path | None = None
    git_environment: dict[str, str] | None = None
    try:
        routing_names = _local_env_vars(environment)
        git_environment = clean_environment(environment, routing_names)
        requested_protected = (base, *protected_paths)
        git_protected = _git_protected_paths(requested_protected, git_environment)
        parent = _safe_temp_parent((*requested_protected, *git_protected))
        state = _WorkspaceState(
            parent=parent,
            repository=parent / "seed",
            worktree=parent / "worktree",
        )
        _prepare_repository(base, state, git_environment)
        pending = _run_command(
            command,
            state,
            git_environment,
            timeout,
            teardown_grace,
        )
    except _RetainedCleanupError as exc:
        pending = WorkspaceResult(
            WorkspaceCode.CLEANUP_FAILED,
            str(exc),
            None,
            state.base_sha if state is not None else None,
            os.fspath(exc.retained_path),
        )
    except _WorkspaceError as exc:
        pending = WorkspaceResult(
            WorkspaceCode.WORKSPACE_FAILED,
            str(exc),
            None,
            state.base_sha if state is not None else None,
        )
    except BaseException as exc:
        active_exception = exc
        raise
    finally:
        if state is not None and git_environment is not None:
            if state.process_cleanup_safe and state.registration is not Registration.ABSENT:
                try:
                    _cleanup_worktree(state, git_environment)
                except _CleanupError as exc:
                    if active_exception is not None:
                        _add_exception_note(active_exception, str(exc))
                    else:
                        pending = _cleanup_result(
                            pending,
                            str(exc),
                            state.parent,
                            state.base_sha,
                        )
                except BaseException as exc:
                    if active_exception is not None:
                        _add_exception_note(
                            active_exception,
                            "worktree cleanup raised "
                            f"{type(exc).__name__}: {exc}; {_retained_workspace(state)}",
                        )
                    else:
                        _add_exception_note(
                            exc,
                            _retained_workspace(state),
                        )
                        raise
            if state.process_cleanup_safe and state.registration is Registration.ABSENT:
                try:
                    shutil.rmtree(state.parent)
                except OSError as exc:
                    if active_exception is not None:
                        _add_exception_note(
                            active_exception,
                            f"cannot remove workspace parent {state.parent}: {exc}",
                        )
                    else:
                        pending = _cleanup_result(
                            pending,
                            f"cannot remove workspace parent {state.parent}: {exc}",
                            state.parent,
                            state.base_sha,
                        )
                except BaseException as exc:
                    if active_exception is not None:
                        _add_exception_note(
                            active_exception,
                            f"workspace parent cleanup raised {type(exc).__name__}: {exc}; retained at {state.parent}",
                        )
                    else:
                        _add_exception_note(
                            exc,
                            f"workspace parent retained at {state.parent}",
                        )
                        raise
        elif parent is not None:
            try:
                shutil.rmtree(parent)
            except OSError as exc:
                if active_exception is not None:
                    _add_exception_note(
                        active_exception,
                        f"cannot remove workspace parent {parent}: {exc}; retained",
                    )
                else:
                    pending = _cleanup_result(
                        pending,
                        f"cannot remove workspace parent {parent}: {exc}",
                        parent,
                        None,
                    )
            except BaseException as exc:
                if active_exception is not None:
                    _add_exception_note(
                        active_exception,
                        "workspace parent cleanup raised "
                        f"{type(exc).__name__}: {exc}; retained at {parent}",
                    )
                else:
                    _add_exception_note(exc, f"workspace parent retained at {parent}")
                    raise
    if pending is None:
        raise AssertionError("workspace produced no result")
    return pending
