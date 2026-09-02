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
is passed.

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

**Transcript tier** (best-effort, derived by parsing each `transcript.txt`):

- `tool_calls` — total tool-call events;
- `repeat` — repeated identical `(toolName, arguments)` calls, counted
  regardless of success
  (`docs/superpowers/research/2026-08-16-harvest-index.md:69-71`);
- `churn` — the same target rewritten with differing content, kept separate
  from `repeat`
  (`docs/superpowers/research/2026-08-16-harvest-index.md:74`;
  `docs/superpowers/research/2026-09-01-handoff-and-eval-harvest.md:360`);
- `context` — peak reported tokens and turn count
  (`docs/superpowers/research/2026-08-27-local-pings-baseline-probe.md:111`).

A transcript that yields no parseable tool calls is reported **unmeasured**,
never zero — the overnight run's finding
(`docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md:160-162`,
`:200`: models emit tool calls as literal JSON text or prose, not a uniform
schema).

**Open dependency.** No transcript grammar is committed in this repository:
V3 deferred "transcript format" (`ROADMAP.md:55`), and the probes parsed
adapter transcripts through `analyze.py` scripts in local evidence bundles,
not committed here
(`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:309`). The
plan therefore either pins the grammar from a committed sample transcript
before its transcript-tier tasks, or ships the structured tier and defers
the transcript tier with that as the reopen condition. The decision is
recorded at plan time, before any transcript code is written.

Counts only: never wall-clock (`BRIEF.md:39-40`). The loop persists all n
attempts even if conditions drift mid-run (`BRIEF.md:38`); it does not abort
a batch.

## Test layout

- Default tier stays model/network/subprocess-free (`BRIEF.md:80-83`, the
  planted-spawn tripwire). `run` is driven by a deterministic fake seam
  command that writes a known patch + transcript; the summary is computed
  from persisted records only.
- A refusal test has a sibling success test (`BRIEF.md:84-85`), and every
  transcript-derived count fires on a known-bad transcript and stays silent
  on a known-good one, both directions (`BRIEF.md:94-97`).
- Capture is separate from grading (`BRIEF.md:72-75`): the summary reads
  only persisted artifacts, so a summary defect re-scores without re-running
  a model.
- Integration tier (marked, not in CI): one real attempt command against a
  bundled task, naming the success and failure fixtures.

## Done-when

- `run TASK --n 8 -- COMMAND...` executes n attempts, persists each
  `attempt.json`, and writes `summary.json` with the structured tier always
  present and the transcript tier best-effort.
- The default tier proves the six metrics from a deterministic fake seam,
  with the refusal/success sibling pair and the planted tripwire untouched.
- The integration tier runs one real attempt command and names both the
  success and failure fixtures.

## Out of scope (deferred)

- The claims layer — pre-registration, intervals, void accounting, A/B
  (`BRIEF.md:33-36`).
- Arm comparison and suite sequencing beyond one task per invocation.
- Suite-with-headroom capture (`BRIEF.md:138-142`).
- A formal transcript schema — V5b parses best-effort; the format contract
  is its own work, not this phase.
