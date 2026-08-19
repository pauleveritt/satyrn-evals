"""Capture orchestration: turn a fixing commit into a valid task.

The lifecycle, re-earned from the satyrn-engine E3 delivery spec: pin the
commits, preflight a clean source, derive the fix diff, add a detached
worktree at the parent, materialize the base, run the oracle three times,
clean up with E3's precedence, and write the capture record. The source
repository's pre-existing files, index, branch, and HEAD are never changed;
the declared output directory is the sole write exception.
"""

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import cast

from satyrn_evals import oracle_hook
from satyrn_evals.capture_record import (
    CHECK_NAMES,
    CaptureOutcome,
    CaptureRecord,
    CheckOutcomes,
    merge_cleanup_failure,
    write_capture_record,
)
from satyrn_evals.diff_filter import parse_name_status_z, without_test_changes
from satyrn_evals.discriminating import (
    FULL_SUITE_ORACLE,
    discriminating_set,
    recorded_oracle,
)
from satyrn_evals.errors import (
    ArtifactFailed,
    CaptureCode,
    CaptureRefused,
    CaptureUsageError,
    CleanupFailed,
    GitFailed,
    HookError,
    NoDiscriminatingTests,
    NoParent,
    NoSourceChange,
    NotWinnable,
    OracleEnv,
    PatchParseError,
    RepoDirty,
)
from satyrn_evals.manifest import is_valid_task_name
from satyrn_evals.verdict import HookResult, load_hook_result

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_GIT_SAFETY_CONFIG = (
    "--no-replace-objects",
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.symlinks=true",
)


class _Registration(Enum):
    """Whether Git may still know about the temporary worktree."""

    ABSENT = auto()
    MAY_EXIST = auto()
    PRESENT = auto()


@dataclass(slots=True)
class _WorktreeState:
    parent: Path
    worktree: Path
    registration: _Registration = _Registration.ABSENT

    def begin_add(self) -> None:
        """Close the deletion gate before Git can mutate shared metadata."""
        self.registration = _Registration.MAY_EXIST

    def observe_registration(self, registered: bool | None) -> None:
        match registered:
            case True:
                self.registration = _Registration.PRESENT
            case False:
                self.registration = _Registration.ABSENT
            case None:
                self.registration = _Registration.MAY_EXIST
            case _:
                raise AssertionError(f"unexpected registration state: {registered!r}")


def slugify_subject(subject: str) -> str | None:
    """Task-name slug from a commit subject; None when underivable."""
    slug = _SLUG_RE.sub("-", subject.strip().lower()).strip("-")
    return slug or None


def _local_env_vars() -> set[str]:
    try:
        proc = subprocess.run(
            ["git", *_GIT_SAFETY_CONFIG, "rev-parse", "--local-env-vars"],
            capture_output=True,
            text=True,
        )
    except OSError as e:
        raise GitFailed(f"cannot inspect Git environment variables: {e}") from e
    names = set(proc.stdout.split()) if proc.returncode == 0 else set()
    names.add("GIT_NAMESPACE")
    return names


def _clean_env() -> dict[str, str]:
    """Child environment with repository-local routing variables stripped."""
    env = dict(os.environ)
    for name in _local_env_vars():
        env.pop(name, None)
    return env


def _git(root: Path, args: list[str], *, input_text: str | None = None) -> str:
    """Run engine-owned Git with repository hooks and fsmonitor disabled."""
    env = _clean_env()
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    env["GIT_GRAFT_FILE"] = os.devnull
    try:
        proc = subprocess.run(
            ["git", *_GIT_SAFETY_CONFIG, *args],
            cwd=root,
            env=env,
            capture_output=True,
            input=os.fsencode(input_text) if input_text is not None else None,
        )
    except OSError as e:
        raise GitFailed(f"cannot run git {' '.join(args)}: {e}") from e
    if proc.returncode != 0:
        stderr = os.fsdecode(proc.stderr).strip()
        raise GitFailed(f"git {' '.join(args)} failed: {stderr}")
    return os.fsdecode(proc.stdout)


def _git_path(value: str) -> Path:
    """Remove Git's one record terminator without stripping legal path bytes."""
    return Path(value.removesuffix("\n"))


def _registered_worktrees(root: Path) -> tuple[Path, ...]:
    """Return Git's registered worktree roots using its NUL-safe format."""
    fields = _git(root, ["worktree", "list", "--porcelain", "-z"]).split("\0")
    return tuple(
        Path(field.removeprefix("worktree ")).resolve()
        for field in fields
        if field.startswith("worktree ")
    )


def _worktree_registered(root: Path, worktree: Path) -> bool | None:
    """Return registration state, or None when Git cannot answer safely."""
    try:
        registered = _registered_worktrees(root)
    except GitFailed:
        return None
    return worktree.resolve() in registered


def _contains_path(root: Path, path: Path) -> bool:
    """Whether path is root/descendant, including filesystem casing aliases."""
    root_resolved = root.resolve()
    cursor = path.resolve()
    if cursor.is_relative_to(root_resolved):
        return True
    while cursor != cursor.parent:
        try:
            if cursor.exists() and cursor.samefile(root_resolved):
                return True
        except OSError:
            pass
        cursor = cursor.parent
    return False


def _safe_temp_parent(root: Path) -> Path:
    """Allocate a temporary parent outside every registered worktree."""
    registered = _registered_worktrees(root)
    candidate_roots = dict.fromkeys(
        (Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"))
    )
    failures: list[str] = []
    for candidate_root in candidate_roots:
        candidate_root = candidate_root.resolve()
        if any(_contains_path(worktree, candidate_root) for worktree in registered):
            failures.append(f"{candidate_root}: inside a registered worktree")
            continue
        try:
            parent = Path(
                tempfile.mkdtemp(prefix="satyrn-capture-", dir=candidate_root)
            ).resolve()
        except OSError as e:
            failures.append(f"{candidate_root}: {e}")
            continue
        if any(_contains_path(worktree, parent) for worktree in registered):
            shutil.rmtree(parent)
            failures.append(f"{candidate_root}: inside a registered worktree")
            continue
        return parent
    detail = "; ".join(failures) or "no candidate temporary directory"
    raise GitFailed(f"cannot allocate a safe temporary directory: {detail}")


def _run_oracle(worktree: Path, cmd: tuple[str, ...], temp_parent: Path) -> HookResult:
    """Run an oracle in the worktree; V1's hook-result machinery.

    A unique reserved-but-unlinked hook path, the run-start timestamp, and
    the stale-file rejection — the verdict never comes from stdout or an
    exit code. Raises OracleEnv when no hook result exists.
    """
    fd: int | None = None
    hook_path: str | None = None
    try:
        fd, hook_path = tempfile.mkstemp(
            prefix="satyrn-hook-", suffix=".json", dir=temp_parent
        )
        os.close(fd)
        fd = None
        os.unlink(hook_path)
    except OSError as e:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if hook_path is not None:
            with contextlib.suppress(OSError):
                Path(hook_path).unlink(missing_ok=True)
        raise OracleEnv(f"cannot prepare oracle result path: {e}") from e
    assert hook_path is not None
    env = _clean_env()
    env[oracle_hook.RESULT_ENV] = hook_path
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    run_started = time.time()
    try:
        subprocess.run(list(cmd), cwd=worktree, env=env, capture_output=True)
    except OSError as e:
        raise OracleEnv(f"oracle failed to start: {e}") from e
    try:
        return load_hook_result(Path(hook_path), run_started)
    except HookError as e:
        raise OracleEnv(str(e)) from e
    finally:
        with contextlib.suppress(OSError):
            Path(hook_path).unlink(missing_ok=True)


def _output_relative_path(
    root: Path, output: Path, git_admin_dirs: tuple[Path, ...]
) -> str | None:
    """Validate output boundaries and return its source-relative path."""
    root_resolved = root.resolve()
    output_resolved = output.resolve()
    if any(_contains_path(admin_dir, output_resolved) for admin_dir in git_admin_dirs):
        raise CaptureUsageError("output directory must not be inside Git metadata")
    if output_resolved == root_resolved or (
        output_resolved.exists() and output_resolved.samefile(root_resolved)
    ):
        raise CaptureUsageError("output directory must not be the source repository root")
    if not _contains_path(root_resolved, output_resolved):
        return None
    try:
        return output_resolved.relative_to(root_resolved).as_posix()
    except ValueError as e:
        raise CaptureUsageError(
            "source-local output must use the repository's canonical path spelling"
        ) from e


def _source_status_pathspec(root: Path, relative_output: str | None) -> list[str]:
    """Build a clean-tree pathspec for the sole declared write exception."""
    if relative_output is None:
        return []
    tracked = _git(root, ["--literal-pathspecs", "ls-files", "-z"])
    output = root / relative_output
    if any(
        _contains_path(output, root / tracked_path)
        for tracked_path in tracked.removesuffix("\0").split("\0")
        if tracked_path
    ):
        raise CaptureUsageError(
            "output directory inside the source repository must not contain "
            "tracked paths"
        )
    return ["--", ".", f":(exclude,top,literal){relative_output}"]


def _cleanup_worktree(root: Path, state: _WorktreeState) -> None:
    """Remove a possible registration and open the parent deletion gate."""
    remove_error: GitFailed | None = None
    try:
        _git(root, ["worktree", "remove", "--force", str(state.worktree)])
    except GitFailed as e:
        remove_error = e
    state.observe_registration(_worktree_registered(root, state.worktree))
    if state.registration is not _Registration.ABSENT:
        detail = f": {remove_error}" if remove_error is not None else ""
        raise CleanupFailed(
            f"worktree cleanup unconfirmed; retained at {state.worktree}{detail}"
        ) from remove_error


def _add_exception_note(error: BaseException, note: str) -> None:
    """Attach cleanup context without allowing diagnostics to mask an error."""
    with contextlib.suppress(BaseException):
        error.add_note(note)


def capture(
    *,
    repo: Path,
    fix_sha: str,
    name: str | None,
    contract: str | None,
    output: Path,
) -> CaptureRecord:
    """Capture a fixing commit as a task; write the record; return it.

    Usage errors (REPO_NOT_GIT, REPO_UNBORN, SHA not a commit, invalid or
    underivable name) raise CaptureUsageError and write nothing. Refusals
    and success write a capture record; the CLI maps outcome to exit code.
    """
    repo_abs = str(Path(repo).resolve())
    output = Path(output)
    checks: CheckOutcomes = {name: "not-run" for name in CHECK_NAMES}
    result: CaptureRecord | None = None
    pending_usage: CaptureUsageError | None = None
    active_exception: BaseException | None = None
    state: _WorktreeState | None = None
    task_owned = False
    base_sha = ""
    resolved_fix = ""

    def refused(code: CaptureCode, message: str) -> CaptureRecord:
        return CaptureRecord(
            version=1,
            outcome=CaptureOutcome.REFUSED,
            code=code,
            message=message,
            repo=repo_abs,
            base_sha=base_sha or None,
            fix_sha=resolved_fix or None,
            task_dir=None,
            oracle=None,
            expected_test_ids=None,
            check_outcomes=dict(checks),
        )

    # Pin (usage errors here write nothing: no task name exists yet)
    try:
        root = _git_path(_git(repo, ["rev-parse", "--show-toplevel"]))
    except GitFailed:
        raise CaptureUsageError(f"not a git repository: {repo_abs}") from None
    try:
        _git(root, ["rev-parse", "--verify", "--quiet", "HEAD^{commit}"])
    except GitFailed:
        raise CaptureUsageError(f"repository has no commits: {repo_abs}") from None
    try:
        git_dir = _git_path(
            _git(root, ["rev-parse", "--absolute-git-dir"])
        ).resolve()
        common_raw = _git_path(_git(root, ["rev-parse", "--git-common-dir"]))
    except GitFailed:
        raise CaptureUsageError(
            f"cannot locate Git metadata for repository: {repo_abs}"
        ) from None
    common_dir = (
        common_raw.resolve()
        if common_raw.is_absolute()
        else (root / common_raw).resolve()
    )
    try:
        resolved_fix = _git(
            root, ["rev-parse", "--verify", "--quiet", f"{fix_sha}^{{commit}}"]
        ).strip()
    except GitFailed:
        raise CaptureUsageError(f"not a commit in the repository: {fix_sha}") from None
    try:
        ancestry = _git(
            root, ["rev-list", "--parents", "-n", "1", resolved_fix]
        ).split()
    except GitFailed:
        raise CaptureUsageError(
            f"cannot inspect parent of fixing commit: {resolved_fix}"
        ) from None
    if not ancestry or ancestry[0] != resolved_fix:
        raise CaptureUsageError(
            f"cannot inspect parent of fixing commit: {resolved_fix}"
        )
    base_sha = ancestry[1] if len(ancestry) > 1 else ""
    # NO_PARENT is a refusal, not usage: the fix resolved, so a name exists
    # and the record is named (spec check 1); base_sha stays empty and the
    # preflight raises NoParent.
    try:
        subject = _git(root, ["log", "-1", "--format=%s", resolved_fix]).strip()
    except GitFailed:
        raise CaptureUsageError(
            f"cannot inspect fixing commit: {resolved_fix}"
        ) from None
    if name is None:
        slug = slugify_subject(subject)
        if slug is None or not is_valid_task_name(slug):
            raise CaptureUsageError(
                f"cannot derive a task name from subject: {subject!r}"
            )
        name = slug
    elif not is_valid_task_name(name):
        raise CaptureUsageError(f"invalid task name: {name}")
    if contract is None:
        contract = subject
    task_dir = output / name
    record_path = output / f"{name}.capture.json"

    if os.path.lexists(task_dir) or os.path.lexists(record_path):
        raise CaptureUsageError(f"task already exists: {name}")
    relative_output = _output_relative_path(root, output, (git_dir, common_dir))
    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise CaptureUsageError(f"cannot create output directory: {e}") from e

    try:
        status_pathspec = _source_status_pathspec(root, relative_output)
        # Preflight (check 1)
        checks["source_preflight"] = "passed"
        try:
            status = _git(
                root,
                [
                    "--no-optional-locks",
                    "status",
                    "--porcelain=v1",
                    "-z",
                    "--untracked-files=all",
                    "--ignore-submodules=none",
                    *status_pathspec,
                ],
            )
            if status:
                raise RepoDirty("source repository is dirty")
            if not base_sha:
                raise NoParent(f"fix has no parent (root commit): {resolved_fix}")
            metadata = _git(
                root,
                [
                    "diff",
                    "--name-status",
                    "-z",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--find-renames",
                    "--find-copies-harder",
                    f"{base_sha}..{resolved_fix}",
                ],
            )
            source_changes = without_test_changes(parse_name_status_z(metadata))
            if not source_changes:
                raise NoSourceChange("fix touches only test paths")
            selected_paths = tuple(
                dict.fromkeys(
                    path
                    for change in source_changes
                    for path in (change.old_path, change.new_path)
                )
            )
            source_paths = selected_paths
            known_good_text = _git(
                root,
                [
                    "-c",
                    "core.quotePath=true",
                    "--literal-pathspecs",
                    "diff",
                    "--binary",
                    "--full-index",
                    "--no-color",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--src-prefix=a/",
                    "--dst-prefix=b/",
                    "--find-renames",
                    "--find-copies-harder",
                    f"{base_sha}..{resolved_fix}",
                    "--",
                    *selected_paths,
                ],
            )
        except CaptureRefused:
            checks["source_preflight"] = "failed"
            raise
        except PatchParseError as e:
            checks["source_preflight"] = "failed"
            raise GitFailed(str(e)) from e

        # Worktree + materialize + verify
        parent = _safe_temp_parent(root)
        state = _WorktreeState(parent=parent, worktree=parent / "worktree")
        state.begin_add()
        _git(
            root,
            [
                "-c",
                "core.sparseCheckout=false",
                "worktree",
                "add",
                "--detach",
                str(state.worktree),
                base_sha,
            ],
        )
        state.observe_registration(_worktree_registered(root, state.worktree))
        if state.registration is not _Registration.PRESENT:
            raise GitFailed("Git did not confirm the temporary worktree registration")
        base_staging = parent / "base"
        try:
            shutil.copytree(
                state.worktree,
                base_staging,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git"),
            )
        except OSError as e:
            raise ArtifactFailed(f"cannot materialize the base tree: {e}") from e
        # check 2: full-suite base run
        base_hook = _run_oracle(state.worktree, FULL_SUITE_ORACLE, parent)
        if base_hook.collect_errors:
            checks["base_oracle"] = "failed"
            raise OracleEnv(f"base oracle did not run: {base_hook.collect_errors[0]}")
        checks["base_oracle"] = "passed"
        # apply known-good in the worktree
        _git(state.worktree, ["apply", "-"], input_text=known_good_text)
        # check 3: full-suite fixed run, discriminating set
        fixed_hook = _run_oracle(state.worktree, FULL_SUITE_ORACLE, parent)
        if fixed_hook.collect_errors:
            checks["un_done_at_base"] = "failed"
            raise NotWinnable(
                f"fixed oracle did not run: {fixed_hook.collect_errors[0]}"
            )
        ids = discriminating_set(base_hook, fixed_hook)
        if not ids:
            checks["un_done_at_base"] = "failed"
            raise NoDiscriminatingTests(
                "no tests fail at base and pass with the fix (task at or near ceiling)"
            )
        checks["un_done_at_base"] = "passed"
        # check 4: recorded restricted oracle passes every discriminating ID
        oracle_cmd = recorded_oracle(ids)
        restricted_hook = _run_oracle(state.worktree, oracle_cmd, parent)
        if restricted_hook.collect_errors:
            checks["winnable"] = "failed"
            raise NotWinnable(
                f"recorded oracle did not run: {restricted_hook.collect_errors[0]}"
            )
        failing = {
            test_id
            for test_id, outcome in restricted_hook.outcomes.items()
            if outcome in ("failed", "error", "skipped")
        } | (set(ids) - set(restricted_hook.executed_test_ids))
        if failing:
            checks["winnable"] = "failed"
            raise NotWinnable(
                f"recorded oracle did not pass: failing {sorted(failing)}"
            )
        checks["winnable"] = "passed"
        result = CaptureRecord(
            version=1,
            outcome=CaptureOutcome.CAPTURED,
            code=CaptureCode.OK,
            message="task captured",
            repo=repo_abs,
            base_sha=base_sha,
            fix_sha=resolved_fix,
            task_dir=str(task_dir),
            oracle=oracle_cmd,
            expected_test_ids=ids,
            check_outcomes=dict(checks),
        )
        # write task dir
        try:
            try:
                task_dir.mkdir(parents=True)
            except FileExistsError as e:
                raise CaptureUsageError(f"task already exists: {name}") from e
            task_owned = True
            (task_dir / "fixtures").mkdir()
            shutil.move(str(base_staging), str(task_dir / "base"))
            (task_dir / "fixtures" / "known-good.patch").write_bytes(
                os.fsencode(known_good_text)
            )
            manifest = {
                "name": name,
                "contract": contract,
                "oracle": list(oracle_cmd),
                "expected_test_ids": list(ids),
                "source_paths": list(source_paths),
                "fixtures": {"known_good": "fixtures/known-good.patch"},
                "provenance": {
                    "repo": str(Path(repo).resolve()),
                    "base_sha": base_sha,
                    "fix_sha": resolved_fix,
                },
            }
            (task_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n"
            )
        except OSError as e:
            if task_owned:
                try:
                    shutil.rmtree(task_dir)
                except OSError as cleanup_error:
                    raise CleanupFailed(
                        "cannot write task artifacts and cannot remove the partial "
                        f"task retained at {task_dir}: {cleanup_error}"
                    ) from e
                task_owned = False
            raise ArtifactFailed(f"cannot write task artifacts: {e}") from e
        except BaseException as unexpected:
            if task_owned:
                try:
                    shutil.rmtree(task_dir)
                    task_owned = False
                except BaseException as cleanup_error:
                    _add_exception_note(
                        unexpected,
                        "task rollback raised "
                        f"{type(cleanup_error).__name__}: {cleanup_error}; "
                        f"recovery state unknown at {task_dir}",
                    )
            raise
    except CaptureUsageError as e:
        pending_usage = e
        result = None
    except CaptureRefused as e:
        try:
            result = (
                merge_cleanup_failure(result, str(e))
                if isinstance(e, CleanupFailed) and result is not None
                else refused(e.code, str(e))
            )
        except BaseException as unexpected:
            active_exception = unexpected
            raise
    except BaseException as unexpected:
        active_exception = unexpected
        raise
    finally:
        if state is not None and state.registration is not _Registration.ABSENT:
            try:
                _cleanup_worktree(root, state)
            except CleanupFailed as ce:
                if active_exception is not None:
                    _add_exception_note(active_exception, str(ce))
                elif result is not None:
                    result = merge_cleanup_failure(result, str(ce))
                else:
                    usage_error = cast("CaptureUsageError", pending_usage)
                    result = refused(
                        CaptureCode.CLEANUP_FAILED,
                        f"{ce}; displaced usage error: {usage_error}",
                    )
            except BaseException as cleanup_error:
                if active_exception is None:
                    raise
                _add_exception_note(
                    active_exception,
                    "worktree cleanup raised "
                    f"{type(cleanup_error).__name__}: {cleanup_error}; "
                    f"recovery state unknown at {state.worktree}",
                )
        if state is not None and state.registration is _Registration.ABSENT:
            try:
                shutil.rmtree(state.parent)
            except OSError as e:
                cleanup = f"temporary directory cleanup failed; retained at {state.parent}: {e}"
                if active_exception is not None:
                    _add_exception_note(active_exception, cleanup)
                elif result is not None:
                    result = merge_cleanup_failure(result, cleanup)
                else:
                    usage_error = cast("CaptureUsageError", pending_usage)
                    result = refused(
                        CaptureCode.CLEANUP_FAILED,
                        f"{cleanup}; displaced usage error: {usage_error}",
                    )
            except BaseException as cleanup_error:
                if active_exception is None:
                    raise
                _add_exception_note(
                    active_exception,
                    "temporary directory cleanup raised "
                    f"{type(cleanup_error).__name__}: {cleanup_error}; "
                    f"recovery state unknown at {state.parent}",
                )

    if pending_usage is not None and result is None:
        raise pending_usage
    final_result = cast("CaptureRecord", result)
    try:
        write_capture_record(record_path, final_result)
    except FileExistsError as e:
        if final_result.code is CaptureCode.CLEANUP_FAILED:
            raise CleanupFailed(
                f"{final_result.message}; capture record publication also failed: {e}"
            ) from e
        if task_owned:
            try:
                shutil.rmtree(task_dir)
            except OSError as cleanup_error:
                raise CleanupFailed(
                    "capture record collision and task rollback failed; "
                    f"task retained at {task_dir}: {cleanup_error}"
                ) from e
        raise CaptureUsageError(f"task already exists: {name}") from e
    except OSError as e:
        if final_result.code is CaptureCode.CLEANUP_FAILED:
            raise CleanupFailed(
                f"{final_result.message}; capture record publication also failed: {e}"
            ) from e
        if task_owned:
            try:
                shutil.rmtree(task_dir)
            except OSError as cleanup_error:
                raise CleanupFailed(
                    "capture record publication and task rollback failed; "
                    f"task retained at {task_dir}: {cleanup_error}"
                ) from e
        raise ArtifactFailed(f"cannot publish capture record: {e}") from e
    except BaseException as unexpected:
        if task_owned:
            try:
                shutil.rmtree(task_dir)
            except BaseException as cleanup_error:
                _add_exception_note(
                    unexpected,
                    "task rollback raised "
                    f"{type(cleanup_error).__name__}: {cleanup_error}; "
                    f"recovery state unknown at {task_dir}",
                )
        raise
    return final_result
