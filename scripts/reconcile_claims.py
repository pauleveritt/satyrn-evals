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
from satyrn_evals.phase_ledger import (
    PhaseLedger,
    ledger_from_baseline,
    ledger_from_engine,
)

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
) -> str:
    digests = digests or {}
    header = ["# Phase V1 — per-phase ledger", "", f"**HEAD:** `{head}`", ""]
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
    return "\n".join(
        (
            *header,
            *lines,
            *provenance,
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
    for spec in ATTEMPTS:
        for artifact in artifacts_for(spec, args.runs_root):
            if artifact.exists():
                digests[str(artifact.relative_to(args.runs_root))] = _sha256(artifact)
    ledgers = tuple((spec, ledger_for(spec, args.runs_root)) for spec in ATTEMPTS)
    report = render_report(
        ledgers,
        head=head,
        digests=digests,
        runs_root=str(args.runs_root),
    )
    if args.check:
        print(report)
        return 0
    args.output.write_text(report, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
