"""The diagnostic-loop summary: counts over cells, with contamination.

A cell is (attempt directory name, record, parsed receipt dict or None).
Visible-task summaries carry cells + oracle_visibility but no contamination
section; hidden-task summaries additionally tally contamination outcomes
beside the verdict counts, with graded = flagged + clean + unmeasured.
"""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.contamination import CheckResult, overall
from satyrn_evals.verdict import Verdict

_ATTEMPT_CODES = frozenset(code.value for code in AttemptCode)
_VERDICTS = frozenset(verdict.value for verdict in Verdict)

type AttemptCell = tuple[str, AttemptRecord, dict | None]


@dataclass(frozen=True, slots=True)
class Summary:
    n: int
    attempted: int
    refused: int
    code_counts: dict[str, int]
    verdict_counts: dict[str, int]
    timeouts: int
    oracle_visibility: str
    cells: list[str]
    contamination: dict[str, int] | None

    def __post_init__(self) -> None:
        if self.n < 0 or self.attempted < 0 or self.refused < 0:
            raise ValueError("counts must be non-negative")
        if self.attempted + self.refused != self.n:
            raise ValueError("attempted + refused must equal n")
        if set(self.code_counts) != _ATTEMPT_CODES or set(self.verdict_counts) != _VERDICTS:
            raise ValueError("counts must hold one key per AttemptCode and per Verdict")
        if self.timeouts != self.code_counts[AttemptCode.COMMAND_TIMEOUT.value]:
            raise ValueError("timeouts must equal code_counts[COMMAND_TIMEOUT]")
        if self.contamination is not None:
            if set(self.contamination) != {"graded", "flagged", "clean", "unmeasured"}:
                raise ValueError(
                    "contamination must hold exactly graded/flagged/clean/unmeasured"
                )
            if (
                sum(self.contamination[k] for k in ("flagged", "clean", "unmeasured"))
                != self.contamination["graded"]
            ):
                raise ValueError("flagged + clean + unmeasured must equal graded")


def _cell_outcome(receipt: dict) -> str:
    """Per-cell contamination outcome from a parsed receipt dict.

    Callers pass only receipts of graded cells (the graded filter is
    `attempted and receipt is not None`), so `receipt` is never None here.
    A pre-V7 receipt — no `contamination` key — is `unmeasured`: grading
    ran, detection did not.
    """
    if (finding := receipt.get("contamination")) is None:
        return "unmeasured"
    results = [
        CheckResult(check["check"], check["outcome"], ())
        for check in finding["checks"]
    ]
    return overall(results)


def compute_summary(
    cells: Sequence[AttemptCell], *, oracle_visibility: str
) -> Summary:
    n = len(cells)
    attempted = sum(
        1 for _, record, _ in cells if record.outcome is AttemptOutcome.ATTEMPTED
    )
    code_counts = {code.value: 0 for code in AttemptCode}
    verdict_counts = {verdict.value: 0 for verdict in Verdict}
    for _, record, _ in cells:
        code_counts[record.code.value] += 1
        if record.verdict is not None:
            verdict_counts[record.verdict.value] += 1
    contamination: dict[str, int] | None = None
    if oracle_visibility == "hidden":
        graded = [
            receipt
            for _, record, receipt in cells
            if record.outcome is AttemptOutcome.ATTEMPTED and receipt is not None
        ]
        tally: dict[str, int] = {
            "graded": len(graded),
            "flagged": 0,
            "clean": 0,
            "unmeasured": 0,
        }
        for receipt in graded:
            tally[_cell_outcome(receipt)] += 1
        contamination = tally
    return Summary(
        n=n,
        attempted=attempted,
        refused=n - attempted,
        code_counts=code_counts,
        verdict_counts=verdict_counts,
        timeouts=code_counts[AttemptCode.COMMAND_TIMEOUT.value],
        oracle_visibility=oracle_visibility,
        cells=[name for name, _, _ in cells],
        contamination=contamination,
    )


def write_summary(path: Path, summary: Summary) -> None:
    data = asdict(summary)
    if summary.contamination is None:
        del data["contamination"]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
