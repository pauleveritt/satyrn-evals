"""The capture record: the durable artifact capture writes, E3-shaped.

Like V1's receipt, the record is the authoritative result; the CLI's exit
code is coarse by design. `merge_cleanup_failure` implements E3's
precedence: a cleanup failure replaces any pending result.
"""

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path

CHECK_NAMES = ("source_preflight", "base_oracle", "un_done_at_base", "winnable")
type CheckState = str  # "passed" | "failed" | "not-run"
type CheckOutcomes = dict[str, CheckState]
_VALID_CHECK_STATES = ("passed", "failed", "not-run")


class CaptureOutcome(StrEnum):
    CAPTURED = "captured"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class CaptureRecord:
    version: int
    outcome: CaptureOutcome
    code: str
    message: str
    repo: str
    base_sha: str | None
    fix_sha: str | None
    task_dir: str | None
    oracle: tuple[str, ...] | None
    expected_test_ids: tuple[str, ...] | None
    check_outcomes: CheckOutcomes


def write_capture_record(path: Path, record: CaptureRecord) -> None:
    path.write_text(json.dumps(asdict(record), indent=2) + "\n")


def load_capture_record(path: Path) -> CaptureRecord:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read capture record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("capture record is not an object")
    try:
        outcome = CaptureOutcome(data["outcome"])
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad outcome: {e}") from e
    check_outcomes = data.get("check_outcomes")
    if not isinstance(check_outcomes, dict):
        raise ValueError("check_outcomes must be an object")
    if set(check_outcomes) != set(CHECK_NAMES) or not all(
        v in _VALID_CHECK_STATES for v in check_outcomes.values()
    ):
        raise ValueError("check_outcomes must name all four checks as passed/failed/not-run")
    try:
        return CaptureRecord(
            version=data["version"],
            outcome=outcome,
            code=data["code"],
            message=data["message"],
            repo=data["repo"],
            base_sha=data.get("base_sha"),
            fix_sha=data.get("fix_sha"),
            task_dir=data.get("task_dir"),
            oracle=tuple(data["oracle"]) if data.get("oracle") is not None else None,
            expected_test_ids=tuple(data["expected_test_ids"])
            if data.get("expected_test_ids") is not None
            else None,
            check_outcomes=dict(check_outcomes),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"capture record missing a field: {e}") from e


def merge_cleanup_failure(pending: CaptureRecord, cleanup_message: str) -> CaptureRecord:
    """CLEANUP_FAILED replaces any pending result (E3 precedence).

    The outcome becomes REFUSED even when the pending record was captured:
    a retained worktree means the operation did not fully complete.
    """
    return replace(
        pending,
        outcome=CaptureOutcome.REFUSED,
        code="CLEANUP_FAILED",
        message=f"{cleanup_message}; displaced {pending.code}: {pending.message}",
    )
