"""The pre-registered reader for the run-record-gate delivery comparison (no model, network or subprocess).

Applies §4 and §5 of docs/superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md
exactly, with §9 D2 (Baseline-favouring ``unavailable``) and D3 (reaches excluded,
admitted-only count also required). Built and frozen on synthetic cells before
any cell of the record exists (D5); it never reads ~/satyrn-runs on its own.

Usage, from the repo root:

    uv run python evidence/2026-10-05-rrg-delivery/decide.py NIGHT RECORD.json

Prints the decision as JSON, a blank line, then a short markdown table.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from math import comb
from pathlib import Path

from satyrn_evals.launch import infrastructure_reason, read_slots

DELIVERED, NOT_DELIVERED, UNAVAILABLE, INFRASTRUCTURE = "delivered", "not delivered", "unavailable", "infrastructure"
ARMS = ("baseline", "engine")
SETTINGS = ("baseline-favouring", "excluded")
HOLDS = "holds"
ONE_COUNT = "not holding: rejects on one count only"
NEGATIVE = "stated negative"
USAGE = "usage: decide.py NIGHT RECORD.json"


@dataclass(frozen=True)
class Cell:
    slot: int
    arm: str
    attempt_dir: str
    cls: str
    refusals: int
    reaches: int


class Refused(SystemExit):
    """A night or record this reader will not decide on; the message names why."""


def classify(result: dict) -> str:
    """§4: one class per finished slot, from the slot's code and harness verdict."""
    if infrastructure_reason(result) is not None:
        return INFRASTRUCTURE
    if result.get("verdict") == "pass":
        return DELIVERED
    if result.get("verdict") == "unavailable":
        return UNAVAILABLE
    return NOT_DELIVERED


def _confinement(night: Path, result: dict, cls: str) -> tuple[int, int]:
    where = f"slot {result['slot']} ({result['arm']}, {result['attempt_dir']})"
    path = night / result["arm"] / result["attempt_dir"] / "attempt.json"
    if not path.is_file():
        if cls == INFRASTRUCTURE:  # never counted (§4); it may have measured nothing to record
            return 0, 0
        raise Refused(f"{where}: no attempt.json at {path}")
    confinement = json.loads(path.read_text(encoding="utf-8")).get("confinement")
    numbers = [confinement.get(key) if isinstance(confinement, dict) else None for key in ("refusals", "reaches")]
    if not all(type(value) is int for value in numbers):
        raise Refused(f"{where}: {path} has no integer confinement.refusals and confinement.reaches")
    return numbers[0], numbers[1]


def load(night: Path) -> list[Cell]:
    """One Cell per finished slot, ordered by slot."""
    found = []
    for index, result in sorted(read_slots(night).items()):
        cls = classify(result)
        refusals, reaches = _confinement(night, result, cls)
        found.append(Cell(index, result["arm"], result["attempt_dir"], cls, refusals, reaches))
    return found


def counts(cells: list[Cell], *, admitted_only: bool, unavailable: str) -> dict:
    """Delivered over n per arm, and every excluded cell by name (§4, D2, D3)."""
    if unavailable not in SETTINGS:
        raise ValueError(f"unavailable must be one of {SETTINGS}, not {unavailable!r}")
    tally = {arm: {"delivered": 0, "n": 0} for arm in ARMS}
    excluded = []
    for cell in cells:
        if cell.cls == INFRASTRUCTURE:
            why = "infrastructure"
        elif cell.reaches > 0:
            why = f"confinement reaches: {cell.reaches}"
        elif admitted_only and cell.refusals > 0:
            why = f"confinement refusals: {cell.refusals} (admitted cells only)"
        elif cell.cls == UNAVAILABLE and unavailable == "excluded":
            why = "unavailable verdict (excluded from both arms)"
        else:
            delivered = cell.cls == DELIVERED or (
                cell.cls == UNAVAILABLE and cell.arm == "baseline")  # D2: Baseline-favouring
            tally[cell.arm]["n"] += 1
            tally[cell.arm]["delivered"] += delivered
            continue
        excluded.append({"attempt_dir": cell.attempt_dir, "arm": cell.arm, "why": why})
    return {**tally, "excluded": excluded}


def fisher_one_sided(x_engine: int, n_engine: int, x_baseline: int, n_baseline: int) -> float:
    """P(engine delivered >= x_engine), both margins fixed (H1: engine rate > baseline rate)."""
    total, delivered = n_engine + n_baseline, x_engine + x_baseline
    ways = comb(total, n_engine)
    top = min(delivered, n_engine)
    return sum(comb(delivered, k) * comb(total - delivered, n_engine - k)
               for k in range(x_engine, top + 1)) / ways


def _reading(cells: list[Cell], alpha: float, *, admitted_only: bool, unavailable: str) -> dict:
    tally = counts(cells, admitted_only=admitted_only, unavailable=unavailable)
    engine, baseline = tally["engine"], tally["baseline"]
    p = fisher_one_sided(engine["delivered"], engine["n"], baseline["delivered"], baseline["n"])
    return {"counts": tally, "p": p, "rejects": p <= alpha}


def decide(cells: list[Cell], alpha: float = 0.05) -> dict:
    """§5: reject on the primary and the admitted-only count to hold; "beside" never decides."""
    readings = {
        "primary": _reading(cells, alpha, admitted_only=False, unavailable="baseline-favouring"),
        "admitted": _reading(cells, alpha, admitted_only=True, unavailable="baseline-favouring"),
        "beside": _reading(cells, alpha, admitted_only=False, unavailable="excluded"),
    }
    rejecting = (readings["primary"]["rejects"], readings["admitted"]["rejects"])
    verdict = HOLDS if all(rejecting) else ONE_COUNT if any(rejecting) else NEGATIVE
    return {"alpha": alpha, **readings, "verdict": verdict}


def _table(result: dict) -> str:
    rows = ["| reading | baseline | engine | p | excluded |", "|---|---|---|---|---|"]
    for name in ("primary", "admitted", "beside"):
        reading = result[name]
        tally = reading["counts"]
        rows.append("| " + " | ".join([
            name,
            *(f"{tally[arm]['delivered']}/{tally[arm]['n']}" for arm in ARMS),
            f"{reading['p']:.6f}",
            str(len(tally["excluded"])),
        ]) + " |")
    return "\n".join([*rows, "", f"alpha {result['alpha']}; verdict: {result['verdict']}"])


def _require_complete(night: Path, record: dict) -> None:
    arms = str(record.get("arm", "")).split("+")
    if sorted(arms) != sorted(ARMS):
        raise Refused(f"record arms are {arms}; this reader decides baseline against engine only")
    finished = [result["arm"] for result in read_slots(night).values()]
    have = {arm: finished.count(arm) for arm in arms}
    if any(have[arm] != record["n"] for arm in arms):
        said = ", ".join(f"{arm} {have[arm]} of {record['n']}" for arm in arms)
        raise Refused(f"incomplete night: {said}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise Refused(USAGE)
    night, record = Path(argv[0]), json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    _require_complete(night, record)
    result = decide(load(night))
    print(json.dumps(result, indent=2) + "\n\n" + _table(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
