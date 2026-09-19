"""The declared line: harvested mid-run without disturbing the cell.

Default-tier tests fake the process and the cumulative-patch build, so
`just gates` proves: the harvest fires exactly once, at the crossing (not the
final tree); the cell is never signaled or torn down; a cell that never
crosses gets no file; a harvest failure is recorded and never changes the
cell's own outcome; the Engine arm's harvest reads its own internal deliver
worktree, not the Evals one.
"""

import os
import subprocess
from pathlib import Path

import pytest

import satyrn_evals.workspace as workspace_module
from satyrn_evals.budget import LineBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.session_patch import PatchCapture
from satyrn_evals.workspace import LINE_PATCH_NAME, WorkspaceCode

TOKEN_LINE = '{"type": "message_end", "message": {"role": "assistant", "usage": {"output": 101}}}'
TOKEN_AT_LIMIT = '{"type": "message_end", "message": {"role": "assistant", "usage": {"output": 100}}}'
TURN_LINE = '{"type": "turn_start"}'

_BEFORE = "diff --git a/a.py b/a.py\n+before\n"
_AFTER = "diff --git a/a.py b/a.py\n+before\n+after\n"


def _capture(text: str) -> PatchCapture:
    return PatchCapture(patch_text=text, changed_paths=(), status_lines=())


def _default_state(tmp_path: Path, *, isolation: Isolation = Isolation.LOCAL) -> workspace_module._WorkspaceState:
    parent = tmp_path / "owned"
    parent.mkdir(parents=True)
    repository = parent / "seed"
    repository.mkdir()
    worktree = parent / "worktree"
    worktree.mkdir()
    state = workspace_module._WorkspaceState(parent, repository, worktree, isolation=isolation)
    state.base_sha = "a" * 40
    return state


class _KeepsRunningProcess:
    """A cell that crosses the line, keeps running unsignaled, then exits on its own."""

    pid = 4242

    def __init__(self, exit_after: int = 3) -> None:
        self.polls = 0
        self.exit_after = exit_after

    def wait(self, timeout: float | None = None) -> int:
        self.polls += 1
        if self.polls >= self.exit_after:
            return 0
        raise subprocess.TimeoutExpired(cmd="x", timeout=timeout or 0)

    def kill(self) -> None:
        raise AssertionError("a line crossing must never signal the cell")

    def terminate(self) -> None:
        raise AssertionError("a line crossing must never signal the cell")

    def send_signal(self, _sig: int) -> None:
        raise AssertionError("a line crossing must never signal the cell")


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    transcript_text: str,
    line_budget: LineBudget,
    build,
    process: object | None = None,
    engine_arm: bool = False,
    state: workspace_module._WorkspaceState | None = None,
) -> tuple[workspace_module.WorkspaceResult, Path]:
    state = state if state is not None else _default_state(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(transcript_text)
    out = tmp_path / LINE_PATCH_NAME
    proc = process if process is not None else _KeepsRunningProcess()
    monkeypatch.setattr(workspace_module.subprocess, "Popen", lambda *_a, **_k: proc)
    monkeypatch.setattr(workspace_module, "_teardown_process", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("a line crossing must never tear the cell down")
    ))
    monkeypatch.setattr("satyrn_evals.session_patch.build_cumulative_patch", build)
    result = workspace_module._run_command(
        ("x",),
        state,
        {},
        10.0,
        0.1,
        transcript=transcript,
        line_budget=line_budget,
        line_patch=out,
        engine_arm=engine_arm,
    )
    return result, out


def test_crossing_the_token_line_harvests_at_the_crossing_not_the_final_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = {"text": _BEFORE}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=()):
        return _capture(tree["text"])

    process = _KeepsRunningProcess(exit_after=3)
    original_wait = process.wait

    def wait(timeout=None):
        try:
            return original_wait(timeout)
        finally:
            # Mutate the "worktree" only after the first poll -- i.e. after
            # the harvest, which happens on the transcript read that
            # precedes this poll in the same loop iteration.
            if process.polls == 1:
                tree["text"] = _AFTER

    process.wait = wait  # type: ignore[method-assign]

    result, out = _run(
        tmp_path, monkeypatch, transcript_text=TOKEN_LINE + "\n", line_budget=LineBudget(100, 48), build=build,
        process=process,
    )
    assert result.code is WorkspaceCode.OK
    assert result.command_exit == 0
    assert result.line_crossed is not None
    assert result.line_crossed.by == "tokens"
    assert result.line_crossed.output_tokens == 101
    assert result.line_patch_written is True
    assert result.line_harvest_error is None
    assert out.read_text() == _BEFORE  # not _AFTER


def test_crossing_the_turn_line_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text="\n".join([TURN_LINE] * 3) + "\n",
        line_budget=LineBudget(32000, 2),
        build=lambda *_a, **_k: _capture(_BEFORE),
    )
    assert result.line_crossed is not None
    assert result.line_crossed.by == "turns"
    assert result.line_crossed.turn == 3
    assert out.read_text() == _BEFORE


def test_crossing_exactly_at_the_limit_does_not_cross(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_AT_LIMIT + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: _capture(_BEFORE),
    )
    assert result.line_crossed is None
    assert result.line_patch_written is False
    assert not out.exists()


def test_never_crossing_leaves_null_and_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TURN_LINE + "\n",
        line_budget=LineBudget(32000, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("harvest must not run")),
    )
    assert result.line_crossed is None
    assert result.line_patch_written is False
    assert result.line_harvest_error is None
    assert not out.exists()


def test_a_harvest_failure_is_recorded_and_the_cell_is_unaffected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_a, **_k):
        raise OSError("git is wedged")

    result, out = _run(
        tmp_path, monkeypatch, transcript_text=TOKEN_LINE + "\n", line_budget=LineBudget(100, 48), build=fail,
    )
    assert result.code is WorkspaceCode.OK  # the cell's own outcome, unchanged
    assert result.command_exit == 0
    assert result.line_crossed is not None
    assert result.line_patch_written is False
    assert result.line_harvest_error == "OSError: git is wedged"
    assert not out.exists()


def _bind_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """I4b: fake every candidate as bound to this attempt (no real git)."""
    monkeypatch.setattr(
        workspace_module,
        "_engine_worktree_bound",
        lambda _state, _candidate, _environment: (True, ""),
    )


def test_the_engine_arm_harvest_reads_its_own_internal_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    engine_tmp = state.parent / "tmp"
    engine_tmp.mkdir()
    internal = engine_tmp / "satyrn-engine-abc123" / "worktree"
    internal.mkdir(parents=True)
    _bind_everything(monkeypatch)

    seen: dict[str, Path] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=()):
        seen["worktree"] = Path(worktree)
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=build,
        engine_arm=True,
        state=state,
    )
    assert seen["worktree"] == internal
    assert result.line_patch_written is True
    assert out.read_text() == _BEFORE


def test_the_engine_arm_harvest_trusts_only_its_own_internal_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Engine's internal deliver worktree is created by the cell user
    (satyrn-engine's own ``git worktree add``, run as ``satyrn-cell``), so a
    maintainer-run git harvest against it hits "dubious ownership" unless the
    harvest scopes ``safe.directory`` to that one resolved path -- never a
    blanket trust of every path (C1)."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    engine_tmp = state.parent / "tmp"
    engine_tmp.mkdir()
    internal = engine_tmp / "satyrn-engine-abc123" / "worktree"
    internal.mkdir(parents=True)
    _bind_everything(monkeypatch)

    seen: dict[str, object] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=()):
        seen["worktree"] = Path(worktree)
        seen["extra_config"] = tuple(extra_config)
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=build,
        engine_arm=True,
        state=state,
    )
    assert seen["worktree"] == internal
    assert seen["extra_config"] == ("-c", f"safe.directory={internal.resolve()}")
    assert result.line_patch_written is True


def test_a_baseline_harvest_never_widens_safe_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The maintainer already owns the Evals worktree's Git admin data (it
    created the worktree itself), so the ordinary harvest passes no extra
    safe.directory config -- the scoped trust is only for the Engine's own
    internal worktree."""
    seen: dict[str, object] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=()):
        seen["extra_config"] = tuple(extra_config)
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path, monkeypatch, transcript_text=TOKEN_LINE + "\n", line_budget=LineBudget(100, 48), build=build,
    )
    assert seen["extra_config"] == ()
    assert result.line_patch_written is True


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    (base / "src").mkdir(parents=True)
    (base / "src" / "app.py").write_text("value = 1\n")
    return base


@pytest.mark.integration
def test_a_real_worktree_crossing_the_line_is_harvested_and_the_cell_keeps_running(
    tmp_path: Path,
) -> None:
    """Real Git, real subprocess: the harness never sends a signal, the cell
    runs to its own end, and the line patch is the tree at the crossing."""
    import os

    from satyrn_evals.attempt import TRANSCRIPT_ENV
    from satyrn_evals.workspace import prepare_workspace, release_workspace

    workspace = prepare_workspace(base=_base(tmp_path), protected_paths=(), environment=dict(os.environ))
    out = tmp_path / LINE_PATCH_NAME
    transcript = tmp_path / "t.jsonl"
    script = (
        f"printf 'value = 2\\n' > src/app.py; "
        f"printf '%s\\n' '{TOKEN_LINE}' >> \"${{{TRANSCRIPT_ENV}}}\"; "
        f"sleep 2; "  # give the harness's poll loop time to harvest the crossing
        f"printf 'value = 3\\n' > src/app.py"  # further edits after the crossing
    )
    try:
        result = workspace_module.run_prepared_command(
            workspace,
            command=["/bin/sh", "-c", script],
            timeout=60.0,
            transcript=transcript,
            extra_environment={TRANSCRIPT_ENV: os.fspath(transcript)},
            line_budget=LineBudget(100, 48),
            line_patch=out,
        )
    finally:
        release_workspace(workspace)
    assert result.code is workspace_module.WorkspaceCode.OK
    assert result.line_crossed is not None
    assert result.line_crossed.by == "tokens"
    patch = out.read_text()
    assert "+value = 2" in patch
    assert "+value = 3" not in patch  # harvested at the crossing, not the final tree


def test_a_write_failure_on_the_line_path_is_recorded_and_the_cell_is_unaffected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A destination the harvest cannot write to (e.g. permission denied, or
    here a missing parent directory) must not escape `_harvest_patch`: the
    write failure is recorded exactly like a git failure, and the cell's own
    outcome is untouched (I1)."""
    state = _default_state(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(TOKEN_LINE + "\n")
    out = tmp_path / "missing-parent" / LINE_PATCH_NAME  # parent dir does not exist
    monkeypatch.setattr(
        workspace_module.subprocess, "Popen", lambda *_a, **_k: _KeepsRunningProcess()
    )
    monkeypatch.setattr(
        workspace_module,
        "_teardown_process",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("a line crossing must never tear the cell down")
        ),
    )
    monkeypatch.setattr(
        "satyrn_evals.session_patch.build_cumulative_patch",
        lambda *_a, **_k: _capture(_BEFORE),
    )
    result = workspace_module._run_command(
        ("x",),
        state,
        {},
        10.0,
        0.1,
        transcript=transcript,
        line_budget=LineBudget(100, 48),
        line_patch=out,
    )
    assert result.code is WorkspaceCode.OK  # the cell's own outcome, unchanged
    assert result.line_crossed is not None
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    assert "FileNotFoundError" in result.line_harvest_error
    assert not out.exists()


def test_the_engine_arm_records_an_error_when_the_worktree_cannot_be_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    (state.parent / "tmp").mkdir()  # empty: no satyrn-engine-* directory yet

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
    )
    assert result.line_crossed is not None
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    assert "engine" in result.line_harvest_error


# --- I4: the candidate is bound to this attempt before it is accepted ------


def _make_candidates(state: workspace_module._WorkspaceState, *names: str) -> list[Path]:
    engine_tmp = state.parent / "tmp"
    engine_tmp.mkdir(exist_ok=True)
    paths = []
    for name in names:
        candidate = engine_tmp / name / "worktree"
        candidate.mkdir(parents=True)
        paths.append(candidate)
    return paths


def _bind_only(monkeypatch: pytest.MonkeyPatch, *own: Path) -> None:
    """I4b: fake every candidate in ``own`` as bound; everything else foreign."""
    own_set = set(own)

    def fake(_state: object, candidate: Path, _environment: object) -> tuple[bool, str]:
        if candidate in own_set:
            return True, ""
        return False, (
            f"engine arm: candidate worktree {candidate} belongs to a foreign "
            "repository, not this attempt"
        )

    monkeypatch.setattr(workspace_module, "_engine_worktree_bound", fake)


def test_two_unbound_candidates_are_refused_not_the_first_of_several(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I4a: the mutation this test kills is 'accept the first match instead
    of refusing several' -- both candidates here are unbound (foreign), so
    accepting either would silently harvest the wrong tree."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    a, b = _make_candidates(state, "satyrn-engine-aaa", "satyrn-engine-bbb")
    _bind_only(monkeypatch)  # nothing is bound

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
    )
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    assert "engine" in result.line_harvest_error
    assert str(a) in result.line_harvest_error or str(b) in result.line_harvest_error


def test_one_foreign_candidate_is_refused_and_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I4b: a single match is no longer accepted unchecked -- a foreign
    directory (same glob shape, different repository) is refused and named,
    never silently diffed."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    (foreign,) = _make_candidates(state, "satyrn-engine-foreign")
    _bind_only(monkeypatch)  # nothing is bound

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
    )
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    assert str(foreign) in result.line_harvest_error
    assert "foreign" in result.line_harvest_error


def test_several_candidates_with_exactly_one_own_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I4b design choice: an ambient TMPDIR can hold a foreign
    ``satyrn-engine-*`` directory (another process, or the Engine
    repository's own test suite) alongside this attempt's own. Refusing the
    harvest just because something foreign is *also* present would defeat
    the point of binding, so the one candidate that binds to this attempt is
    still accepted."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    foreign, own = _make_candidates(state, "satyrn-engine-foreign", "satyrn-engine-own")
    _bind_only(monkeypatch, own)

    seen: dict[str, Path] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=()):
        seen["worktree"] = Path(worktree)
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=build,
        engine_arm=True,
        state=state,
    )
    assert seen["worktree"] == own
    assert result.line_patch_written is True
    assert out.read_text() == _BEFORE


def test_several_all_foreign_candidates_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    _make_candidates(state, "satyrn-engine-a", "satyrn-engine-b", "satyrn-engine-c")
    _bind_only(monkeypatch)  # nothing is bound

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
    )
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    assert "engine" in result.line_harvest_error


def test_several_own_candidates_are_ambiguous_and_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two candidates that both bind to this attempt should not happen in
    practice (satyrn-engine keeps one deliver worktree per attempt), but if
    it ever does, refuse rather than guess which one is current."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    a, b = _make_candidates(state, "satyrn-engine-a", "satyrn-engine-b")
    _bind_only(monkeypatch, a, b)

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
    )
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    assert "engine" in result.line_harvest_error


def test_local_profile_scans_the_engine_fallback_tmp_roots_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I4c: satyrn-engine's own ``_temporary_parent`` falls back to two more
    roots when its ``TMPDIR`` candidate is skipped -- under the ``local``
    profile this harness scans those same roots, and a foreign directory
    found there is harmless because it must still bind (I4b) before it is
    trusted."""
    primary = tmp_path / "primary-tmp"
    fallback_one = tmp_path / "fallback-one"
    fallback_two = tmp_path / "fallback-two"
    for root in (primary, fallback_one, fallback_two):
        root.mkdir()
    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(primary))
    monkeypatch.setattr(
        workspace_module, "_LOCAL_TMP_FALLBACKS", (fallback_one, fallback_two)
    )
    own = fallback_two / "satyrn-engine-own" / "worktree"
    own.mkdir(parents=True)
    _bind_only(monkeypatch, own)

    seen: dict[str, Path] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=()):
        seen["worktree"] = Path(worktree)
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=build,
        engine_arm=True,
        # default state: Isolation.LOCAL
    )
    assert seen["worktree"] == own
    assert result.line_patch_written is True
    assert out.read_text() == _BEFORE
