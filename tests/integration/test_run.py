"""End-to-end run: the fake seam command, n attempts, one summary."""

import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
HIDDEN_TASK_NAME = "session-mechanics"
HIDDEN_KNOWN_GOOD = (
    DEFAULT_TASKS_ROOT / HIDDEN_TASK_NAME / "fixtures" / "known-good.patch"
)


def _cmd(*args: str) -> list[str]:
    return [sys.executable, str(FAKE), *args]


def test_run_names_success_and_failure_fixtures(tmp_path: Path) -> None:
    success = run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "ok",
        command=_cmd("--patch", str(KNOWN_GOOD), "--transcript", "wrote the fix"),
        n=1,
    )
    assert success.attempted == 1
    assert success.verdict_counts["pass"] == 1
    assert (tmp_path / "ok" / "summary.json").exists()

    failure = run(
        task="format_number",
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "fail",
        command=_cmd("--no-patch"),
        n=1,
    )
    assert failure.refused == 1
    assert failure.code_counts["NO_PATCH"] == 1


def test_hidden_task_run_reports_contamination(tmp_path: Path) -> None:
    """The hidden oracle's tally rides the summary through the real fake seam.

    session-mechanics is hidden: every graded attempt carries a contamination
    finding, so the end-to-end summary must report it with the invariant
    graded = flagged + clean + unmeasured over the two derived cells. The
    oracle is pytest, which the fake seam's clean patch satisfies, but the
    verdict itself is beside the point here -- detection and tallying are.
    """
    summary = run(
        task=HIDDEN_TASK_NAME,
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path,
        command=_cmd(
            "--patch", str(HIDDEN_KNOWN_GOOD), "--transcript", "wrote the features"
        ),
        n=2,
    )
    assert summary.oracle_visibility == "hidden"
    assert summary.contamination is not None
    assert summary.contamination["graded"] == 2  # both attempts graded
    assert summary.contamination["graded"] == (
        summary.contamination["flagged"]
        + summary.contamination["clean"]
        + summary.contamination["unmeasured"]
    )
    assert len(summary.cells) == 2
