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

V10: compute_pathology builds the per-cell pathology block from the
preserved transcripts (the artifact binder the run/summarize write paths
call), joining the transcript overlay scan for hidden tasks.
"""

import json
import stat
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.contamination import scan_transcript
from satyrn_evals.errors import OverlayError, SatyrnError, UsageError
from satyrn_evals.grade import grade
from satyrn_evals.manifest import (
    DEFAULT_TASKS_ROOT,
    TaskManifest,
    load_manifest,
    resolve_task,
)
from satyrn_evals.model_error import infrastructure_failure
from satyrn_evals.overlay import OverlaySpec, load_overlay
from satyrn_evals.pathology import count_transcript, decoded_scan_text
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


def _base_texts(task_dir: Path) -> list[str]:
    """UTF-8 text of the task's model-visible base files (visible windows).

    The overlay scan subtracts windows that also appear here: content the
    model saw legitimately is not evidence of having seen the overlay
    (V10 spec §3.8). Unreadable, non-UTF-8, and non-file entries
    contribute nothing.
    """
    texts: list[str] = []
    base = task_dir / "base"
    if not base.is_dir():
        return []
    for path in sorted(base.rglob("*")):
        if not (path.is_file() and not path.is_symlink()):
            continue
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return texts


_ABSENT = {"measured": False, "reason": "absent"}


def _read_transcript(path: Path) -> str | None:
    """The transcript text, or None when the file is not readable.

    V10 spec §4: a named transcript that is missing, not a regular file,
    or unreadable at summary time is per-cell ``absent`` — never a batch
    failure. Decoding uses errors="replace", so only a genuinely
    unreadable file maps to absent; garbage text is the parser's to call
    ``unparseable``.
    """
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _had_patch(path: Path | None) -> bool:
    """Whether the cell preserved a patch with content in it (V11d F2).

    Not ``patch_path is not None``: ``attempt_pi.py:230`` writes
    ``patch.diff`` unconditionally, so on every pi-adapter cell the name
    is always recorded and the file always exists -- which made
    ``tool_free_terminal_turns`` unable to fire on the refusals it was
    built to count. A patch is a patch when it has non-whitespace
    content. A recorded patch that cannot be read is absent evidence,
    not a finding, so it reports ``True`` and the gate stays silent
    (confirmed 2026-09-05).
    """
    if path is None:
        return False
    try:
        return bool(path.read_text(encoding="utf-8", errors="replace").strip())
    except OSError:
        return True


def compute_pathology(
    output: Path,
    cells: Sequence[AttemptCell],
    *,
    task_dir: Path,
    manifest: TaskManifest,
    overlay: OverlaySpec | None = None,
    visible_texts: list[str] | None = None,
) -> dict[str, dict]:
    """Per-cell pathology blocks over the preserved transcripts (V10 §4).

    A per-cell read problem is per-cell ``absent``, never a batch failure;
    only shared task-data problems (the overlay) raise. Hidden-oracle
    measured cells gain ``overlay_windows``: the transcript's *decoded*
    payload text (spec §3.8) is scanned for overlay windows with the base
    texts subtracted; visible-oracle cells never carry the key. Blocks
    appear in the cells' order.

    ``overlay``/``visible_texts`` preload the shared context (close-out
    correction 2026-09-05, spec §4): when a hidden caller already loaded
    them (``run`` validates before its first attempt), they are passed in
    and nothing shared is re-read here; when ``None`` they are loaded from
    the task as before (``summarize``'s path -- its run is already
    anchored, so a broken overlay there is operational and recoverable).
    """
    hidden = manifest.oracle_visibility == "hidden"
    if hidden:
        if overlay is None:
            overlay = load_overlay(task_dir, manifest)
        if visible_texts is None:
            visible_texts = _base_texts(task_dir)
    blocks: dict[str, dict] = {}
    for name, record, _ in cells:
        path = (
            None
            if record.transcript_path is None
            else output / name / record.transcript_path
        )
        if path is None:
            blocks[name] = _ABSENT
            continue
        text = _read_transcript(path)
        if text is None:
            blocks[name] = _ABSENT
            continue
        patch = (
            None
            if record.patch_path is None
            else output / name / record.patch_path
        )
        block = count_transcript(
            text, had_patch=_had_patch(patch)
        ).to_block()
        if hidden and block.get("measured") is True:
            # Hidden implies the overlay is present here -- loaded above or
            # pre-loaded by the caller (it raises on an unreadable
            # overlay), so the cast documents that invariant for the type
            # checker. The scan body is the decoded payload text (spec
            # §3.8): raw-line matching over the JSON-escaped stream alone
            # could not fire.
            scan_body = decoded_scan_text(text)
            block["overlay_windows"] = len(
                scan_transcript(
                    scan_body,
                    cast(OverlaySpec, overlay),
                    visible_texts=(
                        visible_texts if visible_texts is not None else []
                    ),
                )
            )
        blocks[name] = block
    return blocks


def pathology_context(
    task_dir: Path, manifest: TaskManifest
) -> tuple[OverlaySpec | None, list[str]]:
    """The shared pathology context for a run, loaded before its first attempt.

    V10 spec §4 (close-out correction 2026-09-05): ``run`` validates the
    shared pathology context up front so a broken overlay refuses the run
    pre-cell (nothing preserved, recoverable by repair + rerun) and no
    shared-context failure can strand completed cells post-loop. Visible
    tasks carry no overlay and no base-text subtraction.
    """
    if manifest.oracle_visibility != "hidden":
        return None, []
    return load_overlay(task_dir, manifest), _base_texts(task_dir)


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
    cells; an overlay that cannot load (V10 spec §4: shared task data,
    never a per-cell unmeasured). The rebuild carries the same per-cell
    pathology block run writes, recomputed from the preserved transcripts
    (V10 spec §4) — a pre-V10 summary gains the block on re-summarize.
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
        pathology = compute_pathology(
            output, cells, task_dir=task_dir, manifest=manifest
        )
        summary = compute_summary(
            cells,
            oracle_visibility=manifest.oracle_visibility,
            pathology=pathology,
        )
    except ValueError as exc:
        raise SatyrnError(f"summarize: {exc}") from exc
    except OverlayError as exc:
        # An overlay defect is shared task data, not a per-cell problem:
        # operational (3), naming summarize (V10 spec §4). OverlayError
        # alone would exit 2 (usage, the attempt-time reading); the
        # summary write paths must be exit 3.
        raise SatyrnError(f"summarize: overlay unavailable: {exc}") from exc
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
    # V11d slice 4: reclassify before the gradeable check. regrade
    # otherwise no-ops on every refusal cell, which would strand each
    # already-collected infrastructure failure at NO_PATCH with no offline
    # path to correct it -- exactly what BRIEF rule 3 promises against.
    # Scoped to NO_PATCH: that is the observed defect, and a cell that
    # produced a patch is not one the substrate silently swallowed.
    if (
        record.code in (AttemptCode.NO_PATCH, AttemptCode.MODEL_ERROR)
        and record.transcript_path is not None
        and (text := _read_transcript(attempt_dir / record.transcript_path))
        is not None
    ):
        # Re-*derive* rather than only promote. The transcript is the
        # authority, so when the classification rule changes a cell can be
        # re-scored in both directions -- the property that makes a
        # grading decision correctable without re-running a model
        # (BRIEF rule 3). A one-way promotion would strand every cell
        # reclassified under a rule later found wrong.
        fault = infrastructure_failure(text)
        derived = (
            AttemptCode.MODEL_ERROR if fault is not None else AttemptCode.NO_PATCH
        )
        if derived is not record.code:
            rewritten = replace(
                record,
                code=derived,
                message=(
                    f"attempt refused: MODEL_ERROR: {fault}"
                    if fault is not None
                    else "attempt refused: NO_PATCH"
                ),
            )
            write_attempt_record(record_path, rewritten)
            return rewritten
    if not _gradeable(record):
        return None  # nothing was graded, so nothing re-scores (no-op).
    # OK and GRADE_FAILED policies both require patch + transcript, so the
    # record's patch_path is guaranteed present here (a None is a logic
    # bug, not a runtime case).
    assert record.patch_path is not None
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
