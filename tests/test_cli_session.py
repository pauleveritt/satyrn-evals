"""The session CLI branch: exit-code mapping, usage refusal, wiring."""

import shutil
from pathlib import Path

import pytest

from satyrn_evals import cli, session
from satyrn_evals.session_manifest import DEFAULT_SESSION_SPEC
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


def test_cli_and_run_session_defaults_agree_with_the_constant() -> None:
    """The default filename must live in one place.

    ``--session-spec``'s argparse default and ``run_session``'s parameter
    default both have to equal ``DEFAULT_SESSION_SPEC``; editing one site
    without the others would silently break default-path invariance, which
    is what the selector's backward compatibility rests on.
    """
    parsed = cli.parser.parse_args(["session", "mini-session"])
    assert parsed.session_spec == DEFAULT_SESSION_SPEC

    run_session_default = session.run_session.__kwdefaults__["session_spec"]
    assert run_session_default == DEFAULT_SESSION_SPEC


def test_session_spec_escape_refuses_with_exit_two_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malicious --session-spec is refused by the real dispatch path.

    Exercises cli.main -> run_session -> load_session_spec with no
    monkeypatching of the guard itself: ``_check_spec_name`` fires before
    any workspace is prepared or adapter spawned, so this never touches a
    subprocess (the tripwire in conftest.py would fail the build if it
    did).

    The escape target is a real, readable, well-formed session spec
    (mirroring test_session_manifest.py's
    ``test_session_spec_name_traversal_cannot_read_outside_task_dir``) so
    that the refusal is not an incidental "file not found": absent the
    guard, ``../escape.json`` would resolve and load successfully. Exit
    code 2 alone is not proof the guard fired -- an OSError from a missing
    file also maps to exit 2 -- so this asserts the guard's own "traverse"
    message text, and stops the run (via a monkeypatched ``load_overlay``)
    immediately after a successful load would prove the opposite. See the
    discrimination check in the task report: with ``_check_spec_name``'s
    call disabled, this test fails because the escape file *does* load and
    the stderr message no longer says "traverse".
    """
    task_dir = tmp_path / "mini-session"
    shutil.copytree(TASKS_ROOT / "mini-session", task_dir)
    escape_target = tmp_path / "escape.json"
    escape_target.write_text((TASKS_ROOT / "mini-session" / "session.json").read_text())

    def fake_load_overlay(*args: object, **kwargs: object) -> None:
        raise session.UsageError("MARKER_REACHED_PAST_SPEC_LOAD")

    monkeypatch.setattr(session, "load_overlay", fake_load_overlay)

    exit_code = cli.main(
        [
            "session",
            "mini-session",
            "--tasks-root",
            str(tmp_path),
            "--output",
            str(tmp_path / "out"),
            "--session-spec",
            "../escape.json",
            "--",
            "adapter",
        ]
    )
    stderr = capsys.readouterr().err
    assert exit_code == 2
    assert "traverse" in stderr
    assert "MARKER_REACHED_PAST_SPEC_LOAD" not in stderr


def test_session_spec_named_file_reaches_the_loader_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid non-default --session-spec name reaches the real loader.

    Sibling of the refusal test above: this drives the same real
    cli.main -> run_session -> load_session_spec path with a well-formed
    ``custom.json``, and proves the spec actually loaded (not merely that
    the filename passed validation) by monkeypatching ``load_overlay`` --
    the call immediately after ``load_session_spec`` in run_session, and
    still well before any workspace/subprocess work -- to raise a marker
    that only fires once the spec is in hand.
    """
    task_copy = tmp_path / "mini-session"
    shutil.copytree(TASKS_ROOT / "mini-session", task_copy)
    (task_copy / "session.json").rename(task_copy / "custom.json")

    marker = "OVERLAY_REACHED_AFTER_SPEC_LOAD"

    def fake_load_overlay(*args: object, **kwargs: object) -> None:
        raise session.UsageError(marker)

    monkeypatch.setattr(session, "load_overlay", fake_load_overlay)

    out_dir = tmp_path / "out"
    exit_code = cli.main(
        [
            "session",
            "mini-session",
            "--tasks-root",
            str(tmp_path),
            "--output",
            str(out_dir),
            "--session-spec",
            "custom.json",
            "--",
            "adapter",
        ]
    )
    assert exit_code == 2
