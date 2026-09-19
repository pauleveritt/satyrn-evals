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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum, StrEnum, auto
from pathlib import Path
from typing import BinaryIO

from satyrn_evals.attempt_record import DeadlinePhase
from satyrn_evals.budget import (
    AttemptBudget,
    BudgetTripwire,
    LineBudget,
    LineCrossing,
    LineTripwire,
)
from satyrn_evals.cell import (
    CELLS_ROOT,
    Isolation,
    cell_gitconfig,
    cell_paths,
    grant_maintainer,
    kill_cell_group,
    share_with_cell,
)
from satyrn_evals.deadline import AttemptDeadline, AttemptDeadlineExceeded
from satyrn_evals.errors import OracleError, OverlayError, SatyrnError
from satyrn_evals.overlay import OverlaySpec, assert_overlay_absent
from satyrn_evals.repeat_limit import RepeatTripwire
from satyrn_evals.timeline import TimelineWriter

DEFAULT_TIMEOUT = 900.0
# 900 s = the corrected probes' observed per-cell ceiling (2-15 min).
# Longer paths pass --timeout explicitly.
DEFAULT_TEARDOWN_GRACE = 0.25
#: F6/R13: the cell-side kill (`cell.kill_cell_group`, a second sudo call)
#: needs its own floor independent of the teardown grace -- a small grace
#: (the default is 0.25s) left ``max(remaining(), 0.05)`` at ~0.125s under a
#: slow sudo, which reported CLEANUP_FAILED and retained the workspace.
CELL_KILL_TIMEOUT_FLOOR = 2.0
#: Where a BUDGET_EXCEEDED teardown leaves the worktree's cumulative diff
#: (design section 3.2). Written beside the attempt's own artifacts.
TRIPPED_PATCH_NAME = "tripped.diff"
#: Ruling R-2: the teardown harvest is bounded. A wedged git (an index lock,
#: a filesystem stall) must never hold the cell open past its deadline, so
#: the cumulative-patch build gets this per-call ceiling. A timeout is a
#: missing secondary, never a lost cell: `_harvest_tripped` swallows it.
TRIPPED_HARVEST_TIMEOUT_S = 30.0
#: Where a declared-line crossing's harvest is written (release-two line
#: harvest). Written beside the attempt's own artifacts, alongside (never
#: instead of) `tripped.diff`.
LINE_PATCH_NAME = "line.diff"
#: Same ceiling as the tripped harvest (Ruling R-2's reasoning applies
#: identically): a wedged git must never hold a still-running cell's harness
#: thread open, and a slow harvest is a missing secondary, not a lost cell.
LINE_HARVEST_TIMEOUT_S = 30.0

_GIT_SAFETY_CONFIG = (
    "--no-replace-objects",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.symlinks=true",
)
GIT_SAFETY_CONFIG = (
    _GIT_SAFETY_CONFIG  # V9: grade.py reuses the workspace git discipline
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
    REPEAT_LIMIT = "REPEAT_LIMIT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
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
    WorkspaceCode.REPEAT_LIMIT: _WorkspacePolicy(
        # Torn down by the repeated-call spending rule, so the same shape
        # as a timeout: no exit code, a base_sha, nothing retained.
        _Presence.FORBIDDEN,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
    ),
    WorkspaceCode.BUDGET_EXCEEDED: _WorkspacePolicy(
        # Torn down live (no exit code), or observed over budget in the
        # lines the command wrote just before it exited (its exit code).
        _Presence.OPTIONAL,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
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
    #: The declared-line harvest (release two): set regardless of ``code`` --
    #: a cell can cross the line and still end at any outcome. ``None`` means
    #: the cell never crossed either line (or no line was declared).
    line_crossed: LineCrossing | None = None
    line_patch_written: bool = False
    line_harvest_error: str | None = None

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
        if (
            policy.retained_path is _Presence.FORBIDDEN
            and self.retained_path is not None
        ):
            raise ValueError("only CLEANUP_FAILED may retain a path")
        if self.line_crossed is not None and not isinstance(self.line_crossed, LineCrossing):
            raise ValueError("workspace line_crossed must be a LineCrossing or null")
        if type(self.line_patch_written) is not bool:
            raise ValueError("workspace line_patch_written must be a boolean")
        if self.line_harvest_error is not None and not (
            isinstance(self.line_harvest_error, str) and self.line_harvest_error
        ):
            raise ValueError("workspace line_harvest_error must be a non-empty string or null")
        if self.line_crossed is None and (
            self.line_patch_written or self.line_harvest_error is not None
        ):
            raise ValueError("workspace line_patch_written/line_harvest_error require line_crossed")
        if self.line_patch_written and self.line_harvest_error is not None:
            raise ValueError("workspace line result cannot both write a patch and record an error")


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
    isolation: Isolation = Isolation.LOCAL

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


def clean_git_environment(
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
    phase: DeadlinePhase = DeadlinePhase.SETUP,
) -> dict[str, str]:
    """Copy an environment minus Git's repository-routing state (T8).

    Probes the routing variables exactly as the workspace runner does
    (`git rev-parse --local-env-vars` under a GIT_-stripped environment)
    and removes them, pinning GIT_TERMINAL_PROMPT/GIT_NO_REPLACE_OBJECTS/
    GIT_GRAFT_FILE. Ambient GIT_DIR/GIT_INDEX_FILE/GIT_WORK_TREE must not
    redirect where evals' own git commands run.
    """
    try:
        routing_names = _local_env_vars(environment, deadline=deadline, phase=phase)
    except _WorkspaceError as exc:
        # A probe failure (git absent or misbehaving) is an operational
        # grading failure, not a workspace setup failure: grade()'s except
        # tuple turns OracleError into one UNAVAILABLE cell, so the batch
        # continues instead of aborting (B3).
        raise OracleError(str(exc)) from exc
    return clean_environment(environment, routing_names)


def snapshot_tree(root: Path) -> tuple[TreeEntry, ...]:
    """Return Git-representable entries without following symbolic links."""
    root = root.resolve()
    if not root.is_dir():
        raise _WorkspaceError(f"task base is not a directory: {root}")
    entries: list[TreeEntry] = []

    def visit(directory: Path) -> None:
        try:
            children = sorted(
                os.scandir(directory), key=lambda entry: os.fsencode(entry.name)
            )
        except OSError as exc:
            raise _WorkspaceError(
                f"cannot enumerate task base {directory}: {exc}"
            ) from exc
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(root)
            if relative.parts == (".git",):
                continue
            try:
                mode = child.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    value = os.readlink(path)
                    entries.append(
                        TreeEntry(relative.as_posix(), TreeKind.SYMLINK, value)
                    )
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
                raise _WorkspaceError(
                    f"cannot inspect task base entry {relative}: {exc}"
                ) from exc

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
            if (
                root_exists
                and strictly_exists(cursor)
                and cursor.samefile(root_resolved)
            ):
                return True
            cursor = cursor.parent
        return False
    except (OSError, ValueError) as exc:
        raise _WorkspaceError(
            f"cannot compare path identity for {path} against {root}: {exc}"
        ) from exc


def _safe_temp_parent(
    protected: Sequence[Path], roots: Sequence[Path] | None = None
) -> Path:
    """Allocate outside task/output roots without trusting inherited TMPDIR.

    ``roots`` replaces the temporary-directory candidates; an isolated
    attempt passes the cells root and nothing else.
    """
    candidate_roots = dict.fromkeys(
        roots
        if roots is not None
        else (Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"))
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


def _local_env_vars(
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
    phase: DeadlinePhase = DeadlinePhase.SETUP,
) -> set[str]:
    """Ask Git which variables can redirect repository discovery."""
    probe_environment = {
        name: value
        for name, value in environment.items()
        if not name.startswith("GIT_")
    }
    probe_environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        remaining = deadline.remaining(phase) if deadline is not None else None
        completed = subprocess.run(
            ["git", *_GIT_SAFETY_CONFIG, "rev-parse", "--local-env-vars"],
            env=probe_environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            **({"timeout": remaining} if remaining is not None else {}),
        )
    except subprocess.TimeoutExpired:
        assert deadline is not None
        deadline.expire(phase)
    except OSError as exc:
        if deadline is not None:
            deadline.remaining(phase)
        raise _WorkspaceError(
            f"cannot inspect Git environment variables: {exc}"
        ) from exc
    if deadline is not None:
        deadline.remaining(phase)
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
    timeout: float | None = None,
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
            timeout=timeout,
        )
    except OSError as exc:
        raise _WorkspaceError(f"cannot run git {' '.join(args)}: {exc}") from exc
    if completed.returncode not in allowed:
        detail = os.fsdecode(completed.stderr).strip()
        raise _WorkspaceError(f"git {' '.join(args)} failed: {detail}")
    return completed


def _deadline_git(
    root: Path,
    args: Sequence[str],
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None,
    phase: DeadlinePhase,
    input_bytes: bytes | None = None,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    """Run Git without starting or accepting work after whole expiry."""
    if deadline is None:
        return _git(root, args, environment, input_bytes=input_bytes, allowed=allowed)
    try:
        completed = _git(
            root,
            args,
            environment,
            input_bytes=input_bytes,
            allowed=allowed,
            timeout=deadline.remaining(phase),
        )
    except subprocess.TimeoutExpired:
        deadline.expire(phase)
    except _WorkspaceError:
        deadline.remaining(phase)
        raise
    deadline.remaining(phase)
    return completed


def _registered_worktrees(
    repository: Path,
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
    phase: DeadlinePhase = DeadlinePhase.SETUP,
) -> tuple[Path, ...]:
    output = _deadline_git(
        repository,
        ("worktree", "list", "--porcelain", "-z"),
        environment,
        deadline=deadline,
        phase=phase,
    ).stdout
    fields = os.fsdecode(output).split("\0")
    return tuple(
        Path(field.removeprefix("worktree ")).resolve()
        for field in fields
        if field.startswith("worktree ")
    )


def _git_protected_paths(
    paths: Sequence[Path],
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
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
            top_result = _deadline_git(
                cursor,
                ("rev-parse", "--show-toplevel"),
                environment,
                deadline=deadline,
                phase=DeadlinePhase.SETUP,
                allowed=(0, 128),
            )
            top = (
                Path(os.fsdecode(top_result.stdout).removesuffix("\n")).resolve()
                if top_result.returncode == 0
                else None
            )
            git_dir_result = _deadline_git(
                cursor,
                ("rev-parse", "--absolute-git-dir"),
                environment,
                deadline=deadline,
                phase=DeadlinePhase.SETUP,
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
                    _deadline_git(
                        cursor,
                        ("rev-parse", "--git-common-dir"),
                        environment,
                        deadline=deadline,
                        phase=DeadlinePhase.SETUP,
                    ).stdout
                ).removesuffix("\n")
            )
            common = (
                raw_common.resolve()
                if raw_common.is_absolute()
                else (cursor / raw_common).resolve()
            )
            protected[common] = None
            worktrees = (
                _registered_worktrees(repository, environment, deadline=deadline)
                if deadline is not None
                else _registered_worktrees(repository, environment)
            )
            for worktree in worktrees:
                protected[worktree] = None
            if repository == repository.parent:
                break
            cursor = repository.parent
    return tuple(protected)


def _worktree_registered(
    repository: Path,
    worktree: Path,
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
    phase: DeadlinePhase = DeadlinePhase.SETUP,
) -> bool | None:
    try:
        registered = (
            _registered_worktrees(
                repository, environment, deadline=deadline, phase=phase
            )
            if deadline is not None
            else _registered_worktrees(repository, environment)
        )
    except _WorkspaceError:
        return None
    return worktree.resolve() in registered


def _remove_parent(parent: Path) -> None:
    """The removal whose normal-completion arc is attributed in-process."""
    shutil.rmtree(parent)


def _prepare_repository(
    base: Path,
    state: _WorkspaceState,
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
) -> None:
    phase = DeadlinePhase.SETUP
    if deadline is not None:
        deadline.remaining(phase)
    if os.path.lexists(base / ".git"):
        raise _WorkspaceError("task base must not contain top-level .git metadata")
    expected = snapshot_tree(base)
    if deadline is not None:
        deadline.remaining(phase)
    try:
        state.repository.mkdir()
    except OSError as exc:
        raise _WorkspaceError(
            f"cannot create synthetic repository directory: {exc}"
        ) from exc
    try:
        shutil.copytree(base, state.repository, symlinks=True, dirs_exist_ok=True)
    except OSError as exc:
        raise _WorkspaceError(
            f"cannot copy task base into synthetic repository: {exc}"
        ) from exc
    if deadline is not None:
        deadline.remaining(phase)
    for args in (
        ("init", "-q"),
        ("config", "commit.gpgSign", "false"),
        ("config", "core.hooksPath", os.devnull),
        ("config", "core.fsmonitor", "false"),
        ("config", "core.symlinks", "true"),
        ("add", "--force", "--all"),
    ):
        _deadline_git(
            state.repository,
            args,
            environment,
            deadline=deadline,
            phase=phase,
        )
    tree = os.fsdecode(
        _deadline_git(
            state.repository,
            ("write-tree",),
            environment,
            deadline=deadline,
            phase=phase,
        ).stdout
    ).removesuffix("\n")
    commit_env = dict(environment)
    commit_env.update(_FIXED_GIT_ENV)
    commit = os.fsdecode(
        _deadline_git(
            state.repository,
            ("commit-tree", tree),
            commit_env,
            deadline=deadline,
            phase=phase,
            input_bytes=b"satyrn-evals synthetic base\n",
        ).stdout
    ).removesuffix("\n")
    _deadline_git(
        state.repository,
        ("symbolic-ref", "HEAD", "refs/heads/satyrn-base"),
        environment,
        deadline=deadline,
        phase=phase,
    )
    _deadline_git(
        state.repository,
        ("update-ref", "refs/heads/satyrn-base", commit),
        environment,
        deadline=deadline,
        phase=phase,
    )
    state.base_sha = commit
    state.begin_add()
    _deadline_git(
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
        deadline=deadline,
        phase=phase,
    )
    registered = (
        _worktree_registered(
            state.repository,
            state.worktree,
            environment,
            deadline=deadline,
            phase=phase,
        )
        if deadline is not None
        else _worktree_registered(state.repository, state.worktree, environment)
    )
    state.observe_registration(registered)
    if state.registration is not Registration.PRESENT:
        raise _WorkspaceError("Git did not confirm the attempt worktree registration")
    head = os.fsdecode(
        _deadline_git(
            state.worktree,
            ("rev-parse", "--verify", "HEAD^{commit}"),
            environment,
            deadline=deadline,
            phase=phase,
        ).stdout
    ).removesuffix("\n")
    symbolic = _deadline_git(
        state.worktree,
        ("symbolic-ref", "--quiet", "HEAD"),
        environment,
        deadline=deadline,
        phase=phase,
        allowed=(0, 1),
    )
    if head != commit or symbolic.returncode != 1:
        raise _WorkspaceError("attempt worktree is not detached at the synthetic base")
    status_result = _deadline_git(
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
        deadline=deadline,
        phase=phase,
    )
    if status_result.stdout:
        raise _WorkspaceError("attempt worktree is not clean at the synthetic base")
    if deadline is not None:
        deadline.remaining(phase)
    actual = snapshot_tree(state.worktree)
    if deadline is not None:
        deadline.remaining(phase)
    if actual != expected:
        raise _WorkspaceError(
            "Git materialization does not match the persisted task base"
        )


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
    process: subprocess.Popen[bytes], grace: float, *, cell: bool = False
) -> tuple[bool, str | None]:
    """Best-effort teardown within one grace period.

    The allowance begins with termination, rather than being granted afresh
    for each signal, reap, and process-group observation.  Safe still means
    that the direct child is reaped and (on POSIX) its process group is gone.

    ``cell``: the group holds processes the cell user owns. The maintainer's
    SIGKILL cannot reach them, so a group still present after SIGTERM is
    also killed from the cell side (`cell.kill_cell_group`).
    """
    details: list[str] = []
    started = time.monotonic()
    cutoff = started + grace
    terminate_cutoff = started + grace / 2

    def remaining(until: float = cutoff) -> float:
        return max(0.0, until - time.monotonic())

    if _is_posix():
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as exc:
            details.append(f"cannot signal process group with SIGTERM: {exc}")
        # Reserve part of the one shared allowance for SIGKILL and reaping.
        # Otherwise an exited direct child can remain a zombie in the process
        # group until it is reaped, making disappearance impossible to prove.
        gone = _wait_until_group_gone(process.pid, terminate_cutoff)
        if not gone:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as exc:
                details.append(f"cannot signal process group with SIGKILL: {exc}")
            if cell and (
                failure := kill_cell_group(
                    process.pid, timeout=max(remaining(), CELL_KILL_TIMEOUT_FLOOR)
                )
            ):
                details.append(failure)
    else:  # Windows is a direct-child fallback, not part of V4's proof.
        try:
            process.terminate()
        except OSError as exc:
            details.append(f"cannot terminate command: {exc}")
        try:
            process.wait(timeout=remaining(terminate_cutoff))
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError as exc:
                details.append(f"cannot kill command: {exc}")
    reaped = True
    try:
        process.wait(timeout=remaining())
    except subprocess.TimeoutExpired:
        reaped = False
        details.append("direct child was not reaped")
    except OSError as exc:
        reaped = False
        details.append(f"cannot reap direct child: {exc}")
    gone = _wait_until_group_gone(process.pid, cutoff) if _is_posix() else reaped
    if not gone:
        details.append("process group disappearance is unconfirmed")
    return reaped and gone, "; ".join(details) or None


def _teardown(
    process: subprocess.Popen[bytes], grace: float, state: _WorkspaceState
) -> tuple[bool, str | None]:
    """Tear down the command, from the cell side too when the attempt is isolated."""
    if state.isolation is Isolation.ISOLATED:
        return _teardown_process(process, grace, cell=True)
    return _teardown_process(process, grace)


def _wait_or_trip(
    process: subprocess.Popen[bytes],
    *,
    timeout: float,
    transcript: Path | None,
    limit: int | None,
    deadline: AttemptDeadline | None = None,
    poll: float = 0.25,
    budget: AttemptBudget | None = None,
    timeline: Path | None = None,
    line_budget: LineBudget | None = None,
    on_line_crossed: Callable[[LineCrossing], None] | None = None,
) -> tuple[int | None, RepeatTripwire | BudgetTripwire | None]:
    """Wait for the process, watching the transcript for a locked loop.

    Returns ``(exit code, tripwire)``: the exit code when the process
    finished on its own (with a ``None`` tripwire), or ``(None, wire)``
    when the repeated-call limit or the budget tripped first;
    ``(exit code, budget wire)`` when the budget was exceeded by lines the
    command wrote before exiting. With neither ``limit`` nor ``budget`` nor
    ``line_budget`` the tailing is skipped entirely. ``TimeoutExpired``
    propagates, so the timeout path above is unchanged.

    The transcript is read as it is written, so only whole lines are fed
    and a partial trailing write is held until its newline arrives.

    With ``timeline``, each tool start and end line is stamped as read
    (``timeline.py``).

    ``line_budget``, when given, is watched alongside the stopping wires but
    never joins them: crossing it never trips a stop. ``on_line_crossed`` is
    called synchronously, at most once, on the very transcript line whose
    processing first crosses it -- the cell has not been touched and keeps
    running underneath the call.
    """

    def whole_remaining() -> float:
        return (
            deadline.remaining(DeadlinePhase.COMMAND)
            if deadline is not None
            else timeout
        )

    if transcript is None or (
        limit is None and budget is None and timeline is None and line_budget is None
    ):
        try:
            result = process.wait(timeout=min(timeout, whole_remaining()))
        except subprocess.TimeoutExpired:
            # Check the whole deadline first so a simultaneous observation
            # consistently reports the lifecycle bound, not command timeout.
            whole_remaining()
            raise
        whole_remaining()
        return result, None
    wire = RepeatTripwire(limit) if limit is not None else None
    budget_wire = BudgetTripwire(budget) if budget is not None else None
    line_wire = LineTripwire(line_budget) if line_budget is not None else None
    writer = TimelineWriter(timeline) if timeline is not None else None

    def _feed_line(line: str) -> None:
        if line_wire is not None and line_wire.feed(line) and on_line_crossed is not None:
            on_line_crossed(line_wire.crossed)  # type: ignore[arg-type]

    def tripped_by(line: str) -> RepeatTripwire | BudgetTripwire | None:
        if writer is not None:
            writer.feed(line)
        _feed_line(line)
        if budget_wire is not None and budget_wire.feed(line):
            return budget_wire
        if wire is not None and wire.feed(line):
            return wire
        return None

    command_deadline = time.monotonic() + timeout
    pending = ""
    handle: BinaryIO | None = None
    try:
        while True:
            whole = whole_remaining()
            if handle is None and transcript.is_file():
                handle = transcript.open("rb")
            if handle is not None:
                pending += handle.read().decode("utf-8", errors="replace")
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    if (tripped := tripped_by(line)) is not None:
                        whole_remaining()
                        return None, tripped
            if (remaining := command_deadline - time.monotonic()) <= 0:
                # Transcript processing can consume both budgets.  Observe
                # the whole deadline at this same point before accepting the
                # command timeout, so simultaneous expiry has one authority.
                whole_remaining()
                raise subprocess.TimeoutExpired(process.args, timeout)
            try:
                result = process.wait(timeout=min(poll, remaining, whole))
            except subprocess.TimeoutExpired:
                whole_remaining()
                continue
            whole_remaining()
            # What the command wrote after the last poll still counts: a
            # command that finished over budget is still over it, and its
            # last tool end still belongs on the timeline. The repeat rule
            # is a live spending rule and is not applied to this tail.
            if handle is None and transcript.is_file():
                handle = transcript.open("rb")
            if handle is not None:
                pending += handle.read().decode("utf-8", errors="replace")
            over = False
            for line in pending.split("\n"):
                if writer is not None:
                    writer.feed(line)
                _feed_line(line)
                if budget_wire is not None:
                    over = budget_wire.feed(line) or over
            return result, (budget_wire if over else None)
    finally:
        if writer is not None:
            writer.close()
        if handle is not None:
            handle.close()


def _harvest_patch(
    state: _WorkspaceState,
    environment: Mapping[str, str],
    destination: Path,
    *,
    timeout: float,
    worktree: Path | None = None,
) -> tuple[bool, str | None]:
    """Write the cumulative diff of ``worktree`` (default ``state.worktree``)
    against ``state.base_sha`` to ``destination``.

    Returns ``(wrote_a_file, error)``: a blank cumulative diff writes nothing
    and is not an error (nothing changed yet); a raised git/OS failure writes
    nothing and reports its message rather than raising, so a harvest failure
    can never fail or alter the cell that asked for it.
    """
    # Imported here, not at module scope: `session_patch` imports
    # `GIT_SAFETY_CONFIG` from this module, so a top-level import is a cycle.
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch

    if state.base_sha is None:
        return False, "workspace base_sha is not set"
    target = worktree if worktree is not None else state.worktree
    # A `worktree` override names the Engine's own internal deliver
    # worktree (`_engine_worktree`): `git worktree add` for it ran as the
    # cell user (satyrn-engine's own subprocess under isolation), so its
    # Git admin data is cell-owned and the maintainer's git refuses it as
    # "dubious ownership" without this. Scoped to this one resolved path
    # only -- never a blanket `safe.directory=*` and never written to any
    # global/system git config. The Evals worktree itself needs no such
    # override: the maintainer created it, so it already owns the admin
    # data the ordinary harvest reads.
    extra_config: tuple[str, ...] = (
        ("-c", f"safe.directory={os.fspath(target.resolve())}")
        if worktree is not None
        else ()
    )
    try:
        capture = build_cumulative_patch(
            target,
            state.base_sha,
            environment,
            exclude=RESIDUE_EXCLUDES,
            timeout=timeout,
            extra_config=extra_config,
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if capture.patch_text.strip():
        try:
            destination.write_text(capture.patch_text, encoding="utf-8")
        except OSError as exc:
            return False, f"{type(exc).__name__}: {exc}"
        return True, None
    return False, None


def _harvest_tripped(
    state: _WorkspaceState, environment: Mapping[str, str], destination: Path
) -> None:
    """Write the worktree's cumulative diff against ``base_sha`` to ``destination``.

    Preserve before judging (BRIEF invariant 1). This runs at the teardown, not
    in ``_finish_attempt``, because a whole-attempt deadline can expire in
    preservation or cleanup and return without ever reaching the finalizer --
    the tripped evidence must already be on disk by then, so a later regrade
    can read it. Any failure is swallowed: a missing tripped patch is a missing
    secondary, never a lost cell, and the primary outcome must not change
    because a secondary could not be taken.
    """
    _harvest_patch(state, environment, destination, timeout=TRIPPED_HARVEST_TIMEOUT_S)


#: I4c: satyrn-engine's own ``_temporary_parent`` (delivery.py ~1704-1721 at
#: 0a6e5df) tries ``tempfile.gettempdir()`` first and falls back to these two
#: roots in order when that candidate is skipped (inside a repository
#: worktree, or ``mkdtemp`` fails). Under the ``local`` isolation profile this
#: harness scans the same fallback roots Engine itself would have tried, so a
#: deliver worktree that landed in one of them is still found -- a *foreign*
#: ``satyrn-engine-*`` directory left there by something else is harmless
#: because every candidate is bound to this attempt (below) before it is
#: accepted, never guessed at by position or count alone.
_LOCAL_TMP_FALLBACKS: tuple[Path, ...] = (Path("/tmp"), Path("/var/tmp"))


def _engine_worktree_search_roots(state: _WorkspaceState) -> tuple[Path, ...]:
    """Where an Engine arm's transient deliver worktree could be rooted.

    Isolated: exactly the cell's own private ``TMPDIR`` (``cell.cell_paths``:
    ``parent / "tmp"``) -- no other cell's Engine subprocess can write there,
    so one root is both necessary and sufficient. Local (development only,
    never a deciding record): the ambient ``TMPDIR`` plus the two roots
    Engine's own ``_temporary_parent`` falls back to, deduplicated by
    resolved identity -- scanning only the first candidate would miss a
    worktree Engine itself put in a fallback root.
    """
    if state.isolation is Isolation.ISOLATED:
        return (state.parent / "tmp",)
    seen: dict[Path, None] = {}
    for root in (Path(tempfile.gettempdir()), *_LOCAL_TMP_FALLBACKS):
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved.is_dir():
            seen.setdefault(resolved, None)
    return tuple(seen)


def _resolve_git_common_dir(
    root: Path,
    environment: Mapping[str, str],
    *,
    extra_args: tuple[str, ...] = (),
) -> Path | None:
    """``git -C root rev-parse --git-common-dir``, resolved; ``None`` if git refuses."""
    try:
        completed = _git(root, (*extra_args, "rev-parse", "--git-common-dir"), environment)
    except _WorkspaceError:
        return None
    raw = Path(os.fsdecode(completed.stdout).removesuffix("\n"))
    try:
        return (raw if raw.is_absolute() else (root / raw)).resolve()
    except OSError:
        return None


def _engine_worktree_bound(
    state: _WorkspaceState, candidate: Path, environment: Mapping[str, str]
) -> tuple[bool, str]:
    """I4b: verify ``candidate`` is THIS attempt's own Engine deliver worktree.

    satyrn-engine creates its deliver worktree with ``git worktree add`` run
    from ``context.root`` -- the directory the harness itself gave the Engine
    command as its cwd, i.e. this attempt's own ``state.worktree`` (the seed
    the cell was materialized from). A worktree ``git worktree add`` creates
    shares its parent repository's administration data, so the candidate's
    ``git-common-dir`` must equal ``state.worktree``'s own ``git-common-dir``
    -- comparing anything else (e.g. the candidate's path, or a name pattern)
    would accept a same-named directory another process happened to leave
    behind. The candidate's Git admin data is cell-owned (C1), so the check
    scopes ``safe.directory`` to that one resolved path, exactly as the
    harvest itself does -- never ``*``, never global config. ``state.worktree``
    needs no such override: the maintainer created it.
    """
    own_common = _resolve_git_common_dir(state.worktree, environment)
    if own_common is None:
        return False, (
            f"engine arm: cannot resolve this attempt's own git-common-dir "
            f"to verify {candidate}"
        )
    candidate_common = _resolve_git_common_dir(
        candidate,
        environment,
        extra_args=("-c", f"safe.directory={candidate.resolve()}"),
    )
    if candidate_common is None:
        return False, f"engine arm: cannot inspect candidate worktree {candidate}"
    if candidate_common != own_common:
        return False, (
            f"engine arm: candidate worktree {candidate} belongs to a foreign "
            "repository, not this attempt"
        )
    return True, ""


def _engine_worktree(
    state: _WorkspaceState, environment: Mapping[str, str]
) -> tuple[Path | None, str | None]:
    """The Engine arm's own transient deliver worktree, bound to this attempt.

    satyrn-engine's own ``deliver`` allocates a private worktree under a fresh
    ``tempfile.mkdtemp(prefix="satyrn-engine-", dir=<TMPDIR>)``, then
    ``<that>/worktree`` (satyrn-engine ``delivery.py``'s isolated-root
    allocation), removed only after the Pi command it runs exits -- so while a
    line crossing is being harvested (synchronously, from the transcript that
    same Pi process is writing) the directory is guaranteed to still be there.

    I4a/I4b: a glob match is never accepted on position or count alone. Every
    ``satyrn-engine-*/worktree`` found under the search roots
    (``_engine_worktree_search_roots``) is bound to this attempt
    (``_engine_worktree_bound``) before it is trusted; only a candidate that
    binds is a match. Zero bound candidates, or more than one, is refused --
    accepting the first of several (the mutation this guards against) or an
    unverified single match (the local-TMPDIR hazard I4 exists for) would
    both let a harvest silently diff the wrong tree. Exactly one bound
    candidate among several *unbound* ones is still accepted: under
    ``local``, an ambient TMPDIR can hold a foreign ``satyrn-engine-*``
    directory from an unrelated process (including the Engine repository's
    own test suite) alongside this attempt's own -- refusing the harvest
    just because something foreign is also present would defeat the point of
    binding. Returns ``(worktree, None)`` on a bound match, or
    ``(None, reason)`` naming why nothing was accepted.
    """
    candidates: list[Path] = []
    for tmp_root in _engine_worktree_search_roots(state):
        if not tmp_root.is_dir():
            continue
        candidates.extend(
            entry / "worktree"
            for entry in tmp_root.glob("satyrn-engine-*")
            if (entry / "worktree").is_dir()
        )
    if not candidates:
        return None, "engine arm: no satyrn-engine-* worktree found under the cell TMPDIR"
    bound: list[Path] = []
    reasons: list[str] = []
    for candidate in candidates:
        ok, detail = _engine_worktree_bound(state, candidate, environment)
        if ok:
            bound.append(candidate)
        else:
            reasons.append(detail)
    if len(bound) == 1:
        return bound[0], None
    if not bound:
        return None, reasons[0] if reasons else (
            "engine arm: cannot uniquely locate the internal deliver worktree"
        )
    return None, (
        f"engine arm: {len(bound)} worktrees are bound to this attempt; "
        "cannot uniquely locate the internal deliver worktree"
    )


def _run_command(
    command: Sequence[str],
    state: _WorkspaceState,
    environment: Mapping[str, str],
    timeout: float,
    teardown_grace: float,
    *,
    transcript: Path | None = None,
    max_repeated_calls: int | None = None,
    deadline: AttemptDeadline | None = None,
    budget: AttemptBudget | None = None,
    timeline: Path | None = None,
    tripped_patch: Path | None = None,
    line_budget: LineBudget | None = None,
    line_patch: Path | None = None,
    engine_arm: bool = False,
) -> WorkspaceResult:
    outputs: list[BinaryIO] = []
    pending: WorkspaceResult | None = None
    active_exception: BaseException | None = None
    line_state: dict[str, object] = {"crossed": None, "written": False, "error": None}

    def _on_line_crossed(crossing: LineCrossing) -> None:
        line_state["crossed"] = crossing
        if line_patch is None:
            return
        worktree_override: Path | None = None
        if engine_arm:
            worktree_override, error = _engine_worktree(state, environment)
            if worktree_override is None:
                line_state["error"] = error
                return
        wrote, error = _harvest_patch(
            state,
            environment,
            line_patch,
            timeout=LINE_HARVEST_TIMEOUT_S,
            worktree=worktree_override,
        )
        line_state["written"] = wrote
        line_state["error"] = error

    try:
        for _ in range(2):
            outputs.append(
                tempfile.TemporaryFile(  # noqa: SIM115 - explicit cleanup is required
                    dir=state.parent
                )
            )
        state.process_cleanup_safe = False
        try:
            if deadline is not None:
                deadline.remaining(DeadlinePhase.COMMAND)
            process = subprocess.Popen(
                command,
                cwd=state.worktree,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=outputs[0],
                stderr=outputs[1],
                start_new_session=_is_posix(),
            )
        except AttemptDeadlineExceeded:
            # The process did not start; leave the lease intact for the
            # attempt finalizer to retain rather than release after expiry.
            raise
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
            tripped: RepeatTripwire | BudgetTripwire | None = None
            try:
                command_exit, tripped = _wait_or_trip(
                    process,
                    timeout=timeout,
                    transcript=transcript,
                    limit=max_repeated_calls,
                    deadline=deadline,
                    budget=budget,
                    timeline=timeline,
                    line_budget=line_budget,
                    on_line_crossed=_on_line_crossed,
                )
            except subprocess.TimeoutExpired:
                try:
                    safe, detail = _teardown(process, teardown_grace, state)
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
                    safe, detail = _teardown(process, teardown_grace, state)
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
                if isinstance(tripped, BudgetTripwire) and command_exit is not None:
                    # Over budget in the lines written just before a normal
                    # exit: nothing to tear down, the cell is still a fail.
                    # The worktree still holds the cell's last state, and a
                    # cell that finished over budget is the one with the most
                    # to say, so harvest it here too -- before release, exactly
                    # as the teardown branch does. The process already exited
                    # on its own, so cleanup is unconditionally safe here --
                    # record that before the harvest runs, so an unexpected
                    # harvest failure can never leave cleanup unmarked (I1).
                    state.process_cleanup_safe = True
                    if tripped_patch is not None:
                        _harvest_tripped(state, environment, tripped_patch)
                    pending = WorkspaceResult(
                        WorkspaceCode.BUDGET_EXCEEDED,
                        tripped.message(),
                        command_exit,
                        state.base_sha,
                    )
                elif tripped is not None:
                    # The spending rule fired: tear down exactly as the
                    # timeout branch does, and report it as its own code so
                    # a stopped cell is never mistaken for one that refused
                    # on its own. Artifacts already written are harvested
                    # first -- inside its own try/finally, so an unexpected
                    # harvest failure structurally cannot skip the teardown
                    # in the finally block and leave a live process running
                    # (I1). `_harvest_patch` itself never raises for its
                    # known failure modes (git or write errors are recorded,
                    # not raised); this is defense in depth for the rest.
                    try:
                        if isinstance(tripped, BudgetTripwire) and tripped_patch is not None:
                            _harvest_tripped(state, environment, tripped_patch)
                    finally:
                        try:
                            safe, detail = _teardown(process, teardown_grace, state)
                        except BaseException as exc:
                            active_exception = exc
                            _add_exception_note(
                                exc,
                                "process cleanup is unconfirmed; "
                                f"{_retained_workspace(state)}",
                            )
                            raise
                        state.process_cleanup_safe = safe
                    stopped = (
                        (WorkspaceCode.BUDGET_EXCEEDED, tripped.message(), "budget")
                        if isinstance(tripped, BudgetTripwire)
                        else (
                            WorkspaceCode.REPEAT_LIMIT,
                            f"attempt command repeated one tool call "
                            f"{tripped.run} times, at the limit of "
                            f"{tripped.limit}",
                            "repeat-limit",
                        )
                    )
                    pending = (
                        WorkspaceResult(stopped[0], stopped[1], None, state.base_sha)
                        if safe
                        else WorkspaceResult(
                            WorkspaceCode.CLEANUP_FAILED,
                            f"{stopped[2]} cleanup is unconfirmed: {detail}",
                            None,
                            state.base_sha,
                            os.fspath(state.parent),
                        )
                    )
                else:
                    # COMMAND is explicitly synchronous at this V4 boundary.
                    state.process_cleanup_safe = True
                    pending = WorkspaceResult(
                        WorkspaceCode.OK,
                        "attempt command completed",
                        command_exit,
                        state.base_sha,
                    )
    except AttemptDeadlineExceeded as exc:
        active_exception = exc
        raise
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
    if line_state["crossed"] is not None:
        pending = replace(
            pending,
            line_crossed=line_state["crossed"],  # type: ignore[arg-type]
            line_patch_written=bool(line_state["written"]),
            line_harvest_error=line_state["error"],  # type: ignore[arg-type]
        )
    return pending


def _cleanup_worktree(
    state: _WorkspaceState,
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
) -> None:
    remove_error: _WorkspaceError | None = None
    try:
        _deadline_git(
            state.repository,
            ("worktree", "remove", "--force", os.fspath(state.worktree)),
            environment,
            deadline=deadline,
            phase=DeadlinePhase.CLEANUP,
        )
    except _WorkspaceError as exc:
        remove_error = exc
    registered = (
        _worktree_registered(
            state.repository,
            state.worktree,
            environment,
            deadline=deadline,
            phase=DeadlinePhase.CLEANUP,
        )
        if deadline is not None
        else _worktree_registered(state.repository, state.worktree, environment)
    )
    state.observe_registration(registered)
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
    overlay: OverlaySpec | None = None,
    transcript: Path | None = None,
    max_repeated_calls: int | None = None,
) -> WorkspaceResult:
    """Run ``command`` once in a reconstructed detached Git worktree.

    ``max_repeated_calls`` opts the cell into the repeated-call spending
    rule (`repeat_limit.py`), which needs ``transcript`` to watch. Both
    default to off: a batch that did not ask for the rule runs exactly as
    it did before it existed.
    """
    _validate_command_limits(command, timeout, teardown_grace)
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
        if overlay is not None:
            assert_overlay_absent(state.worktree, overlay)
        pending = _run_command(
            command,
            state,
            git_environment,
            timeout,
            teardown_grace,
            transcript=transcript,
            max_repeated_calls=max_repeated_calls,
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
            if (
                state.process_cleanup_safe
                and state.registration is not Registration.ABSENT
            ):
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


class WorkspacePrepareError(SatyrnError):
    """Exit 3: a prepared workspace could not be built."""

    def __init__(
        self,
        message: str,
        retained_path: str | None = None,
        deadline: AttemptDeadlineExceeded | None = None,
    ) -> None:
        super().__init__(message)
        self.retained_path = retained_path
        self.deadline = deadline


class WorkspaceReleaseError(SatyrnError):
    """Exit 3: a prepared workspace could not be confirmed cleaned up."""

    def __init__(self, message: str, retained_path: str | None = None) -> None:
        super().__init__(message)
        self.retained_path = retained_path


@dataclass(frozen=True, slots=True)
class PreparedWorkspace:
    """A prepared detached worktree that a caller releases explicitly.

    It reuses the V4 lifecycle's repository construction, process isolation,
    and cleanup state. The caller may preserve artifacts and write durable
    evidence after ``run_prepared_command`` and before ``release_workspace``.
    """

    parent: Path
    repository: Path
    worktree: Path
    base_sha: str
    _state: _WorkspaceState
    _environment: dict[str, str]


SessionWorkspace = PreparedWorkspace


def _discard_failed_preparation(
    state: _WorkspaceState | None,
    parent: Path | None,
    environment: Mapping[str, str] | None,
    *,
    deadline: AttemptDeadline | None = None,
) -> str | None:
    """Best-effort cleanup that names a parent we cannot safely discard."""
    try:
        if deadline is not None:
            deadline.remaining(DeadlinePhase.SETUP)
        if (
            state is not None
            and environment is not None
            and state.registration is not Registration.ABSENT
        ):
            _cleanup_worktree(state, environment, deadline=deadline)
        candidate = state.parent if state is not None else parent
        if candidate is not None and (
            state is None
            or (
                state.process_cleanup_safe and state.registration is Registration.ABSENT
            )
        ):
            if deadline is not None:
                deadline.remaining(DeadlinePhase.SETUP)
            _remove_parent(candidate)
    except AttemptDeadlineExceeded:
        raise
    except BaseException as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def _expired_preparation(
    error: AttemptDeadlineExceeded,
    state: _WorkspaceState | None,
    parent: Path | None,
) -> WorkspacePrepareError:
    """Make expiry before a returned lease durable and conservatively retained."""
    retained = state.parent if state is not None else parent
    return WorkspacePrepareError(
        str(error),
        os.fspath(retained) if retained is not None else None,
        deadline=error,
    )


def _validate_command_limits(
    command: Sequence[str], timeout: float, teardown_grace: float
) -> None:
    """Reject invalid command work before a workspace or subprocess exists."""
    if not command:
        raise ValueError("workspace command is empty")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("workspace timeout must be a finite number greater than zero")
    if not math.isfinite(teardown_grace) or teardown_grace <= 0:
        raise ValueError(
            "workspace teardown grace must be a finite number greater than zero"
        )


def _share_workspace(
    state: _WorkspaceState,
    environment: Mapping[str, str],
    *,
    deadline: AttemptDeadline | None = None,
) -> None:
    """Hand the cell user a group-shared repository and its own TMPDIR, uv environment and git config."""
    _deadline_git(
        state.repository,
        ("config", "core.sharedRepository", "group"),
        environment,
        deadline=deadline,
        phase=DeadlinePhase.SETUP,
    )
    tmpdir, uv_environment, gitconfig = cell_paths(state.parent)
    try:
        tmpdir.mkdir()
        uv_environment.mkdir()
        gitconfig.write_text(cell_gitconfig(state.worktree), encoding="utf-8")
        share_with_cell(state.parent)
    except OSError as exc:
        raise _WorkspaceError(f"cannot share the workspace with the cell user: {exc}") from exc


def prepare_workspace(
    *,
    base: Path,
    protected_paths: Sequence[Path],
    environment: Mapping[str, str],
    overlay: OverlaySpec | None = None,
    deadline: AttemptDeadline | None = None,
    isolation: Isolation = Isolation.LOCAL,
) -> PreparedWorkspace:
    """Reconstruct a detached worktree and retain its cleaned environment.

    ``Isolation.ISOLATED`` allocates the parent under the cells root and,
    once the base is verified, shares it with the cell user: a group-shared
    repository, the cell's TMPDIR, uv environment and git config beside the
    worktree, every entry group-writable.
    """
    state: _WorkspaceState | None = None
    parent: Path | None = None
    git_environment: dict[str, str] | None = None
    try:
        if deadline is not None:
            deadline.remaining(DeadlinePhase.SETUP)
            routing_names = _local_env_vars(environment, deadline=deadline)
        else:
            routing_names = _local_env_vars(environment)
        git_environment = clean_environment(environment, routing_names)
        if deadline is not None:
            deadline.remaining(DeadlinePhase.SETUP)
        requested_protected = (base, *protected_paths)
        if deadline is not None:
            git_protected = _git_protected_paths(
                requested_protected, git_environment, deadline=deadline
            )
        else:
            git_protected = _git_protected_paths(requested_protected, git_environment)
        if deadline is not None:
            deadline.remaining(DeadlinePhase.SETUP)
        parent = (
            _safe_temp_parent((*requested_protected, *git_protected), (CELLS_ROOT,))
            if isolation is Isolation.ISOLATED
            else _safe_temp_parent((*requested_protected, *git_protected))
        )
        if isolation is Isolation.ISOLATED and (failure := grant_maintainer(parent)):
            raise _WorkspaceError(f"cannot keep the maintainer's access to {parent}: {failure}")
        if deadline is not None:
            deadline.remaining(DeadlinePhase.SETUP)
        state = _WorkspaceState(
            parent=parent,
            # Preserve the legacy workspace topology.  The executable engine
            # seam can observe its current repository's parent layout, so the
            # neutral lease must not rename this internal directory.
            repository=parent / "seed",
            worktree=parent / "worktree",
            isolation=isolation,
        )
        if deadline is not None:
            _prepare_repository(base, state, git_environment, deadline=deadline)
        else:
            _prepare_repository(base, state, git_environment)
        if overlay is not None:
            if deadline is not None:
                deadline.remaining(DeadlinePhase.SETUP)
            assert_overlay_absent(state.worktree, overlay)
            if deadline is not None:
                deadline.remaining(DeadlinePhase.SETUP)
        if isolation is Isolation.ISOLATED:
            _share_workspace(state, git_environment, deadline=deadline)
        assert state.base_sha is not None
        return PreparedWorkspace(
            parent=parent,
            repository=state.repository,
            worktree=state.worktree,
            base_sha=state.base_sha,
            _state=state,
            _environment=git_environment,
        )
    except AttemptDeadlineExceeded as exc:
        raise _expired_preparation(exc, state, parent) from exc
    except OverlayError as exc:
        try:
            detail = _discard_failed_preparation(
                state, parent, git_environment, deadline=deadline
            )
        except AttemptDeadlineExceeded as deadline_error:
            raise _expired_preparation(
                deadline_error, state, parent
            ) from deadline_error
        if detail:
            retained = state.parent if state is not None else parent
            _add_exception_note(exc, f"workspace retained at {retained}: {detail}")
        raise
    except _RetainedCleanupError as exc:
        raise WorkspacePrepareError(str(exc), os.fspath(exc.retained_path)) from exc
    except _WorkspaceError as exc:
        try:
            detail = _discard_failed_preparation(
                state, parent, git_environment, deadline=deadline
            )
        except AttemptDeadlineExceeded as deadline_error:
            raise _expired_preparation(
                deadline_error, state, parent
            ) from deadline_error
        if detail:
            retained = state.parent if state is not None else parent
            raise WorkspacePrepareError(
                f"{exc}; workspace retained at {retained}: {detail}",
                os.fspath(retained) if retained is not None else None,
            ) from exc
        raise WorkspacePrepareError(str(exc)) from exc
    except BaseException as exc:
        try:
            detail = _discard_failed_preparation(
                state, parent, git_environment, deadline=deadline
            )
        except AttemptDeadlineExceeded as deadline_error:
            retained = state.parent if state is not None else parent
            _add_exception_note(
                exc, f"workspace retained at {retained}: {deadline_error}"
            )
            raise exc from deadline_error
        if detail:
            retained = state.parent if state is not None else parent
            _add_exception_note(exc, f"workspace retained at {retained}: {detail}")
        raise


def run_prepared_command(
    workspace: PreparedWorkspace,
    *,
    command: Sequence[str],
    timeout: float,
    teardown_grace: float = DEFAULT_TEARDOWN_GRACE,
    transcript: Path | None = None,
    max_repeated_calls: int | None = None,
    deadline: AttemptDeadline | None = None,
    extra_environment: Mapping[str, str] | None = None,
    budget: AttemptBudget | None = None,
    timeline: Path | None = None,
    tripped_patch: Path | None = None,
    line_budget: LineBudget | None = None,
    line_patch: Path | None = None,
    engine_arm: bool = False,
) -> WorkspaceResult:
    """Run one command while leaving the prepared workspace leased."""
    _validate_command_limits(command, timeout, teardown_grace)
    return _run_command(
        command,
        workspace._state,
        {**workspace._environment, **(extra_environment or {})},
        timeout,
        teardown_grace,
        transcript=transcript,
        max_repeated_calls=max_repeated_calls,
        deadline=deadline,
        budget=budget,
        timeline=timeline,
        tripped_patch=tripped_patch,
        line_budget=line_budget,
        line_patch=line_patch,
        engine_arm=engine_arm,
    )


def release_workspace(
    workspace: PreparedWorkspace,
    *,
    deadline: AttemptDeadline | None = None,
) -> str | None:
    """Clean a prepared worktree and remove its parent when that is safe."""
    state = workspace._state
    if deadline is not None:
        deadline.remaining(DeadlinePhase.CLEANUP)
    if not state.process_cleanup_safe:
        return os.fspath(state.parent)
    try:
        if deadline is not None:
            deadline.remaining(DeadlinePhase.CLEANUP)
            _cleanup_worktree(state, workspace._environment, deadline=deadline)
        else:
            _cleanup_worktree(state, workspace._environment)
    except AttemptDeadlineExceeded:
        raise
    except _CleanupError as exc:
        raise WorkspaceReleaseError(
            f"workspace cleanup is unconfirmed: {exc}",
            os.fspath(state.parent),
        ) from exc
    if state.process_cleanup_safe and state.registration is Registration.ABSENT:
        try:
            if deadline is not None:
                deadline.remaining(DeadlinePhase.CLEANUP)
            _remove_parent(state.parent)
        except OSError as exc:
            raise WorkspaceReleaseError(
                f"cannot remove workspace parent {state.parent}: {exc}",
                os.fspath(state.parent),
            ) from exc
    return None


def prepare_session_workspace(
    *,
    base: Path,
    protected_paths: Sequence[Path],
    overlay: OverlaySpec | None = None,
) -> SessionWorkspace:
    """Session compatibility wrapper around ``prepare_workspace``."""
    return prepare_workspace(
        base=base,
        protected_paths=protected_paths,
        environment=dict(os.environ),
        overlay=overlay,
    )


def release_session_workspace(workspace: SessionWorkspace) -> None:
    """Session compatibility wrapper around ``release_workspace``."""
    try:
        release_workspace(workspace)
    except WorkspaceReleaseError as exc:
        message = str(exc).replace("workspace cleanup", "session worktree cleanup")
        message = message.replace("workspace parent", "session workspace parent")
        raise WorkspaceReleaseError(message, exc.retained_path) from exc
