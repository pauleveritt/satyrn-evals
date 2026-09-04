"""V8 agentclinic fixtures: every known-good/known-broken patch applies.

Real git apply is integration tier (spawns git; default tier stays
subprocess-free). Grading (P5's gate) re-applies each fixture through the
real grade; this file proves the patches themselves are well-formed git
diffs against a fresh base copy before any grading runs.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
from test_agentclinic_reconstruction import STATES

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("fixture", ["known-good", "known-broken"])
def test_fixture_applies_cleanly_to_a_fresh_base(
    state: str, fixture: str, tmp_path: Path
) -> None:
    task_dir = DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}"
    work = tmp_path / state
    shutil.copytree(task_dir / "base", work)
    subprocess.run(["git", "init", "-q"], cwd=work, check=True, capture_output=True)
    patch = (task_dir / "fixtures" / f"{fixture}.patch").read_text()
    applied = subprocess.run(
        ["git", "apply", "-"],
        input=patch.encode(),
        cwd=work,
        capture_output=True,
    )
    assert applied.returncode == 0, (state, fixture, applied.stderr.decode())
