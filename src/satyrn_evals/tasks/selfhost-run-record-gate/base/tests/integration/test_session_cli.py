"""The session CLI end to end through the real dispatcher."""

import sys
from pathlib import Path

import pytest

from satyrn_evals import cli

pytestmark = pytest.mark.integration

DATA = Path(__file__).resolve().parent / "data"
FAKE = Path(__file__).resolve().parent / "fake_session_adapter.py"


def test_session_cli_runs_and_grades_clean(tmp_path: Path) -> None:
    code = cli.main(
        [
            "session",
            "mini-session",
            "--tasks-root",
            str(DATA),
            "--output",
            str(tmp_path),
            "--",
            sys.executable,
            str(FAKE),
            "clean",
        ]
    )
    assert code == 0
    session_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(session_dirs) == 1
    assert (session_dirs[0] / "session-record.json").is_file()
    assert list((session_dirs[0] / "checkpoints").iterdir())
    assert list((session_dirs[0] / "receipts").iterdir())
