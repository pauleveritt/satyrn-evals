"""The live-harvest qualification: a build attempt through the real Baseline adapter.

Integration tier: real Git, a real worktree, the real `satyrn-evals-attempt-pi`
harvest, the real oracle. `pi` is `fake_pi_build.py`; no model runs.
"""

import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
KNOWN_GOOD = TASKS / "calc-build" / "fixtures" / "known-good.patch"


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


def test_a_build_attempt_that_commits_and_leaves_a_file_untracked_is_harvested_whole_and_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pi_on_path(tmp_path, monkeypatch, "commit")
    output = tmp_path / "attempts"
    record = attempt(task="calc-build", tasks_root=TASKS, output=output, command=_baseline(), timeout=120)
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    patch = (output / record.attempt_dir / "patch.diff").read_text()
    assert sorted(parse_patch_paths(patch)) == sorted(parse_patch_paths(KNOWN_GOOD.read_text())) == [
        "calc/core.py", "calc/format.py", "calc/helpers.py"]


def test_an_attempt_that_changes_nothing_is_no_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _pi_on_path(tmp_path, monkeypatch, "idle")
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts", command=_baseline(), timeout=120)
    assert record.code is AttemptCode.NO_PATCH
    assert record.command_exit == 0
