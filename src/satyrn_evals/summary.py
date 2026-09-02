"""The diagnostic-loop summary: counts only, computed from attempt records."""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.verdict import Verdict

_ATTEMPT_CODES = frozenset(code.value for code in AttemptCode)
_VERDICTS = frozenset(verdict.value for verdict in Verdict)


@dataclass(frozen=True, slots=True)
class Summary:
    n: int
    attempted: int
    refused: int
    code_counts: dict[str, int]
    verdict_counts: dict[str, int]
    timeouts: int

    def __post_init__(self) -> None:
        if self.n < 0 or self.attempted < 0 or self.refused < 0:
            raise ValueError("counts must be non-negative")
        if self.attempted + self.refused != self.n:
            raise ValueError("attempted + refused must equal n")
        if set(self.code_counts) != _ATTEMPT_CODES or set(self.verdict_counts) != _VERDICTS:
            raise ValueError("counts must hold one key per AttemptCode and per Verdict")
        if self.timeouts != self.code_counts[AttemptCode.COMMAND_TIMEOUT.value]:
            raise ValueError("timeouts must equal code_counts[COMMAND_TIMEOUT]")


def compute_summary(records: Sequence[AttemptRecord]) -> Summary:
    n = len(records)
    attempted = sum(1 for record in records if record.outcome is AttemptOutcome.ATTEMPTED)
    code_counts = {code.value: 0 for code in AttemptCode}
    verdict_counts = {verdict.value: 0 for verdict in Verdict}
    for record in records:
        code_counts[record.code.value] += 1
        if record.verdict is not None:
            verdict_counts[record.verdict.value] += 1
    return Summary(
        n=n,
        attempted=attempted,
        refused=n - attempted,
        code_counts=code_counts,
        verdict_counts=verdict_counts,
        timeouts=code_counts[AttemptCode.COMMAND_TIMEOUT.value],
    )


def write_summary(path: Path, summary: Summary) -> None:
    path.write_text(json.dumps(asdict(summary), indent=2) + "\n", encoding="utf-8")
