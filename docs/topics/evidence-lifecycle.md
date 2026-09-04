# The evidence lifecycle

Evals' central idea is to keep the change an engine produced separate from the
judgment about that change. This makes a result inspectable and re-gradeable.

```text
capture a task → run an attempt → preserve artifacts → grade offline → diagnose
     real fix       candidate change       patch + transcript       receipt       counts
```

## Capture makes a real change repeatable

`capture --revert SHA` derives a task from a fixing commit. The task holds a
base state, its task statement, the tests that distinguish base from fix, and a
known-good patch. Four deterministic checks establish that the base is un-done
and the known-good patch is winnable.

## Attempt saves what happened

An executable attempt command receives a task in an Evals-owned detached
worktree. It delivers a patch and transcript to reserved paths outside that
worktree. Evals preserves those files before cleanup, including on an artifact
refusal. This is the separation that permits later re-grading without spending
another model run.

## Grade judges patch evidence

Grading applies a supplied patch to a fresh copy of the task base and runs the
task oracle. For an attempt, that is the patch preserved from its delivery
path. Its receipt records the patch digest, verdict, reason, and test evidence.
The command exit status is deliberately not verdict evidence: a clean zero can
mean that no meaningful test actually ran.

## Diagnose looks for a next action

`run` repeats attempts and aggregates outcomes into counts. Those counts are
diagnostic: they show which refusal codes, verdicts, and timeouts occurred.
They are not a statistical comparison by themselves. A task needs a qualifying
baseline probe before it can serve as a diagnostic workload for an engine
change.

For the precise vocabulary, use the [glossary](../glossary.md). For the
implementation shape, see [architecture](../architecture.md).
