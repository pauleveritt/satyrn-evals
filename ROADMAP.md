# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**V5d is complete (2026-09-03). V6 — session eval — is proposed next for
runtime work. D1 — documentation orientation — is active in parallel.**
V5d landed the pre-flight smoke check as a confirmed, documented practice
— one uncounted real-model smoke per materially distinct execution path,
at that path's first real use. V6's approved delta design is
`docs/superpowers/specs/2026-09-03-v6-session-eval-design.md`; its
implementation plan follows maintainer spec review.

V5c captured the admitted suite's first task: `local-pings` exists as a
bundled task with the `format_number` shape (manifest, `base/`, known-good
and known-broken fixtures, engine contract) whose oracle is the five ids —
three upstream local-ping tests plus the two-order curator preservation
parametrization (`[order0]`/`[order1]`). Row 3's adversary was re-specified
mid-phase (maintainer-confirmed amendment): the recorded N=2 type-set does
not reproduce on this machine, and the cross-machine investigation showed
the set-order catch is a discrete function of hash stride versus table
geometry and allocation phase, not a stateable probability — so the fixture
scales to six registry services and the gate carries a canary with a third
outcome (inconclusive) that stops capture rather than silently passing.
**Close-out (2026-09-03).** The captured-task re-probe ran V5b's `run` at
n=8 on the Baseline (bare Pi) and Engine arms and recorded both arms
middle — Baseline 3/8, Engine 4/8
([results](docs/superpowers/research/2026-09-03-local-pings-reprobe-protocol.md)) —
so the task does not satisfy V5a's requirement that a compared pair occupy
different bands and was **de-admitted as a diagnostic workload**
([record](docs/superpowers/research/2026-09-03-local-pings-deadmission.md)).
It remains a valid bundled grader/smoke/regression fixture.
`stringified-annotations` capture is **reopened for proposal** — its
trigger, the local-pings diagnostic run, has occurred (`BACKLOG.md`).

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
| V5a | The admission rule | decide and record which arm the middle-band bar applies to, then index every probed task with its band per arm; no model runs | Model runs, the diagnostic loop (V5b), the claims layer, an Envelope/Engine-arm probe of `magicmock-factory`, the svcs session suite (V6), near-ceiling boundary calibration, suite-headroom capture — see the spec's Out of scope | **complete** |
| V5b | The diagnostic loop | `run --n 8` over admitted tasks, summarizing verdict reasons, repeated calls, churn, tool calls, context, and timeouts | The claims layer — pre-registration, intervals, void accounting (`BRIEF.md:33-36`) | **complete** |
| V5c | Capture the admitted suite | reconstruct and `capture --revert` the corrected `local-pings` synthetic pair, then re-record the probe's three-row qualification table as the gate that the capture is faithful | `stringified-annotations` capture (reopens once the loop runs on `local-pings`); `magicmock-factory` (reopens with an Envelope/Engine probe); oracle improvement (its own proposal); running the loop; suite-headroom capture — see the spec's Out of scope | **complete** |
| V5d | The pre-flight smoke check | run one real-model attempt (`run TASK --n 1`) against each materially distinct command/adapter/runtime path before that path's first budgeted diagnostic run, and read the attempt record — plus the receipt when grading ran — against a short pass/fail checklist; `NO_PATCH`/`COMMAND_TIMEOUT` pass only with positive evidence the model started | automated engine-contract content validation (`BACKLOG.md`); the `pi` argv incompatibility itself (satyrn-engine's backlog); running smoke in CI or any test tier; a manifest smoke-record field; `local-pings` re-admission or new prospective read/write Envelope decisions — see the spec's Out of scope | **complete** |
| D1 | Documentation orientation | adopt a Diátaxis structure that reveals Satyrn Evals from a successful first verdict to task capture, attempts, diagnostics, and the design record; place a small concrete suite example—code, pseudocode, or drawing—immediately before the exact command that runs it on the top-level page | CLI or task behavior; V6 operational docs; model-quality/claims-layer guidance; rewriting historical evidence — see the design spec's Out of scope | **active** — reopened 2026-09-04 for review corrections and the suite example; [design](docs/superpowers/specs/2026-09-04-d1-diataxis-documentation-design.md), [plan](docs/superpowers/plans/2026-09-04-d1-diataxis-documentation.md) |
| D2 | The learner's big picture | teach what actually happens when an AI coding agent works — agent, tools, inference server, model — in one lo-fi diagram and a short page placed after the first verdict, then map those pieces onto Evals' evidence loop in a second diagram; zero runtime JavaScript | animation; client-side rendering runtimes; theme-coupled SVG colors; serving ops detail; Satyrn boxes in diagram 1; more learner pages beyond the two — see the design spec's Out of scope | **complete** — learner page placed after the first verdict teaches what actually happens when an agent works (agent ↔ codebase + tools → inference server containing the model), then maps those pieces onto Evals' evidence loop (the attempt command as the opaque agent loop → patch + transcript → offline grade → receipt); two d2-rendered committed SVGs, zero runtime JavaScript — [design](docs/superpowers/specs/2026-09-04-d2-learner-big-picture-design.md), [plan](docs/superpowers/plans/2026-09-04-d2-learner-big-picture.md) |
| V6 | Session eval | `session TASK -- ADAPTER...` sends ordered prompts to one conversation against one evolving checkout, snapshots a cumulative patch per checkpoint, and grades offline through a grader overlay the executor is never shown | `run --n 8` and admission, model-client integration, retries, a hostile-command sandbox, a persistent Engine daemon | proposed |
| V7 | Task visibility and leak detection | a manifest field declares each task visible- or hidden-oracle; contamination is detected by content and reported per arm, never absorbed into a denominator | OS-level containment — deferred in `BACKLOG.md`; V7 detects rather than prevents | proposed |
| V8 | AgentClinic through Evals | reproduce the repair fixtures on this repository's own `capture`/`attempt`/`grade` path, replacing the spike's scratchpad harness | Engine changes, including a `facts` field (satyrn-engine `BACKLOG.md`); an orchestrator | proposed |

Full done-when criteria for V1–V5 are in `BRIEF.md`'s referenced roadmap
research, not restated here to avoid drift between two copies. **V6–V8 are
new and their done-when lives with each phase's design spec** — V6's is
`docs/superpowers/specs/2026-09-01-svcs-session-eval-design.md`
(superseded banner; the design of record for the session mechanics),
as amended by `docs/superpowers/specs/2026-09-03-v6-session-eval-design.md`
(the V6 delta spec: slice-5 replacement, the session fixture, the proof
ladder, and the smoke done-when).
V5c's done-when is its three-row qualification gate in
`docs/superpowers/specs/2026-09-02-v5c-capture-admitted-suite-design.md`
(complete — see Prior work below).
V5d's done-when is its practice being referenced from `BACKLOG.md` and
confirmed by the maintainer, in
`docs/superpowers/specs/2026-09-03-v5d-preflight-smoke-check-design.md`
(complete — confirmed by the maintainer and landed 2026-09-03. The next
task captured after `local-pings` must follow the practice; a captured
task that reaches a budgeted run without its smoke, or a smoke that
conceals a defect, reopens V5d).
V7 and V8 have no spec yet and must gain one before implementation, per
`docs/sdd.md`; V5a's and V5b's done-when lived with their design specs, now
complete (Prior work below).

**Design work owed, not a phase:** a suite with headroom. See `BRIEF.md`'s
"The unsolved problem." The admission rule keeps the operative measurement
discipline: a qualifying baseline probe must show that the task has room to
move, and admission must keep successful attempt outcomes, retained patch
production, and the conditional quality of retained patches separate
rather than choosing a metric after seeing the result (the V5a design
spec's index applies this per arm). The pre-admission probe records — the
[`oracle audit`](docs/superpowers/research/2026-08-27-local-pings-baseline-probe.md),
the [`corrected probe`](docs/superpowers/research/2026-08-27-local-pings-corrected-probe.md),
the
[`Envelope/Engine follow-up`](docs/superpowers/research/2026-08-27-local-pings-envelope-engine-followup.md),
the
[`magicmock-factory` oracle audit and final probe](docs/superpowers/research/2026-08-29-magicmock-factory-baseline-probe.md),
and the
[product-path pilot](docs/superpowers/research/2026-08-26-product-path-pilot.md)
— are the evidence the index was built from; their pre-decision "do not
admit" verdicts are superseded by the V5a decision (Prior work below).

## Backlog

Moved to [`BACKLOG.md`](BACKLOG.md), so the phase list stays readable. Every
entry there states what reopens it.

## Prior work

Completed phases move here (or to `docs/superpowers/phase-history.md`)
when the roadmap outgrows the front page.

- **D2 — The learner's big picture (2026-09-04).** A dedicated learner page (`what-actually-happens`) wired into Start here after the first verdict — front page → tutorial → learner page → guides — teaches in ordinary words what actually happens when an AI coding agent works, then maps those pieces onto Evals' evidence loop. Diagram 1 (agent ↔ codebase + tools → inference server containing the model, with request/token edge labels) sits inside that page; diagram 2 (Evals evidence loop) redraws diagram 1's whole agent loop as the opaque attempt command whose patch + transcript are graded offline into a receipt. Zero runtime JavaScript; the sdd discipline bullet and the review template's Visual assets group hold both figures legible at documentation width in light and dark Furo. **Bake-off: PASS — d2 v0.8.2** (`--sketch --theme 0 --scale 0.5`) rendered both diagrams from committed `.d2` sources byte-for-byte; no hand-authored fallback. Design: `2026-09-04-d2-learner-big-picture-design.md`.
- **V5d — The pre-flight smoke check (2026-09-03).** The revised proposal
  was confirmed and landed as a documented practice, not new code: one
  uncounted real-model smoke per materially distinct execution path, at
  that path's first real use; the attempt record read always and the
  receipt only when grading occurred; `NO_PATCH`/`COMMAND_TIMEOUT`
  passing only on positive evidence the model started; durable, uniquely
  named smoke evidence. Supersedes the V5c reconciliation's decision 4,
  which had kept V5d off main while unconfirmed. Spec:
  `2026-09-03-v5d-preflight-smoke-check-design.md`.
- **V5c — Capture the admitted suite (2026-09-02).** `local-pings` is
  captured as a bundled task with the `format_number` shape: manifest with
  the five-id oracle (three upstream local-ping tests plus the two-order
  curator preservation parametrization `[order0]`/`[order1]`), `base/` (the
  N=6 synthetic base; `pyproject.toml` gains `pythonpath = ["src"]` so
  uninstalled tree copies run), known-good and known-broken fixtures, and
  the engine contract. The gate re-recorded at N=6 across fresh processes
  with the canary reporting the scramble face every run: base 0/5,
  known-good 5/5, type-set 3 pass / 2 fail (caught 20/20). Row 3's
  adversary was re-specified by maintainer-confirmed amendment — the
  recorded N=2 type-set does not reproduce on this machine, and the
  cross-machine investigation (research record) shows the set-order catch
  is a discrete function of hash stride versus table geometry and
  allocation phase; the object-set substitution was dropped, and the gate
  gained a canary whose third outcome (inconclusive) stops capture. The
  `local-pings` admission numbers are recorded as unearned pending a
  re-probe against the captured task. The re-probe (2026-09-03) then
  recorded both arms middle (Baseline 3/8, Engine 4/8), and the maintainer
  **de-admitted `local-pings` as a diagnostic workload**, retaining it as a
  bundled grader/smoke/regression fixture
  ([record](docs/superpowers/research/2026-09-03-local-pings-deadmission.md);
  the re-probe results carry the numbers). Spec amendment, reconstruction
  correction, research record, and de-admission record under
  `docs/superpowers/`.
- **V5b — The diagnostic loop (2026-09-02).** `run TASK --n 8 -- COMMAND...`
  repeats the attempt seam and writes a counts-only `summary.json` — verdict
  reasons (`code_counts`/`verdict_counts`), timeouts, and the outcome tally.
  Its four transcript-derived metrics — tool calls, repeat, churn, context —
  were deferred to an engine-side emitter rather than parsed evals-side
  (`BACKLOG.md`; the V5b spec's Out of scope): the loop ships, while the
  diagnosis it is named for waits on that engine-side field. Spec and plan
  recorded under `docs/superpowers/`.
- **V5a — The admission rule (2026-09-02).** Decided the admission bar:
  the middle-band rule applies to the arms under comparison, not to the
  bare-Pi reference alone. The superseded kickoff framing named four probed
  tasks — `local-pings`, `stringified-annotations`, `magicmock-factory`, and
  a multi-prompt `svcs` session — and stated "**No probed task has a bare-Pi
  baseline in the middle band.**", then posed the decision:

  > is the admission bar "middle-band for bare Pi", or "discriminates between
  > the arms under comparison"? Under the first, four rigorously qualified tasks
  > are discarded. Under the second, at least two are admissible today.
  > `BRIEF.md`'s middle-band rule assumes the first without saying which arm is
  > the baseline, and that ambiguity now blocks the diagnostic loop.

  The corrected probes falsified the floor-is-a-wall reading (0/4 successful
  attempts with 2/2 constructible retained quality on `local-pings`; Engine
  2/4 in the follow-up; Engine 6/6 vs Baseline 0/6 in the pilot), so the
  decision admits the two tasks whose recorded arms separate: `local-pings`
  (Baseline floor / Envelope floor / Engine middle; **superseded for the
  captured task by the 2026-09-03 de-admission** —
  [record](docs/superpowers/research/2026-09-03-local-pings-deadmission.md))
  and `stringified-annotations` (Baseline floor / Envelope floor / Engine
  ceiling). `magicmock-factory` (Baseline floor, no other arm recorded) is
  unadmitted on an evidence gap; the multi-prompt `svcs` session is deferred
  to V6. `BRIEF.md` and `docs/glossary.md` were amended with the old wording
  kept in notes. Design spec and GLM 5.3 review recorded under
  `docs/superpowers/`.
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
