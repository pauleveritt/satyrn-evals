"""The discriminating set: test IDs that fail at base and pass with the fix.

A captured task's validity (BRIEF's "un-done at base, and winnable") is
proven by this set being non-empty and the recorded oracle passing it.
"""

from satyrn_evals.verdict import HookResult

FULL_SUITE_ORACLE: tuple[str, ...] = (
    "python",
    "-m",
    "pytest",
    "-p",
    "satyrn_evals.oracle_hook",
)

type TestId = str


def failing_ids(hook: HookResult) -> frozenset[TestId]:
    return frozenset(i for i, o in hook.outcomes.items() if o in ("failed", "error"))


def discriminating_set(base: HookResult, fixed: HookResult) -> tuple[TestId, ...]:
    """Sorted IDs that fail at base and pass with the fix. Empty => refuse."""
    failing = failing_ids(base)
    passing = frozenset(i for i, o in fixed.outcomes.items() if o == "passed")
    return tuple(sorted(failing & passing))


def recorded_oracle(ids: tuple[TestId, ...]) -> tuple[str, ...]:
    """The manifest oracle: full-suite command with the discriminating IDs baked in."""
    return (*FULL_SUITE_ORACLE, *ids)
