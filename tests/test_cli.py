import pytest

from satyrn_evals.cli import main


def test_unknown_task_is_usage_error() -> None:
    assert main(["grade", "no_such_task", "whatever.patch"]) == 2


def test_grade_requires_arguments() -> None:
    with pytest.raises(SystemExit):
        main(["grade"])


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
