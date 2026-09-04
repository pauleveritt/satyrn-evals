# Valid tasks and diagnostic workloads

Evals has two different jobs, and each needs a different kind of task.

## A grader fixture proves the grader

A grader fixture is a bundled task with known-good and known-broken patches. It
proves that offline grading can accept a correct change and reject an incorrect
one. It needs no model run or headroom. `format_number` is the small fixture
used in the [first tutorial](../tutorials/see-one-verdict.md).

## A captured task is valid when it is un-done and winnable

Capture derives the tests that fail at the base and pass with the fix. Its
checks establish that the source is eligible, the base oracle runs, the task is
un-done, and the known-good fix passes. This makes the task valid for grading;
it does not tell us whether an engine change can move its outcomes.

## A diagnostic workload needs headroom

A diagnostic workload is a task used to learn whether an engine change helped.
It needs a baseline probe whose compared arms occupy different outcome bands.
That separation prevents a reliable grader fixture from being mistaken for a
useful measure of an engine change.

`local-pings` illustrates the distinction. It remains a valid bundled
grader/smoke/regression fixture, but its captured-task re-probe put both
compared arms in the middle band. It was therefore de-admitted as a diagnostic
workload. The full decision and evidence remain in the development record.

Use the [diagnostic-batch guide](../guides/run-a-diagnostic-batch.md) for the
operational workflow, and the [glossary](../glossary.md) for admission, bands,
and baseline probes.
