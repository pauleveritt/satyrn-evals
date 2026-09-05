# Trust boundaries and limits

Evals is designed to make a result trustworthy enough to diagnose an engine,
not to promise more than it can establish.

## A receipt is evidence; a process status is not

The task oracle writes a hook result at a reserved path. Grading validates that
result, including the exact test IDs that executed, before it computes the
receipt verdict. This prevents a successful process exit from standing in for
a test result when, for example, tests only collected or the process exited
before running them.

The receipt records both the verdict and the evidence behind it. A missing or
inconsistent hook result becomes `unavailable`, not a pass.

## A result file is checked for shape, not for authorship

The oracle result path is reserved by grading, unlinked before the run, and
validated for shape, internal consistency, and freshness against the run's
start. What the loader cannot check is *who wrote it*: the path is in the
oracle's environment, and code the oracle imports at collection time runs in
the same process. Model code could write a shape-valid result and exit
without running the tests. Evals does not claim to bind a result to its
producer; the verdict never comes from stdout or an exit code, and the
result file is not signed. This is a limit of the seam, stated here and in
the brief.

## Preserving first makes re-grading possible

The patch and transcript are persisted before the attempt workspace is cleaned
up. If grading needs repair, the preserved patch can be re-scored without
rerunning the engine. A refusal identifies incomplete delivered artifacts;
`unavailable` identifies a patch that was delivered but could not be graded.

## A disposable worktree is not a sandbox

Evals reconstructs a private Git workspace and removes it after an attempt.
That protects the task base and creates a repeatable working context. The
attempt command is still trusted code running with the user's permissions. Do
not use Evals as containment for an untrusted executable.

## Diagnostic counts are not statistical claims

Evals records counts and failure reasons so a developer can decide what to
inspect or improve. It deliberately defers confidence intervals, A/B
publication, and other claims-layer machinery until a real consumer needs it.
It also does not compare wall-clock times between adjacent runs.

See [the architecture](../architecture.md) for the concrete implementation
and [the glossary](../glossary.md) for the exact terms.
