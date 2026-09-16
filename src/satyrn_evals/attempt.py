"""Attempt orchestration: run a command through the engine seam, preserve
its patch and transcript, grade the delivered patch offline, and record.

The pure decision logic (refusal codes, directory naming) lives here so the
default test tier can exercise it without spawning anything. The seam is
env-var paths: SATYRN_TASK_NAME/CONTRACT are inputs; SATYRN_ATTEMPT_PATCH/
TRANSCRIPT are where the command writes its delivery.
"""

import hashlib
import json
import os
import shutil
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    DeadlinePhase,
    DeadlineProvenance,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell import CELL_PARENT_ENV, ISOLATION_ENV, Isolation
from satyrn_evals.deadline import AttemptDeadline, AttemptDeadlineExceeded
from satyrn_evals.engine_contract import (
    engine_contract_path,
    render_engine_contract,
    write_engine_contract,
)
from satyrn_evals.errors import PatchParseError, SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import TaskManifest, load_manifest, resolve_task
from satyrn_evals.model_error import infrastructure_failure
from satyrn_evals.overlay import load_overlay
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.receipt import patch_digest
from satyrn_evals.timeline import TIMELINE_NAME
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import (
    DEFAULT_TIMEOUT,
    TRIPPED_PATCH_NAME,
    PreparedWorkspace,
    WorkspaceCode,
    WorkspacePrepareError,
    WorkspaceReleaseError,
    WorkspaceResult,
    prepare_workspace,
    release_workspace,
    run_prepared_command,
)

TASK_NAME_ENV = "SATYRN_TASK_NAME"
TASK_CONTRACT_ENV = "SATYRN_TASK_CONTRACT"
PATCH_ENV = "SATYRN_ATTEMPT_PATCH"
TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"
BASE_SHA_ENV = "SATYRN_WORKSPACE_BASE_SHA"
#: Under isolation the command's transcript is written here, beside the
#: worktree where the cell user can write, and copied into the attempt
#: directory as soon as the command returns.
LIVE_TRANSCRIPT_NAME = "transcript.txt"

#: The receipt the tripped secondary writes. Never `receipt.json`: that name is
#: the delivered patch's, and `regrade` reads it as the cell's own verdict.
TRIPPED_RECEIPT_NAME = "tripped-receipt.json"

type SelectedContract = tuple[str | None, str]

_WORKSPACE_ATTEMPT_CODES: dict[WorkspaceCode, AttemptCode] = {
    WorkspaceCode.WORKSPACE_FAILED: AttemptCode.WORKSPACE_FAILED,
    WorkspaceCode.COMMAND_TIMEOUT: AttemptCode.COMMAND_TIMEOUT,
    WorkspaceCode.REPEAT_LIMIT: AttemptCode.REPEAT_LIMIT,
    WorkspaceCode.BUDGET_EXCEEDED: AttemptCode.BUDGET_EXCEEDED,
    WorkspaceCode.CLEANUP_FAILED: AttemptCode.CLEANUP_FAILED,
}


@contextmanager
def _attempt_environment(
    attempt_dir: Path, deadline: AttemptDeadline | None
) -> Iterator[str]:
    """Own the executor environment beneath durable attempt evidence.

    It can contain the executor's project environment and is therefore needed
    to diagnose a stopped attempt. The normal lifecycle performs bounded
    cleanup before returning its durable record; this fallback only handles
    unbounded and exceptional paths.
    """
    root = attempt_dir / "environment"
    root.mkdir()
    try:
        yield os.fspath(root)
    finally:
        if root.exists() and (deadline is None or not deadline.expired):
            shutil.rmtree(root)


def resolve_contract(manifest: TaskManifest, rung: str | None) -> SelectedContract:
    """The (rung key, exact contract text) an attempt exports (V11a spec §4).

    ``None`` selects the manifest's default ``contract`` and records a null
    rung. A rung against a task with no ``contracts`` map, or a key the map
    does not hold, is a usage error naming the task and the available keys —
    never a silent fallback to the default text.
    """
    if rung is None:
        return None, manifest.contract
    match manifest.contracts.get(rung):
        case str() as text:
            return rung, text
        case _ if not manifest.contracts:
            raise UsageError(
                f"task {manifest.name} declares no contracts; "
                f"--rung {rung} is not available"
            )
        case _:
            available = ", ".join(sorted(manifest.contracts))
            raise UsageError(
                f"unknown rung {rung} for task {manifest.name}; "
                f"available rungs: {available}"
            )


def contract_digest(text: str) -> str:
    """SHA-256 of the exact selected contract text, UTF-8 (spec §5)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_engine_wrapper_command(command: list[str]) -> bool:
    """Whether COMMAND is evals' own E5 wrapper: ``uv run --project ENGINE
    satyrn-engine ...`` (`tests/integration/test_attempt.py::_engine_command`
    builds exactly this shape; nothing else in this codebase does).

    Bare-Pi (Baseline) commands run the model's own binary directly and must
    keep receiving ``UV_PROJECT_ENVIRONMENT`` — that is the model-visible
    isolation for its own nested ``uv run`` calls. The engine wrapper is a
    trusted command evals itself constructs, naming its own ``--project``;
    redirecting *its* ``UV_PROJECT_ENVIRONMENT`` onto the attempt's private,
    empty per-attempt directory makes ``uv`` treat that directory as the
    engine project's own virtualenv and, under ``UV_NO_SYNC=1``, fail to spawn
    ``satyrn-engine`` at all (Task 13 report, "Root cause").
    """
    return (
        len(command) >= 5
        and Path(command[0]).name == "uv"
        and command[1] == "run"
        and command[2] == "--project"
        and command[4] == "satyrn-engine"
    )


def _collect_live_transcript(live: Path, transcript_path: Path) -> None:
    """Copy an isolated command's transcript into the attempt directory, if it wrote one."""
    if live != transcript_path and live.is_file():
        shutil.copyfile(live, transcript_path)


def _add_exception_note(error: BaseException, note: str) -> None:
    """Attach recovery evidence without replacing the primary exception."""
    with suppress(BaseException):
        error.add_note(note)


def decide_refusal(
    patch_text: str | None, transcript_text: str | None
) -> AttemptCode | None:
    """Refusal code when the delivered artifacts are incomplete; None to proceed.

    An input of None means the file was absent. Patch checks run first, then
    transcript checks (spec: "the first failure refuses").
    """
    if not patch_text or not patch_text.strip():
        return AttemptCode.NO_PATCH
    try:
        parse_patch_paths(patch_text)
    except PatchParseError:
        return AttemptCode.PATCH_INVALID
    if transcript_text is None:
        return AttemptCode.TRANSCRIPT_MISSING
    if not transcript_text.strip():
        return AttemptCode.TRANSCRIPT_EMPTY
    return None


def attempt_dir_name(task: str, when: datetime) -> str:
    """Attempt directory name: <task>-<UTC microsecond timestamp>."""
    stamp = when.astimezone(UTC).strftime("%Y%m%d-%H%M%S-%f")
    return f"{task}-{stamp}"


def attempt(
    *,
    task: str,
    tasks_root: Path,
    output: Path,
    command: list[str],
    timeout: float = DEFAULT_TIMEOUT,
    rung: str | None = None,
    max_repeated_calls: int | None = None,
    attempt_timeout: float | None = None,
    budget: AttemptBudget | None = None,
    isolation: Isolation = Isolation.LOCAL,
) -> AttemptRecord:
    """Run an unbounded attempt through the stable public API."""
    return _attempt(
        task=task,
        tasks_root=tasks_root,
        output=output,
        command=command,
        timeout=timeout,
        rung=rung,
        max_repeated_calls=max_repeated_calls,
        attempt_timeout=attempt_timeout,
        budget=budget,
        isolation=isolation,
    )


def _attempt(
    *,
    task: str,
    tasks_root: Path,
    output: Path,
    command: list[str],
    timeout: float = DEFAULT_TIMEOUT,
    rung: str | None = None,
    max_repeated_calls: int | None = None,
    deadline: AttemptDeadline | None = None,
    attempt_timeout: float | None = None,
    budget: AttemptBudget | None = None,
    isolation: Isolation = Isolation.LOCAL,
) -> AttemptRecord:
    """Run COMMAND against TASK, preserve patch + transcript, grade, and record.

    Usage errors (unknown task, empty command, command cannot start) raise
    UsageError and write nothing — a start failure also removes the
    freshly-created attempt directory. Refusals and successes write an
    attempt record; the CLI maps outcome/verdict to an exit code.
    """
    task_dir = resolve_task(task, tasks_root)
    manifest = load_manifest(task_dir)
    selected_rung, contract_text = resolve_contract(manifest, rung)
    digest = contract_digest(contract_text)
    if not command:
        raise UsageError("attempt command is empty")
    if deadline is None and attempt_timeout is not None:
        deadline = AttemptDeadline(attempt_timeout)
    output = Path(os.path.abspath(output))
    output.mkdir(parents=True, exist_ok=True)
    attempt_dir = output / attempt_dir_name(manifest.name, datetime.now(UTC))
    attempt_dir.mkdir()
    patch_path = attempt_dir / "patch.diff"
    transcript_path = attempt_dir / "transcript.txt"

    env = dict(os.environ)
    if isolation is Isolation.LOCAL:
        # F8/R13: a stray SATYRN_ISOLATION/SATYRN_CELL_PARENT in the
        # maintainer's own shell must never reach a local-profile command --
        # an adapter reading it would believe it is isolated and try to run
        # as the cell. Isolated attempts set these explicitly below.
        env[ISOLATION_ENV] = Isolation.LOCAL.value
        env.pop(CELL_PARENT_ENV, None)
    env[TASK_NAME_ENV] = manifest.name
    env[TASK_CONTRACT_ENV] = contract_text
    env[PATCH_ENV] = str(patch_path)
    env[TRANSCRIPT_ENV] = str(transcript_path)
    # Keep uv's project environment and Python bytecode out of the model
    # workspace. Pi inherits this temporary location for any ``uv run`` it
    # invokes, but its active evaluator venv is removed separately.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")

    effective_command = list(command)
    rendered_contract: bytes | None = None
    if manifest.engine_contract is not None:
        # A hand-authored contract keeps today's behaviour exactly.
        effective_command.append(
            os.fspath(Path(os.path.abspath(task_dir / manifest.engine_contract)))
        )
    else:
        # Generated from manifest + selected rung, written once at a path
        # keyed by the SHA-256 of its own bytes so every cell of a run
        # records the same command (proposal correction 8).
        rendered_contract = render_engine_contract(
            task_dir, manifest, rung=selected_rung, contract_text=contract_text
        )
        effective_command.append(
            os.fspath(engine_contract_path(output, rendered_contract))
        )
    if deadline is not None:
        try:
            deadline.remaining(DeadlinePhase.SETUP)
        except AttemptDeadlineExceeded:
            return _write_deadline_refusal(
                attempt_dir=attempt_dir,
                patch_path=patch_path,
                transcript_path=transcript_path,
                manifest=manifest,
                effective_command=effective_command,
                timeout=timeout,
                rung=selected_rung,
                digest=digest,
                deadline=deadline,
            )
    if rendered_contract is not None:
        write_engine_contract(output, rendered_contract)

    workspace_lease: PreparedWorkspace | None = None
    with _attempt_environment(attempt_dir, deadline) as environment_root:
        env["UV_PROJECT_ENVIRONMENT"] = environment_root
        try:
            workspace_lease = prepare_workspace(
                base=task_dir / "base",
                protected_paths=(task_dir, output, Path.cwd()),
                environment=env,
                overlay=(
                    load_overlay(task_dir, manifest)
                    if manifest.oracle_visibility == "hidden"
                    else None
                ),
                deadline=deadline,
                isolation=isolation,
            )
        except WorkspacePrepareError as exc:
            if exc.deadline is not None:
                return _write_deadline_refusal(
                    attempt_dir=attempt_dir,
                    patch_path=patch_path,
                    transcript_path=transcript_path,
                    manifest=manifest,
                    effective_command=effective_command,
                    timeout=timeout,
                    rung=selected_rung,
                    digest=digest,
                    deadline=deadline,
                    retained_path=exc.retained_path,
                )
            if deadline is not None:
                try:
                    deadline.remaining(DeadlinePhase.SETUP)
                except AttemptDeadlineExceeded:
                    return _write_deadline_refusal(
                        attempt_dir=attempt_dir,
                        patch_path=patch_path,
                        transcript_path=transcript_path,
                        manifest=manifest,
                        effective_command=effective_command,
                        timeout=timeout,
                        rung=selected_rung,
                        digest=digest,
                        deadline=deadline,
                        retained_path=exc.retained_path,
                    )
            # Keep the legacy observable outcome: setup failures make a
            # durable WORKSPACE_FAILED record rather than escaping after the
            # attempt directory has been allocated.
            workspace = WorkspaceResult(
                (
                    WorkspaceCode.CLEANUP_FAILED
                    if exc.retained_path is not None
                    else WorkspaceCode.WORKSPACE_FAILED
                ),
                str(exc),
                None,
                None,
                exc.retained_path,
            )
        else:
            if _is_engine_wrapper_command(command):
                # The wrapper names its own --project; UV_PROJECT_ENVIRONMENT
                # is for the model's own nested uv run, not for uv finding
                # the engine itself. Popped here (not left out of `env`
                # above) so prepare_workspace still receives it for anything
                # that materializes the task workspace's environment.
                workspace_lease._environment.pop("UV_PROJECT_ENVIRONMENT", None)
            exported = {BASE_SHA_ENV: workspace_lease.base_sha}
            live_transcript = transcript_path
            if isolation is Isolation.ISOLATED:
                live_transcript = workspace_lease.parent / LIVE_TRANSCRIPT_NAME
                exported[ISOLATION_ENV] = isolation.value
                exported[CELL_PARENT_ENV] = os.fspath(workspace_lease.parent)
                exported[TRANSCRIPT_ENV] = os.fspath(live_transcript)
            try:
                try:
                    workspace = run_prepared_command(
                        workspace_lease,
                        command=effective_command,
                        timeout=timeout,
                        transcript=live_transcript,
                        max_repeated_calls=max_repeated_calls,
                        deadline=deadline,
                        extra_environment=exported,
                        budget=budget,
                        timeline=attempt_dir / TIMELINE_NAME,
                        tripped_patch=attempt_dir / TRIPPED_PATCH_NAME,
                    )
                finally:
                    _collect_live_transcript(live_transcript, transcript_path)
                if deadline is not None and workspace.code not in (
                    WorkspaceCode.COMMAND_TIMEOUT,
                    WorkspaceCode.REPEAT_LIMIT,
                    WorkspaceCode.BUDGET_EXCEEDED,
                ):
                    deadline.remaining(DeadlinePhase.COMMAND)
            except AttemptDeadlineExceeded:
                assert deadline is not None
                return _write_deadline_refusal(
                    attempt_dir=attempt_dir,
                    patch_path=patch_path,
                    transcript_path=transcript_path,
                    manifest=manifest,
                    effective_command=effective_command,
                    timeout=timeout,
                    rung=selected_rung,
                    digest=digest,
                    deadline=deadline,
                    command_exit=None,
                    workspace_base_sha=workspace_lease.base_sha,
                    retained_path=os.fspath(workspace_lease.parent),
                )
            except BaseException as exc:
                _release_after_exception(workspace_lease, exc, deadline=deadline)
                raise
        if workspace.code is WorkspaceCode.COMMAND_UNAVAILABLE:
            if deadline is not None:
                try:
                    deadline.remaining(DeadlinePhase.CLEANUP)
                except AttemptDeadlineExceeded:
                    assert workspace_lease is not None
                    return _write_deadline_refusal(
                        attempt_dir=attempt_dir,
                        patch_path=patch_path,
                        transcript_path=transcript_path,
                        manifest=manifest,
                        effective_command=effective_command,
                        timeout=timeout,
                        rung=selected_rung,
                        digest=digest,
                        deadline=deadline,
                        workspace_base_sha=workspace_lease.base_sha,
                        retained_path=os.fspath(workspace_lease.parent),
                    )
            try:
                retained_path, release_message = _release_attempt_workspace(
                    workspace_lease, deadline=deadline
                )
            except AttemptDeadlineExceeded:
                assert deadline is not None
                assert workspace_lease is not None
                return _write_deadline_refusal(
                    attempt_dir=attempt_dir,
                    patch_path=patch_path,
                    transcript_path=transcript_path,
                    manifest=manifest,
                    effective_command=effective_command,
                    timeout=timeout,
                    rung=selected_rung,
                    digest=digest,
                    deadline=deadline,
                    workspace_base_sha=workspace_lease.base_sha,
                    retained_path=os.fspath(workspace_lease.parent),
                )
            except BaseException as exc:
                assert workspace_lease is not None
                _add_exception_note(
                    exc,
                    "command start failed and workspace release is unconfirmed; "
                    f"retained at {workspace_lease.parent}",
                )
                raise
            if deadline is not None:
                try:
                    deadline.remaining(DeadlinePhase.CLEANUP)
                except AttemptDeadlineExceeded:
                    assert workspace_lease is not None
                    return _write_deadline_refusal(
                        attempt_dir=attempt_dir,
                        patch_path=patch_path,
                        transcript_path=transcript_path,
                        manifest=manifest,
                        effective_command=effective_command,
                        timeout=timeout,
                        rung=selected_rung,
                        digest=digest,
                        deadline=deadline,
                        workspace_base_sha=workspace_lease.base_sha,
                        retained_path=retained_path,
                    )
            workspace_lease = None
            if retained_path is None:
                # The command never started, so this private environment has
                # no attempt evidence.  It must be removed before retaining
                # the historic no-attempt-dir API outcome.
                shutil.rmtree(environment_root)
                attempt_dir.rmdir()
                raise UsageError(workspace.message)
            workspace = WorkspaceResult(
                WorkspaceCode.CLEANUP_FAILED,
                f"{release_message}; displaced {workspace.code}: {workspace.message}",
                None,
                workspace.base_sha,
                retained_path,
            )
        if deadline is not None:
            try:
                deadline.remaining(DeadlinePhase.PRESERVATION)
            except AttemptDeadlineExceeded:
                if workspace_lease is None:
                    _finish_attempt(
                        workspace=workspace,
                        task_dir=task_dir,
                        attempt_dir=attempt_dir,
                        patch_path=patch_path,
                        transcript_path=transcript_path,
                        manifest=manifest,
                        effective_command=effective_command,
                        timeout=timeout,
                        rung=selected_rung,
                        digest=digest,
                    )
                    return _retain_expired_record(
                        attempt_dir,
                        deadline,
                        Path(workspace.retained_path)
                        if workspace.retained_path is not None
                        else None,
                    )
                if workspace.code is not WorkspaceCode.OK:
                    _finish_attempt(
                        workspace=workspace,
                        task_dir=task_dir,
                        attempt_dir=attempt_dir,
                        patch_path=patch_path,
                        transcript_path=transcript_path,
                        manifest=manifest,
                        effective_command=effective_command,
                        timeout=timeout,
                        rung=selected_rung,
                        digest=digest,
                    )
                    return _retain_expired_record(
                        attempt_dir, deadline, workspace_lease.parent
                    )
                return _write_deadline_refusal(
                    attempt_dir=attempt_dir,
                    patch_path=patch_path,
                    transcript_path=transcript_path,
                    manifest=manifest,
                    effective_command=effective_command,
                    timeout=timeout,
                    rung=selected_rung,
                    digest=digest,
                    deadline=deadline,
                    command_exit=workspace.command_exit,
                    workspace_base_sha=workspace.base_sha,
                    retained_path=os.fspath(workspace_lease.parent),
                )
        try:
            record = _finish_attempt(
                workspace=workspace,
                task_dir=task_dir,
                attempt_dir=attempt_dir,
                patch_path=patch_path,
                transcript_path=transcript_path,
                manifest=manifest,
                effective_command=effective_command,
                timeout=timeout,
                rung=selected_rung,
                digest=digest,
                deadline=deadline,
            )
        except AttemptDeadlineExceeded:
            assert deadline is not None
            if workspace_lease is None:
                _finish_attempt(
                    workspace=workspace,
                    task_dir=task_dir,
                    attempt_dir=attempt_dir,
                    patch_path=patch_path,
                    transcript_path=transcript_path,
                    manifest=manifest,
                    effective_command=effective_command,
                    timeout=timeout,
                    rung=selected_rung,
                    digest=digest,
                )
                return _retain_expired_record(
                    attempt_dir,
                    deadline,
                    Path(workspace.retained_path)
                    if workspace.retained_path is not None
                    else None,
                )
            if (attempt_dir / "attempt.json").is_file():
                return _finalize_deadline_from_record(
                    attempt_dir, deadline, workspace_lease
                )
            if workspace.code is not WorkspaceCode.OK:
                _finish_attempt(
                    workspace=workspace,
                    task_dir=task_dir,
                    attempt_dir=attempt_dir,
                    patch_path=patch_path,
                    transcript_path=transcript_path,
                    manifest=manifest,
                    effective_command=effective_command,
                    timeout=timeout,
                    rung=selected_rung,
                    digest=digest,
                )
                return _retain_expired_record(
                    attempt_dir, deadline, workspace_lease.parent
                )
            return _write_deadline_refusal(
                attempt_dir=attempt_dir,
                patch_path=patch_path,
                transcript_path=transcript_path,
                manifest=manifest,
                effective_command=effective_command,
                timeout=timeout,
                rung=selected_rung,
                digest=digest,
                deadline=deadline,
                command_exit=workspace.command_exit,
                workspace_base_sha=workspace.base_sha,
                retained_path=os.fspath(workspace_lease.parent),
            )
        except BaseException as exc:
            if workspace_lease is not None:
                _release_after_exception(workspace_lease, exc, deadline=deadline)
            if workspace.code is WorkspaceCode.CLEANUP_FAILED:
                _add_exception_note(
                    exc,
                    f"{workspace.message}; retained at {workspace.retained_path}",
                )
            raise
        release_completed = False
        retained_path: str | None = None
        try:
            retained_path, release_message = _release_attempt_workspace(
                workspace_lease, deadline=deadline
            )
            release_completed = True
            if deadline is not None:
                deadline.remaining(DeadlinePhase.CLEANUP)
        except AttemptDeadlineExceeded:
            assert deadline is not None
            if workspace_lease is None:
                return _retain_expired_record(
                    attempt_dir,
                    deadline,
                    Path(retained_path) if retained_path is not None else None,
                )
            return _finalize_deadline_from_record(
                attempt_dir,
                deadline,
                workspace_lease,
                workspace_retained=(not release_completed or retained_path is not None),
                retained_path=retained_path,
            )
        except BaseException as exc:
            if workspace_lease is not None:
                _add_exception_note(
                    exc,
                    "workspace release is unconfirmed; "
                    f"retained at {workspace_lease.parent}; "
                    f"the durable attempt record remains at "
                    f"{attempt_dir / 'attempt.json'}",
                )
            raise
        if retained_path is not None:
            record = _record_release_retention(
                record,
                retained_path=retained_path,
                release_message=release_message,
            )
            try:
                write_attempt_record(attempt_dir / "attempt.json", record)
            except BaseException as exc:
                _add_exception_note(
                    exc,
                    f"{release_message}; retained at {retained_path}; "
                    f"the prior durable attempt record remains at "
                    f"{attempt_dir / 'attempt.json'}",
                )
                raise
        if deadline is not None:
            try:
                deadline.remaining(DeadlinePhase.CLEANUP)
            except AttemptDeadlineExceeded:
                if workspace_lease is None:
                    return _retain_expired_record(
                        attempt_dir,
                        deadline,
                        Path(retained_path) if retained_path is not None else None,
                    )
                return _finalize_deadline_from_record(
                    attempt_dir,
                    deadline,
                    workspace_lease,
                    workspace_retained=retained_path is not None,
                    retained_path=retained_path,
                )
        shutil.rmtree(environment_root)
        if deadline is not None:
            try:
                deadline.remaining(DeadlinePhase.CLEANUP)
            except AttemptDeadlineExceeded:
                if workspace_lease is None:
                    return _retain_expired_record(
                        attempt_dir,
                        deadline,
                        Path(retained_path) if retained_path is not None else None,
                    )
                return _finalize_deadline_from_record(
                    attempt_dir,
                    deadline,
                    workspace_lease,
                    workspace_retained=retained_path is not None,
                    retained_path=retained_path,
                )
        return record


def _release_attempt_workspace(
    workspace: PreparedWorkspace | None,
    *,
    deadline: AttemptDeadline | None = None,
) -> tuple[str | None, str | None]:
    """Release a lease after durable attempt evidence, naming any retention."""
    if workspace is None:
        return None, None
    try:
        retained_path = (
            release_workspace(workspace, deadline=deadline)
            if deadline is not None
            else release_workspace(workspace)
        )
    except WorkspaceReleaseError as exc:
        if exc.retained_path is None:
            raise
        return exc.retained_path, str(exc)
    if retained_path is None:
        return None, None
    return retained_path, "workspace cleanup was unsafe"


def _write_deadline_refusal(
    *,
    attempt_dir: Path,
    patch_path: Path,
    transcript_path: Path,
    manifest: TaskManifest,
    effective_command: list[str],
    timeout: float,
    rung: str | None,
    digest: str,
    deadline: AttemptDeadline,
    command_exit: int | None = None,
    workspace_base_sha: str | None = None,
    retained_path: str | None = None,
) -> AttemptRecord:
    """Finalize a pre-grade expiry from whatever evidence is already local."""
    expiry: AttemptDeadlineExceeded
    try:
        deadline.remaining(DeadlinePhase.PRESERVATION)
    except AttemptDeadlineExceeded as caught:
        expiry = caught
    else:
        raise AssertionError("deadline refusal requires an expired deadline")
    patch_bytes, _patch_error = _read_artifact(patch_path, "patch")
    transcript_bytes, _transcript_error = _read_artifact(transcript_path, "transcript")
    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.DEADLINE_EXCEEDED,
        message=str(expiry),
        task=manifest.name,
        command=tuple(effective_command),
        command_exit=command_exit,
        patch_path="patch.diff"
        if patch_bytes is not None or _patch_error is not None
        else None,
        transcript_path=(
            "transcript.txt"
            if transcript_bytes is not None or _transcript_error is not None
            else None
        ),
        patch_digest=patch_digest(patch_bytes) if patch_bytes is not None else None,
        transcript_digest=(
            patch_digest(transcript_bytes) if transcript_bytes is not None else None
        ),
        verdict=None,
        receipt_path=None,
        timeout=timeout,
        rung=rung,
        contract_digest=digest,
        workspace_base_sha=workspace_base_sha,
        retained_path=retained_path,
        attempt_dir=attempt_dir.name,
        attempt_timeout=deadline.timeout,
        deadline=DeadlineProvenance(
            deadline.timeout,
            expiry.phase,
            expiry.elapsed,
            workspace_retained=retained_path is not None,
        ),
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    return record


def _retain_expired_record(
    attempt_dir: Path, deadline: AttemptDeadline, retained_path: Path | None
) -> AttemptRecord:
    """Add latched expiry provenance without displacing an earlier outcome."""
    try:
        deadline.remaining(DeadlinePhase.PRESERVATION)
    except AttemptDeadlineExceeded as caught:
        expiry = caught
    else:
        raise AssertionError("deadline retention requires an expired deadline")
    prior = load_attempt_record(attempt_dir / "attempt.json")
    _patch_bytes, patch_error = _read_artifact(attempt_dir / "patch.diff", "patch")
    _transcript_bytes, transcript_error = _read_artifact(
        attempt_dir / "transcript.txt", "transcript"
    )
    resolved_retained_path = (
        retained_path
        if retained_path is not None
        else Path(prior.retained_path) if prior.retained_path is not None else None
    )
    record = replace(
        prior,
        patch_path=(
            prior.patch_path
            if prior.patch_path is not None
            else "patch.diff"
            if _patch_bytes is not None or patch_error is not None
            else None
        ),
        patch_digest=(
            prior.patch_digest
            if prior.patch_digest is not None
            else patch_digest(_patch_bytes) if _patch_bytes is not None else None
        ),
        transcript_path=(
            prior.transcript_path
            if prior.transcript_path is not None
            else "transcript.txt"
            if _transcript_bytes is not None or transcript_error is not None
            else None
        ),
        transcript_digest=(
            prior.transcript_digest
            if prior.transcript_digest is not None
            else patch_digest(_transcript_bytes)
            if _transcript_bytes is not None
            else None
        ),
        attempt_timeout=deadline.timeout,
        deadline=DeadlineProvenance(
            deadline.timeout,
            expiry.phase,
            expiry.elapsed,
            workspace_retained=resolved_retained_path is not None,
        ),
        retained_path=(
            os.fspath(resolved_retained_path)
            if resolved_retained_path is not None
            else None
        ),
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    return record


def _release_after_exception(
    workspace: PreparedWorkspace,
    error: BaseException,
    *,
    deadline: AttemptDeadline | None = None,
) -> None:
    """Release after a primary failure without allowing cleanup to hide it."""
    try:
        retained_path, message = _release_attempt_workspace(
            workspace, deadline=deadline
        )
    except BaseException as release_error:
        _add_exception_note(
            error,
            f"workspace release raised {type(release_error).__name__}: {release_error}; "
            f"retained at {workspace.parent}",
        )
    else:
        if retained_path is not None:
            _add_exception_note(error, f"{message}; retained at {retained_path}")


def _finalize_deadline_from_record(
    attempt_dir: Path,
    deadline: AttemptDeadline,
    workspace: PreparedWorkspace,
    *,
    workspace_retained: bool = True,
    retained_path: str | None = None,
) -> AttemptRecord:
    """Add expiry provenance and reconcile an already-durable receipt.

    A receipt is verdict evidence only when its task and patch digest match
    the pre-grade record.  Otherwise the durable GRADE_FAILED state remains
    regradeable rather than manufacturing an outcome from process status.
    """
    record = load_attempt_record(attempt_dir / "attempt.json")
    receipt_path = attempt_dir / "receipt.json"
    if record.code is AttemptCode.GRADE_FAILED and receipt_path.is_file():
        try:
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            verdict = Verdict(data["verdict"])
            matches = (
                data["task"] == record.task
                and data["patch_digest"] == record.patch_digest
            )
        except KeyError, TypeError, ValueError, json.JSONDecodeError, OSError:
            matches = False
        if matches:
            record = replace(
                record,
                code=AttemptCode.OK,
                message="attempt recorded and graded before deadline finalization",
                verdict=verdict,
                receipt_path="receipt.json",
            )
    expiry: AttemptDeadlineExceeded
    try:
        deadline.remaining(DeadlinePhase.GRADING)
    except AttemptDeadlineExceeded as caught:
        expiry = caught
    else:
        raise AssertionError("deadline finalization requires an expired deadline")
    resolved_retained_path = (
        retained_path
        if workspace_retained and retained_path is not None
        else os.fspath(workspace.parent)
        if workspace_retained
        else None
    )
    record = replace(
        record,
        attempt_timeout=deadline.timeout,
        deadline=DeadlineProvenance(
            deadline.timeout,
            expiry.phase,
            expiry.elapsed,
            workspace_retained=workspace_retained,
        ),
        retained_path=resolved_retained_path,
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    return record


def _record_release_retention(
    record: AttemptRecord,
    *,
    retained_path: str,
    release_message: str | None,
) -> AttemptRecord:
    """Keep a graded outcome regradeable when late cleanup retains its lease."""
    message = f"{record.message}; {release_message}; retained at {retained_path}"
    if record.code in (AttemptCode.OK, AttemptCode.GRADE_FAILED):
        return replace(record, message=message, retained_path=retained_path)
    # No gradeable outcome exists before a refusal.  Preserve any available
    # artifacts but retain the established cleanup-failure precedence.
    return replace(
        record,
        outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.CLEANUP_FAILED,
        message=f"{release_message}; displaced {record.code}: {record.message}",
        verdict=None,
        receipt_path=None,
        retained_path=retained_path,
    )


def _finish_attempt(
    *,
    workspace: WorkspaceResult,
    task_dir: Path,
    attempt_dir: Path,
    patch_path: Path,
    transcript_path: Path,
    manifest: TaskManifest,
    effective_command: list[str],
    timeout: float,
    rung: str | None,
    digest: str,
    deadline: AttemptDeadline | None = None,
) -> AttemptRecord:
    """Preserve, grade, and record artifacts after the workspace is settled."""
    if deadline is not None:
        deadline.remaining(DeadlinePhase.PRESERVATION)
    command_exit = workspace.command_exit
    code = _workspace_refusal(workspace)
    patch_bytes, patch_error = _read_artifact(patch_path, "patch")
    if deadline is not None:
        deadline.remaining(DeadlinePhase.PRESERVATION)
    transcript_bytes, transcript_error = _read_artifact(transcript_path, "transcript")
    if deadline is not None:
        deadline.remaining(DeadlinePhase.PRESERVATION)
    patch_text = (
        patch_bytes.decode("utf-8", errors="replace")
        if patch_bytes is not None
        else None
    )
    transcript_text = (
        transcript_bytes.decode("utf-8", errors="replace")
        if transcript_bytes is not None
        else None
    )
    patch_hash = patch_digest(patch_bytes) if patch_bytes is not None else None
    transcript_hash = (
        patch_digest(transcript_bytes) if transcript_bytes is not None else None
    )
    if deadline is not None:
        deadline.remaining(DeadlinePhase.PRESERVATION)

    fault: str | None = None
    # V11d slice 4. MODEL_ERROR replaces the NO_PATCH this cell would
    # otherwise get -- it never displaces a patch. A model that edited
    # files and then hit a GPU fault on its next turn has still produced a
    # gradeable patch, and refusing it ungraded would destroy evidence
    # that cannot be recovered offline. So the substrate is only consulted
    # where decide_refusal would have said NO_PATCH, which is also exactly
    # the population the re-score path reclassifies. The two call sites
    # must agree or a cell's code depends on when it was decided.
    # Never the exit code (BRIEF rule 4).
    if (
        code is None
        and transcript_text is not None
        and decide_refusal(patch_text, transcript_text) is AttemptCode.NO_PATCH
        and (fault := infrastructure_failure(transcript_text)) is not None
    ):
        code = AttemptCode.MODEL_ERROR
    if code is None:
        if patch_error is not None:
            code = AttemptCode.PATCH_INVALID
        else:
            code = decide_refusal(patch_text, transcript_text)
    if code is None:
        # grading reads the patch strictly (grade.py read_text); a patch that
        # is not valid UTF-8 must be refused here, not crash grading
        assert (
            patch_bytes is not None
        )  # decide_refusal passed => a present, parseable patch
        try:
            patch_bytes.decode("utf-8")
        except UnicodeDecodeError:
            code = AttemptCode.PATCH_INVALID
    if code is not None:
        if deadline is not None:
            deadline.remaining(DeadlinePhase.PRESERVATION)
        tripped_verdict: Verdict | None = None
        tripped_name: str | None = None
        if code is AttemptCode.BUDGET_EXCEEDED:
            tripped_verdict, tripped_name = _grade_tripped(
                task_dir, attempt_dir, attempt_dir / TRIPPED_PATCH_NAME, deadline=deadline
            )
        message = (
            workspace.message
            if workspace.code is not WorkspaceCode.OK
            else f"attempt refused: {code}"
        )
        if code is AttemptCode.MODEL_ERROR and fault is not None:
            message = f"{message}: {fault}"
        artifact_errors = tuple(
            error for error in (patch_error, transcript_error) if error is not None
        )
        if artifact_errors:
            message = f"{message}; {'; '.join(artifact_errors)}"
        record = AttemptRecord(
            version=1,
            outcome=AttemptOutcome.REFUSED,
            code=code,
            message=message,
            task=manifest.name,
            command=tuple(effective_command),
            command_exit=command_exit,
            patch_path="patch.diff" if patch_bytes is not None else None,
            transcript_path="transcript.txt" if transcript_bytes is not None else None,
            patch_digest=patch_hash,
            transcript_digest=transcript_hash,
            verdict=None,
            receipt_path=None,
            timeout=timeout,
            rung=rung,
            contract_digest=digest,
            workspace_base_sha=workspace.base_sha,
            retained_path=workspace.retained_path,
            attempt_dir=attempt_dir.name,
            attempt_timeout=deadline.timeout if deadline is not None else None,
            tripped_verdict=tripped_verdict,
            tripped_patch_path=tripped_name,
        )
        write_attempt_record(attempt_dir / "attempt.json", record)
        return record

    # The durable record is written BEFORE grading (T2): a grading
    # exception must never leave the cell invisible. The pre-grade record
    # is code GRADE_FAILED — "preserved and admitted, grading did not
    # complete"; a successful grade rewrites it OK with verdict + receipt.
    base_record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.GRADE_FAILED,
        message="attempt preserved and admitted; grading did not complete",
        task=manifest.name,
        command=tuple(effective_command),
        command_exit=command_exit,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest=patch_hash,
        transcript_digest=transcript_hash,
        verdict=None,
        receipt_path=None,
        timeout=timeout,
        rung=rung,
        contract_digest=digest,
        workspace_base_sha=workspace.base_sha,
        attempt_dir=attempt_dir.name,
        attempt_timeout=deadline.timeout if deadline is not None else None,
    )
    write_attempt_record(attempt_dir / "attempt.json", base_record)
    try:
        if deadline is not None:
            deadline.remaining(DeadlinePhase.GRADING)
        receipt = (
            grade(task_dir, patch_path, attempt_dir / "receipt.json", deadline=deadline)
            if deadline is not None
            else grade(task_dir, patch_path, attempt_dir / "receipt.json")
        )
        if deadline is not None:
            deadline.remaining(DeadlinePhase.GRADING)
    except SatyrnError as exc:
        record = replace(base_record, message=f"{base_record.message}: {exc}")
        write_attempt_record(attempt_dir / "attempt.json", record)
        return record
    record = replace(
        base_record,
        code=AttemptCode.OK,
        message="attempt recorded and graded",
        verdict=receipt.verdict,
        receipt_path="receipt.json",
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    if deadline is not None:
        deadline.remaining(DeadlinePhase.GRADING)
    return record


def _grade_tripped(
    task_dir: Path,
    attempt_dir: Path,
    patch_path: Path,
    *,
    deadline: AttemptDeadline | None,
) -> tuple[Verdict, str | None]:
    """The declared secondary (design section 3.2): what the torn-down worktree grades.

    The same `grade` call the delivered patch takes, against the same task
    directory and manifest, so the allowlist, `ignored_paths` and the hidden
    suite bite identically -- a different path would answer a different
    question. It is never a pass in the record's own sense: `verdict` stays
    null and the attempt stays REFUSED (Ruling 2). A missing or empty tripped
    patch is `unavailable`, exactly as the grader answers an empty delivered
    patch, and so is a grader failure -- but the patch name is still recorded
    then, because the evidence exists and can be regraded.
    """
    if not patch_path.is_file():
        return Verdict.UNAVAILABLE, None
    try:
        text = patch_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Verdict.UNAVAILABLE, TRIPPED_PATCH_NAME
    if not text.strip():
        return Verdict.UNAVAILABLE, None
    receipt_path = attempt_dir / TRIPPED_RECEIPT_NAME
    try:
        receipt = (
            grade(task_dir, patch_path, receipt_path, deadline=deadline)
            if deadline is not None
            else grade(task_dir, patch_path, receipt_path)
        )
    except SatyrnError:
        return Verdict.UNAVAILABLE, TRIPPED_PATCH_NAME
    return receipt.verdict, TRIPPED_PATCH_NAME


def _workspace_refusal(workspace: WorkspaceResult) -> AttemptCode | None:
    """Map operational workspace outcomes before artifact preservation checks."""
    if workspace.code is WorkspaceCode.OK:
        return None
    try:
        return _WORKSPACE_ATTEMPT_CODES[workspace.code]
    except KeyError as exc:
        raise AssertionError(f"unexpected workspace outcome: {workspace.code}") from exc


def _read_artifact(path: Path, label: str) -> tuple[bytes | None, str | None]:
    """Read one regular artifact without letting it replace workspace authority."""
    try:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            return None, f"{label} artifact is not a regular file: {path}"
        return path.read_bytes(), None
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError) as exc:
        return None, f"cannot read {label} artifact {path}: {exc}"
