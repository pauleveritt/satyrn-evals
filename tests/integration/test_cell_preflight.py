"""The cell preflight on this machine: real sudo, a hunt scoped to a scratch directory.

The full root-anchored hunt takes about a minute and is the maintainer's
attended step; here the hunt runs over the test's own scratch directory so a
planted file proves the refusal and its removal proves the silence.
"""

import json
import os
import stat
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from integration.cell_support import (
    run_as_cell,  # type: ignore[missing-import]  # pytest sibling resolution
)
from integration.test_attempt import _engine_repo  # type: ignore[missing-import]
from satyrn_evals.arms import load_arm
from satyrn_evals.cell import cell_environment
from satyrn_evals.cell_engine import arm_export_problems, export_engine
from satyrn_evals.cell_preflight import preflight_cell
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from preflight_settings import read_cell_pi_models  # noqa: E402

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
PINNED = load_arm(REPO / "arms" / "baseline-ornith15-9b.json").pins.pi


@pytest.fixture
def hermetic_cells_root(tmp_path: Path) -> Path:
    """A sticky, empty stand-in for the real cells root (F2/R11).

    The real ``/Users/Shared/satyrn-cells`` is not sticky yet and holds
    ``spike/``, which is not the maintainer's to touch; these rows check
    the cell user, not the cells root's own hygiene, so they get a root
    the test controls.
    """
    root = tmp_path / "cells"
    root.mkdir()
    root.chmod(root.stat().st_mode | stat.S_ISVTX)
    return root


def test_the_cell_cannot_read_the_maintainers_trees_and_runs_the_pinned_pi(
    cell_scratch: Path, hermetic_cells_root: Path
) -> None:
    report = preflight_cell(
        pinned_pi=PINNED,
        protected=(REPO, DEFAULT_TASKS_ROOT, Path.home()),
        hunt_root=None,
        cells_root=hermetic_cells_root,
    )
    assert report.problems == []


def test_a_directory_the_cell_can_read_is_a_problem(cell_scratch: Path, hermetic_cells_root: Path) -> None:
    report = preflight_cell(
        pinned_pi=PINNED, protected=(cell_scratch,), hunt_root=None, cells_root=hermetic_cells_root
    )
    assert report.problems == [f"the cell can read {cell_scratch}"]


def test_the_hunt_finds_a_planted_answer_key_and_nothing_once_it_is_gone(
    cell_scratch: Path, hermetic_cells_root: Path
) -> None:
    planted = cell_scratch / "leak" / "known-good.patch"
    planted.parent.mkdir()
    planted.write_text("diff --git a/x b/x\n")
    planted.chmod(0o664)
    planted.parent.chmod(0o2770)
    report = preflight_cell(
        pinned_pi=PINNED, protected=(), hunt_root=str(cell_scratch), cells_root=hermetic_cells_root
    )
    assert report.problems == [f"the cell can find {planted}"]
    planted.unlink()
    assert preflight_cell(
        pinned_pi=PINNED, protected=(), hunt_root=str(cell_scratch), cells_root=hermetic_cells_root
    ).problems == []


def test_the_cell_users_pi_models_are_read_as_the_cell(cell_scratch: Path) -> None:
    models = read_cell_pi_models()
    assert "omlx" in models["providers"], json.dumps(models)[:200]


def test_the_hunt_run_as_the_cell_over_the_pinned_engine_export_finds_nothing(
    cell_scratch: Path, hermetic_cells_root: Path
) -> None:
    """The 2026-09-15 hunt refused on the whole-tree export; the allowlisted export of the same commit is silent,
    though the cell reads it, and it is the engine the committed arm pins."""
    committed = load_arm(REPO / "arms" / "engine-ornith15-9b.json")
    assert committed.pins.engine_commit is not None
    export = export_engine(_engine_repo(), committed.pins.engine_commit, root=cell_scratch)
    found = run_as_cell(
        ["/usr/bin/find", os.fspath(export / "packages"), "-name", "engine.ts"], cwd=export,
        environment=cell_environment(parent=cell_scratch),
    )
    assert found.stdout.strip() == os.fspath(export / "packages" / "engine" / "engine.ts"), found.stderr
    report = preflight_cell(pinned_pi=PINNED, protected=(), hunt_root=str(export), cells_root=hermetic_cells_root)
    assert report.problems == [] and report.checked["hunt_hits"] == []
    pointed = replace(committed, argv=("satyrn-evals-attempt-engine", "--engine-repo", os.fspath(export)))
    assert arm_export_problems(pointed) == []
