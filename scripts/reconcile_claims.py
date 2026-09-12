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
    baseline_completion_rate,
    completion_rate,
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


def _prompt_fingerprint(chain: Mapping[str, object]) -> str | None:
    """The full packet of every phase, hashed deterministically.

    Two attempts under the same prompt state share the fingerprint. ``None``
    when a phase lacks a readable packet, so the fingerprint is only asserted
    for chains that record the full prompt content. A phase-2-board runaway
    that retained only phase-1/phase-2 packets hashes only those phases, which
    are shared with the superseded guardrail prompt, so its prompt state is
    not distinguishable by this fingerprint.

    Field scope (a limit, not a semantic summary): the fingerprint is the
    entire retained packet (``json.dumps(packet, sort_keys=True)``), so any
    packet-field change -- not only an objective/facts change -- separates two
    prompt states, and a chain that retained fewer phases cannot match a
    longer one.
    """
    phases = chain.get("phases")
    if not isinstance(phases, list) or not phases:
        return None
    digest = hashlib.sha256()
    for phase in phases:
        if not isinstance(phase, Mapping):
            return None
        packet = phase.get("packet")
        if not isinstance(packet, Mapping):
            return None
        digest.update(json.dumps(packet, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


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


def _engine_task(runs_root: Path, run_dir: str) -> str | None:
    """The task name the grader recorded for an Engine run.

    Engine ``chain.json`` carries no task field; the grader's retained
    receipts (``grading/receipts/*.json``) do. A single agreed task name is
    the membership authority; missing or disagreeing receipts are ``None``.
    """
    receipts_dir = runs_root / run_dir / "grading" / "receipts"
    tasks: set[str] = set()
    for receipt_path in receipts_dir.glob("*.json"):
        receipt = _load_json(receipt_path)
        if receipt is not None and isinstance(receipt.get("task"), str):
            tasks.add(receipt["task"])
    if len(tasks) == 1:
        return next(iter(tasks))
    return None


def _complaint_lifecycle_engine_attempts(
    runs_root: Path,
) -> tuple[AttemptSpec, ...]:
    """Every retained Engine chain the grader names as
    ``agentclinic-complaint-lifecycle``, deterministically.

    Membership is the grader's own receipt task name, never the run directory
    name. This is the committed rule that derives the published 18-attempt
    Engine population rather than copying the figure.
    """
    specs: list[AttemptSpec] = []
    for chain_path in sorted(runs_root.glob("*/chain.json")):
        run_dir = chain_path.parent.name
        if _engine_task(runs_root, run_dir) == "agentclinic-complaint-lifecycle":
            specs.append(AttemptSpec(run_dir, run_dir, "engine"))
    return tuple(specs)


def _complaint_lifecycle_baseline_records(runs_root: Path) -> tuple[Path, ...]:
    """Every retained Baseline session the record names as
    ``agentclinic-complaint-lifecycle``, deterministically."""
    records: list[Path] = []
    for record_path in sorted(runs_root.rglob("session-record.json")):
        record = _load_json(record_path)
        if record is not None and record.get("task") == "agentclinic-complaint-lifecycle":
            records.append(record_path)
    return tuple(records)


def _completion_results(
    specs: Sequence[AttemptSpec],
    runs_root: Path,
    declared_phases: int,
) -> list[str]:
    """``completion_rate`` per Engine member, short task members as ``no``.

    ``completion_rate`` refuses a chain shorter than ``declared_phases``
    because, without the task name, a short chain could be a completed
    shorter task (the phase-2 guardrail candidate) instead of a
    non-completion. The population rule above already restricts ``specs`` to
    ``agentclinic-complaint-lifecycle`` (a four-phase task), so a short member
    here is a phase-2-board runaway that never reached phase 4 — a
    non-completion, not an ungradeable record.
    """
    results: list[str] = []
    for spec in specs:
        chain = _load_json(runs_root / spec.run_dir / "chain.json")
        if chain is None:
            results.append("undecidable")
            continue
        verdict = completion_rate(chain, declared_phases=declared_phases)
        if verdict == "undecidable":
            phases = chain.get("phases")
            final_decision = chain.get("final_decision")
            if (
                isinstance(phases, list)
                and isinstance(final_decision, Mapping)
                and len(phases) < declared_phases
            ):
                results.append("no")
                continue
        results.append(verdict)
    return results


def _current_prompt_attempts(runs_root: Path) -> tuple[AttemptSpec, ...]:
    """The Engine attempts under the current (final) prompt, deterministically.

    The current prompt is the prompt state the final screen's two Engine
    attempts ran under (te6's "identical, final prompt state"); an attempt
    belongs to it iff its chain record's full packet fingerprint matches
    theirs. An attempt that stopped before phase 4 retained only
    phase-1/phase-2 packets, whose content is shared with the superseded
    guardrail prompt, so its membership is not derivable and is *not* guessed
    here -- the caller names that gap instead.
    """
    screen_fingerprints: set[str] = set()
    for spec in ATTEMPTS:
        if spec.arm != "engine" or "te4-screen" not in spec.run_dir:
            continue
        chain = _load_json(runs_root / spec.run_dir / "chain.json")
        if chain is None:
            continue
        fingerprint = _prompt_fingerprint(chain)
        if fingerprint is not None:
            screen_fingerprints.add(fingerprint)
    if len(screen_fingerprints) != 1:
        return ()
    current = next(iter(screen_fingerprints))
    specs: list[AttemptSpec] = []
    for chain_path in sorted(runs_root.glob("*/chain.json")):
        chain = _load_json(chain_path)
        if chain is None or _prompt_fingerprint(chain) != current:
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


def denominator_binding(
    attempts: tuple[str, ...], phase4: tuple[str, ...]
) -> ClaimMeasure:
    """The `6 of 8` -> `6 of 10` correction as an executable binding.

    Names the full attempt population and the phase-4-reaching subset it was
    narrowed to. Confirms only the published denominator's shape -- a
    population of 10 with a phase-4-reaching subset of 8 -- so any other
    non-empty set is `undecidable`, never a guessed `yes`. The completion
    count is *read*, never re-derived: a hidden-grader verdict is not a
    transcript-local fact.
    """
    if not attempts:
        return ClaimMeasure(
            claim_id="c-phase4-denominator-6-of-10",
            measure="denominator_binding",
            population="0 attempts",
            result="undecidable",
            evidence=("no attempts supplied",),
        )
    if len(attempts) == 10 and len(phase4) == 8:
        return ClaimMeasure(
            claim_id="c-phase4-denominator-6-of-10",
            measure="denominator_binding",
            population=f"{len(attempts)} attempts under the current prompt",
            result="yes",
            evidence=(f"phase-4-reaching subset: {len(phase4)} of {len(attempts)}",),
        )
    return ClaimMeasure(
        claim_id="c-phase4-denominator-6-of-10",
        measure="denominator_binding",
        population=f"{len(attempts)} attempts under the current prompt",
        result="undecidable",
        evidence=(
            f"derived {len(phase4)} phase-4-reaching of {len(attempts)} "
            "attempts, not the published 8-of-10 phase-4-reaching shape the "
            "6 of 10 denominator binds",
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

    # The `6 of 8` -> `6 of 10` denominator binding. The correction's
    # population is all 10 attempts under the current prompt: the enumerated
    # phase-4-reaching attempts plus 2 phase-2-board runaways
    # (p4guardrail-engine-02, recurrence-engine-02). The runaways retained
    # only phase-1/phase-2 packets, byte-identical between the superseded
    # guardrail prompt and the current prompt, so their membership is not
    # derivable from retained artifacts -- the confirmed binding below needs
    # all 10 enumerable with the published 8 phase-4-reaching subset, which is
    # unreachable here, so the record names the gap over the honest enumerable
    # set, never a guessed 10.
    current_prompt = _current_prompt_attempts(runs_root)
    current_phase4 = tuple(
        spec for spec in current_prompt
        if spec.run_dir in {p.run_dir for p in phase4}
    )
    if current_prompt and len(current_prompt) == 10:
        measures["c-phase4-denominator-6-of-10"] = denominator_binding(
            tuple(spec.run_dir for spec in current_prompt),
            tuple(spec.run_dir for spec in current_phase4),
        )
    elif current_prompt:
        measures["c-phase4-denominator-6-of-10"] = ClaimMeasure(
            claim_id="c-phase4-denominator-6-of-10",
            measure="denominator_binding",
            population=(
                f"{len(current_prompt)} of 10 attempts under the current "
                "prompt (phase-4-reaching subset enumerable; pre-phase-4 "
                "chains not enumerable)"
            ),
            result="undecidable",
            evidence=(
                "all pre-phase-4 chains are non-enumerable from retained "
                "artifacts (the published correction counts two of them); a "
                "chain that stopped before phase 4 retained only "
                "phase-1/phase-2 packets, whose content is byte-identical "
                "between the superseded guardrail prompt and the current "
                "prompt, so its current-prompt membership is not derivable "
                "from retained artifacts",
            ),
        )
    else:
        measures["c-phase4-denominator-6-of-10"] = ClaimMeasure(
            claim_id="c-phase4-denominator-6-of-10",
            measure="denominator_binding",
            population="10 attempts under the current prompt, not 8",
            result="undecidable",
            evidence=(
                "the current-prompt population could not be enumerated from "
                "the retained artifacts",
            ),
        )

    # V3b: the completion claims. Every retained Engine chain's `chain.json`
    # carries `final_decision` and Baseline's `session-record.json` carries
    # its `code`, so V3's `absent_artifact` label was wrong; the real gap was
    # the population membership rule. The Engine population is the grader's
    # own receipt task name (``agentclinic-complaint-lifecycle``), and the
    # Baseline population is the session record's ``task`` field.
    engine_specs = _complaint_lifecycle_engine_attempts(runs_root)
    baseline_records = _complaint_lifecycle_baseline_records(runs_root)
    screen_run_dirs = {
        spec.run_dir
        for spec in ATTEMPTS
        if spec.arm == "engine" and "te4-screen" in spec.run_dir
    }
    pre_screen = tuple(
        spec for spec in engine_specs if spec.run_dir not in screen_run_dirs
    )

    if engine_specs and baseline_records:
        measures["c-engine-population"] = ClaimMeasure(
            claim_id="c-engine-population",
            measure="population statement",
            population=(
                "agentclinic-complaint-lifecycle attempts named by the "
                "grader's retained receipts and session records"
            ),
            result="yes",
            evidence=(
                f"derived {len(engine_specs)} Engine attempts and "
                f"{len(baseline_records)} Baseline attempts "
                "(published 18 Engine attempts and 3 Baseline attempts)",
            ),
        )
    else:
        measures["c-engine-population"] = ClaimMeasure(
            claim_id="c-engine-population",
            measure=measures["c-engine-population"].measure,
            population=measures["c-engine-population"].population,
            result="undecidable",
            evidence=(
                "the complaint-lifecycle population could not be enumerated "
                "from the retained grader receipts and session records",
            ),
        )

    if engine_specs:
        completion_18 = _completion_results(engine_specs, runs_root, 4)
        measures["c-completion-6-of-18"] = _count_measure(
            "c-completion-6-of-18",
            "completion_rate",
            "18 Engine attempts on agentclinic-complaint-lifecycle",
            completion_18,
            "6 of 18",
            "Engine attempts on agentclinic-complaint-lifecycle completed "
            "the task",
            "a chain shorter than the declared four phases is a "
            "phase-2-board runaway (a non-completion), not an ungradeable "
            "record",
        )
        completion_16 = _completion_results(pre_screen, runs_root, 4)
        measures["c-completion-4-of-16"] = _count_measure(
            "c-completion-4-of-16",
            "completion_rate",
            "16 Engine attempts before the 2026-09-11 screen",
            completion_16,
            "4 of 16",
            "pre-screen Engine attempts on agentclinic-complaint-lifecycle "
            "completed the task",
            "a chain shorter than the declared four phases is a "
            "phase-2-board runaway (a non-completion), not an ungradeable "
            "record",
        )
    else:
        for claim_id in ("c-completion-6-of-18", "c-completion-4-of-16"):
            base = measures[claim_id]
            measures[claim_id] = ClaimMeasure(
                claim_id=claim_id,
                measure=base.measure,
                population=base.population,
                result="undecidable",
                evidence=(
                    "the Engine population could not be enumerated from the "
                    "retained grader receipts",
                ),
            )

    if baseline_records:
        baseline_results = [
            "undecidable"
            if (record := _load_json(path)) is None
            else baseline_completion_rate(record, declared_phases=4)
            for path in baseline_records
        ]
        measures["c-baseline-3-of-3"] = _count_measure(
            "c-baseline-3-of-3",
            "completion_rate",
            "3 Baseline attempts on agentclinic-complaint-lifecycle",
            baseline_results,
            "3 of 3",
            "Baseline sessions on agentclinic-complaint-lifecycle completed "
            "the task",
            "the session `code` names completion; the final step's hidden- "
            "grader `feature_verdict` is a separate signal",
        )
    else:
        measures["c-baseline-3-of-3"] = ClaimMeasure(
            claim_id="c-baseline-3-of-3",
            measure=measures["c-baseline-3-of-3"].measure,
            population=measures["c-baseline-3-of-3"].population,
            result="undecidable",
            evidence=(
                "the Baseline population could not be enumerated from the "
                "retained session records",
            ),
        )

    # c-nonrestore-0-of-6 and c-restore-4-of-7 name the route-specific
    # restoring/non-restoring split of the 13 pre-screen phase-4-reaching
    # attempts. The completion verdicts are readable from chain.json, but the
    # split itself is the route-specific restoration the transcript-level
    # `restoration` measure cannot reproduce (V2a's c-restored-9-of-15
    # mismatch); enumerating it would reopen the 9-of-15 decision, which V3b
    # does not do.
    for claim_id in ("c-nonrestore-0-of-6", "c-restore-4-of-7"):
        base = measures[claim_id]
        measures[claim_id] = ClaimMeasure(
            claim_id=claim_id,
            measure="completion_rate",
            population=base.population,
            result="undecidable",
            evidence=(
                "the completion verdict is readable from chain.json, but the "
                "restoring/non-restoring split is the route-specific "
                "restoration the transcript-level `restoration` measure "
                "cannot reproduce; enumerating the subset would reopen the "
                "9-of-15 decision",
            ),
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
    # V3b: the completion measures read the full complaint-lifecycle
    # population's chain.json, the grader receipts that name each Engine
    # attempt's task, and the Baseline session records. Record their digests
    # under the same currency rule as the per-phase ledger reads.
    engine_specs = _complaint_lifecycle_engine_attempts(args.runs_root)
    baseline_records = _complaint_lifecycle_baseline_records(args.runs_root)
    for spec in engine_specs:
        chain = args.runs_root / spec.run_dir / "chain.json"
        if chain.exists():
            digests[str(chain.relative_to(args.runs_root))] = _sha256(chain)
        receipts_dir = args.runs_root / spec.run_dir / "grading" / "receipts"
        for receipt_path in sorted(receipts_dir.glob("*.json")):
            if receipt_path.exists():
                digests[str(receipt_path.relative_to(args.runs_root))] = _sha256(receipt_path)
    for record_path in baseline_records:
        digests[str(record_path.relative_to(args.runs_root))] = _sha256(record_path)
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
