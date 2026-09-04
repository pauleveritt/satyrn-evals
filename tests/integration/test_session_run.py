"""The session executor against the deterministic fake adapter."""

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from satyrn_evals import session as session_module
from satyrn_evals.adapter_process import AdapterCleanupError  # noqa: F401
from satyrn_evals.errors import SessionSpecError, UsageError
from satyrn_evals.session import run_session
from satyrn_evals.session_record import SessionCode, SessionRecord, load_session_record
from satyrn_evals.workspace import WorkspaceReleaseError

pytestmark = pytest.mark.integration

DATA = Path(__file__).resolve().parent / "data"
FAKE = Path(__file__).resolve().parent / "fake_session_adapter.py"


def _argv(scenario: str, marker: Path | None = None) -> list[str]:
    argv = [sys.executable, str(FAKE), scenario]
    if marker is not None:
        argv += ["--marker", str(marker)]
    return argv


def _run(tmp_path: Path, scenario: str, marker: Path | None = None, **kw: float):
    return run_session(
        task="mini-session",
        tasks_root=DATA,
        output=tmp_path,
        adapter_command=_argv(scenario, marker),
        **kw,
    )


@pytest.fixture()
def fake_clean_session(tmp_path: Path) -> SessionRecord:
    return _run(tmp_path, "clean")


@pytest.fixture()
def fake_leaky_session(tmp_path: Path) -> SessionRecord:
    """Clean mechanics except step 1 leaks grader overlay content into a
    retained source file, so the patch detector must flag it while the
    session still captures every checkpoint."""
    return _run(tmp_path, "leaky")


def test_hidden_session_annotates_checkpoints(fake_clean_session: SessionRecord) -> None:
    record = fake_clean_session  # run_session driven by the existing fake adapter
    for step in record.steps:
        if step.patch_path is None:
            continue
        assert step.contamination is not None
        checks = {c["check"]: c["outcome"] for c in step.contamination["checks"]}
        assert set(checks) == {"grader_content_in_patch", "grader_name_in_payload"}


def test_contaminating_step_flags_and_session_still_captures(
    fake_leaky_session: SessionRecord,
) -> None:
    record = fake_leaky_session
    flagged = [s for s in record.steps if s.contamination and any(
        c["outcome"] == "flagged" for c in s.contamination["checks"]
    )]
    assert flagged, "the leaky step must flag"
    assert record.steps  # capture completed; detection never stops the session


def _hidden_session_task(tmp_path: Path, *, prompt: str) -> Path:
    """Minimal hidden session task for the assert_no_overlay_names wiring.
    Only the loader phases run (the refusal fires before any workspace
    build), so no base content or git repository is needed."""
    task = tmp_path / "named-overlay-task"
    (task / "base").mkdir(parents=True)
    (task / "grader" / "overlay" / "tests").mkdir(parents=True)
    (task / "grader" / "overlay" / "tests" / "t_hidden.py").write_text(
        "def test_x():\n    assert True\n"
    )
    (task / "fixtures").mkdir()
    (task / "fixtures" / "kg.patch").write_text("")
    (task / "manifest.json").write_text(
        json.dumps(
            {
                "name": "named-overlay-task",
                "contract": "do the thing without naming the grader",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["tests/t_hidden.py::test_x"],
                "source_paths": ["src"],
                "fixtures": {"known_good": "fixtures/kg.patch"},
                "grader_overlay": "grader/overlay",
                "oracle_visibility": "hidden",
            }
        )
    )
    (task / "session.json").write_text(
        json.dumps(
            {
                "version": 1,
                "steps": [
                    {
                        "id": "step-0",
                        "kind": "feature",
                        "prompt": prompt,
                        "new_feature_selectors": ["tests/t_hidden.py::test_x"],
                    },
                    {
                        "id": "step-1",
                        "kind": "review",
                        "prompt": "Review and run the public suite.",
                        "new_feature_selectors": [],
                    },
                ],
                "base_preservation_selectors": ["tests/t_hidden.py::test_base"],
            }
        )
    )
    return task


def test_run_refuses_before_any_workspace_when_prompt_names_overlay(
    tmp_path: Path,
) -> None:
    task_dir = _hidden_session_task(
        tmp_path,
        prompt="Wire grader/overlay/tests/t_hidden.py into the build.",
    )
    with pytest.raises(SessionSpecError, match="names grader-only path"):
        run_session(
            task=task_dir.name,
            tasks_root=tmp_path,
            output=tmp_path / "out",
            adapter_command=[sys.executable, str(FAKE), "clean"],
        )
    assert not (tmp_path / "out").exists()  # refused before any artifact was built


def test_run_accepts_clean_session_through_the_same_wiring(
    fake_clean_session: SessionRecord,
) -> None:
    """The clean session-mechanics style prompt passes assert_no_overlay_names:
    the wiring's success sibling to the refusal above."""
    assert fake_clean_session.code is SessionCode.COMPLETE
    assert all(s.outcome == "settled" for s in fake_clean_session.steps)


def test_clean_session_captures_three_checkpoints(tmp_path: Path) -> None:
    record = _run(tmp_path, "clean")
    assert record.code is SessionCode.COMPLETE
    assert record.conversation_id == "fake-conv"
    assert [s.step_id for s in record.steps] == ["add-a", "add-b", "review"]
    assert all(s.outcome == "settled" for s in record.steps)
    assert len({s.prompt_digest for s in record.steps}) == 3
    assert all(s.patch_digest and s.patch_bytes for s in record.steps)
    # review edits nothing: its cumulative patch repeats add-b's
    assert record.steps[2].patch_digest == record.steps[1].patch_digest
    assert record.steps[0].tool_count >= 1 and record.steps[0].turn_count >= 1
    assert all(not s.scope_violations for s in record.steps)
    session_dir = _session_dir(tmp_path)
    loaded = load_session_record(session_dir / "session-record.json")
    assert loaded == record


def _session_dir(tmp_path: Path) -> Path:
    dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(dirs) == 1
    return dirs[0]


def test_scope_violation_continues_and_marks(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    record = _run(tmp_path, "scope", marker)
    assert record.code is SessionCode.SCOPE_VIOLATION
    assert record.steps[0].scope_violations == ()
    assert "outside.txt" in record.steps[1].scope_violations
    # the stop list does not include scope violations: review still ran
    assert marker.exists()
    assert record.steps[2].outcome == "settled"


def test_wrong_identity_is_protocol_error(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    record = _run(tmp_path, "wrong-id", marker)
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"
    assert record.steps[0].outcome == "settled"
    assert record.steps[1].outcome == ""  # terminal refused; tree still captured
    assert not marker.exists()  # no prompt after the protocol failure


def test_output_limit_captures_and_stops(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    record = _run(tmp_path, "output-limit", marker)
    assert record.code is SessionCode.OUTPUT_LIMIT
    assert [s.step_id for s in record.steps] == ["add-a", "add-b"]
    assert record.steps[1].outcome == "output-limit"
    assert not marker.exists()


def test_hang_times_out_captures_after_reap(tmp_path: Path) -> None:
    record = _run(tmp_path, "hang", step_timeout=1.0)
    assert record.code is SessionCode.STEP_TIMEOUT
    assert [s.step_id for s in record.steps] == ["add-a", "add-b"]
    assert record.steps[1].outcome == ""
    assert record.steps[1].patch_digest  # captured after the reap


def test_missing_adapter_is_a_start_refusal(tmp_path: Path) -> None:
    with pytest.raises(UsageError, match="adapter cannot start"):
        run_session(
            task="mini-session",
            tasks_root=DATA,
            output=tmp_path,
            adapter_command=[str(tmp_path / "no-such-adapter")],
        )
    assert list(tmp_path.iterdir()) == []  # usage writes nothing


def test_event_identity_change_is_protocol_error(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    record = _run(tmp_path, "wrong-id-event", marker)
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"
    assert record.steps[0].outcome == "settled"  # step 1 was clean
    assert not marker.exists()  # no prompt after the identity failure


def test_terminal_identity_change_is_protocol_error(tmp_path: Path) -> None:
    """Events carry true identity; the terminal drifts: caught at the terminal."""
    marker = tmp_path / "marker"
    record = _run(tmp_path, "wrong-id", marker)
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"
    assert not marker.exists()


def test_broken_channel_after_start_still_leaves_a_record(
    tmp_path: Path,
) -> None:
    """A started session always leaves a record (review finding 4): the
    adapter exits after step 1; the prompt-2 send fails; the record is
    written with the captured checkpoint and the workspace is released."""
    record = _run(tmp_path, "die-after-one")
    assert record.code is SessionCode.ADAPTER_ERROR
    assert [s.step_id for s in record.steps] == ["add-a"]
    assert record.steps[0].outcome == "settled"
    session_dir = _session_dir(tmp_path)
    assert (session_dir / "session-record.json").is_file()
    assert (session_dir / "checkpoints" / "01-add-a.patch").is_file()


def test_release_failure_becomes_cleanup_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals import session as session_module

    _run(tmp_path, "clean")  # proves the healthy path before the fault
    session_dir = _session_dir(tmp_path)

    def failing_release(workspace: object) -> None:
        raise WorkspaceReleaseError(
            "cleanup unconfirmed", retained_path=str(workspace.parent)
        )

    monkeypatch.setattr(session_module, "release_session_workspace", failing_release)
    regressed = session_module.run_session(
        task="mini-session",
        tasks_root=DATA,
        output=tmp_path / "second",
        adapter_command=[sys.executable, str(FAKE), "clean"],
    )
    assert regressed.code is SessionCode.CLEANUP_FAILED
    assert "retained at" in (regressed.message or "")
    assert [s.step_id for s in regressed.steps] == ["add-a", "add-b", "review"]
    assert session_dir != tmp_path / "second"  # the first record is untouched


def test_record_carries_artifact_digests_and_provenance(tmp_path: Path) -> None:
    """Artifact digests are recorded and recomputable from the files;
    provenance comes from the manifest (review finding 5)."""

    record = _run(tmp_path, "clean")
    session_dir = _session_dir(tmp_path)
    for step in record.steps:
        assert step.snapshot_digest == __import__("hashlib").sha256(
            (session_dir / step.snapshot_path).read_bytes()
        ).hexdigest()
        prefix = (session_dir / step.transcript_prefix_path).read_bytes()[
            : step.transcript_prefix_bytes
        ]
        assert step.transcript_prefix_digest == __import__("hashlib").sha256(
            prefix
        ).hexdigest()
    assert record.provenance == {
        "repo": "bundled synthetic fixture",
        "base_sha": "unrecorded",
        "fix_sha": "unrecorded",
    }


def test_eof_mid_step_is_adapter_error(tmp_path: Path) -> None:
    """EOF during a step: the checkpoint is captured after the reap."""
    record = _run(tmp_path, "die-mid-read")
    assert record.code is SessionCode.ADAPTER_ERROR
    assert record.steps[0].outcome == ""
    assert record.steps[0].patch_digest


def test_garbage_line_is_protocol_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "garbage")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"


def test_event_for_wrong_step_is_protocol_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "event-wrong-step")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"


def test_terminal_for_wrong_step_is_protocol_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "wrong-step-terminal")
    assert record.code is SessionCode.PROTOCOL_ERROR


def test_adapter_close_line_mid_step_is_protocol_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "chaos-close-line")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"


def test_workspace_prepare_failure_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals import session as session_module
    from satyrn_evals.workspace import WorkspacePrepareError

    def failing_prepare(**kwargs: object):
        raise WorkspacePrepareError("git refused the worktree")

    monkeypatch.setattr(session_module, "prepare_session_workspace", failing_prepare)
    record = session_module.run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "clean"],
    )
    assert record.code is SessionCode.WORKSPACE_FAILED
    session_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    loaded = load_session_record(session_dir / "session-record.json")
    assert loaded.code is SessionCode.WORKSPACE_FAILED


def test_unconverted_drive_failure_still_leaves_a_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals import session as session_module
    from satyrn_evals.errors import SatyrnError

    def broken_drive(**kwargs: object):
        raise SatyrnError("defensive arm exercised")

    monkeypatch.setattr(session_module, "_drive", lambda **kwargs: (_ for _ in ()).throw(SatyrnError("defensive arm exercised")))
    record = session_module.run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "clean"],
    )
    assert record.code is SessionCode.ADAPTER_ERROR
    assert "defensive" in (record.message or "")
    session_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    assert (session_dir / "session-record.json").is_file()


def test_adapter_exit_before_banner_is_adapter_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "no-banner")
    assert record.code is SessionCode.ADAPTER_ERROR
    assert record.terminal_step is None
    assert record.steps == ()


def test_non_banner_first_line_is_protocol_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "bad-banner")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step is None


def test_close_timeout_is_adapter_error(tmp_path: Path) -> None:
    record = run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "close-hang"],
        close_timeout=0.5,
    )
    assert record.code is SessionCode.ADAPTER_ERROR
    assert "close timed out" in (record.message or "")


def test_nonzero_close_exit_is_adapter_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "close-fail")
    assert record.code is SessionCode.ADAPTER_ERROR
    assert "exited 3" in (record.message or "")


def test_output_after_close_is_adapter_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "close-extra")
    assert record.code is SessionCode.ADAPTER_ERROR
    assert "output after close" in (record.message or "")


def test_step_timeout_during_step(tmp_path: Path) -> None:
    record = run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "hang"],
        step_timeout=0.5,
    )
    assert record.code is SessionCode.STEP_TIMEOUT
    assert record.steps[-1].outcome == ""


def test_protocol_fault_at_the_terminal_is_stop(tmp_path: Path) -> None:

    record = _run(tmp_path, "wrong-step-terminal")
    assert record.code is SessionCode.PROTOCOL_ERROR
    # the terminal-for-wrong-step scenario leaves the fake sleeping: the
    # executor must have reaped it to produce a record at all
    session_dir = _session_dir(tmp_path)
    assert (session_dir / "session-record.json").is_file()


def test_cleanup_error_in_the_stop_path_is_cleanup_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    def failing_reap(self: object, timeout: float) -> None:
        raise AdapterCleanupError("group did not reap")

    monkeypatch.setattr(session_module.AdapterProcess, "terminate_and_reap", failing_reap)
    regressed = session_module.run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path / "second",
        adapter_command=[sys.executable, str(FAKE), "clean"],
    )
    assert regressed.code is SessionCode.CLEANUP_FAILED
    assert "group did not reap" in (regressed.message or "")
    assert regressed.steps  # captured checkpoints retained


def test_garbage_after_close_is_protocol_error(tmp_path: Path) -> None:
    record = run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "close-garbage"],
        close_timeout=5.0,
    )
    assert record.code is SessionCode.PROTOCOL_ERROR


def test_release_failure_with_no_record_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-SatyrnError escape from _drive (a bug) whose release also
    fails: the release error propagates with the retained path."""

    def broken_drive(**kwargs: object):
        raise RuntimeError("a bug, not a session fault")

    def failing_release(workspace: object) -> None:
        raise WorkspaceReleaseError("cleanup unconfirmed", retained_path="/tmp/x")

    monkeypatch.setattr(session_module, "_drive", broken_drive)
    monkeypatch.setattr(session_module, "release_session_workspace", failing_release)
    with pytest.raises(WorkspaceReleaseError):
        session_module.run_session(
            task="mini-session", tasks_root=DATA, output=tmp_path,
            adapter_command=[sys.executable, str(FAKE), "clean"],
        )


def test_checkpoint_without_transcript_prefix_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A checkpoint captured before any transcript byte exists: the digest
    is None and the record still completes (the 123->127 false arm)."""
    from pathlib import Path as _Path

    from satyrn_evals.session import _capture_checkpoint
    from satyrn_evals.workspace import (
        prepare_session_workspace,
        release_session_workspace,
    )

    task_dir = (_Path("tests/integration/data") / "mini-session").resolve()
    workspace = prepare_session_workspace(
        base=task_dir / "base", protected_paths=(tmp_path,)
    )
    try:
        spec_step = SimpleNamespace(id="add-a")
        record = _capture_checkpoint(
            workspace, tmp_path, spec_step, tmp_path / "no-such-transcript.jsonl",
            1, "settled", "p1", 0, 0, 0, ("solution.py",),
        )
        assert record.transcript_prefix_digest is None
        assert record.transcript_prefix_bytes is None
        assert record.patch_digest is not None
    finally:
        release_session_workspace(workspace)


def test_garbage_banner_is_protocol_error(tmp_path: Path) -> None:
    record = _run(tmp_path, "garbage-banner")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step is None


def test_close_stdin_oserror_is_suppressed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals.adapter_process import AdapterProcess

    def raising_close(self: object) -> None:
        raise OSError("descriptor already gone")

    monkeypatch.setattr(AdapterProcess, "close_stdin", raising_close)
    record = _run(tmp_path, "clean")
    assert record.code is SessionCode.COMPLETE


def test_context_reset_is_a_protocol_error(tmp_path: Path) -> None:
    """design:230 — a context reset stops the sequence as PROTOCOL_ERROR;
    the reset line is preserved in the transcript and the terminal
    checkpoint is captured (the failure-path sibling of context_compacted,
    which counts and continues)."""
    record = _run(tmp_path, "context-reset")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"
    # the step that was in flight still yields its checkpoint
    assert [s.step_id for s in record.steps] == ["add-a", "add-b"]
    assert record.steps[1].patch_digest is not None
    # the reset event is spooled before parsing (evidence retained)
    session_dir = _session_dir(tmp_path)
    transcript = (session_dir / "transcript.jsonl").read_text()
    assert '"context_reset"' in transcript


def test_chatty_adapter_is_bounded_by_the_prompt_deadline(
    tmp_path: Path,
) -> None:
    """Blocker 1: step_timeout bounds the WHOLE prompt, not each idle
    wait. A chatty adapter that keeps emitting events must still be cut
    off at the deadline instead of running indefinitely."""
    started = time.monotonic()
    record = run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "chatty"],
        step_timeout=1.0,
    )
    elapsed = time.monotonic() - started
    assert record.code is SessionCode.STEP_TIMEOUT
    assert elapsed < 5.0  # bounded by the 1s budget, not the chatter
    assert record.terminal_step == "add-a"


def test_each_checkpoint_durably_links_its_record_before_the_next_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Blocker 3: the running record is atomically replaced at every
    checkpoint, so a crash during a later prompt loses no earlier step
    records. The writer is called once per checkpoint with the steps so
    far, before the final write."""
    from satyrn_evals.session_record import write_session_record as real_write

    calls: list[int] = []

    def recording_write(path: Path, record: object) -> None:
        calls.append(len(record.steps))  # type: ignore[attr-defined]
        real_write(path, record)  # type: ignore[arg-type]

    monkeypatch.setattr(session_module, "write_session_record", recording_write)
    record = run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "clean"],
    )
    assert record.code is SessionCode.COMPLETE
    # 3 per-checkpoint provisional writes (1,2,3 steps) + the final write
    assert calls == [1, 2, 3, 3]


def test_invalid_utf8_adapter_output_still_leaves_a_durable_record(
    tmp_path: Path,
) -> None:
    """Invalid-UTF8 adapter output must not bypass the started-session
    durable-record guarantee: the line is spooled byte-verbatim, the
    sequence stops as a protocol failure, and the record is written."""
    record = _run(tmp_path, "garbage-bytes")
    assert record.code is SessionCode.PROTOCOL_ERROR
    assert record.terminal_step == "add-b"
    session_dir = _session_dir(tmp_path)
    transcript = (session_dir / "transcript.jsonl").read_bytes()
    assert b"\xff\xfe" in transcript  # bytes preserved verbatim
    loaded = load_session_record(session_dir / "session-record.json")
    assert loaded.code is SessionCode.PROTOCOL_ERROR


def _provisional_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str, **kw: float
) -> tuple[list[SessionCode], SessionCode]:
    """Record the code on every write_session_record call (the durable
    per-checkpoint and final writes) and return (codes, final code)."""
    from satyrn_evals.session_record import write_session_record as real_write

    codes: list[SessionCode] = []

    def recording_write(path: Path, record: SessionRecord) -> None:
        codes.append(record.code)
        real_write(path, record)

    monkeypatch.setattr(session_module, "write_session_record", recording_write)
    record = run_session(
        task="mini-session", tasks_root=DATA, output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), scenario],
        **kw,
    )
    return codes, record.code


def test_intermediate_record_code_matches_a_step_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash immediately after the timeout checkpoint must leave the
    durable record at STEP_TIMEOUT, not COMPLETE (maintainer blocker)."""
    codes, final = _provisional_codes(
        tmp_path, monkeypatch, "hang", step_timeout=0.6
    )
    assert final is SessionCode.STEP_TIMEOUT
    assert codes[-2] is SessionCode.STEP_TIMEOUT  # last per-checkpoint write
    assert codes[0] is SessionCode.COMPLETE       # add-a settled earlier


def test_intermediate_record_code_matches_a_protocol_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codes, final = _provisional_codes(tmp_path, monkeypatch, "wrong-id")
    assert final is SessionCode.PROTOCOL_ERROR
    assert codes[-2] is SessionCode.PROTOCOL_ERROR


def test_intermediate_record_code_matches_a_non_settled_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codes, final = _provisional_codes(tmp_path, monkeypatch, "output-limit")
    assert final is SessionCode.OUTPUT_LIMIT
    assert codes[-2] is SessionCode.OUTPUT_LIMIT
