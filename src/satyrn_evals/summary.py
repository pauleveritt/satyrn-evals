"""The diagnostic-loop summary: counts over cells, with contamination.

A cell is (attempt directory name, record, parsed receipt dict or None).
Visible-task summaries carry cells + oracle_visibility but no contamination
section; hidden-task summaries additionally tally contamination outcomes
beside the verdict counts, with graded = flagged + clean + unmeasured.
Every summary carries a pathology block: one entry per cell (measured
counts, or measured:false with a reason), keyed in the summary's cell
order (V10 spec §4).
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

# Artifact names. summary.json is written ONLY by a completed run; an
# aborted run (exception or Ctrl-C after at least one cell) writes
# aborted.json instead, so a partial batch is never mistaken for a
# complete short run.
SUMMARY_NAME = "summary.json"
ABORTED_NAME = "aborted.json"

type AttemptCell = tuple[str, AttemptRecord, dict | None]


@dataclass(frozen=True, slots=True)
class Summary:
    n: int
    attempted: int
    refused: int
    code_counts: dict[str, int]
    verdict_counts: dict[str, int]
    timeouts: int
    task: str
    command: list[str]
    timeout: float
    oracle_visibility: str
    cells: list[str]
    contamination: dict[str, int] | None
    pathology: dict[str, dict]
    # V11a rung provenance. Both are null for a pre-V11a batch, whose cells
    # carry no rung identity; a new batch always carries a digest, and the
    # rung is null only when the default `contract` was exported (spec §5).
    rung: str | None = None
    contract_digest: str | None = None

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
        _validate_pathology(self.pathology, set(self.cells))


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


def _validate_pathology(pathology: dict[str, dict], cell_names: set[str]) -> None:
    """Raise ValueError unless pathology names exactly the cells.

    The wire block always carries one entry per cell (V10 spec §4): the
    keys must equal the cell names and every value must be a block
    carrying a boolean ``measured``. Shared by ``Summary.__post_init__``
    and ``compute_summary`` so both constructors enforce the same rule.
    """
    if set(pathology) != cell_names:
        missing = sorted(cell_names - set(pathology))
        extra = sorted(set(pathology) - cell_names)
        raise ValueError(
            f"pathology must name exactly the cells (missing: {missing}, extra: {extra})"
        )
    if any(
        not isinstance(block, dict) or not isinstance(block.get("measured"), bool)
        for block in pathology.values()
    ):
        raise ValueError("each pathology block must carry a boolean measured")


def absent_pathology(cells: Sequence[AttemptCell]) -> dict[str, dict]:
    """One unmeasured block per cell, keyed in cell order.

    The pure tally never reads transcripts; a tally-level caller that has
    not read them names every cell ``absent`` (V10 spec §4: per-cell
    unmeasured is a reporting state, never an error). The V10 binder
    (rescore.compute_pathology, P3a Task 2) replaces this with real
    measured/unmeasured blocks on the run/summarize write paths.
    """
    return {
        name: {"measured": False, "reason": "absent"}
        for name, _, _ in cells
    }


def compute_summary(
    cells: Sequence[AttemptCell],
    *,
    oracle_visibility: str,
    pathology: dict[str, dict],
) -> Summary:
    if not cells:
        raise ValueError("compute_summary requires at least one cell")
    task = cells[0][1].task
    command = cells[0][1].command
    timeout = cells[0][1].timeout
    if timeout is None:
        raise ValueError(
            f"cell {cells[0][0]} has no recorded timeout "
            "(pre-V9 record); cannot summarize"
        )
    rung = cells[0][1].rung
    digest = cells[0][1].contract_digest
    for name, record, _ in cells[1:]:
        if record.task != task:
            raise ValueError(f"mixed tasks in cells ({task!r} vs {record.task!r} at {name})")
        if record.command != command:
            raise ValueError(f"mixed commands in cells ({name})")
        if record.timeout is None:
            raise ValueError(f"cell {name} has no recorded timeout")
        if record.timeout != timeout:
            raise ValueError(f"mixed timeouts in cells ({name})")
        if record.rung != rung:
            raise ValueError(f"mixed rungs in cells ({name})")
        if record.contract_digest != digest:
            raise ValueError(f"mixed contract digests in cells ({name})")
    _validate_pathology(pathology, {name for name, _, _ in cells})
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
        task=task,
        command=list(command),
        timeout=timeout,
        oracle_visibility=oracle_visibility,
        cells=[name for name, _, _ in cells],
        contamination=contamination,
        # the field keys must follow the summary's cell order (spec §4)
        pathology={name: pathology[name] for name, _, _ in cells},
        rung=rung,
        contract_digest=digest,
    )


def write_summary(path: Path, summary: Summary) -> None:
    data = asdict(summary)
    if summary.contamination is None:
        data.pop("contamination")
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
