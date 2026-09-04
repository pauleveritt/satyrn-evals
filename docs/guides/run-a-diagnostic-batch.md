# Run a diagnostic batch

Use this guide when one attempt is not enough to reveal a failure pattern.
`run` repeats the same attempt command, preserves every attempt, and writes a
counts-only summary.

Before a budgeted diagnostic run on a materially distinct command, adapter, or
runtime path, perform one uncounted real-model smoke attempt and read its
attempt record. This confirms that the path starts the model and produces the
artifacts you expect.

## Run the batch

```console
$ satyrn-evals run TASK_NAME --n 8 --output runs/engine -- \
    /absolute/path/to/attempt-command ARGUMENTS
```

The command completes all eight attempts, including refusals, and writes
`runs/engine/summary.json`. Read its `attempted`, `refused`, `code_counts`,
`verdict_counts`, and `timeouts` fields. Individual attempt directories remain
available for inspection.

## Interpret it as diagnosis

The summary tells you what outcomes occurred and how often. It is not a
confidence interval or an A/B publication claim. Use a task only as a
diagnostic workload when it has recorded headroom under the admission rule;
`run` does not enforce admission.

The bundled `local-pings` task is retained for grading, smoke, and regression
use, but was de-admitted as a diagnostic workload. Do not use it as evidence
that an engine change helped without a newly qualifying probe.

For the full `run` interface, see the [`run` reference](../usage.md#run). For
the distinction between a valid task and a diagnostic workload, see
[the explanatory topic](../topics/tasks-and-diagnostic-workloads.md).
