# Run a diagnostic batch

Use this guide when one attempt is not enough to reveal a failure pattern.
`run` repeats the same attempt command, preserves every attempt, and writes a
counts-only summary.

Before a budgeted diagnostic run on a materially distinct command, adapter, or
runtime path, perform one uncounted real-model smoke attempt and read its
attempt record — and the receipt, when grading ran. The smoke confirms that
the path starts the model. `NO_PATCH` and `COMMAND_TIMEOUT` may still pass the
smoke, but only on positive evidence the model started; a silent path is a
failed smoke.

## Run the batch

Run from your Evals checkout; add `--tasks-root tasks` for a captured task.

```console
$ uv run satyrn-evals run TASK_NAME --n 8 --output runs/engine -- \
    /absolute/path/to/attempt-command ARGUMENTS
```

The command completes all eight attempts, including refusals, and writes
`runs/engine/summary.json`. Read its `attempted`, `refused`, `code_counts`,
`verdict_counts`, and `timeouts` fields. Individual attempt directories remain
available for inspection.

## Re-score without re-running

If a grader defect is found after a run, fix the grader and re-score the
preserved patches — no model re-run:

```console
$ satyrn-evals regrade runs/engine/agentclinic-repair-plausible-wrong-fix-20260904-160143
$ satyrn-evals summarize runs/engine
```

`regrade` re-runs the grader over the preserved patch and rewrites the
attempt's receipt and record; `summarize` rebuilds `summary.json` from the
records on disk. A cell whose grading failed mid-run is recorded with code
`GRADE_FAILED` and is exactly what `regrade` is for.

## Interpret it as diagnosis

The summary tells you what outcomes occurred and how often. It is not a
confidence interval or an A/B publication claim. Use a task only as a
diagnostic workload when it has recorded headroom under the admission rule;
`run` does not enforce admission.

The bundled `local-pings` task is retained for grading, smoke, and regression
use, but was de-admitted as a diagnostic workload. Do not use it as evidence
that an engine change helped without a newly qualifying probe.

For the full `run` interface, see the [`run` reference](../usage.md#run);
`summary.json`'s fields are documented in [task and artifact
formats](../reference/formats.md#run-summary). For the distinction between a
valid task and a diagnostic workload, see
[the explanatory topic](../topics/tasks-and-diagnostic-workloads.md).
