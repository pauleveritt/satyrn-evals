"""Run the attempt seam n times and write a counts-only summary.

Each attempt() writes its own <task>-<stamp> directory under ``output`` and
records the directory's name in the attempt record; run names cells from
that recorded identity, never from a directory listing, so a sibling entry
in the output directory cannot corrupt cell provenance. A hidden oracle
produces a contamination tally beside the verdict counts; a visible oracle
omits it.
"""

import json
from pathlib import Path

from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt
from satyrn_evals.errors import UsageError
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.summary import AttemptCell, Summary, compute_summary, write_summary


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
    summary = compute_summary(cells, oracle_visibility=manifest.oracle_visibility)
    output.mkdir(parents=True, exist_ok=True)
    write_summary(output / "summary.json", summary)
    return summary
