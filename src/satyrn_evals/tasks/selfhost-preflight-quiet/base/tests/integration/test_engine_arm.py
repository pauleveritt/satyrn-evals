"""The Engine arm against a fake model: `/implement` behind the Evals seam.

Integration tier and engine-checkout dependent (skips without one, as the
E5 rows in `test_attempt.py` do; set SATYRN_V4_ENGINE_REPO). The real
`satyrn-evals-attempt-engine`, the real `satyrn-engine derive`/`deliver`/
`attempt`, the guards' extension files on Pi's argv; `pi` is
`fake_pi_build.py`. No model runs.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

from integration.test_attempt import (  # type: ignore[missing-import]  # pytest sibling resolution (tests/ on sys.path)
    _configure_engine,
    _engine_repo,
)
from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_engine import RECEIPT_NAME
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell_evidence import collect_evidence
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.pathology import count_transcript
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
CAMPAIGN = AttemptBudget(output_tokens=32_000, turns=48)


def _engine_arm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> list[str]:
    engine_repo = _engine_repo()
    uv = _configure_engine(tmp_path, monkeypatch, engine_repo)
    (tmp_path / "bin" / "pi").unlink()
    (tmp_path / "bin" / "pi").write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    (tmp_path / "bin" / "pi").chmod(0o755)
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", mode)
    return [sys.executable, "-m", "satyrn_evals.attempt_engine", "--model", "omlx/fixture",
            "--engine-repo", os.fspath(engine_repo), "--uv-bin", os.fspath(uv)]


def test_the_engine_arm_delivers_a_candidate_that_is_harvested_and_graded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = _engine_arm(tmp_path, monkeypatch, "write")
    output = tmp_path / "attempts"
    record = attempt(task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300, budget=CAMPAIGN)
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    cell = output / record.attempt_dir
    receipt = json.loads((cell / RECEIPT_NAME).read_text())
    assert (receipt["code"], receipt["validation"]) == ("OK", "passed")
    assert receipt["guard_firings"]["command_bounded"] == 1
    assert sorted(parse_patch_paths((cell / "patch.diff").read_text())) == ["calc/core.py", "calc/format.py", "calc/helpers.py"]
    transcript = (cell / "transcript.txt").read_text()
    assert count_transcript(transcript, had_patch=True).measured is True
    assert collect_evidence(transcript).guard_firings == {"command_bounded": 1}


def test_an_engine_cell_over_budget_is_stopped_and_leaves_no_model_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = _engine_arm(tmp_path, monkeypatch, "spend")
    pidfile = tmp_path / "pi.pid"
    monkeypatch.setenv("SATYRN_FAKE_PI_PIDFILE", os.fspath(pidfile))
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts", command=command, timeout=300, budget=CAMPAIGN)
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert record.retained_path is None
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while time.monotonic() < stop:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail(f"fake pi {pid} outlived its cell")


def test_an_engine_cell_under_the_engines_own_budget_is_stopped_by_the_harness_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The harness's teardown, not the engine's, ends this cell.

    ``trickle`` reports 20,000 output tokens on one turn -- under the
    engine's own default budget (32,000, written into the contract by
    `derive`) and under `deliver`'s live enforcement of it -- so a lower
    harness-only budget (16,000) is the only thing that can trip. If the
    harness's teardown signal never reaches `deliver`'s Pi (each in its own
    process group, Ruling 8/final review Important 1), the fake keeps
    running, the engine tree beneath `deliver` is never told to stop, and
    the transcript would keep growing after this function reads it.
    """
    engine_tmp = tmp_path / "engine-tmp"
    engine_tmp.mkdir()
    monkeypatch.setenv("TMPDIR", os.fspath(engine_tmp))
    command = _engine_arm(tmp_path, monkeypatch, "trickle")
    pidfile = tmp_path / "pi.pid"
    monkeypatch.setenv("SATYRN_FAKE_PI_PIDFILE", os.fspath(pidfile))
    harness_budget = AttemptBudget(output_tokens=16_000, turns=48)
    record = attempt(
        task="calc-build",
        tasks_root=TASKS,
        output=tmp_path / "attempts",
        command=command,
        timeout=300,
        budget=harness_budget,
    )
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert record.command_exit is None, "the harness's stop, not a normal exit, must have ended this cell"
    assert record.retained_path is None
    assert record.attempt_dir is not None
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while time.monotonic() < stop:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail(f"fake pi {pid} outlived its cell")
    cell = tmp_path / "attempts" / record.attempt_dir
    assert not (cell / RECEIPT_NAME).exists(), "deliver must never have produced a receipt"
    transcript_path = cell / "transcript.txt"
    digest_at_return = hashlib.sha256(transcript_path.read_bytes()).hexdigest()
    assert digest_at_return == record.transcript_digest
    time.sleep(1)
    assert hashlib.sha256(transcript_path.read_bytes()).hexdigest() == record.transcript_digest, (
        "a still-running fake pi kept appending to the transcript after the harness returned"
    )
    leftover = sorted(p.name for p in engine_tmp.iterdir() if p.name.startswith("satyrn-engine-"))
    assert leftover == [], f"deliver's temporary directory was never cleaned up: {leftover}"
