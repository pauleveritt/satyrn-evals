import pytest

from satyrn_evals.cli import main, parser, positive_finite_timeout, split_attempt_argv
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
    assert main(["grade", "--tasks-root", str(tmp_path), "no_such_task", "x.patch"]) == 2


def test_attempt_split_keeps_flags_and_command() -> None:
    flags, command = split_attempt_argv(["t", "--tasks-root", "R", "--", "cmd", "--flag", "x"])
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
def test_attempt_timeout_rejects_nonpositive_nonfinite_and_malformed(value: str) -> None:
    with pytest.raises(Exception, match="finite number greater than zero"):
        positive_finite_timeout(value)


def test_attempt_timeout_accepts_positive_finite() -> None:
    assert positive_finite_timeout("0.25") == 0.25


def test_attempt_timeout_default_tracks_workspace_default() -> None:
    args = parser.parse_args(["attempt", "task"])
    assert args.timeout == DEFAULT_TIMEOUT
