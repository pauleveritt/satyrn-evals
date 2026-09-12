"""The V3 close-out audit: every claim one status, no carrier lagging source.

Pure. The audit reads the frozen inventory and the repository's own files;
it originates no figure and changes no record.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from satyrn_evals.claim_inventory import INVENTORY, ClaimLevel, ClaimRecord

type FinalStatus = Literal[
    "confirmed", "corrected", "not_derivable", "claim_measure_mismatch"
]

type GapKind = Literal["absent_artifact", "unimplemented_measure"]

#: What each `not_derivable` record is waiting on, and of which kind. V3's
#: rule is that a `not_derivable` status without a named gap is a close-out
#: failure; the kind matters because "an artifact we never retained" and "a
#: measure this implementation does not define" are different findings, and
#: the second must not read as the first.
#:
#: Corrected 2026-09-11 (V3b): the completion claims were not missing the
#: verdicts — every retained Engine chain carries `final_decision` and every
#: Baseline `session-record.json` carries its `code` — so their
#: `absent_artifact` label was wrong. `c-completion-6-of-18`,
#: `c-completion-4-of-16`, `c-baseline-3-of-3` and `c-engine-population` are
#: now derived and confirmed; `c-nonrestore-0-of-6`/`c-restore-4-of-7` stay
#: `not_derivable`, but for an unimplemented route-specific restoration
#: classifier (the 9-of-15 mismatch), not a missing verdict.
MISSING_ARTIFACT: dict[str, tuple[GapKind, str]] = {
    "c-contemporaneous-screen-tie-2-of-2": (
        "unimplemented_measure",
        "an outcome measure executable from transcripts",
    ),
    "c-nonrestore-0-of-6": (
        "unimplemented_measure",
        "a route-specific restoration classifier to define the non-restoring "
        "subset",
    ),
    "c-restore-4-of-7": (
        "unimplemented_measure",
        "a route-specific restoration classifier to define the restoring "
        "subset",
    ),
    "c-redirect-fixed-1-of-9": (
        "unimplemented_measure",
        "a redirect-trap resolution classifier",
    ),
    "c-redirect-6-of-9": (
        "unimplemented_measure",
        "a redirect-trap occurrence classifier",
    ),
    "c-phase4-denominator-6-of-10": (
        "absent_artifact",
        "prompt-state membership for the pre-phase-4 chains",
    ),
}


@dataclass(frozen=True, slots=True)
class CloseoutRow:
    claim_id: str
    level: ClaimLevel
    status: FinalStatus
    source: str
    carriers: tuple[str, ...]
    missing: str | None = None
    missing_kind: GapKind | None = None


def _record_missing(record: ClaimRecord) -> tuple[GapKind, str] | None:
    if record.status != "not_derivable":
        return None
    return MISSING_ARTIFACT.get(record.id)


def closeout_rows(
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[CloseoutRow, ...]:
    rows: list[CloseoutRow] = []
    for record in records:
        gap = _record_missing(record)
        rows.append(
            CloseoutRow(
                claim_id=record.id,
                level=record.level,
                status=cast(FinalStatus, record.status),
                source=record.source,
                carriers=record.carriers,
                missing=gap[1] if gap else None,
                missing_kind=gap[0] if gap else None,
            )
        )
    return tuple(rows)


def carrier_lag(
    records: Sequence[ClaimRecord] = INVENTORY,
    root: Path = Path("."),
) -> tuple[str, ...]:
    """Carrier paths that no longer exist. A hard failure.

    Path existence is the check V3 can make mechanically; textual drift is
    `quote_drift`, a review list rather than a failure, because a legitimate
    carrier may paraphrase.
    """
    return tuple(
        cited
        for record in records
        for cited in record.carriers
        if not (root / cited.rsplit(":", 1)[0]).exists()
    )


def quote_drift(
    records: Sequence[ClaimRecord] = INVENTORY,
    root: Path = Path("."),
) -> tuple[str, ...]:
    """Carriers whose text no longer contains the record's fixed quote.

    A review list, not a failure: the V1 correction preserved the original
    wording inside a dated block, so a carrier that quotes still matches,
    while one that paraphrases is flagged for a human to read.
    """
    drifted: list[str] = []
    for record in records:
        for cited in record.carriers:
            path = root / cited.rsplit(":", 1)[0]
            if path.exists() and record.quote not in path.read_text(
                encoding="utf-8", errors="replace"
            ):
                drifted.append(cited)
    return tuple(drifted)
