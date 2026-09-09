"""The session CLI branch: exit-code mapping, usage refusal, wiring."""

from pathlib import Path

import pytest

from satyrn_evals import cli
from satyrn_evals.session_record import SessionCode, SessionRecord, StepRecord

TASKS_ROOT = Path(__file__).resolve().parent / "integration" / "data"


def _record(code: SessionCode) -> SessionRecord:
    steps = (StepRecord("add-a", "p1", "settled"),) if code is not SessionCode.WORKSPACE_FAILED else ()
    return SessionRecord(
        version=1,
        task="mini-session",
        adapter_command=("adapter",),
        base_commit="b" * 40,
        code=code,
        steps=steps,
    )


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (SessionCode.COMPLETE, 0),
        (SessionCode.STEP_TIMEOUT, 0),
        (SessionCode.OUTPUT_LIMIT, 0),
        (SessionCode.ADAPTER_ERROR, 0),
        (SessionCode.PROTOCOL_ERROR, 0),
        (SessionCode.SCOPE_VIOLATION, 0),
        (SessionCode.GRADE_UNAVAILABLE, 3),
        (SessionCode.WORKSPACE_FAILED, 3),
        (SessionCode.CLEANUP_FAILED, 3),
    ],
)
def test_session_exit_code_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: SessionCode, expected: int
) -> None:
    seen: dict[str, object] = {}

    def fake_run_session(**kwargs: object) -> SessionRecord:
        seen.update(kwargs)
        return _record(code)

    monkeypatch.setattr(cli, "run_session", fake_run_session)
    assert (
        cli.main(
            [
                "session",
                "mini-session",
                "--tasks-root",
                str(TASKS_ROOT),
                "--output",
                str(tmp_path),
                "--",
                "adapter",
            ]
        )
        == expected
    )
    assert seen["task"] == "mini-session"
    assert seen["adapter_command"] == ["adapter"]
    assert seen["grader"] is not None
    assert seen["session_spec"] == "session.json"


def test_session_spec_flag_threads_to_run_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--session-spec is not the default: it reaches run_session verbatim."""
    seen: dict[str, object] = {}

    def fake_run_session(**kwargs: object) -> SessionRecord:
        seen.update(kwargs)
        return _record(SessionCode.COMPLETE)

    monkeypatch.setattr(cli, "run_session", fake_run_session)
    assert (
        cli.main(
            [
                "session",
                "mini-session",
                "--tasks-root",
                str(TASKS_ROOT),
                "--output",
                str(tmp_path),
                "--session-spec",
                "other.json",
                "--",
                "adapter",
            ]
        )
        == 0
    )
    assert seen["session_spec"] == "other.json"


def test_session_without_adapter_refuses_with_exit_two(tmp_path: Path) -> None:
    def fail(**kwargs: object) -> SessionRecord:
        raise AssertionError("run_session must not be called")

    original = cli.run_session
    cli.run_session = fail  # type: ignore[method-assign]
    try:
        assert (
            cli.main(
                [
                    "session",
                    "mini-session",
                    "--tasks-root",
                    str(TASKS_ROOT),
                    "--output",
                    str(tmp_path),
                ]
            )
            == 2
        )
    finally:
        cli.run_session = original  # type: ignore[method-assign]
    assert list(tmp_path.iterdir()) == []
