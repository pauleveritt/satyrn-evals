# `svcs` long-session eval: proposed design

**Date:** 2026-09-01. **Status:** draft for maintainer review; not approved
for implementation and not a new roadmap phase.

## Why this slice

The proposed `svcs` suite represents a serious Python development session:
six cumulative requests, one evolving checkout, and one conversation whose
earlier decisions remain in context. Running six independent V4 attempts
would change the workload by discarding that conversation state. Running one
V4 attempt would preserve only the final patch and hide where the session
stopped making progress.

The smallest useful addition is therefore a multi-prompt session boundary
that reuses the current Evals machinery:

- V4 owns the private repository and detached attempt worktree;
- V3 owns transcript and patch preservation before cleanup;
- V1 owns offline grading and receipts; and
- a narrow adapter owns the conversation with Pi or another executor.

This is not a port of the Phase 7 harness. `local-ai-pi` and the local probe
record failure evidence and Pi behavior only. The implementation must use the
current `satyrn-evals` types and lifecycle and re-earn each new behavior with
its own success and refusal tests.

## Done-when

- A session task declares two or more ordered public prompts and cumulative
  hidden grading milestones.
- `satyrn-evals session TASK -- ADAPTER...` creates one V4-isolated attempt
  workspace and starts the adapter once in it.
- Evals sends prompts in order. After each settled prompt it captures a
  cumulative patch from the exact base and records its digest before sending
  the next prompt.
- A timeout, output limit, adapter error, protocol error, or failed process
  teardown stops the sequence. No later prompt is sent.
- The adapter and executor never receive the target revision, oracle files,
  expected test IDs, reference patch, or grader output.
- After the adapter is stopped and reaped, Evals grades the immutable
  checkpoint patches offline. The final checkpoint also runs the task's
  preservation oracle.
- The session record keeps terminal condition, completion, deepest passing
  checkpoint, retained-patch production, per-step turns and tool calls, and
  final preservation as separate fields.
- A deterministic fake adapter proves the complete slice. Real Pi, Git,
  environment materialization, and oracle execution remain in the integration
  tier and out of CI.
- The existing single-attempt CLI, manifest, records, and fixtures remain
  compatible. Default tests remain model-, network-, and subprocess-free;
  statement and branch coverage remain 100%.

## Boundary

```text
session task package
  public prompts --------------------------+
  captured base -----------------------+   |
  hidden milestones + oracle files --+ |   |
                                     | |   v
satyrn-evals session                 | |  adapter -> persistent executor
  V4 private repository/worktree <---|-+       |
  checkpoint cumulative patches <----|---------+
  stop and reap adapter              |
  grade immutable checkpoints <------+
  write receipts + session record
```

The adapter is an executable seam, as in V3 and V4. Evals does not import Pi
or Engine internals. A fake adapter and a future Engine-backed adapter occupy
the same slot.

The executor sees only the detached worktree and the current public prompt.
The grader runs later in a separate eval-owned workspace. Instruction text is
not treated as an anti-cheat boundary; filesystem and process separation keep
the hidden inputs out of the executor environment.

## CLI

```text
satyrn-evals session TASK [--tasks-root DIR] [--output DIR]
                     [--step-timeout SECONDS] -- ADAPTER...
```

`TASK`, task-root resolution, output ownership, coarse exit status, and
workspace failures follow the existing commands. `--step-timeout` bounds one
prompt, not the entire session. Version 0.1 deliberately has no automatic
retry, batching, arm comparison, model client, or LLM grader.

The first implementation supports an explicit task path or task-root entry.
It does not bundle the large upstream `svcs` repository in the wheel. A
curated task can be materialized locally through the existing capture and
task-root seams; packaging and distribution are separate follow-up work.

## Session task data

A session-capable task adds `session.json` beside its existing
`manifest.json`:

```json
{
  "version": 1,
  "steps": [
    {
      "id": "sync-functions",
      "prompt": "Add public synchronous and asynchronous autowire helpers.",
      "expected_test_ids": ["tests/test_autowire.py::..."]
    }
  ],
  "preservation_test_ids": ["tests"]
}
```

Step order is significant and IDs are unique, non-empty, filesystem-safe
tokens. The public `prompt` goes to the adapter. `expected_test_ids` and
`preservation_test_ids` remain grader-only. The existing manifest continues
to own the base, source allowlist, oracle command, fixtures, and provenance.

The task loader validates the complete shape before allocating a workspace.
A session task with fewer than two steps, duplicate IDs, an empty prompt,
missing cumulative tests, or no final preservation selection is refused with
a usage error. Ordinary V1–V4 tasks need no `session.json`.

## Adapter protocol

The adapter starts once in the detached worktree and communicates as
versioned JSONL over stdin and stdout. Evals sends:

```json
{"version":1,"type":"prompt","step_id":"sync-functions","text":"..."}
{"version":1,"type":"close"}
```

The adapter sends zero or more opaque events followed by exactly one terminal
message for the active step:

```json
{"version":1,"type":"event","step_id":"sync-functions","event":{}}
{"version":1,"type":"step_finished","step_id":"sync-functions","outcome":"settled","turns":12,"tool_calls":11,"message":null}
```

`outcome` is `settled`, `output-limit`, or `agent-error`. Only `settled`
allows another prompt. A wrong or duplicate step ID, malformed JSON, an
unknown version or type, adapter exit before the terminal message, or output
after termination is a protocol failure.

An `event` payload is transcript evidence, not a verdict. Evals writes each
raw line before interpreting it. The adapter supplies diagnostic turn and
tool-call counts, but the first implementation need not normalize arbitrary
model telemetry. A Pi-specific adapter may derive those counters from Pi RPC
events and retain the original events for recomputation.

## Checkpoint lifecycle

For each step, Evals follows one ordered state transition:

```text
READY
  -> prompt sent
  -> terminal event or timeout
  -> adapter stopped when terminal is not settled
  -> cumulative patch captured and digested
  -> step record durably replaced
  -> next prompt, or session stop
```

The patch is always cumulative from the exact starting commit. An unchanged
tree still receives a step record and the digest of an empty or repeated
patch; that is evidence of stalled progress, not a reason to omit the step.
Patch capture applies the existing source allowlist and records out-of-scope
changes rather than trusting the adapter's account.

On a timeout or exceptional wait path, Evals terminates and reaps the adapter
process group before capturing the checkpoint. This preserves V4's cleanup
ordering: a late descendant must not mutate a patch after its digest is
recorded. Normal `settled` is a trusted quiescence boundary in version 0.1;
hostile daemon containment remains outside the lightweight local scope.

## Offline grading

No hidden test runs while the adapter is alive. Once the adapter is stopped,
Evals applies each retained cumulative patch to a fresh grader workspace and
invokes the existing hook-based oracle. Checkpoint `n` uses the ordered union
of expected test IDs through step `n`; the last captured checkpoint also runs
the declared preservation selection.

Every grade writes an ordinary receipt tied to the checkpoint patch digest.
The verdict comes from the hook result, never stdout, an exit code, or adapter
prose. A collection error or missing hook result is `unavailable`, not a
failed task. Known-good and known-broken session fixtures must prove every
cumulative milestone before the `svcs` task is accepted.

## Artifacts and record

```text
session.json
transcript.jsonl
checkpoints/01-sync-functions.patch
receipts/01-sync-functions.json
session-record.json
```

The record contains the adapter command, exact starting identity, terminal
step and code, and one entry per captured step. Each entry contains the step
ID, adapter outcome, prompt digest, turns, tool calls, patch path and digest,
grade verdict, and receipt path. The top level derives but does not conflate:

- whether all prompts settled;
- the deepest consecutively passing cumulative checkpoint;
- whether any non-empty patch was retained;
- whether final preservation passed; and
- whether grading was available.

Precise codes are `COMPLETE`, `STEP_TIMEOUT`, `OUTPUT_LIMIT`, `ADAPTER_ERROR`,
`PROTOCOL_ERROR`, `GRADE_UNAVAILABLE`, `WORKSPACE_FAILED`, and
`CLEANUP_FAILED`. Existing coarse CLI status remains: `0` for an attempted
session whose artifacts were safely graded, even when its verdict is fail;
`2` for usage or start refusal; and `3` for operational refusal or unavailable
grading.

## Reviewable implementation slices

If this design is approved, implementation should stay small enough to review
as four slices:

1. session manifest, typed records, protocol parser, and pure state tests;
2. one-workspace adapter lifecycle and checkpoint preservation with a fake
   adapter;
3. offline cumulative grading and the known-good/known-broken evidence floor;
4. the locally materialized `svcs` suite, Pi adapter, integration evidence,
   and user documentation.

The first three slices are general Evals machinery. The fourth is the only
`svcs`-specific slice. If any slice grows beyond one clear state transition,
it should be split before implementation rather than hidden behind more
abstractions.

## Deferred

- `run --n 8`, summaries, and V5 admission;
- automatic interpretation or an operator skill;
- API keys or a model-client integration;
- retries, exclusions, and claims-layer condition enforcement;
- replaying an arbitrary developer's existing JSONL session;
- distributing the upstream repository or large raw transcripts;
- public-preservation feedback and other Engine remediations; and
- a persistent Engine daemon or shared Engine/Evals Python package.
