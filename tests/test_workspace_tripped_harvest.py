"""The BUDGET_EXCEEDED branches harvest the worktree they are about to release.

Pure but for git: marked `integration`, because a cumulative patch needs a real
repository. The both-directions pair is a tripped tree with changes and a
tripped tree with none; a fourth row proves the normal-exit over-budget branch
harvests too, not only the teardown branch.
"""

import json
import os
from pathlib import Path

import pytest

from satyrn_evals.attempt import TRANSCRIPT_ENV
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.workspace import (
    TRIPPED_PATCH_NAME,
    WorkspaceCode,
    prepare_workspace,
    release_workspace,
    run_prepared_command,
)

pytestmark = pytest.mark.integration

OVER = json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"output": 99}}})


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    (base / "src").mkdir(parents=True)
    (base / "src" / "app.py").write_text("value = 1\n")
    return base


def _command(script: str) -> list[str]:
    return ["/bin/sh", "-c", script]


def _trip(tmp_path: Path, script: str) -> tuple[WorkspaceCode, int | None, str]:
    workspace = prepare_workspace(
        base=_base(tmp_path),
        protected_paths=(),
        environment=dict(os.environ),
    )
    out = tmp_path / TRIPPED_PATCH_NAME
    transcript = tmp_path / "t.jsonl"
    try:
        result = run_prepared_command(
            workspace,
            command=_command(script),
            timeout=60.0,
            transcript=transcript,
            extra_environment={TRANSCRIPT_ENV: os.fspath(transcript)},
            budget=AttemptBudget(output_tokens=1, turns=48),
            tripped_patch=out,
        )
    finally:
        release_workspace(workspace)
    return result.code, result.command_exit, (out.read_text() if out.is_file() else "")


def test_a_tripped_worktree_with_changes_is_harvested(tmp_path: Path) -> None:
    code, _exit, patch = _trip(
        tmp_path,
        f"printf 'value = 2\\n' > src/app.py; printf '%s\\n' '{OVER}' >> \"${{{TRANSCRIPT_ENV}}}\"; sleep 30",
    )
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert "src/app.py" in patch and "+value = 2" in patch


def test_a_tripped_worktree_with_no_change_writes_no_patch(tmp_path: Path) -> None:
    code, _exit, patch = _trip(
        tmp_path, f"printf '%s\\n' '{OVER}' >> \"${{{TRANSCRIPT_ENV}}}\"; sleep 30"
    )
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert patch == ""


def test_a_normal_exit_over_budget_worktree_is_harvested(tmp_path: Path) -> None:
    """The lines written just before a normal exit still trip the budget, and
    that cell's worktree -- the one with the most to say -- is harvested before
    release on the normal-exit branch, not only on the teardown branch."""
    code, exit_code, patch = _trip(
        tmp_path,
        f"printf 'value = 2\\n' > src/app.py; "
        f"printf '%s\\n' '{OVER}' >> \"${{{TRANSCRIPT_ENV}}}\"",
    )
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert exit_code == 0
    assert "src/app.py" in patch and "+value = 2" in patch
