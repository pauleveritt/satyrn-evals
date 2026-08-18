"""The attempt record: the durable artifact attempt writes, E3-shaped.

Parallel to the capture record: the exit code stays coarse; the record is
precise. It references the receipt by path and repeats the verdict at top
level.
"""

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from satyrn_evals.verdict import Verdict


class AttemptOutcome(StrEnum):
    ATTEMPTED = "attempted"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    version: int
    outcome: AttemptOutcome
    code: str
    message: str
    task: str
    command: tuple[str, ...]
    command_exit: int
    patch_path: str | None
    transcript_path: str | None
    patch_digest: str | None
    transcript_digest: str | None
    verdict: Verdict | None
    receipt_path: str | None


def write_attempt_record(path: Path, record: AttemptRecord) -> None:
    path.write_text(json.dumps(asdict(record), indent=2) + "\n")


def load_attempt_record(path: Path) -> AttemptRecord:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read attempt record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("attempt record is not an object")
    try:
        outcome = AttemptOutcome(data["outcome"])
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad outcome: {e}") from e
    try:
        verdict = Verdict(data["verdict"]) if data.get("verdict") is not None else None
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad verdict: {e}") from e
    try:
        return AttemptRecord(
            version=data["version"],
            outcome=outcome,
            code=data["code"],
            message=data["message"],
            task=data["task"],
            command=tuple(data["command"]),
            command_exit=data["command_exit"],
            patch_path=data.get("patch_path"),
            transcript_path=data.get("transcript_path"),
            patch_digest=data.get("patch_digest"),
            transcript_digest=data.get("transcript_digest"),
            verdict=verdict,
            receipt_path=data.get("receipt_path"),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"attempt record missing a field: {e}") from e
