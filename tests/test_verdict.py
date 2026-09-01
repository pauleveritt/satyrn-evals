import json
import time
from pathlib import Path
from typing import Any, cast

import pytest

from satyrn_evals.errors import HookError
from satyrn_evals.verdict import (
    HookResult,
    Outcome,
    Verdict,
    compute_verdict,
    describe_unavailable,
    load_hook_result,
)


def _hook_data(executed: list[str], outcomes: dict[str, str]) -> dict:
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for outcome in outcomes.values():
        counts[outcome] += 1
    return {"executed_test_ids": sorted(executed), "outcomes": outcomes, "counts": counts}


def _mk_hook(executed: list[str], outcomes: dict[str, Outcome]) -> HookResult:
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for outcome in outcomes.values():
        counts[outcome] += 1
    return HookResult(
        executed_test_ids=tuple(sorted(executed)),
        outcomes=dict(outcomes),
        counts=counts,
    )


@pytest.mark.parametrize(
    ("outcomes", "expected", "verdict"),
    [
        ({"a": "passed", "b": "passed"}, ("a", "b"), Verdict.PASS),
        ({"a": "failed"}, ("a",), Verdict.FAIL),
        ({"a": "error"}, ("a",), Verdict.FAIL),
        ({"a": "passed"}, ("b",), Verdict.UNAVAILABLE),
        ({"a": "skipped"}, ("a",), Verdict.UNAVAILABLE),
    ],
    ids=["all-pass", "failure", "setup-error", "mismatch", "skip"],
)
def test_compute_verdict(
    outcomes: dict[str, Outcome], expected: tuple[str, ...], verdict: Verdict
) -> None:
    hook = _mk_hook(sorted(outcomes), outcomes)
    assert compute_verdict(hook, expected) is verdict


def test_load_fresh_file(tmp_path) -> None:
    path = tmp_path / "hook.json"
    path.write_text(json.dumps(_hook_data(["a"], {"a": "passed"})))
    hook = load_hook_result(path, time.time() - 100)
    assert hook.executed_test_ids == ("a",)
    assert hook.outcomes == {"a": "passed"}
    assert hook.counts["passed"] == 1


def test_load_missing_file_rejected() -> None:
    with pytest.raises(HookError, match="hook result missing"):
        load_hook_result(Path("/nonexistent/hook.json"), time.time())


def test_load_stale_file_rejected(tmp_path) -> None:
    path = tmp_path / "hook.json"
    path.write_text(json.dumps(_hook_data(["a"], {"a": "passed"})))
    with pytest.raises(HookError, match="hook result stale"):
        load_hook_result(path, time.time() + 100)


def test_load_unparseable_rejected(tmp_path) -> None:
    path = tmp_path / "hook.json"
    path.write_text("not json")
    with pytest.raises(HookError, match="unparseable"):
        load_hook_result(path, time.time() - 100)


def test_load_inconsistent_counts_rejected(tmp_path) -> None:
    path = tmp_path / "hook.json"
    data = _hook_data(["a"], {"a": "passed"})
    data["counts"]["passed"] = 99
    path.write_text(json.dumps(data))
    with pytest.raises(HookError, match="counts inconsistent"):
        load_hook_result(path, time.time() - 100)


def test_describe_mismatch() -> None:
    hook = HookResult(("a",), {"a": "passed"}, {"passed": 1, "failed": 0, "error": 0, "skipped": 0})
    assert "mismatch" in describe_unavailable(hook, ("b",))


def test_describe_skip() -> None:
    hook = HookResult(("a",), {"a": "skipped"}, {"passed": 0, "failed": 0, "error": 0, "skipped": 1})
    assert "skip" in describe_unavailable(hook, ("a",))


def test_load_hook_result_with_collect_errors(tmp_path) -> None:
    path = tmp_path / "hook.json"
    data = _hook_data([], {})
    data["collect_errors"] = ["ModuleNotFoundError: nope"]
    path.write_text(json.dumps(data))
    hook = load_hook_result(path, time.time() - 100)
    assert hook.collect_errors == ("ModuleNotFoundError: nope",)


def test_load_hook_result_absent_collect_errors_defaults_empty(tmp_path) -> None:
    path = tmp_path / "hook.json"
    path.write_text(json.dumps(_hook_data(["a"], {"a": "passed"})))
    hook = load_hook_result(path, time.time() - 100)
    assert hook.collect_errors == ()


def test_load_hook_result_non_list_collect_errors_rejected(tmp_path) -> None:
    path = tmp_path / "hook.json"
    data = _hook_data(["a"], {"a": "passed"})
    data["collect_errors"] = "nope"
    path.write_text(json.dumps(data))
    with pytest.raises(HookError, match="collect_errors"):
        load_hook_result(path, time.time() - 100)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "not an object"),
        ({}, "missing fields"),
        (
            _hook_data(cast(Any, [1]), cast(Any, {1: "passed"})),
            "executed_test_ids must be strings",
        ),
        (
            {"executed_test_ids": ["a"], "outcomes": [], "counts": {}},
            "outcomes and counts must be objects",
        ),
        (_hook_data(["a"], {"b": "passed"}), "outcomes do not match"),
        (
            {
                "executed_test_ids": ["a"],
                "outcomes": {"a": "unknown"},
                "counts": {"passed": 0, "failed": 0, "error": 0, "skipped": 0},
            },
            "unknown outcome",
        ),
        (
            {"executed_test_ids": [], "outcomes": {}, "counts": {}},
            "counts must hold one integer",
        ),
    ],
)
def test_load_hook_result_rejects_invalid_shapes(
    tmp_path: Path, data: object, message: str
) -> None:
    path = tmp_path / "hook.json"
    path.write_text(json.dumps(data))
    with pytest.raises(HookError, match=message):
        load_hook_result(path, time.time() - 100)


def test_describe_generic_unavailable() -> None:
    hook = HookResult(
        ("a",), {"a": "passed"}, {"passed": 1, "failed": 0, "error": 0, "skipped": 0}
    )
    assert describe_unavailable(hook, ("a",)) == "verdict unavailable"
