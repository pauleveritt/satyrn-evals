#!/usr/bin/env python3
"""Build the V3 engine gap register. Exploratory; no published figures.

Each row names an engine-improvement candidate, the measure that indicates
it, its population, the observed exploratory value, and the proposed engine
change. No row enters a claim or denominator: the register ranks candidates,
it does not publish rates. ``main`` reads retained Engine transcripts under
``~/satyrn-smokes`` for the classifier-backed rows and reads the phase-4
turn-cost row from the already-generated per-phase ledger; an absent artifact
is written ``not measured``, never guessed.
"""

import argparse
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from reconcile_claims import (
    AttemptSpec,
    _current_prompt_attempts,
    _engine_events,
    _head_commit,
    _phase4_reaching_engine_attempts,
)

from satyrn_evals.claim_measures import (
    destructive_edit,
    restoration,
    self_test_outcome,
    verification_claim,
)

EXPLORATORY = "exploratory"
DEFAULT_RUNS_ROOT = Path(os.path.expanduser("~/satyrn-smokes"))
DEFAULT_OUTPUT = Path("docs/current/phase-v-engine-gap-register.md")
DEFAULT_LEDGER = Path("docs/current/phase-v-claim-inventory.md")
INDEX = Path("docs/current/index.md")
TOCTREE_ENTRY = "phase-v-engine-gap-register"
TOCTREE_ANCHOR = "phase-v-claim-inventory\n"

#: The four screen attempts whose per-phase turn counts the turn-cost row
#: reads from the generated ledger. Two arms, two attempts each.
_SCREEN_ATTEMPTS = frozenset(
    {"baseline-01", "baseline-02", "engine-01", "engine-02"}
)


@dataclass(frozen=True, slots=True)
class GapCandidate:
    id: str
    candidate: str
    measure: str
    population: str
    proposed_change: str
    rationale: str


GAP_REGISTER: tuple[GapCandidate, ...] = (
    GapCandidate(
        id="g-verification-honesty",
        candidate="Self-reported verification is not authoritative",
        measure="verification_claim",
        population="retained Engine attempts under the final prompt",
        proposed_change=(
            "V4: grade Contract.test_command's own result on AttemptResult, "
            "independent of model text"
        ),
        rationale=(
            "A screen attempt fabricated a passing pytest report over a "
            "retained exit code 1; report honesty and pass/fail are separable."
        ),
    ),
    GapCandidate(
        id="g-self-test-friction",
        candidate="The required self-test fails at phase 4 and is not closed",
        measure="self_test_outcome",
        population="phase-4-reaching Engine attempts",
        proposed_change=(
            "V4/V6: surface the authoritative self-test outcome in the packet "
            "result so a failing required check cannot be reported as success"
        ),
        rationale=(
            "Redirect-trap friction recurs across the sequence and never "
            "closed via a prompt fix."
        ),
    ),
    GapCandidate(
        id="g-phase4-turn-cost",
        candidate="Phase-4 turn cost dominates the whole-attempt budget",
        measure="turn_cost",
        population="screen Engine attempts versus Baseline",
        proposed_change=(
            "V5: a whole-attempt turn limit and wall-clock deadline, retaining "
            "partial work"
        ),
        rationale=(
            "Engine uses fewer turns across phases 1-3 in total and far more "
            "on phase 4; the gap is entirely phase 4."
        ),
    ),
    GapCandidate(
        id="g-restoration-churn",
        candidate="Destructive edits are frequent and restoration is not",
        measure="restoration",
        population="phase-4-reaching Engine attempts",
        proposed_change=(
            "V4: a validation boundary that makes a broken route visible before "
            "the attempt ends"
        ),
        rationale=(
            "The V2 classifiers measure a broader property than the published "
            "route-specific counts; the churn signal is exploratory."
        ),
    ),
)


def render_gap_register(
    observations: Mapping[str, str],
    *,
    head: str = "unrecorded",
    runs_root: str = "unrecorded",
) -> str:
    lines = [
        "# Phase V — engine gap register",
        "",
        "**Exploratory. Not published figures.** Each row names the measure that "
        "indicates a candidate engine improvement, its population, and the "
        "observed value. No row enters a claim or denominator.",
        "",
        f"**Provenance:** read under `HEAD` {head}; populations: current-prompt "
        f"and phase-4-reaching Engine attempts from `{runs_root}`, and the "
        f"screen turn costs from the generated per-phase ledger.",
        "",
        "| candidate | measure | population | observed (exploratory) | proposed change | rationale |",
        "|---|---|---|---|---|---|",
    ]
    for row in GAP_REGISTER:
        lines.append(
            f"| {row.candidate} | {row.measure} | {row.population} | "
            f"{observations.get(row.id, 'not measured')} | "
            f"{row.proposed_change} | {row.rationale} |"
        )
    return "\n".join(lines) + "\n"


def observations_for_attempts(
    attempts: Sequence[Sequence[Mapping[str, object]]],
) -> dict[str, str]:
    """Exploratory counts over per-attempt event lists.

    Each row's observed value is a count over the supplied population and is
    labelled exploratory: it is a discovery input, never a published rate.
    """

    def count(measure, expected: str) -> int:
        return sum(1 for events in attempts if measure(events) == expected)

    total = len(attempts)
    return {
        "g-verification-honesty": (
            f"{count(verification_claim, 'no')} of {total} attempts show a false "
            f"verification claim (exploratory)"
        ),
        "g-self-test-friction": (
            f"{count(lambda e: self_test_outcome(e, chain=None), 'no')} of {total} "
            f"attempts fail their required self-test (exploratory)"
        ),
        "g-restoration-churn": (
            f"{count(destructive_edit, 'yes')} destructive, "
            f"{count(restoration, 'yes')} restoring, of {total} (exploratory)"
        ),
    }


def _events_for(
    specs: Sequence[AttemptSpec], runs_root: Path
) -> tuple[tuple[tuple[Mapping[str, object], ...], ...], bool]:
    """Retained event lists for each spec, plus whether any transcript is absent.

    An absent transcript is reported as ``not measured`` by the caller rather
    than silently shrinking the denominator.
    """
    events: list[tuple[Mapping[str, object], ...]] = []
    any_absent = False
    for spec in specs:
        retained = _engine_events(spec, runs_root)
        if retained is None:
            any_absent = True
        else:
            events.append(tuple(retained))
    return tuple(events), any_absent


def _turn_cost_observation(ledger_doc: Path) -> str:
    """The phase-4 turn cost, read from the generated per-phase ledger.

    The ledger is the committed ``phase-v-claim-inventory.md`` table; this
    reads its phase-4 (last) per-phase turn cell for the four screen attempts
    rather than recomputing the counts from transcripts.
    """
    if not ledger_doc.exists():
        return "not measured"
    per_phase: dict[str, int] = {}
    for line in ledger_doc.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] not in _SCREEN_ATTEMPTS:
            continue
        turns = cells[5].split(",")
        if len(turns) != 4:
            return "not measured"
        try:
            per_phase[cells[0]] = int(turns[-1].strip())
        except ValueError:
            return "not measured"
    if set(per_phase) != _SCREEN_ATTEMPTS:
        return "not measured"
    engine = f"{per_phase['engine-01']}, {per_phase['engine-02']}"
    baseline = f"{per_phase['baseline-01']}, {per_phase['baseline-02']}"
    return (
        f"phase-4 turns {engine} (Engine) vs {baseline} (Baseline) — "
        f"per-phase ledger (exploratory)"
    )


def _build_observations(runs_root: Path, ledger_doc: Path) -> dict[str, str]:
    """Fill every register row from its own population's retained artifacts.

    The verification-honesty row counts over the current-prompt (final)
    population; the self-test and restoration rows count over the
    phase-4-reaching population; the turn-cost row reads the committed ledger.
    """
    observations: dict[str, str] = {}
    current, current_absent = _events_for(
        _current_prompt_attempts(runs_root), runs_root
    )
    phase4, phase4_absent = _events_for(
        _phase4_reaching_engine_attempts(runs_root), runs_root
    )

    if current_absent or not current:
        observations["g-verification-honesty"] = "not measured"
    else:
        observations["g-verification-honesty"] = observations_for_attempts(
            current
        )["g-verification-honesty"]

    if phase4_absent or not phase4:
        observations["g-self-test-friction"] = "not measured"
        observations["g-restoration-churn"] = "not measured"
    else:
        from_phase4 = observations_for_attempts(phase4)
        observations["g-self-test-friction"] = from_phase4["g-self-test-friction"]
        observations["g-restoration-churn"] = from_phase4["g-restoration-churn"]

    observations["g-phase4-turn-cost"] = _turn_cost_observation(ledger_doc)
    return observations


def _ensure_toctree_entry(index: Path, entry: str) -> None:
    text = index.read_text(encoding="utf-8")
    if f"\n{entry}\n" in text:
        return
    if TOCTREE_ANCHOR not in text:
        raise RuntimeError(f"toctree anchor missing from {index}")
    index.write_text(
        text.replace(TOCTREE_ANCHOR, TOCTREE_ANCHOR + entry + "\n", 1),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    observations = _build_observations(args.runs_root, args.ledger)
    report = render_gap_register(
        observations,
        head=_head_commit(),
        runs_root=str(args.runs_root),
    )
    if args.check:
        print(report)
        return 0
    args.output.write_text(report, encoding="utf-8")
    _ensure_toctree_entry(args.index, TOCTREE_ENTRY)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
