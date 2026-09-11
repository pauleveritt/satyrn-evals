"""The Phase TE claim inventory: what was claimed, against what, for whom.

Declared in code as a frozen tuple, the way ``scripts/rescore_seams.py``'s
``SEAM_MAP`` declares its map before it is used -- so a reviewer can diff the
claims, and every cited path is testable. The human-readable table is
generated from this tuple, never written twice.

Statuses begin ``unreconciled``. V1 settles the ``level == "unit"`` records
from the per-phase ledger; V2 settles the rest with the claim-level measures;
V3 assigns the final status to every record. A record is never deleted when a
correction lands -- the correction is a dated block at its source.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

type ClaimStatus = Literal[
    "unreconciled",
    "confirmed",
    "corrected",
    "not_derivable",
    "claim_measure_mismatch",
]
type ClaimLevel = Literal["unit", "claim"]


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    """One published figure or framing, with the population it is about.

    ``source`` is the document where the figure was first published; each
    entry of ``carriers`` is another document that repeats it. Both carry an
    optional ``:line`` suffix for a human reader; validation strips it.
    """

    id: str
    quote: str
    source: str
    carriers: tuple[str, ...]
    level: ClaimLevel
    measure: str
    population: str
    status: ClaimStatus = "unreconciled"


#: The V1 inventory. Unit-level records are re-derived by the per-phase
#: ledger; claim-level records are V2's.
INVENTORY: tuple[ClaimRecord, ...] = (
    ClaimRecord(
        id="u-baseline-01-per-phase-turns",
        quote="43 (7/22/6/8)",
        source="docs/current/te4-screen-result.md:28",
        carriers=("ROADMAP.md:289",),
        level="unit",
        measure="turns per step_id",
        population="Baseline-01, 2026-09-11-te4-screen-baseline-01",
        status="confirmed",
    ),
    ClaimRecord(
        id="u-baseline-02-per-phase-turns",
        quote="32 (9/8/9/6)",
        source="docs/current/te4-screen-result.md:29",
        carriers=("ROADMAP.md:289",),
        level="unit",
        measure="turns per step_id",
        population="Baseline-02, 2026-09-11-te4-screen-baseline-02",
        status="confirmed",
    ),
    ClaimRecord(
        id="u-engine-01-per-phase-turns",
        quote="47 (6/8/10/23)",
        source="docs/current/te4-screen-result.md:30",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="Engine-01, 2026-09-11-te4-screen-engine-01",
        status="confirmed",
    ),
    ClaimRecord(
        id="u-engine-02-per-phase-turns",
        quote="45 (6/7/9/23)",
        source="docs/current/te4-screen-result.md:31",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="Engine-02, 2026-09-11-te4-screen-engine-02",
        status="confirmed",
    ),
    ClaimRecord(
        id="u-completion-turn-distribution",
        quote="43, 49, 44, 36",
        source="docs/current/te4-completion-recurrence-check-result.md:181",
        carriers=(),
        level="unit",
        measure="whole-attempt turns",
        population="the 4 recorded Engine completions",
        status="confirmed",
    ),
    ClaimRecord(
        id="u-recurrence-01-per-phase-turns",
        quote="44 (6/8/11/19)",
        source="docs/current/te4-completion-recurrence-check-result.md:12",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="2026-09-11-recurrence-engine-01",
        status="confirmed",
    ),
    ClaimRecord(
        id="u-recurrence-03-per-phase-turns",
        quote="36 (6/8/8/14)",
        source="docs/current/te4-completion-recurrence-check-result.md:14",
        carriers=(),
        level="unit",
        measure="turns per session",
        population="2026-09-11-recurrence-engine-03",
        status="confirmed",
    ),
    ClaimRecord(
        id="c-engine-population",
        quote="18 Engine attempts and 3 Baseline attempts",
        source="docs/current/te6-explain-and-decide.md:38",
        carriers=(),
        level="claim",
        measure="population statement",
        population="agentclinic-complaint-lifecycle, Phase TE sequence",
    ),
    ClaimRecord(
        id="c-baseline-3-of-3",
        quote="Baseline: **3 of 3 complete**",
        source="docs/current/te6-explain-and-decide.md:51",
        carriers=("ROADMAP.md:292",),
        level="claim",
        measure="completion_rate",
        population="3 Baseline attempts on agentclinic-complaint-lifecycle",
    ),
    ClaimRecord(
        id="c-contemporaneous-screen-tie-2-of-2",
        quote="2/2 vs 2/2",
        source="docs/current/te6-explain-and-decide.md:67",
        carriers=("docs/current/te6-explain-and-decide.md:251",),
        level="claim",
        measure="completion_rate",
        population="the final screen, both configurations fresh on the identical prompt",
    ),
    ClaimRecord(
        id="c-completion-6-of-18",
        quote="6 of 18",
        source="docs/current/te6-explain-and-decide.md:54",
        carriers=(
            "ROADMAP.md:292",
            "docs/current/index.md:234",
            "docs/current/te4-screen-result.md:43",
        ),
        level="claim",
        measure="completion_rate",
        population="18 Engine attempts on agentclinic-complaint-lifecycle",
    ),
    ClaimRecord(
        id="c-completion-4-of-16",
        quote="4 of 16",
        source="docs/current/te4-completion-recurrence-check-result.md:22",
        carriers=("ROADMAP.md:275", "docs/current/index.md:208"),
        level="claim",
        measure="completion_rate",
        population="16 Engine attempts before the 2026-09-11 screen",
    ),
    ClaimRecord(
        id="c-destroyed-13-of-15",
        quote="destroyed in 13 of 15",
        source="docs/current/te6-explain-and-decide.md:147",
        carriers=(),
        level="claim",
        measure="destructive_edit",
        population="15 phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-restored-9-of-15",
        quote="9 of 15",
        source="docs/current/te6-explain-and-decide.md:169",
        carriers=(),
        level="claim",
        measure="restoration",
        population="15 phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-redirect-fixed-1-of-9",
        quote="1 of 9",
        source="docs/current/te6-explain-and-decide.md:174",
        carriers=(),
        level="claim",
        measure="redirect_trap_resolution",
        population="9 attempts showing the redirect-trap signature",
    ),
    ClaimRecord(
        id="c-nonrestore-0-of-6",
        quote="0 of 6",
        source="docs/current/te4-completion-recurrence-check-result.md:178",
        carriers=("docs/current/index.md:204", "ROADMAP.md:272"),
        level="claim",
        measure="completion_rate",
        population="6 non-restoring phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-restore-4-of-7",
        quote="4 of 7",
        source="docs/current/te4-completion-recurrence-check-result.md:179",
        carriers=("docs/current/index.md:205", "ROADMAP.md:272"),
        level="claim",
        measure="completion_rate",
        population="7 restoring phase-4-reaching Engine attempts",
    ),
    ClaimRecord(
        id="c-phase4-denominator-6-of-10",
        quote="6 of 8",
        source="docs/current/te6-explain-and-decide.md:87",
        carriers=("docs/current/te6-explain-and-decide.md:93",),
        level="claim",
        measure="denominator_binding",
        population="10 attempts under the current prompt, not 8",
    ),
    ClaimRecord(
        id="c-redirect-6-of-9",
        quote="6 of 9",
        source="docs/current/te4-phase4-guardrail-reverification-result.md:30",
        carriers=("docs/current/index.md:164",),
        level="claim",
        measure="redirect_trap_occurrence",
        population="9 phase-4-reaching Engine attempts at that round",
    ),
    ClaimRecord(
        id="c-fabricated-report-n1",
        quote="fabricated a fully invented passing pytest transcript",
        source="docs/current/te6-explain-and-decide.md:110",
        carriers=("docs/current/te4-screen-result.md:20", "ROADMAP.md:282"),
        level="claim",
        measure="verification_claim",
        population="1 Engine screen attempt (screen-engine-01)",
    ),
)


def validate_sources(
    root: Path = Path("."),
    *,
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[str, ...]:
    """Every path a record cites that does not exist under ``root``.

    The ``:line`` suffix is for readers; only the path is checked, so a
    reflow that moves a figure within its file does not fail this test."""
    missing: list[str] = []
    for record in records:
        for cited in (record.source, *record.carriers):
            path = cited.rsplit(":", 1)[0]
            if not (root / path).exists():
                missing.append(cited)
    return tuple(missing)


def render_table(records: Sequence[ClaimRecord] = INVENTORY) -> str:
    """The inventory as a Markdown table, generated from the tuple."""
    header = (
        "| id | level | status | measure | population | quote | source | carriers |",
        "|---|---|---|---|---|---|---|---|",
    )
    rows = [
        "| {id} | {level} | {status} | {measure} | {population} | {quote} | "
        "{source} | {carriers} |".format(
            id=record.id,
            level=record.level,
            status=record.status,
            measure=record.measure,
            population=record.population,
            quote=record.quote,
            source=record.source,
            carriers=", ".join(record.carriers) or "—",
        )
        for record in records
    ]
    return "\n".join((*header, *rows))
