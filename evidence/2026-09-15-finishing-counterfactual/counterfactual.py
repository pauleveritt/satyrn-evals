#!/usr/bin/env python3
"""The finishing counterfactual (pre-registration
docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md).

If a retained cell had stopped at its first Engine-observable green (spec
section 3), would the hidden suite have passed? Offline, from retained
transcripts only: no model, no network, nothing under /Users/Shared.
Scratch worktrees live under this directory's ``work/`` (git-ignored).

Run from the evals checkout:

    uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase debug
    uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase decision

``--phase debug`` reads only the cells outside the decision set and refuses
any decision attempt id. ``--phase decision`` reads exactly the 24 decision
cells, once, and writes cells.json, table.md and decision.txt.

Extends evidence/2026-09-15-release-one-outcome/reconstruct.py: the same
write/edit/heredoc replay, with the harvest and grade the harness uses.
Pure functions sit above the ``# --- impure ---`` line; the tests in
tests/test_finishing_counterfactual.py exercise only those.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from satyrn_evals.budget import UsageCounter
from satyrn_evals.cell_evidence import (
    _UV_RUN_VALUE_FLAGS,
    _program,
    _segments,
    runs_pytest,
)

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[1]
TASKS = EVALS / "src" / "satyrn_evals" / "tasks"
RUNS = Path.home() / "satyrn-runs"
WORK = HERE / "work"
# Grading runs where the harness grades: under no Python project. pytest reads
# the nearest ancestor config and every ancestor conftest.py, so a grade under
# this checkout would run the hidden suite with evals' own pytest settings.
DEFAULT_GRADE_ROOT = Path.home() / "satyrn-counterfactual-grades"
PROJECT_MARKERS = ("pyproject.toml", "pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg", "conftest.py")

# Spec section 3: the budget a trigger must fall within.
TOKEN_BUDGET = 32_000
TURN_BUDGET = 48


@dataclass(frozen=True, slots=True)
class CellSpec:
    task: str
    run: str
    arm: str
    attempt: str  # the attempt directory's six-digit suffix
    group: str  # "decision", "nights-2026-09-14" or "engine"


def _cells(task: str, run: str, arm: str, group: str, attempts: str) -> tuple[CellSpec, ...]:
    return tuple(CellSpec(task, run, arm, a, group) for a in attempts.split())


# Spec section 2, decision table, in its row order.
DECISION: tuple[CellSpec, ...] = (
    *_cells("agentclinic-repair-depth-3", "2026-09-14-admission-agentclinic-repair-depth-3", "baseline", "decision", "971281 021584 082295 700050"),
    *_cells("selfhost-run-record-gate", "2026-09-15-admission-selfhost-run-record-gate", "baseline", "decision", "388294 448568 519278 028222"),
    *_cells("selfhost-docs-linter", "2026-09-15-admission-selfhost-docs-linter", "baseline", "decision", "147562 204433 270586 970283"),
    *_cells("selfhost-guard-prefixes", "2026-09-15-admission-selfhost-guard-prefixes", "baseline", "decision", "812248 870439 937944 424626"),
    *_cells("selfhost-review-script", "2026-09-15-admission-selfhost-review-script", "baseline", "decision", "688090 746232 816670 501161"),
    *_cells("agentclinic-repair-depth-2", "2026-09-14-admission-agentclinic-repair-depth-2", "baseline", "decision", "523251 575297 634454 616367"),
)
# Spec section 2, "recorded codes", as (code, verdict) in the same order.
RECORDED: dict[str, tuple[str, str | None]] = dict(
    zip(
        (c.attempt for c in DECISION),
        (
            ("COMMAND_TIMEOUT", None), ("BUDGET_EXCEEDED", None), ("OK", "fail"), ("BUDGET_EXCEEDED", None),
            *[("BUDGET_EXCEEDED", None)] * 4,
            ("BUDGET_EXCEEDED", None), ("OK", "pass"), ("BUDGET_EXCEEDED", None), ("BUDGET_EXCEEDED", None),
            *[("OK", "pass")] * 12,
        ),
        strict=True,
    )
)
BUDGET_SHAPED = ("agentclinic-repair-depth-3", "selfhost-run-record-gate", "selfhost-docs-linter")
FLOOR = ("selfhost-guard-prefixes", "selfhost-review-script", "agentclinic-repair-depth-2")

# Spec section 2, "reported, outside the decision".
DEBUG: tuple[CellSpec, ...] = (
    *_cells("selfhost-run-record-gate", "2026-09-14-admission-selfhost-run-record-gate", "baseline", "nights-2026-09-14", "490384 549012 618278 511653"),
    *_cells("selfhost-guard-prefixes", "2026-09-14-admission-selfhost-guard-prefixes", "baseline", "nights-2026-09-14", "249635 305323 372105 309486"),
    *_cells("selfhost-review-script", "2026-09-14-admission-selfhost-review-script", "baseline", "nights-2026-09-14", "714610 770940 840545 624725"),
    *_cells("agentclinic-repair-depth-3", "2026-09-15-route-proof-b-agentclinic-repair-depth-3", "engine", "engine", "808698"),
    *_cells("selfhost-run-record-gate", "2026-09-15-route-proof-selfhost-run-record-gate", "engine", "engine", "296145"),
    *_cells("selfhost-docs-linter", "2026-09-15-route-proof-selfhost-docs-linter", "engine", "engine", "859943"),
    *_cells("agentclinic-repair-misleading-locus", "2026-09-15-dev-before-agentclinic-repair-misleading-locus", "engine", "engine", "117091 172304"),
    *_cells("agentclinic-repair-misleading-locus", "2026-09-15-dev-after-agentclinic-repair-misleading-locus", "engine", "engine", "140540 201516"),
)
DECISION_IDS = frozenset(c.attempt for c in DECISION)
assert len(DECISION) == 24 and len(DECISION_IDS) == 24
assert not DECISION_IDS & {c.attempt for c in DEBUG}


class DecisionCellRefused(ValueError):
    """A debug-phase request named a decision attempt id."""


def select_cells(phase: str, only: tuple[str, ...] = ()) -> tuple[CellSpec, ...]:
    """The cells a phase may read. Debug refuses any decision id; decision takes no filter."""
    if phase == "debug":
        refused = sorted(set(only) & DECISION_IDS)
        if refused:
            raise DecisionCellRefused(f"--phase debug refuses decision attempt ids: {', '.join(refused)}")
        unknown = sorted(set(only) - {c.attempt for c in DEBUG})
        if unknown:
            raise ValueError(f"not a debug attempt id: {', '.join(unknown)}")
        return tuple(c for c in DEBUG if not only or c.attempt in only)
    if phase == "decision":
        if only:
            raise ValueError("--phase decision runs exactly the 24 decision cells; --cell is refused")
        return DECISION
    raise ValueError(f"unknown phase: {phase}")


# --- transcript steps ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Step:
    """One finished tool call, with the budget counted up to its end event."""

    index: int
    turn: int
    output_tokens: int
    name: str
    args: dict
    is_error: bool
    text: str
    details: object


def parse_events(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def session_cwd(events: list[dict]) -> str | None:
    return next(
        (e["cwd"] for e in events if e.get("type") == "session" and isinstance(e.get("cwd"), str) and e["cwd"]),
        None,
    )


def result_text(result: object) -> str:
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list):
        return ""
    return "\n".join(p["text"] for p in content if isinstance(p, dict) and isinstance(p.get("text"), str))


def steps_of(events: list[dict]) -> list[Step]:
    """Every ``tool_execution_end``, joined to its start's arguments, in stream order.

    Turns and output tokens are evals' own count (``budget.UsageCounter``) at
    the end event: one ``turn_start`` is a turn, an assistant ``message_end``
    adds ``usage.output``.
    """
    usage = UsageCounter()
    starts: dict[str, dict] = {}
    steps: list[Step] = []
    for event in events:
        usage.feed_event(event)
        kind = event.get("type")
        if kind == "tool_execution_start" and isinstance(event.get("toolCallId"), str):
            starts[event["toolCallId"]] = event.get("args") if isinstance(event.get("args"), dict) else {}
        elif kind == "tool_execution_end" and isinstance(event.get("toolName"), str):
            result = event.get("result")
            steps.append(
                Step(
                    index=len(steps),
                    turn=usage.turns,
                    output_tokens=usage.output_tokens,
                    name=event["toolName"],
                    args=starts.get(event.get("toolCallId"), {}),
                    is_error=event.get("isError") is True,
                    text=result_text(result),
                    details=result.get("details") if isinstance(result, dict) else None,
                )
            )
    return steps


# --- section 3: source edits --------------------------------------------------


def tree_path(path: str, cwd: str | None) -> str | None:
    """A tool path as a worktree-relative POSIX path, or None when outside the tree."""
    if not isinstance(path, str) or not path:
        return None
    if path.startswith("/"):
        canonical = posixpath.normpath(path.removeprefix("/private"))
        if cwd:
            root = posixpath.normpath(cwd.removeprefix("/private"))
            if canonical == root:
                return "."
            if canonical.startswith(root + "/"):
                return canonical[len(root) + 1 :]
        if "/worktree/" in canonical:
            return canonical.split("/worktree/", 1)[1]
        return None
    relative = posixpath.normpath(path)
    if relative == ".." or relative.startswith("../"):
        return None
    return relative


def is_test_file(path: str) -> bool:
    """Spec section 3: basename test_*.py or *_test.py, or a path under a tests directory."""
    parts = path.split("/")
    base = parts[-1]
    return (base.startswith("test_") and base.endswith(".py")) or base.endswith("_test.py") or "tests" in parts[:-1]


def in_source_paths(path: str, source_paths: tuple[str, ...]) -> bool:
    return any(path == entry or path.startswith(entry.rstrip("/") + "/") for entry in source_paths)


def is_source_file(path: str, source_paths: tuple[str, ...]) -> bool:
    return in_source_paths(path, source_paths) and not is_test_file(path)


def source_edit_indices(
    steps: list[Step], source_paths: tuple[str, ...], cwd: str | None, bash_touched: dict[int, tuple[str, ...]]
) -> list[int]:
    """Spec section 3 "source edit": a landed write, a non-error edit, or a replayed bash
    write, of a non-test file inside source_paths. ``bash_touched`` maps a replayed bash
    step's index to the tree paths its replay changed."""
    found = []
    for step in steps:
        if step.name in ("write", "edit"):
            path = tree_path(step.args.get("path", ""), cwd)
            if not step.is_error and path is not None and is_source_file(path, source_paths):
                found.append(step.index)
        elif step.name == "bash" and any(is_source_file(p, source_paths) for p in bash_touched.get(step.index, ())):
            found.append(step.index)
    return found


# --- section 3: own-green -----------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_SUMMARY = re.compile(r"^=*\s*((?:\d+ [a-z]+(?:, )?)+) in \d+(?:\.\d+)?s\b.*$")


def summary_lines(output: str) -> list[dict[str, int]]:
    """Each pytest summary line in ``output`` ("3 passed, 1 warning in 0.4s") as word -> count."""
    found = []
    for line in _ANSI.sub("", output).splitlines():
        match = _SUMMARY.match(line.strip())
        if match:
            counts = {}
            for part in match.group(1).split(", "):
                number, word = part.split(" ", 1)
                counts[word] = int(number)
            found.append(counts)
    return found


def pytest_output_green(output: str) -> bool:
    """A summary line exists, one reports at least one pass, and none reports failed or error."""
    lines = summary_lines(output)
    bad = ("failed", "error", "errors")
    return (
        bool(lines)
        and any(c.get("passed", 0) >= 1 for c in lines)
        and all(c.get(word, 0) == 0 for c in lines for word in bad)
    )


def self_test_green(step: Step) -> bool:
    """A self_test whose details say ok, exit 0, not timed out, and whose output names no failure."""
    details = step.details if isinstance(step.details, dict) else {}
    result = details.get("result") if isinstance(details.get("result"), dict) else {}
    return (
        step.name == "self_test"
        and not step.is_error
        and details.get("ok") is True
        and result.get("exit_code") == 0
        and result.get("timed_out") is not True
        and all(c.get(word, 0) == 0 for c in summary_lines(step.text) for word in ("failed", "error", "errors"))
    )


def is_test_run(step: Step) -> bool:
    return step.name == "self_test" or (step.name == "bash" and runs_pytest(str(step.args.get("command", ""))))


def is_green(step: Step) -> bool:
    if step.name == "self_test":
        return self_test_green(step)
    return (
        step.name == "bash"
        and runs_pytest(str(step.args.get("command", "")))
        and not step.is_error
        and pytest_output_green(step.text)
    )


@dataclass(frozen=True, slots=True)
class Trigger:
    step: int
    turn: int
    output_tokens: int
    route: str  # "self_test" or "bash"
    within_budget: bool


def within_budget(output_tokens: int, turn: int) -> bool:
    return output_tokens <= TOKEN_BUDGET and turn <= TURN_BUDGET


def find_trigger(steps: list[Step], source_edits: list[int]) -> Trigger | None:
    """Spec section 3: the first green test run after the first source edit."""
    if not source_edits:
        return None
    first_edit = min(source_edits)
    for step in steps:
        if step.index > first_edit and is_test_run(step) and is_green(step):
            return Trigger(step.index, step.turn, step.output_tokens, step.name, within_budget(step.output_tokens, step.turn))
    return None


# --- replay rules (pure) ------------------------------------------------------

_CD_PREFIX = re.compile(r"""^\s*cd\s+("[^"]*"|'[^']*'|\S+)\s*(?:;|&&)\s*""")
_HEREDOC_TARGET_FIRST = re.compile(r"""^cat\s*(?P<op>>>?)\s*(?P<target>\S+)\s*<<(?P<dash>-?)\s*(?P<q>['"]?)(?P<word>\w+)(?P=q)[ \t]*\n""")
_HEREDOC_WORD_FIRST = re.compile(r"""^cat\s*<<(?P<dash>-?)\s*(?P<q>['"]?)(?P<word>\w+)(?P=q)\s*(?P<op>>>?)\s*(?P<target>\S+)[ \t]*\n""")
_SIMPLE_WRITE = re.compile(r"""^(?:sed\s+-i|printf\s|echo\s)""")
_PY_WRITE = re.compile(r"write_text\(|write_bytes\(|(?<!stdout)(?<!stderr)\.write\(|open\([^)]*['\"][wax]|shutil\.|os\.(?:rename|replace|remove|unlink)\(")
_REDIRECTS = frozenset({">", ">>", ">|", "&>", "&>>"})
_LAST_OPERAND_WRITERS = frozenset({"cp", "install", "ln", "rsync"})
_EVERY_OPERAND_WRITERS = frozenset({"mv", "rm", "touch", "truncate", "tee", "patch"})
_GIT_WRITERS = frozenset({"apply", "am", "checkout", "restore", "reset", "stash", "mv", "rm", "cherry-pick", "revert", "merge", "pull", "switch", "clean"})


def strip_cd(command: str, cwd: str | None) -> str | None:
    """Drop a leading ``cd`` into the worktree itself; None when it enters anywhere else."""
    match = _CD_PREFIX.match(command)
    if not match:
        return command
    target = match.group(1).strip("'\"")
    if target in (".", "$(pwd)", "$PWD") or (cwd and tree_path(target, cwd) == "."):
        return command[match.end() :]
    return None


@dataclass(frozen=True, slots=True)
class BashPlan:
    """How a bash command replays: the shell text to run in the scratch tree (or
    None), and the remainder the replay does not run."""

    replay: str | None
    remainder: str


def plan_bash(command: str, cwd: str | None) -> BashPlan:
    """reconstruct.py's replayable forms, narrowed to one write: a ``cat >``/``cat >>``
    heredoc up to its terminator line, or a single simple ``sed -i``/``printf >``/
    ``echo >`` command. The target must be a relative path inside the tree once the
    worktree prefix is removed."""
    stripped = strip_cd(command, cwd)
    if stripped is None:
        return BashPlan(None, command)
    stripped = stripped.lstrip()
    if cwd:
        stripped = _unroot_head(stripped, cwd)
    heredoc = _HEREDOC_TARGET_FIRST.match(stripped) or _HEREDOC_WORD_FIRST.match(stripped)
    if heredoc:
        target = heredoc.group("target").strip("'\"")
        tabs = r"\t*" if heredoc.group("dash") else ""
        terminator = re.compile(rf"^{tabs}{re.escape(heredoc.group('word'))}[ \t]*$", re.M)
        end = terminator.search(stripped, heredoc.end())
        if end is None or not _inside(target):
            return BashPlan(None, command)
        cut = end.end() + 1 if end.end() < len(stripped) else end.end()
        return BashPlan(stripped[: end.end()] + "\n", stripped[cut:])
    if _SIMPLE_WRITE.match(stripped) and len(_segments(stripped)) == 1 and "\n" not in stripped.strip():
        targets = _write_targets(_segments(stripped)[0])[2]
        if targets and all(_inside(t) for t in targets):
            return BashPlan(stripped, "")
    return BashPlan(None, command)


def _unroot_head(command: str, cwd: str) -> str:
    head, sep, body = command.partition("\n")
    for root in {cwd, "/private" + cwd, cwd.removeprefix("/private")}:
        head = head.replace(root + "/", "").replace(root, ".")
    return head + sep + body


def _inside(target: str) -> bool:
    return tree_path(target, None) is not None and not target.startswith(("/", "~", "$"))


def mentions_source(text: str, source_paths: tuple[str, ...]) -> bool:
    """Whether text names a source path: a file entry by path or basename, a directory entry as ``name/``."""
    for entry in source_paths:
        name = entry.rstrip("/")
        if "." in posixpath.basename(name):
            if name in text or re.search(rf"(?<![\w.]){re.escape(posixpath.basename(name))}\b", text):
                return True
        elif re.search(rf"(?<![\w/.-]){re.escape(name)}/", text):
            return True
    return False


def _write_targets(words: list[str]) -> tuple[str, list[str], list[str]]:
    """A simple command's program (past env/timeout/uv run wrappers), its arguments, and
    the operands it could write, before cwd resolution."""
    program, rest = _program(words)
    while program in ("timeout", "env", "nice", "uv") and rest:
        if program == "uv":
            if rest[0] != "run":
                break
            rest = rest[1:]
            while rest and rest[0].startswith("-"):
                rest = rest[2:] if rest[0] in _UV_RUN_VALUE_FLAGS else rest[1:]
        elif program == "timeout":
            while rest and rest[0].startswith("-"):
                rest = rest[1:]
            rest = rest[1:]
        else:
            while rest and (rest[0].startswith("-") or "=" in rest[0]):
                rest = rest[1:]
        program, rest = (posixpath.basename(rest[0]), rest[1:]) if rest else ("", [])
    targets = [rest[i + 1] for i, w in enumerate(rest[:-1]) if w in _REDIRECTS]
    redirection = set()
    for i, w in enumerate(rest):
        if w in _REDIRECTS or w in (">&", "<", "<<", "<<<"):
            redirection.update((i, i + 1))
            if i and rest[i - 1].isdigit():
                redirection.add(i - 1)
    operands = [w for i, w in enumerate(rest) if i not in redirection and w and not w.startswith("-")]
    if program in _LAST_OPERAND_WRITERS and operands:
        targets.append(operands[-1])
    elif program in _EVERY_OPERAND_WRITERS or (
        program in ("sed", "perl") and any(re.fullmatch(r"-[a-zA-Z0-9]*i\S*", w) for w in rest)
    ):
        targets.extend(operands)
    elif program == "dd":
        targets.extend(w[3:] for w in rest if w.startswith("of="))
    return program, rest, targets


def could_write_source(command: str, source_paths: tuple[str, ...], cwd: str | None) -> bool:
    """Spec section 4: whether bash text the replay did not run could have written inside
    source_paths. Per simple command (quoted arguments and heredoc bodies are data): a git
    subcommand that rewrites the tree, or ``ruff format``/``ruff check --fix`` without
    ``--check``/``--diff``, always could; a redirection, ``tee``/``mv``/``rm``/``touch``/
    ``truncate``/``patch`` operand, ``cp``/``install``/``ln``/``rsync`` destination, or
    ``sed -i``/``perl -i`` operand could when it resolves (after any ``cd`` earlier in the
    command) inside source_paths. Python file writes anywhere in the text (heredoc bodies
    included) could when the text names a source path."""
    if _PY_WRITE.search(command) and mentions_source(command, source_paths):
        return True
    directory: str | None = "."
    for words in _segments(command):
        program, rest, targets = _write_targets(words)
        if program == "cd":
            destination = rest[0] if rest else "~"
            if destination.startswith(("/", "~", "$")):
                directory = tree_path(destination, cwd) if destination.startswith("/") else None
            elif directory is not None:
                directory = posixpath.normpath(posixpath.join(directory, destination))
            continue
        if program == "git" and any(w in _GIT_WRITERS for w in rest if not w.startswith("-")):
            return True
        if program == "ruff" and (rest[:1] == ["format"] or "--fix" in rest) and not {"--check", "--diff"} & set(rest):
            return True
        for target in targets:
            target = target.strip("'\"")
            if target.startswith("/"):
                resolved = tree_path(target, cwd)
            elif directory is None or target.startswith(("~", "$")):
                resolved = None
            else:
                resolved = tree_path(posixpath.join(directory, target), None)
            if resolved is not None and in_source_paths(resolved, source_paths):
                return True
    return False


# --- section 4: outcomes, fidelity, unmeasured --------------------------------

GRADED = ("pass", "fail", "unavailable")


def actual_pass(code: str | None, verdict: str | None) -> bool:
    return code == "OK" and verdict == "pass"


def fidelity(harness_verdict: str | None, replay_verdict: str | None) -> str:
    if harness_verdict not in GRADED:
        return "unverifiable"
    return "pass" if replay_verdict == harness_verdict else "fail"


def unmeasured_reasons(
    *,
    fidelity_result: str,
    harness_verdict: str | None,
    final_verdict: str | None,
    trigger: Trigger | None,
    skipped_writer_turns: list[int],
    anchor_miss_turns: list[int],
    raised: str | None,
) -> list[str]:
    """Spec section 4 "unmeasured". Skips and anchor misses count through the end of the
    trigger turn, the state the counterfactual grades."""
    reasons = []
    if raised:
        reasons.append(f"raised: {raised}")
    if fidelity_result == "fail":
        reasons.append(f"fidelity: harness {harness_verdict}, replay {final_verdict}")
    if trigger is not None and trigger.within_budget:
        for turn in sorted(set(skipped_writer_turns)):
            if turn <= trigger.turn:
                reasons.append(f"skipped bash writer at turn {turn}")
        for turn in sorted(set(anchor_miss_turns)):
            if turn <= trigger.turn:
                reasons.append(f"replay raised: edit anchor missing at turn {turn}")
    return reasons


def counterfactual_pass(actual: bool, trigger: Trigger | None, unmeasured: list[str], trigger_verdict: str | None) -> bool:
    """A cell with no counted trigger, or an unmeasured one, keeps its actual outcome."""
    if unmeasured or trigger is None or not trigger.within_budget:
        return actual
    return trigger_verdict == "pass"


def change(actual: bool, counterfactual: bool) -> str:
    if not actual and counterfactual:
        return "rescue"
    if actual and not counterfactual:
        return "harm"
    return "none"


# --- section 5: tallies and the decision --------------------------------------


@dataclass(frozen=True, slots=True)
class TaskTally:
    task: str
    cells: int
    rescues: int
    harms: int
    unmeasured: int

    @property
    def net(self) -> int:
        return self.rescues - self.harms

    @property
    def insufficient(self) -> bool:
        return self.unmeasured > 1


def tally(task: str, changes: list[str], unmeasured_flags: list[bool]) -> TaskTally:
    return TaskTally(task, len(changes), changes.count("rescue"), changes.count("harm"), sum(unmeasured_flags))


def budget_shaped(codes: list[str | None]) -> bool:
    """Spec section 2: at least 2 of 4 decision cells ended BUDGET_EXCEEDED or COMMAND_TIMEOUT."""
    return sum(1 for code in codes if code in ("BUDGET_EXCEEDED", "COMMAND_TIMEOUT")) >= 2


def decide(tallies: dict[str, TaskTally]) -> tuple[str, str]:
    """Spec section 5 and its pre-run amendment (section 7.1). Returns
    (outcome, reason); outcome is "go", "verify" or "not-the-lever"."""
    qualifying = [t for t in BUDGET_SHAPED if not tallies[t].insufficient and tallies[t].net >= 1]
    floor_harm = sum(tallies[t].harms for t in FLOOR)
    floor_insufficient = [t for t in FLOOR if tallies[t].insufficient]
    detail = f"qualifying budget-shaped tasks {qualifying or 'none'}; floor harm cells {floor_harm}; insufficient floor tasks {floor_insufficient or 'none'}"
    if len(qualifying) >= 2 and floor_harm < 2 and not floor_insufficient:
        return "go", detail
    if qualifying:
        return "verify", detail
    if all(tallies[t].net < 1 for t in BUDGET_SHAPED):
        return "not-the-lever", detail
    return "verify", detail + "; a budget-shaped task has net rescues >= 1 but is insufficient (section 7.1)"


def project_markers(path: Path) -> list[Path]:
    """Config files pytest could pick up from ``path`` or any ancestor."""
    return [folder / name for folder in (path, *path.parents) for name in PROJECT_MARKERS if (folder / name).is_file()]


# --- impure: replay, harvest, grade -------------------------------------------


@dataclass(slots=True)
class Replay:
    patch: str = ""
    bash_touched: dict[int, tuple[str, ...]] = field(default_factory=dict)
    skipped_writer_turns: list[int] = field(default_factory=list)
    anchor_miss_turns: list[int] = field(default_factory=list)
    applied: dict[str, int] = field(default_factory=lambda: {"write": 0, "edit": 0, "bash": 0})


def _git(work: Path, *args: str) -> str:
    from satyrn_evals.workspace import GIT_SAFETY_CONFIG

    return subprocess.run(["git", *GIT_SAFETY_CONFIG, *args], cwd=work, capture_output=True, text=True, check=True).stdout


def _digests(work: Path) -> dict[str, str]:
    found = {}
    for path in work.rglob("*"):
        rel = path.relative_to(work).as_posix()
        if path.is_file() and not rel.startswith(".git/") and "/.venv/" not in f"/{rel}" and "__pycache__" not in rel:
            found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def replay(spec: CellSpec, steps: list[Step], cwd: str | None, source_paths: tuple[str, ...], stop_after_turn: int | None) -> Replay:
    """Apply the cell's landed writes to a fresh copy of the task base, through the end
    of ``stop_after_turn`` (None: every step), and harvest the patch as the harness does."""
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch

    assert spec.attempt not in DECISION_IDS or spec.group == "decision"
    work = WORK / f"{spec.attempt}-{'final' if stop_after_turn is None else f'turn-{stop_after_turn:02d}'}"
    if work.exists():
        shutil.rmtree(work)
    try:
        shutil.copytree(TASKS / spec.task / "base", work, symlinks=True)
        _git(work, "init", "-q")
        _git(work, "add", "-A")
        _git(work, "-c", "user.email=replay@localhost", "-c", "user.name=replay", "commit", "-q", "-m", "base")
        base = _git(work, "rev-parse", "HEAD").strip()
        out = Replay()
        for step in steps:
            if stop_after_turn is not None and step.turn > stop_after_turn:
                break
            if step.name == "write" and not step.is_error:
                path = tree_path(step.args.get("path", ""), cwd)
                if path is not None:
                    target = work / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(str(step.args.get("content", "")))
                    out.applied["write"] += 1
            elif step.name == "edit" and not step.is_error:
                path = tree_path(step.args.get("path", ""), cwd)
                if path is None:
                    continue
                target = work / path
                edits = step.args.get("edits") or (
                    [{"oldText": step.args.get("oldText", ""), "newText": step.args.get("newText", "")}] if step.args.get("oldText") else []
                )
                text = target.read_text() if target.is_file() else None
                for edit in edits:
                    old, new = str(edit.get("oldText", "")), str(edit.get("newText", ""))
                    if text is not None and old and old in text:
                        text = text.replace(old, new, 1)
                    else:
                        out.anchor_miss_turns.append(step.turn)
                if text is not None:
                    target.write_text(text)
                    out.applied["edit"] += 1
            elif step.name == "bash":
                command = str(step.args.get("command", ""))
                plan = plan_bash(command, cwd)
                if plan.replay is not None:
                    before = _digests(work)
                    done = subprocess.run(
                        ["/bin/bash", "-c", plan.replay], cwd=work, capture_output=True, timeout=10,
                        env={"PATH": os.environ["PATH"], "HOME": os.fspath(work), "TMPDIR": os.fspath(WORK)},
                    )
                    after = _digests(work)
                    out.bash_touched[step.index] = tuple(sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p)))
                    out.applied["bash"] += 1
                    if done.returncode != 0 and not step.is_error:
                        out.skipped_writer_turns.append(step.turn)
                if plan.remainder and could_write_source(plan.remainder, source_paths, cwd):
                    out.skipped_writer_turns.append(step.turn)
        tempfile.tempdir = os.fspath(WORK)
        out.patch = build_cumulative_patch(work, base, os.environ, exclude=RESIDUE_EXCLUDES).patch_text
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def grade(task: str, patch: str, grade_root: Path, name: str) -> str:
    """``satyrn-evals grade`` on the harvested patch; the receipt's verdict."""
    folder = grade_root / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / "patch.diff").write_text(patch)
    subprocess.run(
        [os.fspath(Path(sys.executable).parent / "satyrn-evals"), "grade", task, "patch.diff", "--receipt", "receipt.json"],
        cwd=folder, capture_output=True, text=True, timeout=900,
        env={**os.environ, "UV_OFFLINE": "1", "TMPDIR": os.fspath(folder)},
    )
    receipt = json.loads((folder / "receipt.json").read_text())
    return receipt["verdict"]


def cell_dir(spec: CellSpec) -> Path:
    matches = sorted((RUNS / spec.run / spec.arm).glob(f"*-{spec.attempt}"))
    if len(matches) != 1:
        raise FileNotFoundError(f"{spec.run}/{spec.arm}: {len(matches)} directories end in {spec.attempt}")
    return matches[0]


def measure(spec: CellSpec, grade_root: Path) -> dict:
    manifest = json.loads((TASKS / spec.task / "manifest.json").read_text())
    source_paths = tuple(manifest["source_paths"])
    folder = cell_dir(spec)
    attempt = json.loads((folder / "attempt.json").read_text())
    code, harness_verdict = attempt.get("code"), attempt.get("verdict")
    actual = actual_pass(code, harness_verdict)
    row: dict = {"task": spec.task, "group": spec.group, "run": spec.run, "arm": spec.arm, "attempt": spec.attempt,
                 "code": code, "harness_verdict": harness_verdict, "actual": "pass" if actual else "not-pass"}
    trigger = None
    final_verdict = trigger_verdict = raised = None
    skipped: list[int] = []
    misses: list[int] = []
    try:
        events = parse_events((folder / "transcript.txt").read_text())
        cwd = session_cwd(events)
        steps = steps_of(events)
        full = replay(spec, steps, cwd, source_paths, None)
        skipped, misses = full.skipped_writer_turns, full.anchor_miss_turns
        row["applied"] = full.applied
        trigger = find_trigger(steps, source_edit_indices(steps, source_paths, cwd, full.bash_touched))
        if harness_verdict in GRADED:
            final_verdict = grade(spec.task, full.patch, grade_root, f"{spec.attempt}-final")
        if trigger is not None and trigger.within_budget:
            at = replay(spec, steps, cwd, source_paths, trigger.turn)
            skipped = sorted(set(skipped) | set(at.skipped_writer_turns))
            misses = sorted(set(misses) | set(at.anchor_miss_turns))
            trigger_verdict = grade(spec.task, at.patch, grade_root, f"{spec.attempt}-turn-{trigger.turn:02d}")
    except Exception as exc:  # spec section 4: replay or grading raises -> unmeasured
        raised = f"{type(exc).__name__}: {exc}"[:200]
    fid = fidelity(harness_verdict, final_verdict)
    reasons = unmeasured_reasons(
        fidelity_result=fid, harness_verdict=harness_verdict, final_verdict=final_verdict, trigger=trigger,
        skipped_writer_turns=skipped, anchor_miss_turns=misses, raised=raised,
    )
    counter = counterfactual_pass(actual, trigger, reasons, trigger_verdict)
    row.update({
        "trigger": asdict(trigger) if trigger else None,
        "trigger_verdict": trigger_verdict,
        "final_replay_verdict": final_verdict,
        "fidelity": fid,
        "counterfactual": "pass" if counter else "not-pass",
        "change": change(actual, counter),
        "unmeasured": reasons,
        "skipped_writer_turns": sorted(set(skipped)),
        "anchor_miss_turns": sorted(set(misses)),
    })
    return row


def stamp(argv: list[str]) -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=EVALS, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "evidence/2026-09-15-finishing-counterfactual/counterfactual.py"], cwd=EVALS, capture_output=True, text=True).stdout.strip())
    return {"evals_commit": commit, "evals_dirty": dirty, "command": " ".join(["counterfactual.py", *argv])}


def table(rows: list[dict], header: dict) -> str:
    lines = [
        f"<!-- evals {header['evals_commit']}{' (dirty)' if header['evals_dirty'] else ''}; {header['command']} -->",
        "",
        "| task | group | attempt | code | trigger turn | tokens at trigger | actual | counterfactual | rescue | harm | fidelity | unmeasured |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        t = r["trigger"]
        turn = "-" if t is None else f"{t['turn']}{'' if t['within_budget'] else ' (over budget)'}"
        tokens = "-" if t is None else str(t["output_tokens"])
        lines.append(
            f"| {r['task']} | {r['group']} | {r['attempt']} | {r['code']}{'-' + r['harness_verdict'] if r['harness_verdict'] else ''} "
            f"| {turn} | {tokens} | {r['actual']} | {r['counterfactual']} | {'1' if r['change'] == 'rescue' else ''} "
            f"| {'1' if r['change'] == 'harm' else ''} | {r['fidelity']} | {'; '.join(r['unmeasured'])} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="counterfactual.py")
    parser.add_argument("--phase", choices=("debug", "decision"), required=True)
    parser.add_argument("--cell", action="append", default=[], help="debug only: one attempt suffix (repeatable)")
    parser.add_argument("--grade-root", type=Path, default=DEFAULT_GRADE_ROOT, help="receipts and grader scratch; no Python project above it")
    args = parser.parse_args(argv)
    try:
        specs = select_cells(args.phase, tuple(args.cell))
    except ValueError as exc:
        print(f"counterfactual: {exc}", file=sys.stderr)
        return 2
    out = HERE if args.phase == "decision" else HERE / "debug"
    if args.phase == "decision" and (out / "cells.json").exists():
        print("counterfactual: cells.json exists; the decision phase runs once (spec section 6)", file=sys.stderr)
        return 2
    grade_root = args.grade_root.resolve() / args.phase
    if markers := project_markers(grade_root.parent):
        print(f"counterfactual: --grade-root sits under {markers[0]}; pytest would read it while grading", file=sys.stderr)
        return 2
    header = stamp(argv)
    shutil.rmtree(WORK, ignore_errors=True)  # a scratch tree left in the checkout breaks `just gates` collection
    WORK.mkdir()
    grade_root.mkdir(parents=True, exist_ok=True)
    try:
        return _run(args.phase, specs, grade_root, header)
    finally:
        shutil.rmtree(WORK, ignore_errors=True)


def _run(phase: str, specs: tuple[CellSpec, ...], grade_root: Path, header: dict) -> int:
    out = HERE if phase == "decision" else HERE / "debug"
    if phase == "decision":
        # Spec section 2: the recorded codes are the pre-registration's; refuse before measuring if any differs.
        codes: dict[str, list[str | None]] = {}
        for spec in specs:
            attempt = json.loads((cell_dir(spec) / "attempt.json").read_text())
            if (attempt.get("code"), attempt.get("verdict")) != RECORDED[spec.attempt]:
                print(f"counterfactual: {spec.attempt} is not the spec's recorded code", file=sys.stderr)
                return 2
            codes.setdefault(spec.task, []).append(attempt.get("code"))
        if [task for task, task_codes in codes.items() if budget_shaped(task_codes)] != list(BUDGET_SHAPED):
            print("counterfactual: recorded codes do not select the spec's budget-shaped tasks", file=sys.stderr)
            return 2
    rows = []
    for spec in specs:
        row = measure(spec, grade_root)
        rows.append(row)
        print(f"{spec.task} {spec.attempt} {row['code']} trigger={row['trigger']} cf={row['counterfactual']} change={row['change']} fidelity={row['fidelity']} unmeasured={row['unmeasured']}", flush=True)
    out.mkdir(exist_ok=True)
    (out / "cells.json").write_text(json.dumps({**header, "cells": rows}, indent=1) + "\n")
    (out / "table.md").write_text(table(rows, header))
    if phase == "decision":
        tallies = {}
        for task in (*BUDGET_SHAPED, *FLOOR):
            mine = [r for r in rows if r["task"] == task]
            tallies[task] = tally(task, [r["change"] for r in mine], [bool(r["unmeasured"]) for r in mine])
        outcome, reason = decide(tallies)
        lines = [f"evals {header['evals_commit']}{' (dirty)' if header['evals_dirty'] else ''}", header["command"], ""]
        for task, t in tallies.items():
            kind = "budget-shaped" if task in BUDGET_SHAPED else "floor"
            lines.append(f"{task} ({kind}): rescues {t.rescues}, harms {t.harms}, net {t.net}, unmeasured {t.unmeasured}{', insufficient' if t.insufficient else ''}")
        lines += ["", f"decision: {outcome}", reason]
        (out / "decision.txt").write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
