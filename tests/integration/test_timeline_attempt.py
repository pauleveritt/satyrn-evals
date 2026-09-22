"""The harness timeline beside a real attempt: both arms get it from the harness."""

import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.timeline import TIMELINE_NAME, read_timeline

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"


def test_every_tool_call_of_an_attempt_has_a_start_and_an_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pi").write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    (bin_dir / "pi").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", "commit")
    output = tmp_path / "attempts"
    record = attempt(task="calc-build", tasks_root=TASKS, output=output,
                     command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"], timeout=120)
    assert record.code is AttemptCode.OK and record.attempt_dir is not None
    spans = read_timeline((output / record.attempt_dir / TIMELINE_NAME).read_text())
    assert sorted(spans) == ["b0", "w0", "w1", "w2"]
    assert all(span.ended is not None for span in spans.values())
    assert spans["b0"].tool_name == "bash"
