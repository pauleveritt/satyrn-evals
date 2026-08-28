"""Attempt orchestration: run a command through the engine seam, preserve
its patch and transcript, grade the delivered patch offline, and record.

The pure decision logic (refusal codes, directory naming) lives here so the
default test tier can exercise it without spawning anything. The seam is
env-var paths: SATYRN_TASK_NAME/CONTRACT are inputs; SATYRN_ATTEMPT_PATCH/
TRANSCRIPT are where the command writes its delivery.
"""

import os
import stat
import sys
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    write_attempt_record,
)
from satyrn_evals.errors import PatchParseError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import TaskManifest, load_manifest, resolve_task
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

_WORKSPACE_ATTEMPT_CODES: dict[WorkspaceCode, AttemptCode] = {
    WorkspaceCode.WORKSPACE_FAILED: AttemptCode.WORKSPACE_FAILED,
    WorkspaceCode.COMMAND_TIMEOUT: AttemptCode.COMMAND_TIMEOUT,
    WorkspaceCode.CLEANUP_FAILED: AttemptCode.CLEANUP_FAILED,
}


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
) -> AttemptRecord:
    """Run COMMAND against TASK, preserve patch + transcript, grade, and record.

    Usage errors (unknown task, empty command, command cannot start) raise
    UsageError and write nothing — a start failure also removes the
    freshly-created attempt directory. Refusals and successes write an
    attempt record; the CLI maps outcome/verdict to an exit code.
    """
    task_dir = resolve_task(task, tasks_root)
    manifest = load_manifest(task_dir)
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
    env[TASK_CONTRACT_ENV] = manifest.contract
    env[PATCH_ENV] = str(patch_path)
    env[TRANSCRIPT_ENV] = str(transcript_path)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")

    effective_command = list(command)
    if manifest.engine_contract is not None:
        effective_command.append(
            os.fspath(Path(os.path.abspath(task_dir / manifest.engine_contract)))
        )

    workspace = run_workspace(
        base=task_dir / "base",
        protected_paths=(task_dir, output, Path.cwd()),
        command=effective_command,
        environment=env,
        timeout=timeout,
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
            workspace_base_sha=workspace.base_sha,
            retained_path=workspace.retained_path,
        )
        write_attempt_record(attempt_dir / "attempt.json", record)
        return record

    receipt = grade(task_dir, patch_path, attempt_dir / "receipt.json")
    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.OK,
        message="attempt recorded and graded",
        task=manifest.name,
        command=tuple(effective_command),
        command_exit=command_exit,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest=patch_hash,
        transcript_digest=transcript_hash,
        verdict=receipt.verdict,
        receipt_path="receipt.json",
        workspace_base_sha=workspace.base_sha,
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
