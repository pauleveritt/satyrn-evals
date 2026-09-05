# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**The next direction is a reliable instrument, a fitted AgentClinic suite,
and one preregistered Engine comparison.** V9, V10, V11a-trim and V11b-trim
are complete and landed; the trimmed contract ladder and the two-arm
substrate are in `main`. Neither of those measures anything. **V11c's
Baseline mini-probe has run and selected its task; its two-arm spike is
held.** The next build work is the V11d fix round and V12's entry gates:
[plan of record](docs/superpowers/plans/2026-09-05-v11d-instrument-fixes-and-v12-entry.md),
proposed 2026-09-05 and awaiting confirmation; its preflight-command slice is
already done and verified. The later phases do not promise
that Engine will win. They promise a durable placement profile, then a
prospective result whose null outcome is recorded as prominently as a
positive one. Rationale: the [`2026-09-04 roadmap record`](docs/superpowers/research/2026-09-04-roadmap-to-a-reliable-instrument-and-a-first-engine-result.md), as amended
by the [`2026-09-05 V11-trim amendment`](docs/superpowers/research/2026-09-05-roadmap-amendment-v11-trim.md); the argument of record is the
[`trim and spike proposal`](docs/superpowers/research/2026-09-05-v11-trim-and-spike-proposal.md).

No later phase starts before its own short design proposal is confirmed, as
required by `CLAUDE.md`. The spike protocol and V13 firewall were confirmed
2026-09-05, so V11c's cells are authorized. All five preconditions were met
and **the Baseline mini-probe has now run** — 12/12 cells, selecting
`agentclinic-repair-misleading-locus` at R1 by the frozen rule
(`~/satyrn-smokes/2026-09-05-v11c-miniprobe-2/RESULT.md`). **The two-arm spike
has not been run**; the maintainer held it. Preflight is per-batch: re-run it
into a new output directory immediately before the spike, as was done for the
mini-probe. The
[V11 fix brief](docs/superpowers/research/2026-09-05-next-agent-brief-v11-fixes.md)
records the corrections that landed to reach this state.

**Complete, and recorded in Prior work below:** V10 and V9 (2026-09-04), V8,
V7, D1, D2, V6, V5a–V5d, and V1–V4. `stringified-annotations` capture is
reopened for proposal (`BACKLOG.md`); `local-pings` is de-admitted as a
diagnostic workload and retained as a grader/smoke/regression fixture.

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
| V9 | Loop integrity and re-scoring | `run` survives a failing cell and writes every cell's record before grading; summaries name task/command/timeout; `regrade ATTEMPT_DIR` and `summarize OUTPUT_DIR` rebuild receipts and summaries from disk; T5–T8 fixed with refusal/success siblings; T9 stated; the 30 s attempt default raised | transcript metrics (V10); the ladder (V11a); model profiles (V12); probes (V13); weight (W1); session re-scoring; any model run — see the design spec's non-goals | **complete** — design spec `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md` confirmed 2026-09-04; implementation per plans p1–p6; post-implementation review closed B1–B3 (aborted runs write `aborted.json`, never `summary.json`; `summarize` rebuilds over the run’s own recorded cells; git-probe failures are one `UNAVAILABLE` cell); verification record `docs/sdd.md` |
| V10 | Transcript-derived pathology counts | Offline-read the preserved Pi attempt transcript and report tool calls, repeat, churn, no-op edits, test_runner_commands (command-text evidence, never proof tests ran), tool_free_terminal_turns, workspace escapes, and overlay windows; absent or unparseable data is `unmeasured`, never zero | Wall-clock metrics; changes to the Engine telemetry seam; causal claims from counts alone; session transcripts (A1) | **complete** — design spec `docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md` accepted 2026-09-04 (maintainer adjustments A1–A4, schema tightenings S1–S2; self-review + GLM 5.3 review + close-out corrections in the spec companion `docs/superpowers/research/2026-09-04-v10-spec-evidence-and-reviews.md`); plans `2026-09-04-v10-p1/p2/p3a/p3b/p4`; verification record `docs/sdd.md` |
| V11a | Evidence ladder (trimmed) | Ship an open `contracts: {rung: text}` manifest map carrying **R1 and R3 only**, generate the engine contract from manifest plus rung, add `--rung`, and record `rung` + `contract_digest` on the attempt record and summary | R0 and R2 — a V12 entry gate; vendoring `specs/` into `base/` — reversed; the widened hidden-id check — contradictory at R1, which carries bare hidden function names by design; model runs; Envelope | **complete** — landed as `a37c56a` and corrected by `1193296`; full gate and post-landing V5d evidence are green. **Rung labels are unverified authoring claims until V12** ([amendment](docs/superpowers/research/2026-09-05-roadmap-amendment-v11-trim.md)) |
| V11b | Reproducible arm substrate (trimmed) | Ship the in-tree Pi attempt adapter and two arm definitions — Baseline and Engine — with exact argv, tools, model identifier, pins and `-nc`, plus preflight, interleave and strict-tally scripts that refuse a malformed batch rather than shrink a denominator | Envelope — deferred to V13 scoping, since nobody knows what `envelope-cap.ts` capped; a budgeted probe; claiming an isolated mechanism effect; creation-capable patch capture — a V12 entry gate | **complete** — Engine repair `25ca0be` is pinned by `45ab88e`; both distinct paths passed uncounted post-landing V5d smokes, and clean-tree preflight is green. See the V11 fix brief and plan for correction evidence. |
| V11c | Baseline mini-probe and two-arm spike | Buy an early product-level signal for at most 36 cells: a Baseline-only mini-probe (R1, `n=4`, three candidate tasks) selects one cell by a rule frozen beforehand, then Baseline vs Engine at `n=12` per arm, interleaved on a seeded schedule | Preregistration and admission — it is **neither**; Envelope, so two arms not three; extending `n` after reading the result; pooling spike cells with V13's; any mechanism sentence | **mini-probe complete 2026-09-05; spike held** — 12/12 Baseline cells at R1 selected `agentclinic-repair-misleading-locus` (3/4 interior; `plausible-wrong-fix` 4/4, `depth-3` 0/4 with 4/4 retained patches — a quality floor, not a capability wall). Result and recompute commands: `~/satyrn-smokes/2026-09-05-v11c-miniprobe-2/RESULT.md`; rule application recorded in the spike-protocol spec. A first attempt is **void** (GPU out-of-memory scored as `NO_PATCH`; `~/satyrn-smokes/2026-09-05-v11c-miniprobe/VOID.md`) and is not pooled with it. The 24-cell spike is authorized by the selection but unrun |
| V12 | Placement profile | Run the reference arm only for both named Gemma capability points, six tasks, and all four rungs at `n=6`; retain the three-way outcome split and classify every task-rung/model cell into a band | Comparing arms; admission claims; tuning a contract or sample size after reading the profile | **queued after V11b** — scientific scope unchanged. **Entry gate:** author R0 and R2 and restore the four-point monotonicity check; ship creation-capable patch capture before `framing-2` runs; re-run the live one-word completion, never `/v1/models`; plus R2 and a well-formed-tool-call canary per model, observed transcript-model validation, and a resume-safe 288-cell driver |
| V13 | Preregistered three-arm probe | Compare Baseline, prospective Envelope, and Engine on a predeclared eligible pure-edit cell, interleaved by a recorded schedule; publish counts, bands, pathology counts, and a positive or null result | Mechanism attribution; build/author tasks; escalating `n` or changing cells after the result | **queued after V10 and V12** — scientific scope unchanged; exactly one primary cell prevents a multiple-cell success hunt. V13 now also **defines and preregisters Envelope**, and its primary-cell and Envelope-budget algorithms are frozen from reference-arm data alone **before** the spike runs |
| W1 | Weight | Simplify unsupported cleanup and git plumbing, remove legacy record/Windows branches and duplicate enums, freeze capture, and retain the 100% branch gate while recording the coverage reduction | New behavior; weaker verification; work that V9 did not first stabilize | **independent after V9** |
| V14 | Build rungs on the same app | Author phase-missing, all-missing, and session build shapes over the same oracle, closing the cumulative-suite entry as hand-authored | Reusing V13's result; work before an Engine runner and file creation exist | **conditional** — starts only if V12 needs build headroom and Engine-side prerequisites land |
| V15 | A second application | Package a larger multi-module dependency-bearing fixture | Starting before V14 has placed the 26B-A4B capability point at ceiling | **conditional** — only if every AgentClinic rung, including build, ceilings for that point |
| V1 | It installs and grades | `grade` accepts a bundled task's known-good patch and rejects its known-broken one, offline and deterministic | Capture, attempt, the claims layer | **complete** |
| V2 | Capture by revert | `capture --revert SHA` makes a task winnable by construction, in minutes | Environment materialization, baseline probes, commit mining, a sandbox, Windows | **complete** |
| V3 | Attempt persistence | `attempt TASK -- COMMAND...` runs a fake command, persists patch and transcript, regrades offline | The real engine seam (V4), the diagnostic loop, transcript format, retry, repair | **complete** |
| V4 | A real engine attempt | Reconstruct an isolated Git workspace and produce the V3 artifact set with `satyrn-engine attempt` | Model-quality claims, admission, repeated attempts, A/B (V5); containment; Windows | **complete** |
| V5a | The admission rule | decide and record which arm the middle-band bar applies to, then index every probed task with its band per arm; no model runs | Model runs, the diagnostic loop (V5b), the claims layer, an Envelope/Engine-arm probe of `magicmock-factory`, the svcs session suite (V6), near-ceiling boundary calibration, suite-headroom capture — see the spec's Out of scope | **complete** |
| V5b | The diagnostic loop | `run --n 8` over admitted tasks, summarizing verdict reasons, repeated calls, churn, tool calls, context, and timeouts | The claims layer — pre-registration, intervals, void accounting (`BRIEF.md:33-36`) | **complete** |
| V5c | Capture the admitted suite | reconstruct and `capture --revert` the corrected `local-pings` synthetic pair, then re-record the probe's three-row qualification table as the gate that the capture is faithful | `stringified-annotations` capture (reopens once the loop runs on `local-pings`); `magicmock-factory` (reopens with an Envelope/Engine probe); oracle improvement (its own proposal); running the loop; suite-headroom capture — see the spec's Out of scope | **complete** |
| V5d | The pre-flight smoke check | run one real-model attempt (`run TASK --n 1`) against each materially distinct command/adapter/runtime path before that path's first budgeted diagnostic run, and read the attempt record — plus the receipt when grading ran — against a short pass/fail checklist; `NO_PATCH`/`COMMAND_TIMEOUT` pass only with positive evidence the model started | automated engine-contract content validation (`BACKLOG.md`); the `pi` argv incompatibility itself (satyrn-engine's backlog); running smoke in CI or any test tier; a manifest smoke-record field; `local-pings` re-admission or new prospective read/write Envelope decisions — see the spec's Out of scope | **complete** |
| D1 | Documentation orientation | adopt a Diátaxis structure that reveals Satyrn Evals from a successful first verdict to task capture, attempts, diagnostics, and the design record; place a small concrete suite example—code, pseudocode, or drawing—immediately before the exact command that runs it on the top-level page | CLI or task behavior; V6 operational docs; model-quality/claims-layer guidance; rewriting historical evidence — see the design spec's Out of scope | **complete** — amended 2026-09-04 (review corrections and the suite example; spec amendment); [design](docs/superpowers/specs/2026-09-04-d1-diataxis-documentation-design.md), [plan](docs/superpowers/plans/2026-09-04-d1-diataxis-documentation.md) |
| D2 | The learner's big picture | teach what actually happens when an AI coding agent works — agent, tools, inference server, model — in one lo-fi diagram and a short page placed after the first verdict, then map those pieces onto Evals' evidence loop in a second diagram; zero runtime JavaScript | animation; client-side rendering runtimes; theme-coupled SVG colors; serving ops detail; Satyrn boxes in diagram 1; more learner pages beyond the two — see the design spec's Out of scope | **complete** — learner page placed after the first verdict teaches what actually happens when an agent works (agent ↔ codebase + tools → inference server containing the model), then maps those pieces onto Evals' evidence loop (the attempt command as the opaque agent loop → patch + transcript → offline grade → receipt); two d2-rendered committed SVGs, zero runtime JavaScript — [design](docs/superpowers/specs/2026-09-04-d2-learner-big-picture-design.md), [plan](docs/superpowers/plans/2026-09-04-d2-learner-big-picture.md) |
| V6 | Session eval | `session TASK -- ADAPTER...` sends ordered prompts to one conversation against one evolving checkout, snapshots a cumulative patch per checkpoint, and grades offline through a grader overlay the executor is never shown | `run --n 8` and admission, model-client integration, retries, a hostile-command sandbox, a persistent Engine daemon | **complete** |
| V7 | Task visibility and leak detection | a manifest field declares each task visible- or hidden-oracle; contamination is detected by content and reported per arm, never absorbed into a denominator | OS-level containment — deferred in `BACKLOG.md`; V7 detects rather than prevents | **complete** — remains so; post-merge verification corrections recorded in the spec's close-out amendment ([design](docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md)) and the V7 verification record (`docs/sdd.md`); phase not reopened |
| V8 | AgentClinic through Evals | reproduce the repair fixtures on this repository's own `capture`/`attempt`/`grade` path, replacing the spike's scratchpad harness | Engine changes, including a `facts` field (satyrn-engine `BACKLOG.md`); an orchestrator | **complete** — six bundled `agentclinic-repair-*` tasks, two production changes, 24/24 gate, smoke passed; spec `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md`, record `docs/sdd.md` |

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
V8's done-when lives in its design spec — now complete (Prior work
below); V7's done-when lives in its design spec — now complete (Prior
work below); V5a's and V5b's done-when lived with their design specs, now
complete (Prior work below).

## Next roadmap: gates and sequence

The path to the first result is
`V9 → V11a → V11b → (V11c) → V12 → V10 → V13`. V9 and V10 are complete.
W1 may run after V9 without delaying that path. V10's output is applied
retroactively to V12's preserved transcripts and is a gate before the V13
cell is chosen, keeping the placement profile's verdict evidence separate
from the diagnostic counts that explain a later arm difference.

**V11c is a detour, not a step.** It buys an early product-level signal for
at most 36 cells and two unattended nights. It admits no workload and
replaces no phase. What it changes is nearer-term engineering priority: a
directional Engine advantage keeps the pure-edit path plausible; a valid null
makes the missing Engine test runner the next Engine prerequisite before V13;
an instrument failure repairs the substrate before another model cell runs.
Its `n=12` is a fixed spending limit, not a powered design — under true rates
0.50 versus 0.125, exact enumeration gives about **36% power** at
`α = 0.025`, so the spike carries **no significance threshold** and Fisher's
one-sided value is descriptive beside the counts. **No extension after
reading the result.**

**The firewall.** Before the spike runs, both V13 algorithms are frozen: the
ordered primary-cell selection from V12 reference-arm data, and the rule
mapping reference-arm budget evidence to Envelope's cap. Neither reads spike
outcomes. If the resulting primary cell coincides with the spike cell, V13
discloses the prior peek and labels the fresh comparison a replication.
**Spike cells are never pooled with V13 cells.**

V12 keeps all four rungs, including R2. Its `n=6` is for placement only, not
confirmation. Before its first budgeted cell, each model must pass both a
real completion preflight and a well-formed-tool-call canary; every transcript
must validate the observed `message.model`, not only the requested argv; each
materially different adapter/arm path also follows the existing V5d smoke
practice; and the 288 cells need a resume-safe driver that preserves the
planned denominator across interrupted nights. The two named Gemma points are
capability points, not a parameter-size scale: the 26B-A4B model has 4B active
parameters, so profile tables name the complete model/quantization identifiers
and make no "larger model" claim.

V13 selects only pure-edit repair cells that V12 places below ceiling and
above a capability wall. Its proposal must freeze an ordered selection rule
before any non-reference arm runs; that rule yields one primary
`(model, task, rung)` cell. The comparison uses `n=12` per arm, an
interleaved, seed-recorded schedule, and two predeclared one-sided Engine
contrasts (against Envelope and Baseline), each at Bonferroni-adjusted
`α = 0.025`. Any additional eligible cells are descriptive replications, not
independent opportunities for a positive claim. If the primary comparison
does not meet the criterion, the result is a null at that cell and `n` and
the selected cell do not change; a later rung is a new proposal and
preregistration.

Envelope is prospective and **is defined in V13, not V11b**: the 900 s /
8192 tokens / 80k context in the de-admission record are pi and model
settings, **not** what `envelope-cap.ts` capped, so the cap is a fresh choice
that must be argued from a per-cell floor measured inside a materialized
workspace. It is not called a reproduction because the historical
configuration cannot be recovered. The three arm surfaces are a product-level
comparison, so an Engine advantage supports no claim that any single
component (mutator, loop breaker, or handoff) caused it. The Engine's
model-invocable test runner is therefore not a V13 blocker for the pure-edit
probe; it is a blocker for V14 and for any broader mechanism or build-task
interpretation.

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

- **V10 — Transcript-derived pathology counts (2026-09-04).** An offline
  reader of the preserved Pi attempt transcript reports tool calls, repeat,
  churn, no-op edits, `test_runner_commands` (command-text evidence, **never**
  proof that tests ran), `tool_free_terminal_turns`, workspace escapes and
  overlay windows. Absent or unparseable data is **`unmeasured`, never zero** —
  the discipline four recorded silent-zero incidents paid for. No engine
  telemetry seam changed and no causal claim follows from a count. A standing
  limit the V11 smokes must clear: all eight preserved 2026-09-03 Baseline
  reprobe transcripts read `unmeasured: unknown_event` because they carry
  `tool_execution_update`, so **a non-empty transcript is not proof V10 can
  measure it**. Design:
  `2026-09-04-v10-transcript-pathology-counts-design.md` (adjustments A1–A4,
  tightenings S1–S2, reviews in its research companion); plans
  `2026-09-04-v10-p*`; verification record `docs/sdd.md`.
- **V9 — Loop integrity and re-scoring (2026-09-04).** The batch loop
  survives a failing cell: every cell's record is written before grading
  (`GRADE_FAILED` when grading did not complete), summaries name
  task/command/timeout, and `regrade ATTEMPT_DIR` + `summarize OUTPUT_DIR`
  make BRIEF rule 3 executable — the rebuilt summary is byte-identical to
  the run's own. T5 preservation grading stops auto-overlaying; T6's
  umask-002 stored-file refusal is removed (recorded correction); T7's
  oracle-hook shim keeps the locked env authoritative; T8's grading git
  runs in the cleaned environment; T9 is stated as a limit beside BRIEF
  rule 4; the 30 s attempt default is 900 s. A post-implementation review
  closed three structural blockers: aborted runs write `aborted.json`
  (requested/completed/error, never `summary.json`), `summarize` rebuilds
  over the run's own recorded cells (strays cannot change it), and a
  git-environment probe failure is one `UNAVAILABLE` cell, not a batch
  abort. Default tier 748; full gate 1000 passed, 100% statement +
  branch. Design: `2026-09-04-v9-loop-integrity-and-rescoring-design.md`;
  plans `2026-09-04-v9-p*.md`; verification record `docs/sdd.md`.
- **V8 — AgentClinic through Evals (2026-09-04).** Six bundled
  `agentclinic-repair-*` tasks vendored from the `swiftstar` companion
  repository (MIT, notice retained): reconstructed broken bases as locked
  projects, the full 13-test acceptance suite as a hidden per-task overlay,
  and failure-digest contracts that never name a grader file. Two
  production changes: `grade` materializes a dependency-bearing task's own
  locked environment and attests the executed distributions as
  `resolved_versions` from `uv pip freeze` (stdlib tasks untouched, no key);
  the contamination detector subtracts base-visible overlay windows
  (additive). The 24/24 offline gate proves every task by fixture name
  (base rows from hook records, six known-good 13/13, six known-broken
  fails, six contamination pairs). The uncounted V5d smoke — one real-model
  stock-engine attempt on `plausible-wrong-fix` — passed end to end after
  the engine's pi-argv fix it surfaced (recorded, not fixed in V8). The
  budgeted admission probe stays closed in `BACKLOG.md` until its reopen
  condition is met. Spec and plan under `docs/superpowers/`; verification
  record in `docs/sdd.md`.

- **V7 — Task visibility and leak detection (2026-09-04).** A manifest
  field (`oracle_visibility`) declares each task visible- or hidden-oracle,
  enforced by the ⇔ rule with `grader_overlay` and an authoring-time name
  check. Contamination on hidden tasks is detected by content — a pure,
  verbatim block-rule tripwire with evidence pointers — and reported per
  graded artifact as `flagged`/`clean`/`unmeasured`, never changing a
  verdict, an exit code, or a denominator; an ordinary attempt's `clean`
  covers its preserved patch and the workspace-absence invariant only, not
  the engine transcript. Read-only modes ship with their stated limit:
  `0o444` at materialization is accidental-exposure prevention, not
  security isolation, and a stored-file check refuses group/other-writable
  overlay files. Every summary from V7 names its `cells` and
  `oracle_visibility` (closing the V5 evidence-provenance correction);
  hidden-task summaries carry the contamination tally with
  `flagged + clean + unmeasured == graded`. Spec:
  `2026-09-04-v7-task-visibility-leak-detection-design.md`.
- **D1 — Documentation orientation (2026-09-04, amended the same day).** The
  public docs use a Diátaxis structure: a first-time reader sees the
  actionable-evidence promise and a successful `format_number` receipt before
  operational guides, explanatory topics, CLI reference, or development
  history; capture, attempt, and diagnostic-batch instructions are organized
  by desired outcome; the task/artifact formats have a reference page;
  the architecture and glossary are current. Reopened 2026-09-04 for review
  corrections, then amended: a deep review's nine findings (formats
  reference, guide execution context and `--tasks-root`, capture-record
  filename, refusal and smoke semantics, architecture/glossary currency, the
  receipt example, EOF blank lines) plus the front-page suite example, all
  recorded in the design spec's amendment. Design and plan:
  `2026-09-04-d1-diataxis-documentation-design.md` and
  `2026-09-04-d1-diataxis-documentation.md`.
- **D2 — The learner's big picture (2026-09-04).** A dedicated learner page (`what-actually-happens`) wired into Start here after the first verdict — front page → tutorial → learner page → guides — teaches in ordinary words what actually happens when an AI coding agent works, then maps those pieces onto Evals' evidence loop. Diagram 1 (agent ↔ codebase + tools → inference server containing the model, with request/token edge labels) sits inside that page; diagram 2 (Evals evidence loop) redraws diagram 1's whole agent loop as the opaque attempt command whose patch + transcript are graded offline into a receipt. Zero runtime JavaScript; the sdd discipline bullet and the review template's Visual assets group hold both figures legible at documentation width in light and dark Furo. **Bake-off: PASS — d2 v0.8.2** (`--sketch --theme 0 --scale 0.5`) rendered both diagrams from committed `.d2` sources byte-for-byte; no hand-authored fallback. Design: `2026-09-04-d2-learner-big-picture-design.md`.
- **V6 — Session eval (2026-09-04).** `session TASK -- ADAPTER...`:
  one conversation against one evolving checkout, cumulative checkpoints
  snapshotted and durably linked before the next prompt, offline grading
  through a grader overlay the executor never sees, and a shipped Pi
  adapter over `pi --mode rpc`. Two independent reviews drove recorded
  corrections: prompt-wide deadlines, cleaned Git environment, per-
  checkpoint durable records, collector selectors, context_reset as a
  protocol failure, message_update retention, Pi-declared terminals,
  scope-preserving source_paths, and preservation `invalid` on
  protected-test edits. Session runtime policy
  (`PYTHONDONTWRITEBYTECODE`) keeps bytecode out of the workspace. Three
  uncounted real-model smokes on the local model passed plumbing.
  Bundled `session-mechanics` grader fixture; svcs materialization and
  qualification remain a separate proposal.
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
