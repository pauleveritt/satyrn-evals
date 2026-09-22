"""T8: hostile ambient git cannot redirect grading."""

import os
from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASK = DEFAULT_TASKS_ROOT / "format_number"
PATCH = TASK / "fixtures" / "known-good.patch"


def test_grade_ignores_ambient_git_redirect(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("GIT_DIR", os.fspath(tmp_path / "trap" / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", os.fspath(elsewhere))
    monkeypatch.setenv("GIT_INDEX_FILE", os.fspath(tmp_path / "trap-index"))
    try:
        receipt = grade(TASK, PATCH, tmp_path / "receipt.json")
    finally:
        monkeypatch.undo()
    assert receipt.verdict is Verdict.PASS  # graded the real tree
    # the redirected work tree was never materialized
    assert not elsewhere.exists()
    assert not (tmp_path / "trap-index").exists()
