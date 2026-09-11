#!/usr/bin/env python3
"""Reconcile the Phase TE claim inventory against the per-phase ledger.

Reads retained artifacts already on disk under a runs root, runs the pure
per-phase ledger over each named attempt, and writes
``docs/current/phase-v-claim-inventory.md``. No model, no network. The
artifacts live outside the repository, so this script is run explicitly; the
default tier never needs it.

Never originates a figure. The report states each attempt's recomputed
per-phase values beside the inventory's published values and the population
each belongs to; a refusal is printed as its named state, never as a zero.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.claim_inventory import (
    INVENTORY,
    ClaimRecord,
    render_table,
    validate_sources,
)
from satyrn_evals.claim_measures import (
    ClaimMeasure,
    destructive_edit,
    measure_inventory,
    restoration,
    verification_claim,
)
from satyrn_evals.phase_ledger import (
    PhaseLedger,
    ledger_from_baseline,
    ledger_from_engine,
)
from satyrn_evals.turn_ledger import events_from_pi_stdout

DEFAULT_RUNS_ROOT = Path(os.path.expanduser("~/satyrn-smokes"))
DEFAULT_OUTPUT = Path("docs/current/phase-v-claim-inventory.md")


@dataclass(frozen=True, slots=True)
class AttemptSpec:
    label: str
    run_dir: str
    arm: str


#: The attempts whose per-phase values are published. Engine transcripts are
#: `harness/.satyrn-implementer-transcript.jsonl`; Baseline transcripts are
#: nested under a session directory and carry a `session-record.json` sister.
ATTEMPTS: tuple[AttemptSpec, ...] = (
    AttemptSpec("baseline-01", "2026-09-11-te4-screen-baseline-01", "baseline"),
    AttemptSpec("baseline-02", "2026-09-11-te4-screen-baseline-02", "baseline"),
    AttemptSpec("engine-01", "2026-09-11-te4-screen-engine-01", "engine"),
    AttemptSpec("engine-02", "2026-09-11-te4-screen-engine-02", "engine"),
    AttemptSpec("round2-01", "2026-09-11-p4guardrail-round2-engine-01", "engine"),
    AttemptSpec("round2-02", "2026-09-11-p4guardrail-round2-engine-02", "engine"),
    AttemptSpec("recurrence-01", "2026-09-11-recurrence-engine-01", "engine"),
    AttemptSpec("recurrence-03", "2026-09-11-recurrence-engine-03", "engine"),
)


def _load_json(path: Path) -> Mapping[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def ledger_for(spec: AttemptSpec, runs_root: Path) -> PhaseLedger:
    run = runs_root / spec.run_dir
    if spec.arm == "engine":
        transcript = run / "harness" / ".satyrn-implementer-transcript.jsonl"
        if not transcript.exists():
            return PhaseLedger("absent", "no implementer transcript", ())
        return ledger_from_engine(
            transcript.read_text(encoding="utf-8", errors="replace"),
            _load_json(run / "chain.json"),
        )
    transcript = next(run.rglob("transcript.jsonl"), None)
    record = next(run.rglob("session-record.json"), None)
    if transcript is None:
        return PhaseLedger("absent", "no session transcript", ())
    return ledger_from_baseline(
        transcript.read_text(encoding="utf-8", errors="replace"),
        _load_json(record) if record is not None else None,
    )


def artifacts_for(spec: AttemptSpec, runs_root: Path) -> tuple[Path, ...]:
    """Every retained artifact this attempt's ledger reads."""
    run = runs_root / spec.run_dir
    if spec.arm == "engine":
        return (
            run / "harness" / ".satyrn-implementer-transcript.jsonl",
            run / "chain.json",
        )
    transcript = next(run.rglob("transcript.jsonl"), None)
    record = next(run.rglob("session-record.json"), None)
    return tuple(path for path in (transcript, record) if path is not None)


def _engine_events(
    spec: AttemptSpec, runs_root: Path
) -> tuple[Mapping[str, object], ...] | None:
    """Raw pi events from an Engine attempt's retained transcript.

    ``None`` when the transcript is absent, so a caller records that member as
    `undecidable` rather than silently folding the absence into an empty event
    list. The classifiers in ``claim_measures`` read the raw pi event shape,
    which ``events_from_pi_stdout`` produces directly from the Engine JSONL.
    """
    transcript = (
        runs_root / spec.run_dir / "harness" / ".satyrn-implementer-transcript.jsonl"
    )
    if not transcript.exists():
        return None
    return tuple(
        events_from_pi_stdout(
            transcript.read_text(encoding="utf-8", errors="replace")
        )
    )


def _phase4_reaching_engine_attempts(runs_root: Path) -> tuple[AttemptSpec, ...]:
    """Every Engine attempt whose chain record declares the full 4 phases.

    An Engine attempt reaches phase 4 iff its ``chain.json`` names
    ``phase-4-resolve-reopen``. This is the deterministic enumeration of the
    "15 phase-4-reaching Engine attempts" population: it reads the chain
    records, never guesses from run directory names.
    """
    specs: list[AttemptSpec] = []
    for chain_path in sorted(runs_root.glob("*/chain.json")):
        chain = _load_json(chain_path)
        if chain is None:
            continue
        phases = chain.get("phases")
        if not isinstance(phases, list):
            continue
        if not any(
            isinstance(phase, Mapping)
            and phase.get("step_id") == "phase-4-resolve-reopen"
            for phase in phases
        ):
            continue
        run_dir = chain_path.parent.name
        specs.append(AttemptSpec(run_dir, run_dir, "engine"))
    return tuple(specs)


def _count_measure(
    claim_id: str,
    measure: str,
    population: str,
    results: Sequence[str],
    published: str,
    action: str,
    gap: str,
) -> ClaimMeasure:
    """Fold per-attempt classifier results into one claim-level tri-state.

    `yes` only when at least one attempt is a match and no member is
    unreadable; `undecidable` when any member is unreadable (even alongside
    a `yes`), so a missing answer is never folded into a decided count; `no`
    only when every attempt answered no. The evidence carries the derived
    yes/undecidable count beside the published figure and the
    operationalization gap between them, never just the tri-state.
    """
    yes = results.count("yes")
    undecided = results.count("undecidable")
    if undecided:
        result = "undecidable"
    elif yes:
        result = "yes"
    else:
        result = "no"
    return ClaimMeasure(
        claim_id=claim_id,
        measure=measure,
        population=population,
        result=result,
        evidence=(
            f"derived {yes} yes, {undecided} undecidable, of {len(results)} "
            f"{action} (published {published})",
            f"operationalization gap: {gap}",
        ),
    )


def measure_inventory_for_run(
    records: Sequence[ClaimRecord],
    runs_root: Path,
    phase4: Sequence[AttemptSpec],
) -> tuple[ClaimMeasure, ...]:
    """The claim→measure binding, with the three covered measures wired.

    Starts from ``measure_inventory`` (every claim is ``undecidable`` until a
    classifier answers it) and overrides the three measures V2a can derive.
    An unenumerable phase-4 population stays ``undecidable`` and names the
    missing enumeration rather than guessing it.
    """
    measures = {m.claim_id: m for m in measure_inventory(records)}
    if phase4:
        destructive: list[str] = []
        restorations: list[str] = []
        for spec in phase4:
            events = _engine_events(spec, runs_root)
            destructive.append(
                "undecidable" if events is None else destructive_edit(events)
            )
            restorations.append(
                "undecidable" if events is None else restoration(events)
            )
        measures["c-destroyed-13-of-15"] = _count_measure(
            "c-destroyed-13-of-15",
            "destructive_edit",
            "15 phase-4-reaching Engine attempts",
            destructive,
            "13 of 15",
            "phase-4-reaching Engine attempts applied a destructive edit",
            "the classifier counts any content-changing edit, not the "
            "source's route-specific destruction (2 of 15 never touched the "
            "route)",
        )
        measures["c-restored-9-of-15"] = _count_measure(
            "c-restored-9-of-15",
            "restoration",
            "15 phase-4-reaching Engine attempts",
            restorations,
            "9 of 15",
            "phase-4-reaching Engine attempts restored removed content",
            "the classifier counts any removed content re-added, not the "
            "source's route-specific restoration before the phase ended",
        )
    else:
        for claim_id in ("c-destroyed-13-of-15", "c-restored-9-of-15"):
            base = measures[claim_id]
            measures[claim_id] = ClaimMeasure(
                claim_id=claim_id,
                measure=base.measure,
                population=base.population,
                result="undecidable",
                evidence=(
                    "the phase-4-reaching Engine population could not be "
                    "enumerated from the retained artifacts",
                ),
            )

    screen_01 = next(
        spec for spec in ATTEMPTS if spec.run_dir == "2026-09-11-te4-screen-engine-01"
    )
    screen_events = _engine_events(screen_01, runs_root)
    fabricated = (
        "undecidable"
        if screen_events is None
        else verification_claim(screen_events)
    )
    fabricated_evidence = (
        (
            "screen-engine-01's final summary claimed a passing test run while "
            "its last retained run_self_test returned exit code 1",
        )
        if fabricated == "no"
        else (
            f"verification_claim returned {fabricated}; the published "
            "fabrication framing is not reproduced by this measure",
        )
    )
    measures["c-fabricated-report-n1"] = ClaimMeasure(
        claim_id="c-fabricated-report-n1",
        measure="verification_claim",
        population="1 Engine screen attempt (screen-engine-01)",
        result=fabricated,
        evidence=fabricated_evidence,
    )

    return tuple(
        measures[record.id] for record in records if record.level == "claim"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head_commit() -> str:
    """The revision the artifacts were read under (V1 Currency rule)."""
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or "unrecorded"


def render_report(
    ledgers: Sequence[tuple[AttemptSpec, PhaseLedger]],
    *,
    head: str = "unrecorded",
    digests: Mapping[str, str] | None = None,
    runs_root: str = "unrecorded",
    measures: Sequence[ClaimMeasure] | None = None,
) -> str:
    digests = digests or {}
    if measures is None:
        measures = measure_inventory(INVENTORY)
    header = ["# Phase V — claim reconciliation", "", f"**HEAD:** `{head}`", ""]
    lines = [
        "| attempt | arm | state | reason | phases | per-phase turns | per-phase tool calls |",
        "|---|---|---|---|---|---|---|",
    ]
    for spec, ledger in ledgers:
        phases = ", ".join(cell.step_id for cell in ledger.cells) or "—"
        turns = ", ".join(str(cell.turns) for cell in ledger.cells) or "—"
        tools = ", ".join(str(cell.tool_calls) for cell in ledger.cells) or "—"
        lines.append(
            f"| {spec.label} | {spec.arm} | {ledger.state} | "
            f"{ledger.reason or '—'} | {phases} | {turns} | {tools} |"
        )
    provenance = [
        "",
        f"**Runs root:** `{runs_root}`",
        "",
        "## Artifact digests (sha256)",
        "",
        "| artifact | sha256 |",
        "|---|---|",
    ]
    provenance += [f"| {path} | {digest} |" for path, digest in digests.items()]
    measures_section = [
        "",
        "## Claim measures",
        "",
        "| claim_id | measure | population | result | evidence |",
        "|---|---|---|---|---|",
    ]
    for measure in measures:
        evidence = "; ".join(measure.evidence) or "—"
        measures_section.append(
            f"| {measure.claim_id} | {measure.measure} | {measure.population} | "
            f"{measure.result} | {evidence} |"
        )
    return "\n".join(
        (
            *header,
            *lines,
            *provenance,
            *measures_section,
            "",
            "## Claim inventory",
            "",
            render_table(),
            "",
        )
    )


def validate_root(
    root: Path,
    *,
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[str, ...]:
    return validate_sources(root, records=records)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    missing = validate_root(Path("."))
    if missing:
        print("missing cited sources:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    head = _head_commit()
    digests: dict[str, str] = {}
    phase4 = _phase4_reaching_engine_attempts(args.runs_root)
    for spec in (*ATTEMPTS, *phase4):
        for artifact in artifacts_for(spec, args.runs_root):
            if artifact.exists():
                digests[str(artifact.relative_to(args.runs_root))] = _sha256(artifact)
    ledgers = tuple((spec, ledger_for(spec, args.runs_root)) for spec in ATTEMPTS)
    measures = measure_inventory_for_run(INVENTORY, args.runs_root, phase4)
    report = render_report(
        ledgers,
        head=head,
        digests=digests,
        runs_root=str(args.runs_root),
        measures=measures,
    )
    if args.check:
        print(report)
        return 0
    args.output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
