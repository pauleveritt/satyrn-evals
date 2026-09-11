# Phase V — the evidence is trustworthy, then delivery is verified

**Proposed 2026-09-11. Authorizes no implementation, no commit, and no
inference.** Track A is offline and spends nothing; Track B's live cycle needs
its own budget authorization. This design supersedes the Phase V sketch in
`satyrn-engine`'s `ROADMAP.md` (V1 analysis, V2 authoritative status, V3 budget,
V4 live proof); that sketch must be updated in the same session — a separate
repository, so not the same commit — with each side recording the other's
revision, so the two roadmaps cannot disagree silently.

**Track A is owned here** — it reads retained artifacts this repository keeps;
Track B's `AttemptResult` and budget work is engine-owned and needs mirrored
entries there.

## Why this shape

Phase V was proposed as "analyze the Phase TE transcripts for the next-highest
engine gap, then make validation authoritative and budgets real." A maintainer
redirected its first step on 2026-09-11: *before* extracting new work from the
evidence, establish whether the evidence can be trusted, for both arms,
"spread across multiple cycles... to allow deep focus on narrow issues."

**The evidence supports the numbers; nothing committed derives them.** Both
arms' per-phase figures recompute exactly from retained artifacts — Engine by
splitting at `session` boundaries (`[6,8,10,23]`, `[6,7,9,23]`, `[6,8,11,19]`,
`[6,8,8,14]`), Baseline by counting `turn_start` per `step_id`
(`7/22/6/8 = 43`). No committed command reproduces "9 of 15", "13 of 15
destroyed / 4 of 7 restored", or "6 of 18". Those numbers were derived ad hoc
at authoring time and survive only as prose.

**Six causes, each drawn from the correction record** (twelve correction or
verification commits across Phase TE):

1. **No committed derivation for any forensic number.** Reviewers re-derive by
   hand each pass, each pass differs, and the error runs both ways — the
   redirect-trap count went `1 of 9` → `2 of 9` → `1 of 9`.
2. **The two arms' evidence has different layouts and attribution mechanisms.**
   Baseline carries `step_id`; Engine is positional `session` blocks with no
   label. Two hand-counting methods produced an arm-asymmetric denominator
   (`6 of 8` Engine against all-attempts Baseline, corrected to `6 of 10`).
3. **Measures are re-operationalized per claim, and can miss the claim.** A
   `"== 303"` substring match caught a printed source line and an unrelated
   `405 == 303`; test-file *additivity* was read as tests *passing* and reports
   being *honest*, so a fabricated pytest transcript went unnoticed.
4. **Prose is the transport layer.** An error migrates and a reader cannot tell
   derived from copied; `index.md:234` still read the stale framing while
   `te6-explain-and-decide.md:255` held the correction.
5. **No committed QA for forensic or interpretive numbers.** Committed QA does
   exist for run-time bookkeeping (`turn_ledger`, `check_chain`, `chain.json`,
   `session-record.json`); missing is derivation for what is written *about* a run.
6. **The claims have no home but prose** — no registry of what was claimed,
   against which measure and population.

**A committed instrument was wrong about the Engine arm.** `census.py`'s
`KNOWN_TOOL_NAMES` lacked `run_self_test` (8 unknown-tool hits on screen
Engine-02), `detect_noop_edit` bucketed a rejected edit with a true no-op, and
`pathology.py` shared the staleness. `count_transcript` refused the transcript
as `malformed` — on the leading `adapter_marker` header, not the multi-session
shape (which is real); dropping the header left `unknown_event`, the same
vocabulary gap. **V2b repaired all of it.**

## What this is not

- **Not a re-run of Phase TE.** Track A reads retained artifacts. It authorizes
  no inference and no live spending, and it cannot be satisfied by running
  another attempt.
- **Not a general "improve the instrument" program.** Track A is capped at
  three cycles, and each must end in published findings. The V1 deliverable —
  name the next-highest-value engine gap — is delivered by Track A's findings
  **and the V3 engine gap register**; each inventory finding is a confirmation
  or correction of a published figure, while the register's candidates are
  exploratory hypotheses.
- **Not a new published comparison.** Track A confirms or corrects *published*
  figures; it may not originate a new figure or Engine-vs-Baseline contrast. The
  V3 engine gap register is the one exception: its measurements are exploratory,
  carry their population, and never enter a published claim or denominator.
- **Not a remedy.** Nothing here changes the engine. At the phase level Track A
  may end as `AGENTS.md`'s "instrument only" — no remedy tested, none refused —
  while each of its cycles is findings-bearing. Track B is where a remedy is
  tested.

## Cycles

| # | Cycle | Track | Product | Findings-bearing test |
|---|---|---|---|---|
| V1 | Inventory and the per-phase ledger | A (here) | Claim inventory; shared per-phase ledger for both layouts; unit-level reconciliation | ≥1 inventory claim changes status |
| V2 | Claim-level measures and the denominator binding | A (here) | Claim→measure→population binding; four pure classifiers; vocabulary/structure repair; claim-level reconciliation | ≥1 inventory claim changes status |
| V3 | Close-out and the engine gap register | A (here) | Every inventory claim carries a status; reopen bound applied; **exploratory engine gap register**; Track B gate published | The inventory is exhausted, and the register names ≥1 engine candidate with its measure and population |
| V4 | Authoritative validation status | B (engine) | `Contract.test_command`'s result on `AttemptResult`, independent of model text | n/a |
| V5 | Real turn/deadline budget | B (engine) | Whole-attempt turn limit and wall-clock deadline, retaining partial work | n/a |
| V6 | Live route proof | B (engine) | One bounded orchestrated delivery, `n` frozen at 1 | n/a |

V4–V6 are the original sketch's V2–V4, unchanged in substance. Track B does not
start until Track A's V3 publishes a status for every inventory claim.

### Every Track A cycle must end in published findings

`AGENTS.md` stops the loop after two consecutive instrument-only pieces. Track A
is offline by construction, so the rule binds it. The resolution is an
**object test a later reviewer can apply**, not a reclassification:

> A Track A cycle counts as findings-bearing only if it publishes at least one
> status change against the pre-committed inventory, in the same commit that
> updates the affected source document and every carrier of it **in this
> repository**. A cross-repo carrier is bound by the two-way revision recording
> in the preamble, not by this commit test — the `satyrn-engine` roadmap cannot
> share this repository's commit. A cycle that produces only code does not
> count, and the two-consecutive rule then applies to it.

**V3 reconciliation, 2026-09-11.** The final review adjudicated V3
findings-bearing: the Cycles-table row is V3's pre-committed test, the
zero-corrections clause covers `corrected == 0`, and the reopen of
`c-restored-9-of-15` withdraws a cited TE6 reading. The object test above
binds V1 and V2; V3 is measured against its pre-committed test.

V1 and V2 each settle a share of the inventory; V3 exhausts it. No cycle is
instrument-only, and none is findings-bearing on the strength of its own code.

### V1 — Inventory and the per-phase ledger

**Narrow issue:** which phase a piece of work happened in, counted identically
on both arms; and what has actually been claimed.

**Products, in order.**

1. **The claim inventory, committed before any tooling.** One record per
   published figure or framing that a recorded phase decision rests on, across
   the TE result documents *and their carriers* (`index.md`, `ROADMAP.md`,
   `te6-explain-and-decide.md`), declared in code as a frozen tuple the way
   `scripts/rescore_seams.py`'s `SEAM_MAP` declares its map in advance, with a
   test asserting every cited source path exists. Statuses begin `unreconciled`;
   a human-readable table is generated from the inventory rather than written
   twice.
2. **The shared per-phase ledger**, a new pure module owning phase attribution
   (Baseline: `step_id`; Engine: positional `session` boundaries, cross-checked
   against the chain's declared phase list) and per-phase aggregation of turns,
   tool calls and self-test outcomes. It **refuses** rather than guesses: a
   session count disagreeing with the chain's declared phases is `undecidable`,
   not a per-phase number. `turn_ledger.py` is imported for stream parsing and
   is not changed; its docstring already fixes its contract as whole-stream.
3. **Unit-level reconciliation.** Re-derive every unit-level claim from the
   ledger, correct in place with dated blocks, update every carrier in the same
   commit — `docs/current/index.md:234`, the stale carrier named in cause 4, is
   the first.

**Refusal conditions:** phase attribution undecidable; artifact absent; a
transcript whose session count disagrees with its chain record. Each refusal is a
named status in the table, never a zero.

**Files:** `src/satyrn_evals/phase_ledger.py`,
`src/satyrn_evals/claim_inventory.py`, `scripts/reconcile_claims.py`,
`tests/data/` fixtures, `docs/current/phase-v-claim-inventory.md`.

**Tests:** refusal and success for each layout (a multi-session transcript whose
count disagrees with its chain's phases; a Baseline transcript missing `step_id`;
the four screen attempts and the recurrence batch recomputed to their published
values).

**Deliberately not in V1:** the claim-level measures, the census/pathology
repair, and any figure the ledger cannot settle. Those are V2's.

**V1 reconciled, 2026-09-11.** Seven of the inventory's 20 records now carry a
status; the other 13 are `claim`-level for V2. All seven `unit` records are
`confirmed`: the per-phase ledger recomputes each to its published value
(`corrected` 0, `not_derivable` 0) — the published unit-level numbers hold
under committed derivation. The ledger covers eight retained attempts, not
six: `u-completion-turn-distribution`'s population is the 4 recorded Engine
completions, two of which are the round-2 attempts. V1 is findings-bearing by
the object test: it publishes seven status changes and corrects `index.md:234`,
the stale carrier named in cause 4, in the same tree as the regenerated
`docs/current/phase-v-claim-inventory.md`, which also records the ledger's
`HEAD` revision and the sha256 of every artifact it read.

### V2 — Claim-level measures and the denominator binding

**Narrow issue:** the claim and its measure can disagree, and the population is
chosen at write time.

**Products.**

1. **The claim→measure→population binding.** The most expensive recorded error
   (`6 of 8` → `6 of 10`) is unaffected by any classifier: both values are
   computable, and the error was which population the claim referred to. So the
   deliverable is the binding, with classifiers as its executable backing.
2. **Four pure classifiers**, each returning `undecidable` — never `False` —
   where evidence is absent:
   - `destructive_edit` — separates a replacement from a rejected edit
     (`oldText` did not match) and from a true no-op.
   - `restoration` — the destroyed content returned before the phase ended.
   - `self_test_outcome` — Engine: the `run_self_test` call and `chain.json`'s
     independently recorded per-phase outcome. Baseline: **specified or
     refused** — no `chain.json`, self-test runs are `bash` calls, reports are
     message text; a Baseline-side measure that cannot be proven in both
     directions from retained artifacts returns `undecidable`, and V3's table
     records that as an arm-asymmetric-evidence finding rather than improvising
     a detector.
   - `verification_claim` — what the implementer said about its own
     verification, against what the retained tool results show.
3. **Vocabulary, structure and discovery repair** in `census.py` and
   `pathology.py`: the tool vocabulary above; a specified behaviour for
   multi-session concatenated transcripts; and **discovery of the Engine arm's
   retained transcript** (`.satyrn-implementer-transcript.jsonl`; 24 on disk,
   zero `transcript.txt`), where `census_root` returned **0 cells** so the
   `8 unknown tools` was visible only by a direct detector call. This satisfies
   `BACKLOG.md`'s first entry and creates no arm-neutral rate.
4. **Claim-level reconciliation** of the inventory's remaining claims.

**Evidence standard.** Each classifier is proven on the retained counterexamples
the correction record already found: the `405 == 303` string, the rejected
`edit`, the fabricated "2 passed" report, and `check_chain`'s "implementer
window never observed". Fixtures are trimmed real transcript excerpts committed
under `tests/data/` with their source attempt path and digest recorded — the
precedent set by `tests/data/real-hp7-live-route-transcript.jsonl` — plus a
marked integration check running the same measures against the full retained
artifacts present on disk, and saying so loudly when they are not.

**Files:** `src/satyrn_evals/claim_measures.py`, `census.py`, `pathology.py`,
`tests/data/`, `scripts/reconcile_claims.py`.

**V2a reconciled, 2026-09-11.** `ClaimMeasure` and `measure_inventory(records)`
bind every claim-level record, defaulting to `undecidable` — a finding, not a
zero. Three measures are wired:

- `c-destroyed-13-of-15` (`destructive_edit`, 15 phase-4-reaching Engine attempts):
  derived **15 of 15**, not the published 13 of 15 — **`claim_measure_mismatch`**.
- `c-restored-9-of-15` (`restoration`, same 15): derived **3 of 15**, not the
  published 9 of 15 — **`claim_measure_mismatch`**.
- `c-fabricated-report-n1` (`verification_claim`, screen-engine-01): `no`
  (summary "2 passed" over last `run_self_test` exit 1) — `confirmed`.

**The mismatch finding.** The classifiers measure a broader property than the
published route-specific counts, so they neither reproduce nor contradict
13 of 15 and 9 of 15; V3 must decide whether to narrow the classifiers or
restate the claims.

The 13 claim records now carry **1 `confirmed`**, **2 `claim_measure_mismatch`**,
**10 `not_derivable`**, **0** `corrected`/`unreconciled`; with the 7 unit records
the tally is **8 `confirmed`**. No V2a classifier covers the 10 `not_derivable` measures: `completion_rate`, `population statement`, `redirect_trap_resolution`, `redirect_trap_occurrence`, `denominator_binding` — V3 findings, not zeros.

**V2b reconciled, 2026-09-11.** Two parts landed: the census/pathology repair
(product 3) and the denominator binding (product 1, deferred from V2a).

**Repair.** `census.py` gains `run_self_test`, splits a rejected edit from a
true no-op, and discovers the packet route's implementer transcript;
`pathology.py` accepts the adapter-marker header and names the multi-session
shape. All 24 packet-route transcripts now read `multi_session`, `unknown_tool` 0.

**Denominator binding — `not_derivable`.** The `6 of 8` → `6 of 10` correction
needs the current-prompt population. The 8 phase-4-reaching attempts enumerate
deterministically by full four-phase packet fingerprint; the pre-phase-4 chains
retained only phase-1/phase-2 packets byte-identical across prompt states, so
their membership is readable only from run directory names, which the
reconciliation refuses as evidence. `c-phase4-denominator-6-of-10` therefore
stays `not_derivable`, naming the missing enumeration; the published `6 of 10` is
neither reproduced nor contradicted.

V2b is **instrument only**, 2026-09-11: it changed no inventory status, so it is
the first consecutive instrument-only piece — V3 must be findings-bearing on the
test it pre-committed, or a second consecutive one stops the loop.

### V3 — Close-out

**Narrow issue:** nothing is left unaccounted for, and the reopen decisions are
made once, on the record.

**Products** (`docs/superpowers/plans/2026-09-11-phase-v3-closeout.md`): one
final status per record, each `not_derivable` naming its missing artifact; no
carrier lagging its source; the reopen bound applied to each affected recorded
decision; the **engine gap register**
(`docs/current/phase-v-engine-gap-register.md`), whose rows are labelled
`exploratory`, are excluded from every published claim and denominator, and are
the discovery input Track B acts on; and the Track B gate — an enumerated
inventory with a status for every entry.

**Zero corrections is a pass.** If every claim confirms, the finding is "the
published numbers hold under committed derivation," and Track B opens on that.

**V3 closed, 2026-09-11 — findings-bearing.** The inventory is exhausted: all 20 records carry exactly one
final status — **8 `confirmed`, 0 `corrected`, 10 `not_derivable`, 2 `claim_measure_mismatch`** — and the
Track B gate is published as `docs/current/phase-v-track-b-gate.md`, whose `missing` column names what each
refusal waits on: `c-completion-6-of-18` (hidden-grader verdicts across all 18 Engine attempts),
`c-completion-4-of-16` (hidden-grader verdicts for the 16 pre-screen attempts), `c-baseline-3-of-3`
(matched-repeat Baseline attempts under the final prompt), `c-contemporaneous-screen-tie-2-of-2` (an outcome
measure executable from transcripts), `c-nonrestore-0-of-6` (a completion verdict per non-restoring
attempt), `c-restore-4-of-7` (a completion verdict per restoring attempt), `c-redirect-fixed-1-of-9` (a
redirect-trap resolution classifier), `c-redirect-6-of-9` (a redirect-trap occurrence classifier),
`c-phase4-denominator-6-of-10` (prompt-state membership for the pre-phase-4 chains), `c-engine-population`
(a measure binding the population statement to an attempt set).

No carrier lags its source — path existence, a hard failure — and the six `quote_drift` entries are
published for review on the gate page rather than silently passed: five paraphrase the figure without its
literal string, one is a hard line wrap.

**Reopen decisions** (bound: at most one reopen per claim per reconciliation). `confirmed` and
`not_derivable` records reopen nothing; 18 records leave every recorded phase decision standing.

- **`c-destroyed-13-of-15` — not reopened.** It supported TE6's attribution of destructive-edit-then-restore
  as a characterized Engine failure mechanism (`## Attribution`). The committed classifier is
  transcript-level and finds 15 of 15 — broader, and in the same direction — so no support is withdrawn,
  the classifier is not narrowed, and the published count is not restated.
- **`c-restored-9-of-15` — reopened, once.** It supported TE6's trace-backed reading that the pattern is
  "mostly, but not purely, productive recovery," which cites exactly "9 were restored before the phase
  ended and 6 of those 9 completed." That derivation is ad hoc (cause 1) and the committed classifier
  returns 3 of 15 under a different operation, so the reading may not be cited again until a narrowed
  classifier or a restated claim exists. The reopen publishes this corrected record, spends the bound's
  single reopen here, and authorizes no live spending.

The **engine gap register** is published as `docs/current/phase-v-engine-gap-register.md`: four exploratory
candidates, each with its measure, population, observed value and proposed change, and none entering a
published claim or denominator.

**Findings-bearing, on the test this design pre-committed for V3** — the Cycles table's "the inventory is
exhausted, and the register names ≥1 engine candidate with its measure and population". What changed: the
inventory is settled at 20 of 20 records, every refusal now names its missing artifact, the reopen decisions
are made once on the record, the carrier audit runs, and the gate and register are published. V3 publishes no
new status change — the two `claim_measure_mismatch` statuses were settled in V2a and are final here — so it
rests on exhaustion rather than the object test above. **Track B's gate is published: V4–V6 may start.**

## Governance

**The reopen rule, bounded.** Accepted 2026-09-11: a corrected count reopens the
claim it supported. Bounded so it cannot cascade:

1. It reopens only claims a **recorded phase decision** rests on, not every
   number in every document.
2. Corrections are recorded in place with dated blocks; the original text is not
   rewritten.
3. Every carrier of a corrected claim **in this repository** is updated in the
   **same commit** — the `index.md:234` staleness is the failure this prevents —
   and a cross-repo carrier follows the revision-recording rule below.
4. `archive/` stays closed. It is evidence, never a live surface.
5. One reopen per claim per reconciliation. A reopen publishes a corrected
   record and authorizes **no live spending**.

**Cross-repo bookkeeping (an explicit checklist item, not a V1 code task).**
This design supersedes the Phase V sketch in `satyrn-engine`'s `ROADMAP.md`. On
confirmation:

1. Update that sketch to this design's V1–V6.
2. Record this repository's design revision in the engine roadmap entry.
3. Record the engine repository's resulting revision here in a dated block —
   the two-way recording the preamble requires.

**Done, 2026-09-11.** `satyrn-engine`'s Phase V row is updated to this design's
V1–V6 and records `satyrn-evals@2d20aac`; the engine repository's revision
`satyrn-engine@fd92eca` records the reverse. Both recordings exist, so the two
roadmaps cannot disagree silently.

**No new contrasts.** Track A confirms or corrects a published figure and never
originates one; every row carries its population statement, including the
asymmetry — Engine's 18 attempts were run adaptively, Baseline's 2–3 fresh — so
a rate that hides that is the error. The register's `exploratory` rows stay the
exception named above.

**Currency.** V1 records the digest of every artifact it reads and the `HEAD`
commit it read them under, per `AGENTS.md`'s currency rule, before measuring.

## Limits

- **Counting better does not fix an asymmetric design.** Baseline's n=2–3 is
  not repairable by any seam. If Track A's reconciliation makes any
  Engine-vs-Baseline rate look comparable, Track A has failed its own rule.
- **Some claims may be undecidable.** A `not_derivable` status is a finding, not
  a failure, when the artifact was never retained.
- **Track A changes no engine behaviour.** It can end with no remedy tested and
  none proposed; that is the phase's declared first step, not a shortfall. The
  cap and the findings test keep it out of the overnight-run failure mode
  (`AGENTS.md`: four consecutive instrument cycles, no remedy enabled or tested).
- **The census repair is instrument work.** It is recorded as debt, scoped to
  what V2's measures need, and it is `AGENTS.md`'s second category: permitted
  when it blocks the measurement in hand.

## Review round

Reviewed 2026-09-11 by GLM 5.3 (`zai`) at `xhigh`, working tree `82da340`.
Twelve findings; dispositions recorded. **Accepted:** the inventory precedes
tooling and includes carriers; the earlier claim that `census.py` "already
distinguishes" a rejected edit was wrong; the denominator binding is the real
fix; Track A confirms or corrects but does not originate; all four reopen
bounds and the exit condition; the citation, commit-count, doc-cap and
cross-repo-bookkeeping corrections. **Scoped correction:** forensic and
interpretive numbers, not all QA. **Resolved differently:** every Track A cycle
publishes reconciliation findings (the object test), rather than merging V1+V2.

**Maintainer verification, 2026-09-11** corrected two attributions — the
`malformed` cause (header plus vocabulary gap, F1) and `census_root` discovery
(F2, folded into V2 product 3) — and scoped the carrier-commit test, reworded
`verification_claim` as a binding, and made the cross-repo roadmap update an
explicit checklist item.
