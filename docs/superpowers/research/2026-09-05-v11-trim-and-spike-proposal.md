# Proposal: trimmed V11, a Baseline mini-probe, and a two-arm spike

**Status: revised proposal after deep review. Nothing here is confirmed and
no code has been written.**
Per `CLAUDE.md`, V11a and V11b are phases and each needs the maintainer's
explicit confirmation before implementation. This document exists so both
can be ruled on in one sitting rather than two.

**Origin.** The maintainer asked to cut V11's duration hard to raise project
velocity. This is the answer to that, after an independent critical review
(Fable, 2026-09-05) that corrected several parts of the first draft. The
deeper repository review that followed added implementation, measurement,
and sequencing corrections. All corrections are recorded in §7 rather than
edited away.

## 1. The problem being solved

The committed path to a first Engine result is
`V9 → V11a → V11b → V12 → V10 → V13` (`ROADMAP.md:145`). V9 and V10 are
complete. What remains before any arm comparison is V11a, V11b, and V12 —
and V12 is 6 tasks x 4 rungs x 2 models at `n=6`, all reference arm.

That ordering is methodologically correct and it is expensive. It spends the
single largest inference block in the plan *before* anyone knows whether a
Baseline/Engine gap exists anywhere at all. The proposal below buys an early
product-level comparison for at most 36 cells and two nights. Its result does
not admit a workload or replace V12. It changes nearer-term engineering
priority: a directional Engine advantage keeps the current pure-edit path
plausible, while a valid null makes the missing Engine test runner the next
Engine prerequisite before V13. An instrument failure repairs the substrate
before another model cell runs.

## 2. What gets cut, and what it costs

### 2.1 Ship R1 and R3 only

V11a as written adds `R0`-`R3` (`ROADMAP.md:99`). This proposes R1 and R3
only.

**This is a sequencing bet, and it should be priced openly.** Every prior
suggests R1 may already sit at ceiling for a 12B: the fixture author's own
review says
`assert 307 == 303` "delivers the answer" and the fixture "measures
assert-reading, not diagnosis"; Block B recorded 19/20 on
`plausible-wrong-fix`; the V8 smoke passed first try at R3, and R1 removes
only the file name and the fix sentence. If the mini-probe ceilings at R1,
the trimmed ladder has no harder rung and R0 returns before the spike.

Two mitigations make the bet cheap to lose:

- **`contracts` is an open map**, `{rung: text}`, validated generically. R0
  and R2 become later authoring additions, not new machinery. They remain a
  V12 entry obligation because V12 still profiles all four rungs.
- **R0 does not need `specs/` vendored for five of six tasks.** The public
  suite is red at base on 5/6, so "the suite is red; public tests are in
  `tests/`" is a fair R0 with zero fixture bytes changed. Only
  `framing-2-edit` (public suite green) would need the spec.

**Known limit to state, not hide:** the R0->R3 monotonicity authoring gate
collapses to a two-point `R1 <= R3` check, and a one-task spike measures
neither. The rung labels are unverified authoring claims until V12. The cut
advances an early comparison; it does not remove the later R0/R2 work.

### 2.2 Do not vendor `specs/` into `base/`

This is what makes the cut cascade, and the reasoning was independently
verified. `grade.py:121-129` builds `visible_texts` from every file under
`base/`; the contamination scanner subtracts any overlay window that also
appears there. Vendoring `specs/` enlarges that subtraction set and could
silence the known-broken half of the contamination pair test — which is
exactly why re-derivation would be owed. With `base/` byte-identical the
subtraction set is unchanged, and the six contamination pairs and the 24/24
gate need no re-derivation.

The argument is **independence, not cost** — the gate is integration-tier
and runs in minutes. The point is that nothing about it changes.

**But the manifest does change**, and today `_assert_contract_names_no_overlay`
runs over `manifest.contract` alone (`manifest.py:207`). It and the manifest
shape tests must run over **every rung text**. Default-tier, cheap, and not
optional.

### 2.3 Defer the widened hidden-id check

For these tasks the overlay declares exactly `overlay`,
`test_acceptance.py`, and `overlay/test_acceptance.py`. Two consequences:

- The **existing** check already forbids the file name, so an R1 digest must
  carry **bare function names** — never the `test_acceptance.py::test_x`
  node-id form that `expected_test_ids` uses — or the manifest is refused at
  load.
- The proposed widening would forbid bare hidden function names, which R1
  carries by design. At R1 the widening is contradictory. V8 §4 already
  authorized naming them.

The residual risk the widening was meant to cover — a model inferring a
second suite and hunting for it, with the overlay present on this machine
and Baseline holding `bash` — is not closed by any text check. V10 supplies
partial detection: `workspace_escapes` sees lexical paths passed to file
tools but not paths embedded in `bash`, while `overlay_windows` sees verbatim
overlay windows but not paraphrases or short disclosures. The Engine still
has `read`, so its narrower tool surface reduces exposure without proving
isolation. The spike reports both counters per arm, preserves `unmeasured` as
its own state, and keeps flagged cells in the denominator.

### 2.4 A prospective Envelope with no TypeScript — deferred out of the spike

`pi` 0.84.4 has no turn or token budget flag, so a budget is either an
extension or an external kill. The adapter tees the JSON stream to the
transcript and that stream carries `turn_end`, so a Python turn cap is
feasible with no TypeScript on the critical path.

**Correction to the earlier draft:** "cap at the pilot's recorded values" is
not what it sounds like. The 900 s / 8192 tokens / 80k context in the
de-admission record are pi and model settings, not what `envelope-cap.ts`
capped. Nobody knows what it capped. The cap value is a **fresh choice that
must be argued**, not inherited. A kill is also not an in-loop cap — there
is no graceful final turn — and that semantic belongs in the arm definition.

Because of this, **Envelope is not in V11b-trim or the spike** (§4.3).
Before the spike, the V13 firewall freezes the reference-only rule that will
select its budget and primary cell (§4.5). V13 then defines Envelope once,
commits it, and reuses it byte-identical or re-versions explicitly.

### 2.5 Thin plans, unchanged review

`CLAUDE.md` requires that a spec and plan *exist*, not that they be long.
V9 and V10 together ran to roughly 3,300 lines of plan and still shipped
blockers that a one-hour review caught. Cut prose; keep the review.

### 2.6 A gap none of the cuts noticed: nothing records the rung

`Summary` carries task, command and timeout (`summary.py:42-44`);
`AttemptRecord` carries no contract digest. Two runs at R1 and R3 with the
same command differ only by the prompt echoed in the transcript's first
`message_start`. Recomputable, not indexed — the same shape as V9's T4.
**Add `rung` and `contract_digest` to both the attempt record and summary.**
`rung` is `null` when the default `contract` was used; the digest always
names the exact selected text. Summary construction refuses mixed rungs or
digests just as it refuses mixed tasks and commands.

## 3. Roadmap adjustments requested

1. **V11a-trim**: replace "Add `R0`-`R3` contracts ... vendor each task's
   `specs/` into `base/`, and prove the widened hidden-id check and all
   fixture/contamination rows again" with an open `contracts` map shipping
   R1 and R3, a generated engine contract, `--rung`, and rung plus contract
   digest recorded in the attempt record and summary. Vendoring and the
   widened check are deferred with the conditions in §2.2-2.3.
2. **V11b-trim**: unchanged in intent, reduced in surface — in-tree Pi adapter,
   two committed arm definitions (Baseline, Engine), preflight and
   interleave and strict tally scripts. Envelope is deferred to V13 scoping;
   its reference-only selection rule is frozen before the spike.
3. **New, between V11b and V12**: a Baseline mini-probe and a two-arm spike,
   both explicitly not preregistered and not admissible (§4).
4. **V12 entry gate**: author R0 and R2, restore the four-point monotonicity
   check, and add creation-capable patch capture before `framing-2` runs.
   V12's scientific scope stays unchanged: two named models, six tasks, four
   rungs, reference arm only, `n=6`.
5. **V13**: unchanged in scientific scope. Its primary-cell algorithm and
   Envelope-budget selection rule are frozen before the spike and use
   reference-arm data only. Fresh V13 cells are never pooled with spike cells.

**This amends roadmap decision 2 and reverses decision 4** from the
2026-09-04 research record. The open manifest map survives, while its
initial shipment narrows to R1/R3 and completes before V12; vendoring
`specs/` into `base/` is dropped. Per `CLAUDE.md`, the change is recorded as
a dated amendment to that record, not edited into it.

## 4. The sequence

Gates marked **[G]** need the maintainer and cannot be self-confirmed.

**0. Current-state verification — already satisfied.** V10 is committed at
`3734ca7`. Engine `main` is clean at `75d4863`; that commit has the same
patch-id as the earlier `d5d5d37` model-argument fix. The 26B weights and
saved oMLX model directory are durable (§5-6). These are preflight facts,
not outstanding maintainer decisions.

**1a / 1b. V11a-trim and V11b-trim, in parallel [G once, for both]**

These are nearly independent. V11a touches `manifest.py`, `attempt.py`,
`cli.py` and a new `engine_contract.py`; V11b adds `attempt_pi.py`,
`arms/*.json` and scripts. The adapter never needs `--rung`, because the
rung is exported as `SATYRN_TASK_CONTRACT` by evals before the adapter is
invoked (`attempt.py:108-110`). The only coupling is that the *Engine
smoke* needs the generated contract. Two agents, small merge surface.

*V11a-trim*

- `manifest.py`: optional `contracts: {rung: text}`, open map, non-empty
  strings; `_assert_contract_names_no_overlay` over `contract` **and every
  rung**; `contract` stays the default.
- `attempt.py` / `run.py` / `cli.py`: `--rung KEY` selects the text exported
  as `SATYRN_TASK_CONTRACT`; unknown rung is a usage error; `rung` and
  `contract_digest` on `AttemptRecord` and `Summary`.
- This is a new record generation, not a rewrite of history. Older records
  still load with `rung = null` and `contract_digest = null`; every new
  record requires a digest, including the default contract. Re-summarizing
  legacy output preserves the explicit unknowns.
- New `engine_contract.py`: render `{id, task, writable_paths}` from manifest
  plus rung. `id` is stable for task+rung+digest. File entries in
  `source_paths` remain exact; directory entries become fnmatch patterns for
  their descendants.
- Write generated bytes once at a deterministic path under the output root,
  keyed by the digest of the rendered bytes, and append that stable absolute
  path to the command. A fresh attempt-directory path cannot be used:
  `Summary` requires every recorded
  command in a run to be equal (`summary.py:141-149`). The digest pins the
  exact generated bytes.
- Author R1 for all six tasks, bare function names, re-derived from this
  repo's own base rows.
- Tests, default tier: rung refusal/success pair; `--rung` unknown/valid
  pair; record carries rung+digest; generator bytes pinned; generated
  patterns admit every intended source file and reject a neighboring path;
  a two-attempt Engine-shaped batch summarizes and re-summarizes with equal
  commands. Integration tier: `satyrn-engine check` accepts all six
  generated contracts.

*V11b-trim*

- `attempt_pi.py` plus console script: the reprobe wrapper moved in-tree,
  `--model`, `--tools`, `git diff HEAD`.
- `arms/baseline.json`, `arms/engine.json`: argv template, tools, model id,
  pins (pi 0.84.4, engine commit, sha256 of `engine.ts` and `mutator.ts`).
  The preflight and interleave driver consume these files through one small
  reader; they are executable inputs rather than parallel documentation. No
  registry or arm framework.
- `scripts/preflight.sh`, `scripts/interleave.py`, `scripts/tally.py`. The
  confirmed protocol commits the seed and schedule construction; preflight
  writes the realized arm order before the first cell. The tally refuses
  missing, duplicate, aborted, unexpected-task, wrong-rung, wrong-digest,
  wrong-model, or wrong-arm cells instead of shrinking a denominator.
- Tests, default tier: argv construction pair and tally refusal/success
  siblings. Integration: adapter against the existing fake-pi fixture
  produces patch and transcript.

**Known limit of `git diff HEAD`:** it drops files created by `write`
(untracked). Harmless on pure-edit repair, fatal for `framing-2` and for
build shapes. `git add -A` is not the fix — it would sweep a model's
`uv run pytest` residue into the patch and trip the allowlist check. Document
the limit; do not paper over it. Creation-capable capture is a V12 entry
gate because `framing-2` otherwise measures this adapter limit as model
behavior.

**2. Two V5d smokes** — n=1 each, uncounted, durable dirs, checklist read
against `attempt.json`, the receipt, and the rebuilt summary. Both are
required: the in-tree Baseline adapter is a new executable, and Engine with
a *generated* multi-file contract has never run. The V8 smoke already showed the
hand-authored contract had drifted from the manifest by a token, so this is
a real gate, not a formality — the `writable_paths` globs are the obvious
place for a generated contract to load cleanly and mean something different.

The Baseline smoke also fulfills V10's vocabulary duty: its pathology block
must be `measured: true`, and the observed event types, tool names, plus
`bash`/`write` argument shapes are checked against the parser. All eight
preserved 2026-09-03 Baseline reprobe transcripts currently read
`unmeasured: unknown_event` because they contain `tool_execution_update`.
That historical mismatch is proof that a non-empty transcript is not enough.
If either new smoke is unmeasured, amend V10 with a discriminating fixture and
test before any budgeted cell.

**3. Spike protocol and V13 firewall [G]** — one page, confirmed before any
budgeted cell. It freezes the mini-probe metric and task rule, the seeded
interleave schedule, expected cell identities, reporting states, and the
reference-only algorithms V13 will use for its primary cell and Envelope
budget. It also records what each spike outcome changes (§4.2).
`ROADMAP.md`'s "Now" bars model cells until the ladder, adapter, arm
definitions, pins and preflight record are fixed, so V11b cannot be skipped
to reach the spike sooner.

**4. Mini-probe** — Baseline only, R1, `n=4`, three tasks, 12 cells,
sequential, unattended overnight.

**5. Spike** — Baseline vs Engine, `n=12` per arm, 24 cells, interleaved,
unattended overnight.

### 4.1 Task selection is frozen before the mini-probe runs

**No usable per-task prior exists.** Block B is a different model and
harness. Overnight block 7's rates are on fixtures that are never named and
cannot be mapped onto the six. `misleading-locus` has nothing at all.
`framing-2` is out because Engine cannot create files. Any task choice made
now would be recall dressed as evidence.

The candidates are `plausible-wrong-fix`, `misleading-locus`, `depth-3`.
The primary metric is successful attempts out of four. Retained-patch
production and conditional retained-patch quality are recorded separately;
the metric never changes after the results appear.

The frozen rule:

1. Exclude an operationally invalid candidate; it has no success count.
2. If any valid candidate is interior (`1/4`, `2/4`, or `3/4`), pick the one
   maximizing `min(successes, 4 - successes)`.
3. If no candidate is interior but any valid candidate is `0/4`, pick a
   floor candidate. A Baseline floor is not a capability wall: the project
   previously recorded Engine gains from Baseline-floor tasks.
4. If every valid candidate is `4/4`, the spike does not run; author R0
   before proceeding toward V12.
5. If no candidate is valid, repair the instrument and repeat no model cell
   until a new confirmed protocol says how.

Every tie uses `misleading-locus`, then `depth-3`, then
`plausible-wrong-fix`. The result may state "no interior count observed among
these candidates"; it cannot generalize that R1 has no headroom. Selecting
from the reference arm alone keeps arm comparison out of the cell choice.

### 4.2 `n = 12`, with the stopping rule fixed in advance

One-sided Fisher exact, computed for this proposal:

```
6/12 vs 1/12   p = 0.0343
8/12 vs 2/12   p = 0.0180
4/8  vs 1/8    p = 0.1410
4/4  vs 0/4    p = 0.0143
```

These values show attainable exact outcomes, not power. At the V13
Bonferroni threshold `alpha = 0.025`, exact enumeration under true rates of
0.50 versus 0.125 gives only about 36% power at `n=12` per arm. The spike is
exploratory, so no significance threshold governs its verdict; Fisher's
one-sided value is descriptive beside the counts and bands. `n=12` is a
fixed spending limit with better resolution than `n=8`. **No extension after
reading the result.** A null is weak evidence about product performance and
no evidence about an isolated mechanism.

The predeclared operational consequences are:

- Engine higher than Baseline: retain the product-path hypothesis and
  continue V12; the spike remains exploratory.
- Tie or Engine lower with a valid instrument: continue the reference-only
  V12 profile, but make the missing Engine test runner a prerequisite before
  interpreting a V13 null as evidence about the Engine composite.
- Both arms ceiling: bring R0 forward before later comparison work.
- Any instrument-invalid batch: repair and smoke the substrate before more
  model work.

### 4.3 Two arms, not three

Baseline vs Engine is the only contrast with a prior (`stringified-annotations`
Engine 6/6 vs 0/6; `local-pings` 2/4 vs 0/4). Envelope's definition is a
decision owed its own proposal and V13 must preregister it; see §2.4.

### 4.4 Confounds predeclared

- **Tool surface.** Baseline holds `read,bash,edit,write`; Engine holds
  `read,edit` and its prompt is wrapped by the handoff builder. The
  comparison is meaningful only stated as *"the shipped Engine versus bare
  Pi as shipped"* — a product-level comparison. No mechanism sentence.
- **A null is uninformative about machinery**, because the missing runner
  may dominate. Written down before running, not after.
- **Grader hunting.** Report `workspace_escapes`, `overlay_windows`, and
  `unmeasured` per arm with the limitations in §2.3; flagged cells stay in
  the denominator.
- **Scheduling.** `run` cannot interleave, and `summarize` needs a
  `summary.json` anchor, so twelve `run --n 1` calls into one directory
  would overwrite it. The committed driver writes one directory per expected
  cell and the strict tally reads exactly those 24 summaries. These scripts
  are part of the instrument even though they stay outside production code.
- **Timeout harvesting.** The Baseline adapter harvests `git diff` only after
  Pi exits. A timeout therefore retains no intermediate patch. Report this
  limit beside retained-patch production; do not infer a capability wall from
  a completion floor under this adapter.
- **Model identity.** Live one-word completion before the batch, never
  `/v1/models`; one omlx process for all cells; model id read back from each
  transcript.
- **Provenance.** Record the evals SHA and an empty `git status --porcelain`.
- **No durations reported.** Counts only.

### 4.5 The firewall between the spike and V13

The `local-pings` precedent is narrower than the earlier draft stated: the
captured task was de-admitted because Baseline 3/8 and Engine 4/8 occupied the
same band, not because its preregistration followed an arm comparison.

The general contamination risk still applies. Before the spike, freeze both
V13 algorithms: the ordered primary-cell selection from V12 reference-arm
data and the rule that maps reference-arm budget evidence to Envelope's cap.
Neither algorithm reads spike outcomes. If the resulting primary cell
coincides with the spike cell, V13 discloses the prior peek and labels the
fresh comparison a replication. Spike cells are never pooled with V13.

## 5. The engine commit — resolved before this revision

Engine is on a clean `main` at `75d4863` ("emit pi `--model` as separate
tokens"). Its stable patch-id is identical to the earlier `d5d5d37` fix, so
the proposal's requested cherry-pick has already landed under a different
commit id. `arms/engine.json` pins `75d4863`; preflight asserts that exact
HEAD plus a clean tree and the extension digests. There is no remaining
maintainer decision here.

## 6. Model ladder status, verified 2026-09-05

**`gemma-4-12B-it-MLX-8bit`** — the model for every cell in this sequence,
and the same model as the V6 and V8 smokes. Verified 2026-09-05 twice: a
direct chat completion (`"OK"`, 19 tokens, load 4.35 s) and **end-to-end
through pi**, which is the path the arms actually take —

```
pi --print --mode json --no-session --model omlx/gemma-4-12B-it-MLX-8bit "Reply with exactly: OK"
# agent_end: provider "omlx", model "gemma-4-12B-it-MLX-8bit", text "OK"
```

Note the two naming surfaces: the server advertises the bare id, pi addresses
it as `omlx/<id>`. The arm definitions record the pi-facing form.

**`gemma-4-26b-a4b-it-8bit`** — download complete and **verified with a real
chat completion** (`"OK"`, 19 tokens, load 9.67 s), not `/v1/models`. All
six safetensors shards present and matching the index; 26 GB. It is a **V12**
concern and is deliberately absent from this sequence.

Current operational state:

- **The durable move is complete.** All six indexed shards are under
  `~/.cache/huggingface/hub/mlx-community/gemma-4-26b-a4b-it-8bit/`, and
  `~/.omlx/settings.json` points `model.model_dir` at the durable
  `mlx-community` directory. The copy under `/private/tmp/mellum-eval/models/`
  is no longer the only V12 prerequisite.
- **A phantom model appeared and then cleared during this session.** The
  first `/v1/models` call on `:8001` advertised
  `gemma-4-26B-A4B-it-OptiQ-4bit`, whose weights exist nowhere on this
  machine. Three later calls, after the 26B had been loaded, list ten models
  and no OptiQ entry. So the stale advertisement was real but is no longer
  present, and the server's listing is **not stable across a session** —
  which is a stronger reason for the real-completion rule than a persistent
  phantom would have been. The harvest-index "preflight that could not fail"
  incident is the precedent. Re-run the real completion, not the listing,
  immediately before V12.

When the 26B enters at V12: name both models in full every time, and never
call the 26B "larger" — it has 4B active parameters. They are capability
points, not a parameter-size scale (`ROADMAP.md:152`).

## 7. Corrections to the earlier draft

Recorded rather than edited away, per `CLAUDE.md`.

1. **"The Engine arm cannot run until `d5d5d37` lands" was wrong.** The
   detached checkout plus editable install meant it could run then; the
   patch-equivalent `75d4863` is now on Engine `main` (§5).
2. **"Dropping R0 is why vendoring can be dropped" was wrong.** R0 never
   needed vendoring for five of six tasks (§2.1).
3. **The `depth-2` task lean had no basis.** Its supposed prior is a
   different model and harness; the "7/12" figure is on unnamed fixtures
   (§4.1). Replaced by a frozen selection rule over a reference-arm probe.
4. **"Cap at the pilot's recorded values" was a misreading** of the
   de-admission record (§2.4).
5. **A three-arm spike was proposed; two is correct** (§4.3).
6. **`4/4 vs 0/4, p = 0.029` was the two-sided figure.** One-sided is
   0.0143. The arithmetic is correct, but the spike is exploratory and has
   no significance threshold; `alpha = 0.025` belongs to V13 (§4.2).
7. **"If all three Baselines floor or ceiling, R1 has no headroom" was
   wrong.** A Baseline floor can be the cell an Engine intervention moves.
   Only an all-ceiling result brings R0 forward; floor candidates remain
   eligible under the frozen rule (§4.1).
8. **A generated contract under each attempt directory breaks batch
   summaries.** Its absolute path changes the recorded command, and
   `compute_summary` refuses mixed commands. Generated bytes now live at a
   deterministic digest-keyed path under the output root (§4, V11a-trim).
9. **A non-empty Baseline transcript does not prove V10 can measure it.**
   All eight preserved 2026-09-03 Baseline reprobe transcripts contain
   `tool_execution_update` and currently return `unknown_event`. The new
   Baseline smoke must fulfill V10's vocabulary duty (§4, step 2).
10. **The leak counters are tripwires, not containment.** File-tool lexical
    escapes omit shell paths, verbatim windows omit paraphrases, and Engine
    still has `read` (§2.3).
11. **An attainable Fisher outcome is not statistical power.** Under true
    rates 0.50 versus 0.125, `n=12` per arm has about 36% exact power at
    `alpha = 0.025`; the fixed `n` is an exploratory budget (§4.2).
12. **The two operational decisions are already resolved.** The Engine fix
    is on `main`, and a complete durable copy of the 26B weights is configured
    (§5-6).
13. **The earlier `local-pings` analogy named the wrong de-admission cause.**
    The captured task was de-admitted because both arms occupied the same
    band. The V13 firewall remains justified prospectively (§4.5).
14. **The generated Engine shape omitted a required field.** Engine requires
    `id` as well as `task`; the generator now specifies both (§4, V11a-trim).

## 8. Cost, and one speedup declined

Roughly two to three agent-days of initial code — less with 1a and 1b in
parallel — at most two unattended nights, and two maintainer confirmation
gates: the combined V11 scope and the later spike protocol. Completing R0,
R2, and creation-capable capture remains additional work at the V12 entry
gate; the trim advances feedback rather than erasing that cost.

Both nights assume the 900 s per-cell ceiling (`workspace.py:28`), not the
expectation. Reading the V8 smoke's actual attempt duration would sharpen
both estimates. That is scheduling arithmetic; the prohibition on wall-clock
is about published comparisons between arms, not about planning.

**Declined:** collapsing the two nights by running Baseline and Engine
interleaved at `n=4` across all three candidate tasks in night 1. It saves
at most one night, and it is structurally "three tasks, two arms, pick one"
— the exact shape §4.5 exists to prevent. The parallelism is better spent on
the code phases, where it costs nothing methodological.

## 9. What is being asked

1. Confirm or amend the revised V11a-trim and V11b-trim scopes (§4, step 1).
2. Confirm the roadmap amendment, the reversal of vendoring, and the explicit
   V12 entry gate (§3).
3. Confirm the mini-probe selection rule, exploratory interpretation, outcome
   actions, and V13 firewall as the basis for the later one-page spike
   protocol (§4.1-4.5).

Implementation starts only after (1). The spike protocol is a separate,
later gate (§4, step 3).
