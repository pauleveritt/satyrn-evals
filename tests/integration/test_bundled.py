"""The evidence floor (BRIEF.md rule 2): the bundled task's fixtures, named.

The grader is not done until it has accepted the known-good patch and
rejected the known-broken one.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration


def _fixture(name: str) -> Path:
    return DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / name


def test_bundled_known_good_patch_is_accepted(tmp_path: Path) -> None:
    receipt = tmp_path / "r.json"
    code = main(
        ["grade", "format_number", str(_fixture("known-good.patch")), "--receipt", str(receipt)]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["task"] == "format_number"
    assert data["verdict"] == "pass"
    assert data["evidence"]["counts"]["passed"] == 4


def test_bundled_known_broken_patch_is_rejected(tmp_path: Path) -> None:
    receipt = tmp_path / "r.json"
    code = main(
        ["grade", "format_number", str(_fixture("known-broken.patch")), "--receipt", str(receipt)]
    )
    assert code == 0
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "fail"


def test_bundled_unappliable_patch_exits_3(tmp_path: Path) -> None:
    bad = tmp_path / "bad.patch"
    bad.write_text(
        "diff --git a/solution.py b/solution.py\n"
        "--- a/solution.py\n"
        "+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def format_number(n: int) -> str:\n"
        "-    return str(n) + 'x'\n"
        "+    return str(n)\n"
    )
    receipt = tmp_path / "r.json"
    code = main(["grade", "format_number", str(bad), "--receipt", str(receipt)])
    assert code == 3
    data = json.loads(receipt.read_text())
    assert data["verdict"] == "unavailable"
