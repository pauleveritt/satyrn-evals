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

| # | Phase | Direction (one sentence) | Status |
|---|-------|--------------------------|--------|
| V1 | It installs and grades | `grade` accepts a bundled task's known-good patch and rejects its known-broken one, offline and deterministic | **complete** |
| V2 | Capture by revert | `capture --revert SHA` makes a task winnable by construction, in minutes | **complete** |
| V3 | Attempt persistence | `attempt TASK -- COMMAND...` runs a fake command, persists patch and transcript, regrades offline | **complete** |
| V4 | A real engine attempt | Reconstruct an isolated Git workspace and produce the V3 artifact set with `satyrn-engine attempt` | **complete** |
| V5a | The admission rule | decide and record which arm the middle-band bar applies to, then index every probed task with its band per arm; no model runs | **next** |
| V6 | Session eval | `session TASK -- ADAPTER...` sends ordered prompts to one conversation against one evolving checkout, snapshots a cumulative patch per checkpoint, and grades offline through a grader overlay the executor is never shown | proposed |
| V7 | Task visibility and leak detection | a manifest field declares each task visible- or hidden-oracle; contamination is detected by content and reported per arm, never absorbed into a denominator | proposed |
| V8 | AgentClinic through Evals | reproduce the repair fixtures on this repository's own `capture`/`attempt`/`grade` path, replacing the spike's scratchpad harness | proposed |
| V5b | The diagnostic loop | `run --n 8` over admitted tasks, summarizing verdict reasons, repeated calls, churn, tool calls, context, and timeouts | blocked on V5a |

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

Deferred, each with the condition that reopens it — see `BRIEF.md`:
automated commit mining (after three manual captures show which steps
repeat); paired A/B of two engine versions (when a contributor needs "did
my fix help" across versions); resumable large batches (only if the prior
checkpoint transplants verbatim); the whole claims layer.

**OS-level containment for the attempt** (reopens when all four recorded
blockers are cleared, or when detection proves insufficient in practice). A
whole-process sandbox profile was built and measured during the 2026-09-01
spike and is **deferred, not adopted**: it is macOS-only; it silently removed
the model's own test runner, so an entire block measured models that could not
self-verify; a hard link created inside the run root still read the grader
through it; and it conflicts with V4's absolute external engine-contract path
— though the V6 design already routes around that last one by copying a public
contract into the worktree rather than referencing it by task path. V7 uses
after-the-fact content detection instead. *Recorded direction change:* an
earlier note in this planning cycle said "make containment genuinely usable,
including a test runner"; this entry defers it rather than fixing it, and a
still earlier draft wrote "refused" where the evidence only supports
"deferred".

**Cheap partial prevention** (reopens with V7): POSIX file modes and a separate
run user need no new system, and V7 should require one of them for any task
declaring a hidden oracle rather than relying on detection alone.

**Text-contract support** (reopens when a roster model cannot emit tool calls —
two of six models measured in the spike could not, so this is when, not if);
**writable-scope injection** (reopens if scope overreach is measured here);
**an orchestrator process** (remains unjustified — every effect measured so far
was obtained without one, and autonomous contract authoring measured worse than
hand authoring).

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
