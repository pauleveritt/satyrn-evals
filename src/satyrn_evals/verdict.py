"""Verdict computation. The only evidence is the oracle hook result JSON."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict

from satyrn_evals.errors import HookError

type Outcome = Literal["passed", "failed", "error", "skipped"]

VALID_OUTCOMES: frozenset[Outcome] = frozenset(("passed", "failed", "error", "skipped"))


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"


class HookResultData(TypedDict):
    executed_test_ids: list[str]
    outcomes: dict[str, Outcome]
    counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class HookResult:
    executed_test_ids: tuple[str, ...]
    outcomes: dict[str, Outcome]
    counts: dict[str, int]


def load_hook_result(path: Path, run_started: float) -> HookResult:
    if not path.exists():
        raise HookError("hook result missing")
    if path.stat().st_mtime < run_started - 1.0:
        raise HookError("hook result stale")
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise HookError(f"hook result unparseable: {e}") from e
    if not isinstance(data, dict):
        raise HookError("hook result is not an object")
    try:
        executed = tuple(data["executed_test_ids"])
        outcomes = data["outcomes"]
        counts = data["counts"]
    except (KeyError, TypeError) as e:
        raise HookError(f"hook result missing fields: {e}") from e
    if not all(isinstance(i, str) for i in executed):
        raise HookError("executed_test_ids must be strings")
    if not isinstance(outcomes, dict) or not isinstance(counts, dict):
        raise HookError("outcomes and counts must be objects")
    if set(outcomes) != set(executed):
        raise HookError("outcomes do not match executed_test_ids")
    if any(v not in VALID_OUTCOMES for v in outcomes.values()):
        raise HookError("unknown outcome value")
    if set(counts) != set(VALID_OUTCOMES) or any(not isinstance(v, int) for v in counts.values()):
        raise HookError("counts must hold one integer per outcome")
    tallies: dict[str, int] = {}
    for outcome in VALID_OUTCOMES:
        tallies[outcome] = 0
    for outcome in outcomes.values():
        tallies[outcome] += 1
    if counts != tallies:
        raise HookError("counts inconsistent with outcomes")
    return HookResult(
        executed_test_ids=tuple(sorted(executed)),
        outcomes=dict(outcomes),
        counts=dict(counts),
    )


def compute_verdict(hook: HookResult, expected: tuple[str, ...]) -> Verdict:
    if set(hook.executed_test_ids) != set(expected):
        return Verdict.UNAVAILABLE
    outcomes = set(hook.outcomes.values())
    if "skipped" in outcomes:
        return Verdict.UNAVAILABLE
    if outcomes & {"failed", "error"}:
        return Verdict.FAIL
    return Verdict.PASS


def describe_unavailable(hook: HookResult, expected: tuple[str, ...]) -> str:
    if set(hook.executed_test_ids) != set(expected):
        missing = sorted(set(expected) - set(hook.executed_test_ids))
        extra = sorted(set(hook.executed_test_ids) - set(expected))
        return f"executed tests mismatch expected (missing {missing}, extra {extra})"
    if "skipped" in hook.outcomes.values():
        return "suite did not fully run (skipped tests)"
    return "verdict unavailable"
