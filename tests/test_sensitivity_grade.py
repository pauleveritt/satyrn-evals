"""``satyrn-evals grade-sensitivity``'s pure grading rules: a fake grader
seam, no subprocess/model/network (default tier). Every branch has a
sibling test for the other direction.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    write_attempt_record,
)
from satyrn_evals.errors import UsageError
from satyrn_evals.run_record import RunRecord
from satyrn_evals.sensitivity_grade import (
    GradeCache,
    check_combinable,
    combine_summaries,
    fisher_exact_greater,
    grade_cell_sensitivity,
    grade_night_sensitivity,
    render_report,
    strip_and_grade,
    summarize,
)
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import TRIPPED_PATCH_NAME

SHA = "0" * 40
DIGEST = "1" * 64

DIFF_TWO_FILES = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
    "diff --git a/coverage.json b/coverage.json\n"
    "--- a/coverage.json\n"
    "+++ b/coverage.json\n"
    "@@ -1 +1 @@\n"
    "-{}\n"
    "+{\"x\": 1}\n"
)


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


class _ScriptedGrader:
    """Returns a scripted verdict/reason sequence per call, keyed by name
    prefix (before the ``-rN`` round suffix ``strip_and_grade`` appends)."""

    def __init__(self, scripts: dict[str, list[dict]]) -> None:
        self.scripts = scripts
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, task: str, patch: str, grade_root: Path, name: str, cache: GradeCache) -> dict:
        self.calls.append((task, patch, name))
        prefix = name.rsplit("-r", 1)[0]
        script = self.scripts[prefix]
        index = min(len([c for c in self.calls if c[2].rsplit("-r", 1)[0] == prefix]) - 1, len(script) - 1)
        return script[index]


# --- strip_and_grade: repeats while the grader names a non-source path ----


def test_strip_and_grade_passes_immediately_with_no_refusal(tmp_path: Path) -> None:
    grader = _ScriptedGrader({"cell": [{"verdict": "pass", "reason": ""}]})
    verdict, stripped = strip_and_grade("t", DIFF_TWO_FILES, tmp_path, "cell", {}, grader)
    assert (verdict, stripped) == ("pass", ())
    assert len(grader.calls) == 1


def test_strip_and_grade_strips_a_named_non_source_path_and_regrades(tmp_path: Path) -> None:
    grader = _ScriptedGrader(
        {
            "cell": [
                {"verdict": "unavailable", "reason": "patch touches non-source path: coverage.json"},
                {"verdict": "pass", "reason": ""},
            ]
        }
    )
    verdict, stripped = strip_and_grade("t", DIFF_TWO_FILES, tmp_path, "cell", {}, grader)
    assert (verdict, stripped) == ("pass", ("coverage.json",))
    assert len(grader.calls) == 2
    # The second call's patch no longer carries the stripped section.
    assert "coverage.json" not in grader.calls[1][1]
    assert "solution.py" in grader.calls[1][1]


def test_strip_and_grade_repeats_for_a_second_named_path(tmp_path: Path) -> None:
    three_files = DIFF_TWO_FILES + (
        "diff --git a/PROVENANCE.md b/PROVENANCE.md\n"
        "--- a/PROVENANCE.md\n+++ b/PROVENANCE.md\n@@ -1 +1 @@\n-a\n+b\n"
    )
    grader = _ScriptedGrader(
        {
            "cell": [
                {"verdict": "unavailable", "reason": "patch touches non-source path: coverage.json"},
                {"verdict": "unavailable", "reason": "patch touches non-source path: PROVENANCE.md"},
                {"verdict": "fail", "reason": ""},
            ]
        }
    )
    verdict, stripped = strip_and_grade("t", three_files, tmp_path, "cell", {}, grader)
    assert (verdict, stripped) == ("fail", ("coverage.json", "PROVENANCE.md"))


def test_strip_and_grade_a_genuine_unavailable_is_not_a_refusal_to_strip(tmp_path: Path) -> None:
    """The reason does not name a non-source path: never mistaken for a
    strippable refusal."""
    grader = _ScriptedGrader({"cell": [{"verdict": "unavailable", "reason": "RuntimeError: grade exited 1: boom"}]})
    verdict, stripped = strip_and_grade("t", DIFF_TWO_FILES, tmp_path, "cell", {}, grader)
    assert (verdict, stripped) == ("unavailable", ())
    assert len(grader.calls) == 1


def test_strip_and_grade_refuses_a_cycle_on_the_same_path(tmp_path: Path) -> None:
    grader = _ScriptedGrader(
        {
            "cell": [
                {"verdict": "unavailable", "reason": "patch touches non-source path: coverage.json"},
                {"verdict": "unavailable", "reason": "patch touches non-source path: coverage.json"},
            ]
        }
    )
    verdict, stripped = strip_and_grade("t", DIFF_TWO_FILES, tmp_path, "cell", {}, grader)
    assert (verdict, stripped) == ("unavailable", ("coverage.json",))
    assert len(grader.calls) == 2


def test_strip_and_grade_stops_when_the_named_path_is_not_in_the_patch(tmp_path: Path) -> None:
    grader = _ScriptedGrader(
        {"cell": [{"verdict": "unavailable", "reason": "patch touches non-source path: nowhere.txt"}]}
    )
    verdict, stripped = strip_and_grade("t", DIFF_TWO_FILES, tmp_path, "cell", {}, grader)
    assert (verdict, stripped) == ("unavailable", ())


def test_strip_and_grade_hits_the_round_cap(tmp_path: Path) -> None:
    diff = "".join(
        f"diff --git a/f{i}.json b/f{i}.json\n--- a/f{i}.json\n+++ b/f{i}.json\n@@ -1 +1 @@\n-a\n+b\n"
        for i in range(5)
    )
    script = [
        {"verdict": "unavailable", "reason": f"patch touches non-source path: f{i}.json"} for i in range(5)
    ]
    grader = _ScriptedGrader({"cell": script})
    verdict, stripped = strip_and_grade("t", diff, tmp_path, "cell", {}, grader, max_rounds=2)
    assert verdict == "unavailable"
    assert len(stripped) == 2


# --- grade_cell_sensitivity: the per-cell rules -----------------------------


def test_delivered_pass_is_exactly_the_recorded_verdict_and_never_reregraded() -> None:
    record = _record(verdict=Verdict.PASS)
    grader = _ScriptedGrader({})
    row = grade_cell_sensitivity(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=grader)
    assert row.delivered_pass is True
    assert row.delivered_pass_stripped is True
    assert grader.calls == []


def test_a_failing_verdict_is_unchanged_and_never_reregraded() -> None:
    """Sibling to the passing case above."""
    record = _record(verdict=Verdict.FAIL)
    grader = _ScriptedGrader({})
    row = grade_cell_sensitivity(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=grader)
    assert row.delivered_pass is False
    assert row.delivered_pass_stripped is False
    assert grader.calls == []


def test_a_non_ok_cell_with_no_patch_stays_not_delivered(tmp_path: Path) -> None:
    record = _record(
        code=AttemptCode.NO_PATCH, outcome=AttemptOutcome.REFUSED, patch_path=None,
        patch_digest=None, verdict=None, receipt_path=None,
    )
    grader = _ScriptedGrader({})
    row = grade_cell_sensitivity(record, cell_dir=tmp_path, arm="baseline", grade_root=tmp_path, cache={}, grader=grader)
    assert (row.delivered_pass, row.delivered_pass_stripped) == (False, False)
    assert grader.calls == []


def test_an_unavailable_verdict_with_a_non_source_path_is_stripped_and_regraded(tmp_path: Path) -> None:
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / "patch.diff").write_text(DIFF_TWO_FILES)
    record = _record(verdict=Verdict.UNAVAILABLE)
    grader = _ScriptedGrader(
        {
            "t-1-delivered": [
                {"verdict": "unavailable", "reason": "patch touches non-source path: coverage.json"},
                {"verdict": "pass", "reason": ""},
            ]
        }
    )
    row = grade_cell_sensitivity(record, cell_dir=cell_dir, arm="baseline", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert row.delivered_pass is False
    assert row.delivered_pass_stripped is True
    assert row.stripped_paths == ("coverage.json",)


def test_a_budget_exceeded_cells_tripped_patch_is_reported_as_undelivered_tree(tmp_path: Path) -> None:
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / TRIPPED_PATCH_NAME).write_text(DIFF_TWO_FILES)
    record = _record(
        code=AttemptCode.BUDGET_EXCEEDED, outcome=AttemptOutcome.REFUSED, verdict=None,
        patch_path=None, patch_digest=None, receipt_path=None,
        tripped_patch_path=TRIPPED_PATCH_NAME,
    )
    grader = _ScriptedGrader(
        {
            "t-1-tripped": [
                {"verdict": "unavailable", "reason": "patch touches non-source path: coverage.json"},
                {"verdict": "pass", "reason": ""},
            ]
        }
    )
    row = grade_cell_sensitivity(record, cell_dir=cell_dir, arm="baseline", grade_root=tmp_path / "grades", cache={}, grader=grader)
    # Never counted in either delivered column.
    assert (row.delivered_pass, row.delivered_pass_stripped) == (False, False)
    assert row.undelivered_tree == "yes"
    assert row.undelivered_tree_stripped_paths == ("coverage.json",)


def test_a_budget_exceeded_cell_whose_tripped_tree_never_passes_is_no(tmp_path: Path) -> None:
    """Sibling to the "yes" case above."""
    cell_dir = tmp_path / "t-1"
    cell_dir.mkdir()
    (cell_dir / TRIPPED_PATCH_NAME).write_text(DIFF_TWO_FILES)
    record = _record(
        code=AttemptCode.BUDGET_EXCEEDED, outcome=AttemptOutcome.REFUSED, verdict=None,
        patch_path=None, patch_digest=None, receipt_path=None,
        tripped_patch_path=TRIPPED_PATCH_NAME,
    )
    grader = _ScriptedGrader({"t-1-tripped": [{"verdict": "fail", "reason": ""}]})
    row = grade_cell_sensitivity(record, cell_dir=cell_dir, arm="baseline", grade_root=tmp_path / "grades", cache={}, grader=grader)
    assert row.undelivered_tree == "no"


def test_a_non_budget_exceeded_cell_has_no_undelivered_tree_column() -> None:
    record = _record(verdict=Verdict.PASS)
    row = grade_cell_sensitivity(record, cell_dir=Path("/cells/t-1"), arm="baseline", grade_root=Path("/g"), cache={}, grader=_ScriptedGrader({}))
    assert row.undelivered_tree is None


# --- grade_night_sensitivity: enumeration is iter_finished_cells -----------


def _write_slot(night: Path, index: int, *, arm: str, attempt_dir: str) -> None:
    (night / "slots").mkdir(parents=True, exist_ok=True)
    (night / "slots" / f"{index:02d}.json").write_text(
        json.dumps({"slot": index, "arm": arm, "attempt_dir": attempt_dir, "code": "OK"})
    )


def test_grade_night_sensitivity_reads_every_finished_slot(tmp_path: Path) -> None:
    night = tmp_path / "night"
    for arm in ("baseline", "engine"):
        cell_dir = night / arm / "t-1"
        cell_dir.mkdir(parents=True)
        write_attempt_record(cell_dir / "attempt.json", _record(attempt_dir="t-1"))
    _write_slot(night, 0, arm="baseline", attempt_dir="t-1")
    _write_slot(night, 1, arm="engine", attempt_dir="t-1")
    record = _run_record(arm="baseline+engine")
    report = grade_night_sensitivity(night, record, tmp_path / "grades", grader=_ScriptedGrader({}))
    assert {(cell.arm, cell.attempt) for cell in report.cells} == {("baseline", "t-1"), ("engine", "t-1")}


def test_grade_night_sensitivity_refuses_a_slot_arm_not_in_the_record(tmp_path: Path) -> None:
    night = tmp_path / "night"
    cell_dir = night / "engine" / "t-1"
    cell_dir.mkdir(parents=True)
    write_attempt_record(cell_dir / "attempt.json", _record(attempt_dir="t-1"))
    _write_slot(night, 0, arm="engine", attempt_dir="t-1")
    record = _run_record(arm="baseline")
    with pytest.raises(UsageError, match="engine"):
        grade_night_sensitivity(night, record, tmp_path / "grades", grader=_ScriptedGrader({}))


# --- summarize / fisher_exact_greater / combine -----------------------------


def test_summarize_denominators_are_completed_cells_never_pooled() -> None:
    night = "n"
    from satyrn_evals.sensitivity_grade import CellSensitivity, SensitivityReport

    report = SensitivityReport(
        night=night,
        cells=(
            CellSensitivity(attempt="a1", task="t1", arm="baseline", code="OK", delivered_pass=True, delivered_pass_stripped=True),
            CellSensitivity(attempt="a2", task="t1", arm="baseline", code="OK", delivered_pass=False, delivered_pass_stripped=True, stripped_paths=("coverage.json",)),
            CellSensitivity(attempt="a3", task="t2", arm="baseline", code="OK", delivered_pass=False, delivered_pass_stripped=False),
        ),
    )
    groups = summarize(report)
    assert groups[("t1", "baseline")].n == 2
    assert groups[("t1", "baseline")].delivered_pass == 1
    assert groups[("t1", "baseline")].delivered_pass_stripped == 2
    assert groups[("t1", "baseline")].changed == ({"attempt": "a2", "stripped_paths": ["coverage.json"]},)
    assert groups[("t2", "baseline")].n == 1


def test_fisher_exact_greater_matches_the_known_3_of_3_vs_0_of_3_value() -> None:
    assert fisher_exact_greater(3, 3, 0, 3) == pytest.approx(0.05)


def test_fisher_exact_greater_matches_the_known_12_of_24_vs_6_of_24_value() -> None:
    """Computed independently here (not via the module under test): the
    one-sided hypergeometric tail P(X >= 12) with N=48, K=18, n=24."""
    import math

    n1, n0, k1, k0 = 24, 24, 12, 6
    population, successes = n1 + n0, k1 + k0
    expected = sum(
        math.comb(successes, x) * math.comb(population - successes, n1 - x)
        for x in range(k1, min(n1, successes) + 1)
    ) / math.comb(population, n1)
    assert fisher_exact_greater(k1, n1, k0, n0) == pytest.approx(expected)


def test_check_combinable_accepts_identical_task_rung_arm_budgets() -> None:
    a = _run_record(previous_result=None)
    b = _run_record(previous_result="records/x.result.json")
    check_combinable(a, b)  # no raise


def test_check_combinable_refuses_a_differing_field() -> None:
    a = _run_record(rung="R1")
    b = _run_record(rung="R1-plan")
    with pytest.raises(UsageError, match="rung"):
        check_combinable(a, b)


def test_combine_summaries_sums_matching_groups() -> None:
    from satyrn_evals.sensitivity_grade import GroupSummary

    a = {("t", "baseline"): GroupSummary(task="t", arm="baseline", n=3, delivered_pass=1, delivered_pass_stripped=2, changed=(), undelivered_tree={})}
    b = {("t", "baseline"): GroupSummary(task="t", arm="baseline", n=3, delivered_pass=0, delivered_pass_stripped=1, changed=(), undelivered_tree={})}
    combined = combine_summaries(a, b)
    assert combined[("t", "baseline")].n == 6
    assert combined[("t", "baseline")].delivered_pass == 1
    assert combined[("t", "baseline")].delivered_pass_stripped == 3


def test_render_report_includes_fisher_p_when_both_arms_present() -> None:
    from satyrn_evals.sensitivity_grade import GroupSummary

    groups = {
        ("t", "engine"): GroupSummary(task="t", arm="engine", n=3, delivered_pass=3, delivered_pass_stripped=3, changed=(), undelivered_tree={}),
        ("t", "baseline"): GroupSummary(task="t", arm="baseline", n=3, delivered_pass=0, delivered_pass_stripped=1, changed=(), undelivered_tree={}),
    }
    text = render_report([("A", groups)])
    assert "Fisher exact" in text
    assert "0.05" in text


def test_render_report_names_the_paths_stripped_from_an_undelivered_tree() -> None:
    from satyrn_evals.sensitivity_grade import GroupSummary

    groups = {
        ("t", "baseline"): GroupSummary(
            task="t", arm="baseline", n=1, delivered_pass=0, delivered_pass_stripped=0, changed=(),
            undelivered_tree={"a1": {"verdict": "yes", "stripped_paths": ["coverage.json"]}},
        ),
    }
    text = render_report([("A", groups)])
    assert "held a passing tree: yes" in text
    assert "coverage.json" in text
