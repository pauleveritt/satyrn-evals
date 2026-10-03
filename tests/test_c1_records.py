"""The six C1 records carry the design's parameters and pin the current task
trees (docs/superpowers/specs/2026-10-02-c1-requalify-design.md §5). A base
that moves after they were issued fails here, before any sitting.
No model, network, or subprocess.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.qualify import CENSUS_TASKS
from satyrn_evals.run_record import CONFINEMENT
from satyrn_evals.task_tree import tree_digest

ROOT = Path(__file__).resolve().parent.parent
DESIGN = "docs/superpowers/specs/2026-10-02-c1-requalify-design.md"
MACHINE = "Apple M5 Max"
C1 = sorted(p for p in (ROOT / "records").glob("*-c1-*.json") if not p.name.endswith(".result.json"))
EXPECTED = {
    "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit", "backend": "omlx",
    "purpose": "admission", "confinement": CONFINEMENT, "mode": "batch", "n": 6, "k": 3,
    "token_budget": 48_000, "turn_budget": 72, "command_backstop_s": 4_800, "max_minutes": 240,
    "previous_result": None,
}


def c1_problems(record: dict, current_tree: str) -> list[str]:
    """Every way a record departs from the design's §5 table, or ``[]``."""
    problems = [
        f"{key} is {record.get(key)!r}, want {want!r}"
        for key, want in EXPECTED.items()
        if record.get(key) != want
    ]
    if record.get("rung") != CENSUS_TASKS.get(record.get("task", "")):
        problems.append(f"rung is {record.get('rung')!r}, want {CENSUS_TASKS.get(record.get('task', ''))!r}")
    if record.get("task_tree_sha256") != current_tree:
        problems.append("task_tree_sha256 is not the current tree")
    authority = record.get("authority") or ""
    if DESIGN not in authority or MACHINE not in authority:
        problems.append("authority does not name the C1 design and the machine")
    return problems


def test_the_c1_records_are_exactly_the_census_set() -> None:
    tasks = [json.loads(p.read_text())["task"] for p in C1]
    assert sorted(tasks) == sorted(CENSUS_TASKS)


@pytest.mark.parametrize("path", C1, ids=lambda p: p.stem)
def test_a_c1_record_carries_the_design_and_pins_the_current_tree(path: Path) -> None:
    record = json.loads(path.read_text())
    assert c1_problems(record, tree_digest(DEFAULT_TASKS_ROOT / record["task"])) == []


def test_the_check_names_a_changed_budget_and_a_drifted_tree() -> None:
    """The refusal sibling, on a real record with one field changed at a time."""
    record = json.loads(C1[0].read_text())
    current = tree_digest(DEFAULT_TASKS_ROOT / record["task"])
    assert c1_problems({**record, "token_budget": 32_000}, current) == ["token_budget is 32000, want 48000"]
    assert c1_problems(record, "0" * 64) == ["task_tree_sha256 is not the current tree"]
