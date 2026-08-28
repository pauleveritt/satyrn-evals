# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**V4 is complete. Suite headroom is next.** Before V5 starts, baseline probes
must identify tasks between the floor and ceiling so the diagnostic loop has
something useful to measure. See the Phases table below and `BRIEF.md` for the
binding rules.

## Concept budget

*Every term below is a cost against a 5–10 h/wk volunteer's ability to hold
the design in mind. Checked and updated at the end of each cycle; a term
earns its place by naming something the design actually needs, not by being
convenient shorthand.*

The terms used through V4 are defined in this repository's own words in
[`docs/glossary.md`](docs/glossary.md), checked and updated at the end of
V4. Terms for later phases earn their place when the phase that needs them
lands.

## Phases

| # | Phase | Direction (one sentence) | Status |
|---|-------|--------------------------|--------|
| V1 | It installs and grades | `grade` accepts a bundled task's known-good patch and rejects its known-broken one, offline and deterministic | **complete** |
| V2 | Capture by revert | `capture --revert SHA` makes a task winnable by construction, in minutes | **complete** |
| V3 | Attempt persistence | `attempt TASK -- COMMAND...` runs a fake command, persists patch and transcript, regrades offline | **complete** |
| V4 | A real engine attempt | Reconstruct an isolated Git workspace and produce the V3 artifact set with `satyrn-engine attempt` | **complete** |
| V5 | The diagnostic loop | admit tasks with a recorded n=4–6 baseline probe, then `run --n 8` and summarize verdict reasons, repeated calls, churn, tool calls, context, and timeouts | not started |

Full done-when criteria are in `BRIEF.md`'s referenced roadmap research, not
restated here to avoid drift between two copies.

**Design work owed, not a phase:** a suite with headroom. See `BRIEF.md`'s
"The unsolved problem." V3 deliberately persisted single attempts without
claiming a baseline. V4 supplies the real engine attempt; before V5 admits a
task, an n=4–6 baseline probe must show that the task has room to move.
`local-pings` remains unadmitted. Its first probe exposed an unsound oracle;
the corrected probe then recorded 0/4 successful attempts, while two timed-out
attempts retained patches that passed the corrected oracle and preservation
suite. Before V5, admission must keep successful attempt outcomes, retained
patch production, and the conditional quality of retained patches separate
rather than choosing a metric after seeing the result. A follow-up recorded a
budget-only Envelope variant at 0/4 and the handoff-contract Engine composite
at 2/4, which is useful product-path evidence but does not move the Baseline
off its floor. The three records are the
[`oracle audit`](docs/superpowers/research/2026-08-27-local-pings-baseline-probe.md),
the [`corrected probe`](docs/superpowers/research/2026-08-27-local-pings-corrected-probe.md),
and the
[`Envelope/Engine follow-up`](docs/superpowers/research/2026-08-27-local-pings-envelope-engine-followup.md).

`magicmock-factory` is also unadmitted. Successive task versions recorded 3/6,
1/6, and then 0/4, but their increasingly explicit contracts and fresh
stochastic samples make those rates unsuitable as a direct comparison. The
candidate audit is decisive: all five first-stage patches fail correction 1,
and the sole second-stage passing patch fails correction 2. The final task is
valid and its exact upstream fix passes all 142 upstream tests, but bare Pi
retained no patch that passed the final oracle. See the
[`magicmock-factory` oracle audit and final probe](docs/superpowers/research/2026-08-29-magicmock-factory-baseline-probe.md).

`stringified-annotations`, the only discriminator in the old Cycle 7 batch,
is not admitted under the rebooted protocol either. Its exact upstream fix
passes the preservation-strengthened oracle and all 125 upstream tests, but
the frozen bare Pi plus Gemma probe recorded 0/4. Two invocations retained
partial patches and neither passed the five-case oracle. An earlier two-case
probe was superseded after review found a parameter-name loophole. This is a
valid floor result, not a comparison with an Envelope or Engine arm. See the
[`stringified-annotations` baseline probe](docs/superpowers/research/2026-08-29-stringified-annotations-baseline-probe.md).

## Backlog

Deferred, each with the condition that reopens it — see `BRIEF.md`:
automated commit mining (after three manual captures show which steps
repeat); paired A/B of two engine versions (when a contributor needs "did
my fix help" across versions); resumable large batches (only if the prior
checkpoint transplants verbatim); the whole claims layer.

## Prior work

Completed phases move here (or to `docs/superpowers/phase-history.md`)
when the roadmap outgrows the front page.

- **V4 — A real engine attempt (2026-08-23).** Evals reconstructs a private
  Git repository from the persisted task base, runs the executable once in a
  detached worktree, preserves its artifacts before cleanup, and proves the
  seam with a real Engine E5 attempt.
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
