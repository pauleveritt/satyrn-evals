"""Per-arm cost tables from retained comparison cells, no model.

Usage: ``uv run python evidence/2026-10-02-engine-budget/cells.py RUN_DIR...``
where each RUN_DIR is a launch directory holding ``baseline/`` and
``engine/`` with one ``<task>-<stamp>/`` cell each (``transcript.txt``,
``timeline.jsonl``, ``attempt.json``).

Rules: tool calls are counted from ``tool_execution_start``, one per call;
context for a turn is ``usage.input + usage.cacheRead``; medians carry their
range; denominators (cells, delivered passes) are printed; nothing is pooled
across tasks or arms. Pre-registered EB0 counts (spec §5) are the per-cell
columns: calls before the first landed edit and how many touch ``tests/``,
test files written, rejected edit/write calls by error shape, automatic
self-tests and their note bytes, edit-result bytes, turns from the finish
steer to stop, and ``confinement_refused`` events.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

EDIT_TOOLS = {"edit", "write"}
ENGINE_NOTE = "[satyrn-engine note"
SELF_TEST_NOTE = "The Engine also ran self_test"


def _events(path: Path):
    with path.open() as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _text(message: dict) -> str:
    return "".join(part.get("text", "") for part in message.get("content", []) if isinstance(part, dict))


def _error_shape(text: str) -> str:
    if text.startswith("Validation failed"):
        return "schema"
    for code in ("ANCHOR_MISSING", "REVISION_STALE", "NO_CHANGE_REQUESTED", "ANCHOR_ALREADY_APPLIED",
                 "ANCHOR_AMBIGUOUS", "INVALID_REQUEST", "REVISION_UNAVAILABLE"):
        if code in text:
            return code
    if "Could not find" in text:
        return "anchor (pi)"
    if "outside the attempt worktree" in text or "protected path" in text:
        return "confinement"
    return "other"


def read_cell(cell: Path) -> dict:
    verdict = json.loads((cell / "attempt.json").read_text()).get("verdict")
    out = turns = calls = peak = 0
    pre_calls = pre_test_calls = 0
    first_edit_seen = False
    test_files: set[str] = set()
    rejected: Counter[str] = Counter()
    self_tests = 0
    note_bytes = edit_result_bytes = 0
    steer_at: int | None = None
    confinement_refused = 0
    for event in _events(cell / "transcript.txt"):
        kind = event.get("type")
        if kind == "tool_execution_start":
            calls += 1
            name = event.get("toolName")
            args = event.get("args") or {}
            if name in EDIT_TOOLS and str(args.get("path", "")).startswith("tests/"):
                test_files.add(args["path"])
            if not first_edit_seen:
                pre_calls += 1
                if "test" in json.dumps(args):
                    pre_test_calls += 1
            continue
        if kind == "entry_appended" and event.get("entryType") == "confinement_refused":
            confinement_refused += 1
            continue
        if kind != "message_end":
            continue
        message = event["message"]
        role = message.get("role")
        if role == "assistant":
            usage = message["usage"]
            turns += 1
            out += usage["output"]
            peak = max(peak, usage["input"] + usage.get("cacheRead", 0))
            if not first_edit_seen and any(
                part.get("type") == "toolCall" and part.get("name") in EDIT_TOOLS
                for part in message.get("content", []) if isinstance(part, dict)
            ):
                first_edit_seen = True
        elif role == "custom" and message.get("customType") == "finish_nudged":
            steer_at = steer_at if steer_at is not None else turns
        elif role == "toolResult":
            text = _text(message)
            if message.get("isError") and message.get("toolName") in EDIT_TOOLS:
                rejected[_error_shape(text)] += 1
            elif message.get("toolName") == "edit":
                edit_result_bytes += len(text)
            if SELF_TEST_NOTE in text:
                self_tests += 1
            at = text.find(ENGINE_NOTE)
            if at >= 0:
                note_bytes += len(text) - at
    stamps = [e["at"] for e in _events(cell / "timeline.jsonl")] if (cell / "timeline.jsonl").exists() else []
    return {
        "cell": cell.name, "verdict": verdict, "output": out, "turns": turns, "calls": calls,
        "peak": peak, "span_min": (max(stamps) - min(stamps)) / 60 if stamps else None,
        "pre_calls": pre_calls, "pre_test_calls": pre_test_calls, "test_files": len(test_files),
        "rejected": dict(rejected), "self_tests": self_tests, "note_bytes": note_bytes,
        "edit_result_bytes": edit_result_bytes,
        "steer_to_stop": (turns - steer_at) if steer_at is not None else None,
        "confinement_refused": confinement_refused,
    }


def _median(values: list[float]) -> str:
    values = [v for v in values if v is not None]
    if not values:
        return "—"
    med = statistics.median(values)
    fmt = (lambda v: f"{v:,.1f}") if any(isinstance(v, float) and v != int(v) for v in values) else (lambda v: f"{int(v):,}")
    return f"{fmt(med)} ({fmt(min(values))}–{fmt(max(values))})"


def report(run_dir: Path) -> None:
    for arm in ("baseline", "engine"):
        arm_dir = run_dir / arm
        if not arm_dir.is_dir():
            continue
        cells = [read_cell(c) for c in sorted(arm_dir.iterdir()) if (c / "attempt.json").exists()]
        passes = [c for c in cells if c["verdict"] == "pass"]
        print(f"\n== {run_dir.name} / {arm}: cells={len(cells)} delivered passes={len(passes)}")
        for label, key in (("output tokens", "output"), ("turns", "turns"), ("tool calls", "calls"),
                           ("peak context", "peak"), ("span (min)", "span_min")):
            print(f"  {label:14} per pass: {_median([c[key] for c in passes])}")
        print(f"  calls before first edit: {_median([c['pre_calls'] for c in passes])}; "
              f"touching tests: {_median([c['pre_test_calls'] for c in passes])}")
        print(f"  cells writing a test file: {sum(1 for c in cells if c['test_files'])} of {len(cells)}")
        shapes: Counter[str] = Counter()
        for c in cells:
            shapes.update(c["rejected"])
        print(f"  rejected edit/write calls: {sum(shapes.values())} in "
              f"{sum(1 for c in cells if c['rejected'])} of {len(cells)} cells; shapes {dict(shapes)}")
        print(f"  automatic self-tests: {sum(c['self_tests'] for c in cells)}; "
              f"note bytes per cell: {_median([c['note_bytes'] for c in cells])}; "
              f"edit-result bytes per cell: {_median([c['edit_result_bytes'] for c in cells])}")
        print(f"  turns from steer to stop: {_median([c['steer_to_stop'] for c in cells])}; "
              f"confinement_refused: {sum(c['confinement_refused'] for c in cells)}")
        if arm == "engine" and (run_dir / "baseline").is_dir():
            base = [read_cell(c) for c in sorted((run_dir / "baseline").iterdir()) if (c / "attempt.json").exists()]
            bp = [c["output"] for c in base if c["verdict"] == "pass"]
            ep = [c["output"] for c in passes]
            higher = sum(1 for e in ep for b in bp if e > b)
            print(f"  pairwise: engine higher in {higher} of {len(ep) * len(bp)} cross-arm pass pairs")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for arg in argv[1:]:
        report(Path(arg).expanduser())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
