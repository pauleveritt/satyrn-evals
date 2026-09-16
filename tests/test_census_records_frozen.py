"""The five frozen census records still match the task trees they pin.

A record's ``task_tree_sha256`` is checked by the launcher at launch, which
refuses on drift; this row catches the drift in the default tier instead,
before a night is started. The 2026-09-16 fix wave moved
``selfhost-cell-loop``'s digest (a ``validity.commit`` correction in its
manifest) under a record frozen the day before, and nothing in the gates saw
it. No model, network, or subprocess.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.task_tree import tree_digest

RECORDS = Path(__file__).resolve().parent.parent / "records"
CENSUS = sorted(RECORDS.glob("2026-09-16-census-*.json"))
CENSUS = [p for p in CENSUS if not p.name.endswith(".result.json")]


@pytest.mark.parametrize("record_path", CENSUS, ids=[p.stem for p in CENSUS])
def test_a_frozen_census_record_pins_the_current_task_tree(record_path: Path) -> None:
    record = json.loads(record_path.read_text())
    task_dir = DEFAULT_TASKS_ROOT / record["task"]
    assert record["task_tree_sha256"] == tree_digest(task_dir), (
        f"{record_path.name} pins a tree that has drifted; re-issue the record "
        "with `record new` before the night"
    )


def test_the_five_census_records_are_all_present() -> None:
    assert [p.stem.removeprefix("2026-09-16-census-") for p in CENSUS] == sorted(
        ["agentclinic-repair-depth-3", "selfhost-cell-loop", "selfhost-docs-linter",
         "selfhost-run-record-gate", "selfhost-speed-probe"]
    )
