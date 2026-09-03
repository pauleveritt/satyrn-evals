# V5b — The diagnostic loop: design spec

**Phase:** V5b (`ROADMAP.md:61`). **Date:** 2026-09-02.
**Status:** proposal confirmed by the maintainer 2026-09-02; spec written
before implementation per `docs/sdd.md`.

## What V5b ships

V5b adds one subcommand, `run`, that executes an attempt command n=8 times
against one admitted task and writes a summary of counts only. It is the
first phase since V4 that runs a model, so the integration-tier rules
(`BRIEF.md:80-83`) come back into force.

V5b does not re-admit, re-probe, or compare arms. Admission is V5a's gate
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:238-245`);
arm comparison and any confidence claim are the claims layer, deferred
(`BRIEF.md:33-36`). The loop is arm-agnostic: it summarizes whatever command
is passed. This phase ships the structured tier alone: it is close to what
the probe records already reported by hand, while the deferred transcript
metrics (Out of scope) are the ones that catch the harvest-index failure
modes — 245 identical `ls -R` calls, 27 rewrites of one template
(`docs/superpowers/research/2026-08-16-harvest-index.md:69-74`). V5b ships
the loop and the sequencing; the diagnosis it is named for largely waits on
an engine-side emitter for those counts.

## CLI surface

    satyrn-evals run TASK [--n N] [--tasks-root DIR] [--output DIR] [--timeout S] -- COMMAND...

Mirrors `attempt` (`src/satyrn_evals/cli.py:111-124`), adding `--n`
(default 8). The attempt command travels the same `-- COMMAND...` engine
seam (`src/satyrn_evals/attempt.py:80`); `run` is repeated `attempt` plus a
summary, with no new engine coupling. `--n` must be a positive integer;
zero or negative is a usage error. One task per invocation; suite
sequencing over the V5a index is the caller's loop, not this phase.

## Exit codes

- `0` — the loop completed: all n attempts persisted and the summary
  written, whatever the verdicts.
- `2` — usage error: unknown task, empty command, or a non-positive `--n`
  (raised before any attempt runs).
- `3` — operational failure: the loop itself could not complete.

Per-attempt refusals are not exit 3; they are recorded and summarized
(`attempt` already writes a record for every refusal,
`src/satyrn_evals/attempt.py:53-71`). The summary is the authoritative
result, never the exit code (`BRIEF.md:76-79`).

## Data shapes

Per attempt, the existing V3/V4 `attempt.json` record
(`src/satyrn_evals/attempt_record.py:144`): patch and transcript persisted
before cleanup, graded offline, carrying `outcome`, `code`, `verdict`, and
`command_exit`. No new per-attempt shape.

One summary per run — `summary.json`, counts only. Every count names the
exact cell set it was computed over (the overnight-run standing test,
`docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md:186-190`):

**Structured tier** (from the attempt records — always available):

- `n`, `attempted`, `refused`;
- `code_counts` — tally of `AttemptCode` values, the refusal reasons
  (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`,
  `WORKSPACE_FAILED`, `COMMAND_TIMEOUT`, `CLEANUP_FAILED`, `OK`) —
  `src/satyrn_evals/attempt_record.py:38-49`;
- `verdict_counts` — tally of `PASS` / `FAIL` / `UNAVAILABLE` over the
  attempted records;
- `timeouts` — count of `COMMAND_TIMEOUT` (also in `code_counts`; called
  out because `ROADMAP.md:61` lists it).

**Transcript tier — deferred.** The four remaining roadmap metrics —
`tool_calls`, `repeat`, `churn`, `context` — are not shipped in V5b. Their
data is Pi's print-mode stream-JSON, spooled verbatim by the engine as
`transcript.jsonl` (`satyrn-engine/src/satyrn_engine/attempt.py:578`,
`:206-225`). Parsing that stream inside evals would reach through the engine
seam to the runtime behind it, coupling evals to an upstream tool's output
schema — a breach of the V4 property that the Engine contract stays opaque
to evals. The counts belong engine-side, published as an artifact the engine
derives from its own Pi stream; see Out of scope and `BACKLOG.md`. Their
definitions are already recorded: `repeat` is identical `(toolName,
arguments)` calls counted regardless of success
(`docs/superpowers/research/2026-08-16-harvest-index.md:69-71`), `churn` is
the same target rewritten with differing content (`:74`), kept separate
(`docs/superpowers/research/2026-09-01-handoff-and-eval-harvest.md:360`).

Counts only: never wall-clock (`BRIEF.md:39-40`). The loop persists all n
attempts even if conditions drift mid-run (`BRIEF.md:38`); it does not abort
a batch.

## Test layout

- Default tier stays model/network/subprocess-free (`BRIEF.md:80-83`, the
  planted-spawn tripwire). `run` is driven by a deterministic fake seam
  command that writes a known patch + transcript; the summary is computed
  from persisted records only.
- A refusal test has a sibling success test (`BRIEF.md:84-85`); the summary
  is computed from persisted records only, so its tests never parse a
  transcript.
- Capture is separate from grading (`BRIEF.md:72-75`): the summary reads
  only persisted artifacts, so a summary defect re-scores without re-running
  a model.
- Integration tier (marked, not in CI): one real attempt command against a
  bundled task, naming the success and failure fixtures.

## Done-when

- `run TASK --n 8 -- COMMAND...` executes n attempts, persists each
  `attempt.json`, and writes `summary.json` with the structured tier.
- The default tier proves the structured tier from a deterministic fake
  seam (persisted records only; no transcript parsing), with the
  refusal/success sibling pair and the planted tripwire untouched.
- The integration tier runs one real attempt command and names both the
  success and failure fixtures.

## Out of scope (deferred)

- The claims layer — pre-registration, intervals, void accounting, A/B
  (`BRIEF.md:33-36`).
- Arm comparison and suite sequencing beyond one task per invocation.
- Suite-with-headroom capture (`BRIEF.md:138-142`).
- The four transcript-derived metrics — `tool_calls`, `repeat`, `churn`,
  `context` — deferred because their data is Pi's stream-JSON behind the
  engine seam that V4 established as opaque to evals
  (`satyrn-engine/src/satyrn_engine/attempt.py:578`, `:206-225`). **Reopens
  when the engine exposes those counts across the seam** — a new engine-side
  emitter reading its own Pi stream — and not when a transcript sample
  becomes available. Tracked in `BACKLOG.md`. *Recorded correction
  (2026-09-02): this deferral previously named satyrn-engine's `facts`
  field as the home; that field is a `Contract` field rendered into the
  handoff prompt (`satyrn-engine/src/satyrn_engine/contract.py:23-28`,
  `attempt.py:229-238`) — prompt content, not run telemetry. The pointer
  was wrong.*
