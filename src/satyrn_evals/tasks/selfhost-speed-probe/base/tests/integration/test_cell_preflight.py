"""The cell preflight on this machine: real sudo, a hunt scoped to a scratch directory.

The full root-anchored hunt takes about a minute and is the maintainer's
attended step; here the hunt runs over the test's own scratch directory so a
planted file proves the refusal and its removal proves the silence.
"""

import json
import sys
from pathlib import Path

import pytest

from satyrn_evals.arms import load_arm
from satyrn_evals.cell_preflight import preflight_cell
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from preflight_settings import read_cell_pi_models  # noqa: E402

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
PINNED = load_arm(REPO / "arms" / "baseline-ornith15-9b.json").pins.pi


def test_the_cell_cannot_read_the_maintainers_trees_and_runs_the_pinned_pi(cell_scratch: Path) -> None:
    report = preflight_cell(pinned_pi=PINNED, protected=(REPO, DEFAULT_TASKS_ROOT, Path.home()), hunt_root=None)
    assert report.problems == []


def test_a_directory_the_cell_can_read_is_a_problem(cell_scratch: Path) -> None:
    report = preflight_cell(pinned_pi=PINNED, protected=(cell_scratch,), hunt_root=None)
    assert report.problems == [f"the cell can read {cell_scratch}"]


def test_the_hunt_finds_a_planted_answer_key_and_nothing_once_it_is_gone(cell_scratch: Path) -> None:
    planted = cell_scratch / "leak" / "known-good.patch"
    planted.parent.mkdir()
    planted.write_text("diff --git a/x b/x\n")
    planted.chmod(0o664)
    planted.parent.chmod(0o2770)
    report = preflight_cell(pinned_pi=PINNED, protected=(), hunt_root=str(cell_scratch))
    assert report.problems == [f"the cell can find {planted}"]
    planted.unlink()
    assert preflight_cell(pinned_pi=PINNED, protected=(), hunt_root=str(cell_scratch)).problems == []


def test_the_cell_users_pi_models_are_read_as_the_cell(cell_scratch: Path) -> None:
    models = read_cell_pi_models()
    assert "omlx" in models["providers"], json.dumps(models)[:200]
