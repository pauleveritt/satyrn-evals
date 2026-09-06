# Roadmap

> **Planning surface, not the front door.** Where the current phase, the
> concept budget, deferred candidates, and the backlog live. Completed
> phases move to [`ARCHIVE.md`](ARCHIVE.md). Not where a
> new contributor should start — see
> [`README.md`](README.md) for what's usable now.

*Phases group feature cycles. One direction at a time. Tangents go to the
Backlog, not into the current phase.*

## Now

**The next direction is a reliable instrument, a fitted AgentClinic suite,
and one preregistered Engine comparison.** V9, V10, V11a-trim and V11b-trim
are complete and landed; the trimmed contract ladder and the two-arm
substrate are in `main`. Neither of those measures anything. **V11c's two-arm spike recorded Engine 10/12 versus
Baseline 5/12** successful attempts — outcome 1 by the predeclared table,
exploratory, no mechanism claim. A follow-up probe closed the one
condition that could have made that an instrument artifact: compaction
rescues no locked loop. pi's context window is now corrected to the
enforced 80,000 for every arm, so successful-attempt counts stay
comparable across the change while `code_counts` do not (records beside
their cells; [decision](docs/superpowers/research/2026-09-05-context-window-decision.md)).
A **staged V12 reference profile** has now run — 168 cells over R0, R1
and R3 at both named Gemma capability points, every tally accepted
(`~/satyrn-smokes/2026-09-06-overnight-232554/RESULT.md` and
`~/satyrn-smokes/2026-09-06-r0-profile-081459/RESULT.md`). R3 ceilings
almost everywhere and R0 is bimodal, so **every middle-band value sits at
R1** — a thin headroom inventory for V13 — and the two capability points
do not order cleanly. **V12's remaining entry gates are closed by
evidence, not by more code** — the amendment under the phase table names
each one and what closes it. Its instrument-fix round
([plan of record](docs/superpowers/plans/2026-09-05-v11d-instrument-fixes-and-v12-entry.md),
confirmed 2026-09-05) is closed too: slices 0–2 and 4 are done (F1, F2, F3:
[record](docs/superpowers/research/2026-09-05-v11d-f2-f3-record.md); F4 is
`MODEL_ERROR`); the round **stopped after slice 2** by the rule it paid
for (`CLAUDE.md`); slice 3 is **withdrawn** — staging in batches of at most
60 cells made a resume-safe driver moot — and slice 5's gates are the
evidence just named. **V13 has run, and it is a null.** Baseline **7/12**, Envelope
**4/12**, Engine **4/12** successful attempts on the preregistered cell;
neither predeclared contrast is met, the tally accepted 36/36, and all
four publishability conditions are recorded with the counts
(`~/satyrn-smokes/2026-09-06-v13-143343/RESULT.md`). **The null carries no
claim about Engine's design:** five of its twelve cells never got to try,
because the engine's own edit tool refused **973** calls — its schema
forbids a `path` key inside the edit item that the model also sends at the
top level, where the schema requires it, and its loop breaker keys on
exact call identity so a varying `newText` never trips it
(`satyrn-engine/packages/engine/mutator.ts:107-127`,
`engine.ts:100-126`). Neither pi arm carries the defect. **That engine change
has since landed** (`satyrn-engine` `b977941`; 973 refused calls replay
clean, malformed ones still refused), and **V13a verified it live**:
Baseline and Engine interleaved, `n=6` per arm on `depth-2` and
`misleading-locus` at R1, **0 schema refusals across 12 Engine cells**
against 973 before, no Engine timeouts, and Engine 4/6 and 5/6 against
Baseline 2/6 and 3/6 — descriptive, `n=6` carries no threshold
(`~/satyrn-smokes/2026-09-06-v13a-174142/RESULT.md`, protocol frozen in
`docs/superpowers/specs/2026-09-06-v13a-engine-fix-verification-spike.md`).
**The arms are comparable again; that is the claim, not that Engine is
better.** Envelope's restricted surface also cost it against Baseline in
V13 — the first evidence that `read,edit` *loses* on a repair task.

> **Recorded 2026-09-06, and it changes how a probe may be designed.**
> Baseline on `depth-2` R1 measured 7/12 in the V13 batch and 2/6 in the
> V13a batch — same arm, task, rung and model, different batch, with
> `temperature` unpinned for every arm. V13a was first designed as
> Engine-only read against V13's Baseline; that design would have compared
> Engine 4/6 against Baseline 7/12 and concluded the opposite of what the
> interleaved batch shows. **Counts are compared within an interleaved
> batch or not at all.**
>
> **Pinned the same day, and it is a re-baseline.** Every arm now records
> `temperature: 1.0`, pi's `models.json` sends it through the model entry's
> `samplingParams`, and preflight 0c checks the two against each other —
> refusing an arm that pins none, a config that sends none, and the case
> where *both* are absent, which is not agreement but nobody having decided.
> **Every batch before this pin ran at the server's own unrecorded default
> and is not comparable across it**: V11c, the V12 profile, V13 and V13a are
> all pre-pin. 1.0 was chosen as the value most likely to match what was
> already running — for continuity, not tuned — and that continuity is
> assumed, not measured. The correction that made it possible: preflight
> read `settings.json`'s `temperature`, a key **pi never reads**, so both
> sides of that comparison were always `None` — a check that could not fail,
> inside the check whose job is to catch those.
The later phases do not promise
that Engine will win. They promise a durable placement profile, then a
prospective result whose null outcome is recorded as prominently as a
positive one. Rationale: the [`2026-09-04 roadmap record`](docs/superpowers/research/2026-09-04-roadmap-to-a-reliable-instrument-and-a-first-engine-result.md), as amended
by the [`2026-09-05 V11-trim amendment`](docs/superpowers/research/2026-09-05-roadmap-amendment-v11-trim.md); the argument of record is the
[`trim and spike proposal`](docs/superpowers/research/2026-09-05-v11-trim-and-spike-proposal.md).

No later phase starts before its own short design proposal is confirmed, as
required by `CLAUDE.md`. Every batch is recorded beside its own cells.
Preflight is per-batch: re-run it into a new output directory immediately
before each budgeted batch, as was done for all five. **Quiet the machine first** — the voided attempt was a GPU
out-of-memory, which is machine state that no V11d fix prevents. The
[V11 fix brief](docs/superpowers/research/2026-09-05-next-agent-brief-v11-fixes.md)
records the corrections that landed to reach this state.

**Complete, and recorded in [`ARCHIVE.md`](ARCHIVE.md):** V10 and V9 (2026-09-04), V8,
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
| V11c | Baseline mini-probe and two-arm spike | Buy an early product-level signal for at most 36 cells: a Baseline-only mini-probe (R1, `n=4`, three candidate tasks) selects one cell by a rule frozen beforehand, then Baseline vs Engine at `n=12` per arm, interleaved on a seeded schedule | Preregistration and admission — it is **neither**; Envelope, so two arms not three; extending `n` after reading the result; pooling spike cells with V13's; any mechanism sentence | **mini-probe complete 2026-09-05; spike held** — 12/12 Baseline cells at R1 selected `agentclinic-repair-misleading-locus` (3/4 interior; `plausible-wrong-fix` 4/4, `depth-3` 0/4 with 4/4 retained patches — a quality floor, not a capability wall). Result and recompute commands: `~/satyrn-smokes/2026-09-05-v11c-miniprobe-2/RESULT.md`; rule application recorded in the spike-protocol spec. A first attempt is **void** (GPU out-of-memory scored as `NO_PATCH`; `~/satyrn-smokes/2026-09-05-v11c-miniprobe/VOID.md`) and is not pooled with it. The 24-cell spike then ran: tally accepted 24/24, **Engine 10/12 vs Baseline 5/12** successful attempts — **outcome 1**, exploratory, no mechanism claim. Every non-success in **both** arms is one shape: a `read app.py` loop locked at the fifth tool call. Result and the recompute: `~/satyrn-smokes/2026-09-05-v11c-spike-184017/RESULT.md` |
| V12 | Placement profile | Run the reference arm only for both named Gemma capability points, six tasks, and the rungs that carry placement information at `n=6`; retain the three-way outcome split and classify every task-rung/model cell into a band | Comparing arms; admission claims; tuning a contract or sample size after reading the profile | **profile run 2026-09-06; entry gates closed by evidence** — 168 cells over R0, R1 and R3 at both capability points, every tally accepted (records in **Now** above); every middle-band value sits at R1. Scientific scope unchanged. **Rung set amended 2026-09-06:** the staged profile placed R3 at 6/6 on nine of ten task/model pairs, so **R3 is dropped from placement** and R0 is authored for the four tasks whose public suite is red at base — `framing-2`/`framing-2-edit` need `specs/` vendored, which V11a reversed. R2 is not authored: it sits between R1 and a rung that ceilings. The four-point monotonicity check becomes a two-point **R0 &lt; R1** authoring gate (`tests/test_rung_ladder.py`). **Entry gates closed by evidence, not code:** the observed-`message.model` check is `scripts/tally.py:155-227`; 216 cells of well-formed tool calls answer the canary; creation-capable capture is owed only if `framing-2` enters placement, and a recorded gate excludes it |
| V13 | Preregistered three-arm probe | Compare Baseline, prospective Envelope, and Engine on a predeclared eligible pure-edit cell, interleaved by a recorded schedule; publish counts, bands, pathology counts, and a positive or null result | Mechanism attribution; build/author tasks; escalating `n` or changing cells after the result | **complete 2026-09-06 — null** — Baseline **7/12**, Envelope **4/12**, Engine **4/12** successful attempts on `agentclinic-repair-depth-2` R1, `gemma-4-12B-it-MLX-8bit`; neither predeclared one-sided Engine contrast is met (p = 0.950 vs Baseline, 0.667 vs Envelope, descriptive). Tally accepted 36/36. **Diagnosis:** all five Engine `COMMAND_TIMEOUT` cells are mutator schema rejection loops — 973 refused `edit` calls across 6/12 cells, none in either pi arm — so the null carries no claim about Engine's design. Envelope's restricted surface also cost it against Baseline. Result, recompute and the four publishability conditions: `~/satyrn-smokes/2026-09-06-v13-143343/RESULT.md` |
| W1 | Weight | Simplify unsupported cleanup and git plumbing, remove legacy record/Windows branches and duplicate enums, freeze capture, and retain the 100% branch gate while recording the coverage reduction | New behavior; weaker verification; work that V9 did not first stabilize | **independent after V9; scheduled directly after V13** (2026-09-06) — the weight check has never been run, and the measured figures that make it due are recorded under the phase table |
| V14 | Build rungs on the same app | Author phase-missing, all-missing, and session build shapes over the same oracle, closing the cumulative-suite entry as hand-authored | Reusing V13's result; work before an Engine runner and file creation exist | **conditional** — starts only if V12 needs build headroom and Engine-side prerequisites land |
| V15 | A second application | Package a larger multi-module dependency-bearing fixture | Starting before V14 has placed the 26B-A4B capability point at ceiling | **conditional, and its trigger rests on a refuted premise** (2026-09-06) — the wording above assumes the 26B-A4B point exhausts the suite first; the staged profile refuted that ordering (the 26B is *worse* on `depth-2` R1, 1/6 against 3/6), and nothing in V13, W1 or the headroom proposal runs a build rung to test it. The old wording stays visible until **the headroom proposal rewrites this row**, keyed to tasks rather than a model — reopening when no task on the current app places any compared pair in different bands, which is the admission rule's own question |
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
(complete — see [`ARCHIVE.md`](ARCHIVE.md)).
V5d's done-when is its practice being referenced from `BACKLOG.md` and
confirmed by the maintainer, in
`docs/superpowers/specs/2026-09-03-v5d-preflight-smoke-check-design.md`
(complete — confirmed by the maintainer and landed 2026-09-03. The next
task captured after `local-pings` must follow the practice; a captured
task that reaches a budgeted run without its smoke, or a smoke that
conceals a defect, reopens V5d).
V8's, V7's, V5a's and V5b's done-when live with their design specs — all
four complete, and recorded in [`ARCHIVE.md`](ARCHIVE.md).

## Next roadmap: gates and sequence

The path to the first result is
`V9 → V11a → V11b → (V11c) → V12 → V10 → V13`. V9 and V10 are complete.
W1 may run after V9 without delaying that path, and **is scheduled
directly after V13** (2026-09-06): the weight check has never been run and
the figures below say it is due. V10's output is applied
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
practice. The two named Gemma points are
capability points, not a parameter-size scale: the 26B-A4B model has 4B active
parameters, so profile tables name the complete model/quantization identifiers
and make no "larger model" claim.

> **Recorded amendment (2026-09-06).** Two clauses above are superseded,
> and are kept visible as the record. **Rungs:** the staged profile placed
> R3 at 6/6 on nine of ten task/model pairs, so R3 is dropped from
> placement and R2 is not authored — the V12 row carries the amended set.
> **Entry gates:** they are closed by evidence, not by code. The
> observed-`message.model` check exists (`scripts/tally.py:155-227`); 216
> cells of well-formed tool calls at both capability points answer the
> canary; creation-capable capture is needed only if `framing-2` enters
> placement, which a recorded gate excludes. **The resume-safe driver is
> withdrawn** with the 288-cell count that motivated it: 168 cells landed
> in staged batches of at most 60 with no interruption loss. The same
> profile retires the repeated-call limit's per-model re-validation — no
> patch-producing cell exceeds an identical run of 2 against a limit of 10,
> at either capability point
> (`~/satyrn-smokes/2026-09-06-overnight-232554/RESULT.md:58-69`) — so that
> backlog entry is pruned rather than re-titled. Evidence and
> the recompute:
> [V13 handoff brief](docs/superpowers/research/2026-09-06-next-agent-brief-v13-envelope-and-roadmap-control.md).

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

> **Recorded amendment (2026-09-06).** Envelope is a **tool surface, not a
> budget**: `satyrn-evals-attempt-pi` on Engine's `read,edit` surface, every
> other setting identical to Baseline, no engine code and no cap. Two
> sentences that presume a cap therefore no longer bind, and stay visible
> as the record — "the rule mapping reference-arm budget evidence to
> Envelope's cap" under **The firewall**, and the cap "argued from a
> per-cell floor" in the paragraph above. The canonical product Envelope
> was itself a restricted surface, `read,write`
> ([follow-up](docs/superpowers/research/2026-08-27-local-pings-envelope-engine-followup.md)),
> which `read,edit` is not: this arm is prospective, not a reproduction.
> Decision and rationale:
> [V13 handoff brief](docs/superpowers/research/2026-09-06-next-agent-brief-v13-envelope-and-roadmap-control.md).

> **Recorded 2026-09-06: what follows V13, and what does not.** The order
> is **V13 → W1 → the headroom proposal**, and *not* V14.
>
> **W1 is due on measured weight.** `src` (excluding vendored tasks) is
> 9,015 lines, `scripts` + `arms` 1,893, and `tests` 22,092 — against
> `BRIEF.md`'s named trap, a 6,065-line harness measuring a 340-line
> engine. Not there yet, trending there. W1 is also where the withdrawn
> items are **removed** rather than left unbuilt: the resume-driver slice,
> the stale `test_real_e5_*`, and any code path whose only caller was a
> gate now closed by evidence. Recompute:
> `find src -name '*.py' -not -path '*/tasks/*' | xargs wc -l | tail -1`,
> and the same shape for `scripts arms` and `tests`.
>
> **The headroom proposal is written with V13's counts in hand**, which is
> not a peek but the V11c consequence table doing its job: a positive keeps
> the pure-edit path, a null makes the Engine test runner the next
> prerequisite. Two candidates, in cost order, chosen *in* the proposal and
> not before: (1) more repair tasks at R1 on the same app — no engine
> change, no creation-capable capture, the oracle shape that already
> discriminates; (2) V14's build rungs, which **cannot start before the
> engine pin moves** — Engine exposes only `read,edit`, so no test runner
> and no file creation, and evals still owes creation-capable capture.
> Rationale and evidence:
> [V13 handoff brief](docs/superpowers/research/2026-09-06-next-agent-brief-v13-envelope-and-roadmap-control.md) §10.

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
admit" verdicts are superseded by the V5a decision ([`ARCHIVE.md`](ARCHIVE.md)).

## Backlog

Moved to [`BACKLOG.md`](BACKLOG.md), so the phase list stays readable. Every
entry there states what reopens it.

## Prior work

Moved to [`ARCHIVE.md`](ARCHIVE.md), so the planning surface stays inside
its cap. Completed phases and superseded framings are recorded there
verbatim, most recent first.

## Workflow

This repository runs on spec-driven development — see
[`docs/sdd.md`](docs/sdd.md). Each feature cycle gets a committed design
spec, an implementation plan, then code. The default test suite needs no
model, network, or subprocess; process behavior lives in a small marked
integration tier.
