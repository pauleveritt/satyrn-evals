# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**V4 is complete. V5a — the admission rule — is next.**

Four tasks have now been probed and none admitted: `local-pings`,
`stringified-annotations`, `magicmock-factory`, and a multi-prompt `svcs`
session. **No probed task has a bare-Pi baseline in the middle band.** But two
of them do discriminate between arms — `local-pings` records Engine 2/4 against
Baseline 0/4 (see the Phases note below), and `stringified-annotations` records
Engine 6/6 against Baseline 0/6 in the
[product-path pilot](docs/superpowers/research/2026-08-26-product-path-pilot.md).

That gap is the thing to settle before more probing, and it is a decision, not
a measurement: **is the admission bar "middle-band for bare Pi", or
"discriminates between the arms under comparison"?** Under the first, four
rigorously qualified tasks are discarded. Under the second, at least two are
admissible today. `BRIEF.md`'s middle-band rule assumes the first without
saying which arm is the baseline, and that ambiguity now blocks the diagnostic
loop.

V5 is therefore split: **V5a** decides the rule and indexes the suite with no
model runs at all; **V5b** is the run-and-summarize loop, sequenced by what
V5a admits. See the Phases table below and `BRIEF.md` for the binding rules.

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

| # | Phase | Direction (one sentence) | Excludes | Status |
|---|-------|--------------------------|----------|--------|
| V1 | It installs and grades | `grade` accepts a bundled task's known-good patch and rejects its known-broken one, offline and deterministic | Capture, attempt, the claims layer | **complete** |
| V2 | Capture by revert | `capture --revert SHA` makes a task winnable by construction, in minutes | Environment materialization, baseline probes, commit mining, a sandbox, Windows | **complete** |
| V3 | Attempt persistence | `attempt TASK -- COMMAND...` runs a fake command, persists patch and transcript, regrades offline | The real engine seam (V4), the diagnostic loop, transcript format, retry, repair | **complete** |
| V4 | A real engine attempt | Reconstruct an isolated Git workspace and produce the V3 artifact set with `satyrn-engine attempt` | Model-quality claims, admission, repeated attempts, A/B (V5); containment; Windows | **complete** |
| V5a | The admission rule | decide and record which arm the middle-band bar applies to, then index every probed task with its band per arm; no model runs | Model runs, the diagnostic loop (V5b), the claims layer | **next** |
| V6 | Session eval | `session TASK -- ADAPTER...` sends ordered prompts to one conversation against one evolving checkout, snapshots a cumulative patch per checkpoint, and grades offline through a grader overlay the executor is never shown | `run --n 8` and admission, model-client integration, retries, a hostile-command sandbox, a persistent Engine daemon | proposed |
| V7 | Task visibility and leak detection | a manifest field declares each task visible- or hidden-oracle; contamination is detected by content and reported per arm, never absorbed into a denominator | OS-level containment — deferred in `BACKLOG.md`; V7 detects rather than prevents | proposed |
| V8 | AgentClinic through Evals | reproduce the repair fixtures on this repository's own `capture`/`attempt`/`grade` path, replacing the spike's scratchpad harness | Engine changes, including a `facts` field (satyrn-engine `BACKLOG.md`); an orchestrator | proposed |
| V5b | The diagnostic loop | `run --n 8` over admitted tasks, summarizing verdict reasons, repeated calls, churn, tool calls, context, and timeouts | The claims layer — pre-registration, intervals, void accounting (`BRIEF.md:33-36`) | blocked on V5a |

Full done-when criteria for V1–V5 are in `BRIEF.md`'s referenced roadmap
research, not restated here to avoid drift between two copies. **V5a and
V6–V8 are new and their done-when lives with each phase's design spec** —
V6's is `docs/superpowers/specs/2026-09-01-svcs-session-eval-design.md`
(superseded banner; the design of record for the session mechanics). V5a, V7
and V8 have no spec yet and must gain one before implementation, per
`docs/sdd.md`.

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

## Backlog

Moved to [`BACKLOG.md`](BACKLOG.md), so the phase list stays readable. Every
entry there states what reopens it.

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
