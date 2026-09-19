"""The BUDGET_EXCEEDED branches harvest the worktree they are about to release.

The default-tier tests fake the cumulative-patch build (the only subprocess the
harvest needs), so `just gates` exercises both over-budget harvest branches --
and the blank and raising-build negatives -- with no subprocess. The
integration tests below need a real repository, because a real cumulative patch
is a real Git operation; they prove the harvest against Git itself.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

import satyrn_evals.workspace as workspace_module
from satyrn_evals.attempt import TRANSCRIPT_ENV
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.session_patch import PatchCapture
from satyrn_evals.workspace import (
    TRIPPED_PATCH_NAME,
    WorkspaceCode,
    prepare_workspace,
    release_workspace,
    run_prepared_command,
)

OVER = json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"output": 99}}})

_CAPTURED = "diff --git a/src/app.py b/src/app.py\n+value = 2\n"


class _TrippedLiveProcess:
    """A command that has already written its over-budget transcript and is
    still running: the poll trips before any wait."""

    pid = 4242

    def wait(self, timeout: float | None = None) -> int:
        raise AssertionError("a tripped live process must never be waited on")


class _WritesThenExits:
    """A command that writes its last transcript lines and exits in one wait."""

    pid = 4242

    def __init__(self, transcript: Path, text: str) -> None:
        self.transcript = transcript
        self.text = text

    def wait(self, timeout: float | None = None) -> int:
        self.transcript.write_text(self.text)
        return 0


def _capture(text: str) -> PatchCapture:
    return PatchCapture(patch_text=text, changed_paths=(), status_lines=())


def _default_state(tmp_path: Path) -> workspace_module._WorkspaceState:
    parent = tmp_path / "owned"
    parent.mkdir(parents=True)
    repository = parent / "seed"
    repository.mkdir()
    worktree = parent / "worktree"
    worktree.mkdir()
    state = workspace_module._WorkspaceState(parent, repository, worktree)
    state.base_sha = "a" * 40
    return state


def _default_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    process: object,
    build: object,
    transcript_text: str | None = None,
) -> tuple[workspace_module.WorkspaceResult, Path]:
    state = _default_state(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    if transcript_text is not None:
        transcript.write_text(transcript_text)
    out = tmp_path / TRIPPED_PATCH_NAME
    monkeypatch.setattr(workspace_module.subprocess, "Popen", lambda *_a, **_k: process)
    monkeypatch.setattr(
        workspace_module, "_teardown_process", lambda *_a, **_k: (True, None)
    )
    monkeypatch.setattr("satyrn_evals.session_patch.build_cumulative_patch", build)
    result = workspace_module._run_command(
        ("x",),
        state,
        {},
        10.0,
        0.1,
        transcript=transcript,
        budget=AttemptBudget(output_tokens=1, turns=48),
        tripped_patch=out,
    )
    return result, out


def test_the_teardown_over_budget_branch_harvests_the_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, out = _default_run(
        tmp_path,
        monkeypatch,
        process=_TrippedLiveProcess(),
        build=lambda *_a, **_k: _capture(_CAPTURED),
        transcript_text=f"{OVER}\n",
    )
    assert result.code is WorkspaceCode.BUDGET_EXCEEDED
    assert result.command_exit is None
    assert out.read_text() == _CAPTURED


def test_the_normal_exit_over_budget_branch_harvests_the_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, out = _default_run(
        tmp_path,
        monkeypatch,
        process=_WritesThenExits(tmp_path / "transcript.jsonl", f"{OVER}\n"),
        build=lambda *_a, **_k: _capture(_CAPTURED),
    )
    assert result.code is WorkspaceCode.BUDGET_EXCEEDED
    assert result.command_exit == 0
    assert out.read_text() == _CAPTURED


def test_a_blank_captured_patch_writes_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, out = _default_run(
        tmp_path,
        monkeypatch,
        process=_WritesThenExits(tmp_path / "transcript.jsonl", f"{OVER}\n"),
        build=lambda *_a, **_k: _capture("  \n"),
    )
    assert result.code is WorkspaceCode.BUDGET_EXCEEDED
    assert not out.exists()


@pytest.mark.parametrize(
    "error",
    [OSError("git"), subprocess.SubprocessError("git"), ValueError("git")],
)
def test_a_failed_build_is_swallowed_and_writes_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def fail(*_args: object, **_kwargs: object) -> PatchCapture:
        raise error

    result, out = _default_run(
        tmp_path,
        monkeypatch,
        process=_WritesThenExits(tmp_path / "transcript.jsonl", f"{OVER}\n"),
        build=fail,
    )
    assert result.code is WorkspaceCode.BUDGET_EXCEEDED
    assert not out.exists()


def test_a_write_failure_on_the_teardown_branch_still_tears_down_and_is_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_harvest_tripped` runs before `_teardown` on this branch (I1): a write
    failure must not skip teardown and leave a live cell running. The
    destination's parent directory does not exist, so the write inside
    `_harvest_patch` fails -- teardown must still fire."""
    state = _default_state(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(f"{OVER}\n")
    out = tmp_path / "missing-parent" / TRIPPED_PATCH_NAME
    torn_down: list[bool] = []
    monkeypatch.setattr(
        workspace_module.subprocess, "Popen", lambda *_a, **_k: _TrippedLiveProcess()
    )

    def fake_teardown_process(*_a: object, **_k: object) -> tuple[bool, str | None]:
        torn_down.append(True)
        return True, None

    monkeypatch.setattr(workspace_module, "_teardown_process", fake_teardown_process)
    monkeypatch.setattr(
        "satyrn_evals.session_patch.build_cumulative_patch",
        lambda *_a, **_k: _capture(_CAPTURED),
    )
    result = workspace_module._run_command(
        ("x",),
        state,
        {},
        10.0,
        0.1,
        transcript=transcript,
        budget=AttemptBudget(output_tokens=1, turns=48),
        tripped_patch=out,
    )
    assert torn_down == [True]  # teardown ran despite the write failure
    assert result.code is WorkspaceCode.BUDGET_EXCEEDED
    assert not out.exists()


def test_the_teardown_branch_tears_down_even_when_the_harvest_itself_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defense in depth for I1: `_harvest_patch` is guarded against write
    failures, but the teardown-branch call site must not depend on that --
    any exception out of `_harvest_tripped` must still leave teardown
    structurally unskippable."""
    state = _default_state(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(f"{OVER}\n")
    out = tmp_path / TRIPPED_PATCH_NAME
    torn_down: list[bool] = []
    monkeypatch.setattr(
        workspace_module.subprocess, "Popen", lambda *_a, **_k: _TrippedLiveProcess()
    )

    def fake_teardown_process(*_a: object, **_k: object) -> tuple[bool, str | None]:
        torn_down.append(True)
        return True, None

    monkeypatch.setattr(workspace_module, "_teardown_process", fake_teardown_process)

    def raising_harvest_tripped(*_a: object, **_k: object) -> None:
        raise RuntimeError("unexpected harvest bug")

    monkeypatch.setattr(workspace_module, "_harvest_tripped", raising_harvest_tripped)
    with pytest.raises(RuntimeError, match="unexpected harvest bug"):
        workspace_module._run_command(
            ("x",),
            state,
            {},
            10.0,
            0.1,
            transcript=transcript,
            budget=AttemptBudget(output_tokens=1, turns=48),
            tripped_patch=out,
        )
    assert torn_down == [True]  # teardown ran even though the harvest raised


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


@pytest.mark.integration
def test_a_tripped_worktree_with_changes_is_harvested(tmp_path: Path) -> None:
    code, _exit, patch = _trip(
        tmp_path,
        f"printf 'value = 2\\n' > src/app.py; printf '%s\\n' '{OVER}' >> \"${{{TRANSCRIPT_ENV}}}\"; sleep 30",
    )
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert "src/app.py" in patch and "+value = 2" in patch


@pytest.mark.integration
def test_a_tripped_worktree_with_no_change_writes_no_patch(tmp_path: Path) -> None:
    code, _exit, patch = _trip(
        tmp_path, f"printf '%s\\n' '{OVER}' >> \"${{{TRANSCRIPT_ENV}}}\"; sleep 30"
    )
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert patch == ""


@pytest.mark.integration
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
