"""Attempt orchestration: run a command through the engine seam, preserve
its patch and transcript, grade the delivered patch offline, and record.

The pure decision logic (refusal codes, directory naming) lives here so the
default test tier can exercise it without spawning anything. The seam is
env-var paths: SATYRN_TASK_NAME/CONTRACT are inputs; SATYRN_ATTEMPT_PATCH/
TRANSCRIPT are where the command writes its delivery.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from satyrn_evals.attempt_record import (
    AttemptOutcome,
    AttemptRecord,
    write_attempt_record,
)
from satyrn_evals.errors import PatchParseError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.receipt import patch_digest

TASK_NAME_ENV = "SATYRN_TASK_NAME"
TASK_CONTRACT_ENV = "SATYRN_TASK_CONTRACT"
PATCH_ENV = "SATYRN_ATTEMPT_PATCH"
TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"

REFUSAL_CODES = ("NO_PATCH", "PATCH_INVALID", "TRANSCRIPT_MISSING", "TRANSCRIPT_EMPTY")


def decide_refusal(patch_text: str | None, transcript_text: str | None) -> str | None:
    """Refusal code when the delivered artifacts are incomplete; None to proceed.

    An input of None means the file was absent. Patch checks run first, then
    transcript checks (spec: "the first failure refuses").
    """
    if not patch_text or not patch_text.strip():
        return "NO_PATCH"
    try:
        parse_patch_paths(patch_text)
    except PatchParseError:
        return "PATCH_INVALID"
    if transcript_text is None:
        return "TRANSCRIPT_MISSING"
    if not transcript_text.strip():
        return "TRANSCRIPT_EMPTY"
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

    with tempfile.TemporaryDirectory(prefix="satyrn-attempt-") as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(task_dir / "base", work)
        try:
            proc = subprocess.run(command, cwd=work, env=env, capture_output=True)
        except OSError as e:
            shutil.rmtree(attempt_dir, ignore_errors=True)  # usage writes nothing
            raise UsageError(f"attempt command cannot start: {e}") from e
    command_exit = proc.returncode

    patch_bytes = patch_path.read_bytes() if patch_path.exists() else None
    transcript_bytes = (
        transcript_path.read_bytes() if transcript_path.exists() else None
    )
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

    code = decide_refusal(patch_text, transcript_text)
    if code is None:
        # grading reads the patch strictly (grade.py read_text); a patch that
        # is not valid UTF-8 must be refused here, not crash grading
        assert patch_bytes is not None  # decide_refusal passed => a present, parseable patch
        try:
            patch_bytes.decode("utf-8")
        except UnicodeDecodeError:
            code = "PATCH_INVALID"
    if code is not None:
        record = AttemptRecord(
            version=1,
            outcome=AttemptOutcome.REFUSED,
            code=code,
            message=f"attempt refused: {code}",
            task=manifest.name,
            command=tuple(command),
            command_exit=command_exit,
            patch_path="patch.diff" if patch_bytes is not None else None,
            transcript_path="transcript.txt" if transcript_bytes is not None else None,
            patch_digest=patch_hash,
            transcript_digest=transcript_hash,
            verdict=None,
            receipt_path=None,
        )
        write_attempt_record(attempt_dir / "attempt.json", record)
        return record

    receipt = grade(task_dir, patch_path, attempt_dir / "receipt.json")
    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code="OK",
        message="attempt recorded and graded",
        task=manifest.name,
        command=tuple(command),
        command_exit=command_exit,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest=patch_hash,
        transcript_digest=transcript_hash,
        verdict=receipt.verdict,
        receipt_path="receipt.json",
    )
    write_attempt_record(attempt_dir / "attempt.json", record)
    return record
