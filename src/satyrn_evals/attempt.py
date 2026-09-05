"""Attempt orchestration: run a command through the engine seam, preserve
its patch and transcript, grade the delivered patch offline, and record.

The pure decision logic (refusal codes, directory naming) lives here so the
default test tier can exercise it without spawning anything. The seam is
env-var paths: SATYRN_TASK_NAME/CONTRACT are inputs; SATYRN_ATTEMPT_PATCH/
TRANSCRIPT are where the command writes its delivery.
"""

import hashlib
import os
import stat
import sys
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    write_attempt_record,
)
from satyrn_evals.engine_contract import (
    render_engine_contract,
    write_engine_contract,
)
from satyrn_evals.errors import PatchParseError, SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import TaskManifest, load_manifest, resolve_task
from satyrn_evals.overlay import load_overlay
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.receipt import patch_digest
from satyrn_evals.workspace import (
    DEFAULT_TIMEOUT,
    WorkspaceCode,
    WorkspaceResult,
    run_workspace,
)

TASK_NAME_ENV = "SATYRN_TASK_NAME"
TASK_CONTRACT_ENV = "SATYRN_TASK_CONTRACT"
PATCH_ENV = "SATYRN_ATTEMPT_PATCH"
TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"

type SelectedContract = tuple[str | None, str]

_WORKSPACE_ATTEMPT_CODES: dict[WorkspaceCode, AttemptCode] = {
    WorkspaceCode.WORKSPACE_FAILED: AttemptCode.WORKSPACE_FAILED,
    WorkspaceCode.COMMAND_TIMEOUT: AttemptCode.COMMAND_TIMEOUT,
    WorkspaceCode.CLEANUP_FAILED: AttemptCode.CLEANUP_FAILED,
}


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
    output = Path(os.path.abspath(output))
    output.mkdir(parents=True, exist_ok=True)
    attempt_dir = output / attempt_dir_name(manifest.name, datetime.now(UTC))
    attempt_dir.mkdir()
    patch_path = attempt_dir / "patch.diff"
    transcript_path = attempt_dir / "transcript.txt"

    env = dict(os.environ)
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
    if manifest.engine_contract is not None:
        # A hand-authored contract keeps today's behaviour exactly.
        effective_command.append(
            os.fspath(Path(os.path.abspath(task_dir / manifest.engine_contract)))
        )
    else:
        # Generated from manifest + selected rung, written once at a path
        # keyed by the SHA-256 of its own bytes so every cell of a run
        # records the same command (proposal correction 8).
        effective_command.append(
            os.fspath(
                write_engine_contract(
                    output,
                    render_engine_contract(
                        task_dir,
                        manifest,
                        rung=selected_rung,
                        contract_text=contract_text,
                    ),
                )
            )
        )

    with TemporaryDirectory(prefix="satyrn-evals-uv-") as environment_root:
        env["UV_PROJECT_ENVIRONMENT"] = environment_root
        workspace = run_workspace(
            base=task_dir / "base",
            protected_paths=(task_dir, output, Path.cwd()),
            command=effective_command,
            environment=env,
            timeout=timeout,
            overlay=(
                load_overlay(task_dir, manifest)
                if manifest.oracle_visibility == "hidden"
                else None
            ),
        )
    if workspace.code is WorkspaceCode.COMMAND_UNAVAILABLE:
        attempt_dir.rmdir()  # usage writes nothing; artifacts cannot exist before start
        raise UsageError(workspace.message)
    try:
        return _finish_attempt(
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
    except BaseException as exc:
        if workspace.code is WorkspaceCode.CLEANUP_FAILED:
            _add_exception_note(
                exc,
                f"{workspace.message}; retained at {workspace.retained_path}",
            )
        raise


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
) -> AttemptRecord:
    """Preserve, grade, and record artifacts after the workspace is settled."""
    command_exit = workspace.command_exit
    code = _workspace_refusal(workspace)
    patch_bytes, patch_error = _read_artifact(patch_path, "patch")
    transcript_bytes, transcript_error = _read_artifact(transcript_path, "transcript")
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

    if code is None:
        if patch_error is not None:
            code = AttemptCode.PATCH_INVALID
        else:
            code = decide_refusal(patch_text, transcript_text)
    if code is None:
        # grading reads the patch strictly (grade.py read_text); a patch that
        # is not valid UTF-8 must be refused here, not crash grading
        assert patch_bytes is not None  # decide_refusal passed => a present, parseable patch
        try:
            patch_bytes.decode("utf-8")
        except UnicodeDecodeError:
            code = AttemptCode.PATCH_INVALID
    if code is not None:
        message = (
            workspace.message
            if workspace.code is not WorkspaceCode.OK
            else f"attempt refused: {code}"
        )
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
    )
    write_attempt_record(attempt_dir / "attempt.json", base_record)
    try:
        receipt = grade(task_dir, patch_path, attempt_dir / "receipt.json")
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
    return record


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
