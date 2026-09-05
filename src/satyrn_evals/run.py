"""Run the attempt seam n times and write a counts-only summary.

Each attempt() writes its own <task>-<stamp> directory under ``output`` and
records the directory's name in the attempt record; run names cells from
that recorded identity, never from a directory listing, so a sibling entry
in the output directory cannot corrupt cell provenance. A hidden oracle
produces a contamination tally beside the verdict counts; a visible oracle
omits it.

Completion contract: ``summary.json`` is written only when all n attempts
complete. If the loop aborts — an exception or Ctrl-C after at least one
cell — run writes ``aborted.json`` (requested/completed/error plus the
tallies over the completed cells) and re-raises, so a partial batch is
never mistaken for a completed short run.
"""

import json
from dataclasses import asdict
from pathlib import Path

from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt, resolve_contract
from satyrn_evals.errors import OverlayError, SatyrnError, UsageError
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.rescore import compute_pathology, pathology_context
from satyrn_evals.summary import (
    ABORTED_NAME,
    SUMMARY_NAME,
    AttemptCell,
    Summary,
    absent_pathology,
    compute_summary,
    write_summary,
)


def _write_aborted(
    output: Path,
    *,
    requested: int,
    cells: list[AttemptCell],
    error: str,
    oracle_visibility: str,
    pathology: dict[str, dict] | None = None,
) -> None:
    """Record an aborted batch; never under the name summary.json.

    The marker carries the requested count, the completed count, the
    error, and — over the completed cells — the same tally a summary
    would carry, including the pathology block when the binder supplied
    it. When the binder failed (pathology is None) the block is omitted
    and the caller's ``error`` already names the binder failure, so the
    marker never fabricates blocks and never hides the primary exception
    (V10 spec §4).
    """
    data: dict[str, object] = {
        "requested": requested,
        "completed": len(cells),
        "error": error,
    }
    if cells:
        # compute_summary requires a block per cell; when the binder
        # failed, absent blocks are only a construction scaffold and the
        # pathology key is dropped from the wire payload below.
        blocks = pathology if pathology is not None else absent_pathology(cells)
        payload = asdict(compute_summary(
            cells, oracle_visibility=oracle_visibility, pathology=blocks,
        ))
        if payload["contamination"] is None:
            payload.pop("contamination")
        if pathology is None:
            payload.pop("pathology")  # binder failed: error names it
        data.update(payload)
    output.mkdir(parents=True, exist_ok=True)
    (output / ABORTED_NAME).write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )


def run(
    *,
    task: str,
    tasks_root: Path,
    output: Path,
    command: list[str],
    n: int,
    timeout: float = DEFAULT_TIMEOUT,
    rung: str | None = None,
) -> Summary:
    if n < 1:
        raise UsageError("run requires a positive --n")
    if not command:
        raise UsageError("run command is required: run TASK [flags] -- COMMAND...")
    task_dir = resolve_task(task, tasks_root=tasks_root)
    manifest = load_manifest(task_dir)
    # An unknown rung must cost no cells: resolve it here, before the first
    # attempt, so the refusal preserves nothing and is fixed by re-running.
    resolve_contract(manifest, rung)
    # Shared pathology context is validated BEFORE the first attempt
    # (V10 spec §4, close-out correction 2026-09-05): a broken overlay
    # refuses the run pre-cell (exit 3, nothing preserved, recoverable by
    # repair + rerun), and the binder runs on this pre-loaded context so
    # no shared-context failure can strand completed cells post-loop
    # (per-cell reads map to absent and never raise). summarize_output
    # keeps loading the overlay itself -- its run is already anchored.
    try:
        overlay, visible_texts = pathology_context(task_dir, manifest)
    except OverlayError as exc:
        raise SatyrnError(f"run: overlay unavailable: {exc}") from exc
    cells: list[AttemptCell] = []
    try:
        for _ in range(n):
            record = attempt(
                task=task, tasks_root=tasks_root, output=output, command=command,
                timeout=timeout, rung=rung,
            )
            if record.attempt_dir is None:
                raise RuntimeError("attempt record does not name its attempt directory")
            receipt: dict | None = None
            if record.receipt_path is not None:
                receipt_path = output / record.attempt_dir / record.receipt_path
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            cells.append((record.attempt_dir, record, receipt))
    except BaseException as exc:
        # never lose the tally over completed cells (T1) — but never as a
        # file named summary.json: an aborted batch must not look complete.
        # The pathology binder runs best-effort: a binder failure must not
        # mask the primary abort exception, so it is folded into the
        # marker's error and the block is omitted (V10 spec §4).
        pathology: dict[str, dict] | None = None
        binder_error: str | None = None
        if cells:
            try:
                pathology = compute_pathology(
                    output, cells, task_dir=task_dir, manifest=manifest,
                    overlay=overlay, visible_texts=visible_texts,
                )
            except BaseException as bind_exc:  # never mask the abort
                binder_error = (
                    f"pathology unavailable: "
                    f"{type(bind_exc).__name__}: {bind_exc}"
                )
        _write_aborted(
            output,
            requested=n,
            cells=cells,
            error=(
                f"{type(exc).__name__}: {exc}"
                + (f"; {binder_error}" if binder_error is not None else "")
            ),
            oracle_visibility=manifest.oracle_visibility,
            pathology=pathology,
        )
        raise
    pathology = compute_pathology(
        output, cells, task_dir=task_dir, manifest=manifest,
        overlay=overlay, visible_texts=visible_texts,
    )
    summary = compute_summary(
        cells,
        oracle_visibility=manifest.oracle_visibility,
        pathology=pathology,
    )
    output.mkdir(parents=True, exist_ok=True)
    stale = output / ABORTED_NAME
    if stale.exists():
        stale.unlink()  # a completed run replaces any earlier abort marker
    write_summary(output / SUMMARY_NAME, summary)
    return summary
