#!/usr/bin/env python3
"""The pre-registered post-hoc read for `selfhost-preflight-quiet`, night 3.

This is the script `postreg.md`'s "recompute command" section promises: a
source-pattern read over each retained night-3 cell's harvested patch, for
the four columns `postreg.md` pre-registers (`maxsplit`, `one_decimal`,
`inputs_keys`, `cli_last`), never touching a cell's grade or verdict.

No model, no network, no GPU, no subprocess: everything here is text
already on disk -- `attempt.json` and the patch file it names -- read with
the standard library only. `tests/conftest.py`'s audit-hook tripwire would
fail the default test tier if this script ever shelled out; it does not.

Locating a night's retained cells follows
`evidence/2026-09-16-census/classify.py`'s `cells()`: the night's
`launch.json` names its slots and must carry the given record's own
sha256, and the record's `task` must match the night's. That function is
reproduced here (not imported) so this stays one dependency-free file --
the two cannot drift on any load-bearing rule because both are reading the
same `launch.json`/record contract, not each other.

Each cell's own harvested patch is not rebuilt from a worktree (there is
none to read for a retained night): `src/satyrn_evals/attempt.py` writes
`patch_path` into `attempt.json` for an ordinary attempt, and
`src/satyrn_evals/workspace.py`'s `TRIPPED_PATCH_NAME` ("tripped.diff") is
what a `BUDGET_EXCEEDED` teardown harvest names as
`tripped_patch_path` -- both plain unified-diff text files beside
`attempt.json`, exactly what `postreg.md` describes as "a torn-down
worktree's cumulative patch, or `tripped.diff` for a `BUDGET_EXCEEDED`
cell." A cell whose `attempt.json` names neither is a cell with no source
touched: `postreg.md` records that as `n/a` in all four columns, not a
dropped row.

**Layout detail this script could not settle without a night that has
run:** whether a slot `cells()` accepts as finished can ever be missing
its own `attempt.json`, or carry one that fails to parse. Nothing in
`classify.py` rules this out -- its own `cell_span()` has a distinct,
handled `NO_ATTEMPT_JSON` case for a different read -- so rather than
silently treating that as "no patch" (which would fold a tooling failure
into the ordinary `n/a` case `postreg.md` already expects), this script
refuses loudly instead: `attempt_patch()` raises `Refused` naming the
exact path, and `main()` reports the refusal and stops rather than
guessing. If night 3 turns out to have a legitimate reason for a missing
`attempt.json` on a finished slot, that reason belongs in `postreg.md`
next to the `n/a` rule, not silently absorbed here.

    uv run --project . python evidence/2026-09-18-census-3/postreg_read.py \\
        --night "$HOME/satyrn-runs/2026-09-18-census3-selfhost-preflight-quiet" \\
        --record records/2026-09-18-census3-selfhost-preflight-quiet.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

#: The one file every column reads a diff of.
SOURCE_PATH = "scripts/preflight_quiet.py"

#: `postreg.md`'s `inputs_keys` column: the exact key set `as_dict()["inputs"]`
#: must carry, and no more.
INPUTS_KEYS = frozenset({"load", "busy", "decode", "floor_tok_s", "model", "last"})

#: `postreg.md`'s four pre-registered columns, in the order it lists them.
COLUMNS: tuple[str, ...] = ("maxsplit", "one_decimal", "inputs_keys", "cli_last")

_STAMP = re.compile(r"-\d{8}-\d{6}-\d{6}\Z")


class Verdict(StrEnum):
    """A column's three-way read for one cell -- never a bare boolean.

    `postreg.md` commits to recording a cell the reader cannot decide from,
    rather than silently counting it as a miss; `UNDETERMINED` is that
    recording, not a fourth kind of failure.
    """

    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    UNDETERMINED = "undetermined"


class Refused(ValueError):
    """A refusal: the night, the record, or a cell's own artefacts don't
    hold together well enough to read."""


@dataclass(frozen=True, slots=True)
class Cell:
    arm: str
    attempt: str
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
    """The finished cells of `night`, checked against `record` -- the same
    `launch.json`/`record_sha256`/task-match rule as
    `evidence/2026-09-16-census/classify.py:cells()`."""
    launch_path = night / "launch.json"
    if not launch_path.is_file():
        raise Refused(f"{night} has no launch.json")
    launch = json.loads(launch_path.read_text())
    if not record.is_file():
        raise Refused(f"no such record: {record}")
    record_sha = hashlib.sha256(record.read_bytes()).hexdigest()
    if launch.get("record_sha256") != record_sha:
        raise Refused(
            f"record {record} sha256 {record_sha} is not the night's {launch.get('record_sha256')}"
        )
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
                arm=str(slot.get("arm")),
                attempt=attempt_dir.rsplit("-", 1)[-1],
                attempt_dir=attempt_dir,
                folder=folder,
            )
        )
    if not found:
        raise Refused(f"{night} has no finished slots")
    return found


def cell_patch(cell: Cell) -> str | None:
    """The cell's harvested patch text, or None for a cell with no patch at
    all (`postreg.md`'s `n/a` case -- no source touched).

    Raises `Refused` when `attempt.json` itself cannot be read, or when it
    names a patch file that is not there: see the module docstring's
    "layout detail" note.
    """
    attempt_path = cell.folder / "attempt.json"
    try:
        record = json.loads(attempt_path.read_text())
    except OSError as exc:
        raise Refused(f"{attempt_path}: cannot read attempt record ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise Refused(f"{attempt_path}: not valid JSON ({exc})") from exc
    if not isinstance(record, dict):
        raise Refused(f"{attempt_path}: attempt record is not a JSON object")
    for key in ("patch_path", "tripped_patch_path"):
        name = record.get(key)
        if isinstance(name, str) and name:
            patch_file = cell.folder / name
            if not patch_file.is_file():
                raise Refused(f"{cell.attempt_dir}: {key} names {patch_file}, which does not exist")
            return patch_file.read_text(errors="replace")
    return None


def _hunk_for(patch_text: str, path: str) -> str | None:
    """The `diff --git a/<path> b/<path>` block for `path`, or None if the
    patch never touches it."""
    lines = patch_text.splitlines()
    marker = f"a/{path} b/{path}"
    start = None
    for index, line in enumerate(lines):
        if line.startswith("diff --git") and marker in line:
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("diff --git"):
            end = index
            break
    return "\n".join(lines[start:end])


def _added_lines(hunk: str) -> list[str]:
    """The hunk's added source lines (`+...`), the `+` dropped, `+++` excluded."""
    added = []
    for line in hunk.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
    return added


def _function_body(added: list[str], name: str) -> list[str] | None:
    """The added lines belonging to `def name(...)`'s body, by indentation,
    or None if `added` never defines it."""
    body: list[str] = []
    def_indent: int | None = None
    pattern = re.compile(rf"^(\s*)def\s+{re.escape(name)}\s*\(")
    for line in added:
        if def_indent is None:
            match = pattern.match(line)
            if match:
                def_indent = len(match.group(1))
            continue
        if not line.strip():
            body.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= def_indent:
            break
        body.append(line)
    return body if def_indent is not None else None


def maxsplit(patch_text: str) -> Verdict:
    """Does `busy_processes` split each `ps` line with `split(maxsplit=2)`
    (or `split(None, 2)`), rather than a bare `split()`?"""
    hunk = _hunk_for(patch_text, SOURCE_PATH)
    if hunk is None:
        return Verdict.UNDETERMINED
    body = _function_body(_added_lines(hunk), "busy_processes")
    if body is None:
        return Verdict.UNDETERMINED
    text = "\n".join(body)
    bounded = re.search(r"\.split\(\s*maxsplit\s*=\s*2\s*\)", text) or re.search(
        r"\.split\(\s*None\s*,\s*2\s*\)", text
    )
    bare = re.search(r"\.split\(\s*\)", text)
    if bounded and not bare:
        return Verdict.SATISFIED
    if bare and not bounded:
        return Verdict.NOT_SATISFIED
    return Verdict.UNDETERMINED


#: The two message shapes `postreg.md`'s `one_decimal` column reads --
#: loose enough to match either message's literal wording, tight enough not
#: to match an unrelated f-string.
_LOAD_MESSAGE = re.compile(r"f[\"'].*load.*>.*cores\)", re.IGNORECASE)
_DECODE_MESSAGE = re.compile(r"f[\"'].*decode.*tok/s.*completions", re.IGNORECASE)
_ONE_DECIMAL = re.compile(r":\.1f\b")


def one_decimal(patch_text: str) -> Verdict:
    """Are the `load` and `decode` messages formatted to one decimal place?"""
    hunk = _hunk_for(patch_text, SOURCE_PATH)
    if hunk is None:
        return Verdict.UNDETERMINED
    added = _added_lines(hunk)
    load_line = next((line for line in added if _LOAD_MESSAGE.search(line)), None)
    decode_line = next((line for line in added if _DECODE_MESSAGE.search(line)), None)
    if load_line is None or decode_line is None:
        return Verdict.UNDETERMINED
    if _ONE_DECIMAL.search(load_line) and _ONE_DECIMAL.search(decode_line):
        return Verdict.SATISFIED
    return Verdict.NOT_SATISFIED


def inputs_keys(patch_text: str) -> Verdict:
    """Does `as_dict()["inputs"]` carry exactly `INPUTS_KEYS`, and no more?"""
    hunk = _hunk_for(patch_text, SOURCE_PATH)
    if hunk is None:
        return Verdict.UNDETERMINED
    added = _added_lines(hunk)
    start = next((index for index, line in enumerate(added) if re.search(r"[\"']inputs[\"']\s*:", line)), None)
    if start is None:
        return Verdict.UNDETERMINED
    open_at = added[start].index(":", added[start].find("inputs")) + 1
    tail = added[start][open_at:]
    depth = tail.count("{") - tail.count("}")
    span = [tail]
    index = start
    while depth > 0:
        index += 1
        if index >= len(added):
            return Verdict.UNDETERMINED  # the dict literal runs past the added lines
        line = added[index]
        span.append(line)
        depth += line.count("{") - line.count("}")
    block = "\n".join(span)
    keys = frozenset(re.findall(r"[\"'](\w+)[\"']\s*:", block))
    return Verdict.SATISFIED if keys == INPUTS_KEYS else Verdict.NOT_SATISFIED


def cli_last(patch_text: str) -> Verdict:
    """Is the `last` passed to `certificate(...)` the parsed `--last`, rather
    than a hardcoded `DEFAULT_LAST`?"""
    hunk = _hunk_for(patch_text, SOURCE_PATH)
    if hunk is None:
        return Verdict.UNDETERMINED
    text = "\n".join(_added_lines(hunk))
    match = re.search(r"certificate\(([^)]*)\)", text)
    if match is None:
        return Verdict.UNDETERMINED
    call_args = match.group(1)
    last_match = re.search(r"\blast\s*=\s*([A-Za-z_][A-Za-z0-9_.]*)", call_args)
    if last_match is None:
        return Verdict.UNDETERMINED
    value = last_match.group(1)
    if value == "DEFAULT_LAST":
        return Verdict.NOT_SATISFIED
    return Verdict.SATISFIED


#: Column name -> its pure predicate, in `postreg.md`'s own order.
PREDICATES: dict[str, "callable[[str], Verdict]"] = {
    "maxsplit": maxsplit,
    "one_decimal": one_decimal,
    "inputs_keys": inputs_keys,
    "cli_last": cli_last,
}


def read_cell(patch_text: str | None) -> dict[str, Verdict]:
    """A cell's row: `n/a`-equivalent (`UNDETERMINED` on every column) for a
    cell with no patch, else each predicate over the patch text."""
    if patch_text is None:
        return {name: Verdict.UNDETERMINED for name in COLUMNS}
    return {name: predicate(patch_text) for name, predicate in PREDICATES.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="postreg_read.py", description=__doc__.splitlines()[0])
    parser.add_argument("--night", required=True, type=Path, help="the retained night directory")
    parser.add_argument("--record", required=True, type=Path, help="the frozen record this night ran")
    args = parser.parse_args(argv)

    try:
        found = cells(args.night.resolve(), args.record.resolve())
    except Refused as exc:
        print(f"postreg_read: refused: {exc}", file=sys.stderr)
        return 2

    counts = {name: 0 for name in COLUMNS}
    denominator = len(found)
    for cell in found:
        try:
            patch_text = cell_patch(cell)
        except Refused as exc:
            print(f"postreg_read: refused: {exc}", file=sys.stderr)
            return 2
        row = read_cell(patch_text)
        for name in COLUMNS:
            if row[name] is Verdict.SATISFIED:
                counts[name] += 1
        printed = ", ".join(f"{name}={row[name].value}" for name in COLUMNS)
        print(f"{cell.attempt_dir}: {printed}")

    print("---")
    for name in COLUMNS:
        print(f"{name}: {counts[name]}/{denominator}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
