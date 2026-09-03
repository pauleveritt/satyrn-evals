"""Integration tier: the V1 evidence floor on the captured local-pings task.

Mirrors tests/integration/test_bundled.py for format_number: the grader is
not done until it has accepted the known-good patch and rejected the
known-broken one, each asserted by naming the fixture (BRIEF.md rule 2).

These tests spawn Git and pytest and need svcs's test dependencies in the
runtime environment, so they are marked integration and do not run in CI.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration

_TASK = "local-pings"


def _fixture(name: str) -> Path:
    return DEFAULT_TASKS_ROOT / _TASK / "fixtures" / name


def test_local_pings_known_good_patch_is_accepted(tmp_path: Path) -> None:
    receipt = tmp_path / "r.json"
    code = main(
        ["grade", _TASK, str(_fixture("known-good.patch")), "--receipt", str(receipt)]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["task"] == _TASK
    assert data["verdict"] == "pass"
    assert data["evidence"]["counts"]["passed"] == 5


def test_local_pings_known_broken_patch_is_rejected(tmp_path: Path) -> None:
    receipt = tmp_path / "r.json"
    code = main(
        ["grade", _TASK, str(_fixture("known-broken.patch")), "--receipt", str(receipt)]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "fail"
    # The failure must be the curator cases catching the type-set adversary
    # (row 3's shape), not "anything went wrong": rejection is the default
    # outcome of most failures, so a broken test would pass silently.
    assert data["evidence"]["counts"]["passed"] == 3
    assert data["evidence"]["counts"]["failed"] == 2
