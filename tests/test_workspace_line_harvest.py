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
import time
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
    outer_timeout: float = 10.0,
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
        outer_timeout,
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

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
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


_DUMMY_OWN_COMMON = Path("/dummy-common-dir")


def _fake_own_common(monkeypatch: pytest.MonkeyPatch) -> None:
    """N8/N1: `_engine_worktree` resolves ``state.worktree``'s own
    git-common-dir once, itself, before consulting `_engine_worktree_bound`
    per candidate -- so a test that fakes only the latter (no real git repo
    at `state.worktree`) must also stub this one resolution, or it fails for
    an unrelated reason (not a git repo) before the faked binding logic ever
    runs."""
    monkeypatch.setattr(
        workspace_module,
        "_resolve_git_common_dir",
        lambda *_a, **_k: _DUMMY_OWN_COMMON,
    )


def _bind_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """I4b: fake every candidate as bound to this attempt (no real git)."""
    _fake_own_common(monkeypatch)
    monkeypatch.setattr(
        workspace_module,
        "_engine_worktree_bound",
        lambda _state, _candidate, _environment, **_kwargs: (True, ""),
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

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
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

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
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

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
        seen["extra_config"] = tuple(extra_config)
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path, monkeypatch, transcript_text=TOKEN_LINE + "\n", line_budget=LineBudget(100, 48), build=build,
    )
    assert seen["extra_config"] == ()
    assert result.line_patch_written is True


def test_the_line_harvest_passes_a_total_deadline_not_a_per_call_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F2: `build_cumulative_patch` makes four git calls; passing
    `LINE_HARVEST_TIMEOUT_S` as `timeout=` (applied to each of the four)
    would let the wait loop block up to 4x longer than the ceiling's name
    says. `_harvest_patch(total=True)` must instead pass a `deadline=`
    computed once, and never also pass `timeout=`."""
    seen: dict[str, object] = {}
    before = time.monotonic()

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
        seen["timeout"] = timeout
        seen["deadline"] = deadline
        return _capture(_BEFORE)

    result, out = _run(
        tmp_path, monkeypatch, transcript_text=TOKEN_LINE + "\n", line_budget=LineBudget(100, 48), build=build,
    )
    assert seen["timeout"] is None
    deadline = seen["deadline"]
    assert isinstance(deadline, float)
    assert before < deadline <= before + workspace_module.LINE_HARVEST_TIMEOUT_S + 1.0
    assert result.line_patch_written is True


def test_the_tripped_harvest_still_passes_a_per_call_timeout_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling of the test above: F2 must not touch the tripped harvest's
    existing per-call-timeout behaviour."""
    seen: dict[str, object] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
        seen["timeout"] = timeout
        seen["deadline"] = deadline
        return _capture(_BEFORE)

    monkeypatch.setattr("satyrn_evals.session_patch.build_cumulative_patch", build)
    state = _default_state(tmp_path)
    out = tmp_path / "tripped.diff"
    workspace_module._harvest_tripped(state, {}, out)
    assert seen["timeout"] == workspace_module.TRIPPED_HARVEST_TIMEOUT_S
    assert seen["deadline"] is None


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


def test_a_write_that_creates_the_file_then_fails_removes_the_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Path.write_text` can create the destination and then fail partway
    (ENOSPC/EIO): the harvest must not leave a partial `line.diff` behind,
    because attempt.py treats the file's mere presence as the interface --
    a partial file left on disk would be reported as a successful harvest
    even though `line_harvest_error` is also set (N2)."""
    state = _default_state(tmp_path)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(TOKEN_LINE + "\n")
    out = tmp_path / LINE_PATCH_NAME
    orig_write_text = Path.write_text

    def flaky_write_text(self, data, encoding=None, errors=None, newline=None):
        if self.name == LINE_PATCH_NAME:
            self.write_bytes(data.encode(encoding or "utf-8"))
            raise OSError(28, "No space left on device")
        return orig_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)
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
    assert "No space left" in result.line_harvest_error
    assert not out.exists()  # the partial file must be removed, not left behind


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
    _fake_own_common(monkeypatch)
    own_set = set(own)

    def fake(_state: object, candidate: Path, _environment: object, **_kwargs: object) -> tuple[bool, str]:
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

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
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


# --- N13: _engine_worktree_bound against real git, not stubbed ------------


def _init_repo(path: Path, environment: dict[str, str]) -> None:
    """A real, minimal git repository with one commit -- no `_git` stubbing."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "f.txt").write_text("x\n")
    workspace_module._git(path, ("init", "-q"), environment)
    workspace_module._git(path, ("add", "-A"), environment)
    commit_env = {**environment, **workspace_module._FIXED_GIT_ENV}
    workspace_module._git(path, ("commit", "-q", "-m", "seed"), commit_env)


@pytest.mark.integration
def test_a_genuinely_foreign_worktree_is_refused_while_an_own_worktree_beside_it_is_accepted(
    tmp_path: Path,
) -> None:
    """N13: `_engine_worktree_bound` is stubbed (`_bind_only`/`_bind_everything`)
    in every other test in this file. This one uses real git throughout: a
    linked worktree created by ``git worktree add`` from a DIFFERENT
    repository, placed where the glob finds it (I4a/I4b), must be refused
    and named -- not accepted just because it has the right shape and name
    -- while an own worktree, created by ``git worktree add`` from this
    attempt's own ``state.worktree``, sitting right beside it in the same
    scanned directory, is accepted.

    Marked, not default tier (the default-tier subprocess tripwire in
    conftest.py blocks any real ``git`` spawn): four real git repos/commands
    (init x2, worktree add x2, plus the resolutions inside
    `_engine_worktree_bound`/`_engine_worktree`) are well over what the
    audit-hook tripwire allows outside the ``integration`` marker."""
    environment = dict(os.environ)
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    _init_repo(state.worktree, environment)

    engine_tmp = state.parent / "tmp"
    engine_tmp.mkdir()

    # Own: git-worktree-add'd from this attempt's own worktree, so it shares
    # state.worktree's git-common-dir -- exactly how satyrn-engine creates
    # its deliver worktree (from context.root, the cwd the harness gave it).
    own = engine_tmp / "satyrn-engine-own" / "worktree"
    own.parent.mkdir(parents=True)
    workspace_module._git(state.worktree, ("worktree", "add", "--detach", os.fspath(own)), environment)

    # Foreign: a completely separate repository (its own git-common-dir),
    # git-worktree-add'd into a directory with the exact same glob shape.
    foreign_repo = tmp_path / "foreign-repo"
    _init_repo(foreign_repo, environment)
    foreign = engine_tmp / "satyrn-engine-foreign" / "worktree"
    foreign.parent.mkdir(parents=True)
    workspace_module._git(foreign_repo, ("worktree", "add", "--detach", os.fspath(foreign)), environment)

    own_common = workspace_module._resolve_git_common_dir(state.worktree, environment)
    assert own_common is not None

    # The negative case, directly: the foreign worktree is refused, named.
    ok, detail = workspace_module._engine_worktree_bound(
        state, foreign, environment, own_common=own_common
    )
    assert ok is False
    assert str(foreign) in detail
    assert "foreign" in detail

    # Sibling: the own worktree, beside it, is accepted.
    ok2, detail2 = workspace_module._engine_worktree_bound(
        state, own, environment, own_common=own_common
    )
    assert (ok2, detail2) == (True, "")

    # And end to end, through the real candidate search over both: exactly
    # the own worktree is selected -- the foreign one beside it is scanned
    # but never trusted.
    resolved, error = workspace_module._engine_worktree(state, environment)
    assert resolved == own
    assert error is None


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

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
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


# --- N1: one deadline for the whole line harvest (binding + patch) --------


class _FakeClock:
    """A controllable stand-in for `time.monotonic`."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def test_local_profile_no_candidate_message_names_the_scanned_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1: only ISOLATED has a single, cell-private TMPDIR -- the LOCAL
    profile scans three roots (ambient TMPDIR plus two fallbacks), so the
    no-candidate message must not claim "the cell TMPDIR" when nothing like
    that was searched."""
    state = _default_state(tmp_path, isolation=Isolation.LOCAL)
    # Isolate from any real satyrn-engine-* leftovers in the ambient TMPDIR
    # or the real /tmp, /var/tmp fallbacks (a live system can easily have
    # some from unrelated real runs).
    primary = tmp_path / "primary-tmp"
    fallback_one = tmp_path / "fallback-one"
    fallback_two = tmp_path / "fallback-two"
    for root in (primary, fallback_one, fallback_two):
        root.mkdir()
    monkeypatch.setattr(workspace_module.tempfile, "gettempdir", lambda: os.fspath(primary))
    monkeypatch.setattr(
        workspace_module, "_LOCAL_TMP_FALLBACKS", (fallback_one, fallback_two)
    )

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
    )
    assert result.line_harvest_error is not None
    assert "cell TMPDIR" not in result.line_harvest_error


def test_a_hanging_git_call_during_binding_is_cut_off_within_the_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1: `_resolve_git_common_dir` (used to bind the Engine arm's internal
    worktree) used to call `_git` with no timeout at all. A wedged git there
    must be cut off within the line harvest's own bound -- not hang the
    still-running cell's poll loop indefinitely -- and the failure must
    become a recorded `line_harvest_error`, never an uncaught exception."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    _make_candidates(state, "satyrn-engine-abc")
    clock = _FakeClock()
    monkeypatch.setattr(workspace_module.time, "monotonic", clock)

    def hanging_git(root, args, environment, **kwargs):
        timeout = kwargs.get("timeout")
        # A wedged git: it consumes whatever timeout it was given (or, if
        # unbounded, far more than the harvest's own ceiling) and then
        # still fails to return.
        clock.advance(timeout if timeout is not None else 999.0)
        raise subprocess.TimeoutExpired(cmd="git", timeout=timeout or 0.0)

    monkeypatch.setattr(workspace_module, "_git", hanging_git)

    result, _out = _run(
        tmp_path,
        monkeypatch,
        transcript_text=TOKEN_LINE + "\n",
        line_budget=LineBudget(100, 48),
        build=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not reach the build")),
        engine_arm=True,
        state=state,
        # Large outer timeout: the fake clock advances far more than a real
        # 10s command timeout would tolerate, and this test is about the
        # line harvest's OWN bound, not the command's.
        outer_timeout=10_000.0,
    )
    assert result.line_crossed is not None
    assert result.line_patch_written is False
    assert result.line_harvest_error is not None
    # Bound as a WHOLE: binding alone must not be allowed to burn more than
    # the harvest's own ceiling, let alone leave it uncut.
    assert clock.t <= workspace_module.LINE_HARVEST_TIMEOUT_S + 1.0


def test_remaining_time_shrinks_across_binding_and_patch_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N1: binding and the patch build share ONE deadline instant for the
    whole line harvest -- time binding spends must come out of what the
    patch build gets, not be forgotten and re-granted a fresh full budget."""
    state = _default_state(tmp_path, isolation=Isolation.ISOLATED)
    (candidate,) = _make_candidates(state, "satyrn-engine-abc")
    clock = _FakeClock()
    monkeypatch.setattr(workspace_module.time, "monotonic", clock)

    def slow_git(root, args, environment, **kwargs):
        clock.advance(5.0)  # each binding git call "takes" 5 seconds
        return subprocess.CompletedProcess(
            args=["git", *args], returncode=0, stdout=b"/common\n", stderr=b""
        )

    monkeypatch.setattr(workspace_module, "_git", slow_git)

    seen: dict[str, object] = {}

    def build(worktree, base, env, *, exclude=(), timeout=None, extra_config=(), deadline=None):
        seen["deadline"] = deadline
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
        outer_timeout=10_000.0,
    )
    assert result.line_patch_written is True
    assert seen["worktree"] == candidate
    # Binding made two git calls (own-common, candidate-common) before the
    # patch build ever ran, so the clock has already moved by the time the
    # deadline is consulted -- yet the deadline INSTANT passed to the patch
    # build is unchanged from the one computed at the very start of the
    # harvest (clock was 0 then), proving it is the same shared deadline,
    # not a fresh one recomputed after binding.
    assert clock.t == 10.0
    assert seen["deadline"] == workspace_module.LINE_HARVEST_TIMEOUT_S
