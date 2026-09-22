"""``satyrn-evals record new``: a record the launcher accepts, written without hand-editing JSON."""

import json
from pathlib import Path

import pytest

from satyrn_evals.cell import Isolation
from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import (
    ADMISSION_DECISION_RULE,
    RunRecordError,
    load_run_record,
    new_record,
    record_arms,
)
from satyrn_evals.task_tree import tree_digest

TASK = "agentclinic-repair-depth-3"
AUTHORITY = "maintainer's one-time unattended-inference exception, 2026-09-14"


def _new(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "record", "new", "--output", str(tmp_path / "records" / "depth-3.json"), "--task", TASK,
        "--arm", "baseline", "--rung", "R1", "--n", "4", "--k", "2", "--purpose", "admission",
        "--authority", AUTHORITY, *extra,
    ]


def test_an_admission_record_is_written_with_the_tree_digest_and_the_spec_rule(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    record = load_run_record(tmp_path / "records" / "depth-3.json")
    assert record.task_tree_sha256 == tree_digest(DEFAULT_TASKS_ROOT / TASK)
    assert (record.n, record.k, record.rung, record.purpose) == (4, 2, "R1", "admission")
    assert record.isolation is Isolation.ISOLATED
    assert (record.token_budget, record.turn_budget, record.max_minutes) == (32000, 48, 60)
    assert record.decision_rule == ADMISSION_DECISION_RULE and record.authority == AUTHORITY
    assert record.model == "omlx/Ornith-1.5-9B-MLX-8bit" and record.previous_result is None


def test_a_written_record_is_never_overwritten(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    before = (tmp_path / "records" / "depth-3.json").read_text()
    assert main(_new(tmp_path, "--n", "3")) == 2
    assert (tmp_path / "records" / "depth-3.json").read_text() == before


def test_an_unknown_rung_writes_nothing(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--rung", "R9")) == 2
    assert not (tmp_path / "records" / "depth-3.json").exists()


def test_a_record_the_gate_refuses_is_not_left_behind(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--isolation", "local")) == 2
    assert main(_new(tmp_path, "--n", "9")) == 2
    assert not (tmp_path / "records" / "depth-3.json").exists()


@pytest.mark.parametrize("k", ["0", "4"])
def test_k_outside_one_to_three_is_a_usage_error(tmp_path: Path, k: str) -> None:
    with pytest.raises(SystemExit):
        main(_new(tmp_path, "--k", k))


def test_a_campaign_record_must_state_its_decision_rule(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="needs --decision-rule"):
        new_record(
            task=TASK, tasks_root=DEFAULT_TASKS_ROOT, arm="baseline+engine", model="omlx/m", n=12, k=2,
            rung="R1", purpose="campaign", isolation="isolated", mode="batch", max_minutes=720,
            token_budget=32000, turn_budget=48, previous_result=None, authority=None, decision_rule=None,
        )


def test_an_interleaved_development_record_names_both_arms_in_order(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    assert main([
        "record", "new", "--output", str(out), "--task", TASK, "--arm", "baseline+engine", "--rung", "R1",
        "--n", "2", "--k", "2", "--purpose", "development", "--isolation", "local",
    ]) == 0
    assert record_arms(load_run_record(out)) == ("baseline", "engine")
    assert json.loads(out.read_text())["decision_rule"] == "none: development, no task outcome"


def test_the_default_contract_is_pinned_as_a_null_rung(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    assert main([
        "record", "new", "--output", str(out), "--task", "format_number", "--arm", "baseline",
        "--rung", "contract", "--n", "1", "--k", "1", "--purpose", "development",
    ]) == 0
    assert load_run_record(out).rung is None


def test_a_record_that_follows_a_result_is_written_and_its_commit_is_left_to_launch(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--previous-result", "records/depth-3.result.json")) == 0
    assert load_run_record(tmp_path / "records" / "depth-3.json").previous_result == "records/depth-3.result.json"


def test_record_new_defaults_the_backstop_and_writes_it(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    assert load_run_record(tmp_path / "records" / "depth-3.json").command_backstop_s == 1800


def test_record_new_takes_a_backstop(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--command-backstop", "3000", "--mode", "batch", "--max-minutes", "240")) == 0
    assert load_run_record(tmp_path / "records" / "depth-3.json").command_backstop_s == 3000


def test_record_new_refuses_a_backstop_that_does_not_fit_the_wall_clock(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--command-backstop", "3600", "--max-minutes", "60")) == 2
    assert not (tmp_path / "records" / "depth-3.json").exists()


def test_record_new_takes_a_line(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--line-token-budget", "16000", "--line-turn-budget", "24")) == 0
    record = load_run_record(tmp_path / "records" / "depth-3.json")
    assert (record.line_token_budget, record.line_turn_budget) == (16000, 24)


def test_record_new_without_a_line_writes_neither_field(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    record = load_run_record(tmp_path / "records" / "depth-3.json")
    assert record.line_token_budget is None
    assert record.line_turn_budget is None


def test_record_new_refuses_only_one_line_flag(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--line-token-budget", "16000")) == 2
    assert not (tmp_path / "records" / "depth-3.json").exists()
