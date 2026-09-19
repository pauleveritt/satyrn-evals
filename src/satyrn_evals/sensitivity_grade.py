"""``satyrn-evals grade-sensitivity``: the pre-registered sensitivity
reading for a comparison night, offline.

The frozen comparison records
(``records/2026-09-21-comparison-selfhost-run-record-gate-a.json``'s
``decision_rule``; read, never modified) pre-register, on both arms: "the
same count after stripping from each patch every path the grader itself
names in a 'patch touches non-source path' refusal, repeated until the
grader accepts or names none, then graded unchanged."

Two columns per completed cell:

- ``delivered_pass``: code OK and verdict pass, exactly as recorded --
  never changed by this tool. This is the decision rule's own primary
  reading.
- ``delivered_pass_stripped``: for a cell with code OK whose verdict is
  ``unavailable`` because the grader itself named a non-source path, strip
  that path's whole file-diff and re-grade, repeating while the grader
  names another non-source path (hard cap ``MAX_STRIP_ROUNDS``). A cell
  already pass or fail is unchanged; a cell with no patch (not code OK)
  stays not delivered.

Plus one informational column, never pooled into either delivered count:
``undelivered_tree``, the same strip-and-grade applied to a BUDGET_EXCEEDED
cell's tripped patch (the candidate in flight when the budget tripped --
never a delivered candidate), reported as "held a passing tree: yes/no/
unavailable".

Enumeration is ``line_grade.iter_finished_cells``, the same walk
``grade_night`` uses -- never reimplemented here. Stripping a path is
``patch.drop_ignored`` (already lifted for exactly this: dropping a
``diff --git`` section by the paths it touches), applied to one path at a
time so each round's grade reflects exactly one fewer refusal. Grading is
``line_grade.grade_offline`` -- the same offline call ``grade_night`` uses,
so ``delivered_pass`` and its sensitivity twin can never silently diverge in
method.

The Fisher exact one-sided test (Engine > Baseline) is computed exactly via
the hypergeometric tail (``math.comb``, ``fractions.Fraction`` -- no scipy).
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from satyrn_evals.attempt_record import AttemptCode, AttemptRecord
from satyrn_evals.errors import UsageError
from satyrn_evals.line_grade import (
    GradeCache,
    Grader,
    grade_offline,
    iter_finished_cells,
    make_grader,
)
from satyrn_evals.patch import drop_ignored
from satyrn_evals.run_record import RunRecord
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import TRIPPED_PATCH_NAME

#: A round of stripping never repeats past this many refusals: a runaway
#: patch (or a grader bug that keeps naming a new path forever) must not
#: hang the report. 20 is far above any patch this harness has ever seen
#: touch outside its source paths.
MAX_STRIP_ROUNDS = 20

#: Same wording as `patch.check_allowlist`'s `PatchRejected` message. `\S+`
#: (not `.+$`) because `grade_offline`'s reason may carry a trailing
#: " (grade exited N)" (the Part 1 fix) after the path, and a patch path
#: never itself contains whitespace.
_NON_SOURCE_PATH_RE = re.compile(r"patch touches non-source path: (\S+)")


def _extract_non_source_path(reason: str) -> str | None:
    match = _NON_SOURCE_PATH_RE.search(reason)
    return match.group(1) if match else None


def strip_and_grade(
    task: str,
    patch_text: str,
    grade_root: Path,
    name_prefix: str,
    cache: GradeCache,
    grader: Grader,
    *,
    max_rounds: int = MAX_STRIP_ROUNDS,
) -> tuple[str, tuple[str, ...]]:
    """Grade ``patch_text``; while the verdict is ``unavailable`` because the
    grader named a non-source path, strip that path's whole file-diff
    (``patch.drop_ignored``, section-level -- never edits a hunk, and
    handles new files/deletions/renames/binary sections because it only
    ever removes or keeps a whole ``diff --git`` section) and grade again.

    Stops -- returning ``"unavailable"`` -- on a genuine unavailable (the
    reason does not name a non-source path), a path already stripped this
    round (a cycle the grader itself cannot resolve), a named path this
    patch does not actually touch (``drop_ignored`` drops nothing), or
    ``max_rounds`` reached. Returns ``(verdict, stripped_paths)``.
    """
    stripped: list[str] = []
    current = patch_text
    rounds = 0
    while True:
        result = grader(task, current, grade_root, f"{name_prefix}-r{rounds}", cache)
        verdict = result["verdict"]
        if verdict != "unavailable":
            return verdict, tuple(stripped)
        path = _extract_non_source_path(result.get("reason") or "")
        if path is None or path in stripped or rounds >= max_rounds:
            return "unavailable", tuple(stripped)
        new_patch, dropped = drop_ignored(current, (path,))
        if not dropped:
            return "unavailable", tuple(stripped)
        stripped.append(path)
        current = new_patch
        rounds += 1


@dataclass(frozen=True, slots=True)
class CellSensitivity:
    attempt: str
    task: str
    arm: str
    code: str
    #: code OK and verdict pass, exactly as recorded -- never changed.
    delivered_pass: bool
    #: Same as `delivered_pass` for a cell already pass/fail, or not
    #: delivered (no patch / code not OK); for a code-OK cell whose verdict
    #: is unavailable, the strip-and-grade result.
    delivered_pass_stripped: bool
    stripped_paths: tuple[str, ...] = ()
    #: BUDGET_EXCEEDED only: "yes"/"no"/"unavailable" -- never counted in
    #: either delivered column. None for every other cell (not applicable:
    #: no tripped patch, because the cell was not BUDGET_EXCEEDED).
    undelivered_tree: str | None = None
    undelivered_tree_stripped_paths: tuple[str, ...] = ()

    def to_json(self) -> dict:
        return asdict(self)


def grade_cell_sensitivity(
    record: AttemptRecord,
    *,
    cell_dir: Path,
    arm: str,
    grade_root: Path,
    cache: GradeCache,
    grader: Grader = grade_offline,
) -> CellSensitivity:
    """One cell's sensitivity row (design in this module's docstring)."""
    name = cell_dir.name
    delivered_pass = record.code is AttemptCode.OK and record.verdict is Verdict.PASS
    stripped_paths: tuple[str, ...] = ()

    if record.code is not AttemptCode.OK or record.patch_path is None:
        # Not delivered: no patch to re-grade, stays not delivered in both
        # columns (never re-graded).
        delivered_pass_stripped = False
    elif record.verdict in (Verdict.PASS, Verdict.FAIL):
        # Already decided: unchanged, never re-graded.
        delivered_pass_stripped = delivered_pass
    else:
        patch_path = cell_dir / record.patch_path
        patch_text = patch_path.read_text() if patch_path.is_file() else ""
        if not patch_text.strip():
            delivered_pass_stripped = False
        else:
            verdict, stripped_paths = strip_and_grade(
                record.task, patch_text, grade_root, f"{name}-delivered", cache, grader
            )
            delivered_pass_stripped = verdict == "pass"

    undelivered_tree: str | None = None
    undelivered_tree_stripped_paths: tuple[str, ...] = ()
    if record.code is AttemptCode.BUDGET_EXCEEDED:
        tripped_path = cell_dir / TRIPPED_PATCH_NAME
        tripped_text = tripped_path.read_text() if tripped_path.is_file() else ""
        if not tripped_text.strip():
            undelivered_tree = "unavailable"
        else:
            verdict, undelivered_tree_stripped_paths = strip_and_grade(
                record.task, tripped_text, grade_root, f"{name}-tripped", cache, grader
            )
            undelivered_tree = "yes" if verdict == "pass" else ("no" if verdict == "fail" else "unavailable")

    return CellSensitivity(
        attempt=name,
        task=record.task,
        arm=arm,
        code=record.code.value,
        delivered_pass=delivered_pass,
        delivered_pass_stripped=delivered_pass_stripped,
        stripped_paths=stripped_paths,
        undelivered_tree=undelivered_tree,
        undelivered_tree_stripped_paths=undelivered_tree_stripped_paths,
    )


@dataclass(frozen=True, slots=True)
class SensitivityReport:
    night: str
    cells: tuple[CellSensitivity, ...]

    def to_json(self) -> dict:
        return {"night": self.night, "cells": [cell.to_json() for cell in self.cells]}


def grade_night_sensitivity(
    night: Path,
    record: RunRecord,
    grade_root: Path,
    *,
    tasks_root: Path | None = None,
    grader: Grader | None = None,
) -> SensitivityReport:
    """Every finished cell of ``night`` (``iter_finished_cells``, the same
    walk ``grade_night`` uses), graded for sensitivity."""
    if grader is None:
        grader = make_grader(tasks_root)
    cache: GradeCache = {}
    cells = [
        grade_cell_sensitivity(
            cell.record, cell_dir=cell.cell_dir, arm=cell.arm, grade_root=grade_root, cache=cache, grader=grader
        )
        for cell in iter_finished_cells(night, record)
    ]
    return SensitivityReport(night=os.fspath(night), cells=tuple(cells))


@dataclass(frozen=True, slots=True)
class GroupSummary:
    """One (task, arm)'s counts: denominator is completed cells, never
    pooled across tasks or arms."""

    task: str
    arm: str
    n: int
    delivered_pass: int
    delivered_pass_stripped: int
    #: Cells whose delivered_pass/delivered_pass_stripped disagree, with the
    #: paths stripped to get there.
    changed: tuple[dict, ...]
    #: attempt -> {"verdict": "yes"/"no"/"unavailable", "stripped_paths": [...]},
    #: BUDGET_EXCEEDED cells only.
    undelivered_tree: dict[str, dict]

    def to_json(self) -> dict:
        return asdict(self)


def summarize(report: SensitivityReport) -> dict[tuple[str, str], GroupSummary]:
    """Per (task, arm) group summary, denominators never pooled."""
    groups: dict[tuple[str, str], list[CellSensitivity]] = {}
    for cell in report.cells:
        groups.setdefault((cell.task, cell.arm), []).append(cell)
    summary: dict[tuple[str, str], GroupSummary] = {}
    for (task, arm), cells in groups.items():
        changed = tuple(
            {"attempt": cell.attempt, "stripped_paths": list(cell.stripped_paths)}
            for cell in cells
            if cell.delivered_pass != cell.delivered_pass_stripped
        )
        undelivered_tree = {
            cell.attempt: {"verdict": cell.undelivered_tree, "stripped_paths": list(cell.undelivered_tree_stripped_paths)}
            for cell in cells
            if cell.undelivered_tree is not None
        }
        summary[(task, arm)] = GroupSummary(
            task=task,
            arm=arm,
            n=len(cells),
            delivered_pass=sum(cell.delivered_pass for cell in cells),
            delivered_pass_stripped=sum(cell.delivered_pass_stripped for cell in cells),
            changed=changed,
            undelivered_tree=undelivered_tree,
        )
    return summary


def fisher_exact_greater(k1: int, n1: int, k0: int, n0: int) -> float:
    """One-sided exact p-value that arm 1 (Engine) beats arm 0 (Baseline):
    P(X >= k1) under the hypergeometric distribution with population
    N = n1 + n0, K = k1 + k0 successes, n1 draws -- the standard one-sided
    Fisher exact test on a 2x2 table, computed exactly (``math.comb`` +
    ``fractions.Fraction``; no scipy)."""
    if not (0 <= k1 <= n1 and 0 <= k0 <= n0):
        raise ValueError("fisher_exact_greater: k must sit within 0..n")
    population = n1 + n0
    successes = k1 + k0
    denominator = math.comb(population, n1)
    total = Fraction(0)
    for x in range(k1, min(n1, successes) + 1):
        total += Fraction(math.comb(successes, x) * math.comb(population - successes, n1 - x))
    return float(total / denominator)


#: Fields that must agree for two parts to be summed together (the
#: decision rule: "identical in task, rung, arms, model, engine commit,
#: budgets and machine"; engine commit/machine are not RunRecord fields, so
#: this checks what the record itself carries).
_COMBINE_FIELDS = ("task", "rung", "arm", "model", "token_budget", "turn_budget")


def check_combinable(a: RunRecord, b: RunRecord) -> None:
    """Refuse combining two parts that are not the same task/rung/arms/
    budgets, naming the differing field."""
    for field_name in _COMBINE_FIELDS:
        value_a, value_b = getattr(a, field_name), getattr(b, field_name)
        if value_a != value_b:
            raise UsageError(
                f"grade-sensitivity --combine: parts differ in {field_name}: {value_a!r} vs {value_b!r}"
            )


def combine_summaries(
    a: dict[tuple[str, str], GroupSummary], b: dict[tuple[str, str], GroupSummary]
) -> dict[tuple[str, str], GroupSummary]:
    """Sum two parts' per-(task, arm) summaries. Caller must have already
    called ``check_combinable`` on the underlying records."""
    combined: dict[tuple[str, str], GroupSummary] = {}
    for key in set(a) | set(b):
        left = a.get(key)
        right = b.get(key)
        task, arm = key
        if left is None:
            combined[key] = right  # type: ignore[assignment]
            continue
        if right is None:
            combined[key] = left
            continue
        combined[key] = GroupSummary(
            task=task,
            arm=arm,
            n=left.n + right.n,
            delivered_pass=left.delivered_pass + right.delivered_pass,
            delivered_pass_stripped=left.delivered_pass_stripped + right.delivered_pass_stripped,
            changed=left.changed + right.changed,
            undelivered_tree={**left.undelivered_tree, **right.undelivered_tree},
        )
    return combined


def _arm_pair(groups: dict[tuple[str, str], GroupSummary]) -> tuple[str, GroupSummary, GroupSummary] | None:
    """The (task, engine group, baseline group) when a night's groups hold
    exactly one task with both a "baseline" and an "engine" arm; else None
    (Fisher needs both arms of one task)."""
    by_task: dict[str, dict[str, GroupSummary]] = {}
    for (task, arm), group in groups.items():
        by_task.setdefault(task, {})[arm] = group
    for task, arms in by_task.items():
        if "baseline" in arms and "engine" in arms:
            return task, arms["engine"], arms["baseline"]
    return None


def render_markdown(label: str, groups: dict[tuple[str, str], GroupSummary]) -> list[str]:
    """Markdown lines for one part's (or combined) summary: a table with
    denominators never pooled, the changed-cell list, and the exact
    one-sided Fisher p (Engine > Baseline) for both columns when the group
    holds both arms of one task."""
    lines = [f"## {label}", "", "| task | arm | delivered_pass | delivered_pass_stripped |", "| --- | --- | --- | --- |"]
    for task, arm in sorted(groups):
        group = groups[(task, arm)]
        lines.append(
            f"| {task} | {arm} | {group.delivered_pass}/{group.n} | {group.delivered_pass_stripped}/{group.n} |"
        )
    lines.append("")
    pair = _arm_pair(groups)
    if pair is not None:
        task, engine, baseline = pair
        p_primary = fisher_exact_greater(engine.delivered_pass, engine.n, baseline.delivered_pass, baseline.n)
        p_stripped = fisher_exact_greater(
            engine.delivered_pass_stripped, engine.n, baseline.delivered_pass_stripped, baseline.n
        )
        lines.append(f"Fisher exact, one-sided (Engine > Baseline), {task}:")
        lines.append(f"- delivered_pass: p = {p_primary:.6g}")
        lines.append(f"- delivered_pass_stripped: p = {p_stripped:.6g}")
        lines.append("")
    changed = [
        (task, arm, entry)
        for (task, arm), group in sorted(groups.items())
        for entry in group.changed
    ]
    lines.append("cells whose count changed with paths stripped:")
    if changed:
        lines.extend(
            f"- {task}/{arm} {entry['attempt']}: stripped {entry['stripped_paths']}"
            for task, arm, entry in changed
        )
    else:
        lines.append("(none)")
    lines.append("")
    lines.append(
        "undelivered_tree (informational; NEVER added to either delivered count -- "
        "BUDGET_EXCEEDED cells only, the tripped patch was never a delivered candidate):"
    )
    tree_rows = [
        (task, arm, attempt, entry["verdict"], entry["stripped_paths"])
        for (task, arm), group in sorted(groups.items())
        for attempt, entry in sorted(group.undelivered_tree.items())
    ]
    if tree_rows:
        lines.extend(
            f"- {task}/{arm} {attempt}: held a passing tree: {verdict}"
            + (f" (stripped {stripped_paths})" if stripped_paths else "")
            for task, arm, attempt, verdict, stripped_paths in tree_rows
        )
    else:
        lines.append("(none)")
    return lines


def render_report(parts: list[tuple[str, dict[tuple[str, str], GroupSummary]]]) -> str:
    """Markdown for one or more labeled parts (``[("A", summary)]`` or, with
    ``--combine``, ``[("A", ...), ("B", ...), ("A+B", combined)]``)."""
    lines = ["# grade-sensitivity", ""]
    for label, groups in parts:
        lines.extend(render_markdown(label, groups))
        lines.append("")
    return "\n".join(lines)


def default_out_path(grade_root: Path, night: Path) -> Path:
    return grade_root / f"grade-sensitivity-{night.name}.json"


def write_report(report: SensitivityReport, out_path: Path) -> None:
    out_path.write_text(json.dumps(report.to_json(), indent=2) + "\n", encoding="utf-8")
