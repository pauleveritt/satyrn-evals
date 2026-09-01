# `svcs` long-session eval: proposed design

**Date:** 2026-09-01. **Status:** draft for maintainer review; not approved
for implementation and not a new roadmap phase.

## Why this slice

The proposed `svcs` suite represents a serious Python development session:
five cumulative feature requests, one final review request, one evolving
checkout, and one conversation whose earlier decisions remain in context.
Six independent V4 attempts would throw
that conversation state away. One V4 attempt would preserve only the final
patch and hide where the session stopped making progress.

The smallest useful addition is a multi-prompt boundary that reuses the
current Evals responsibilities:

- V4 owns the private repository and detached attempt worktree;
- V3 owns transcript and patch preservation before cleanup;
- V1 owns hook-based offline grading and receipts; and
- a narrow executable adapter owns one conversation with Pi or another
  executor.

The current V4 implementation is synchronous and disconnects stdin. The
session implementation must extract and share its repository/worktree
lifecycle; it must not fork a second copy of the isolation and cleanup code.

This is not a port of the Phase 7 harness. `local-ai-pi` and the local probe
record failure evidence and Pi behavior only. The implementation must use the
current `satyrn-evals` types and re-earn every new behavior with its own
success and refusal tests.

## Done-when

- A session task declares two or more ordered public prompts, one or more
  cumulative hidden feature milestones, and a separate base-preservation
  selection.
- `satyrn-evals session TASK -- ADAPTER...` creates one V4-owned attempt
  worktree and starts the adapter and its model process once.
- Evals sends prompts in order. At each terminal step it snapshots the whole
  worktree, writes one cumulative Git patch from the exact base, and records
  its digest before another prompt can be sent.
- A timeout, output limit, adapter error, protocol error, or unconfirmed
  process teardown stops the sequence. No later prompt is sent.
- Grader-only files are stored outside `base/`, overlaid only in a fresh grader
  workspace, and never named in adapter argv, environment, or prompts.
- A scope violation is retained as evidence and makes the checkpoint
  non-passing. Evals neither discards forbidden changes nor grades only the
  allowlisted part as if the violation had not happened.
- After the adapter is stopped and reaped, Evals grades immutable checkpoint
  patches offline. The last captured checkpoint also runs the independent
  base-preservation selection.
- The record keeps prompt completion, deepest feature milestone, patch
  production, scope validity, base preservation, terminal reason, turns, and
  tool calls as separate fields. Counts are derived from retained events, not
  copied from adapter totals.
- A deterministic fake adapter proves the slice. Real Pi, Git, environment
  materialization, and oracle execution remain in the integration tier and
  out of CI.
- Existing single-attempt tasks and commands remain compatible. Default tests
  remain model-, network-, and subprocess-free; statement and branch coverage
  remain 100%.

## Boundary

```text
task/base/ --------------------------------> V4 detached worktree
task/session.json -- public prompts ------> adapter -> one model conversation
                                                    |
                                      Evals snapshots the whole tree
                                                    |
                                                    v
                                      immutable cumulative patches
                                                    |
task/grader/overlay/ -- grader only -----> fresh grader workspaces
task/session.json -- hidden selections --> hook receipts + session record
```

The adapter is an executable seam, as in V3 and V4. Evals does not import Pi
or Engine internals. A fake adapter and a future Engine-backed adapter occupy
the same slot. Session execution passes no path inside the task package to the
adapter. Any public Engine contract needed by a later adapter is copied into
the attempt worktree before it starts; it is not referenced through its
original task-directory path.

This is a non-adversarial local evaluation boundary, not a security sandbox.
The command runs with the user's permissions and a malicious executor could
search other paths on the machine. "Hidden" means that Evals does not place
the oracle in the worktree or conversation and does not disclose its location.
Evals cannot observe arbitrary file reads or prove that an executor did not
search the machine. Defending against a hostile command would require a
container, sandbox, or separate OS identity and remains outside version 0.1.

## CLI

```text
satyrn-evals session TASK [--tasks-root DIR] [--output DIR]
                     [--start-timeout SECONDS] [--step-timeout SECONDS]
                     [--close-timeout SECONDS]
                     -- ADAPTER...
```

`TASK` remains a task name resolved below `--tasks-root`, matching the
existing CLI. Output ownership, protected paths, usage errors, and coarse exit
status follow `attempt`. `--start-timeout` bounds the initial
`session_started` wait, and `--step-timeout` bounds one prompt.
`--close-timeout` bounds graceful adapter exit after the final checkpoint.
Version 0.1 has no automatic retry, batching, arm comparison, model client,
or LLM grader.

The large upstream `svcs` repository is not bundled in the wheel. The curated
task directory is materialized locally below a task root. Automating that
materialization or distributing the task is a separate reviewable slice; the
existing `capture --revert` command cannot construct this multi-prompt hidden
overlay without extension.

## Task layout

```text
svcs-autowire-session/
  manifest.json
  session.json
  base/                    executor-visible source and public tests
  grader/overlay/          hidden feature tests; never copied to executor
  fixtures/known-good.patch
  fixtures/known-broken.patch
```

The manifest gains one optional, validated path:

```json
{"grader_overlay": "grader/overlay"}
```

Session
tasks require it; V1-V4 tasks may omit it and keep current behavior. Overlay
paths are regular files below the declared directory, may not contain
symlinks, and may not overlap `source_paths`. Their relative paths and SHA-256
digests are recorded during qualification.

Grading copies `base/`, applies the candidate patch, and only then overlays
the grader files at their declared relative paths. An overlay may add or
replace tests, but never production source. This closes the current task-shape
gap: putting the tests in `base/` would expose them to the executor, while
leaving them outside without an overlay would make the current grader unable
to run them.

`session.json` contains both public prompts and grader-only selections because
the file itself stays in the protected task package and its path is never sent
to the adapter:

```json
{
  "version": 1,
  "steps": [
    {
      "id": "sync-functions",
      "kind": "feature",
      "prompt": "Add public synchronous and asynchronous autowire helpers.",
      "new_feature_selectors": ["tests/test_autowire.py::..."]
    },
    {
      "id": "review-and-regression",
      "kind": "review",
      "prompt": "Review the implementation and run the public suite.",
      "new_feature_selectors": []
    }
  ],
  "base_preservation_selectors": ["tests"]
}
```

Step order is significant. IDs are unique, non-empty, filesystem-safe tokens.
A `feature` step adds at least one previously unseen hidden pytest selector.
A `review` step adds none and cannot increase the feature-milestone score; it captures
repair and preservation behavior separately. The actual `svcs` workload has
five feature milestones followed by one review prompt.

The loader rejects fewer than two steps, duplicate IDs, empty prompts,
duplicate or missing feature selectors, a feature step without a new selector,
or an empty base-preservation selector list before allocating a workspace. The grader also
proves that every feature selector collects at least one test in the overlaid
task. Ordinary tasks need no `session.json`.

## Adapter protocol and conversation identity

The adapter starts once in the detached worktree and communicates as
versioned JSONL over stdin and stdout. Its first message declares one opaque
conversation identity:

```json
{"version":1,"type":"session_started","conversation_id":"opaque-id"}
```

Evals then sends one prompt at a time:

```json
{"version":1,"type":"prompt","step_id":"sync-functions","text":"..."}
```

The adapter emits raw, countable events followed by one terminal message for
the active step:

```json
{"version":1,"type":"event","step_id":"sync-functions","kind":"turn_end","payload":{}}
{"version":1,"type":"event","step_id":"sync-functions","kind":"tool_end","payload":{}}
{"version":1,"type":"step_finished","step_id":"sync-functions","conversation_id":"opaque-id","outcome":"settled","message":null}
```

`kind` is `turn_end`, `tool_end`, `context_compacted`, `context_reset`, or
`other`. Evals writes every raw line before parsing it and derives counters
from these retained events. The terminal message supplies no totals. A Pi
adapter maps Pi RPC events to these kinds and keeps the complete original Pi
event in `payload`, so its mapping and every count are recomputable.

`outcome` is `settled`, `output-limit`, or `agent-error`. The adapter maps a
model-runtime terminal event to `output-limit`; Evals does not infer a token
limit from prose. Only `settled` permits another prompt. Every event and
terminal message must carry the active step and the original conversation
identity. A second `session_started`, changed identity, context reset,
malformed JSON, wrong or duplicate step, unknown version or type, premature
EOF, or adapter exit before a terminal message is a protocol failure.

One process and stable identity are evidence that the adapter preserved one
conversation, not proof against a dishonest adapter. The shipped Pi adapter's
integration test starts one Pi RPC process, sends two prompts, observes the
same conversation, and records any compaction event. Process restarts are not
allowed in version 0.1.

## Checkpoint and close lifecycle

For each step, Evals owns this transition:

```text
READY
  -> prompt sent
  -> terminal event or timeout
  -> stop and reap adapter if terminal is not settled
  -> snapshot full status and cumulative Git patch
  -> classify source paths and scope violations
  -> write patch, transcript prefix, and step record durably
  -> next prompt, graceful close, or session stop
```

Evals, not the adapter, obtains the patch with Git from the detached worktree.
After the adapter is quiescent or reaped, Evals creates an alternate Git index
outside the attempt worktree, seeds it from the exact base, and runs
`git add -N --all` against that index. This makes untracked paths visible
without changing the real index that the next prompt will observe. Evals reads
the full status and binary diff through the alternate index, then removes it.
The patch is cumulative from its exact synthetic base and includes binary,
rename, delete, mode, symlink, and untracked-file intent. The associated full
tree snapshot and status are recorded. Evals writes the patch to a new file,
fsyncs it, computes the digest from those bytes, then atomically replaces the
step record. An unchanged tree still receives an empty or repeated patch and
its digest; stalled progress is evidence, not an omitted step.

Any changed path outside `source_paths` sets `scope_valid=false`. The full
patch remains in evidence, hidden grading is skipped for that checkpoint, and
no filtered patch is substituted for it. This includes modifications,
additions, deletions, renames, modes, symlinks, and untracked files.

On timeout or exceptional wait, Evals terminates and reaps the adapter process
group before snapshotting. This preserves V4's ordering: a late descendant
must not mutate a patch after its digest is recorded. Normal `settled` is a
trusted quiescence boundary in the non-adversarial version 0.1 scope.

After the final settled checkpoint, Evals sends:

```json
{"version":1,"type":"close"}
```

The adapter must close stdout and exit with code zero before `--close-timeout`.
Further protocol output, non-zero exit, or timeout is `ADAPTER_ERROR`; Evals
performs bounded group teardown. Failure to confirm child reap and group
disappearance is `CLEANUP_FAILED` and retains the recovery path. A safe
adapter error still leaves captured patches available for offline grading.

## Offline grading

No hidden test runs while the adapter is alive. After confirmed process
teardown, feature and preservation grading use separate workspaces:

- the feature grader copies `base/`, applies the patch, overlays grader-only
  files, and runs cumulative hidden feature selectors;
- the preservation grader copies `base/`, applies the same patch without the
  overlay, and runs the declared public selectors.

Both invoke the existing hook mechanism. Keeping preservation free of the
target overlay prevents a replaced test file from silently changing the base
behavior being preserved.

Feature checkpoint `n` runs the ordered union of hidden selectors introduced
through that step. A review step repeats the current cumulative feature selection but
does not increase the feature score. The last captured checkpoint, including
one captured after early termination, also runs the independent base
preservation selectors.
Receipts keep `feature_verdict` and `base_preservation_verdict` separate.

The verdict comes from hook files, never stdout, exit code, or adapter prose.
A collection error or missing hook result is `unavailable`, not a failed task.
A scope violation is a candidate failure, not infrastructure unavailability.
The final session passes only if every prompt settled, the last feature
selection passes, base preservation passes, and every checkpoint is
scope-valid.

Before the `svcs` task is accepted, the final upstream patch must pass every
cumulative feature selection and base preservation three times in fresh,
separate grader workspaces. The empty/broken fixture must fail for the registered
reason. Because the current base fails collection at the first missing public
symbol, this proves the whole feature is absent; it does not prove that each
later milestone independently has middle-band difficulty. Baseline runs, not
qualification, establish discriminating power.

## Artifacts and record

```text
session.json
transcript.jsonl
checkpoints/01-sync-functions.patch
snapshots/01-sync-functions.json
receipts/01-sync-functions.json
session-record.json
```

The record contains the adapter command, synthetic starting commit, task
provenance, terminal step and code, conversation identity, and one entry per
captured step. A step contains its prompt digest, adapter outcome, derived
turn/tool/context-event counts, patch and snapshot digests, scope violations,
feature verdict, base-preservation verdict when run, and receipt paths.

The top level derives but does not conflate:

- whether all prompts settled;
- the deepest passing feature milestone, from zero through five for this task;
- whether any non-empty patch was retained;
- whether every checkpoint stayed in scope;
- whether the last captured patch preserved base behavior; and
- whether grading was available.

Precise codes are `COMPLETE`, `STEP_TIMEOUT`, `OUTPUT_LIMIT`, `ADAPTER_ERROR`,
`PROTOCOL_ERROR`, `SCOPE_VIOLATION`, `GRADE_UNAVAILABLE`, `WORKSPACE_FAILED`,
and `CLEANUP_FAILED`. Coarse CLI status remains `0` for a safely captured and
graded session, including a model failure or scope violation; `2` for usage or
start refusal; and `3` for operational refusal or unavailable grading.

## Reviewable implementation slices

If approved, implementation stays reviewable as five slices:

1. grader-only overlay, its known-good/known-broken evidence floor, and
   backward-compatible ordinary grading;
2. session manifest, typed records, protocol parser, and pure state tests;
3. a shared V4 workspace lifecycle plus fake-adapter process and checkpoint
   preservation tests;
4. cumulative feature/base grading, scope enforcement, and records;
5. the locally materialized `svcs` task, Pi adapter, integration evidence,
   and user documentation.

The fifth slice is the only `svcs`-specific code. If any slice grows beyond
one clear state transition, it is split before implementation rather than
hidden behind more abstractions.

## Deferred

- `run --n 8`, summaries, and V5 admission;
- automatic interpretation or an operator skill;
- API keys or model-client integration;
- retries, exclusions, and claims-layer condition enforcement;
- replaying an arbitrary developer's existing JSONL session;
- distributing upstream source or large raw transcripts;
- public-test feedback and other Engine remediations; and
- a persistent Engine daemon, hostile-command sandbox, or shared
  Engine/Evals Python package.
