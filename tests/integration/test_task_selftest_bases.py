"""Integration tier: every Engine-nameable task base self-tests green, before and after its known-good patch.

The 2026-09-18 route proof was void because the Engine's self-test could not
go green on the real task tree. This is the check the whole-path review owed,
run against every task an Engine record can name with the real runner.
"""

from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.qualify import CENSUS_TASKS
from satyrn_evals.task_selftest import task_self_test

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("task", sorted(CENSUS_TASKS))
def test_the_task_self_tests_green_on_the_base_and_the_known_good_patch(task: str) -> None:
    task_dir = Path(DEFAULT_TASKS_ROOT) / task
    manifest = load_manifest(task_dir)
    assert task_self_test(task_dir, manifest).problems == []
