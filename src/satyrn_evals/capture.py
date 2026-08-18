"""Capture orchestration: turn a fixing commit into a valid task.

The lifecycle, re-earned from the satyrn-engine E3 delivery spec: pin the
commits, preflight a clean source, derive the fix diff, add a detached
worktree at the parent, materialize the base, run the oracle three times,
clean up with E3's precedence, and write the capture record. The source
repository's working tree, index, branch, and HEAD are never touched.
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
from pathlib import Path

from satyrn_evals import oracle_hook
from satyrn_evals.capture_record import (
    CHECK_NAMES,
    CaptureOutcome,
    CaptureRecord,
    merge_cleanup_failure,
    write_capture_record,
)
from satyrn_evals.diff_filter import strip_test_hunks
from satyrn_evals.discriminating import (
    FULL_SUITE_ORACLE,
    discriminating_set,
    recorded_oracle,
)
from satyrn_evals.errors import (
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
    RepoDirty,
)
from satyrn_evals.manifest import is_valid_task_name
from satyrn_evals.verdict import HookResult, load_hook_result

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_subject(subject: str) -> str | None:
    """Task-name slug from a commit subject; None when underivable."""
    slug = _SLUG_RE.sub("-", subject.strip().lower()).strip("-")
    return slug or None


def _local_env_vars() -> set[str]:
    proc = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True
    )
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
    """Run git from the source root with stripped env; raise GitFailed."""
    env = _clean_env()
    proc = subprocess.run(
        ["git", *args], cwd=root, env=env, capture_output=True, text=True, input=input_text
    )
    if proc.returncode != 0:
        raise GitFailed(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _git_worktree(root: Path, args: list[str], empty_hooks: Path) -> str:
    """Git for worktree add/remove: hooksPath pointed at an engine-owned empty dir."""
    env = _clean_env()
    proc = subprocess.run(
        ["git", "-c", f"core.hooksPath={empty_hooks}", *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitFailed(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _run_oracle(worktree: Path, cmd: tuple[str, ...]) -> HookResult:
    """Run an oracle in the worktree; V1's hook-result machinery.

    A unique reserved-but-unlinked hook path, the run-start timestamp, and
    the stale-file rejection — the verdict never comes from stdout or an
    exit code. Raises OracleEnv when no hook result exists.
    """
    fd, hook_path = tempfile.mkstemp(prefix="satyrn-hook-", suffix=".json")
    os.close(fd)
    os.unlink(hook_path)
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
        Path(hook_path).unlink(missing_ok=True)


def _cleanup_worktree(root: Path, worktree: Path, empty_hooks: Path) -> None:
    """git worktree remove --force; raises CleanupFailed naming the path."""
    try:
        _git_worktree(root, ["worktree", "remove", "--force", str(worktree)], empty_hooks)
    except GitFailed as e:
        raise CleanupFailed(
            f"worktree cleanup failed; retained at {worktree}: {e}"
        ) from e


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
    checks: dict[str, str] = {n: "not-run" for n in CHECK_NAMES}
    result: CaptureRecord | None = None
    tmp_root: Path | None = None
    worktree: Path | None = None
    worktree_registered = False
    base_sha = ""
    resolved_fix = ""

    def refused(code: str, message: str) -> CaptureRecord:
        nonlocal result
        record = CaptureRecord(
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
        write_capture_record(output / f"{name}.capture.json", record)
        result = record
        return record

    # Pin (usage errors here write nothing: no task name exists yet)
    try:
        root = Path(_git(repo, ["rev-parse", "--show-toplevel"]).strip())
    except GitFailed:
        raise CaptureUsageError(f"not a git repository: {repo_abs}") from None
    try:
        _git(root, ["rev-parse", "--verify", "--quiet", "HEAD^{commit}"])
    except GitFailed:
        raise CaptureUsageError(f"repository has no commits: {repo_abs}") from None
    try:
        resolved_fix = _git(
            root, ["rev-parse", "--verify", "--quiet", f"{fix_sha}^{{commit}}"]
        ).strip()
    except GitFailed:
        raise CaptureUsageError(f"not a commit in the repository: {fix_sha}") from None
    with contextlib.suppress(GitFailed):
        base_sha = _git(
            root, ["rev-parse", "--verify", "--quiet", f"{resolved_fix}^"]
        ).strip()
    # NO_PARENT is a refusal, not usage: the fix resolved, so a name exists
    # and the record is named (spec check 1); base_sha stays empty and the
    # preflight raises NoParent.
    subject = _git(root, ["log", "-1", "--format=%s", resolved_fix]).strip()
    if name is None:
        slug = slugify_subject(subject)
        if slug is None or not is_valid_task_name(slug):
            raise CaptureUsageError(f"cannot derive a task name from subject: {subject!r}")
        name = slug
    elif not is_valid_task_name(name):
        raise CaptureUsageError(f"invalid task name: {name}")
    if contract is None:
        contract = subject
    output.mkdir(parents=True, exist_ok=True)
    task_dir = output / name

    try:
        # TASK_EXISTS is a refusal before checks begin (name exists now)
        if task_dir.exists() or (output / f"{name}.capture.json").exists():
            return refused("TASK_EXISTS", f"task already exists: {name}")
        # Preflight (check 1)
        checks["source_preflight"] = "passed"
        try:
            status = _git(
                root,
                [
                    "--no-optional-locks", "status", "--porcelain=v1", "-z",
                    "--untracked-files=all", "--ignore-submodules=none",
                ],
            )
            if status:
                raise RepoDirty("source repository is dirty")
            if not base_sha:
                raise NoParent(f"fix has no parent (root commit): {resolved_fix}")
            fix_diff = _git(root, ["diff", f"{base_sha}..{resolved_fix}"])
            source_text, source_paths = strip_test_hunks(fix_diff)
            if not source_paths:
                raise NoSourceChange("fix touches only test paths")
        except CaptureRefused:
            checks["source_preflight"] = "failed"
            raise
        except GitFailed as e:
            checks["source_preflight"] = "failed"
            raise GitFailed(str(e)) from e

        # Derive
        known_good_text = source_text

        # Worktree + materialize + verify
        tmp_root = Path(tempfile.mkdtemp(prefix="satyrn-capture-"))
        empty_hooks = tmp_root / "empty-hooks"
        empty_hooks.mkdir()
        worktree = tmp_root / "worktree"
        _git_worktree(
            root, ["worktree", "add", "--detach", str(worktree), base_sha], empty_hooks
        )
        worktree_registered = True
        base_staging = tmp_root / "base"
        shutil.copytree(worktree, base_staging, ignore=shutil.ignore_patterns(".git"))
        # check 2: full-suite base run
        base_hook = _run_oracle(worktree, FULL_SUITE_ORACLE)
        if base_hook.collect_errors:
            checks["base_oracle"] = "failed"
            raise OracleEnv(f"base oracle did not run: {base_hook.collect_errors[0]}")
        checks["base_oracle"] = "passed"
        # apply known-good in the worktree
        _git(worktree, ["apply", "-"], input_text=known_good_text)
        # check 3: full-suite fixed run, discriminating set
        fixed_hook = _run_oracle(worktree, FULL_SUITE_ORACLE)
        if fixed_hook.collect_errors:
            checks["un_done_at_base"] = "failed"
            raise NotWinnable(f"fixed oracle did not run: {fixed_hook.collect_errors[0]}")
        ids = discriminating_set(base_hook, fixed_hook)
        if not ids:
            checks["un_done_at_base"] = "failed"
            raise NoDiscriminatingTests(
                "no tests fail at base and pass with the fix (task at or near ceiling)"
            )
        checks["un_done_at_base"] = "passed"
        # check 4: recorded restricted oracle passes every discriminating ID
        oracle_cmd = recorded_oracle(ids)
        restricted_hook = _run_oracle(worktree, oracle_cmd)
        if restricted_hook.collect_errors:
            checks["winnable"] = "failed"
            raise NotWinnable(
                f"recorded oracle did not run: {restricted_hook.collect_errors[0]}"
            )
        failing = set(
            i for i, o in restricted_hook.outcomes.items() if o in ("failed", "error", "skipped")
        ) | (set(ids) - set(restricted_hook.executed_test_ids))
        if failing:
            checks["winnable"] = "failed"
            raise NotWinnable(f"recorded oracle did not pass: failing {sorted(failing)}")
        checks["winnable"] = "passed"
        # write task dir
        task_dir.mkdir(parents=True)
        (task_dir / "fixtures").mkdir()
        shutil.move(str(base_staging), str(task_dir / "base"))
        (task_dir / "fixtures" / "known-good.patch").write_text(known_good_text)
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
        (task_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        record = CaptureRecord(
            version=1,
            outcome=CaptureOutcome.CAPTURED,
            code="OK",
            message="task captured",
            repo=repo_abs,
            base_sha=base_sha,
            fix_sha=resolved_fix,
            task_dir=str(task_dir),
            oracle=oracle_cmd,
            expected_test_ids=ids,
            check_outcomes=dict(checks),
        )
        write_capture_record(output / f"{name}.capture.json", record)
        result = record
        return record
    except CaptureRefused as e:
        return refused(e.code, str(e))
    except GitFailed as e:
        return refused("GIT_FAILED", str(e))
    finally:
        if worktree is not None and worktree_registered and tmp_root is not None:
            try:
                _cleanup_worktree(root, worktree, tmp_root / "empty-hooks")
                worktree_registered = False
            except CleanupFailed as ce:
                # cleanup failure replaces any pending result (E3 precedence);
                # the guard STAYS True so the retained worktree and its temp
                # root survive for the manual recovery in the record message
                if result is not None:
                    write_capture_record(
                        output / f"{name}.capture.json",
                        merge_cleanup_failure(result, str(ce)),
                    )
                else:
                    refused("CLEANUP_FAILED", str(ce))
        if tmp_root is not None and not worktree_registered:
            shutil.rmtree(tmp_root, ignore_errors=True)
