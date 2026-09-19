"""The record's optional declared line: `line_token_budget` / `line_turn_budget`.

Both or neither, positive, and strictly less than the attempt budget they
sit inside. Absent means no line harvest and today's record shape, byte for
byte -- `tests/test_census_records_frozen.py` proves every committed record
still validates and is untouched by this addition.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.budget import LineBudget
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import (
    RunRecordError,
    gate,
    line_budget,
    load_run_record,
    new_record,
)

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


def test_a_line_field_one_below_the_attempt_budget_passes(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, line_token_budget=31999, line_turn_budget=47))
    assert record.line_token_budget == 31999
    gate(record, previous_result_committed=None)


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
