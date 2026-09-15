"""End-to-end: run -> regrade -> summarize over the real fake seam."""

import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.rescore import regrade_attempt, summarize_output
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = (
    DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
)


def test_run_regrade_summarize_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "run"
    run(
        task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=output,
        command=[sys.executable, str(FAKE), "--patch", str(KNOWN_GOOD),
                 "--transcript", "wrote the fix"],
        n=2, timeout=123.0,
    )
    before = (output / "summary.json").read_text()
    # re-score every cell explicitly by name (refusals no-op; graded re-grade)
    for cell in sorted(p for p in output.iterdir() if p.is_dir()):
        regrade_attempt(cell, tasks_root=DEFAULT_TASKS_ROOT)
    after_regrade = summarize_output(output, tasks_root=DEFAULT_TASKS_ROOT)
    # the rebuild is byte-identical to the run's own summary
    assert (output / "summary.json").read_text() == before
    assert after_regrade.attempted == 2
