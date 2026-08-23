# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**Phase V4 — A real engine attempt. Waiting for engine E5.** V3's executable
seam is complete; V4 uses the same artifact set with `satyrn-engine attempt`.
See the Phases table below and `BRIEF.md` for the binding rules.

## Concept budget

*Every term below is a cost against a 5–10 h/wk volunteer's ability to hold
the design in mind. Checked and updated at the end of each cycle; a term
earns its place by naming something the design actually needs, not by being
convenient shorthand.*

The seed terms plus V2's additions — **capture record**, **discriminating
set**, **provenance** — are defined in this repository's own words in
[`docs/glossary.md`](docs/glossary.md), checked and updated at the end of
V2. Terms for later phases earn their place when the phase that needs
them lands.

## Phases

| # | Phase | Direction (one sentence) | Status |
|---|-------|--------------------------|--------|
| V1 | It installs and grades | `grade` accepts a bundled task's known-good patch and rejects its known-broken one, offline and deterministic | **complete** |
| V2 | Capture by revert | `capture --revert SHA` makes a task winnable by construction, in minutes | **complete** |
| V3 | Attempt persistence | `attempt TASK -- COMMAND...` runs a fake command, persists patch and transcript, regrades offline | **complete** |
| V4 | A real engine attempt | The same artifact set, produced by `satyrn-engine attempt` (engine phase E5) | **current; waiting for E5** |
| V5 | The diagnostic loop | admit tasks with a recorded n=4–6 baseline probe, then `run --n 8` and summarize verdict reasons, repeated calls, churn, tool calls, context, and timeouts | not started |

Full done-when criteria are in `BRIEF.md`'s referenced roadmap research, not
restated here to avoid drift between two copies.

**Design work owed, not a phase:** a suite with headroom. See `BRIEF.md`'s
"The unsolved problem." V3 deliberately persisted single attempts without
claiming a baseline. V4 supplies the real engine attempt; before V5 admits a
task, an n=4–6 baseline probe must show that the task has room to move.

## Backlog

Deferred, each with the condition that reopens it — see `BRIEF.md`:
automated commit mining (after three manual captures show which steps
repeat); paired A/B of two engine versions (when a contributor needs "did
my fix help" across versions); resumable large batches (only if the prior
checkpoint transplants verbatim); the whole claims layer.

## Prior work

Completed phases move here (or to `docs/superpowers/phase-history.md`)
when the roadmap outgrows the front page.

- **V3 — Attempt persistence (2026-08-18).** `attempt TASK -- COMMAND...`
  runs an executable through the environment seam in a disposable workspace,
  preserves patch and transcript before cleanup, grades the preserved patch,
  and writes an attempt record.
- **V2 — Capture by revert (2026-08-18).** `satyrn-evals capture --revert
  SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]`:
  four deterministic checks, a detached-worktree lifecycle re-earned from
  the engine's E3 spec, optional `known_broken`/`provenance` in the
  manifest, the E3-shaped capture record, `grade --tasks-root`, and the
  oracle hook recording collection errors. Spec, plan, and revisions are
  recorded under `docs/superpowers/`.
- **V1 — It installs and grades (2026-08-16).** `satyrn-evals grade TASK
  PATCH [--receipt PATH]`: manifest-validated tasks, allowlisted unified
  diffs, hook-result verdicts, receipts, the audit-hook tripwire, and two
  test tiers. Spec, plan, and corrections are recorded under
  `docs/superpowers/`.

## Workflow

This repository runs on spec-driven development — see
[`docs/sdd.md`](docs/sdd.md). Each feature cycle gets a committed design
spec, an implementation plan, then code. The default test suite needs no
model, network, or subprocess; process behavior lives in a small marked
integration tier.
