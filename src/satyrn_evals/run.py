"""Run the attempt seam n times and write a counts-only summary."""

from pathlib import Path

from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt
from satyrn_evals.errors import UsageError
from satyrn_evals.summary import Summary, compute_summary, write_summary


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
    records = [
        attempt(
            task=task, tasks_root=tasks_root, output=output, command=command, timeout=timeout
        )
        for _ in range(n)
    ]
    summary = compute_summary(records)
    output.mkdir(parents=True, exist_ok=True)
    write_summary(output / "summary.json", summary)
    return summary
