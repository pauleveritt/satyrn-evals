# Run a diagnostic batch

Use this guide after a deterministic reproducer establishes the specific
software question. `run` repeats one attempt command, preserves every attempt,
and writes a counts-only summary. Target useful development feedback in
10–15 minutes: begin with one bounded attempt, then use two attempts for each
matched configuration on one relevant qualified task only when the question is
whether a change is promising enough to investigate.

Declare the budget and stopping rule before a live run. An established
infrastructure failure (for example, a wrong model, unavailable executable,
invalid task setup, or broken artifact path) stops the remaining launches;
retain the partial batch. An ordinary failed repair remains a counted
observation, not a reason for an improvised retry. Small runs are triage, not
success-rate, headroom, or causal conclusions. A broader confirmation needs a
separate plan and a fresh run.

## Run the batch

Run from your Evals checkout; add `--tasks-root tasks` for a captured task.

```console
$ uv run satyrn-evals run TASK_NAME --n 1 --output runs/engine -- \
    /absolute/path/to/attempt-command ARGUMENTS
```

Always state `--n` explicitly: the example asks whether one complete path
works. For a matched two-configuration triage screen, use `--n 2` for each
configuration after checking representative retained attempts show the relevant
behavior within the selected command budget. A two-minute command budget and a
fifteen-minute command budget answer different questions; keep their results
separate. Do not use a repeated-call limit when recovery from repetition is the
question.

The command completes the declared attempts, including refusals, and writes
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
confidence interval or an A/B publication claim. Before using it to evaluate
an engine change, qualify the task's requirements and checks, freeze the
condition, and state the comparison the result can support. `run` does not
perform those decisions.

Use retained requests, patches, and transcripts from expensive failures to add
the cheapest deterministic regression test that covers the reproducible
component. That test can show the component now handles the saved evidence; a
subsequent bounded live attempt is needed to learn whether a model chooses a
better sequence. Measure setup, command, and grading durations before proposing
cache reuse, model reuse, or concurrency changes. A whole-attempt deadline is
not yet implemented: it needs a separate design that bounds setup, command,
preservation, grading, and cleanup without losing evidence.

`local-pings` remains useful for grading, smoke, and regression use. Its past
diagnostic interpretation is historical evidence, not a current selection
rule.

For the full `run` interface, see the [`run` reference](../usage.md#run);
`summary.json`'s fields are documented in [task and artifact
formats](../reference/formats.md#run-summary). For the distinction between a
valid task and a diagnostic workload, see
[the explanatory topic](../topics/tasks-and-diagnostic-workloads.md).
