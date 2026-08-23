# Satyrn Evals

**Captures a Python-development task, invokes an attempt command, preserves
what happened, and grades the result offline.**

Evals is the measurement half of the two-repo satyrn effort: the engine
delivers a candidate change for a task, and evals captures real
Python-development workflows, runs an attempt command against each, and
grades what happened offline. Small models fail in predictable ways — they
lose their place, edit the wrong file, drift from the task — and the
failure reasons and thrashing evals summarizes are the evidence engine
fixes are built on. The features built into the engine are the ones that
evidence surfaces.

Its only seam into the engine is an executable {term}`attempt command`, run
inside an eval-owned disposable workspace with task, contract, patch, and
transcript paths supplied through environment variables. Evals never imports engine internals; a fake command
satisfies the same seam, and V4 runs `satyrn-engine attempt` in that same
slot — so eval development never waits for the real engine.

## Status

Phases completed, each with its design spec and implementation plan:

- **V3 — Attempt persistence.** `attempt TASK -- COMMAND...` runs the seam,
  preserves patch and transcript, and grades the preserved patch offline.
- **V2 — Capture by revert.** `capture --revert SHA` creates a verified task
  from a fixing commit.
- [_V1_](https://github.com/pauleveritt/satyrn-evals/tree/v1) — it
  installs and grades. `satyrn-evals grade TASK PATCH [--receipt PATH]`
  accepts a bundled task's known-good patch and rejects its known-broken
  one, offline and deterministic. ({doc}`spec <superpowers/specs/2026-08-16-v1-grade-design>`, {doc}`plan <superpowers/plans/2026-08-16-v1-grade>`)

The next eval phase is **V4 — A real engine attempt**, after engine E5; the roadmap of feature
cycles lives in [`ROADMAP.md`](https://github.com/pauleveritt/satyrn-evals/blob/main/ROADMAP.md). The `e1` git tag holds the
scaffolded starting state — toolchain, docs stack, CI, the brief, the
roadmap, and the harvest index — for learners following along step by
step.

## What is Satyrn Evals?

### The big picture

Evals is how the engine gets built on evidence instead of guesses. The
loop:

1. **Capture** — a real Python-development workflow becomes a {term}`task`:
   manifest, base state, and a known-good fixture patch.
2. **Attempt** — the task's {term}`attempt command` runs in an eval-owned
   disposable worktree; its patch and transcript are preserved before
   cleanup.
3. **Grade** — grading reads only those preserved artifacts and records an
   offline {term}`verdict` {term}`receipt` — no model, no network.
4. **Diagnose** — a run of n=8 plus a summary: verdict reasons, repeated
   calls, churn, tool calls, context, timeouts.
5. **Fix and re-measure** — the summary names what broke and where; the
   engine gets fixed; the suite re-runs. Each task carries a
   {term}`baseline probe`, recorded once, so a later run shows whether the
   fix moved it.

The summary is diagnostic, not statistical: it counts failure reasons and
thrashing, and never compares wall-clock time between adjacent runs. It is
only informative on tasks whose baseline can move — a suite with headroom
is design work this project still owes. And the claims layer —
pre-registration, confidence intervals, A/B publication — is deferred until
a consumer needs it.

### How it works, from an end-user's perspective

The CLI now has `grade`, `capture`, and `attempt`. `grade` applies a patch to
the task's base state, runs the task's
{term}`oracle`, and writes a {term}`receipt` whose {term}`verdict` —
`pass`, `fail`, or `unavailable` — never comes from stdout or an exit code.

The road ahead: `capture --revert SHA` makes a task winnable by
construction in minutes; `attempt TASK -- COMMAND...` runs the seam and
preserves patch and transcript; `run --n 8` produces the diagnostic
summary. The engine enters as a command — `satyrn-engine attempt` — in the
same slot a fake command occupies today.

### What is planned

One phase at a time, each shipping one user-visible behavior:

- **V1 — It installs and grades.** `grade` applies a patch to a bundled
  task and records an offline verdict receipt. *Complete.*
- **V2 — Capture by revert.** `capture --revert SHA` makes a task winnable
  by construction, in minutes. *Complete.*
- **V3 — Attempt persistence.** `attempt TASK -- COMMAND...` runs a fake
  command, persists patch and transcript, regrades offline. *Complete.*
- **V4 — A real engine attempt.** The same artifact set, produced by
  `satyrn-engine attempt` (engine phase E5). *Waiting for E5.*
- **V5 — The diagnostic loop.** `run --n 8` plus a summary: verdict
  reasons, repeated calls, churn, tool calls, context, timeouts.
  *Not started.*

The roadmap, concept budget, and backlog live in
[`ROADMAP.md`](https://github.com/pauleveritt/satyrn-evals/blob/main/ROADMAP.md)
at the repository root; the mission and status live in the README.

See {doc}`usage` for the command in detail and {doc}`architecture` for the
shape of the machinery.

```{toctree}
:maxdepth: 1
:caption: Usage

usage
glossary
```

```{toctree}
:maxdepth: 1
:caption: Development

architecture
contributing
sdd
superpowers/index
```
