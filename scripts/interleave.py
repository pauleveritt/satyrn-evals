#!/usr/bin/env python3
"""Build a seeded, committed interleave schedule — one directory per cell.

Instrument, not production code: it lives outside ``src/satyrn_evals`` and
outside the coverage gate's ``--cov`` path, and is covered by
``tests/test_interleave.py`` all the same.

**One directory per expected cell, deliberately.** ``satyrn-evals run``
cannot interleave arms, and ``summarize`` needs a ``summary.json`` anchor
in the directory it reads — so twelve ``run --n 1`` calls into one output
directory would overwrite that anchor eleven times and leave one cell's
counts standing for the batch. Each cell therefore gets its own directory,
named for its position in the realized order, and ``scripts/tally.py``
reads exactly that set.

**The order is written before the first cell runs.** A schedule realized
after the fact is not a schedule; it is a description of what happened.
The seed is recorded beside the order so the order can be rebuilt.

Usage::

    scripts/interleave.py --seed N --n 12 --task TASK --rung R1 \\
        --contract-digest HEX --output RUNS_ROOT arms/baseline.json arms/engine.json
"""

import argparse
import json
import random
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from satyrn_evals.arms import Arm, build_argv, load_arm  # noqa: E402

SCHEDULE_VERSION = 1
SCHEDULE_NAME = "schedule.json"


class ScheduleError(Exception):
    """The requested schedule is not one that could support a comparison."""


def build_order(*, seed: int | None, per_arm: Mapping[str, int]) -> list[str]:
    """The realized arm order: balanced, shuffled, reproducible from ``seed``.

    ``per_arm`` maps an arm name to its cell count. The counts must be
    equal: an unbalanced schedule makes the arms' denominators differ
    before a single cell has run, which is a choice that belongs in a
    preregistration, not in a shuffler.
    """
    if seed is None:
        raise ScheduleError(
            "a seed is required; an unrecorded order is not reproducible"
        )
    if not per_arm:
        raise ScheduleError("at least one arm is required")
    if len(set(per_arm.values())) != 1:
        raise ScheduleError(f"unbalanced request: {dict(sorted(per_arm.items()))}")
    if not all(count >= 1 for count in per_arm.values()):
        raise ScheduleError("each arm needs at least one cell")
    order = [arm for arm, count in sorted(per_arm.items()) for _ in range(count)]
    random.Random(seed).shuffle(order)
    return order


def build_schedule(
    *,
    seed: int,
    arm_paths: Sequence[Path],
    per_arm: Mapping[str, int],
    task: str,
    rung: str,
    contract_digest: str,
) -> dict[str, object]:
    """The whole schedule: the realized order plus each cell's exact argv."""
    arms: dict[str, Arm] = {}
    for path in arm_paths:
        arm = load_arm(Path(path))
        arms[arm.arm] = arm
    if missing := sorted(set(per_arm) - set(arms)):
        raise ScheduleError(f"no arm file for {', '.join(missing)}")
    if len({arm.model for arm in arms.values()}) != 1:
        raise ScheduleError(
            "the arms do not agree on the model: "
            + ", ".join(f"{name}={arm.model}" for name, arm in sorted(arms.items()))
        )
    order = build_order(seed=seed, per_arm=per_arm)
    return {
        "version": SCHEDULE_VERSION,
        "seed": seed,
        "task": task,
        "rung": rung,
        "contract_digest": contract_digest,
        "model": next(iter(arms.values())).model,
        "cells": [
            {
                "index": index,
                "arm": name,
                "dir": f"cell-{index:03d}-{name}",
                "command": build_argv(arms[name]),
            }
            for index, name in enumerate(order)
        ],
    }


def materialize(schedule: Mapping[str, object], runs_root: Path) -> list[Path]:
    """Create one empty directory per cell and write the schedule beside them.

    An existing cell directory is refused rather than reused: ``run``
    overwrites ``summary.json`` in place, so a second batch into the same
    root would destroy the first batch's record silently.
    """
    root = Path(runs_root)
    cells = list(schedule["cells"])  # type: ignore[arg-type]
    made: list[Path] = []
    root.mkdir(parents=True, exist_ok=True)
    for cell in cells:
        directory = root / cell["dir"]
        if directory.exists():
            raise ScheduleError(f"{directory} already exists; refusing to reuse it")
        directory.mkdir()
        made.append(directory)
    (root / SCHEDULE_NAME).write_text(
        json.dumps(schedule, indent=2) + "\n", encoding="utf-8"
    )
    return made


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("arms", nargs="+", help="paths to the arm definition files")
    parser.add_argument("--seed", type=int, required=True, help="recorded shuffle seed")
    parser.add_argument("--n", type=int, required=True, help="cells per arm")
    parser.add_argument("--task", required=True)
    parser.add_argument("--rung", required=True)
    parser.add_argument("--contract-digest", required=True)
    parser.add_argument("--output", required=True, help="the runs root to create")
    args = parser.parse_args(argv)
    names: list[str] = [load_arm(Path(path)).arm for path in args.arms]
    try:
        schedule = build_schedule(
            seed=args.seed,
            arm_paths=[Path(path) for path in args.arms],
            per_arm={name: args.n for name in names},
            task=args.task,
            rung=args.rung,
            contract_digest=args.contract_digest,
        )
        materialize(schedule, Path(args.output))
    except ScheduleError as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    print(
        f"{len(schedule['cells'])} cells under {args.output} "  # type: ignore[arg-type]
        f"(seed {args.seed}); order recorded in {SCHEDULE_NAME}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
