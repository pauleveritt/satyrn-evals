"""Run the attempt seam n times and write a counts-only summary.

Each attempt() call creates exactly one new <task>-<stamp> directory under
``output``; run names cells by that directory delta and reads the receipt
the grader wrote inside it. A hidden oracle produces a contamination tally
beside the verdict counts; a visible oracle omits it.
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
        before = {p.name for p in output.iterdir()} if output.is_dir() else set()
        record = attempt(
            task=task, tasks_root=tasks_root, output=output, command=command,
            timeout=timeout,
        )
        after = {p.name for p in output.iterdir()} if output.is_dir() else set()
        if not (new := after - before):
            raise RuntimeError("attempt created no attempt directory")
        (cell_name,) = new  # exactly one directory per attempt call
        receipt: dict | None = None
        if record.receipt_path is not None:
            receipt_path = output / cell_name / record.receipt_path
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        cells.append((cell_name, record, receipt))
    summary = compute_summary(cells, oracle_visibility=manifest.oracle_visibility)
    output.mkdir(parents=True, exist_ok=True)
    write_summary(output / "summary.json", summary)
    return summary
