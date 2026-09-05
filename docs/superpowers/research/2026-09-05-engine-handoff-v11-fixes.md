# Engine handoff — V11 correction round

**Date:** 2026-09-05
**Status:** handoff for `satyrn-engine`; no Engine code was changed here and
no new model or smoke run is authorized by this note.

This records the final surviving Engine spool and the repairs required before
an Engine arm can consume budget in V11c or V12. The evidence is diagnostic,
not a result about model quality.

## Confirmed evidence

The retained spool is approximately 3.5 MB and was modified at 2026-09-05
11:25 EDT. It contains 816 tool calls across six distinct calls; 811 are
`read tests/test_app.py`. Of 816 tool results, 806 are loop-breaker refusals.
The model emits no prose and turns take approximately 3.5 seconds. Earlier
749/744/739 counts were snapshots taken while the orphaned process was still
writing and are superseded by these final counts.

The loop-breaker telemetry is also independently confirmed: all 806 relevant
events are `entry_appended` entries whose `entry.customType` is exactly
`loop_broken`. The evals pathology vocabulary now counts that event as
`loop_broken`; other custom entry types remain unknown.

## Defects owed to Engine

1. The Engine contract tells the model about a runnable public suite, but the
   Engine arm exposes only `read,edit`; it has no `bash` and cannot run that
   suite. Alongside phantom test names this causes repeated reads of the only
   test file.
2. The loop breaker refuses repeated calls after its threshold (`5` in a
   `20`-call window) but does not terminate the agent. Pi 0.84.4 has no turn
   cap, so the same refusal repeats until the eval timeout.
3. A timed-out Engine cell loses its transcript. Engine publishes its spool
   only after Pi exits, has no SIGTERM publication guard on this path, and
   evals removes the temporary workspace during cleanup. Baseline's direct
   stream preserves a partial transcript, so the two arms currently have an
   unacknowledged timeout asymmetry.

## Required repair behavior

- Terminate the agent after a bounded number of consecutive blocked calls (or
  enforce an equivalent turn cap), while preserving the explicit
  `loop_broken` telemetry.
- Publish the accumulated spool on SIGTERM and other timeout teardown paths,
  before the Engine process exits or its temporary workspace is removed.
- Keep the Engine transcript JSONL and model identity intact so the strict
  tally can inspect `message.model` for every counted attempt.

The evals-side follow-up is to copy any Engine spool before workspace teardown
once the Engine exposes a reliable published artifact. This is not a license
to infer a completed Engine cell from a timed-out or unpublished spool.

## Re-smoke acceptance criteria

Run one uncounted V5d Engine smoke against a generated contract after the
Engine repair and the correction tree has landed. The smoke is acceptable
only if all of the following are true:

- the Engine process terminates before the eval timeout when the loop-breaker
  condition is reached;
- the attempt record and preserved transcript survive teardown, with a
  parseable `message.model` matching the scheduled model;
- the generated contract is the bytes actually handed to Engine;
- the resulting summary reports measured pathology, including the observed
  `loop_broken` count, rather than `unknown_event`;
- patch/transcript delivery and offline grading retain their existing V5d
  behavior; and
- no `.venv`, bytecode, or other runtime residue is left in the materialized
  workspace.

A passing smoke clears the Engine-specific V11c gate. It does not authorize a
budgeted comparison by itself: clean-tree preflight, the remaining V11
landing controls, and the protocol's other preconditions still apply.
