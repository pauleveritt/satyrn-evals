"""Offline re-scoring from preserved artifacts (rule 3, executable).

summarize_output rebuilds a run's summary.json from the attempt records on
disk through the same compute_summary/write_summary path run() uses, so a
rebuilt summary is byte-identical to the run's own. The rebuild is anchored
on the cell names the run's summary.json records — never a directory scan —
so a stray sibling or an un-appended crash cell cannot change the rebuilt
artifact, and a directory whose run aborted is refused (an aborted run
writes aborted.json, never summary.json). regrade_attempt re-runs the
grader over a preserved patch and rewrites receipt + record. Pure file
I/O up to the grade call: default-tier testable without argparse.
"""

import json
from dataclasses import replace
from pathlib import Path

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.errors import SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest, resolve_task
from satyrn_evals.summary import (
    ABORTED_NAME,
    SUMMARY_NAME,
    AttemptCell,
    Summary,
    compute_summary,
    write_summary,
)
from satyrn_evals.verdict import Verdict


def _root(tasks_root: Path | None) -> Path:
    return tasks_root if tasks_root is not None else DEFAULT_TASKS_ROOT


def _read_anchor(output: Path) -> list[str]:
    """The cell names a completed run's summary.json records (B2).

    An aborted run has no summary.json by contract (it wrote aborted.json
    instead), so its directory is refused rather than re-summarized: the
    anchored set is authoritative and strays never change the rebuild.
    """
    anchor_path = output / SUMMARY_NAME
    aborted_path = output / ABORTED_NAME
    if aborted_path.exists() and not anchor_path.exists():
        try:
            marker = json.loads(aborted_path.read_text(encoding="utf-8"))
            requested = marker.get("requested", "?")
            completed = marker.get("completed", "?")
        except (OSError, json.JSONDecodeError):
            requested = completed = "?"
        raise SatyrnError(
            f"summarize: the batch in {output} aborted after {completed} of "
            f"{requested} cells (see {ABORTED_NAME}); a completed run is "
            "required before summarizing"
        )
    if not anchor_path.is_file():
        raise UsageError(
            f"summarize: not a run output directory: no {SUMMARY_NAME} "
            f"under {output}"
        )
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SatyrnError(
            f"summarize: cannot read {SUMMARY_NAME}: {exc}"
        ) from exc
    cells = anchor.get("cells")
    if not isinstance(cells, list) or not all(
        isinstance(name, str) for name in cells
    ):
        raise SatyrnError(f"summarize: {SUMMARY_NAME} has no usable cells list")
    if not cells:
        raise SatyrnError(f"summarize: {SUMMARY_NAME} names no cells")
    return cells


def _load_cell(cell_dir: Path) -> AttemptCell:
    """Load one cell into the summary cell shape (name, record, receipt).

    An identity mismatch (the record names a different directory) is usage;
    an unreadable record or receipt is operational. The name is the
    directory name -- the same string run() records as the cell identity,
    so a rebuilt summary is byte-identical to the run's own.
    """
    name = cell_dir.name
    try:
        record = load_attempt_record(cell_dir / "attempt.json")
    except ValueError as exc:
        raise SatyrnError(f"cannot read {name}: {exc}") from exc
    if record.attempt_dir is not None and record.attempt_dir != name:
        raise UsageError(
            f"record in {name} names {record.attempt_dir!r} "
            "(moved or renamed cell)"
        )
    receipt: dict | None = None
    if record.receipt_path is not None:
        receipt_path = cell_dir / record.receipt_path
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SatyrnError(f"cannot read receipt for {name}: {exc}") from exc
    return name, record, receipt


def summarize_output(
    output: Path, *, tasks_root: Path | None = None
) -> Summary:
    """Rebuild OUTPUT_DIR/summary.json over the run's own recorded cells.

    The rebuild is anchored on the cells the run's summary.json names (B2):
    strays and un-appended crash cells never change it, and a directory
    whose run aborted is refused (B1: an aborted run writes aborted.json,
    never summary.json).

    Usage (2): missing dir / not a run output directory / unknown task /
    moved cell. Operational (3): aborted batch, unreadable anchor, record,
    or receipt; a named cell missing from disk; mixed or inconsistent
    cells.
    """
    output = Path(output)
    if not output.is_dir():
        raise UsageError(f"summarize: not a directory: {output}")
    names = _read_anchor(output)
    cells: list[AttemptCell] = []
    for name in names:
        cell_dir = output / name
        if not (cell_dir / "attempt.json").is_file():
            raise SatyrnError(
                f"summarize: cell {name} named by {SUMMARY_NAME} is missing "
                "its attempt record"
            )
        cells.append(_load_cell(cell_dir))
    root = _root(tasks_root)
    task_dir = resolve_task(cells[0][1].task, tasks_root=root)
    manifest = load_manifest(task_dir)
    try:
        summary = compute_summary(
            cells, oracle_visibility=manifest.oracle_visibility
        )
    except ValueError as exc:
        raise SatyrnError(f"summarize: {exc}") from exc
    write_summary(output / SUMMARY_NAME, summary)
    return summary


def _gradeable(record: AttemptRecord) -> bool:
    """A patch was admitted to grading: OK (re-score) or GRADE_FAILED."""
    return record.code in (AttemptCode.OK, AttemptCode.GRADE_FAILED)


def regrade_attempt(
    attempt_dir: Path, *, tasks_root: Path | None = None
) -> AttemptRecord | None:
    """Re-grade a preserved patch; rewrite receipt + record in place.

    Returns the rewritten record on PASS/FAIL; ``None`` for a no-op (a
    refusal-code cell was never graded, so nothing re-scores). Usage (2):
    no attempt.json or an identity mismatch. Operational (3): unreadable
    record or UNAVAILABLE verdict.
    """
    attempt_dir = Path(attempt_dir)
    record_path = attempt_dir / "attempt.json"
    if not record_path.is_file():
        raise UsageError(f"regrade: no attempt record under {attempt_dir}")
    try:
        record = load_attempt_record(record_path)
    except ValueError as exc:
        raise SatyrnError(f"regrade: {exc}") from exc
    if record.attempt_dir is not None and record.attempt_dir != attempt_dir.name:
        raise UsageError(
            f"regrade: record names {record.attempt_dir!r}, "
            f"not {attempt_dir.name!r}"
        )
    if not _gradeable(record):
        return None  # nothing was graded, so nothing re-scores (no-op).
    # OK and GRADE_FAILED policies both require patch + transcript, so the
    # record's patch_path is guaranteed present here.
    root = _root(tasks_root)
    task_dir = resolve_task(record.task, tasks_root=root)
    receipt = grade(
        task_dir, attempt_dir / record.patch_path, attempt_dir / "receipt.json"
    )
    rewritten = replace(
        record,
        code=AttemptCode.OK,
        verdict=receipt.verdict,
        receipt_path="receipt.json",
        message="attempt re-graded",
    )
    write_attempt_record(record_path, rewritten)
    if receipt.verdict is Verdict.UNAVAILABLE:
        raise SatyrnError(
            f"regrade: verdict unavailable for {attempt_dir.name}: "
            f"{receipt.reason}"
        )
    return rewritten
