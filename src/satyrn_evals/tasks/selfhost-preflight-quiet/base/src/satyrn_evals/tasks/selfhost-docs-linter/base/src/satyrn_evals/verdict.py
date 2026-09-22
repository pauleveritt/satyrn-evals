"""Verdict computation. The only evidence is the oracle hook result JSON."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

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
    collect_errors: NotRequired[list[str]]


@dataclass(frozen=True, slots=True)
class HookResult:
    executed_test_ids: tuple[str, ...]
    outcomes: dict[str, Outcome]
    counts: dict[str, int]
    collect_errors: tuple[str, ...] = ()


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
    raw_errors = data.get("collect_errors", [])
    if not isinstance(raw_errors, list) or not all(isinstance(e, str) for e in raw_errors):
        raise HookError("collect_errors must be a list of strings")
    return HookResult(
        executed_test_ids=tuple(sorted(executed)),
        outcomes=dict(outcomes),
        counts=dict(counts),
        collect_errors=tuple(raw_errors),
    )


def _expected_is_collector(entry: str) -> bool:
    """A pytest node id (contains ``::``) is expected exactly; anything
    else (a file or directory path) is a collector whose collected ids
    are only known after the run."""
    return "::" not in entry


def _executed_covered(executed_id: str, expected: tuple[str, ...]) -> bool:
    """Whether an executed id is one of the expected node ids or was
    collected from one of the expected file/directory collectors."""
    for entry in expected:
        if executed_id == entry:
            return True
        if _expected_is_collector(entry) and (
            executed_id.startswith(f"{entry}/")
            or executed_id.startswith(f"{entry}::")
        ):
            return True
    return False


def compute_verdict(hook: HookResult, expected: tuple[str, ...]) -> Verdict:
    """A verdict with expected ids that are exact node ids or collectors.

    Each node-id entry must have executed exactly; a collector entry
    (``tests``, ``tests/test_textkit.py``) admits whatever pytest
    collects beneath it — the ids are not pre-knowable, so the verdict
    requires every executed id to fall under an expected entry, none to
    run outside the expectation, and at least one to have run (no
    vacuous pass). With only node-id entries this reduces to the exact
    executed==expected rule.
    """
    executed = set(hook.executed_test_ids)
    node_ids = {entry for entry in expected if not _expected_is_collector(entry)}
    if not executed or not node_ids <= executed:
        return Verdict.UNAVAILABLE
    if any(not _executed_covered(eid, expected) for eid in executed):
        return Verdict.UNAVAILABLE
    outcomes = set(hook.outcomes.values())
    if "skipped" in outcomes:
        return Verdict.UNAVAILABLE
    if outcomes & {"failed", "error"}:
        return Verdict.FAIL
    return Verdict.PASS


def describe_unavailable(hook: HookResult, expected: tuple[str, ...]) -> str:
    executed = set(hook.executed_test_ids)
    node_ids = {entry for entry in expected if not _expected_is_collector(entry)}
    missing = sorted(node_ids - executed)
    extra = sorted(eid for eid in executed if not _executed_covered(eid, expected))
    if missing or extra or not executed:
        return (
            f"executed tests mismatch expected (missing {missing}, "
            f"extra {extra}, executed {len(executed)})"
        )
    if "skipped" in hook.outcomes.values():
        return "suite did not fully run (skipped tests)"
    return "verdict unavailable"
