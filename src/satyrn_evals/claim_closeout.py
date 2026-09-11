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

#: The artifact each `not_derivable` record names as missing. V3's rule is
#: that a `not_derivable` status without a named artifact is a close-out
#: failure, so this map is the record of what each refusal is waiting on.
MISSING_ARTIFACT: dict[str, str] = {
    "c-completion-6-of-18": "hidden-grader verdicts across all 18 Engine attempts",
    "c-completion-4-of-16": "hidden-grader verdicts for the 16 pre-screen attempts",
    "c-baseline-3-of-3": "matched-repeat Baseline attempts under the final prompt",
    "c-contemporaneous-screen-tie-2-of-2": "an outcome measure executable from transcripts",
    "c-nonrestore-0-of-6": "a completion verdict per non-restoring attempt",
    "c-restore-4-of-7": "a completion verdict per restoring attempt",
    "c-redirect-fixed-1-of-9": "a redirect-trap resolution classifier",
    "c-redirect-6-of-9": "a redirect-trap occurrence classifier",
    "c-phase4-denominator-6-of-10": "prompt-state membership for the pre-phase-4 chains",
    "c-engine-population": "a measure that binds the population statement to an attempt set",
}


@dataclass(frozen=True, slots=True)
class CloseoutRow:
    claim_id: str
    level: ClaimLevel
    status: FinalStatus
    source: str
    carriers: tuple[str, ...]
    missing: str | None


def _record_missing(record: ClaimRecord) -> str | None:
    if record.status != "not_derivable":
        return None
    return MISSING_ARTIFACT.get(record.id)


def closeout_rows(
    records: Sequence[ClaimRecord] = INVENTORY,
) -> tuple[CloseoutRow, ...]:
    return tuple(
        CloseoutRow(
            claim_id=record.id,
            level=record.level,
            status=cast(FinalStatus, record.status),
            source=record.source,
            carriers=record.carriers,
            missing=_record_missing(record),
        )
        for record in records
    )


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
