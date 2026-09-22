"""The record's optional declared line: `line_token_budget` / `line_turn_budget`.

Both or neither, positive, and strictly less than the attempt budget they
sit inside. Absent means no line harvest and today's record shape, byte for
byte -- `tests/test_census_records_frozen.py` proves every committed record
still validates and is untouched by this addition.

F2: `line_token_budget` must also sit at least `LINE_BUDGET_MARGIN_TOKENS`
below `token_budget` -- one arm's per-turn output cap -- so a budget trip
can never land inside the line harvest window.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.budget import LineBudget
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import (
    LINE_BUDGET_MARGIN_TOKENS,
    RunRecordError,
    gate,
    line_budget,
    load_run_record,
    new_record,
)

ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms"

GOOD = {
    "version": 1, "task": "agentclinic-repair-misleading-locus", "task_tree_sha256": "a" * 64,
    "arm": "baseline", "model": "omlx/gemma-4-12B-it-MLX-8bit", "condition": "cold", "n": 4,
    "mode": "attended", "max_minutes": 60,
    "stop_rule": "established infrastructure failure only", "decision_rule": "presence counts; no rate",
    "previous_result": None, "token_budget": 32000, "turn_budget": 48,
    "isolation": "isolated", "purpose": "admission",
}


def _write(tmp_path: Path, **over: object) -> Path:
    path = tmp_path / "record.json"
    path.write_text(json.dumps({**GOOD, **over}))
    return path


def test_a_record_without_a_line_has_no_line_budget(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path))
    assert record.line_token_budget is None
    assert record.line_turn_budget is None
    assert line_budget(record) is None


def test_a_record_with_both_line_fields_loads(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, line_token_budget=16000, line_turn_budget=24))
    assert record.line_token_budget == 16000
    assert record.line_turn_budget == 24
    assert line_budget(record) == LineBudget(output_tokens=16000, turns=24)


@pytest.mark.parametrize("present", ["line_token_budget", "line_turn_budget"])
def test_only_one_line_field_is_refused(tmp_path: Path, present: str) -> None:
    with pytest.raises(RunRecordError, match="both"):
        load_run_record(_write(tmp_path, **{present: 100}))


@pytest.mark.parametrize("field,value", [("line_token_budget", 0), ("line_turn_budget", 0)])
def test_a_non_positive_line_field_is_refused(tmp_path: Path, field: str, value: int) -> None:
    other = "line_turn_budget" if field == "line_token_budget" else "line_token_budget"
    with pytest.raises(RunRecordError, match="positive"):
        load_run_record(_write(tmp_path, **{field: value, other: 10}))


def test_a_line_token_budget_at_the_attempt_budget_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="strictly less"):
        load_run_record(_write(tmp_path, line_token_budget=32000, line_turn_budget=24))


def test_a_line_turn_budget_at_the_attempt_budget_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="strictly less"):
        load_run_record(_write(tmp_path, line_token_budget=16000, line_turn_budget=48))


def test_a_line_turn_budget_one_below_the_attempt_turn_budget_passes(tmp_path: Path) -> None:
    """The turn field alone, at its own strictly-less boundary -- the token
    field stays at the margin boundary (below) so this isolates the turn
    check from the token-margin check added for F2."""
    record = load_run_record(_write(tmp_path, line_token_budget=16000, line_turn_budget=47))
    assert record.line_turn_budget == 47
    gate(record, previous_result_committed=None)


def test_a_line_token_budget_within_the_margin_of_token_budget_is_refused(
    tmp_path: Path,
) -> None:
    """F2: 40,000 inside 48,000 (an 8,000 gap, half the margin) is refused --
    a budget trip could otherwise fall inside the line harvest window."""
    with pytest.raises(RunRecordError, match="margin|below"):
        load_run_record(
            _write(tmp_path, token_budget=48000, turn_budget=72, line_token_budget=40000, line_turn_budget=48)
        )


def test_a_line_token_budget_exactly_at_the_margin_validates(tmp_path: Path) -> None:
    """F2: the intended comparison shape -- 32,000 / 48 inside 48,000 / 72 --
    sits exactly `LINE_BUDGET_MARGIN_TOKENS` below `token_budget` and validates."""
    assert LINE_BUDGET_MARGIN_TOKENS == 16000
    record = load_run_record(
        _write(tmp_path, token_budget=48000, turn_budget=72, line_token_budget=32000, line_turn_budget=48)
    )
    assert record.line_token_budget == 32000
    gate(record, previous_result_committed=None)


def test_a_line_token_budget_one_token_inside_the_margin_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="margin|below"):
        load_run_record(
            _write(tmp_path, token_budget=48000, turn_budget=72, line_token_budget=32001, line_turn_budget=48)
        )


def test_no_committed_arms_per_turn_output_cap_exceeds_the_named_margin() -> None:
    """The record does not carry the arm's own cap, so `LINE_BUDGET_MARGIN_TOKENS`
    stands in for it -- this fails the moment a committed arm's
    `inference.max_tokens` would make that stand-in too small."""
    arm_files = sorted(ARMS_ROOT.glob("*.json"))
    assert arm_files, "no committed arm files found to scan"
    for path in arm_files:
        max_tokens = json.loads(path.read_text())["inference"]["max_tokens"]
        assert max_tokens <= LINE_BUDGET_MARGIN_TOKENS, (
            f"{path.name}: inference.max_tokens={max_tokens} exceeds "
            f"LINE_BUDGET_MARGIN_TOKENS={LINE_BUDGET_MARGIN_TOKENS}; a line crossing could "
            "then fall inside a single over-budget turn"
        )


def test_a_line_field_wrong_type_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="wrong type"):
        load_run_record(_write(tmp_path, line_token_budget="16000", line_turn_budget=24))


def test_new_record_with_a_line_writes_both_fields(tmp_path: Path) -> None:
    body = new_record(
        task="agentclinic-repair-depth-3", tasks_root=DEFAULT_TASKS_ROOT,
        arm="baseline", model="m", n=4, k=1, rung=None, purpose="admission", isolation="isolated",
        mode="attended", max_minutes=60, token_budget=32000, turn_budget=48, previous_result=None,
        authority=None, decision_rule=None, line_token_budget=16000, line_turn_budget=24,
    )
    assert body["line_token_budget"] == 16000
    assert body["line_turn_budget"] == 24


def test_new_record_without_a_line_writes_neither_field(tmp_path: Path) -> None:
    body = new_record(
        task="agentclinic-repair-depth-3", tasks_root=DEFAULT_TASKS_ROOT,
        arm="baseline", model="m", n=4, k=1, rung=None, purpose="admission", isolation="isolated",
        mode="attended", max_minutes=60, token_budget=32000, turn_budget=48, previous_result=None,
        authority=None, decision_rule=None,
    )
    assert "line_token_budget" not in body
    assert "line_turn_budget" not in body
