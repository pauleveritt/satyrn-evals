#!/usr/bin/env python3
"""Tally exactly the expected set of cells, or refuse.

This script is instrument, not production code: it lives outside
``src/satyrn_evals`` and outside the coverage gate's ``--cov`` path, and
it is covered by ``tests/test_tally.py`` all the same.

**Why it refuses.** The failure this file exists to prevent is the one the
harvest index records five times over: an absence of signal reported as a
finding. A tally that skipped a missing cell, ignored a stray directory,
or quietly accepted a cell run at the wrong rung would report a clean
fraction over a denominator nobody chose. So every discrepancy between the
committed schedule and what is on disk is a refusal, all of them are
reported together, and a refused batch produces **no counts at all**.

Contamination is different, and is deliberately not a refusal: a flagged
cell stays **in** the denominator and is reported beside it (V7).

**Counts only.** No durations, ever — two published figures in the prior
project were retracted for comparing wall-clock time between contiguous
arms (`BRIEF.md`).

Usage::

    scripts/tally.py SCHEDULE.json RUNS_ROOT [--output TALLY.json]

``SCHEDULE.json`` is what ``scripts/interleave.py`` wrote before the first
cell ran; ``RUNS_ROOT`` is the directory holding one subdirectory per
scheduled cell, plus the preserved attempt directories named by each
summary's ``cells``. Every counted attempt must have a JSONL
``transcript.txt`` containing a consistent ``message.model`` identity
matching its scheduled arm. The requested ``--model`` in ``command`` remains
configuration evidence only.
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SCHEDULE_VERSION = 2
SUMMARY_NAME = "summary.json"
ABORTED_NAME = "aborted.json"

type RefusalKind = Literal[
    "missing",
    "aborted",
    "unreadable",
    "duplicate",
    "unscheduled",
    "unexpected_task",
    "wrong_rung",
    "wrong_digest",
    "wrong_model",
    "missing_observed_model",
    "inconsistent_observed_model",
    "wrong_observed_model",
    "wrong_arm",
]


@dataclass(frozen=True, slots=True)
class Refusal:
    """One discrepancy between the committed schedule and what is on disk."""

    kind: RefusalKind
    cell: str
    detail: str

    def line(self) -> str:
        return f"{self.kind}: {self.cell}: {self.detail}"


class TallyRefused(Exception):
    """The batch is not the batch that was scheduled; no counts are produced."""

    def __init__(self, refusals: list[Refusal]) -> None:
        super().__init__("; ".join(refusal.line() for refusal in refusals))
        self.refusals = refusals


@dataclass(slots=True)
class ArmTally:
    """Counts for one arm. Every field is a count; none is a duration."""

    cells: int = 0
    attempted: int = 0
    refused: int = 0
    code_counts: Counter[str] = field(default_factory=Counter)
    verdict_counts: Counter[str] = field(default_factory=Counter)
    timeouts: int = 0
    contamination: Counter[str] = field(default_factory=Counter)
    pathology: Counter[str] = field(default_factory=Counter)

    def to_wire(self) -> dict[str, object]:
        return {
            "cells": self.cells,
            "attempted": self.attempted,
            "refused": self.refused,
            "code_counts": dict(self.code_counts),
            "verdict_counts": dict(self.verdict_counts),
            "timeouts": self.timeouts,
            "contamination": dict(self.contamination),
            "pathology": {
                "measured": self.pathology["measured"],
                "unmeasured": self.pathology["unmeasured"],
            },
        }


@dataclass(frozen=True, slots=True)
class Tally:
    """The whole batch: the denominator, and per-arm counts under it."""

    task: str
    rung: str
    contract_digest: str
    model: str
    server_model: str
    seed: int
    cells: int
    per_arm: dict[str, dict[str, object]]

    def to_wire(self) -> dict[str, object]:
        return {
            "task": self.task,
            "rung": self.rung,
            "contract_digest": self.contract_digest,
            "model": self.model,
            "server_model": self.server_model,
            "seed": self.seed,
            "cells": self.cells,
            "per_arm": self.per_arm,
        }


def _model_of(command: list[str]) -> str | None:
    """The value of the space-form ``--model`` flag, or None if absent."""
    for index, token in enumerate(command):
        if token == "--model" and index + 1 < len(command):
            return command[index + 1]
    return None


def _without_model(command: list[str]) -> list[str]:
    """The command with its ``--model VALUE`` pair removed."""
    if (index := command.index("--model") if "--model" in command else -1) < 0:
        return list(command)
    return [*command[:index], *command[index + 2 :]]


def _observed_models(transcript: Path) -> list[str]:
    """Return model ids from the preserved Pi ``message.model`` events.

    ``responseModel`` is intentionally not considered: Pi uses that field
    for the ``keepalive`` response, which is transport metadata rather than
    the model that handled the attempt.
    """
    models: list[str] = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        if not isinstance(message, dict):
            continue
        model = message.get("model")
        if isinstance(model, str) and model:
            models.append(model)
    return models


def _check_cell(
    cell: dict, summary: dict, schedule: dict, cell_directory: Path
) -> list[Refusal]:
    """Every way this cell can fail to be the cell that was scheduled."""
    name = cell["dir"]
    refusals: list[Refusal] = []
    if (task := summary.get("task")) != schedule["task"]:
        refusals.append(Refusal("unexpected_task", name, f"recorded task {task!r}"))
    if (rung := summary.get("rung")) != schedule["rung"]:
        refusals.append(Refusal("wrong_rung", name, f"recorded rung {rung!r}"))
    if (digest := summary.get("contract_digest")) != schedule["contract_digest"]:
        refusals.append(
            Refusal("wrong_digest", name, f"recorded contract_digest {digest!r}")
        )
    command = list(summary.get("command", []))
    if (model := _model_of(command)) != schedule["model"]:
        refusals.append(Refusal("wrong_model", name, f"recorded model {model!r}"))
    expected = _without_model(list(cell["command"]))
    if _without_model(command)[: len(expected)] != expected:
        refusals.append(
            Refusal(
                "wrong_arm",
                name,
                f"recorded command does not start with the {cell['arm']!r} argv",
            )
    )
    for attempt_cell in summary.get("cells", []):
        transcript = cell_directory / attempt_cell / "transcript.txt"
        try:
            observed = _observed_models(transcript)
        except (OSError, UnicodeError) as error:
            refusals.append(
                Refusal(
                    "missing_observed_model",
                    name,
                    f"{attempt_cell!r} transcript unreadable: {error}",
                )
            )
            continue
        if not observed:
            refusals.append(
                Refusal(
                    "missing_observed_model",
                    name,
                    f"{attempt_cell!r} has no message.model",
                )
            )
        elif len(set(observed)) != 1:
            refusals.append(
                Refusal(
                    "inconsistent_observed_model",
                    name,
                    f"{attempt_cell!r} observed models {sorted(set(observed))!r}",
                )
            )
        elif observed[0] != schedule["server_model"]:
            refusals.append(
                Refusal(
                    "wrong_observed_model",
                    name,
                    f"{attempt_cell!r} observed model {observed[0]!r}",
                )
            )
    return refusals


def _add_cell(arm: ArmTally, summary: dict) -> None:
    """Fold one cell's counts in. Flagged cells stay in the denominator."""
    arm.cells += int(summary.get("n", 0))
    arm.attempted += int(summary.get("attempted", 0))
    arm.refused += int(summary.get("refused", 0))
    arm.code_counts.update(
        {key: int(value) for key, value in summary.get("code_counts", {}).items()}
    )
    arm.verdict_counts.update(
        {key: int(value) for key, value in summary.get("verdict_counts", {}).items()}
    )
    arm.timeouts += int(summary.get("timeouts", 0))
    arm.contamination.update(
        {key: int(value) for key, value in (summary.get("contamination") or {}).items()}
    )
    for block in summary.get("pathology", {}).values():
        arm.pathology["measured" if block.get("measured") else "unmeasured"] += 1


def tally(schedule_path: Path, runs_root: Path) -> Tally:
    """Read exactly the scheduled cells, or raise ``TallyRefused``."""
    schedule = json.loads(Path(schedule_path).read_text(encoding="utf-8"))
    if schedule.get("version") != SCHEDULE_VERSION:
        raise TallyRefused(
            [
                Refusal(
                    "unreadable",
                    str(schedule_path),
                    f"schedule version {schedule.get('version')!r} is not "
                    f"{SCHEDULE_VERSION}",
                )
            ]
        )
    runs_root = Path(runs_root)
    refusals: list[Refusal] = []
    arms: dict[str, ArmTally] = {}
    seen_attempt_cells: dict[str, str] = {}
    scheduled_dirs = {cell["dir"] for cell in schedule["cells"]}

    for cell in schedule["cells"]:
        name = cell["dir"]
        directory = runs_root / name
        if (directory / ABORTED_NAME).exists():
            refusals.append(Refusal("aborted", name, f"the cell wrote {ABORTED_NAME}"))
            continue
        if not (path := directory / SUMMARY_NAME).exists():
            refusals.append(Refusal("missing", name, f"no {SUMMARY_NAME}"))
            continue
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            refusals.append(Refusal("unreadable", name, f"{SUMMARY_NAME}: {error}"))
            continue
        if faults := _check_cell(cell, summary, schedule, directory):
            refusals.extend(faults)
            continue
        duplicated = [
            attempt_cell
            for attempt_cell in summary.get("cells", [])
            if attempt_cell in seen_attempt_cells
        ]
        if duplicated:
            refusals.append(
                Refusal(
                    "duplicate",
                    name,
                    f"attempt cell {duplicated[0]!r} already counted under "
                    f"{seen_attempt_cells[duplicated[0]]!r}",
                )
            )
            continue
        for attempt_cell in summary.get("cells", []):
            seen_attempt_cells[attempt_cell] = name
        _add_cell(arms.setdefault(cell["arm"], ArmTally()), summary)

    for stray in sorted(runs_root.iterdir()):
        if (
            stray.is_dir()
            and stray.name not in scheduled_dirs
            and (stray / SUMMARY_NAME).exists()
        ):
            refusals.append(
                Refusal("unscheduled", stray.name, "not named by the schedule")
            )

    if refusals:
        raise TallyRefused(refusals)
    return Tally(
        task=schedule["task"],
        rung=schedule["rung"],
        contract_digest=schedule["contract_digest"],
        model=schedule["model"],
        server_model=schedule["server_model"],
        seed=schedule["seed"],
        cells=sum(arm.cells for arm in arms.values()),
        per_arm={name: arm.to_wire() for name, arm in sorted(arms.items())},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("schedule", help="the schedule interleave.py wrote")
    parser.add_argument("runs_root", help="directory holding one dir per cell")
    parser.add_argument("--output", help="write the tally JSON here as well")
    args = parser.parse_args(argv)
    try:
        result = tally(Path(args.schedule), Path(args.runs_root))
    except TallyRefused as refused:
        for refusal in refused.refusals:
            print(refusal.line(), file=sys.stderr)
        print(
            f"refused: {len(refused.refusals)} discrepancies; no counts written",
            file=sys.stderr,
        )
        return 1
    payload = json.dumps(result.to_wire(), indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
