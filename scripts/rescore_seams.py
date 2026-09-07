#!/usr/bin/env python3
"""Re-score seam completion from retained cells. No model, no network.

Written for the V15 premise correction
(`docs/superpowers/research/2026-09-07-v15-premise-correction.md`). It reads
only artifacts that are already on disk — `patch.diff` and `receipt.json` —
so it exercises the property `BRIEF.md` rule 3 exists to buy: a new measure
is computed over old cells without re-running anything.

**Two measures, kept apart.** They answer different questions and are never
summed or averaged together:

- ``seams_touched`` — how many of the known-good patch's files the attempt's
  own patch also modified. A patch-level fact. Touching is not fixing.
- ``seams_closed`` — how many seams' acceptance checks all passed, read from
  the receipt's retained per-test outcomes. A verdict-level fact.

**The seam map is not post-hoc.** Each seam's checks are the ones named in
that task's own ``contracts.R1`` text, authored in V8/V11a long before the
batches read here, paired with the file the known-good patch changes for
them. The map is additionally *validated* against the data: a seam whose
checks pass in a cell that never touched its file would falsify the
pairing, and every such violation is reported rather than absorbed.

**Unmeasured is never zero.** Four silent-zero incidents are recorded in
`docs/superpowers/research/2026-08-16-harvest-index.md`. A cell with no
receipt, no evidence, or an ``unavailable`` verdict is ``unmeasured`` for
``seams_closed`` and is reported as its own count; it does not become a 0
and it does not silently leave the denominator.

W1 note: this is a one-off instrument for one correction. It is a deletion
candidate, not a fixture of the repository.

Usage:
    uv run python scripts/rescore_seams.py ~/satyrn-smokes/2026-09-07-v14b-133236
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

#: A seam: the source file that must change, and the acceptance checks that
#: go green when it does. Derived from each task's `contracts.R1` text plus
#: the files in its `fixtures/known-good.patch`. See the module docstring.
SEAM_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "agentclinic-repair-misleading-locus": {
        "app.py": ("test_posted_complaint_appears_on_complaints_board",),
    },
    "agentclinic-repair-depth-2": {
        "app.py": ("test_post_complaint_redirects_to_complaints_board",),
        "templates/base.html": (
            "test_home_html_element_declares_english_language",
            "test_complaints_board_preserves_the_shared_layout",
        ),
    },
    "agentclinic-repair-depth-3": {
        "app.py": ("test_post_complaint_redirects_to_complaints_board",),
        "models.py": ("test_complaint_model_contract_is_preserved",),
        "templates/base.html": (
            "test_home_html_element_declares_english_language",
            "test_complaints_board_preserves_the_shared_layout",
        ),
    },
}

type Arm = Literal["baseline", "engine", "envelope"]
type SeamState = Literal["closed", "open", "unmeasured"]

_PATCH_TARGET_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)
_CELL_RE = re.compile(r"^cell-(\d+)-([a-z]+)$")


@dataclass(frozen=True, slots=True)
class CellScore:
    """One cell's two measures, plus what could not be measured."""

    task: str
    arm: str
    cell: str
    verdict: str | None
    touched: frozenset[str] | None
    closed: dict[str, SeamState]

    @property
    def n_seams(self) -> int:
        return len(self.closed)

    @property
    def n_touched(self) -> int | None:
        return None if self.touched is None else len(self.touched)

    @property
    def n_closed(self) -> int | None:
        states = self.closed.values()
        if any(state == "unmeasured" for state in states):
            return None
        return sum(1 for state in states if state == "closed")


def _seam_files_touched(patch_path: Path, seams: dict[str, tuple[str, ...]]) -> frozenset[str]:
    text = patch_path.read_text(errors="replace")
    targets = set(_PATCH_TARGET_RE.findall(text))
    return frozenset(seam for seam in seams if seam in targets)


def _closed_states(
    receipt: dict | None, seams: dict[str, tuple[str, ...]]
) -> dict[str, SeamState]:
    """Per-seam state. A missing or unusable receipt makes every seam
    ``unmeasured`` — never ``open``, which would read as a measured failure."""
    match receipt:
        case {"evidence": {"outcomes": dict() as outcomes}} if receipt.get(
            "verdict"
        ) != "unavailable":
            pass
        case _:
            return {seam: "unmeasured" for seam in seams}

    by_name = {node.split("::")[-1]: result for node, result in outcomes.items()}
    states: dict[str, SeamState] = {}
    for seam, checks in seams.items():
        results = [by_name.get(check) for check in checks]
        if any(result is None for result in results):
            states[seam] = "unmeasured"
        else:
            states[seam] = "closed" if all(r == "passed" for r in results) else "open"
    return states


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def score_cell(cell_dir: Path, task: str, arm: str) -> CellScore:
    seams = SEAM_MAP[task]
    patches = sorted(cell_dir.glob("*/patch.diff"))
    receipts = sorted(cell_dir.glob("*/receipt.json"))

    touched = _seam_files_touched(patches[0], seams) if patches else None
    receipt = _load_json(receipts[0]) if receipts else None
    return CellScore(
        task=task,
        arm=arm,
        cell=cell_dir.name,
        verdict=(receipt or {}).get("verdict"),
        touched=touched,
        closed=_closed_states(receipt, seams),
    )


def collect(run_root: Path) -> list[CellScore]:
    scores: list[CellScore] = []
    for task_dir in sorted(run_root.iterdir()):
        if not task_dir.is_dir() or task_dir.name not in SEAM_MAP:
            continue
        for cell_dir in sorted(task_dir.iterdir()):
            if not cell_dir.is_dir() or not (m := _CELL_RE.match(cell_dir.name)):
                continue
            scores.append(score_cell(cell_dir, task_dir.name, m.group(2)))
    return scores


def map_violations(scores: list[CellScore]) -> list[str]:
    """A seam closed without its file being touched falsifies the seam map
    (or means the check was green at base). Either way it is reported."""
    violations = []
    for score in scores:
        if score.touched is None:
            continue
        for seam, state in score.closed.items():
            if state == "closed" and seam not in score.touched:
                violations.append(
                    f"{score.task} {score.cell}: seam {seam!r} closed but not touched"
                )
    return violations


def _dist(values: list[int | None]) -> str:
    counter = Counter("unmeasured" if v is None else v for v in values)
    return ", ".join(f"{k}:{counter[k]}" for k in sorted(counter, key=str))


def report(scores: list[CellScore]) -> str:
    lines: list[str] = []
    lines.append(
        f"{'task':<38} {'seams':>5} {'arm':<9} {'cells':>5} "
        f"{'touched dist':<22} {'closed dist':<22} {'mean closed/n':>13} {'verdict pass':>12}"
    )
    for task in sorted({s.task for s in scores}, key=lambda t: len(SEAM_MAP[t])):
        n_seams = len(SEAM_MAP[task])
        for arm in sorted({s.arm for s in scores if s.task == task}):
            cells = [s for s in scores if s.task == task and s.arm == arm]
            closed = [s.n_closed for s in cells]
            measured = [c for c in closed if c is not None]
            mean = f"{sum(measured) / len(measured) / n_seams:.3f}" if measured else "n/a"
            passes = sum(1 for s in cells if s.verdict == "pass")
            lines.append(
                f"{task:<38} {n_seams:>5} {arm:<9} {len(cells):>5} "
                f"{_dist([s.n_touched for s in cells]):<22} {_dist(closed):<22} "
                f"{mean:>13} {f'{passes}/{len(cells)}':>12}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path, nargs="+")
    args = parser.parse_args(argv)

    for run_root in args.run_root:
        if not (scores := collect(run_root)):
            print(f"no scorable cells under {run_root}", file=sys.stderr)
            return 1
        print(f"\n== {run_root.name}  ({len(scores)} cells)\n")
        print(report(scores))
        if violations := map_violations(scores):
            print(f"\nseam-map violations ({len(violations)}):")
            for violation in violations:
                print(f"  {violation}")
        else:
            print("\nseam-map validation: no seam closed without its file being touched")
        if unmeasured := [s for s in scores if s.n_closed is None]:
            print(f"\nunmeasured for seams_closed ({len(unmeasured)}):")
            for score in unmeasured:
                print(f"  {score.task} {score.cell} verdict={score.verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
