"""The frozen record a run must carry before the launcher will spend anything.

A record is a small JSON file written and committed in daylight. `gate`
refuses anything outside the cadence the design fixed: attended runs are
n <= 8 and an hour; the weekly batch is n <= 12 and twelve hours. The check
is pure; the CLI supplies the one fact that needs git.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.errors import UsageError
from satyrn_evals.task_tree import tree_digest

type Mode = Literal["attended", "batch"]
type Condition = Literal["cold", "warm"]
type Purpose = Literal["admission", "route-proof", "campaign", "development"]

#: Purposes whose cells decide something: the launcher runs them only isolated (Ruling 1).
DECIDING_PURPOSES = frozenset({"admission", "route-proof", "campaign"})
PURPOSES = DECIDING_PURPOSES | {"development"}
#: The adapter each committed arm runs, by module or console-script name.
ARM_ADAPTERS = {
    "satyrn_evals.attempt_pi": "baseline",
    "satyrn-evals-attempt-pi": "baseline",
    "satyrn_evals.attempt_engine": "engine",
    "satyrn-evals-attempt-engine": "engine",
}

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
    # The launcher profile and what the run is for (Ruling 1).
    isolation: Isolation
    purpose: Purpose


_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "version": int, "task": str, "task_tree_sha256": str, "arm": str, "model": str,
    "condition": str, "n": int, "mode": str, "max_minutes": int,
    "stop_rule": str, "decision_rule": str, "previous_result": (str, type(None)),
    "token_budget": int, "turn_budget": int, "isolation": str, "purpose": str,
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
    if body["isolation"] not in {profile.value for profile in Isolation}:
        raise RunRecordError(f"run record {path}: isolation must be isolated or local")
    if body["purpose"] not in PURPOSES:
        raise RunRecordError(
            f"run record {path}: purpose must be one of {', '.join(sorted(PURPOSES))}"
        )
    fields = {k: body[k] for k in _REQUIRED}
    fields["isolation"] = Isolation(body["isolation"])
    return RunRecord(**fields)


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
    if record.purpose in DECIDING_PURPOSES and record.isolation is not Isolation.ISOLATED:
        raise RunRecordError(
            f"{record.purpose} records run only under the isolated profile; "
            "the local profile is for development records"
        )


def command_model(command: Sequence[str]) -> str | None:
    """The value of the command's ``--model`` flag (space or equals form), if any."""
    for index, token in enumerate(command):
        if token == "--model" and index + 1 < len(command):
            return command[index + 1]
        if token.startswith("--model="):
            return token.removeprefix("--model=")
    return None


def command_arm(command: Sequence[str]) -> str | None:
    """The committed arm whose adapter the command runs, if it runs one."""
    for token in command:
        if (arm := ARM_ADAPTERS.get(token)) or (arm := ARM_ADAPTERS.get(Path(token).name)):
            return arm
    return None


def check_invocation(record: RunRecord, *, task: str, task_dir: Path, command: Sequence[str]) -> None:
    """Refuse an attempt or run whose task, tree, arm or model is not the record's."""
    if task != record.task:
        raise RunRecordError(f"the record is for task {record.task}, not {task}")
    if (actual := tree_digest(task_dir)) != record.task_tree_sha256:
        raise RunRecordError(
            f"task_tree_sha256 drifted: the record pins {record.task_tree_sha256}, the tree is {actual}"
        )
    if (arm := command_arm(command)) != record.arm:
        raise RunRecordError(f"the record is for arm {record.arm}; the command runs {arm or 'no known adapter'}")
    if (model := command_model(command)) != record.model:
        raise RunRecordError(f"the record is for model {record.model}; the command passes --model {model}")
