"""Helpers for integration rows that run commands as the cell user (fixture: ``conftest.cell_scratch``)."""

import os
import subprocess
from pathlib import Path

from satyrn_evals.cell import cell_command


def cell_process_alive(pid: int) -> bool:
    """Whether ``pid`` still exists; the maintainer may not signal it, so EPERM means alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_as_cell(argv: list[str], *, cwd: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cell_command(argv, cwd=cwd, environment=environment), cwd=cwd, capture_output=True, text=True, check=False
    )
