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

from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.summary import (
    ABORTED_NAME,
    SUMMARY_NAME,
    AttemptCell,
    Summary,
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
) -> None:
    """Record an aborted batch; never under the name summary.json.

    The marker carries the requested count, the completed count, the
    error, and — over the completed cells — the same tally a summary
    would carry. A reader can tell a partial batch from a complete short
    run: summary.json exists only for the latter.
    """
    data: dict[str, object] = {
        "requested": requested,
        "completed": len(cells),
        "error": error,
    }
    if cells:
        payload = asdict(compute_summary(cells, oracle_visibility=oracle_visibility))
        if payload["contamination"] is None:
            del payload["contamination"]
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
) -> Summary:
    if n < 1:
        raise UsageError("run requires a positive --n")
    if not command:
        raise UsageError("run command is required: run TASK [flags] -- COMMAND...")
    manifest = load_manifest(resolve_task(task, tasks_root=tasks_root))
    cells: list[AttemptCell] = []
    try:
        for _ in range(n):
            record = attempt(
                task=task, tasks_root=tasks_root, output=output, command=command,
                timeout=timeout,
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
        _write_aborted(
            output,
            requested=n,
            cells=cells,
            error=f"{type(exc).__name__}: {exc}",
            oracle_visibility=manifest.oracle_visibility,
        )
        raise
    summary = compute_summary(cells, oracle_visibility=manifest.oracle_visibility)
    output.mkdir(parents=True, exist_ok=True)
    stale = output / ABORTED_NAME
    if stale.exists():
        stale.unlink()  # a completed run replaces any earlier abort marker
    write_summary(output / SUMMARY_NAME, summary)
    return summary
