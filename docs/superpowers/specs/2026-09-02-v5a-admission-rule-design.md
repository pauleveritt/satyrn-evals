# V5a — The admission rule: design spec

**Phase:** V5a (`ROADMAP.md:60`). **Date:** 2026-09-02.
**Status:** decision recorded; proposal posted for confirmation per
`CLAUDE.md`. No code follows until the proposal is confirmed; no model has
run.

## What V5a ships (and the proposal template)

V5a is a documentation phase: it ships the recorded decision, the `BRIEF.md`
amendment, and the per-arm index in the section below. Per `CLAUDE.md`'s
proposal template, stated explicitly:

- **CLI surface:** none. No command is added or changed.
- **Exit codes:** none. No executable is added or changed.
- **Data shapes:** no code-level schema. The durable data shape is the index
table above — task × arm × (successful attempts, retained patches, conditional
quality, band) — plus the amended rule text in `BRIEF.md` and the glossary.
- **Test layout:** no tests are added. Verification is `just lint-docs` and
the existing default tier (`uv run pytest -q`, no model/network/subprocess).
The planted process-spawning tripwire is untouched.

No model runs at all in this phase.

## Question

`ROADMAP.md:15-21` names four probed tasks — `local-pings`,
`stringified-annotations`, `magicmock-factory`, and a multi-prompt `svcs`
session — and states "**No probed task has a bare-Pi baseline in the middle
band.**" Two do discriminate between arms: `local-pings` records Engine 2/4
against Baseline 0/4, and `stringified-annotations` records Engine 6/6
against Baseline 0/6.

`ROADMAP.md:24-29` then poses the decision this phase must record:

> is the admission bar "middle-band for bare Pi", or "discriminates between
> the arms under comparison"? Under the first, four rigorously qualified tasks
> are discarded. Under the second, at least two are admissible today.
> `BRIEF.md`'s middle-band rule assumes the first without saying which arm is
> the baseline, and that ambiguity now blocks the diagnostic loop.

`BRIEF.md:110-121` now carries the amended rule. The superseded wording,
preserved in the recorded amendment note at `BRIEF.md:123-131`, read:

> **A diagnostic workload** must be able to show a difference. It requires a
> **baseline probe** — the baseline attempt command at n=4–6, recorded once as a
> property of the task. A task at or near ceiling is smoke only. A task at the
> floor is a capability wall, not something an engine change moves. Diagnosis
> lives in between.

The roadmap's own design-work note adds the operative requirement
(`ROADMAP.md:75-84`): a baseline probe "must show that the task has room to
move," and admission "must keep successful attempt outcomes, retained patch
production, and the conditional quality of retained patches separate rather
than choosing a metric after seeing the result."

## The corrected probes falsified the floor sentence

The superseded floor claim (preserved at `BRIEF.md:125-126`) said a task at
the floor "is a capability wall, not something an engine change moves." This
repo's own records falsify that for the two tasks that discriminate:

- The corrected `local-pings` probe fixed its primary metric before the run
  and recorded **0/4 successful attempts** at n=4
  (`2026-08-27-local-pings-corrected-probe.md:11-13`). It then separated the
  three measurements: successful attempt outcome **0/4**, retained patch
  production **2/4**, conditional retained patch quality **2/2** passing the
  corrected four-test oracle and five fresh 89-test preservation runs
  (`2026-08-27-local-pings-corrected-probe.md:15-23`, preservation rows
  `:128-130`). The floor was a **completion floor** — bare Pi constructed
  the change but could not finish a successful attempt under its own tool
  loop (`2026-08-27-local-pings-corrected-probe.md:140-143`).
- The follow-up then recorded the Envelope/Engine comparison on the same
  task (`2026-08-27-local-pings-envelope-engine-followup.md:44-46`): Baseline
  0/4, Envelope 0/4, **Engine 2/4** — an engine change moved the floored task.
- The three-arm pilot recorded `stringified-annotations` Baseline 0/6,
  Envelope 0/6, **Engine 6/6** with byte-identical patches
  (`2026-08-26-product-path-pilot.md:83-85`, `:113-117`).

A 0/4 or 0/6 baseline is therefore not by itself a wall: the middle-band
sentence conflated **successful attempt outcome** (what it measured) with
**capability** (what it concluded). The harvest index records the same lesson
(`2026-08-16-harvest-index.md:158-163`): "Attempt completion, retained-patch
production, and the conditional quality of retained patches are different
measurements; record them before running if they matter, and never switch the
admission metric after seeing the result."

## The decision

**The middle-band bar applies to the arms under comparison, not to the
bare-Pi arm alone.** Operationally:

1. A task is admissible when its qualifying probe records the arms under
   comparison at **different successful-attempt bands** — the recorded
   difference is what the diagnostic loop has to move
   (`BRIEF.md:110`; `ROADMAP.md:78`).
2. The **reference arm (bare Pi) stays the recorded baseline property**, per
   `BRIEF.md:111-112` and the glossary. It is the arm the loop moves *from*;
   its band never admits or refuses on its own — a floor reference can be a
   completion floor an arm under comparison moves, and a ceiling reference is
   refused only because no arm under comparison can be recorded above it, so
   discrimination is impossible (point 4).
3. **Floor and ceiling are classified per arm from the three separate
   measurements**, with the successful-attempt metric and stopping rule fixed
   before the run (`2026-08-27-local-pings-corrected-probe.md:11-13`, `:80`).
   A successful-attempt floor is a capability wall only when no arm under
   comparison is recorded above it **and** no retained patch passes a
   preservation-safe oracle. A completion floor — retained patches pass — is
   admissible when a product arm under comparison is recorded above it.
4. **Smoke is refused**: a task whose reference arm sits at or near ceiling
   has nothing for an engine change to move and admits nothing. None of the
   four probed tasks is in that band.
5. **Never choose the admission metric after the result**
   (`ROADMAP.md:84`; `2026-08-16-harvest-index.md:161-162`). The probe's
   pre-registered primary metric is the band metric; retained-patch and
   conditional-quality results are recorded per arm, never substituted.

Consequences for the four probed tasks: **`local-pings` and
`stringified-annotations` are admissible today**; `magicmock-factory` and the
multi-prompt `svcs` session are not (each for a recorded reason below).

### Why not the first reading

The bare-Pi-middle-band reading requires a task's unaided baseline to sit
between floor and ceiling. Every probed task fails that — all four baselines
are at or near the floor. The reading therefore discards the two tasks whose
recorded arms separate, on the superseded sentence (`BRIEF.md:125-126`) this
repo's own corrected probes falsified (above), and leaves V5b with an empty
suite: the diagnostic loop cannot start (`ROADMAP.md:28-29`). Its "floor is a
wall" premise also collapses the three measurements the corrected probe was
built to separate (`2026-08-27-local-pings-corrected-probe.md:18-23`).

## Index: every probed task, band per arm

Bands below are per arm on that arm's own recorded successful-attempt
outcome, from each probe's frozen conditions, with retained-patch production
and conditional quality recorded separately and never merged. Tools, oracle
strength, and deadlines differ between tasks and between records; the bands
are not comparable across tasks.

### local-pings (corrected task)

Records: corrected probe (`2026-08-27-local-pings-corrected-probe.md`) and
Envelope/Engine follow-up (`2026-08-27-local-pings-envelope-engine-followup.md`).

| Arm | Successful attempts | Retained patches | Conditional quality | Band |
| --- | ---: | ---: | ---: | --- |
| Baseline (bare Pi) | 0/4 | 2/4 | 2/2 pass | floor (completion) |
| Envelope (budget-only variant) | 0/4 | 1/4 | 0/1 pass | floor |
| Engine composite | 2/4 | 3/4 | 2/3 pass | middle |

Primary table: `2026-08-27-local-pings-envelope-engine-followup.md:44-46`;
retained audit `:62-64`; Baseline 0/4 from the corrected probe
(`2026-08-27-local-pings-corrected-probe.md:11-13`, attempt rows `:103-106`).
The follow-up's Envelope is a budget-only variant of the same
`read,bash,edit,write` surface, not the canonical read/write Envelope
(`2026-08-27-local-pings-envelope-engine-followup.md:24-27`).

**Verdict: admissible.** Baseline floor (with 2/2 constructible retained
quality) vs Engine middle discriminates; the corrected probe's oracle is
preservation-safe (`2026-08-27-local-pings-corrected-probe.md:128-130`). The
corrected probe and follow-up each concluded "do not admit" under the first
reading — the follow-up's own words: "the binding V5 rule asks for a
preservation-safe task whose successful-attempt Baseline is between floor
and ceiling" (`2026-08-27-local-pings-envelope-engine-followup.md:94-96`).
This decision records that reading as superseded, so those verdicts do not
carry forward.

### stringified-annotations

Record: product-path pilot (`2026-08-26-product-path-pilot.md`), three arms,
n=6 each (`:57`), tools `read`, `edit` (`:62`).

| Arm | Successful attempts | Retained patches | Conditional quality | Band |
| --- | ---: | ---: | ---: | --- |
| Baseline (bare Pi) | 0/6 | none reported | — | floor |
| Envelope (budget extension) | 0/6 | none (6 `NO_PATCH`) | — | floor |
| Engine (contract + bounded tools) | 6/6 | 6/6 | byte-identical (`:113-117`) | ceiling |

`2026-08-26-product-path-pilot.md:83-85`. The baseline floor was a
tool-discovery/completion wall for bare Pi (`:95-98`) that the Engine arm
moved to ceiling; the pilot's single byte-identical patch later regraded
125/125 under the strengthened oracle
(`2026-09-02-phase-proposals-and-session-eval-convergence.md:190-193`).

**Verdict: admissible.** Baseline floor vs Engine ceiling discriminates. The
Engine arm sits at ceiling, so within V5b this task functions as product
demonstration and regression detection, not improvement headroom — the pilot
itself used it that way and, applying the first reading, called it "not an
admissible V5 diagnostic workload under `BRIEF.md`'s middle-band rule"
(`2026-08-26-product-path-pilot.md:159-161`). That verdict is superseded by
this decision; the recorded arms are the admission evidence.

### magicmock-factory (final task)

Record: final probe (`2026-08-29-magicmock-factory-baseline-probe.md`). Only
the bare-Pi arm was run (`:84`).

| Arm | Successful attempts | Retained patches | Conditional quality | Band |
| --- | ---: | ---: | ---: | --- |
| Baseline (bare Pi) | 0/4 | 3/4 | 0/3 pass | floor |

`2026-08-29-magicmock-factory-baseline-probe.md:12-13` and attempt rows
`:105-108`. All four attempts timed out; no Envelope or Engine arm has ever
been recorded for this task, and the task is not captured on disk
(`2026-09-02-phase-proposals-and-session-eval-convergence.md:197-199`: no
`manifest.json`/`base/`/`fixtures/` under `~/.satyrn-authoring/`).

**Verdict: not admissible today — evidence gap, not a wall verdict.** No arm
under comparison exists in the record, so discrimination is unestablished.
Reopens when an Envelope/Engine-arm probe at n=4–6 records a band above the
floor (the phase-proposals E2 generalization-test thread,
`2026-09-02-phase-proposals-and-session-eval-convergence.md:188-195`).

### Multi-prompt svcs session

Record: `2026-09-01-svcs-autowire-session-probe.md`, currently only on
`origin/svcs-session-eval-design` (PR #17) and in a local worktree
(`2026-09-02-phase-proposals-and-session-eval-convergence.md:13-17`).

| Arm | Primary measurement | Result | Band |
| --- | --- | ---: | --- |
| Baseline (bare Pi session, six prompts) | deepest milestone of five | 1, 0, 0, 0 | floor/wall |
| Remediation screens (read-only enumeration; bounded-anchor feedback; optional public check; runner-owned preservation check) | deepest milestone of five | 0,0,0,0 / 1,0,0,0 / 0,0,0,0 / 0,0,0,0 | floor |

Baseline table rows and retained-patch note:
`2026-09-01-svcs-autowire-session-probe.md:80-85`; remediation results
`:105-107` (branch-local). Its own record calls the baseline "a useful
capability wall, not a V5 middle-band workload" (`:12-14`) and says the suite
is "intentionally not admitted to V5 yet" (`:146-149`).

**Verdict: not admissible to V5b.** Session-shaped workload requiring V6
`session` machinery (`ROADMAP.md:61`), wall on every recorded variant, and no
arm under comparison on the evals path. Its admission question reopens with
V6.

## What this means for V5b

V5b (`ROADMAP.md:64`) runs `--n 8` over admitted tasks and summarizes verdict
reasons, repeated calls, churn, tool calls, context, and timeouts. Admission
is the gate that keeps that summary informative. The index records each
admitted task's band per arm so V5b can sequence runs: `local-pings` offers
Engine improvement headroom (middle band, mixed verdict reasons in the
follow-up); `stringified-annotations` offers product demonstration and
regression detection (Engine at ceiling).

## BRIEF.md amendment

`BRIEF.md:110-121` is amended to record this decision; the old wording is
kept in the amendment note rather than edited away (see the `BRIEF.md`
diff). The operative text becomes:

> A diagnostic workload must be able to show a difference between the arms
> under comparison. It requires a baseline probe — the baseline attempt
> command at n=4–6, recorded once as a property of the task. The middle-band
> bar applies to the arms under comparison, not to the reference arm alone:
> a task is admissible when its probe records those arms in different
> successful-attempt bands, with the metric and stopping rule fixed before
> the run and successful-attempt outcome, retained-patch production, and
> conditional retained-patch quality kept separate. A task is smoke only when
> its reference arm sits at or near ceiling. A task at the floor is a
> capability wall only when no arm under comparison is recorded above it
> and no retained patch passes a preservation-safe oracle; a completion floor
> whose retained patches pass is what an engine change exists to move.

The glossary entries for `baseline probe` and `diagnostic workload`
(`docs/glossary.md:50-66`) are updated to match, with the superseded wording
kept in a note.

## Out of scope (deferred, with the phase that reopens each)

- Model runs of any kind. *V5b and every later probe.*
- The diagnostic loop itself — `run --n 8`, summary formats, sequencing
  admitted tasks by their per-arm bands. *V5b.*
- The claims layer — pre-registration, intervals, void accounting, A/B
  publication. *A later consumer, per `BRIEF.md:33-36` and `BACKLOG.md`.*
- A `magicmock-factory` Envelope/Engine-arm probe. The task is not captured
  on disk, so capture and the two-stage oracle reconstruction come first
  (`2026-09-02-phase-proposals-and-session-eval-convergence.md:197-199`).
  *V5b-era probing / the phase-proposals E2 generalization test (`:188-195`).*
- The svcs session suite, its V6 `session` machinery, and its admission rule.
  *V6 (`ROADMAP.md:61`).*
- Near-ceiling boundary calibration. No probed task sits there; the follow-up
  left "the agreed near-ceiling boundary" undefined
  (`2026-08-27-local-pings-envelope-engine-followup.md:101-103`). *Reopens
  when a probe records an arm at n−1/n or when V5b sequencing needs it.*
- The suite-with-headroom design work and any new task capture
  (`BRIEF.md:140-144`). *Reopens with V5b suite search and later workload
  phases (V6, V8).*

The phase-table Excludes cell for V5a (`ROADMAP.md:60`) condenses this
section and is reconciled against it.

## Done-when for V5a

- This spec records which arm the middle-band bar applies to (the arms under
  comparison) and why; `BRIEF.md` carries the amendment with the old wording
  kept in a note.
- Every probed task is indexed with its band per arm: `local-pings`
  (Baseline floor / Envelope floor / Engine middle), `stringified-annotations`
  (Baseline floor / Envelope floor / Engine ceiling), `magicmock-factory`
  (Baseline floor, no other arm recorded), svcs session (wall on every
  recorded variant).
- The proposal is posted and confirmed before any code follows
  (`CLAUDE.md`); no model has run.

## Evidence and recomputation

Every count above is cited to its record at the time of writing. The probe
records carry recomputation commands over local evidence bundles, each with a
SHA-256 (verify from the adjacent `.sha256`, then rerun the record's own
`analyze.py`/`recompute.py`):

- corrected probe: `2026-08-27-local-pings-corrected-probe.md` —
  `2feb305fb70c74e06fef80a0f34aa69ad20d54c95e883f8ae2d7e7a41d622386`;
- Envelope/Engine follow-up:
  `2026-08-27-local-pings-envelope-engine-followup.md` —
  `3d99a31b2da56076cdfcf52650b605e9b7a6ca202c7594e38f82740ff67825ff`;
- product-path pilot: `2026-08-26-product-path-pilot.md` (local bundle);
- magicmock final probe: `2026-08-29-magicmock-factory-baseline-probe.md` —
  `8405b27543230078cca7375e39d8b63038353aa5012f6951f4bf28247c083b27`;
- svcs session probe: branch-local at `origin/svcs-session-eval-design`,
  evidence under
  `/Users/koudai/work/satyrn/evidence/svcs-autowire-session-20260901`.

Each archive is local evidence, not a repository or CI dependency.
