#!/usr/bin/env python3
"""The census night driver: one night directory and one record in, the classified
table, the section 6 offline fields and the finish-on-green counterfactual out.

Design section 7 of `2026-09-15-release-two-census-design.md`. This script is
night-specific and frozen beside its outputs; the pure rules it computes with
live in `satyrn_evals.census_classify`, and the pre-registered replay, own-green
and trigger rules are imported by path and unmodified from
`evidence/2026-09-15-finishing-counterfactual/counterfactual.py`, exactly as
`run-2/trajectory.py` already does (Ruling 7). Nothing here re-implements them:
the census reads the same instrument run 1 and run 2 read.

Read-only on `~/satyrn-runs` and on `evidence/2026-09-15-finishing-counterfactual/`.
Replay scratch lives under this directory's git-ignored ``work/``; grade receipts
under ``--grade-root`` (default ``$HOME/satyrn-census-grades``), never under a
Python project, because pytest reads the nearest ancestor config and every
ancestor conftest.py.

    uv run --project . python evidence/2026-09-16-census/classify.py \
        --night "$HOME/satyrn-runs/2026-09-16-census-selfhost-docs-linter" \
        --record records/2026-09-16-census-selfhost-docs-linter.json

Writes, per task, ``<out>/<task>/{cells.json,table.md,classes.md}``. The eight
class columns of ``classes.md`` are deliberately empty: a reviewer fills them
from the reconstruction, and the mechanical ``flags`` are printed beneath as the
evidence a class would be argued from.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from satyrn_evals import census_classify as cc
from satyrn_evals import census_decode as cd
from satyrn_evals.cell_evidence import HARNESS_CUT_CODES, collect_evidence
from satyrn_evals.errors import PatchParseError
from satyrn_evals.patch import drop_ignored, parse_patch_paths, within_source
from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[1]
SCRIPT = EVALS / "evidence/2026-09-15-finishing-counterfactual/counterfactual.py"
DEFAULT_GRADE_ROOT = Path.home() / "satyrn-census-grades"
#: `<task>-YYYYmmdd-HHMMSS-ffffff`, the attempt directory's name.
_STAMP = re.compile(r"-\d{8}-\d{6}-\d{6}\Z")

# Load the pre-registered instrument by path, unmodified (Ruling 7).
_spec = importlib.util.spec_from_file_location("cf", SCRIPT)
cf = importlib.util.module_from_spec(_spec)
sys.modules["cf"] = cf
_spec.loader.exec_module(cf)
cf.WORK = HERE / "work"

_GRADES: dict[str, dict] = {}


class Refused(ValueError):
    """A refusal: the night and the record do not belong together."""


@dataclass(frozen=True, slots=True)
class Cell:
    task: str
    night: str
    arm: str
    attempt: str  # the six-digit suffix
    attempt_dir: str
    folder: Path


def _task_of(slots: list[dict]) -> str | None:
    for slot in slots:
        attempt_dir = slot.get("attempt_dir")
        if isinstance(attempt_dir, str) and (match := _STAMP.search(attempt_dir)):
            return attempt_dir[: match.start()]
    return None


def _task_from_name(name: str) -> str:
    match = re.match(r"^\d{4}-\d{2}-\d{2}-[^-]+-(.+)$", name)
    return match.group(1) if match else name


def cells(night: Path, record: Path) -> list[Cell]:
    """The finished cells of ``night``, checked against ``record``.

    No hard-coded cell lists: the night's ``launch.json`` slots and the record
    are the arguments. Refuses a night whose ``record_sha256`` is not the given
    record's, and a record whose ``task`` is not the night's.
    """
    launch_path = night / "launch.json"
    if not launch_path.is_file():
        raise Refused(f"{night} has no launch.json")
    launch = json.loads(launch_path.read_text())
    if not record.is_file():
        raise Refused(f"no such record: {record}")
    record_sha = hashlib.sha256(record.read_bytes()).hexdigest()
    if launch.get("record_sha256") != record_sha:
        raise Refused(f"record {record} sha256 {record_sha} is not the night's {launch.get('record_sha256')}")
    body = json.loads(record.read_text())
    task = body.get("task")
    slots = launch.get("slots") or []
    night_task = _task_of(slots) or _task_from_name(night.name)
    if task != night_task:
        raise Refused(f"record task {task!r} is not the night's {night_task!r}")
    found: list[Cell] = []
    for slot in slots:
        attempt_dir = slot.get("attempt_dir")
        if not isinstance(attempt_dir, str) or not attempt_dir:
            continue
        folder = night / str(slot.get("arm")) / attempt_dir
        if not folder.is_dir():
            raise Refused(f"slot {slot.get('slot')} directory is missing: {folder}")
        found.append(
            Cell(
                task=task,
                night=night.name,
                arm=str(slot.get("arm")),
                attempt=attempt_dir.rsplit("-", 1)[-1],
                attempt_dir=attempt_dir,
                folder=folder,
            )
        )
    if not found:
        raise Refused(f"{night} has no finished slots")
    return found


def select(night: Path, record: Path, only: tuple[str, ...] = ()) -> list[Cell]:
    found = cells(night.resolve(), record.resolve())
    if not only:
        return found
    wanted = set(only)
    chosen = [c for c in found if c.attempt in wanted or c.attempt_dir in wanted]
    matched = {c.attempt for c in chosen} | {c.attempt_dir for c in chosen}
    missing = sorted(wanted - matched)
    if missing:
        raise Refused(f"--cell matches no slot: {', '.join(missing)}")
    return chosen


def _spec_of(cell: Cell) -> cf.CellSpec:
    # cf.replay guards its own debug phase by asserting a retained decision
    # attempt is only ever replayed as one. The census reuses the same
    # instrument outside that script, and the field is otherwise unused, so a
    # retained attempt keeps its label and every new cell is "census".
    group = "decision" if cell.attempt in cf.DECISION_IDS else "census"
    return cf.CellSpec(task=cell.task, run=cell.night, arm=cell.arm, attempt=cell.attempt, group=group)


def audit(cell: Cell, attempt: dict, bash_touched: dict[int, tuple[str, ...]]) -> dict:
    """run-2/audit.py's row, for this cell, with the package's per-turn count and
    the section 6 fields taken from `cell_evidence.collect_evidence`.

    Ruling R-5b: the source-edit route is the replay's ``bash_touched`` map, the
    same route the committed counterfactual's `measure` uses
    (`counterfactual.py:953`), so the census's exploration turns and edits are
    comparable with run 2's."""
    manifest = json.loads((cf.TASKS / cell.task / "manifest.json").read_text())
    sp = tuple(manifest["source_paths"])
    transcript = (cell.folder / "transcript.txt").read_text()
    events = cf.parse_events(transcript)
    cwd = cf.session_cwd(events)
    steps = cf.steps_of(events)
    timeline_path = cell.folder / "timeline.jsonl"
    evidence = collect_evidence(
        transcript,
        timeline=timeline_path.read_text() if timeline_path.is_file() else None,
        source_paths=sp,
        # A cell the harness stopped (a cut code with no command exit) leaves
        # an ``agent_end`` as tear-down residue, not a self-stop (Ruling R-3).
        # A normal-exit over-budget cell was not cut: its ``agent_end`` is a
        # genuine self-stop.
        cut=attempt.get("code") in HARNESS_CUT_CODES and attempt.get("command_exit") is None,
    ).to_block()
    edits = cf.source_edit_indices(steps, sp, cwd, bash_touched)
    first = (
        None
        if not edits
        else {
            "step": edits[0],
            "turn": steps[edits[0]].turn,
            "tokens": steps[edits[0]].output_tokens,
            "name": steps[edits[0]].name,
            "path": steps[edits[0]].args.get("path"),
        }
    )
    all_edits = [
        {"step": i, "turn": steps[i].turn, "name": steps[i].name, "path": cf.tree_path(steps[i].args.get("path", ""), cwd)}
        for i in range(len(steps))
        if steps[i].name in ("write", "edit") and not steps[i].is_error
    ]
    edit_errors = [
        {"step": s.index, "turn": s.turn, "name": s.name, "path": s.args.get("path")}
        for s in steps
        if s.name in ("write", "edit") and s.is_error
    ]
    runs = []
    for s in steps:
        if cf.is_test_run(s):
            cmd = s.args.get("command", "") if s.name == "bash" else "<self_test>"
            runs.append(
                {
                    "step": s.index,
                    "turn": s.turn,
                    "tokens": s.output_tokens,
                    "name": s.name,
                    "cmd": str(cmd)[:200],
                    "is_error": s.is_error,
                    "green": cf.is_green(s),
                    "summary": cf.summary_lines(s.text),
                    "after_first_edit": bool(edits) and s.index >= edits[0],
                    "text_tail": s.text[-300:],
                }
            )
    bashes = []
    for s in steps:
        if s.name == "bash":
            cmd = str(s.args.get("command", ""))
            plan = cf.plan_bash(cmd, cwd)
            bashes.append(
                {
                    "step": s.index,
                    "turn": s.turn,
                    "tokens": s.output_tokens,
                    "is_error": s.is_error,
                    "replayable": plan.replay is not None,
                    "read_only": cf.is_read_only_bash(cmd, cwd),
                    "verified": cf.bash_verified(s, cwd),
                    "could_write": cf.could_write_source(plan.remainder, sp, cwd) if plan.remainder else False,
                    "runs_pytest": cf.runs_pytest(cmd),
                    "cmd": cmd[:400],
                }
            )
    trigger = cf.find_trigger(steps, edits, cwd)
    return {
        "task": cell.task,
        "arm": cell.arm,
        "attempt": cell.attempt,
        "attempt_dir": cell.attempt_dir,
        "code": attempt.get("code"),
        "verdict": attempt.get("verdict"),
        # Both are the driver's to fill after the audit: the record no longer
        # carries a tripped verdict (Ruling R-1), and the allowlist reason
        # comes only from a filtered pass (Ruling R-4).
        "tripped_verdict": None,
        "allowlist_reason": None,
        "cwd": cwd,
        "first_source_edit": first,
        "all_edits": all_edits,
        "edit_errors": edit_errors,
        "test_runs": runs,
        "bash": bashes,
        "trigger_no_bash_replay": (
            None
            if trigger is None
            else {
                "step": trigger.step,
                "turn": trigger.turn,
                "tokens": trigger.output_tokens,
                "route": trigger.route,
                "within_budget": trigger.within_budget,
            }
        ),
        "turns": [asdict(row) for row in cc.per_turn(events)],
        "evidence": evidence,
        "whole_attempt_seconds": cc.whole_attempt_seconds(
            cell.attempt_dir, (cell.folder / "attempt.json").stat().st_mtime
        ),
    }


def _empty_evidence() -> dict:
    return {
        "turns": 0,
        "output_tokens": 0,
        "length_stops": 0,
        "root_searches": 0,
        "tool_reported_timeouts": 0,
        "exploration_turns": None,
        "biggest_turn": None,
        "tool_span_seconds": None,
        "self_stop": None,
    }


def _empty_audit(cell: Cell, attempt: dict) -> dict:
    return {
        "task": cell.task,
        "arm": cell.arm,
        "attempt": cell.attempt,
        "attempt_dir": cell.attempt_dir,
        "code": attempt.get("code"),
        "verdict": attempt.get("verdict"),
        # Consistent with `audit`: the driver fills both after the audit.
        "tripped_verdict": None,
        "allowlist_reason": None,
        "cwd": None,
        "first_source_edit": None,
        "all_edits": [],
        "edit_errors": [],
        "test_runs": [],
        "bash": [],
        "trigger_no_bash_replay": None,
        "turns": [],
        "evidence": _empty_evidence(),
        "whole_attempt_seconds": None,
    }


def _snapshot_replay(cell: Cell, steps: list, cwd: str | None) -> dict[int, str]:
    """run-2/trajectory.py's std replay: one worktree, a patch at the end of every
    turn. The `ext` replay is not carried over -- it executed model-written Python,
    which needs its own review, and the census's question is answered here."""
    work = cf.WORK / f"{cell.attempt}-std"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(cf.TASKS / cell.task / "base", work, symlinks=True)
    cf._git(work, "init", "-q")
    cf._git(work, "add", "-A")
    cf._git(work, "-c", "user.email=replay@localhost", "-c", "user.name=replay", "commit", "-q", "-m", "base")
    base = cf._git(work, "rev-parse", "HEAD").strip()
    snapshots: dict[int, str] = {}
    current: int | None = None

    def snap(turn: int) -> None:
        tempfile.tempdir = os.fspath(cf.WORK)
        snapshots[turn] = build_cumulative_patch(work, base, os.environ, exclude=RESIDUE_EXCLUDES).patch_text

    try:
        for step in steps:
            if current is not None and step.turn != current:
                snap(current)
            current = step.turn
            if step.name == "write" and not step.is_error:
                path = cf.tree_path(step.args.get("path", ""), cwd)
                if path is not None:
                    target = work / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(str(step.args.get("content", "")))
            elif step.name == "edit" and not step.is_error:
                path = cf.tree_path(step.args.get("path", ""), cwd)
                if path is None:
                    continue
                target = work / path
                edits = step.args.get("edits") or (
                    [{"oldText": step.args.get("oldText", ""), "newText": step.args.get("newText", "")}]
                    if step.args.get("oldText")
                    else []
                )
                text = target.read_text() if target.is_file() else None
                for edit in edits:
                    old, new = str(edit.get("oldText", "")), str(edit.get("newText", ""))
                    if text is not None and old and old in text:
                        text = text.replace(old, new, 1)
                if text is not None:
                    target.write_text(text)
            elif step.name == "bash":
                command = str(step.args.get("command", ""))
                plan = cf.plan_bash(command, cwd)
                if plan.replay is not None:
                    subprocess.run(
                        ["/bin/bash", "-c", plan.replay],
                        cwd=work,
                        capture_output=True,
                        timeout=10,
                        env={"PATH": os.environ["PATH"], "HOME": os.fspath(work), "TMPDIR": os.fspath(cf.WORK)},
                    )
        if current is not None:
            snap(current)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return snapshots


def _grade(task: str, patch: str, grade_root: Path, name: str) -> dict:
    """`satyrn-evals grade` on one reconstructed patch, cached by task + digest.

    A grade root under a Python project would run the hidden suite with the
    project's pytest settings, so `main` refuses one with any `cf.project_markers`.
    """
    key = hashlib.sha256((task + "\0" + patch).encode()).hexdigest()
    if key in _GRADES:
        return _GRADES[key]
    folder = grade_root / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / "patch.diff").write_text(patch)
    subprocess.run(
        [os.fspath(Path(sys.executable).parent / "satyrn-evals"), "grade", task, "patch.diff", "--receipt", "receipt.json"],
        cwd=folder,
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "UV_OFFLINE": "1", "TMPDIR": os.fspath(folder)},
    )
    receipt = json.loads((folder / "receipt.json").read_text())
    result = {"verdict": receipt["verdict"], "reason": (receipt.get("reason") or "")[:200]}
    _GRADES[key] = result
    return result


def trajectory(cell: Cell, steps: list, cwd: str | None, edits: list[int], grade_root: Path) -> dict:
    """Grade the reconstructed worktree at the end of every turn from the first
    source edit, cached by patch digest."""
    if not edits:
        return {"first_edit_turn": None, "turns": {}}
    first = steps[edits[0]].turn
    snapshots = _snapshot_replay(cell, steps, cwd)
    turns = {}
    for turn in sorted(snapshots):
        if turn < first:
            continue
        patch = snapshots[turn]
        digest = hashlib.sha256(patch.encode()).hexdigest()[:12]
        result = _grade(cell.task, patch, grade_root, f"{cell.attempt}-turn-{turn:02d}")
        turns[turn] = {"patch_digest": digest, "verdict": result["verdict"], "reason": result["reason"]}
    return {"first_edit_turn": first, "turns": turns}


def _cumulative_at(turns: list[dict]):
    def at(turn: int) -> int:
        return max((row["cumulative_output_tokens"] for row in turns if row["turn"] <= turn), default=0)

    return at


def offline_fields(cell: Cell, audit_row: dict, traj: dict, steps: list, edits: list[int], cwd: str | None) -> dict:
    """Section 6's offline four: the first hidden-suite pass state and its tokens,
    the own-green turn, and the spend after the pass state."""
    cumulative = _cumulative_at(audit_row["turns"])
    keys = sorted(traj["turns"])
    pass_turn = next((turn for turn in keys if traj["turns"][turn]["verdict"] == "pass"), None)
    pass_tokens = cumulative(pass_turn) if pass_turn is not None else None
    trigger = cf.find_trigger(steps, edits, cwd)
    total_turns = audit_row["evidence"]["turns"]
    total_tokens = audit_row["evidence"]["output_tokens"]
    return {
        "pass_turn": pass_turn,
        "pass_tokens": pass_tokens,
        "own_green_turn": None if trigger is None else trigger.turn,
        "post_pass_turns": None if pass_turn is None else total_turns - pass_turn,
        "post_pass_tokens": None if pass_turn is None else total_tokens - (pass_tokens or 0),
    }


def _tripped_verdict(cell: Cell, grade_root: Path) -> str | None:
    """Grade the harvested torn-down worktree offline (Ruling R-1).

    Task 1's harvest writes the conventional `<attempt_dir>/tripped.diff`, so
    the file -- not the record field -- is the interface; a cell without one
    (every non-`BUDGET_EXCEEDED` cell) has no tripped verdict. Cached by digest
    through `_grade`.
    """
    path = cell.folder / "tripped.diff"
    if not path.is_file():
        return None
    return _grade(cell.task, path.read_text(), grade_root, f"{cell.attempt}-tripped")["verdict"]


def _filtered_allowlist_reason(
    cell: Cell,
    patch: str,
    source_paths: tuple[str, ...],
    ignored_paths: tuple[str, ...],
    grade_root: Path,
) -> str | None:
    """A voiding non-source path is allowlist evidence only when the filtered patch passes.

    Ruling R-4: design section 7's allowlist class is "a passing state exists
    but a file outside `source_paths` voids the patch". The grader drops
    ``manifest.ignored_paths`` before its allowlist check (`grade.py:164-168`),
    so only a non-source path OUTSIDE ``ignored_paths`` voids the patch; a cell
    whose only non-source files are ignored (both retained tasks ignore
    ``PROVENANCE.md``) is not an allowlist case. For a genuinely voiding path,
    the patch's non-source sections are dropped with the same filter
    ``ignored_paths`` uses (`drop_ignored`), the remainder is graded, and the
    reason is returned only when that remainder grades ``pass``.
    """
    try:
        paths = parse_patch_paths(patch)
    except PatchParseError:
        return None
    non_source = tuple(path for path in paths if not within_source(path, source_paths))
    ignored = set(ignored_paths)
    voiding = tuple(path for path in non_source if path not in ignored)
    if not voiding:
        return None
    filtered, dropped = drop_ignored(patch, non_source)
    if not filtered.strip():
        return None
    if _grade(cell.task, filtered, grade_root, f"{cell.attempt}-filtered")["verdict"] != "pass":
        return None
    return "filtered pass after removing non-source path(s): " + ", ".join(dropped)


def counterfactual(
    cell: Cell,
    audit_row: dict,
    traj: dict,
    steps: list,
    edits: list[int],
    cwd: str | None,
    full,
    final_verdict: str | None,
    raised: str | None,
) -> dict:
    """The finish-on-green reading at the 32k line, twice: run 1's pre-registered
    rules (with `cf.unmeasured_reasons` recorded) and run 2's method (the graded
    worktree at the end of the trigger turn).

    `final_verdict` is run 1's full-patch grade, taken whenever the harness
    verdict is graded -- including a cell that landed no source edit, whose
    empty patch run 1 still grades (FINDING 1). `raised` is folded into run 1's
    unmeasured reasons exactly as run 1 folds it (MINOR 3)."""
    # Design section 3.2: the counterfactual is read at the pre-registered line.
    # The record's 48,000-token budget stays as a second column, never as the
    # comparison (Ruling 3). Feeding the line reading to `cf.unmeasured_reasons`
    # moves run 1's unmeasured list, which is correct: run 1 withholds an
    # unverified rescue, and more cells are now not-actual (Ruling 19).
    actual_48k = audit_row["code"] == "OK" and audit_row["verdict"] == "pass"
    actual = cc.actual_at_line(
        verdict=audit_row["verdict"],
        output_tokens=audit_row["evidence"]["output_tokens"],
        turns=audit_row["evidence"]["turns"],
    )
    trigger = cf.find_trigger(steps, edits, cwd)
    fidelity = cf.fidelity(audit_row["verdict"], final_verdict)
    trigger_verdict = None
    unverified: list[int] = []
    if trigger is not None and trigger.within_budget:
        trigger_verdict = traj["turns"].get(trigger.turn, {}).get("verdict")
        unverified = sorted(
            set(cf.unverified_bash_turns(steps, cwd, trigger.turn))
            | {turn for turn in full.failed_replay_turns if turn <= trigger.turn}
        )
    unmeasured = cf.unmeasured_reasons(
        fidelity_result=fidelity,
        harness_verdict=audit_row["verdict"],
        final_verdict=final_verdict,
        trigger=trigger,
        skipped_writer_turns=full.skipped_writer_turns,
        anchor_miss_turns=full.anchor_miss_turns,
        raised=raised,
        actual=actual,
        trigger_verdict=trigger_verdict,
        unverified_bash_turns=unverified,
    )
    run1 = cf.counterfactual_pass(actual, trigger, unmeasured, trigger_verdict)
    run2 = (trigger_verdict == "pass") if (trigger is not None and trigger.within_budget) else actual
    return {
        "actual": actual,
        "actual_48k": actual_48k,
        "trigger": asdict(trigger) if trigger is not None else None,
        "trigger_verdict": trigger_verdict,
        "final_verdict": final_verdict,
        "fidelity": fidelity,
        "unmeasured": unmeasured,
        "run1": {"counterfactual": "pass" if run1 else "not-pass", "change": cf.change(actual, run1)},
        "run2": {"counterfactual": "pass" if run2 else "not-pass", "change": cf.change(actual, run2)},
        "raised": raised,
    }


def _no_reading(audit_row: dict, raised: str | None = None) -> dict:
    actual_48k = audit_row["code"] == "OK" and audit_row["verdict"] == "pass"
    actual = cc.actual_at_line(
        verdict=audit_row["verdict"],
        output_tokens=audit_row["evidence"]["output_tokens"],
        turns=audit_row["evidence"]["turns"],
    )
    value = "pass" if actual else "not-pass"
    return {
        "actual": actual,
        "actual_48k": actual_48k,
        "trigger": None,
        "trigger_verdict": None,
        "final_verdict": None,
        "fidelity": "unverifiable",
        "unmeasured": [f"raised: {raised}"] if raised else [],
        "run1": {"counterfactual": value, "change": "none"},
        "run2": {"counterfactual": value, "change": "none"},
        "raised": raised,
    }


def row(
    cell: Cell,
    audit_row: dict,
    offline: dict,
    reading: dict,
    raised: str | None,
    exploration_turns: int | None,
) -> dict:
    """Assemble one output row. The table shape is the driver's, not the package's."""
    evidence = audit_row["evidence"]
    facts = cc.Facts(
        code=audit_row["code"],
        verdict=audit_row["verdict"],
        passed_at_line=bool(reading["actual"]),
        tripped_verdict=audit_row["tripped_verdict"],
        raised=raised,
        length_stops=evidence["length_stops"],
        root_searches=evidence["root_searches"],
        tool_reported_timeouts=evidence["tool_reported_timeouts"],
        first_pass_turn=offline["pass_turn"],
        first_pass_tokens=offline["pass_tokens"],
        self_stop_turn=(evidence["self_stop"] or {}).get("turn"),
        allowlist_reason=audit_row["allowlist_reason"],
    )
    biggest = evidence["biggest_turn"] or {}
    stop = evidence["self_stop"] or {}
    return {
        "task": cell.task,
        "arm": cell.arm,
        "attempt": cell.attempt,
        "code": audit_row["code"],
        "verdict": audit_row["verdict"],
        "actual_32k": reading["actual"],
        "actual_48k": reading["actual_48k"],
        "tripped_verdict": audit_row["tripped_verdict"],
        "turns": evidence["turns"],
        "tokens": evidence["output_tokens"],
        "length_stops": evidence["length_stops"],
        "exploration_turns": exploration_turns,
        "biggest_turn": biggest.get("turn"),
        "biggest_tokens": biggest.get("output_tokens"),
        "biggest_share": biggest.get("share"),
        "tool_span_seconds": evidence["tool_span_seconds"],
        "whole_attempt_seconds": audit_row["whole_attempt_seconds"],
        "self_stop_turn": stop.get("turn"),
        "self_stop_tokens": stop.get("output_tokens"),
        "pass_turn": offline["pass_turn"],
        "pass_tokens": offline["pass_tokens"],
        "own_green_turn": offline["own_green_turn"],
        "post_pass_turns": offline["post_pass_turns"],
        "post_pass_tokens": offline["post_pass_tokens"],
        "flags": cc.flags(facts),
        "run1": reading["run1"],
        "run2": reading["run2"],
        "unmeasured": reading["unmeasured"],
        "raised": raised,
    }


@dataclass(frozen=True, slots=True)
class DecodeLog:
    """The night's completions and every selected cell's span (Ruling 7)."""

    completions: list
    spans: list


def cell_span(cell: Cell) -> tuple[float | None, float | None, str | None]:
    """`[attempt directory stamp, mtime(attempt.json)]`, or a stated reason (Ruling 10)."""
    started = cc.attempt_started(cell.attempt_dir)
    if started is None:
        return None, None, cd.NO_STAMP
    try:
        ended = (cell.folder / "attempt.json").stat().st_mtime
    except OSError:
        return None, None, cd.NO_ATTEMPT_JSON
    return started, ended, None


def load_decode_log(pattern: str, selected: list[Cell]) -> DecodeLog:
    """Read-only over `~/.omlx/logs/`. Files are read in name order, which is
    date order for oMLX's rotation, and the completions are not re-sorted: the
    attribution is by instant, not by position."""
    completions: list = []
    for name in sorted(glob.glob(pattern)):
        completions.extend(cd.parse_completions(Path(name).read_text(errors="replace")))
    spans = [(s, e) for s, e, reason in map(cell_span, selected) if reason is None]
    return DecodeLog(completions=completions, spans=spans)


def decode_row(cell: Cell, log: DecodeLog) -> dict:
    start, end, reason = cell_span(cell)
    if reason is not None:
        return {"decode_tok_s": None, "decode_median_tok_s": None, "decode_completions": 0,
                "decode_overlap": None, "decode_reason": reason}
    reading = cd.decode_rate(log.completions, start=start, end=end)
    return {
        "decode_tok_s": reading.tok_s,
        "decode_median_tok_s": reading.median_tok_s,
        "decode_completions": reading.completions,
        "decode_overlap": cd.span_overlap(log.spans, start, end),
        "decode_reason": reading.reason,
    }


def measure(cell: Cell, grade_root: Path, log: DecodeLog) -> dict:
    raised = None
    attempt: dict = {}
    try:
        attempt = json.loads((cell.folder / "attempt.json").read_text())
        if not isinstance(attempt, dict):  # valid JSON that is not an object is reported, not fatal
            attempt = {}
    except Exception as exc:  # an unreadable attempt is reported, not fatal
        raised = f"{type(exc).__name__}: {exc}"[:200]
    # Ruling R-5b: replay once, before the audit, so the audit's source-edit
    # route is the same bash_touched route the counterfactual uses.
    context = None
    bash_touched: dict[int, tuple[str, ...]] = {}
    try:
        manifest = json.loads((cf.TASKS / cell.task / "manifest.json").read_text())
        sp = tuple(manifest["source_paths"])
        ignored = tuple(manifest.get("ignored_paths", ()))
        transcript = (cell.folder / "transcript.txt").read_text()
        events = cf.parse_events(transcript)
        cwd = cf.session_cwd(events)
        steps = cf.steps_of(events)
        full = cf.replay(_spec_of(cell), steps, cwd, sp, None)
        edits = cf.source_edit_indices(steps, sp, cwd, full.bash_touched)
        bash_touched = full.bash_touched
        context = (sp, ignored, cwd, steps, full, edits)
    except Exception as exc:  # a cell with no readable transcript is reported, not fatal
        raised = raised or f"{type(exc).__name__}: {exc}"[:200]
    try:
        audit_row = audit(cell, attempt, bash_touched)
    except Exception as exc:
        raised = raised or f"{type(exc).__name__}: {exc}"[:200]
        audit_row = _empty_audit(cell, attempt)
    traj = {"first_edit_turn": None, "turns": {}}
    offline = {
        "pass_turn": None,
        "pass_tokens": None,
        "own_green_turn": None,
        "post_pass_turns": None,
        "post_pass_tokens": None,
    }
    reading = _no_reading(audit_row, raised)
    # The torn-down worktree is graded offline here, never in the cell path
    # (Ruling R-1). A grade that fails is a swallowed measurement failure.
    try:
        audit_row["tripped_verdict"] = _tripped_verdict(cell, grade_root)
    except Exception as exc:
        raised = raised or f"{type(exc).__name__}: {exc}"[:200]
        audit_row["tripped_verdict"] = None
        reading = _no_reading(audit_row, raised)
    exploration_turns = audit_row["evidence"]["exploration_turns"]
    if context is not None:
        sp, ignored, cwd, steps, full, edits = context
        # Ruling R-5b: exploration turns follow the bash_touched source-edit
        # route, not cell_evidence's write/edit-only rule, so they are
        # comparable with run 2's.
        exploration_turns = None if not edits else steps[edits[0]].turn - 1
        try:
            # Run 1 grades the full patch whenever the harness verdict is graded,
            # even with no source edit; a no-edit cell's fidelity is that grade
            # (FINDING 1).
            final = None
            if audit_row["verdict"] in cf.GRADED:
                final = _grade(cell.task, full.patch, grade_root, f"{cell.attempt}-final")
            traj = trajectory(cell, steps, cwd, edits, grade_root)
            offline = offline_fields(cell, audit_row, traj, steps, edits, cwd)
            # Ruling R-4: the allowlist reason comes from a filtered pass over a
            # genuinely voiding path (one outside ignored_paths), never from an
            # unfiltered "non-source path" reason.
            audit_row["allowlist_reason"] = _filtered_allowlist_reason(
                cell, full.patch, sp, ignored, grade_root
            )
            reading = counterfactual(
                cell,
                audit_row,
                traj,
                steps,
                edits,
                cwd,
                full,
                None if final is None else final["verdict"],
                raised,
            )
        except Exception as exc:
            raised = raised or f"{type(exc).__name__}: {exc}"[:200]
            reading = _no_reading(audit_row, raised)
    else:
        # No replay means no filtered grade; a reason alone is not allowlist
        # evidence (Ruling R-4).
        audit_row["allowlist_reason"] = None
    return {**row(cell, audit_row, offline, reading, raised, exploration_turns), **decode_row(cell, log)}


def tallies(rows: list[dict]) -> list[dict]:
    """Rescues, harms and net per task, under each reading. Nothing pools across tasks."""
    out = []
    for task in sorted({r["task"] for r in rows}):
        mine = [r for r in rows if r["task"] == task]
        for reading in ("run1", "run2"):
            changes = [r[reading]["change"] for r in mine]
            out.append(
                {
                    "task": task,
                    "reading": reading,
                    "cells": len(mine),
                    "actual_32k": sum(1 for r in mine if r["actual_32k"]),
                    "actual_48k": sum(1 for r in mine if r["actual_48k"]),
                    "rescues": changes.count("rescue"),
                    "harms": changes.count("harm"),
                    "net": changes.count("rescue") - changes.count("harm"),
                    # `unmeasured` is run 1's recorded caveat; run 2's method does
                    # not withhold a rescue for it, so the cell is listed under
                    # run 1 only and never double-counted.
                    "unmeasured": [r["attempt"] for r in mine if reading == "run1" and r["unmeasured"]],
                }
            )
    return out


def _dash(value: object) -> str:
    return "-" if value is None else str(value)


def _stamp_text(header: dict) -> str:
    return f"evals {header['evals_commit']}{' (dirty)' if header['evals_dirty'] else ''}; {header['command']}"


def table(rows: list[dict], header: dict) -> str:
    columns = [
        "task", "attempt", "code", "verdict", "verdict@32k", "raised", "tripped", "turns", "tokens",
        "length stops", "exploration turns", "biggest turn", "biggest share", "tool span s",
        "whole-attempt s", "decode tok/s", "decode n", "self-stop turn", "self-stop tokens", "pass turn",
        "pass tokens", "own-green turn", "post-pass turns", "post-pass tokens",
    ]
    lines = [
        f"<!-- {_stamp_text(header)} -->",
        "",
        "| " + " | ".join(columns) + " |",
        "|" + "---|" * len(columns),
    ]
    for r in rows:
        biggest = "-" if r["biggest_turn"] is None else f"t{r['biggest_turn']}:{r['biggest_tokens']}"
        share = "-" if r["biggest_share"] is None else f"{r['biggest_share']:.0%}"
        span = "-" if r["tool_span_seconds"] is None else f"{r['tool_span_seconds']:.1f}"
        whole = "-" if r["whole_attempt_seconds"] is None else f"{r['whole_attempt_seconds']:.1f}"
        decode = "-" if r["decode_tok_s"] is None else f"{r['decode_tok_s']:.1f}"
        verdict_at_line = "pass" if r["actual_32k"] else "not-pass"
        values = [
            r["task"], r["attempt"], _dash(r["code"]), _dash(r["verdict"]), verdict_at_line, _dash(r["raised"]),
            _dash(r["tripped_verdict"]), str(r["turns"]), str(r["tokens"]), str(r["length_stops"]),
            _dash(r["exploration_turns"]), biggest, share, span, whole, decode, str(r["decode_completions"]),
            _dash(r["self_stop_turn"]), _dash(r["self_stop_tokens"]), _dash(r["pass_turn"]),
            _dash(r["pass_tokens"]), _dash(r["own_green_turn"]), _dash(r["post_pass_turns"]),
            _dash(r["post_pass_tokens"]),
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def tally_table(rows: list[dict]) -> str:
    lines = [
        "",
        "## Per task (nothing pools across tasks)",
        "",
        "| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in tallies(rows):
        unmeasured = ", ".join(t["unmeasured"]) if t["unmeasured"] else "-"
        lines.append(
            f"| {t['task']} | {t['reading']} | {t['cells']} | {t['actual_32k']} | {t['actual_48k']} | "
            f"{t['rescues']} | {t['harms']} | {t['net']} | {unmeasured} |"
        )
    return "\n".join(lines) + "\n"


def classes(rows: list[dict], header: dict) -> str:
    columns = ["task", "attempt", "raised", *cc.CLASSES, "primary", "cited turns"]
    lines = [
        f"<!-- {_stamp_text(header)} -->",
        "",
        "The eight class columns are empty on purpose: a reviewer fills them, by turn, "
        "from the reconstruction (design section 7). `primary` and `cited turns` are the "
        "reviewer's too. The mechanical evidence each class would be argued from is "
        "printed beneath.",
        "",
        "| " + " | ".join(columns) + " |",
        "|" + "---|" * len(columns),
    ]
    for r in rows:
        lines.append("| " + " | ".join([r["task"], r["attempt"], _dash(r["raised"]), *([""] * len(cc.CLASSES)), "", ""]) + " |")
    lines.append("")
    for r in rows:
        shown = ", ".join(f"{name}={r['flags'][name]}" for name in cc.CLASSES)
        decode = "-" if r["decode_tok_s"] is None else f"{r['decode_tok_s']:.1f}"
        lines.append(
            f"evidence: {r['task']} {r['attempt']} {shown} actual@32k={r['actual_32k']} "
            f"actual@48k={r['actual_48k']} decode_tok_s={decode} decode_overlap={_dash(r['decode_overlap'])}"
        )
    return "\n".join(lines) + "\n"


def stamp(argv: list[str], night: Path) -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=EVALS, capture_output=True, text=True).stdout.strip()
    # The instrument loaded by path is watched too, as run 1 watches its own
    # counterfactual.py (MINOR 4): a dirty instrument must not read as clean.
    watched = ["src", "evidence/2026-09-16-census/classify.py", os.fspath(SCRIPT.relative_to(EVALS))]
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--", *watched],
            cwd=EVALS,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {"evals_commit": commit, "evals_dirty": dirty, "night": night.name,
            "command": " ".join(["classify.py", *argv]),
            "tz_offset": datetime.now().astimezone().strftime("%z")}


def _overwrite_refusal(out: Path, tasks: set[str], night: str) -> str | None:
    """Ruling 11: refuse to let this night's cells silently overwrite another
    night's committed folder. Three of night 2's four tasks share night 1's
    names, and the default ``--out`` is night 1's directory.

    Returns the refusal text for the first task whose existing ``cells.json``
    names a different night, or ``None`` when every task is clear to write --
    either its folder is fresh, or it already holds this same night's cells
    (a deliberate re-classification).
    """
    for task in sorted(tasks):
        existing = out / task / "cells.json"
        if existing.is_file():
            previous = json.loads(existing.read_text()).get("night")
            if previous is not None and previous != night:
                return (
                    f"classify: {existing} holds {previous}, not {night}; "
                    "pass --out for this night rather than overwriting another night's table"
                )
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="classify.py", description="Classify one census night against its record.")
    parser.add_argument("--night", type=Path, required=True, help="the night directory under ~/satyrn-runs")
    parser.add_argument("--record", type=Path, required=True, help="the frozen run record")
    parser.add_argument("--out", type=Path, default=HERE, help="output base; <out>/<task>/ holds the three files")
    parser.add_argument("--grade-root", type=Path, default=DEFAULT_GRADE_ROOT, help="receipts and grader scratch; no Python project above it")
    parser.add_argument("--cell", action="append", default=[], help="one attempt suffix or attempt_dir (repeatable)")
    parser.add_argument(
        "--server-log",
        default=str(Path.home() / ".omlx" / "logs" / "server.log*"),
        help="glob for the oMLX server logs the decode rate is read from (read-only)",
    )
    args = parser.parse_args(argv)
    try:
        selected = select(args.night, args.record, tuple(args.cell))
    except Refused as exc:
        print(f"classify: {exc}", file=sys.stderr)
        return 2
    grade_root = args.grade_root.resolve()
    if markers := cf.project_markers(grade_root):
        print(f"classify: --grade-root sits under {markers[0]}; pytest would read it while grading", file=sys.stderr)
        return 2
    grade_root.mkdir(parents=True, exist_ok=True)
    header = stamp(argv, args.night)
    cf.WORK = HERE / "work"
    shutil.rmtree(cf.WORK, ignore_errors=True)
    cf.WORK.mkdir(parents=True, exist_ok=True)
    log = load_decode_log(args.server_log, selected)
    if not log.completions and not glob.glob(args.server_log):
        print(f"classify: no server log matched {args.server_log!r}; decode columns will be unmeasured", file=sys.stderr)
    rows = []
    try:
        for cell in selected:
            measured = measure(cell, grade_root, log)
            rows.append(measured)
            print(
                f"{cell.task} {cell.attempt} {measured['code']} own-green={measured['own_green_turn']} "
                f"pass={measured['pass_turn']} run1={measured['run1']['change']} run2={measured['run2']['change']}"
                + (f" raised={measured['raised']}" if measured["raised"] else ""),
                flush=True,
            )
    finally:
        shutil.rmtree(cf.WORK, ignore_errors=True)
    if (refusal := _overwrite_refusal(args.out, {r["task"] for r in rows}, header["night"])) is not None:
        print(refusal, file=sys.stderr)
        return 2
    for task in sorted({r["task"] for r in rows}):
        mine = [r for r in rows if r["task"] == task]
        folder = args.out / task
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "cells.json").write_text(
            json.dumps({**header, "task": task, "cells": mine, "tallies": tallies(mine)}, indent=1) + "\n"
        )
        (folder / "table.md").write_text(table(mine, header) + tally_table(mine))
        (folder / "classes.md").write_text(classes(mine, header))
        print(f"{task}: {len(mine)} cells -> {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
