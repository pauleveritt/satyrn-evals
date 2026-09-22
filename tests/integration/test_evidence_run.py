"""A run's summary carries evidence for a cell the budget stopped."""

import json
import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.budget import AttemptBudget
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"


def test_a_budget_stopped_cell_has_evidence_in_the_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pi").write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    (bin_dir / "pi").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", "spend")
    output = tmp_path / "run"
    summary = run(task="calc-build", tasks_root=TASKS, output=output, n=1, timeout=120,
                  command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"],
                  budget=AttemptBudget(output_tokens=32_000, turns=48))
    assert summary.code_counts["BUDGET_EXCEEDED"] == 1
    [cell] = summary.cells
    written = json.loads((output / "summary.json").read_text())
    assert written["pathology"][cell]["measured"] is False
    evidence = written["evidence"][cell]
    assert (evidence["transcript"], evidence["turns"], evidence["output_tokens"], evidence["timeline"]) == (True, 2, 40_000, True)
