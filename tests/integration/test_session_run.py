"""The session executor against the deterministic fake adapter."""

import sys
from pathlib import Path

import pytest

from satyrn_evals.errors import UsageError
from satyrn_evals.session import run_session
from satyrn_evals.session_record import SessionCode, load_session_record

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
