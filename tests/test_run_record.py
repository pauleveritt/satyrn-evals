import json
from pathlib import Path

import pytest

from satyrn_evals.errors import UsageError
from satyrn_evals.run_record import RunRecord, RunRecordError, gate, load_run_record

GOOD = {
    "version": 1, "task": "agentclinic-repair-misleading-locus", "task_tree_sha256": "a" * 64,
    "arm": "baseline", "model": "omlx/gemma-4-12B-it-MLX-8bit", "condition": "cold", "n": 4,
    "mode": "attended", "max_minutes": 60,
    "stop_rule": "established infrastructure failure only", "decision_rule": "presence counts; no rate",
    "previous_result": None,
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
