import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from suite_durations import (  # noqa: E402  # scripts/ via sys.path, as tests/test_power.py does
    CANDIDATES,
    fits,
    longest_public,
)

JSON = Path(__file__).parents[1] / "scripts" / "suite_durations.json"
BOUNDS = {"default_seconds": 120, "clamp_seconds": 300, "runner_seconds": 120, "margin": 2.0}


def test_the_seven_candidates_are_named_with_their_branches() -> None:
    assert {c.task for c in CANDIDATES} == {
        "agentclinic-repair-misleading-locus", "agentclinic-complaint-lifecycle",
        "agentclinic-repair-depth-2", "agentclinic-repair-depth-3",
        "selfhost-docs-linter", "selfhost-guard-prefixes", "selfhost-run-record-gate"}
    assert {c.branch for c in CANDIDATES} == {
        "release-one", "worktree-ornith-ceiling-probe", "worktree-selfhost-headroom-probe"}


def test_a_bound_fits_when_the_longest_suite_times_the_margin_is_under_it() -> None:
    assert fits(45.0, **BOUNDS) == []


def test_a_default_or_runner_bound_that_does_not_fit_is_named_not_adjusted() -> None:
    assert fits(70.0, **BOUNDS) == [
        "default 120 s < 140.0 s (70.0 s x 2.0)", "runner 120 s < 140.0 s (70.0 s x 2.0)"]


def test_a_clamp_under_twice_the_default_is_refused() -> None:
    assert "clamp 200 s < 240 s (2 x default)" in fits(10.0, **{**BOUNDS, "clamp_seconds": 200})


def test_no_measured_suite_at_all_is_a_failure_not_a_fit() -> None:
    assert fits(None, **BOUNDS) == ["no candidate with a public suite was measured"]


def test_rows_without_a_public_suite_are_excluded_from_the_longest() -> None:
    rows = {"a": {"public_suite": None, "public_seconds": []},
            "b": {"public_suite": ["x"], "public_seconds": [3.0, 2.0]}}
    assert longest_public(rows) == 3.0
    assert longest_public({"a": rows["a"]}) is None


def test_the_committed_measurement_freezes_120_300_and_the_runner_bound() -> None:
    body = json.loads(JSON.read_text())
    assert body["version"] == 1 and body["margin"] == 2.0 and body["fit_failures"] == []
    assert body["longest_public_seconds"] == longest_public(body["tasks"])
    for row in body["tasks"].values():
        assert all(code == 0 for code in row["public_exits"]), row["task"]
    assert fits(body["longest_public_seconds"], **BOUNDS) == []
