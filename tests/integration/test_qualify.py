"""Offline qualification with the real grader, adapter and harness; no model.

Roadmap row 2b: "every candidate passes offline qualification". Nothing is
copied out of a bundled hidden task: the refusal row uses the visible
``calc-build`` fixture task.
"""

import shutil
from pathlib import Path

import pytest

from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.qualify import (
    CEILING_CANDIDATES,
    FLOOR_CANDIDATES,
    HELDOUT_TASKS,
    qualify,
)

pytestmark = pytest.mark.integration

FIXTURE_TASKS = Path(__file__).parent / "data" / "tasks"


@pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES, *HELDOUT_TASKS])
def test_every_candidate_qualifies_offline(name: str) -> None:
    checks = qualify(DEFAULT_TASKS_ROOT / name)
    assert [check.name for check in checks] == ["known-good run 1", "known-good run 2", "known-good run 3", "known-broken", "r1-plan-prompt", "prompt-edits", "authored-disclosure", "live-harvest"]
    assert all(check.passed for check in checks), "\n".join(check.line(name) for check in checks)


def test_a_task_whose_known_broken_fixture_passes_does_not_qualify(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "calc-build"
    shutil.copytree(FIXTURE_TASKS / "calc-build", task)
    shutil.copyfile(task / "fixtures" / "known-good.patch", task / "fixtures" / "known-broken.patch")
    failed = [check.name for check in qualify(task) if not check.passed]
    assert failed == ["known-broken"]


def test_the_qualify_command_exits_zero_for_a_qualifying_task(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["qualify", "calc-build", "--tasks-root", str(FIXTURE_TASKS)]) == 0
    out = capsys.readouterr().out
    # Every check line is prefixed "qualify calc-build: "; a passing one also
    # carries " ok: ". Comparing the two counts asserts every check passed
    # without pinning how many checks `qualify` currently runs.
    assert out.count(" ok: ") == out.count("qualify calc-build: ")
