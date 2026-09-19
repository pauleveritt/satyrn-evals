"""``satyrn-evals grade-line``: grade every completed cell's harvested
declared-line patch of a night offline against the hidden suite.

One row per completed cell (``attempt``, ``arm``, ``code``, ``verdict``,
``tripped_verdict``, ``line_crossed``, and the new ``line_verdict``/
``line_source``), plus a per-(task, arm) pass count -- never pooled across
tasks or arms.

Enumeration reuses ``launch.read_slots`` and ``attempt_record.
load_attempt_record``, the same readers ``launch_record.write_arm_summaries``
uses to walk a night's finished slots
(``src/satyrn_evals/launch_record.py:279-292``); nothing here re-implements
that walk.

``line_verdict`` grades the raw tree at the crossing on both arms; an
Engine cell's final verdict grades its delivered candidate, whose carried
tests the Engine restores.

A broken record -- a cell whose ``AttemptCode`` is not classified in
``_NEVER_CROSSED_RULES``, or a ``BUDGET_EXCEEDED`` cell that never crossed a
declared line (impossible, since the line budget sits strictly below the
attempt budget) -- never aborts the night's report (the F5 failure mode).
It becomes a per-cell ``line_verdict: "unavailable"`` row with a named
``line_unavailable_reason``, excluded from the pass denominator like any
other unavailable cell but listed first, under its own heading, in
``render_summary``'s markdown. The CLI still writes the full report, then
exits ``LINE_GRADE_NEEDS_REVIEW_EXIT_CODE`` when any such row exists.

The offline grading mechanism -- write a reconstructed patch under a scratch
grade root outside any Python project, run ``satyrn-evals grade`` in a fresh
subprocess so the hidden suite's own pytest run can never collide with this
package's own pytest configuration, cache by task + patch digest -- is
lifted from ``evidence/2026-09-16-census/classify.py``'s ``_grade`` and
``project_markers`` (imported from
``evidence/2026-09-15-finishing-counterfactual/counterfactual.py``). Both are
frozen evidence, not a library: this module holds its own copy rather than
importing them, and ``PROVENANCE.md`` names the source. A tripped patch is
graded by exactly the same call as a harvested line patch, so the two verdict
columns can never silently diverge in method.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum, auto
from pathlib import Path

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptRecord,
    DeadlinePhase,
    load_attempt_record,
)
from satyrn_evals.errors import UsageError
from satyrn_evals.launch import read_slots
from satyrn_evals.run_record import RunRecord, record_arms
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import LINE_PATCH_NAME, TRIPPED_PATCH_NAME

#: Config files pytest could pick up from a grade root or any ancestor. Same
#: check as ``evidence/2026-09-15-finishing-counterfactual/counterfactual.py``'s
#: ``project_markers`` (also frozen evidence, so reproduced rather than
#: imported): a ``--grade-root`` under a Python project would run the hidden
#: suite with that project's own pytest settings.
PROJECT_MARKERS = ("pyproject.toml", "pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg", "conftest.py")

GradeCache = dict[str, dict]
#: (task, patch text, grade root, scratch-folder name, cache) -> {"verdict", "reason"}
Grader = Callable[[str, str, Path, str, GradeCache], dict]

#: `satyrn-evals grade-line`'s exit code when the night's report holds at
#: least one broken-record row (N5): an unclassified `AttemptCode`, or a
#: BUDGET_EXCEEDED cell that never crossed a declared line -- a contradiction
#: the harness itself could not explain. The full report is still written
#: and printed; this exit code is the only signal that a human must look at
#: it. Distinct from 0 (graded clean), 2 (usage error), 3 (operational
#: error, from `SatyrnError.exit_code`).
LINE_GRADE_NEEDS_REVIEW_EXIT_CODE = 4


def project_markers(path: Path) -> list[Path]:
    """Every pytest config file ``path`` or an ancestor of it holds."""
    return [
        folder / name
        for folder in (path, *path.parents)
        for name in PROJECT_MARKERS
        if (folder / name).is_file()
    ]


def grade_offline(
    task: str, patch: str, grade_root: Path, name: str, cache: GradeCache, *, tasks_root: Path | None = None
) -> dict:
    """``satyrn-evals grade`` on one reconstructed patch, cached by task + digest.

    Lifted from ``evidence/2026-09-16-census/classify.py``'s ``_grade``
    (PROVENANCE.md names the source), with one addition: an optional
    ``tasks_root``, passed on as ``--tasks-root`` when given, so this can
    grade against a non-bundled task root (e.g. the integration fixtures)
    without shelling out with the CLI's own default. The census never needed
    this -- its tasks are always the bundled ones. Callers must refuse a
    ``grade_root`` with any ``project_markers`` before reaching here -- this
    function does not check, so a caller that skips the check would run the
    hidden suite under whatever pytest config sits above ``grade_root``.
    """
    key = hashlib.sha256((task + "\0" + patch).encode()).hexdigest()
    if key in cache:
        return cache[key]
    folder = grade_root / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / "patch.diff").write_text(patch)
    argv = [os.fspath(Path(sys.executable).parent / "satyrn-evals"), "grade", task, "patch.diff"]
    if tasks_root is not None:
        argv += ["--tasks-root", os.fspath(tasks_root)]
    argv += ["--receipt", "receipt.json"]
    try:
        completed = subprocess.run(
            argv,
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=900,
            env={**os.environ, "UV_OFFLINE": "1", "TMPDIR": os.fspath(folder)},
        )
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip()[-500:]
            raise RuntimeError(f"grade exited {completed.returncode}: {tail}" if tail else f"grade exited {completed.returncode}")
        receipt = json.loads((folder / "receipt.json").read_text())
        result = {"verdict": receipt["verdict"], "reason": (receipt.get("reason") or "")[:200]}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError, RuntimeError) as exc:
        # A crashed grade, a missing receipt, or an unreadable one must never
        # raise out of here: the cell is unavailable, not a lost night's
        # report (F5). `grade_cell`/`grade_night` never catch this -- the
        # only well-formed outcome from a grader is a dict with a verdict.
        result = {"verdict": "unavailable", "reason": f"{type(exc).__name__}: {exc}"[:200]}
    cache[key] = result
    return result


def make_grader(tasks_root: Path | None) -> Grader:
    """A `Grader` bound to a fixed `tasks_root`, for `grade_night`'s default."""

    def grader(task: str, patch: str, grade_root: Path, name: str, cache: GradeCache) -> dict:
        return grade_offline(task, patch, grade_root, name, cache, tasks_root=tasks_root)

    return grader


@dataclass(frozen=True, slots=True)
class LineGradeRow:
    attempt: str
    task: str
    arm: str
    code: str
    verdict: str | None
    tripped_verdict: str | None
    line_crossed: dict | None
    line_verdict: str
    line_source: str
    line_harvest_error: str | None = None
    #: N5: set only for a broken-record cell (unclassified AttemptCode, or a
    #: BUDGET_EXCEEDED cell that never crossed a declared line) -- distinct
    #: from an ordinary `line_harvest_error`, and the reason a human needs to
    #: look at this cell specifically, surfaced at the top of the report.
    line_unavailable_reason: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


class _NeverCrossedRule(Enum):
    """How a never-crossed cell's ``line_verdict`` is derived from its
    ``AttemptCode``. Never a silent default (I3): every rule is named."""

    #: OK: the record's own pass/fail verdict; any other verdict (e.g. a
    #: receipt that itself came back UNAVAILABLE) falls back to "not-pass".
    MODEL_VERDICT = auto()
    #: The model's own outcome, with no patch to grade -- never infrastructure.
    NOT_PASS = auto()
    #: The cell measured nothing about the model: excluded from the pass
    #: denominator, reported separately, never scored as a model outcome.
    UNAVAILABLE = auto()
    #: DEADLINE_EXCEEDED: the command phase is the model's own stop (like
    #: COMMAND_TIMEOUT); every other phase is the harness's own overhead.
    DEADLINE = auto()
    #: BUDGET_EXCEEDED: cannot coexist with "never crossed" once a line is
    #: declared for this run -- the line budget is strictly below the
    #: attempt budget (`run_record.load_run_record`), so the line must trip
    #: first. A record shaped this way is broken, not merely unlucky.
    BUDGET = auto()


#: Every `AttemptCode` member, classified for the "never crossed the
#: declared line" case (`grade_cell`'s ``final`` branch). Pinned by
#: ``test_every_attempt_code_is_classified_for_the_never_crossed_case``:
#: a new code with no entry here is a bug, not a silent "not-pass"
#: (AGENTS.md: infrastructure stops, model outcomes never do).
_NEVER_CROSSED_RULES: dict[AttemptCode, _NeverCrossedRule] = {
    AttemptCode.OK: _NeverCrossedRule.MODEL_VERDICT,
    AttemptCode.NO_PATCH: _NeverCrossedRule.NOT_PASS,
    AttemptCode.COMMAND_TIMEOUT: _NeverCrossedRule.NOT_PASS,
    AttemptCode.REPEAT_LIMIT: _NeverCrossedRule.NOT_PASS,
    AttemptCode.BUDGET_EXCEEDED: _NeverCrossedRule.BUDGET,
    AttemptCode.PATCH_INVALID: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.TRANSCRIPT_MISSING: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.TRANSCRIPT_EMPTY: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.WORKSPACE_FAILED: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.MODEL_ERROR: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.CLEANUP_FAILED: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.GRADE_FAILED: _NeverCrossedRule.UNAVAILABLE,
    AttemptCode.DEADLINE_EXCEEDED: _NeverCrossedRule.DEADLINE,
}


def _never_crossed_verdict(
    code: AttemptCode,
    verdict: Verdict | None,
    deadline_phase: DeadlinePhase | None,
    *,
    line_declared: bool,
    name: str,
) -> tuple[str, str | None]:
    """The ``line_verdict`` for a cell that never crossed the declared line,
    plus a broken-record reason (N5) when the shape is a contradiction the
    harness itself cannot explain.

    Never raises: aborting the whole night's report on one broken cell is
    the exact failure mode the F5 fix removed for crashed grades. Instead,
    an unclassified ``AttemptCode`` (not in ``_NEVER_CROSSED_RULES``) or a
    ``BUDGET_EXCEEDED`` cell with a declared line that was somehow never
    crossed becomes ``("unavailable", <reason naming the cell and the
    contradiction>)`` -- excluded from the pass denominator like any other
    unavailable cell, but surfaced separately at the top of the report as
    needing a human look (``render_summary``), since neither shape is a
    normal outcome.
    """
    rule = _NEVER_CROSSED_RULES.get(code)
    if rule is None:
        return "unavailable", f"cell {name}: unclassified attempt code {code}"
    if rule is _NeverCrossedRule.MODEL_VERDICT:
        return (verdict.value if verdict in (Verdict.PASS, Verdict.FAIL) else "not-pass"), None
    if rule is _NeverCrossedRule.NOT_PASS:
        return "not-pass", None
    if rule is _NeverCrossedRule.UNAVAILABLE:
        return "unavailable", None
    if rule is _NeverCrossedRule.DEADLINE:
        return ("not-pass" if deadline_phase is DeadlinePhase.COMMAND else "unavailable"), None
    # rule is _NeverCrossedRule.BUDGET
    if line_declared:
        return "unavailable", (
            f"cell {name}: broken record: BUDGET_EXCEEDED without a line crossing -- "
            "the line budget is strictly below the attempt budget, so the line "
            "must trip first"
        )
    return "not-pass", None


def grade_cell(
    record: AttemptRecord,
    *,
    cell_dir: Path,
    arm: str,
    grade_root: Path,
    cache: GradeCache,
    grader: Grader = grade_offline,
    line_declared: bool = False,
) -> LineGradeRow:
    """One cell's row: the tripped verdict (if it tripped) and the new
    ``line_verdict``/``line_source``, following the rule set in the design:

    - never crossed the line -> ``_never_crossed_verdict`` classifies the
      cell's own ``AttemptCode`` explicitly (the model's final verdict, a
      model-side ``not-pass``, or an infrastructure ``unavailable`` --
      never guessed); ``line_source: "final"``. ``line_declared`` names
      whether this run declared a line at all, for the one code
      (``BUDGET_EXCEEDED``) that cannot coexist with "never crossed" once
      it has.
    - crossed the line -> grade ``line.diff`` offline; ``not-pass`` when the
      harvest wrote nothing (empty patch); ``line_source: "harvested"``.
    - a harvest error -> ``unavailable``, ``line_source: "harvested"``.
    """
    name = cell_dir.name
    tripped_verdict: str | None = None
    if record.tripped_patch_path is not None:
        tripped_path = cell_dir / TRIPPED_PATCH_NAME
        if tripped_path.is_file():
            tripped_verdict = grader(
                record.task, tripped_path.read_text(), grade_root, f"{name}-tripped", cache
            )["verdict"]

    line_crossed = None if record.line_crossed is None else asdict(record.line_crossed)

    line_unavailable_reason: str | None = None
    if record.line_crossed is None:
        line_source = "final"
        deadline_phase = record.deadline.phase if record.deadline is not None else None
        line_verdict, line_unavailable_reason = _never_crossed_verdict(
            record.code, record.verdict, deadline_phase, line_declared=line_declared, name=name
        )
    else:
        line_source = "harvested"
        if record.line_harvest_error is not None:
            line_verdict = "unavailable"
        else:
            line_path = cell_dir / LINE_PATCH_NAME
            text = (
                line_path.read_text()
                if record.line_patch_path is not None and line_path.is_file()
                else ""
            )
            if not text.strip():
                line_verdict = "not-pass"
            else:
                line_verdict = grader(record.task, text, grade_root, f"{name}-line", cache)["verdict"]

    return LineGradeRow(
        attempt=name,
        task=record.task,
        arm=arm,
        code=record.code.value,
        verdict=None if record.verdict is None else record.verdict.value,
        tripped_verdict=tripped_verdict,
        line_crossed=line_crossed,
        line_verdict=line_verdict,
        line_source=line_source,
        line_harvest_error=record.line_harvest_error,
        line_unavailable_reason=line_unavailable_reason,
    )


@dataclass(frozen=True, slots=True)
class LineGradeReport:
    night: str
    rows: tuple[LineGradeRow, ...]

    def to_json(self) -> dict:
        return {"night": self.night, "rows": [row.to_json() for row in self.rows]}


def grade_night(
    night: Path,
    record: RunRecord,
    grade_root: Path,
    *,
    tasks_root: Path | None = None,
    grader: Grader | None = None,
) -> LineGradeReport:
    """Every finished slot of ``night``, graded.

    Enumeration matches ``launch_record.write_arm_summaries``: ``read_slots``
    names each finished slot's ``arm``/``attempt_dir``; each cell's record is
    read with ``attempt_record.load_attempt_record``, never reimplemented.
    ``tasks_root`` (default: the bundled tasks) is ignored when ``grader`` is
    given explicitly, e.g. a test's fake.
    """
    if grader is None:
        grader = make_grader(tasks_root)
    finished = read_slots(night)
    known_arms = set(record_arms(record))
    line_declared = record.line_token_budget is not None
    cache: GradeCache = {}
    rows: list[LineGradeRow] = []
    for _index, slot in sorted(finished.items()):
        arm = slot["arm"]
        if arm not in known_arms:
            raise UsageError(
                f"grade-line: slot names arm {arm!r}, not among the record's {sorted(known_arms)}"
            )
        cell_dir = night / arm / slot["attempt_dir"]
        attempt_record = load_attempt_record(cell_dir / "attempt.json")
        rows.append(
            grade_cell(
                attempt_record, cell_dir=cell_dir, arm=arm, grade_root=grade_root, cache=cache,
                grader=grader, line_declared=line_declared,
            )
        )
    return LineGradeReport(night=os.fspath(night), rows=tuple(rows))


def render_summary(report: LineGradeReport) -> str:
    """Per-(task, arm) ``line_verdict == "pass"`` counts with denominators,
    never pooled, plus the cells whose harvested line verdict is
    ``unavailable``.

    An ``unavailable`` cell measured nothing about the model (I3): it is
    excluded from both sides of the pass fraction, and the number excluded
    is stated per (task, arm) -- not left implicit in the attempt list below.

    N5: a row with ``line_unavailable_reason`` set is a broken record (an
    unclassified ``AttemptCode``, or a BUDGET_EXCEEDED cell that never
    crossed a declared line) -- a contradiction the harness itself could not
    explain, not an ordinary unavailable cell. It is still excluded from the
    pass denominator like any other unavailable cell, but it is also listed
    first, at the very top of the report, under a heading that says a human
    needs to look, ahead of the per-(task, arm) table.
    """
    counts: dict[tuple[str, str], list[int]] = {}
    excluded: dict[tuple[str, str], int] = {}
    unavailable: list[str] = []
    needs_review: list[tuple[str, str]] = []
    for row in report.rows:
        key = (row.task, row.arm)
        if row.line_unavailable_reason is not None:
            needs_review.append((row.attempt, row.line_unavailable_reason))
        if row.line_verdict == "unavailable":
            excluded[key] = excluded.get(key, 0) + 1
            unavailable.append(row.attempt)
            continue
        entry = counts.setdefault(key, [0, 0])
        entry[1] += 1
        if row.line_verdict == "pass":
            entry[0] += 1
    lines = [
        f"# grade-line: {report.night}",
        "",
        "## NEEDS HUMAN REVIEW",
        "",
        "Each cell below is a broken record: its shape is a contradiction "
        "the harness itself could not explain (an unclassified attempt "
        "code, or a BUDGET_EXCEEDED cell that never crossed a declared "
        "line). It is excluded from the pass counts below like any other "
        "unavailable cell, but needs a human to look at it directly.",
        "",
    ]
    if needs_review:
        lines.extend(f"- {attempt}: {reason}" for attempt, reason in sorted(needs_review))
    else:
        lines.append("(none)")
    lines.append("")
    lines.append(
        "line_verdict grades the raw tree at the crossing on both arms; an "
        "Engine cell's final verdict grades its delivered candidate, whose "
        "carried tests the Engine restores."
    )
    lines.append("")
    lines.append("| task | arm | line pass | excluded (unavailable) |")
    lines.append("| --- | --- | --- | --- |")
    for key in sorted(set(counts) | set(excluded)):
        task, arm = key
        passed, total = counts.get(key, [0, 0])
        lines.append(f"| {task} | {arm} | {passed}/{total} | {excluded.get(key, 0)} |")
    lines.append("")
    lines.append("## unavailable")
    if unavailable:
        lines.extend(f"- {attempt}" for attempt in sorted(unavailable))
    else:
        lines.append("(none)")
    return "\n".join(lines)


def default_out_path(grade_root: Path, night: Path) -> Path:
    return grade_root / f"grade-line-{night.name}.json"


def write_report(report: LineGradeReport, out_path: Path) -> None:
    out_path.write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8")


def refuse_project_grade_root(grade_root: Path) -> None:
    if markers := project_markers(grade_root):
        raise UsageError(
            f"grade-line: --grade-root {grade_root} sits under a Python project "
            f"({', '.join(os.fspath(m) for m in markers)}); the hidden suite must "
            "grade under its own settings"
        )
