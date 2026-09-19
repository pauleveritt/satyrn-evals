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

from satyrn_evals.attempt import resolve_contract
from satyrn_evals.budget import AttemptBudget, LineBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import load_manifest, resolve_task
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
#: The per-attempt-command wall-clock backstop, seconds. A record field since
#: the 2026-09-16 census (design section 3.3); 1800 is the value every record
#: written before it ran under, so it is the default an older record loads with.
DEFAULT_COMMAND_BACKSTOP_S = 1800
#: What the whole-attempt deadline adds on top of the command backstop: the
#: preserve, grade and cleanup tail the DeadlinePhase ladder needs. It does not
#: grow with the command budget, so the difference is kept, not the ratio
#: (2100 - 1800 at the release-one setting).
DEADLINE_MARGIN_S = 300
#: Concurrency the spec allows ("Concurrency, both arms"): the largest of 1, 2 or 3 the probe admits.
K_VALUES = (1, 2, 3)
#: Arms a record interleaves are joined with this separator in its ``arm`` field (Ruling 3).
ARM_SEPARATOR = "+"
STOP_RULE = "established infrastructure failure only"
#: The spec's admission rule ("Workloads"), written into every admission record by ``record new``.
ADMISSION_DECISION_RULE = (
    "admission: ceiling when bare Pi passes at most 1 of 4 within budget and no passing cell "
    "read material outside its worktree; floor when it passes 4 of 4; a ceiling candidate "
    "passing 2 of 4 or more moves to the floor set"
)
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
    # Phase 2c (Ruling 2): optional so earlier records load; ``record new`` always writes them.
    k: int = 1
    # Design section 3.3: the command backstop is the record's, not a module constant.
    command_backstop_s: int = DEFAULT_COMMAND_BACKSTOP_S
    rung: str | None = None
    authority: str | None = None
    # Release two "line harvest": both or neither, and each strictly below
    # the attempt budget above. Absent means no line harvest and today's
    # behaviour byte for byte -- older records need not carry these.
    line_token_budget: int | None = None
    line_turn_budget: int | None = None


_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "version": int, "task": str, "task_tree_sha256": str, "arm": str, "model": str,
    "condition": str, "n": int, "mode": str, "max_minutes": int,
    "stop_rule": str, "decision_rule": str, "previous_result": (str, type(None)),
    "token_budget": int, "turn_budget": int, "isolation": str, "purpose": str,
}


_OPTIONAL: dict[str, type | tuple[type, ...]] = {
    "k": int, "rung": (str, type(None)), "authority": (str, type(None)),
    "command_backstop_s": int, "line_token_budget": int, "line_turn_budget": int,
}
_ARM_PART = re.compile(r"^[a-z][a-z-]*$")


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
    parts = body["arm"].split(ARM_SEPARATOR)
    if not all(_ARM_PART.match(part) for part in parts) or len(set(parts)) != len(parts):
        raise RunRecordError(f"run record {path}: arm must name distinct arms joined by {ARM_SEPARATOR}")
    for field, kind in _OPTIONAL.items():
        if field in body and (not isinstance(body[field], kind) or isinstance(body[field], bool)):
            raise RunRecordError(f"run record {path}: {field} has the wrong type")
    if body.get("k", 1) not in K_VALUES:
        raise RunRecordError(f"run record {path}: k must be 1, 2 or 3")
    backstop = body.get("command_backstop_s", DEFAULT_COMMAND_BACKSTOP_S)
    if backstop < 1:
        raise RunRecordError(f"run record {path}: command_backstop_s must be a positive integer")
    line_token = body.get("line_token_budget")
    line_turn = body.get("line_turn_budget")
    if (line_token is None) != (line_turn is None):
        raise RunRecordError(
            f"run record {path}: line_token_budget and line_turn_budget must both be set or neither"
        )
    if line_token is not None:
        if line_token < 1 or line_turn < 1:
            raise RunRecordError(
                f"run record {path}: line_token_budget and line_turn_budget must be positive integers"
            )
        if line_token >= body["token_budget"] or line_turn >= body["turn_budget"]:
            raise RunRecordError(
                f"run record {path}: line_token_budget and line_turn_budget must be "
                "strictly less than the record's token_budget and turn_budget"
            )
    fields = {k: body[k] for k in _REQUIRED} | {k: body[k] for k in _OPTIONAL if k in body}
    fields["isolation"] = Isolation(body["isolation"])
    return RunRecord(**fields)


def record_arms(record: RunRecord) -> tuple[str, ...]:
    """The arms the record runs, in the order the launcher alternates them."""
    return tuple(record.arm.split(ARM_SEPARATOR))


def attempt_budget(record: RunRecord) -> AttemptBudget:
    """The budget every attempt under this record is held to."""
    return AttemptBudget(output_tokens=record.token_budget, turns=record.turn_budget)


def line_budget(record: RunRecord) -> LineBudget | None:
    """The record's declared line, or None when it did not name one."""
    if record.line_token_budget is None:
        return None
    assert record.line_turn_budget is not None  # both-or-neither, enforced at load
    return LineBudget(output_tokens=record.line_token_budget, turns=record.line_turn_budget)


def attempt_deadline_s(record: RunRecord) -> float:
    """The whole-attempt deadline this record's backstop implies (Ruling 11)."""
    return float(record.command_backstop_s + DEADLINE_MARGIN_S)


def gate(
    record: RunRecord, *, previous_result_committed: bool | None, record_frozen: bool | None = None
) -> None:
    """Refuse a record outside the cadence; ``None`` for a fact means the caller did not check it.

    ``record_frozen`` is the launcher's: the record file is tracked and has no
    change against ``HEAD`` (``launch RECORD`` supplies it; ``--check`` does not).
    """
    if record_frozen is False:
        raise RunRecordError("the run record is not frozen: commit it, unchanged, before launch")
    max_n, max_minutes = CAPS[record.mode]
    if record.n > max_n or record.max_minutes > max_minutes:
        raise RunRecordError(
            f"{record.mode} runs are capped at n<={max_n} and {max_minutes} minutes; "
            f"record asks n={record.n}, {record.max_minutes} minutes")
    if record.command_backstop_s + DEADLINE_MARGIN_S > record.max_minutes * 60:
        raise RunRecordError(
            f"a {record.command_backstop_s} s backstop plus the {DEADLINE_MARGIN_S} s deadline margin "
            f"leaves no room for one cell in {record.max_minutes} minutes"
        )
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


def count_model_flags(command: Sequence[str]) -> int:
    """How many ``--model`` flags (space or equals form) the command carries."""
    count = 0
    index = 0
    while index < len(command):
        token = command[index]
        if token == "--model":
            count += 1
            index += 2
            continue
        if token.startswith("--model="):
            count += 1
        index += 1
    return count


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
    if (arm := command_arm(command)) not in record_arms(record):
        raise RunRecordError(f"the record is for arm {record.arm}; the command runs {arm or 'no known adapter'}")
    if count_model_flags(command) > 1:
        raise RunRecordError(
            "the command carries more than one --model flag; the record cannot be "
            "cross-checked against a command whose model an adapter might pick differently"
        )
    if (model := command_model(command)) != record.model:
        raise RunRecordError(f"the record is for model {record.model}; the command passes --model {model}")


def new_record(
    *,
    task: str,
    tasks_root: Path,
    arm: str,
    model: str,
    n: int,
    k: int,
    rung: str | None,
    purpose: str,
    isolation: str,
    mode: str,
    max_minutes: int,
    token_budget: int,
    turn_budget: int,
    previous_result: str | None,
    authority: str | None,
    decision_rule: str | None,
    stop_rule: str = STOP_RULE,
    command_backstop_s: int = DEFAULT_COMMAND_BACKSTOP_S,
    line_token_budget: int | None = None,
    line_turn_budget: int | None = None,
) -> dict[str, object]:
    """A record body ``load_run_record`` and ``gate`` accept, with the tree digest and rung read from the task.

    ``rung=None`` pins the manifest's default ``contract`` (a task without a
    ``contracts`` map). The decision rule defaults only for admission (the spec's rule) and
    development; route-proof and campaign records state their own.
    """
    task_dir = resolve_task(task, tasks_root=tasks_root)
    resolve_contract(load_manifest(task_dir), rung)
    if decision_rule is None:
        match purpose:
            case "admission":
                decision_rule = ADMISSION_DECISION_RULE
            case "development":
                decision_rule = "none: development, no task outcome"
            case _:
                raise RunRecordError(f"a {purpose} record needs --decision-rule")
    body: dict[str, object] = {
        "version": 1, "task": task, "task_tree_sha256": tree_digest(task_dir), "arm": arm, "model": model,
        "condition": "cold", "n": n, "mode": mode, "max_minutes": max_minutes, "stop_rule": stop_rule,
        "decision_rule": decision_rule, "previous_result": previous_result, "token_budget": token_budget,
        "turn_budget": turn_budget, "isolation": isolation, "purpose": purpose, "k": k, "rung": rung,
        "authority": authority, "command_backstop_s": command_backstop_s,
    }
    if line_token_budget is not None or line_turn_budget is not None:
        body["line_token_budget"] = line_token_budget
        body["line_turn_budget"] = line_turn_budget
    return body


def write_new_record(path: Path, body: dict[str, object]) -> RunRecord:
    """Write ``body`` to a new file and read it back through the loader and the gate; never overwrite."""
    if path.exists():
        raise RunRecordError(f"{path} exists: a written record is frozen, write a new one")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    try:
        record = load_run_record(path)
        # Whether the previous result is committed is the launcher's fact, checked at launch.
        gate(record, previous_result_committed=True)
    except RunRecordError:
        path.unlink()
        raise
    return record
