"""End-to-end run: the fake seam command, n attempts, one summary."""

import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"


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
