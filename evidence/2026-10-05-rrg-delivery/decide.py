"""The pre-registered reader for the run-record-gate delivery comparison (no model, network or subprocess).

Applies §4 and §5 of docs/superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md
exactly, with §9 D2 (Baseline-favouring ``unavailable``) and D3 (reaches excluded,
admitted-only count also required). Built and frozen on synthetic cells before
any cell of the record exists (D5); it never reads ~/satyrn-runs on its own.

Usage, from the repo root (one or more night/record pairs, decided once over their combined cells):

    uv run python evidence/2026-10-05-rrg-delivery/decide.py NIGHT RECORD.json [NIGHT RECORD.json ...]

Prints the decision as JSON, a blank line, then a short markdown table.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from math import comb
from pathlib import Path

from satyrn_evals import launch
from satyrn_evals.launch import infrastructure_reason, read_slots

DELIVERED, NOT_DELIVERED, UNAVAILABLE, INFRASTRUCTURE = "delivered", "not delivered", "unavailable", "infrastructure"
ARMS = ("baseline", "engine")
SETTINGS = ("baseline-favouring", "excluded")
#: launch.py is not frozen, so the infrastructure codes it classifies by are pinned here, as of 2026-10-05.
EXPECTED_INFRASTRUCTURE_CODES = frozenset({
    "WORKSPACE_FAILED", "CLEANUP_FAILED", "GRADE_FAILED", "TRANSCRIPT_MISSING", "TRANSCRIPT_EMPTY",
    "MODEL_ERROR", "PATCH_INVALID",
})
HOLDS = "holds"
ONE_COUNT = "not holding: rejects on one count only"
NEGATIVE = "stated negative"
#: Record fields that may differ between the batch records of one decision (cap amendment, three n = 12 records).
RECORD_FIELDS_MAY_DIFFER = frozenset({"authority", "decision_rule", "previous_result"})
USAGE = "usage: decide.py NIGHT RECORD.json [NIGHT RECORD.json ...]"


@dataclass(frozen=True)
class Cell:
    slot: int
    arm: str
    attempt_dir: str
    cls: str
    refusals: int
    reaches: int
    night: str = ""


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
    """Read attempt.json (§4: classes come from hook-written evidence) and agree with the slot, or refuse."""
    where = f"slot {result['slot']} ({result['arm']}, {result['attempt_dir']})"
    path = night / result["arm"] / result["attempt_dir"] / "attempt.json"
    if not path.is_file():
        if cls == INFRASTRUCTURE:  # never counted (§4); it may have measured nothing to record
            return 0, 0
        raise Refused(f"{where}: no attempt.json at {path}")
    attempt = json.loads(path.read_text(encoding="utf-8"))
    for key in ("code", "verdict"):
        if attempt.get(key) != result.get(key):
            raise Refused(f"{where}: {key} disagrees: slot {result.get(key)!r}, {path} {attempt.get(key)!r}")
    if cls == INFRASTRUCTURE:  # never counted: its confinement, if any, is not read
        return 0, 0
    confinement = attempt.get("confinement")
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
        found.append(Cell(index, result["arm"], result["attempt_dir"], cls, refusals, reaches, night.name))
    return found


def counts(cells: list[Cell], *, admitted_only: bool, unavailable: str) -> dict:
    """Delivered over n per arm, and every excluded cell by name (§4, D2, D3)."""
    if unavailable not in SETTINGS:
        raise ValueError(f"unavailable must be one of {SETTINGS}, not {unavailable!r}")
    tally = {arm: {"delivered": 0, "n": 0} for arm in ARMS}
    excluded, reclassified = [], []
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
            if cell.cls == UNAVAILABLE:
                counted = "delivered" if delivered else "not delivered"
                reclassified.append({"attempt_dir": cell.attempt_dir, "arm": cell.arm, "night": cell.night,
                                     "why": f"unavailable verdict counted as {counted} (D2, Baseline-favouring)"})
            tally[cell.arm]["n"] += 1
            tally[cell.arm]["delivered"] += delivered
            continue
        excluded.append({"attempt_dir": cell.attempt_dir, "arm": cell.arm, "night": cell.night, "why": why})
    return {**tally, "excluded": excluded, "reclassified": reclassified}


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
    for name in ("primary", "admitted"):
        for arm in ARMS:
            if readings[name]["counts"][arm]["n"] == 0:
                raise Refused(f"the {name} reading has no {arm} cells; an empty arm decides nothing")
    rejecting = (readings["primary"]["rejects"], readings["admitted"]["rejects"])
    verdict = HOLDS if all(rejecting) else ONE_COUNT if any(rejecting) else NEGATIVE
    return {"alpha": alpha, **readings, "verdict": verdict}


def _table(result: dict) -> str:
    rows = ["| reading | baseline | engine | p | excluded | reclassified |", "|---|---|---|---|---|---|"]
    for name in ("primary", "admitted", "beside"):
        reading = result[name]
        tally = reading["counts"]
        rows.append("| " + " | ".join([
            name,
            *(f"{tally[arm]['delivered']}/{tally[arm]['n']}" for arm in ARMS),
            f"{reading['p']:.6f}",
            str(len(tally["excluded"])),
            str(len(tally["reclassified"])),
        ]) + " |")
    pairs = [f"night {pair['night']}; record {pair['record']}; evals_head: {', '.join(pair['evals_head']) or 'none recorded'}"
             for pair in result["pairs"]]
    return "\n".join([*rows, "", *pairs, "", f"alpha {result['alpha']}; verdict: {result['verdict']}"])


def _require_night_of_record(night: Path, record_path: Path) -> dict:
    """The night is complete and belongs to this record file; return its ledger."""
    if sorted(c.value for c in launch.INFRASTRUCTURE_CODES) != sorted(EXPECTED_INFRASTRUCTURE_CODES):
        raise Refused("launch.py's infrastructure codes differ from the frozen set: "
                      f"{sorted(c.value for c in launch.INFRASTRUCTURE_CODES)} against {sorted(EXPECTED_INFRASTRUCTURE_CODES)}")
    path = night / launch.LEDGER_NAME
    if not path.is_file():
        raise Refused(f"no {launch.LEDGER_NAME} in {night}")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if ledger.get("status") != "complete":
        raise Refused(f"the night's status is {ledger.get('status')!r}, not 'complete'")
    wanted = hashlib.sha256(record_path.read_bytes()).hexdigest()
    if ledger.get("record_sha256") != wanted:
        raise Refused(f"the night belongs to another record: its record_sha256 is {ledger.get('record_sha256')!r}, "
                      f"not {wanted!r}")
    if not isinstance(ledger.get("arm_sha256"), dict):
        raise Refused("launch.json has no arm_sha256 pinning the arms")
    return ledger


def _heads(ledger: dict) -> list[str]:
    heads = [sitting["evals_head"] for sitting in ledger.get("sittings", []) if sitting.get("evals_head")]
    return list(dict.fromkeys(heads))


def _require_complete(night: Path, record: dict) -> None:
    arms = str(record.get("arm", "")).split("+")
    if sorted(arms) != sorted(ARMS):
        raise Refused(f"record arms are {arms}; this reader decides baseline against engine only")
    finished = [result["arm"] for result in read_slots(night).values()]
    have = {arm: finished.count(arm) for arm in arms}
    if any(have[arm] != record["n"] for arm in arms):
        said = ", ".join(f"{arm} {have[arm]} of {record['n']}" for arm in arms)
        raise Refused(f"incomplete night: {said}")


def _across_pairs(pairs: list[tuple[Path, Path]], records: list[dict], ledgers: list[dict]) -> None:
    """Pairs belong to one decision: distinct, the same record apart from the allowed fields, the same arms."""
    for index, label in ((0, "night"), (1, "record")):
        resolved = [pair[index].resolve() for pair in pairs]
        for each in resolved:
            if resolved.count(each) > 1:
                raise Refused(f"the same {label} is named twice: {each}")
    first = {k: v for k, v in records[0].items() if k not in RECORD_FIELDS_MAY_DIFFER}
    for (_, path), record in zip(pairs[1:], records[1:], strict=True):
        other = {k: v for k, v in record.items() if k not in RECORD_FIELDS_MAY_DIFFER}
        differing = sorted(k for k in first.keys() | other.keys() if first.get(k) != other.get(k))
        if differing:
            raise Refused(f"{path} differs from {pairs[0][1]} in: {', '.join(differing)}")
    for (night, _), ledger in zip(pairs[1:], ledgers[1:], strict=True):
        if ledger["arm_sha256"] != ledgers[0]["arm_sha256"]:
            raise Refused(f"arm_sha256 differs between {pairs[0][0]} and {night}")


def main(argv: list[str]) -> int:
    if not argv or len(argv) % 2:
        raise Refused(USAGE)
    pairs = [(Path(argv[i]), Path(argv[i + 1])) for i in range(0, len(argv), 2)]
    records, ledgers = [], []
    for night, record_path in pairs:
        try:
            ledgers.append(_require_night_of_record(night, record_path))
            records.append(json.loads(record_path.read_text(encoding="utf-8")))
            _require_complete(night, records[-1])
        except Refused as refusal:
            raise Refused(f"{night}: {refusal}") from None
    _across_pairs(pairs, records, ledgers)
    cells = []
    for night, _ in pairs:
        try:
            cells += load(night)
        except Refused as refusal:
            raise Refused(f"{night}: {refusal}") from None
    listing = [{"night": str(night), "record": str(record_path), "evals_head": _heads(ledger)}
               for (night, record_path), ledger in zip(pairs, ledgers, strict=True)]
    result = {"pairs": listing, **decide(cells)}
    print(json.dumps(result, indent=2) + "\n\n" + _table(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
