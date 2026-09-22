
from satyrn_evals.discriminating import (
    discriminating_set,
    failing_ids,
    recorded_oracle,
)
from satyrn_evals.verdict import HookResult, Outcome


def _hook(outcomes: dict[str, Outcome]) -> HookResult:
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for outcome in outcomes.values():
        counts[outcome] += 1
    return HookResult(executed_test_ids=tuple(sorted(outcomes)), outcomes=dict(outcomes), counts=counts)


def test_failing_ids() -> None:
    hook = _hook({"a": "failed", "b": "error", "c": "passed", "d": "skipped"})
    assert failing_ids(hook) == frozenset({"a", "b"})


def test_discriminating_set() -> None:
    base = _hook({"a": "failed", "b": "failed", "c": "passed"})
    fixed = _hook({"a": "passed", "b": "failed", "c": "passed"})
    assert discriminating_set(base, fixed) == ("a",)


def test_discriminating_set_sorted() -> None:
    base = _hook({"z": "failed", "a": "failed"})
    fixed = _hook({"z": "passed", "a": "passed"})
    assert discriminating_set(base, fixed) == ("a", "z")


def test_discriminating_set_empty_is_refusal_case() -> None:
    base = _hook({"a": "failed"})
    fixed = _hook({"a": "failed"})  # fix did not move it
    assert discriminating_set(base, fixed) == ()


def test_discriminating_set_ignores_extra_fixed_tests() -> None:
    base = _hook({"a": "failed"})
    fixed = _hook({"a": "passed", "b": "passed"})  # b added by the fix, not at base
    assert discriminating_set(base, fixed) == ("a",)


def test_recorded_oracle() -> None:
    assert recorded_oracle(("a", "b")) == (
        "python",
        "-m",
        "pytest",
        "-p",
        "satyrn_evals.oracle_hook",
        "a",
        "b",
    )


def test_recorded_oracle_empty() -> None:
    assert recorded_oracle(()) == ("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook")
