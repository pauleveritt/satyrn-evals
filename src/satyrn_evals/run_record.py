"""The frozen record a run must carry before the launcher will spend anything.

A record is a small JSON file written and committed in daylight. `gate`
refuses anything outside the cadence the design fixed: attended runs are
n <= 8 and an hour; the weekly batch is n <= 12 and twelve hours. The check
is pure; the CLI supplies the one fact that needs git.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.budget import AttemptBudget
from satyrn_evals.errors import UsageError

type Mode = Literal["attended", "batch"]
type Condition = Literal["cold", "warm"]

CAPS: dict[str, tuple[int, int]] = {"attended": (8, 60), "batch": (12, 720)}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class RunRecordError(UsageError):
    """The record is absent, ill-formed, or outside the cadence."""


@dataclass(frozen=True, slots=True)
class RunRecord:
    version: int
    task: str
    task_tree_sha256: str
    arm: str
    model: str
    condition: Condition
    n: int
    mode: Mode
    max_minutes: int
    stop_rule: str
    decision_rule: str
    previous_result: str | None
    # The campaign budget per attempt, spec "Budget, both arms".
    token_budget: int
    turn_budget: int


_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "version": int, "task": str, "task_tree_sha256": str, "arm": str, "model": str,
    "condition": str, "n": int, "mode": str, "max_minutes": int,
    "stop_rule": str, "decision_rule": str, "previous_result": (str, type(None)),
    "token_budget": int, "turn_budget": int,
}


def load_run_record(path: Path) -> RunRecord:
    try:
        body = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RunRecordError(f"run record {path}: {error}") from error
    if not isinstance(body, dict):
        raise RunRecordError(f"run record {path}: not a JSON object")
    for field, kind in _REQUIRED.items():
        if field not in body:
            raise RunRecordError(f"run record {path}: missing {field}")
        if not isinstance(body[field], kind) or isinstance(body[field], bool):
            raise RunRecordError(f"run record {path}: {field} has the wrong type")
    if body["condition"] not in ("cold", "warm"):
        raise RunRecordError(f"run record {path}: condition must be cold or warm")
    if body["mode"] not in CAPS:
        raise RunRecordError(f"run record {path}: mode must be attended or batch")
    if not _HEX64.match(body["task_tree_sha256"]):
        raise RunRecordError(f"run record {path}: task_tree_sha256 must be 64 lowercase hex")
    for field in ("stop_rule", "decision_rule"):
        if not body[field].strip():
            raise RunRecordError(f"run record {path}: {field} is empty")
    for field in ("token_budget", "turn_budget"):
        if body[field] < 1:
            raise RunRecordError(
                f"run record {path}: {field} must be a positive integer"
            )
    return RunRecord(**{k: body[k] for k in _REQUIRED})


def attempt_budget(record: RunRecord) -> AttemptBudget:
    """The budget every attempt under this record is held to."""
    return AttemptBudget(output_tokens=record.token_budget, turns=record.turn_budget)


def gate(record: RunRecord, *, previous_result_committed: bool | None) -> None:
    max_n, max_minutes = CAPS[record.mode]
    if record.n > max_n or record.max_minutes > max_minutes:
        raise RunRecordError(
            f"{record.mode} runs are capped at n<={max_n} and {max_minutes} minutes; "
            f"record asks n={record.n}, {record.max_minutes} minutes")
    if record.previous_result is not None and previous_result_committed is not True:
        raise RunRecordError(f"previous_result {record.previous_result} is not committed")
