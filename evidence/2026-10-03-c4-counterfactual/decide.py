#!/usr/bin/env python3
"""C4: the finishing counterfactual's verdict on the C3 census.

Pre-registration: docs/superpowers/specs/2026-10-03-c4-finishing-counterfactual-rederive.md.
Reads classify.py's per-cell rows, each night's summary.json admission, and (for the two
beside counts of section 2, which never decide) each cell's transcript, read-only; one run.
"""
from __future__ import annotations
import argparse, json, math, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
from satyrn_evals.budget import UsageCounter
from satyrn_evals.cell_evidence import _events
from satyrn_evals.confinement import Protected, _reaches, audit, finding, protected
from satyrn_evals.manifest import resolve_task

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[1]
DECIDING = ("selfhost-run-record-gate", "selfhost-docs-linter", "selfhost-preflight-quiet",
            "agentclinic-repair-depth-3", "selfhost-cell-loop")  # D6
OUTSIDE = ("selfhost-speed-probe",)                              # D6: reported only
READINGS = ("run2", "run1")                                      # D3: first decides
FILE_TOOLS = ("read", "edit", "write")


@dataclass(frozen=True, slots=True)
class Tally:
    task: str
    admitted: int
    not_pass_at_line: int
    rescues: int
    harms: int
    unmeasured: int

    @property
    def net(self) -> int:
        return self.rescues - self.harms

    @property
    def budget_shaped(self) -> bool:  # D5
        return self.admitted >= 3 and self.not_pass_at_line >= math.ceil(self.admitted / 2)

    @property
    def insufficient(self) -> bool:  # section 4, plus D5's admitted floor
        return self.admitted < 3 or self.unmeasured > 1


def change(row: dict, reading: str) -> str:
    """D3: both readings withhold on a fidelity failure or a raise; run 1 on any reason."""
    reasons = row["unmeasured"] or []
    if row["raised"] or any(r.startswith(("fidelity:", "raised:")) for r in reasons):
        return "unmeasured"
    return "unmeasured" if reading == "run1" and reasons else row[reading]["change"]


def tally(task: str, rows: list[dict], admitted: dict[str, bool], reading: str) -> Tally:
    mine = [r for r in rows if admitted.get(r["attempt"]) is True]  # D4
    changes = [change(r, reading) for r in mine]
    return Tally(task, len(mine), sum(1 for r in mine if not r["actual_32k"]),
                 changes.count("rescue"), changes.count("harm"), changes.count("unmeasured"))


def decide(tallies: list[Tally]) -> tuple[str, str]:
    """2026-09-15 pre-registration section 5 with amendment 7.1; kinds from D5."""
    budget = [t for t in tallies if t.budget_shaped]
    floor = [t for t in tallies if not t.budget_shaped]
    qualifying = [t.task for t in budget if not t.insufficient and t.net >= 1]
    harm = sum(t.harms for t in floor)
    thin = [t.task for t in floor if t.insufficient]
    detail = f"budget-shaped {[t.task for t in budget]}; qualifying {qualifying}; floor harm {harm}; insufficient floor {thin}"
    if len(qualifying) >= 2 and harm < 2 and not thin:
        return "go", detail
    if qualifying:
        return "verify", detail
    if all(t.net < 1 for t in budget):
        return "not-the-lever", detail
    return "verify", detail + "; a budget-shaped task has net >= 1 but is insufficient (7.1)"


# --- section 2's beside counts: reported per task, never an input to tally or decide ---

def _refusals(events: list[dict]) -> list[tuple[int, dict]]:
    """(event index, entry.data) of each confinement_refused entry, by finding()'s predicate."""
    return [(i, e["entry"].get("data") if isinstance(e["entry"].get("data"), dict) else {})
            for i, e in enumerate(events)
            if e.get("type") == "entry_appended" and isinstance(e.get("entry"), dict)
            and e["entry"].get("customType") == "confinement_refused"]


def _turn_at(events: list[dict], index: int) -> int:
    """The number of turn_start events at or before ``index`` (budget.UsageCounter's count)."""
    usage = UsageCounter()
    for event in events[: index + 1]:
        usage.feed_event(event)
    return usage.turns


def flagged_after_trigger(text: str, terms: Protected, own_green_turn: int | None) -> bool:
    """Flagged, a trigger turn, and the earlier of the first refusal and the first counted
    reach (in-worktree reaches ignored, as finding() ignores them) falls after it."""
    cell = finding(text, protected_=terms)
    if cell is None or cell.admitted or own_green_turn is None:
        return False
    events = _events(text)
    first = min([i for i, _ in _refusals(events)]
                + [r.index for r in audit(text, protected_=terms) if not r.in_worktree])
    return _turn_at(events, first) > own_green_turn


def only_non_protected_refusals(text: str, terms: Protected) -> bool:
    """Reaches 0, refusals >= 1, and every refusal a file tool with a string path that
    reaches no protected term from the first event's cwd. A bash refusal never qualifies."""
    cell = finding(text, protected_=terms)
    if cell is None or cell.reaches != 0 or cell.refusals < 1:
        return False
    events = _events(text)
    cwd = events[0].get("cwd") if isinstance(events[0].get("cwd"), str) else None
    return all(data.get("toolName") in FILE_TOOLS and isinstance(data.get("path"), str)
               and _reaches(data["path"], cwd, terms) is None for _, data in _refusals(events))


def beside(rows: list[dict], texts: dict[str, str], admitted: dict[str, bool], terms: Protected) -> tuple[list[str], list[str]]:
    """One task's two counts as attempt lists. Refuses when a transcript's admission
    disagrees with summary.json's confinement_admitted."""
    green = {r["attempt"]: r["own_green_turn"] for r in rows}
    after, scratch = [], []
    for attempt, text in sorted(texts.items()):
        cell = finding(text, protected_=terms)
        if (cell is not None and cell.admitted) is not (admitted.get(attempt) is True):
            raise ValueError(f"attempt {attempt}: transcript admission disagrees with summary.json")
        if flagged_after_trigger(text, terms, green.get(attempt)):
            after.append(attempt)
        if only_non_protected_refusals(text, terms):
            scratch.append(attempt)
    return after, scratch


def render(per_task: dict[str, tuple[list[dict], dict[str, bool]]],
           side: dict[str, tuple[list[str], list[str]]]) -> tuple[list[str], list[str]]:
    """decision.txt and table.md lines. Verdicts read rows and admission only; ``side`` is appended."""
    lines, table = [], ["| reading | task | admitted | not-pass@line | kind | rescues | harms | net | unmeasured | insufficient |", "|" + "---|" * 10]
    for reading in READINGS:
        tallies = []
        for task in DECIDING + OUTSIDE:
            rows, admitted = per_task[task]
            t = tally(task, rows, admitted, reading)
            tallies.append(t)
            kind = "outside" if task in OUTSIDE else ("budget-shaped" if t.budget_shaped else "floor")
            table.append(f"| {reading} | {task} | {t.admitted} | {t.not_pass_at_line} | {kind} | {t.rescues} | {t.harms} | {t.net} | {t.unmeasured} | {t.insufficient} |")
        verdict, detail = decide([t for t in tallies if t.task in DECIDING])
        lines.append(f"{reading}{' (deciding)' if reading == READINGS[0] else ' (beside)'}: {verdict}\n  {detail}")
    lines.append("beside counts (pre-registration section 2; never decide):")
    table += ["", "| task | flagged after trigger | cells | flagged only by non-protected refusals | cells |", "|---|---|---|---|---|"]
    for task, (after, scratch) in side.items():
        lines.append(f"  {task}: flagged after trigger {len(after)} {after}; non-protected refusals only {len(scratch)} {scratch}")
        table.append(f"| {task} | {len(after)} | {', '.join(after) or '-'} | {len(scratch)} | {', '.join(scratch) or '-'} |")
    return lines, table


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="decide.py")
    p.add_argument("--census", type=Path, required=True, help="evidence/<c3-date>-c3-census")
    p.add_argument("--c1-date", required=True)
    p.add_argument("--runs-root", type=Path, default=Path.home() / "satyrn-runs")
    a = p.parse_args(argv)
    if (HERE / "decision.txt").exists():
        print("decide: decision.txt exists; the pre-registration allows one run", file=sys.stderr)
        return 2
    git = lambda *x: subprocess.run(["git", *x], cwd=EVALS, capture_output=True, text=True).stdout.strip()
    stamp = f"evals {git('rev-parse', 'HEAD')} dirty={bool(git('status', '--porcelain', '--', 'src', 'evidence'))} argv={argv}"
    per_task, side = {}, {}
    for task in DECIDING + OUTSIDE:
        night = a.runs_root / f"{a.c1_date}-c1-{task}" / "baseline"
        rows = json.loads((a.census / task / "cells.json").read_text())["cells"]
        blocks = json.loads((night / "summary.json").read_text())["evidence"] or {}
        admitted = {name.rsplit("-", 1)[-1]: block.get("confinement_admitted") is True for name, block in blocks.items()}
        per_task[task] = (rows, admitted)
        task_dir = resolve_task(task)
        texts = {name.rsplit("-", 1)[-1]: (night / name / "transcript.txt").read_text()
                 for name, block in blocks.items() if block.get("transcript") is True}
        try:
            side[task] = beside(rows, texts, admitted, protected(task_dir.parent, task_dir.name))
        except ValueError as exc:
            print(f"decide: {task}: {exc}; nothing written", file=sys.stderr)
            return 2
    lines, table = render(per_task, side)
    (HERE / "table.md").write_text(f"<!-- {stamp} -->\n\n" + "\n".join(table) + "\n")
    (HERE / "decision.txt").write_text(f"# {stamp}\n" + "\n".join(lines) + "\n")
    print((HERE / "decision.txt").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
