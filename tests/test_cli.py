import argparse
from pathlib import Path

import pytest

from satyrn_evals import cli as cli_module
from satyrn_evals.cli import (
    main,
    parser,
    positive_finite_timeout,
    positive_int,
    split_attempt_argv,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.summary import SUMMARY_NAME
from satyrn_evals.workspace import DEFAULT_TIMEOUT


def test_unknown_task_is_usage_error() -> None:
    assert main(["grade", "no_such_task", "whatever.patch"]) == 2


def test_grade_requires_arguments() -> None:
    with pytest.raises(SystemExit):
        main(["grade"])


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_capture_requires_revert() -> None:
    with pytest.raises(SystemExit):
        main(["capture"])


def test_grade_tasks_root_unknown_task_is_usage(tmp_path) -> None:
    assert (
        main(["grade", "--tasks-root", str(tmp_path), "no_such_task", "x.patch"]) == 2
    )


def test_attempt_split_keeps_flags_and_command() -> None:
    flags, command = split_attempt_argv(
        ["t", "--tasks-root", "R", "--", "cmd", "--flag", "x"]
    )
    assert flags == ["t", "--tasks-root", "R"]
    assert command == ["cmd", "--flag", "x"]


def test_attempt_split_without_dashdash_has_no_command() -> None:
    flags, command = split_attempt_argv(["t", "--tasks-root", "R"])
    assert flags == ["t", "--tasks-root", "R"]
    assert command == []


def test_attempt_missing_command_is_usage() -> None:
    assert main(["attempt", "t"]) == 2


def test_attempt_unknown_task_is_usage(tmp_path) -> None:
    assert (
        main(
            [
                "attempt",
                "--tasks-root",
                str(tmp_path),
                "no_such_task",
                "--",
                "echo",
                "hi",
            ]
        )
        == 2
    )


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "not-a-number"])
def test_attempt_timeout_rejects_nonpositive_nonfinite_and_malformed(
    value: str,
) -> None:
    with pytest.raises(Exception, match="finite number greater than zero"):
        positive_finite_timeout(value)


def test_attempt_timeout_accepts_positive_finite() -> None:
    assert positive_finite_timeout("0.25") == 0.25


def test_attempt_timeout_default_tracks_workspace_default() -> None:
    args = parser.parse_args(["attempt", "task"])
    assert args.timeout == DEFAULT_TIMEOUT


def test_attempt_whole_timeout_defaults_off_and_accepts_positive_value() -> None:
    assert parser.parse_args(["attempt", "task"]).attempt_timeout is None
    assert (
        parser.parse_args(
            ["attempt", "task", "--attempt-timeout", "12"]
        ).attempt_timeout
        == 12.0
    )


def test_run_whole_timeout_is_dispatched(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    assert (
        main(
            ["run", "format_number", "--n", "1", "--attempt-timeout", "12", "--", "cmd"]
        )
        == 0
    )
    assert seen["attempt_timeout"] == 12.0


def test_run_requires_command() -> None:
    assert main(["run", "format_number"]) == 2


def test_run_requires_explicit_planned_denominator() -> None:
    with pytest.raises(SystemExit):
        main(["run", "format_number", "--", "cmd"])


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_run_n_rejects_non_positive_and_malformed(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="integer greater than zero"):
        positive_int(value)


@pytest.mark.parametrize("n", [1, 2])
def test_run_cli_dispatches_an_explicit_planned_denominator(
    n: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kw: seen.update(kw))
    assert cli_module.main(["run", "format_number", "--n", str(n), "--", "cmd"]) == 0
    assert seen["n"] == n and seen["task"] == "format_number"


def test_run_cli_rejects_nonpositive_n() -> None:
    with pytest.raises(SystemExit):
        cli_module.main(["run", "format_number", "--n", "0", "--", "cmd"])


def test_attempt_grade_failed_exits_3_and_prints_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from satyrn_evals.attempt_record import (
        AttemptCode,
        AttemptOutcome,
        AttemptRecord,
    )

    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.GRADE_FAILED,
        message="attempt preserved and admitted; grading did not complete: boom",
        task="t",
        command=("fake",),
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=None,
        receipt_path=None,
        timeout=900.0,
        workspace_base_sha="c" * 40,
        attempt_dir="t-1",
    )
    monkeypatch.setattr(cli_module, "attempt", lambda **kw: record)
    assert cli_module.main(["attempt", "t", "--", "cmd"]) == 3
    assert "boom" in capsys.readouterr().err


def test_attempt_cli_reports_a_retained_graded_workspace(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from satyrn_evals.attempt_record import (
        AttemptCode,
        AttemptOutcome,
        AttemptRecord,
    )
    from satyrn_evals.verdict import Verdict

    record = AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.OK,
        message="attempt recorded and graded; workspace cleanup was unsafe",
        task="t",
        command=("fake",),
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=Verdict.PASS,
        receipt_path="receipt.json",
        timeout=900.0,
        workspace_base_sha="c" * 40,
        retained_path="/tmp/retained",
        attempt_dir="t-1",
    )
    monkeypatch.setattr(cli_module, "attempt", lambda **kw: record)
    assert cli_module.main(["attempt", "t", "--", "cmd"]) == 3
    assert "workspace retained at /tmp/retained" in capsys.readouterr().err


# --- P4b Task 2: summarize/regrade CLI dispatch and exit codes ---


def test_summarize_cli_writes_summary(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        cli_module,
        "summarize_output",
        lambda output, **kw: seen.update(output=str(output), **kw),
    )
    assert cli_module.main(["summarize", str(tmp_path)]) == 0
    assert seen["output"] == str(tmp_path)


def test_summarize_cli_usage_error_exits_2(tmp_path: Path, monkeypatch) -> None:
    def refuse(output, **kw):
        raise UsageError(f"no {SUMMARY_NAME} under {output}")

    monkeypatch.setattr(cli_module, "summarize_output", refuse)
    assert cli_module.main(["summarize", str(tmp_path)]) == 2


def test_regrade_cli_dispatches(
    tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(
        cli_module,
        "regrade_attempt",
        lambda attempt_dir, **kw: (
            seen.update(attempt_dir=str(attempt_dir), **kw) or object()
        ),  # non-None: graded leg, no no-op note
    )
    assert cli_module.main(["regrade", str(tmp_path)]) == 0
    assert seen["attempt_dir"] == str(tmp_path)
    assert capsys.readouterr().err == ""


def test_regrade_cli_noop_exits_0_with_note(
    tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "regrade_attempt", lambda attempt_dir, **kw: None)
    assert cli_module.main(["regrade", str(tmp_path)]) == 0
    assert "nothing" in capsys.readouterr().err


def test_regrade_cli_usage_error_exits_2(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "regrade_attempt",
        lambda attempt_dir, **kw: (_ for _ in ()).throw(
            UsageError("no attempt record")
        ),
    )
    assert cli_module.main(["regrade", str(tmp_path)]) == 2


def test_regrade_cli_operational_error_exits_3(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "regrade_attempt",
        lambda attempt_dir, **kw: (_ for _ in ()).throw(
            SatyrnError("regrade: verdict unavailable")
        ),
    )
    assert cli_module.main(["regrade", str(tmp_path)]) == 3


# --- V11a Task 4: --rung on the attempt and run subparsers ---


def test_attempt_rung_defaults_to_none() -> None:
    """Sibling success for the dispatch tests: no --rung is a null rung."""
    assert parser.parse_args(["attempt", "task"]).rung is None


def test_attempt_cli_passes_rung_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake(**kw):
        seen.update(kw)
        raise UsageError("stop here; the dispatch is what is under test")

    monkeypatch.setattr(cli_module, "attempt", fake)
    assert cli_module.main(["attempt", "t", "--rung", "R1", "--", "cmd"]) == 2
    assert seen["rung"] == "R1"
    assert seen["command"] == ["cmd"]  # the adapter never sees --rung


def test_run_cli_passes_rung_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kw: seen.update(kw))
    assert (
        cli_module.main(
            ["run", "format_number", "--n", "2", "--rung", "R1", "--", "cmd"]
        )
        == 0
    )
    assert seen["rung"] == "R1"
    assert seen["command"] == ["cmd"]


def test_run_cli_rung_defaults_to_none() -> None:
    assert parser.parse_args(["run", "task", "--n", "1"]).rung is None
