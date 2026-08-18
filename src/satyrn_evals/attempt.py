"""Attempt orchestration: run a command through the engine seam, preserve
its patch and transcript, grade the delivered patch offline, and record.

The pure decision logic (refusal codes, directory naming) lives here so the
default test tier can exercise it without spawning anything. The seam is
env-var paths: SATYRN_TASK_NAME/CONTRACT are inputs; SATYRN_ATTEMPT_PATCH/
TRANSCRIPT are where the command writes its delivery.
"""

from datetime import UTC, datetime

from satyrn_evals.errors import PatchParseError
from satyrn_evals.patch import parse_patch_paths

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
