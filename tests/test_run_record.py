import json
from pathlib import Path

import pytest

from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.cli import main
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import (
    RunRecord,
    RunRecordError,
    attempt_budget,
    check_invocation,
    command_arm,
    command_model,
    gate,
    load_run_record,
)
from satyrn_evals.task_tree import tree_digest

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


def test_a_complete_record_loads_and_passes_the_gate(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path))
    assert isinstance(record, RunRecord) and record.n == 4
    gate(record, previous_result_committed=None)


def test_a_missing_field_is_named(tmp_path: Path) -> None:
    body = {k: v for k, v in GOOD.items() if k != "decision_rule"}
    path = tmp_path / "r.json"
    path.write_text(json.dumps(body))
    with pytest.raises(RunRecordError, match="decision_rule"):
        load_run_record(path)


def test_run_record_error_is_a_usage_error() -> None:
    assert issubclass(RunRecordError, UsageError)


@pytest.mark.parametrize("over", [{"n": 9}, {"max_minutes": 61}])
def test_attended_caps_are_enforced(tmp_path: Path, over: dict[str, object]) -> None:
    with pytest.raises(RunRecordError, match="attended"):
        gate(load_run_record(_write(tmp_path, **over)), previous_result_committed=None)


def test_batch_allows_twelve_and_twelve_hours(tmp_path: Path) -> None:
    gate(load_run_record(_write(tmp_path, mode="batch", n=12, max_minutes=720)), previous_result_committed=None)


def test_batch_refuses_thirteen(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="batch"):
        gate(load_run_record(_write(tmp_path, mode="batch", n=13, max_minutes=720)), previous_result_committed=None)


def test_a_bad_digest_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="task_tree_sha256"):
        load_run_record(_write(tmp_path, task_tree_sha256="abc"))


def test_a_previous_result_must_be_committed(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, previous_result="docs/results/2026-09-14-x.md"))
    with pytest.raises(RunRecordError, match="previous_result"):
        gate(record, previous_result_committed=False)
    gate(record, previous_result_committed=True)


def test_an_unknown_condition_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="condition"):
        load_run_record(_write(tmp_path, condition="lukewarm"))


def test_warm_condition_loads_and_passes_the_gate(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, condition="warm"))
    assert record.condition == "warm"
    gate(record, previous_result_committed=None)


@pytest.mark.parametrize("body", ["null", "5"])
def test_a_non_object_record_is_refused(tmp_path: Path, body: str) -> None:
    path = tmp_path / "r.json"
    path.write_text(body)
    with pytest.raises(RunRecordError, match="not a JSON object"):
        load_run_record(path)


def test_malformed_json_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    path.write_text("not json")
    with pytest.raises(RunRecordError, match="r.json"):
        load_run_record(path)


def test_a_wrong_typed_field_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="n has the wrong type"):
        load_run_record(_write(tmp_path, n="four"))


def test_an_unknown_mode_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="mode must be attended or batch"):
        load_run_record(_write(tmp_path, mode="turbo"))


@pytest.mark.parametrize("field", ["stop_rule", "decision_rule"])
def test_an_empty_rule_field_is_refused(tmp_path: Path, field: str) -> None:
    with pytest.raises(RunRecordError, match=f"{field} is empty"):
        load_run_record(_write(tmp_path, **{field: "   "}))


def test_launch_without_check_is_a_usage_error() -> None:
    assert main(["launch"]) == 2


def test_launch_check_accepts_a_good_record(tmp_path: Path) -> None:
    assert main(["launch", "--check", str(_write(tmp_path))]) == 0


def test_the_record_carries_the_attempt_budget(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, token_budget=24000, turn_budget=36))
    assert attempt_budget(record) == AttemptBudget(output_tokens=24000, turns=36)


@pytest.mark.parametrize("field", ["token_budget", "turn_budget"])
def test_a_record_without_a_budget_is_refused(tmp_path: Path, field: str) -> None:
    body = {k: v for k, v in GOOD.items() if k != field}
    path = tmp_path / "r.json"
    path.write_text(json.dumps(body))
    with pytest.raises(RunRecordError, match=f"missing {field}"):
        load_run_record(path)


@pytest.mark.parametrize(("field", "value"), [("token_budget", 0), ("turn_budget", -1)])
def test_a_non_positive_budget_is_refused(tmp_path: Path, field: str, value: int) -> None:
    with pytest.raises(RunRecordError, match=f"{field} must be a positive integer"):
        load_run_record(_write(tmp_path, **{field: value}))


@pytest.mark.parametrize("field", ["isolation", "purpose"])
def test_a_record_without_a_profile_or_purpose_is_refused(tmp_path: Path, field: str) -> None:
    body = {k: v for k, v in GOOD.items() if k != field}
    path = tmp_path / "r.json"
    path.write_text(json.dumps(body))
    with pytest.raises(RunRecordError, match=f"missing {field}"):
        load_run_record(path)


def test_an_unknown_profile_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="isolation must be isolated or local"):
        load_run_record(_write(tmp_path, isolation="docker"))


def test_an_unknown_purpose_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="purpose must be one of"):
        load_run_record(_write(tmp_path, purpose="probe"))


@pytest.mark.parametrize("purpose", ["admission", "route-proof", "campaign"])
def test_a_deciding_record_is_refused_under_the_local_profile(tmp_path: Path, purpose: str) -> None:
    record = load_run_record(_write(tmp_path, isolation="local", purpose=purpose))
    with pytest.raises(RunRecordError, match="only under the isolated profile"):
        gate(record, previous_result_committed=None)


@pytest.mark.parametrize("purpose", ["admission", "route-proof", "campaign", "development"])
def test_every_purpose_passes_the_gate_under_the_isolated_profile(tmp_path: Path, purpose: str) -> None:
    record = load_run_record(_write(tmp_path, purpose=purpose))
    assert record.isolation is Isolation.ISOLATED
    gate(record, previous_result_committed=None)


def test_a_local_development_record_passes_the_gate(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, isolation="local", purpose="development"))
    assert record.isolation is Isolation.LOCAL
    gate(record, previous_result_committed=None)


def test_launch_check_refuses_a_local_admission_record(tmp_path: Path) -> None:
    assert main(["launch", "--check", str(_write(tmp_path, isolation="local"))]) == 2


TASK = "agentclinic-repair-misleading-locus"
BASELINE = ["satyrn-evals-attempt-pi", "--model", "omlx/gemma-4-12B-it-MLX-8bit"]


def _pinned(tmp_path: Path, **over: object) -> RunRecord:
    return load_run_record(_write(tmp_path, task_tree_sha256=tree_digest(DEFAULT_TASKS_ROOT / TASK), **over))


def test_an_invocation_that_matches_the_record_is_accepted(tmp_path: Path) -> None:
    check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=BASELINE)


def test_an_invocation_for_another_task_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="is for task"):
        check_invocation(_pinned(tmp_path), task="format_number", task_dir=DEFAULT_TASKS_ROOT / "format_number", command=BASELINE)


def test_a_drifted_task_tree_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="task_tree_sha256 drifted"):
        check_invocation(load_run_record(_write(tmp_path)), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=BASELINE)


def test_an_invocation_of_another_arm_is_refused(tmp_path: Path) -> None:
    engine = [".venv/bin/satyrn-evals-attempt-engine", "--model", "omlx/gemma-4-12B-it-MLX-8bit"]
    with pytest.raises(RunRecordError, match="the command runs engine"):
        check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=engine)


def test_an_invocation_with_another_model_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="--model omlx/other"):
        check_invocation(
            _pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK,
            command=["satyrn-evals-attempt-pi", "--model=omlx/other"],
        )


def test_the_command_arm_and_model_are_read_from_either_spelling() -> None:
    assert command_arm(["/x/python", "-m", "satyrn_evals.attempt_engine"]) == "engine"
    assert command_arm(["cmd"]) is None
    assert command_model(["a", "--model=omlx/m"]) == "omlx/m"
    assert command_model(["a", "--model"]) is None


def test_a_command_with_a_repeated_model_flag_is_refused_even_when_the_first_matches(
    tmp_path: Path,
) -> None:
    """F4/R13: command_model returns the first --model; a smuggled second
    flag must not pass the cross-check on the strength of the first."""
    smuggled = [
        "satyrn-evals-attempt-pi",
        "--model",
        "omlx/gemma-4-12B-it-MLX-8bit",
        "--model",
        "omlx/other",
    ]
    with pytest.raises(RunRecordError, match="more than one --model"):
        check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=smuggled)


def test_a_command_with_a_repeated_model_flag_in_equals_form_is_refused(
    tmp_path: Path,
) -> None:
    smuggled = [
        "satyrn-evals-attempt-pi",
        "--model=omlx/gemma-4-12B-it-MLX-8bit",
        "--model=omlx/other",
    ]
    with pytest.raises(RunRecordError, match="more than one --model"):
        check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=smuggled)


def test_a_command_with_one_model_flag_still_passes(tmp_path: Path) -> None:
    check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=BASELINE)
