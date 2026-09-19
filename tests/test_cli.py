import argparse
import json
from pathlib import Path

import pytest

from satyrn_evals import cli as cli_module
from satyrn_evals.budget import AttemptBudget, LineBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.cli import (
    main,
    parser,
    positive_finite_timeout,
    positive_int,
    split_attempt_argv,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.summary import SUMMARY_NAME
from satyrn_evals.task_tree import tree_digest
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


PI = ["satyrn-evals-attempt-pi", "--model", "omlx/Ornith-1.5-9B-MLX-8bit"]


def _record(tmp_path: Path, **over: object) -> Path:
    path = tmp_path / "record.json"
    path.write_text(json.dumps({
        "version": 1, "task": "format_number", "task_tree_sha256": tree_digest(DEFAULT_TASKS_ROOT / "format_number"),
        "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4, "mode": "attended",
        "max_minutes": 60, "stop_rule": "infrastructure only", "decision_rule": "fisher",
        "previous_result": None, "token_budget": 24000, "turn_budget": 36,
        "isolation": "local", "purpose": "development", **over,
    }))
    return path


def test_run_takes_its_budget_and_profile_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    assert main(["run", "format_number", "--n", "4", "--run-record", str(_record(tmp_path)), "--", *PI]) == 0
    assert seen["budget"] == AttemptBudget(output_tokens=24000, turns=36)
    assert seen["isolation"] is Isolation.LOCAL


def test_attempt_takes_the_isolated_profile_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_attempt(**kwargs: object) -> object:
        seen.update(kwargs)
        raise UsageError("stop here")

    monkeypatch.setattr(cli_module, "attempt", fake_attempt)
    record = _record(tmp_path, isolation="isolated", purpose="admission")
    assert main(["attempt", "format_number", "--run-record", str(record), "--", *PI]) == 2
    assert seen["isolation"] is Isolation.ISOLATED


def test_attempt_takes_the_line_budget_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The launcher path (`launch_cell.run_cell`) already builds a `LineBudget`
    from a record's `line_token_budget`/`line_turn_budget` and passes it to
    `attempt()`; the CLI's `--run-record` path must do the same, reusing
    `run_record.line_budget()` (release-two line-harvest gap, Part B)."""
    seen: dict[str, object] = {}

    def fake_attempt(**kwargs: object) -> object:
        seen.update(kwargs)
        raise UsageError("stop here")

    monkeypatch.setattr(cli_module, "attempt", fake_attempt)
    # F2: line_token_budget must sit LINE_BUDGET_MARGIN_TOKENS below
    # token_budget, so this record's own token_budget is raised to fit.
    record = _record(tmp_path, token_budget=40000, line_token_budget=16000, line_turn_budget=24)
    assert main(["attempt", "format_number", "--run-record", str(record), "--", *PI]) == 2
    assert seen["line_budget"] == LineBudget(output_tokens=16000, turns=24)


def test_run_takes_the_line_budget_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    record = _record(tmp_path, token_budget=40000, line_token_budget=16000, line_turn_budget=24)
    assert main(["run", "format_number", "--n", "4", "--run-record", str(record), "--", *PI]) == 0
    assert seen["line_budget"] == LineBudget(output_tokens=16000, turns=24)


def test_attempt_without_a_declared_line_has_no_line_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sibling success: a record with no declared line still reaches attempt()
    with a line_budget of None, same as the launcher's own both-or-neither rule."""
    seen: dict[str, object] = {}

    def fake_attempt(**kwargs: object) -> object:
        seen.update(kwargs)
        raise UsageError("stop here")

    monkeypatch.setattr(cli_module, "attempt", fake_attempt)
    record = _record(tmp_path)
    assert main(["attempt", "format_number", "--run-record", str(record), "--", *PI]) == 2
    assert seen["line_budget"] is None


def test_attempt_refuses_a_command_the_record_does_not_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_module, "attempt", lambda **kw: pytest.fail("no cell may start"))
    assert main(["attempt", "format_number", "--run-record", str(_record(tmp_path)), "--", "cmd"]) == 2


def test_run_without_a_record_has_no_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    assert main(["run", "format_number", "--n", "1", "--", "cmd"]) == 0
    assert seen["budget"] is None


def test_attempt_with_an_unreadable_record_is_a_usage_error(tmp_path: Path) -> None:
    assert main(["attempt", "format_number", "--run-record", str(tmp_path / "absent.json"), "--", "cmd"]) == 2


# --- F3/R13: attempt/run --run-record calls gate(); run --n must match record.n ---


def test_attempt_refuses_an_admission_record_under_the_local_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gate() runs the same as launch --check: a deciding purpose refuses local."""
    monkeypatch.setattr(cli_module, "attempt", lambda **kw: pytest.fail("no cell may start"))
    record = _record(tmp_path, isolation="local", purpose="admission")
    assert main(["attempt", "format_number", "--run-record", str(record), "--", *PI]) == 2


def test_run_refuses_an_admission_record_under_the_local_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_module, "run", lambda **kw: pytest.fail("no cell may start"))
    record = _record(tmp_path, isolation="local", purpose="admission", n=1)
    assert main(["run", "format_number", "--n", "1", "--run-record", str(record), "--", *PI]) == 2


def test_attempt_gate_still_accepts_a_development_record_under_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake_attempt(**kwargs: object) -> object:
        seen.update(kwargs)
        raise UsageError("stop here")

    monkeypatch.setattr(cli_module, "attempt", fake_attempt)
    record = _record(tmp_path, isolation="local", purpose="development")
    assert main(["attempt", "format_number", "--run-record", str(record), "--", *PI]) == 2
    assert seen["isolation"] is Isolation.LOCAL


def test_run_refuses_an_n_that_disagrees_with_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_module, "run", lambda **kw: pytest.fail("no cell may start"))
    record = _record(tmp_path, n=4)
    assert main(["run", "format_number", "--n", "1", "--run-record", str(record), "--", *PI]) == 2


def test_run_accepts_an_n_that_agrees_with_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    record = _record(tmp_path, n=1)
    assert main(["run", "format_number", "--n", "1", "--run-record", str(record), "--", *PI]) == 0
    assert seen["n"] == 1


ARM = Path(__file__).resolve().parent.parent / "arms" / "baseline-ornith15-9b.json"


def _preflight_record(tmp_path: Path, **over: object) -> Path:
    return _record(tmp_path, isolation="isolated", purpose="admission", **over)


def _fake_preflight(monkeypatch: pytest.MonkeyPatch, *, model_server_problems: list[str] | None = None) -> None:
    from satyrn_evals.cell_preflight import CellPreflight

    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight([], {"pi_version": "0.85.1"}))
    monkeypatch.setattr(cli_module, "arm_export_problems", lambda arm: [])
    monkeypatch.setattr(
        cli_module, "model_server_checks",
        lambda arms, isolation, **kw: (model_server_problems or [], {arm.server_model: {"base_url": "http://x"} for arm in arms}),
    )


def test_launch_preflight_exits_1_when_the_model_server_check_finds_a_problem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_preflight(monkeypatch, model_server_problems=["the model server at http://x is unreachable: refused"])
    record = _preflight_record(tmp_path)
    assert main(["launch", "--preflight", str(record), "--arm", str(ARM)]) == 1
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["problems"] == ["the model server at http://x is unreachable: refused"]
    assert "launch preflight FAILED: the model server at http://x is unreachable: refused" in captured.err


def test_launch_preflight_exits_0_when_the_model_server_check_is_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_preflight(monkeypatch, model_server_problems=[])
    record = _preflight_record(tmp_path)
    assert main(["launch", "--preflight", str(record), "--arm", str(ARM)]) == 0


def test_launch_preflight_asks_the_model_server_check_about_this_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from satyrn_evals.cell_preflight import CellPreflight

    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight([], {}))
    monkeypatch.setattr(cli_module, "arm_export_problems", lambda arm: [])

    def model_server_checks(arms: list, isolation: Isolation, **kw: object) -> tuple[list[str], dict]:
        seen["arms"] = [arm.server_model for arm in arms]
        seen["isolation"] = isolation
        return [], {}

    monkeypatch.setattr(cli_module, "model_server_checks", model_server_checks)
    record = _preflight_record(tmp_path)
    assert main(["launch", "--preflight", str(record), "--arm", str(ARM)]) == 0
    assert seen == {"arms": ["Ornith-1.5-9B-MLX-8bit"], "isolation": Isolation.ISOLATED}


# --- Part C: grade-line ---


def _fake_report() -> object:
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    return LineGradeReport(
        night="/n",
        rows=(LineGradeRow("t-1", "t", "baseline", "OK", "pass", None, None, "pass", "final"),),
    )


def test_grade_line_cli_wires_night_record_and_grade_root_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake_grade_night(night: Path, record: object, grade_root: Path, **kw: object) -> object:
        seen["night"] = night
        seen["record"] = record
        seen["grade_root"] = grade_root
        return _fake_report()

    monkeypatch.setattr(cli_module, "grade_night", fake_grade_night)
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    record_path = _record(tmp_path)
    assert main(["grade-line", str(night), "--record", str(record_path), "--grade-root", str(grade_root)]) == 0
    assert seen["night"] == night
    assert seen["grade_root"] == grade_root
    assert seen["record"].task == "format_number"


def test_grade_line_cli_writes_json_and_prints_the_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "grade_night", lambda *a, **kw: _fake_report())
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    record_path = _record(tmp_path)
    out_path = tmp_path / "out.json"
    assert main([
        "grade-line", str(night), "--record", str(record_path),
        "--grade-root", str(grade_root), "--out", str(out_path),
    ]) == 0
    body = json.loads(out_path.read_text())
    assert body["rows"][0]["attempt"] == "t-1"
    captured = capsys.readouterr()
    assert "| t | baseline | 1/1 |" in captured.out


def test_grade_line_cli_exits_the_needs_review_code_when_a_row_needs_a_human_look(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """N5: a broken-record cell must not silently pass as exit 0 -- the CLI
    still writes the full report, then exits a distinct, documented code."""
    from satyrn_evals.line_grade import (
        LINE_GRADE_NEEDS_REVIEW_EXIT_CODE,
        LineGradeReport,
        LineGradeRow,
    )

    def fake_report() -> LineGradeReport:
        return LineGradeReport(
            night="/n",
            rows=(
                LineGradeRow(
                    "t-1", "t", "baseline", "BUDGET_EXCEEDED", None, None, None,
                    "unavailable", "final", None,
                    "broken record: BUDGET_EXCEEDED without a line crossing",
                ),
            ),
        )

    monkeypatch.setattr(cli_module, "grade_night", lambda *a, **kw: fake_report())
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    record_path = _record(tmp_path)
    out_path = tmp_path / "out.json"
    exit_code = main([
        "grade-line", str(night), "--record", str(record_path),
        "--grade-root", str(grade_root), "--out", str(out_path),
    ])
    assert exit_code == LINE_GRADE_NEEDS_REVIEW_EXIT_CODE
    assert exit_code not in (0, 2, 3)
    # The full report is still written and printed, not skipped:
    assert out_path.exists()
    assert "t-1" in capsys.readouterr().out


def test_grade_line_cli_refuses_a_grade_root_under_a_python_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module, "grade_night", lambda *a, **kw: pytest.fail("must not grade under a project's own pytest config")
    )
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    (grade_root / "pyproject.toml").write_text("[project]\n")
    record_path = _record(tmp_path)
    assert main(["grade-line", str(night), "--record", str(record_path), "--grade-root", str(grade_root)]) == 2


# --- grade-sensitivity ------------------------------------------------------


def _fake_sensitivity_report(*, task: str = "t", arm: str = "baseline", passed: bool = True) -> object:
    from satyrn_evals.sensitivity_grade import CellSensitivity, SensitivityReport

    return SensitivityReport(
        night="/n",
        cells=(
            CellSensitivity(
                attempt="t-1", task=task, arm=arm, code="OK",
                delivered_pass=passed, delivered_pass_stripped=passed,
            ),
        ),
    )


def test_grade_sensitivity_cli_wires_night_record_and_grade_root_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake_grade_night_sensitivity(night: Path, record: object, grade_root: Path, **kw: object) -> object:
        seen["night"] = night
        seen["record"] = record
        seen["grade_root"] = grade_root
        return _fake_sensitivity_report()

    monkeypatch.setattr(cli_module, "grade_night_sensitivity", fake_grade_night_sensitivity)
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    record_path = _record(tmp_path)
    assert main([
        "grade-sensitivity", str(night), "--record", str(record_path), "--grade-root", str(grade_root),
    ]) == 0
    assert seen["night"] == night
    assert seen["grade_root"] == grade_root
    assert seen["record"].task == "format_number"


def test_grade_sensitivity_cli_writes_json_and_prints_the_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "grade_night_sensitivity", lambda *a, **kw: _fake_sensitivity_report())
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    record_path = _record(tmp_path)
    out_path = tmp_path / "out.json"
    assert main([
        "grade-sensitivity", str(night), "--record", str(record_path),
        "--grade-root", str(grade_root), "--out", str(out_path),
    ]) == 0
    body = json.loads(out_path.read_text())
    assert body["cells"][0]["attempt"] == "t-1"
    captured = capsys.readouterr()
    assert "delivered_pass" in captured.out
    assert "1/1" in captured.out


def test_grade_sensitivity_cli_refuses_a_grade_root_under_a_python_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module, "grade_night_sensitivity",
        lambda *a, **kw: pytest.fail("must not grade under a project's own pytest config"),
    )
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    (grade_root / "pyproject.toml").write_text("[project]\n")
    record_path = _record(tmp_path)
    assert main([
        "grade-sensitivity", str(night), "--record", str(record_path), "--grade-root", str(grade_root),
    ]) == 2


def test_grade_sensitivity_cli_record2_without_combine_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_module, "grade_night_sensitivity", lambda *a, **kw: _fake_sensitivity_report())
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    night = tmp_path / "night"
    night.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    record_path = _record(tmp_path)
    assert main([
        "grade-sensitivity", str(night), "--record", str(record_path), "--grade-root", str(grade_root),
        "--record2", str(record_path),
    ]) == 2


def test_grade_sensitivity_cli_combine_sums_two_parts_and_checks_combinable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reports = [
        _fake_sensitivity_report(passed=True),
        _fake_sensitivity_report(passed=False),
    ]
    calls: list[Path] = []

    def fake_grade_night_sensitivity(night: Path, record: object, grade_root: Path, **kw: object) -> object:
        calls.append(night)
        return reports[len(calls) - 1]

    combinable_calls: list[tuple[object, object]] = []
    monkeypatch.setattr(cli_module, "grade_night_sensitivity", fake_grade_night_sensitivity)
    monkeypatch.setattr(cli_module, "refuse_project_grade_root", lambda grade_root: None)
    monkeypatch.setattr(
        cli_module, "check_combinable",
        lambda a, b: combinable_calls.append((a, b)),
    )
    night = tmp_path / "night"
    night.mkdir()
    night2 = tmp_path / "night2"
    night2.mkdir()
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    record_path = _record(tmp_path)
    part2_dir = tmp_path / "part2"
    part2_dir.mkdir()
    record_path2 = _record(part2_dir)
    exit_code = main([
        "grade-sensitivity", str(night), "--record", str(record_path), "--grade-root", str(grade_root),
        "--combine", str(night2), "--record2", str(record_path2),
    ])
    assert exit_code == 0
    assert calls == [night, night2]
    assert len(combinable_calls) == 1
    captured = capsys.readouterr()
    assert "## A" in captured.out
    assert "## B" in captured.out
    assert "## A+B" in captured.out
    # Part A alone: 1/1; part B alone: 0/1; combined: 1/2.
    assert "1/1" in captured.out
    assert "0/1" in captured.out
    assert "1/2" in captured.out


def test_launch_preflight_skips_the_model_server_check_on_the_fake_pi_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals.cell import CELL_PATH_PREFIX_ENV
    from satyrn_evals.cell_preflight import CellPreflight

    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, "/fake/bin")
    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight([], {}))
    monkeypatch.setattr(cli_module, "arm_export_problems", lambda arm: [])
    monkeypatch.setattr(
        cli_module, "model_server_checks",
        lambda arms, isolation, **kw: pytest.fail("model_server_checks must not be consulted on the fake-pi seam"),
    )
    record = _preflight_record(tmp_path)
    # exits 1 regardless (the seam itself is flagged as a problem), but must not have blown up
    assert main(["launch", "--preflight", str(record), "--arm", str(ARM)]) == 1
