"""``satyrn-evals grade-line``'s pure grading rules: a fake grader seam, no
subprocess/model/network (default tier). Every refusal branch has a sibling
success/other-branch test.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    DeadlinePhase,
    write_attempt_record,
)
from satyrn_evals.budget import LineCrossing
from satyrn_evals.errors import SatyrnError
from satyrn_evals.line_grade import (
    _NEVER_CROSSED_RULES,
    GradeCache,
    _never_crossed_verdict,
    default_out_path,
    grade_cell,
    grade_night,
    project_markers,
    refuse_project_grade_root,
    render_summary,
    write_report,
)
from satyrn_evals.run_record import RunRecord
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import LINE_PATCH_NAME, TRIPPED_PATCH_NAME

SHA = "0" * 40
DIGEST = "1" * 64
AT = "2026-09-19T00:00:00+00:00"


def _record(**overrides: object) -> AttemptRecord:
    fields: dict = dict(
        version=1, outcome=AttemptOutcome.ATTEMPTED, code=AttemptCode.OK,
        message="attempt recorded and graded", task="t", command=("pi",), command_exit=0,
        patch_path="patch.diff", transcript_path="transcript.txt", patch_digest=DIGEST,
        transcript_digest=DIGEST, verdict=Verdict.PASS, receipt_path="receipt.json", timeout=3000.0,
        rung="R1", contract_digest=DIGEST, workspace_base_sha=SHA, attempt_dir="t-1",
    )
    return AttemptRecord(**(fields | overrides))


def _run_record(**overrides: object) -> RunRecord:
    fields: dict = dict(
        version=1, task="t", task_tree_sha256=DIGEST, arm="baseline", model="omlx/m",
        condition="cold", n=1, mode="batch", max_minutes=60, stop_rule="infrastructure only",
        decision_rule="fisher", previous_result=None, token_budget=24000, turn_budget=36,
        isolation="local", purpose="development",
    )
    return RunRecord(**(fields | overrides))


class _FakeGrader:
    """Records every call and returns a scripted verdict per (task, patch)."""

    def __init__(self, verdicts: dict[str, str]) -> None:
        self.verdicts = verdicts
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, task: str, patch: str, grade_root: Path, name: str, cache: GradeCache) -> dict:
        self.calls.append((task, patch, name))
        return {"verdict": self.verdicts[patch], "reason": ""}


# --- grade_offline: a failed grade never crashes the night's report -------


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_a_non_zero_grade_exit_with_no_receipt_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`grade` crashed before writing a receipt: the cell is `unavailable`
    with the error text, not an uncaught exception that kills the night's
    report (F5)."""
    import satyrn_evals.line_grade as line_grade_module

    monkeypatch.setattr(
        line_grade_module.subprocess, "run",
        lambda *_a, **_k: _FakeCompleted(1, stderr="Traceback: boom"),
    )
    result = line_grade_module.grade_offline("t", "diff", tmp_path, "cell-1", {})
    assert result["verdict"] == "unavailable"
    assert "boom" in result["reason"] or "1" in result["reason"]


def test_a_non_zero_grade_exit_is_unavailable_even_with_a_stale_receipt_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exit code is checked on its own, not inferred from receipt
    presence: a non-zero exit must not be trusted even when a (stale)
    receipt.json happens to be sitting there."""
    import satyrn_evals.line_grade as line_grade_module

    def fake_run(argv: list[str], *, cwd: Path, **_k: object) -> _FakeCompleted:
        (Path(cwd) / "receipt.json").write_text(json.dumps({"verdict": "pass"}))
        return _FakeCompleted(1, stderr="boom")

    monkeypatch.setattr(line_grade_module.subprocess, "run", fake_run)
    result = line_grade_module.grade_offline("t", "diff", tmp_path, "cell-1b", {})
    assert result["verdict"] == "unavailable"
    assert "boom" in result["reason"]


def test_a_missing_receipt_after_a_zero_exit_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`grade` exited 0 but somehow never wrote `receipt.json`."""
    import satyrn_evals.line_grade as line_grade_module

    monkeypatch.setattr(
        line_grade_module.subprocess, "run", lambda *_a, **_k: _FakeCompleted(0)
    )
    result = line_grade_module.grade_offline("t", "diff", tmp_path, "cell-2", {})
    assert result["verdict"] == "unavailable"
    assert result["reason"]


def test_an_invalid_receipt_json_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`grade` wrote something to `receipt.json`, but it is not valid JSON."""
    import satyrn_evals.line_grade as line_grade_module

    def fake_run(argv: list[str], *, cwd: Path, **_k: object) -> _FakeCompleted:
        (Path(cwd) / "receipt.json").write_text("not json")
        return _FakeCompleted(0)

    monkeypatch.setattr(line_grade_module.subprocess, "run", fake_run)
    result = line_grade_module.grade_offline("t", "diff", tmp_path, "cell-3", {})
    assert result["verdict"] == "unavailable"
    assert result["reason"]


def test_grade_night_completes_when_one_cells_grade_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End to end: a broken grade for one cell does not stop the whole
    night's report from being written (F5)."""
    night = tmp_path / "night"
    cell_dir = night / "baseline" / "t-1"
    cell_dir.mkdir(parents=True)
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=1, at=AT)
    (cell_dir / LINE_PATCH_NAME).write_text("diff --git a/x b/x\n")
    write_attempt_record(
        cell_dir / "attempt.json",
        _record(attempt_dir="t-1", line_crossed=crossing, line_patch_path=LINE_PATCH_NAME),
    )
    _write_slot(night, 0, arm="baseline", attempt_dir="t-1")
    record = _run_record()

    import satyrn_evals.line_grade as line_grade_module

    monkeypatch.setattr(
        line_grade_module.subprocess, "run",
        lambda *_a, **_k: _FakeCompleted(1, stderr="grade crashed"),
    )
    report = grade_night(night, record, tmp_path / "grades", tasks_root=tmp_path / "tasks")
    assert len(report.rows) == 1
    assert report.rows[0].line_verdict == "unavailable"


# --- grade_cell: never crossed -------------------------------------------


def test_never_crossed_with_a_passing_verdict_uses_the_final_verdict() -> None:
    record = _record(verdict=Verdict.PASS)
    grader = _FakeGrader({})
    row = grade_cell(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=grader)
    assert (row.line_verdict, row.line_source) == ("pass", "final")
    assert grader.calls == []


def test_never_crossed_with_a_failing_verdict_uses_the_final_verdict() -> None:
    """Sibling to the passing case above."""
    record = _record(verdict=Verdict.FAIL)
    row = grade_cell(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=_FakeGrader({}))
    assert (row.line_verdict, row.line_source) == ("fail", "final")


def test_never_crossed_and_refused_with_no_verdict_is_not_pass() -> None:
    record = _record(
        outcome=AttemptOutcome.REFUSED, code=AttemptCode.NO_PATCH, verdict=None,
        patch_path=None, patch_digest=None, receipt_path=None,
    )
    row = grade_cell(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=_FakeGrader({}))
    assert (row.line_verdict, row.line_source) == ("not-pass", "final")


def test_never_crossed_with_an_unavailable_verdict_is_not_pass() -> None:
    """UNAVAILABLE is a verdict object, but never counts as `pass`/`fail`."""
    record = _record(verdict=Verdict.UNAVAILABLE)
    row = grade_cell(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=_FakeGrader({}))
    assert row.line_verdict == "not-pass"


# --- _never_crossed_verdict: infrastructure never becomes a model outcome --


def test_every_attempt_code_is_classified_for_the_never_crossed_case() -> None:
    """Pins the table: a new `AttemptCode` member with no entry here must
    fail this test, not silently default to `not-pass` (I3)."""
    assert set(_NEVER_CROSSED_RULES) == set(AttemptCode)


def test_an_unclassified_code_is_unavailable_with_a_named_reason_rather_than_raising() -> None:
    """N5: an unclassified `AttemptCode` must never abort the whole night's
    report (the same failure mode F5 removed for crashed grades). The cell
    becomes a per-cell `unavailable` result with a reason naming the code,
    not an uncaught `UsageError`."""
    assert AttemptCode.NO_PATCH in _NEVER_CROSSED_RULES
    trimmed = dict(_NEVER_CROSSED_RULES)
    del trimmed[AttemptCode.NO_PATCH]
    import satyrn_evals.line_grade as line_grade_module

    original = line_grade_module._NEVER_CROSSED_RULES
    line_grade_module._NEVER_CROSSED_RULES = trimmed
    try:
        verdict, reason = _never_crossed_verdict(
            AttemptCode.NO_PATCH, None, None, line_declared=False, name="cell-x"
        )
        assert verdict == "unavailable"
        assert reason is not None
        assert "cell-x" in reason
        assert "unclassified attempt code" in reason
        assert "NO_PATCH" in reason
    finally:
        line_grade_module._NEVER_CROSSED_RULES = original


@pytest.mark.parametrize(
    "code",
    [
        AttemptCode.PATCH_INVALID,
        AttemptCode.TRANSCRIPT_MISSING,
        AttemptCode.TRANSCRIPT_EMPTY,
        AttemptCode.WORKSPACE_FAILED,
        AttemptCode.MODEL_ERROR,
        AttemptCode.CLEANUP_FAILED,
        AttemptCode.GRADE_FAILED,
    ],
)
def test_infrastructure_codes_are_unavailable_when_never_crossed(code: AttemptCode) -> None:
    """These measured nothing about the model: excluded from the pass
    denominator, never scored as a model outcome."""
    verdict, reason = _never_crossed_verdict(code, None, None, line_declared=False, name="cell-x")
    assert verdict == "unavailable"
    assert reason is None


@pytest.mark.parametrize("code", [AttemptCode.NO_PATCH, AttemptCode.COMMAND_TIMEOUT, AttemptCode.REPEAT_LIMIT])
def test_the_models_own_no_patch_outcomes_are_not_pass_when_never_crossed(code: AttemptCode) -> None:
    """The model's own outcome, with nothing to grade -- not infrastructure."""
    assert _never_crossed_verdict(code, None, None, line_declared=False, name="cell-x") == ("not-pass", None)


def test_a_deadline_in_the_command_phase_is_not_pass_when_never_crossed() -> None:
    """A command-phase whole-attempt deadline is the model's own stop, exactly
    like COMMAND_TIMEOUT -- not infrastructure."""
    assert _never_crossed_verdict(
        AttemptCode.DEADLINE_EXCEEDED, None, DeadlinePhase.COMMAND, line_declared=False, name="cell-x"
    ) == ("not-pass", None)


@pytest.mark.parametrize("phase", [DeadlinePhase.SETUP, DeadlinePhase.PRESERVATION, DeadlinePhase.GRADING, DeadlinePhase.CLEANUP])
def test_a_deadline_outside_the_command_phase_is_unavailable_when_never_crossed(phase: DeadlinePhase) -> None:
    """Sibling to the command-phase case above: every other phase is the
    harness's own overhead, not the model's turn -- infrastructure."""
    verdict, reason = _never_crossed_verdict(AttemptCode.DEADLINE_EXCEEDED, None, phase, line_declared=False, name="cell-x")
    assert verdict == "unavailable"
    assert reason is None


def test_budget_exceeded_never_crossed_with_a_declared_line_is_a_broken_record() -> None:
    """N5: the line budget is strictly below the attempt budget (`run_record`
    enforces it), so the line must trip before the attempt budget can -- a
    BUDGET_EXCEEDED cell that never crossed a declared line is a
    contradiction, not a normal outcome. It becomes a per-cell `unavailable`
    result with a named reason, never an aborting raise (F5's failure mode)."""
    verdict, reason = _never_crossed_verdict(
        AttemptCode.BUDGET_EXCEEDED, None, None, line_declared=True, name="cell-x"
    )
    assert verdict == "unavailable"
    assert reason is not None
    assert "cell-x" in reason
    assert "broken record" in reason
    assert "BUDGET_EXCEEDED" in reason


def test_budget_exceeded_never_crossed_with_no_declared_line_is_not_pass() -> None:
    """Sibling to the contradiction case above: when this run never declared
    a line at all, a BUDGET_EXCEEDED cell that never crossed is ordinary."""
    assert _never_crossed_verdict(
        AttemptCode.BUDGET_EXCEEDED, None, None, line_declared=False, name="cell-x"
    ) == ("not-pass", None)


def test_grade_cell_wires_line_declared_into_the_budget_contradiction_check(tmp_path: Path) -> None:
    """End-to-end: `grade_cell` itself turns the broken-record contradiction
    into an `unavailable` row with a named reason, not a raise."""
    record = _record(
        outcome=AttemptOutcome.REFUSED, code=AttemptCode.BUDGET_EXCEEDED, verdict=None,
        patch_path=None, patch_digest=None, receipt_path=None,
    )
    row = grade_cell(
        record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"),
        cache={}, grader=_FakeGrader({}), line_declared=True,
    )
    assert row.line_verdict == "unavailable"
    assert row.line_unavailable_reason is not None
    assert "t-1" in row.line_unavailable_reason
    assert "broken record" in row.line_unavailable_reason


# --- grade_cell: crossed ---------------------------------------------------


def test_a_crossed_line_is_graded_offline_and_can_pass(tmp_path: Path) -> None:
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=10, at=AT)
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / LINE_PATCH_NAME).write_text("diff --git a/x b/x\n")
    record = _record(line_crossed=crossing, line_patch_path=LINE_PATCH_NAME)
    grader = _FakeGrader({"diff --git a/x b/x\n": "pass"})
    row = grade_cell(record, cell_dir=cell_dir, arm="engine", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert (row.line_verdict, row.line_source) == ("pass", "harvested")
    assert grader.calls == [("t", "diff --git a/x b/x\n", "t-1-line")]
    assert row.line_crossed == {"by": "tokens", "output_tokens": 16001, "turn": 10, "at": AT}


def test_a_crossed_line_can_fail_offline(tmp_path: Path) -> None:
    """Sibling to the passing case above."""
    crossing = LineCrossing(by="turns", output_tokens=10, turn=25, at=AT)
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / LINE_PATCH_NAME).write_text("diff --git a/x b/x\n")
    record = _record(line_crossed=crossing, line_patch_path=LINE_PATCH_NAME)
    grader = _FakeGrader({"diff --git a/x b/x\n": "fail"})
    row = grade_cell(record, cell_dir=cell_dir, arm="engine", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert row.line_verdict == "fail"


def test_a_crossed_line_with_no_harvested_patch_is_not_pass(tmp_path: Path) -> None:
    """Nothing was built yet at the crossing point: no LINE_PATCH_NAME file."""
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=1, at=AT)
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    record = _record(line_crossed=crossing, line_patch_path=None)
    grader = _FakeGrader({})
    row = grade_cell(record, cell_dir=cell_dir, arm="engine", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert (row.line_verdict, row.line_source) == ("not-pass", "harvested")
    assert grader.calls == []


def test_a_crossed_line_with_an_empty_harvested_patch_is_not_pass(tmp_path: Path) -> None:
    """The file exists but holds nothing (whitespace only) -- also not-pass."""
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=1, at=AT)
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / LINE_PATCH_NAME).write_text("   \n")
    record = _record(line_crossed=crossing, line_patch_path=LINE_PATCH_NAME)
    grader = _FakeGrader({})
    row = grade_cell(record, cell_dir=cell_dir, arm="engine", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert row.line_verdict == "not-pass"
    assert grader.calls == []


def test_a_harvest_error_is_unavailable_and_carries_the_message(tmp_path: Path) -> None:
    crossing = LineCrossing(by="tokens", output_tokens=16001, turn=1, at=AT)
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    record = _record(line_crossed=crossing, line_patch_path=None, line_harvest_error="git apply failed")
    grader = _FakeGrader({})
    row = grade_cell(record, cell_dir=cell_dir, arm="engine", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert (row.line_verdict, row.line_source) == ("unavailable", "harvested")
    assert row.line_harvest_error == "git apply failed"
    assert grader.calls == []


# --- tripped_verdict, graded by the same mechanism as line_verdict --------


def test_a_tripped_cell_is_graded_by_the_same_grader(tmp_path: Path) -> None:
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / TRIPPED_PATCH_NAME).write_text("diff --git a/y b/y\n")
    record = _record(
        outcome=AttemptOutcome.REFUSED, code=AttemptCode.BUDGET_EXCEEDED, verdict=None,
        patch_path=None, patch_digest=None, receipt_path=None, tripped_patch_path=TRIPPED_PATCH_NAME,
    )
    grader = _FakeGrader({"diff --git a/y b/y\n": "fail"})
    row = grade_cell(record, cell_dir=cell_dir, arm="baseline", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert row.tripped_verdict == "fail"
    assert grader.calls == [("t", "diff --git a/y b/y\n", "t-1-tripped")]


def test_a_cell_that_never_tripped_has_no_tripped_verdict() -> None:
    """Sibling to the tripped case above."""
    record = _record()
    row = grade_cell(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=_FakeGrader({}))
    assert row.tripped_verdict is None


# --- grade_night: enumeration, reused readers ------------------------------


def _write_slot(night: Path, index: int, *, arm: str, attempt_dir: str) -> None:
    (night / "slots").mkdir(parents=True, exist_ok=True)
    (night / "slots" / f"{index:02d}.json").write_text(
        json.dumps({"slot": index, "arm": arm, "attempt_dir": attempt_dir, "code": "OK"})
    )


def test_grade_night_reads_every_finished_slot_through_read_slots(tmp_path: Path) -> None:
    night = tmp_path / "night"
    for arm, attempt_dir in (("baseline", "t-1"), ("engine", "t-1")):
        cell_dir = night / arm / attempt_dir
        cell_dir.mkdir(parents=True)
        write_attempt_record(cell_dir / "attempt.json", _record(attempt_dir=attempt_dir))
    _write_slot(night, 0, arm="baseline", attempt_dir="t-1")
    _write_slot(night, 1, arm="engine", attempt_dir="t-1")
    record = _run_record(arm="baseline+engine")
    report = grade_night(night, record, tmp_path / "grades", grader=_FakeGrader({}))
    assert {(row.arm, row.attempt) for row in report.rows} == {("baseline", "t-1"), ("engine", "t-1")}


def test_grade_night_refuses_a_slot_arm_not_in_the_record(tmp_path: Path) -> None:
    night = tmp_path / "night"
    cell_dir = night / "engine" / "t-1"
    cell_dir.mkdir(parents=True)
    write_attempt_record(cell_dir / "attempt.json", _record(attempt_dir="t-1"))
    _write_slot(night, 0, arm="engine", attempt_dir="t-1")
    record = _run_record(arm="baseline")
    with pytest.raises(SatyrnError, match="engine"):
        grade_night(night, record, tmp_path / "grades", grader=_FakeGrader({}))


# --- render_summary: per (task, arm), never pooled -------------------------


def test_render_summary_header_states_what_each_arm_grades(tmp_path: Path) -> None:
    """I2: the report header says the raw-tree/delivered-candidate split so a
    reader never mistakes the two verdict columns for grading the same tree."""
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),)
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    assert "delivered candidate" in summary
    assert "carried tests" in summary


def test_render_summary_breaks_out_pass_counts_by_task_and_arm(tmp_path: Path) -> None:
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (
        LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),
        LineGradeRow("a-2", "taskA", "baseline", "OK", "fail", None, None, "fail", "final"),
        LineGradeRow("a-3", "taskA", "engine", "OK", "pass", None, None, "pass", "final"),
        LineGradeRow("b-1", "taskB", "baseline", "OK", "pass", None, None, "pass", "final"),
    )
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    assert "| taskA | baseline | 1/2 |" in summary
    assert "| taskA | engine | 1/1 |" in summary
    assert "| taskB | baseline | 1/1 |" in summary
    # Never a single pooled number across tasks or arms:
    assert "2/4" not in summary
    assert "3/4" not in summary


def test_render_summary_lists_unavailable_cells(tmp_path: Path) -> None:
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (
        LineGradeRow("a-1", "taskA", "engine", "OK", None, None, {"by": "tokens"}, "unavailable", "harvested", "boom"),
        LineGradeRow("a-2", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),
    )
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    assert "a-1" in summary.split("## unavailable")[1]
    assert "a-2" not in summary.split("## unavailable")[1]


def test_render_summary_excludes_unavailable_cells_from_the_pass_denominator() -> None:
    """An `unavailable` cell measured nothing: it must not inflate either
    side of a (task, arm) pass fraction, and the count excluded must be
    stated (I3)."""
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (
        LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),
        LineGradeRow("a-2", "taskA", "baseline", "OK", None, None, None, "unavailable", "final", "boom"),
    )
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    assert "| taskA | baseline | 1/1 |" in summary
    assert "1/2" not in summary
    # The per-(task, arm) exclusion count is stated, not just the attempt list:
    assert "1" in summary.split("| taskA | baseline |")[1].split("\n")[0]


def test_render_summary_with_no_unavailable_cells_says_so() -> None:
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),)
    report = LineGradeReport(night="/n", rows=rows)
    assert "(none)" in render_summary(report)


# --- render_summary: N5 broken records surface at the top, need a human ----


def test_render_summary_puts_broken_records_in_a_top_heading_before_the_table() -> None:
    """N5: a broken-record cell (unclassified code / BUDGET_EXCEEDED
    contradiction) is not just another `unavailable` row -- it is listed
    prominently at the top, under a heading that says a human needs to look,
    ahead of the per-(task, arm) table."""
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (
        LineGradeRow(
            "a-1", "taskA", "baseline", "BUDGET_EXCEEDED", None, None, None,
            "unavailable", "final", None, "broken record: BUDGET_EXCEEDED without a line crossing",
        ),
        LineGradeRow("a-2", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),
    )
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    heading_index = summary.index("NEEDS")
    table_index = summary.index("| task | arm |")
    assert heading_index < table_index
    assert "a-1" in summary[heading_index:table_index]
    assert "broken record" in summary[heading_index:table_index]


def test_render_summary_needs_review_section_says_none_when_empty() -> None:
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),)
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    heading_index = summary.index("NEEDS")
    table_index = summary.index("| task | arm |")
    assert "(none)" in summary[heading_index:table_index]


def test_render_summary_broken_records_are_still_excluded_from_the_pass_denominator() -> None:
    """A broken record is also, like any other `unavailable` cell, excluded
    from both sides of the pass fraction."""
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (
        LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),
        LineGradeRow(
            "a-2", "taskA", "baseline", "BUDGET_EXCEEDED", None, None, None,
            "unavailable", "final", None, "broken record: BUDGET_EXCEEDED without a line crossing",
        ),
    )
    report = LineGradeReport(night="/n", rows=rows)
    summary = render_summary(report)
    assert "| taskA | baseline | 1/1 |" in summary


# --- write_report / default_out_path / refuse_project_grade_root ----------


def test_write_report_writes_json(tmp_path: Path) -> None:
    from satyrn_evals.line_grade import LineGradeReport, LineGradeRow

    rows = (LineGradeRow("a-1", "taskA", "baseline", "OK", "pass", None, None, "pass", "final"),)
    report = LineGradeReport(night="/n", rows=rows)
    out = tmp_path / "out.json"
    write_report(report, out)
    body = json.loads(out.read_text())
    assert body["night"] == "/n"
    assert body["rows"][0]["attempt"] == "a-1"


def test_default_out_path_is_named_from_the_night(tmp_path: Path) -> None:
    night = tmp_path / "2026-09-16-census-selfhost-docs-linter"
    assert default_out_path(tmp_path / "grades", night).name == "grade-line-2026-09-16-census-selfhost-docs-linter.json"


def test_refuse_project_grade_root_raises_under_a_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    with pytest.raises(SatyrnError, match="pyproject.toml"):
        refuse_project_grade_root(grade_root)


def test_refuse_project_grade_root_accepts_a_root_with_no_markers(tmp_path: Path) -> None:
    """Sibling to the refusal above."""
    grade_root = tmp_path / "grades"
    grade_root.mkdir()
    refuse_project_grade_root(grade_root)  # must not raise


def test_project_markers_finds_ancestor_config(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text("")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert project_markers(nested) == [tmp_path / "conftest.py"]
