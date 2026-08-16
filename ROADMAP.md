# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**Repository scaffolding — complete.** The toolchain, docs stack, CI, and
superpowers structure are initialized. `BRIEF.md` is landed.

**Phase V1 — It installs and grades. Not started; the current phase.**
`satyrn-evals grade TASK PATCH`. See the Phases table below and
`BRIEF.md` for the binding rules, especially the two selection rules for
V1's bundled task and the baseline probe. Brainstorm V1's details; do not
reopen the phase list or the diagnosis-before-claims split — both are
settled, cited in `docs/superpowers/research/2026-08-16-harvest-index.md`.

## Concept budget

*Every term below is a cost against a 5–10 h/wk volunteer's ability to hold
the design in mind. Checked and updated at the end of each cycle; a term
earns its place by naming something the design actually needs, not by being
convenient shorthand.*

Seed terms, not yet defined in this repository's own words — define each
when the phase that needs it lands: **task**, **oracle**, **preservation**,
**baseline probe**, **attempt command**, **verdict**.

## Phases

| # | Phase | Direction (one sentence) | Status |
|---|-------|--------------------------|--------|
| V1 | It installs and grades | `grade` accepts a bundled task's known-good patch and rejects its known-broken one, offline and deterministic | **current** |
| V2 | Capture by revert | `capture --revert SHA` makes a task winnable by construction, in minutes | not started |
| V3 | Attempt persistence | `attempt TASK -- COMMAND...` runs a fake command, persists patch and transcript, regrades offline | not started |
| V4 | A real engine attempt | The same artifact set, produced by `satyrn-engine attempt` (engine phase E5) | not started |
| V5 | The diagnostic loop | `run --n 8` plus a summary: verdict reasons, repeated calls, churn, tool calls, context, timeouts | not started |

Full done-when criteria are in `BRIEF.md`'s referenced roadmap research, not
restated here to avoid drift between two copies.

**Design work owed, not a phase:** a suite with headroom. See `BRIEF.md`'s
"The unsolved problem." V5's summary is only informative on tasks whose
baseline can move, and nothing here reliably produces those yet.

## Backlog

Deferred, each with the condition that reopens it — see `BRIEF.md`:
automated commit mining (after three manual captures show which steps
repeat); paired A/B of two engine versions (when a contributor needs "did
my fix help" across versions); resumable large batches (only if the prior
checkpoint transplants verbatim); the whole claims layer.

## Prior work

Completed phases move here (or to `docs/superpowers/phase-history.md`)
when the roadmap outgrows the front page. Nothing here yet.

## Workflow

This repository runs on spec-driven development — see
[`docs/sdd.md`](docs/sdd.md). Each feature cycle gets a committed design
spec, an implementation plan, then code. The default test suite needs no
model, network, or subprocess; process behavior lives in a small marked
integration tier.
