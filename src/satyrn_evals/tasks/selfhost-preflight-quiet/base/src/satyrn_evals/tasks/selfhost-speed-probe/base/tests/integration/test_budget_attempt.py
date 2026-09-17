"""The output-token and turn budget against a live transcript.

Integration tier: a real worktree, the real Baseline adapter, a fake `pi`
(`fake_pi_build.py`) that reports usage. No model runs. Both directions: a
cell over budget is stopped as `BUDGET_EXCEEDED` with its `pi` gone; the same
adapter within budget is graded.
"""

import os
import sys
import time
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
CAMPAIGN = AttemptBudget(output_tokens=32_000, turns=48)


def _pi_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "pi"
    shim.write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", mode)


def _baseline() -> list[str]:
    return [sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"]


def _gone(pid: int, within: float = 5.0) -> bool:
    stop = time.monotonic() + within
    while time.monotonic() < stop:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_a_cell_over_the_output_budget_is_stopped_as_budget_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pi_on_path(tmp_path, monkeypatch, "spend")
    pidfile = tmp_path / "pi.pid"
    monkeypatch.setenv("SATYRN_FAKE_PI_PIDFILE", str(pidfile))
    started = time.monotonic()
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts",
                     command=_baseline(), timeout=120, budget=CAMPAIGN)
    assert time.monotonic() - started < 60  # the fake sleeps 120 s; only the budget ends it
    assert (record.code, record.outcome) == (AttemptCode.BUDGET_EXCEEDED, AttemptOutcome.REFUSED)
    assert record.message == "attempt command spent 40000 output tokens, over the budget of 32000"
    assert record.command_exit is None and record.verdict is None
    assert _gone(int(pidfile.read_text()))


def test_the_same_adapter_within_budget_is_graded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _pi_on_path(tmp_path, monkeypatch, "commit")
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts",
                     command=_baseline(), timeout=120, budget=CAMPAIGN)
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
