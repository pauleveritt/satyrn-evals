# Whole-attempt deadline: preserve evidence while bounding live work

## Decision

Add an explicit, opt-in whole-attempt deadline for future live development
runs. It is a different limit from the existing command timeout: one monotonic
budget spans attempt setup, the executor command, artifact preservation,
grading, and cleanup. No default changes merely because this facility exists;
a budgeted run names both limits deliberately.

The deadline begins after no-write argument, task, and rung validation, but
before the attempt directory and generated engine contract are created. It
ends when the normal attempt lifecycle settles. The implementation checks the
budget between local operations and passes its remaining time to every
Evals-owned subprocess. The command timeout and the whole deadline race; the
first observed expiry wins. If both are already expired at one observation
point, record the whole deadline as the controlling limit because it bounds
the complete lifecycle.

Expiry stops new productive work, not safe finalization. The only permitted
post-expiry operations are: terminate and reap an already-started command
group; read already-written artifacts; atomically write the attempt record or
receipt; and retain instead of deleting a workspace. No new executor, oracle,
environment-sync, freeze-attestation, or cleanup subprocess may start. The
implementation replaces the current multiple-grace teardown waits with one
shared monotonic finalization cutoff of `DEFAULT_TEARDOWN_GRACE`, measured when
termination begins; every signal, reap, and group-disappearance poll consumes
that one allowance.

Finalization can exceed the advertised deadline by that one teardown allowance
and by necessary local final record I/O; local filesystem I/O is not promised
to have a wall-time bound. The finalizer tries to hash a retained artifact, but
if it cannot obtain a digest it records the retained path with a missing digest
and explicit missingness rather than discarding the artifact or blocking
indefinitely. The record reports the phase and observed elapsed time so that
overrun is visible. The deadline never claims to preempt a currently executing
filesystem call.

## Durable outcome

Persist the configured whole-attempt seconds as `attempt_timeout` on every
bounded attempt record. On expiry, add a `deadline` block with its matching
configured seconds, first-expired phase (`setup`, `command`, `preservation`,
`grading`, or `cleanup`), observed elapsed seconds, and whether finalization
retained a workspace. This provenance is separate from the execution code and
the hook-derived verdict. It survives offline regrading unchanged.

Before the pre-grade record exists, expiry writes a new
`DEADLINE_EXCEEDED` refusal record, with the recorded phase and every
already-written patch/transcript and any available digest. It starts no grade.
During grading, the durable `GRADE_FAILED` pre-grade record remains the
execution outcome; it gains deadline provenance and stays eligible for offline
regrading. If expiry is observed after `grade()` atomically writes a receipt
but before its matching record is rewritten, finalization reads that receipt
and writes the matching `OK` record with the receipt's hook-derived `pass`,
`fail`, or `unavailable` verdict and deadline provenance. It never leaves a
receipt beside an ambiguous `GRADE_FAILED` record. A receipt and matching `OK`
record durable before expiry retain their grading outcome; deadline provenance
is an additional operational diagnostic, not a rewritten refusal.

Cleanup runs last, after a receipt and matching record when grading was
admitted. If finalization after an expiry at any earlier phase cannot prove
safe deletion, it retains the workspace and records that fact without changing
the first-expired phase. An expiry observed during cleanup does the same. In
both cases the deadline block preserves the existing execution and grading
outcome. An
`unavailable` receipt that was durable before cleanup expiry is therefore a
completed, counted unavailable observation. Cleanup health is reported
independently from verdict quality; neither stdout nor process status supplies
a verdict.

Offline regrading is not subject to the old live deadline. It uses retained
evidence, may turn a `GRADE_FAILED` record into `OK` with a new receipt, and
must retain the original deadline block rather than implying that the original
live attempt completed in time.

## Interfaces and propagation

Expose `--attempt-timeout SECONDS` on `attempt` and `run`; omit it only for
today's unbounded whole-attempt behavior. Keep `--timeout` as the executor
command limit. Persist both values in every attempt record and in any frozen
batch schedule. A route or caller that promises 10–15 minute feedback must set
an explicit whole-attempt limit; command timeout alone is not that promise.

Introduce a small deadline value owned by the attempt layer. It supplies
remaining monotonic seconds or raises the typed expiry for the current phase.
Workspace setup and cleanup receive it; grading receives it and applies it to
environment materialization, Git work, oracle execution, and freeze
attestation. Existing command timeout and repeated-call-limit behavior remain
distinct, including their existing cleanup and evidence rules.

`run` keeps its predeclared denominator. It writes deadline provenance and any
completed verdict into the normal summary; a batch-level stopping rule,
declared by its caller, decides whether a deadline is infrastructure failure
that halts later cells. The generic `run` command does not invent a retry or a
causal interpretation.

## Required witnesses

Default-tier tests use a fake monotonic clock and fake subprocess boundaries:

1. expiry in setup writes a `DEADLINE_EXCEEDED` record before an executor can
   launch;
2. command timeout first records the existing command-timeout outcome; whole
   deadline first tears down the command, preserves available artifacts, and
   records `DEADLINE_EXCEEDED` at `command`; a simultaneous observation uses
   the whole deadline;
3. expiry after delivery preserves patch and transcript before recording
   `DEADLINE_EXCEEDED` at `preservation`;
4. expiry in grading leaves the durable `GRADE_FAILED` record and makes later
   offline regrading possible;
5. expiry after an unavailable receipt or any other receipt is written but
   before final recording/cleanup preserves that receipt, its matching outcome,
   and deadline provenance;
6. expiry in cleanup retains the workspace, names `cleanup`, and preserves the
   earlier grading outcome; and
7. offline regrading changes only eligible grading evidence, never deadline
   provenance.

Each refusal witness has a sibling within-budget success witness. Marked
integration tests additionally exercise real command-group teardown and an
oracle subprocess with a short remaining budget. They must prove retention and
resume behavior, including the bounded finalization allowance, never infer the
result from stdout or process status.

## Boundaries and gate

This work does not authorize model inference, change the qualified task/rung,
add telemetry, or choose a live executor, model, prompt, engine revision,
schedule, budget, or stopping rule. It does not make an elapsed deadline a
model-quality finding.

**Review policy.** Sol reviews implementation slices and recommendations as
they are developed. Astra performs the final acceptance review, after focused
checks pass and before any live run. A live run still needs an explicit frozen
condition, budget, stopping rule, and evidence-review request.
