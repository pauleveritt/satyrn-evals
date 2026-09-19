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
from pathlib import Path

from satyrn_evals.attempt_record import AttemptRecord, load_attempt_record
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
    subprocess.run(
        argv,
        cwd=folder,
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "UV_OFFLINE": "1", "TMPDIR": os.fspath(folder)},
    )
    receipt = json.loads((folder / "receipt.json").read_text())
    result = {"verdict": receipt["verdict"], "reason": (receipt.get("reason") or "")[:200]}
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

    def to_json(self) -> dict:
        return asdict(self)


def grade_cell(
    record: AttemptRecord,
    *,
    cell_dir: Path,
    arm: str,
    grade_root: Path,
    cache: GradeCache,
    grader: Grader = grade_offline,
) -> LineGradeRow:
    """One cell's row: the tripped verdict (if it tripped) and the new
    ``line_verdict``/``line_source``, following the rule set in the design:

    - never crossed the line -> the cell's final verdict (pass/fail), or
      ``not-pass`` when it was refused with none; ``line_source: "final"``.
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

    if record.line_crossed is None:
        line_source = "final"
        line_verdict = (
            record.verdict.value if record.verdict in (Verdict.PASS, Verdict.FAIL) else "not-pass"
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
                attempt_record, cell_dir=cell_dir, arm=arm, grade_root=grade_root, cache=cache, grader=grader
            )
        )
    return LineGradeReport(night=os.fspath(night), rows=tuple(rows))


def render_summary(report: LineGradeReport) -> str:
    """Per-(task, arm) ``line_verdict == "pass"`` counts with denominators,
    never pooled, plus the cells whose harvested line verdict is
    ``unavailable``."""
    counts: dict[tuple[str, str], list[int]] = {}
    unavailable: list[str] = []
    for row in report.rows:
        key = (row.task, row.arm)
        entry = counts.setdefault(key, [0, 0])
        entry[1] += 1
        if row.line_verdict == "pass":
            entry[0] += 1
        if row.line_verdict == "unavailable":
            unavailable.append(row.attempt)
    lines = [f"# grade-line: {report.night}", "", "| task | arm | line pass |", "| --- | --- | --- |"]
    for (task, arm), (passed, total) in sorted(counts.items()):
        lines.append(f"| {task} | {arm} | {passed}/{total} |")
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
