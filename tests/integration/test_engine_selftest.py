"""Integration tier: the Engine-argv preflight against the exported Engine.

Live acceptance (maintainer's 2026-09-18 order): after the export under the
cells root, the new preflight runs the Engine's own derive + self-test on
every Engine-nameable base and on its known-good state, and requires it green.
Skips until the export exists, which is the maintainer's step.
"""

import os
from pathlib import Path

import pytest

from satyrn_evals.arms import load_arm
from satyrn_evals.cell_engine import arm_export
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.qualify import CENSUS_TASKS
from satyrn_evals.task_selftest import engine_self_test

pytestmark = pytest.mark.integration

ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"


@pytest.mark.parametrize("task", sorted(CENSUS_TASKS))
def test_the_engine_argv_preflight_is_green_on_a_real_base_and_known_good(task: str) -> None:
    arm = load_arm(ENGINE_ARM)
    export = arm_export(arm)
    if export is None or not export.is_dir():
        pytest.skip(f"the Engine export is not present yet: {export} (the maintainer's step)")
    task_dir = Path(DEFAULT_TASKS_ROOT) / task
    manifest = load_manifest(task_dir)
    report = engine_self_test(
        task_dir,
        manifest,
        engine=("uv", "run", "--no-sync", "--project", os.fspath(export), "satyrn-engine"),
        request=manifest.contract,
        token_budget=48000,
        turn_budget=72,
    )
    assert report.problems == [], report.problems
    assert report.checked["known_good_exit"] == 0
