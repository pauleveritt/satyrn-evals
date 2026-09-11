"""The V16 pathology census: offline, arm-neutral, and never voids a cell.

`archive/2026-09-07-pre-reset/docs/superpowers/specs/2026-09-07-v16-pathology-census-design.md`
is the confirmed design; this module implements its sections 2-4. Where V10
(`pathology.py`) marks a whole transcript ``measured: false`` on one
unrecognised event -- blinding it on exactly the cells worth reading -- the
census scans what it can and reports that refusal (``v10_unmeasured``) as
one pathology among others (spec §3). Every detector here is pure: text or
a parsed event list in, a magnitude out, no filesystem, no subprocess, no
model.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from satyrn_evals.adapters.pi_implementer import TRANSCRIPT_NAME
from satyrn_evals.pathology import count_transcript

type PathologyName = Literal[
    "schema_refusal",
    "tool_not_found",
    "unknown_tool",
    "read_lock",
    "anchor_refusal",
    "rejected_edit",
    "noop_edit",
    "stall",
    "v10_unmeasured",
]

#: Order matches the spec §2 table; the table and JSON both walk this order.
PATHOLOGY_NAMES: tuple[PathologyName, ...] = (
    "schema_refusal",
    "tool_not_found",
    "unknown_tool",
    "read_lock",
    "anchor_refusal",
    "rejected_edit",
    "noop_edit",
    "stall",
    "v10_unmeasured",
)

#: The known tool vocabulary for `unknown_tool` (spec §2). This grows as the
#: product does -- adding a real tool means adding its name here, not
#: reworking the detector.
KNOWN_TOOL_NAMES = frozenset(
    {"read", "bash", "edit", "write", "run_tests", "run_self_test"}
)

_SCHEMA_REFUSAL_MARKER = "Validation failed for tool"
_TOOL_NOT_FOUND_RE = re.compile(r"^Tool\s+\S+\s+not found\b")
# Corrected 2026-09-07: the first version matched only "no change|no matching
# text", which caught 851 of pi's "No changes made" results and **none** of
# its 1,813 "Could not find the exact text" ones -- so `noop_edit`
# undercounted by roughly two thirds wherever pi's own edit tool refused.
# Corrected 2026-09-11 (V2b cause 3): that fix bucketed a *rejected* edit
# with a *true* no-op, leaving `noop_edit` ambiguous. The refusal shapes now
# land in `rejected_edit`; `noop_edit` counts only "nothing to do" results.
_REJECTED_EDIT_RE = re.compile(
    r"could not find the exact text|validation failed for tool", re.IGNORECASE
)
_NOOP_EDIT_RE = re.compile(
    r"no changes? made|no matching text|replacement produced identical content",
    re.IGNORECASE,
)

#: Naming threshold for the two run-length pathologies: a run of 1 is just
#: "a tool call happened" and is not worth naming a cell over. Count-type
#: pathologies are named whenever their magnitude is nonzero.
_RUN_LENGTH_NAMING_FLOOR = 2


@dataclass(frozen=True, slots=True)
class CellCensus:
    """One cell's pathology magnitudes -- never `measured:false`.

    Grouping fields (`batch`/`task`/`arm`/`engine_commit`) may be `None`
    when the surrounding `schedule.json`/`preflight.json` could not be
    found or parsed; a census never guesses a value it cannot support
    (spec §3).
    """

    path: Path
    batch: str | None
    task: str | None
    arm: str | None
    engine_commit: str | None
    events_scanned: int
    schema_refusal: int
    tool_not_found: int
    unknown_tool: int
    read_lock: int
    anchor_refusal: int
    rejected_edit: int
    noop_edit: int
    stall: int
    v10_unmeasured: bool
    v10_reason: str | None

    def magnitude(self, name: PathologyName) -> int | bool:
        if name == "v10_unmeasured":
            return self.v10_unmeasured
        return getattr(self, name)

    def is_present(self, name: PathologyName) -> bool:
        magnitude = self.magnitude(name)
        if name == "v10_unmeasured":
            return bool(magnitude)
        # `stall` is reported as a magnitude but never names a cell:
        # measured 2026-09-07, it was nonzero in every cell of every batch,
        # and a presence flag that is always true names nothing. Its
        # magnitude is also confounded on retained cells, where the engine
        # reported no-op edits as applied and so reset the run.
        if name == "read_lock":
            return magnitude >= _RUN_LENGTH_NAMING_FLOOR
        return magnitude > 0

    def to_record(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "batch": self.batch,
            "task": self.task,
            "arm": self.arm,
            "engine_commit": self.engine_commit,
            "events_scanned": self.events_scanned,
            "schema_refusal": self.schema_refusal,
            "tool_not_found": self.tool_not_found,
            "unknown_tool": self.unknown_tool,
            "read_lock": self.read_lock,
            "anchor_refusal": self.anchor_refusal,
            "rejected_edit": self.rejected_edit,
            "noop_edit": self.noop_edit,
            "stall": self.stall,
            "v10_unmeasured": self.v10_unmeasured,
            "v10_reason": self.v10_reason,
        }


def _parse_events(text: str) -> list[dict]:
    """Lenient line-by-line JSON parse: bad lines are skipped, never fatal.

    Unlike `pathology.count_transcript`, this never refuses the whole
    document -- an unparseable transcript still yields whatever events its
    well-formed lines contain (spec §3, the no-void rule).
    """
    events: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _result_text(result: object) -> str:
    """Newline-joined text parts of a `tool_execution_end` result."""
    if not isinstance(result, dict):
        return ""
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for part in content:
        if (
            isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
        ):
            parts.append(part["text"])
    return "\n".join(parts)


def _is_anchor_refusal(end_event: dict) -> bool:
    result = end_event.get("result")
    if not isinstance(result, dict):
        return False
    details = result.get("details")
    return (
        isinstance(details, dict)
        and details.get("satyrn") is True
        and details.get("ok") is False
    )


def detect_schema_refusal(events: list[dict]) -> int:
    """Count of tool results carrying a schema validation failure."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_end"
        and _SCHEMA_REFUSAL_MARKER in _result_text(event.get("result"))
    )


def detect_tool_not_found(events: list[dict]) -> int:
    """Count of results naming an unregistered tool."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_end"
        and _TOOL_NOT_FOUND_RE.search(_result_text(event.get("result")))
    )


def detect_unknown_tool(events: list[dict]) -> int:
    """Count of calls to a tool name outside `KNOWN_TOOL_NAMES`."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_start"
        and isinstance(event.get("toolName"), str)
        and event["toolName"] not in KNOWN_TOOL_NAMES
    )


def detect_anchor_refusal(events: list[dict]) -> int:
    """Count of mutator refusals: `details.satyrn: true, ok: false`."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_end" and _is_anchor_refusal(event)
    )


# `rejected_edit` is not disjoint with `schema_refusal`: a schema refusal's
# "Validation failed for tool" text also matches `_REJECTED_EDIT_RE`, so the
# two counts overlap and must not be summed.
def detect_rejected_edit(events: list[dict]) -> int:
    """Count of edit results refusing to apply (anchor mismatch or schema)."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_end"
        and event.get("toolName") == "edit"
        and _REJECTED_EDIT_RE.search(_result_text(event.get("result")))
    )


def detect_noop_edit(events: list[dict]) -> int:
    """Count of edit results doing nothing: the content already matched."""
    return sum(
        1
        for event in events
        if event.get("type") == "tool_execution_end"
        and event.get("toolName") == "edit"
        and _NOOP_EDIT_RE.search(_result_text(event.get("result")))
    )


def detect_read_lock(events: list[dict]) -> int:
    """Longest run of identical consecutive tool calls before the first edit.

    Frozen by `docs/superpowers/specs/2026-09-06-v13d-read-lock-attribution.md`
    §3: "identical" means same tool name and same arguments; the window
    ends -- exclusive -- at the first `tool_execution_start` naming `edit`.
    """
    starts = [e for e in events if e.get("type") == "tool_execution_start"]
    window: list[dict] = []
    for start in starts:
        if start.get("toolName") == "edit":
            break
        window.append(start)
    longest = 0
    current = 0
    previous_key: tuple[object, str] | None = None
    for start in window:
        key = (start.get("toolName"), json.dumps(start.get("args"), sort_keys=True))
        current = current + 1 if key == previous_key else 1
        previous_key = key
        longest = max(longest, current)
    return longest


def _edit_applied(end_event: dict) -> bool:
    """An edit result indicating success: not refused, not a no-op."""
    if end_event.get("toolName") != "edit":
        return False
    if end_event.get("isError"):
        return False
    if _is_anchor_refusal(end_event):
        return False
    text = _result_text(end_event.get("result"))
    if _SCHEMA_REFUSAL_MARKER in text:
        return False
    return not (_REJECTED_EDIT_RE.search(text) or _NOOP_EDIT_RE.search(text))


def detect_stall(events: list[dict]) -> int:
    """Longest run of tool calls without an applied edit.

    A refused or no-op edit is still a tool call in the run -- it does not
    reset the count, only an *applied* edit does (spec §2).
    """
    ends = [e for e in events if e.get("type") == "tool_execution_end"]
    longest = 0
    current = 0
    for end in ends:
        if _edit_applied(end):
            # The applied edit itself ends the run rather than extending
            # it: it is the event the run is measured *up to*.
            longest = max(longest, current)
            current = 0
        else:
            current += 1
    return max(longest, current)


def detect_v10_unmeasured(text: str) -> tuple[bool, str | None]:
    """Whether V10's parser (`pathology.count_transcript`) would refuse this
    transcript, and its reason."""
    block = count_transcript(text, had_patch=False)
    if block.measured:
        return False, None
    return True, block.reason


@dataclass(frozen=True, slots=True)
class _BatchContext:
    """What one `schedule.json` + sibling `preflight.json` establishes."""

    batch: str
    task: str | None
    engine_commit: str | None
    cell_arms: dict[str, str]  # cell dir name -> arm


def _load_batch_context(schedule_path: Path, *, batch_label: str) -> _BatchContext:
    task: str | None = None
    cell_arms: dict[str, str] = {}
    try:
        schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        schedule = {}
    if isinstance(schedule, dict):
        raw_task = schedule.get("task")
        task = raw_task if isinstance(raw_task, str) else None
        cells = schedule.get("cells")
        if isinstance(cells, list):
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                cell_dir = cell.get("dir")
                arm = cell.get("arm")
                if isinstance(cell_dir, str) and isinstance(arm, str):
                    cell_arms[cell_dir] = arm
    engine_commit: str | None = None
    preflight_path = schedule_path.parent / "preflight.json"
    try:
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        preflight = {}
    if isinstance(preflight, dict):
        raw_commit = preflight.get("engine_commit")
        engine_commit = raw_commit if isinstance(raw_commit, str) else None
    return _BatchContext(
        batch=batch_label, task=task, engine_commit=engine_commit, cell_arms=cell_arms
    )


def _batch_label(root: Path, schedule_dir: Path) -> str:
    if schedule_dir == root:
        return root.name
    return f"{root.name}/{schedule_dir.relative_to(root)}"


def _arm_from_dir_name(dir_name: str) -> str | None:
    """Fallback arm guess from a `cell-NNN-ARM` directory name."""
    parts = dir_name.split("-")
    if len(parts) >= 3 and parts[0] == "cell":
        return "-".join(parts[2:]) or None
    return None


def _cell_dir_for(transcript_path: Path, root: Path) -> Path | None:
    """The `cell-*` ancestor directory of a transcript, if any, under root."""
    try:
        relative = transcript_path.relative_to(root)
    except ValueError:
        return None
    for ancestor in relative.parents:
        name = ancestor.name if str(ancestor) != "." else ""
        if name.startswith("cell-"):
            return root / ancestor
    return None


def _census_one_transcript(
    transcript_path: Path,
    *,
    root: Path,
    contexts: dict[Path, _BatchContext],
) -> CellCensus:
    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    events = _parse_events(text)

    batch: str | None = None
    task: str | None = None
    arm: str | None = None
    engine_commit: str | None = None

    cell_dir = _cell_dir_for(transcript_path, root)
    if cell_dir is not None:
        # Find the nearest ancestor schedule directory that knows this cell.
        for schedule_dir, context in contexts.items():
            if cell_dir.name in context.cell_arms and (
                schedule_dir == cell_dir.parent or schedule_dir in cell_dir.parents
            ):
                batch = context.batch
                task = context.task
                arm = context.cell_arms[cell_dir.name]
                engine_commit = context.engine_commit
                break
        if arm is None:
            arm = _arm_from_dir_name(cell_dir.name)
        if batch is None:
            batch = root.name

    v10_refused, v10_reason = detect_v10_unmeasured(text)

    return CellCensus(
        path=transcript_path,
        batch=batch,
        task=task,
        arm=arm,
        engine_commit=engine_commit,
        events_scanned=len(events),
        schema_refusal=detect_schema_refusal(events),
        tool_not_found=detect_tool_not_found(events),
        unknown_tool=detect_unknown_tool(events),
        read_lock=detect_read_lock(events),
        anchor_refusal=detect_anchor_refusal(events),
        rejected_edit=detect_rejected_edit(events),
        noop_edit=detect_noop_edit(events),
        stall=detect_stall(events),
        v10_unmeasured=v10_refused,
        v10_reason=v10_reason,
    )


def census_root(root: Path) -> list[CellCensus]:
    """Walk one RUNS_ROOT: every `schedule.json` builds batch context, then
    every retained transcript becomes one `CellCensus`. Both names the two
    routes write are discovered -- the Baseline attempt's `transcript.txt`
    and the packet route's `harness/.satyrn-implementer-transcript.jsonl`
    (the adapter's `TRANSCRIPT_NAME`); a census blind to the second returns
    zero cells on a packet-route root. Never raises on a missing or
    malformed schedule/preflight -- those degrade to `None` fields, not a
    refusal (spec §3)."""
    contexts: dict[Path, _BatchContext] = {}
    for schedule_path in sorted(root.rglob("schedule.json")):
        label = _batch_label(root, schedule_path.parent)
        contexts[schedule_path.parent] = _load_batch_context(
            schedule_path, batch_label=label
        )
    cells: list[CellCensus] = []
    for transcript_path in sorted(root.rglob("transcript.txt")):
        cells.append(
            _census_one_transcript(transcript_path, root=root, contexts=contexts)
        )
    for transcript_path in sorted(root.rglob(TRANSCRIPT_NAME)):
        cells.append(
            _census_one_transcript(transcript_path, root=root, contexts=contexts)
        )
    return cells


@dataclass(frozen=True, slots=True)
class GroupKey:
    batch: str | None
    task: str | None
    arm: str | None
    engine_commit: str | None


@dataclass(frozen=True, slots=True)
class GroupTotals:
    """Sum of count-type magnitudes and cell count for one group."""

    key: GroupKey
    cell_count: int
    totals: dict[PathologyName, int] = field(default_factory=dict)


def aggregate(cells: list[CellCensus]) -> list[GroupTotals]:
    """Group by (batch, task, arm, engine_commit); sum count-type
    magnitudes, and count cells reaching the naming floor for the two
    run-length pathologies (spec §3: never pooled across arms into one
    number -- each group stays keyed by all four fields)."""
    grouped: dict[GroupKey, list[CellCensus]] = defaultdict(list)
    for cell in cells:
        key = GroupKey(cell.batch, cell.task, cell.arm, cell.engine_commit)
        grouped[key].append(cell)
    groups: list[GroupTotals] = []
    for key, group_cells in grouped.items():
        totals: dict[PathologyName, int] = {}
        for name in PATHOLOGY_NAMES:
            if name == "v10_unmeasured":
                totals[name] = sum(1 for c in group_cells if c.v10_unmeasured)
            elif name in ("read_lock", "stall"):
                totals[name] = sum(
                    1 for c in group_cells if c.is_present(name)
                )
            else:
                totals[name] = sum(int(c.magnitude(name)) for c in group_cells)
        groups.append(
            GroupTotals(key=key, cell_count=len(group_cells), totals=totals)
        )
    groups.sort(
        key=lambda g: (
            g.key.batch or "",
            g.key.task or "",
            g.key.arm or "",
            g.key.engine_commit or "",
        )
    )
    return groups


def render_table(groups: list[GroupTotals]) -> str:
    if not groups:
        return "no transcripts found"
    header = ["batch", "task", "arm", "engine_commit", "cells", *PATHOLOGY_NAMES]
    rows = [header]
    for group in groups:
        rows.append(
            [
                group.key.batch or "-",
                group.key.task or "-",
                group.key.arm or "-",
                (group.key.engine_commit or "-")[:12],
                str(group.cell_count),
                *[str(group.totals[name]) for name in PATHOLOGY_NAMES],
            ]
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    lines = [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))
        for row in rows
    ]
    return "\n".join(lines)


def render_named_cells(cells: list[CellCensus]) -> str:
    lines: list[str] = []
    for name in PATHOLOGY_NAMES:
        named = [cell for cell in cells if cell.is_present(name)]
        if not named:
            continue
        lines.append(f"{name}:")
        for cell in named:
            magnitude = cell.magnitude(name)
            extra = f" ({cell.v10_reason})" if name == "v10_unmeasured" else ""
            lines.append(f"  {magnitude}{extra}  {cell.path}")
    return "\n".join(lines)


def run_census(roots: list[Path]) -> list[CellCensus]:
    cells: list[CellCensus] = []
    for root in roots:
        if not root.exists():
            print(f"satyrn-evals: census: {root} does not exist, skipping", file=sys.stderr)
            continue
        cells.extend(census_root(root))
    return cells


def build_arg_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    census_p = sub.add_parser(
        "census",
        help="scan retained transcripts for named pathologies (no model, no gate)",
    )
    census_p.add_argument("runs_root", nargs="+", help="one or more run output roots")
    census_p.add_argument(
        "--json", dest="json_path", default=None, help="write the full per-cell record here"
    )
    return census_p


def run_cli(runs_roots: list[str], json_path: str | None) -> int:
    roots = [Path(root) for root in runs_roots]
    cells = run_census(roots)
    groups = aggregate(cells)
    print(render_table(groups))
    named = render_named_cells(cells)
    if named:
        print()
        print(named)
    if json_path is not None:
        Path(json_path).write_text(
            json.dumps([cell.to_record() for cell in cells], indent=2, default=str)
        )
    return 0
