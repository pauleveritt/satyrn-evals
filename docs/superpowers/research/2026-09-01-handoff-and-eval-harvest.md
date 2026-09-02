# Harvest: handoff packet and eval design, from `local-ai-pi` and `swiftstar`

**Date:** 2026-09-01
**Status:** spike notes — **input to brainstorming, not a design and not a plan**
**Sanitized for a public repository.** One of the two source repositories
(private repo) and a third referenced below (private repo) are **private**.
Their internal file paths, verbatim text, and unpublished measurements are
deliberately **not reproduced here** — only the transferable design lessons,
which are ours to state. Where a claim rests on private evidence this note says
so and points at the repository rather than quoting it. `local-ai-pi` and
`satyrn-engine` are public and are cited normally.

**Method:** read-only survey of two evidence repositories, plus a small
measured probe recorded separately in
[`2026-09-01-agentclinic-spike.md`](2026-09-01-agentclinic-spike.md).

Nothing here is a commitment. The purpose is to put the prior art in one place
so a brainstorm can start from what is already known rather than re-deriving
it — which this spike did **four** times in one afternoon (§5).

> **Revised after adversarial review, 2026-09-01.** This document was
> assembled from subagent research reports rather than from first-hand reading
> of the sources, and a review against the primary sources found real defects:
> a headroom comparison presented without the source's own "does not establish
> a difference" verdict (§3), two items wrongly listed as refuted (§7), an
> unverifiable word-count figure (§5), a field count, and several quotations
> taken from passages their own documents later retract. Those are corrected
> in place and marked. Most quotations and numbers did verify; the ones that
> did not are called out where they appear. Treat any remaining unmarked
> claim as second-hand until checked against `branch:path:line`.

## 0. Provenance and how much to trust each source

| Source | What it is | Trust |
| --- | --- | --- |
| `local-ai-pi` `oracle-repair` | Gen-1 packet, chapter prose | **Numbers withdrawn**; mechanism findings stand |
| `local-ai-pi` `pre-restructure` | 3-phase specs, references, per-phase suites | Fixtures good; SP2 numbers superseded |
| `local-ai-pi` `main` | Gen-3 typed contract, harvest index | Current |
| `swiftstar` (**private**) | Gen-4 packet type, campaign discipline, repair fixtures | Current; contents not reproduced here |

**Four** generations of the handoff artifact exist. **Do not conflate them.**
The Gen 3 → Gen 4 lineage is source-attested; the Gen 1 → Gen 2 numbering is
this document's narrative, not a distinction either source draws.

1. **Gen 1 — prose "packet"**, four `##` sections, model-authored
   (`pre-restructure:prompts/orchestrator.md`).
2. **Gen 2 — hardened prompt**, same four sections
   (`main:improvements/sdd-orchestrator/orchestrator.md`).
3. **Gen 3 — typed handoff contract**, JSON/YAML, validated before any model
   call (`main:extensions/implementer/handoff-contract.ts`,
   `main:harness/typed_contract.py`).
4. **Gen 4 — `HandoffPacket`**, **12** stored properties, `Codable`, captured
   to disk (private repo; path withheld).
   (Corrected from "13 typed fields".)

`local-ai-pi`'s SP1/SP2 arc (0/8 → 3/8 → 5/8) is **retracted** — the oracle
behind it failed textbook-correct solutions — and the source transcripts
(~455 MB, 46 sessions) were deliberately deleted with an inventory. Treat
those claims as *recorded, not reproducible*.

## 1. The packet, as it ended up

### Field set (Gen 4)

`taskText`, `writableFiles`, `validationCommand`, `selfTestCommand`,
`baselines`, `turnBudget`, `toolCallBudget`, `textContract`, `facts`,
`redacts`, `role`, `sampling`.

Gen 3's equivalent adds `readableFiles`, `preservedBehavior`, `knownFacts`,
`removableSymbols`.

### The three-way split — the most transferable idea in either repo

- **Authored** by a human or the decompose role: task text, `facts`,
  `redacts`.
- **Host-computed**, never model-computed: `writableFiles`, budgets,
  `validationCommand`, `sampling`.
- **Derived** at dispatch time by reading the worktree: `baselines`
  (per-file sha256 + line ending + mode) — read from the worktree at dispatch
  time and never guessed or accepted from input.

Stated doctrine, paraphrased: even when a model authors the packet, it must
not be the thing that computes the writable manifest, the budgets, or the
validation command. The model supplies
judgment; it never computes its own permissions. Its prose is parsed by the
same deterministic splitter the host uses, so the intended property is that it
can only fail closed. **Caveat from that same source:** a later review found
the splitter actually failed *open* for the most probable input, and the
"fails closed" claim was false until fixed. Take the principle, not the
guarantee.

### Decisions the sources landed on (recorded, not adopted)

- **`facts` pre-empt deliberation.** Ambiguity converts directly into
  deliberation for some models, so an unstated contract is a cost rather than a
  neutral omission. One recorded failure burned tens of thousands of characters
  of reasoning on a single unstated environmental question. The fix pinned the
  *consequence* the model was agonising over, not just the mechanism.
- **Facts must be rendered, not merely stored** — only `taskText` is sent, so
  a fact left in a struct field is a no-op. Assembly order puts facts first.
- **`redacts` are checked across every channel the worker sees** — task text,
  each fact, both commands, and each writable path — and validated on the
  **assembled** packet, never the authored fragment, because the contamination
  that motivated the gate lived in appended content.
- **A fact contradicting a redaction is an error, not a warning.**
- **Hand-written decoder** so packets stored before a field existed still
  replay. A synthesized `Codable` treats a missing key as an error and would
  break every stored artifact the day a field is added. This bears directly on
  our "grading must be re-runnable against stored artifacts" rule.
- **Validate before the model loads, and again on the packet actually
  dispatched.** A refusal is free; a wasted run looks like data.
- **The validator ships its own limitations in its own docstring:** the check
  is verbatim and case-sensitive, so a restated fix passes it, and a spec left
  on disk defeats it entirely. It is described there as a tripwire for the
  mistake that actually happened — explicitly not a proof of ignorance.

### The verdict

Pure, no I/O, ordered, with the order documented as load-bearing: contract
violation → budget → validation → no-changes → candidate. Contract violation
outranks budget so that a contract violation is always reported even when the turn also blew its budget. At the budget limit (`==`) the turn is still a
candidate. Refusals are typed; what folds back to the orchestrator is a candidate reference or a refusal reason — **never the worker's transcript**.

### `validation` belongs to the parent

**`validation` is what the parent runs; the implementer never runs it.**
The "false passes" examined in `local-ai-pi` turned out to be
**validation-command drift** (shown for two post-tuning runs, inferred from
result text; the transcripts were later deleted, so treat as recorded rather
than reproducible — an earlier draft said "every") — the packet said `uv run pytest -q`, the implementer ran
`uv run pytest -q tests/test_app.py`, which passed in isolation and failed
under full collection. Originally misdiagnosed as dishonest reporting;
corrected in place to: a packet/validation-specification bug, not a dishonesty
bug.

## 2. Eval design

### Three outcomes, not two

`pass` / `fail` / `harness-void`, plus `unauditable` as a distinct state
inside the validity checker.

- "No usable output from the model" (e.g. contract not followed) is a
  **fail**.
- "The instrument broke" is a **void**, excluded from the denominator.
  Its absence is what made an early all-zero result describe the harness
  rather than the model.
- Any analyzer error, timeout, or bad JSON defaults to **void**, so
  instrument failure can never become model failure.
- **Voids stay re-runnable.** Closure means *graded*, not "has a row" —
  otherwise one broken engine permanently fixes n at whatever ran before the
  breakage. A stale binary did exactly that to a dry run there.

### Pre-registration, as actually practised

A committed file written **before** the first cell, carrying hypothesis, N,
config, oracle, seed range, decision bands, and a compromise threshold
(for example, declaring the run compromised if voids exceed a pre-set share of
attempted cells).
Two standing invariants: **a recorded cell is never re-run or overwritten**,
and **debugging seeds are disjoint from measured seeds** (a reserved debug range that appears in no manifest) so a diagnostic run can never consume a measured cell.

One manifest states its own power honestly — at its n it is an *estimation*
instrument, not a hypothesis test. Another pre-registers a three-band decision
rule and then honours it against a near miss, recording that the near-miss
result is dead and not to be revisited, because re-running until an endpoint
clears its bar is the trap the discipline exists to prevent.

### Negative controls

- A **single-file control** that must *not* move; a drop there voids the arm.
- A **paired control with exactly one function reverted**, with the exact
  revert instructions committed — because a previous control branch was
  deleted, which is exactly the evidence-hygiene failure that cleanup effort was about
- The **null arm named as distinct from the control**.
- Best idea in either repo: **a negative control on the probe itself.** The
  preflight asks the engine to accept a canary flag that cannot exist and
  fails if it is *not* rejected — without it, a changed error string would make the check above a permanent silent pass

### Reporting

Prefer a **concurrent control on one binary** over a frozen baseline: a frozen
baseline caps power at *its* n and leaves an irremovable binary-drift
confound. Report **failure-mode incidence per named mode**, not just success
rate — the decisive example is two prompt variants of one suite differing by
wording alone, success 16/16 both times (saturated, reports nothing) while hang
incidence went 0/16 → 6/16 and mean turns 10.8 → 24.2.

## 3. The headroom question, already answered elsewhere

A private companion repository measured the same prescriptiveness dial on a
larger model through an orchestrated path. **Its figures are not reproduced
here.** What is reportable, and what matters for us, is its own stated verdict:
the two arms' confidence intervals **overlap**, so that work does **not**
establish a difference between the detailed and user-story specs — only that a
generalization bar was not reached. Its pass criterion also required a
delegation to have occurred, which is a stricter bar than acceptance alone.

So the middle-band evidence this project owes is **not** already sitting in
that repository, and an underpowered non-difference there should not be cited
as if it were.


## 4. Failure modes to build against

### 4.1 A run where the mechanism never engaged, graded `accepted`

`--extension` pointed at a directory; the subagent tool silently never
registered; the parent wrote the whole solution itself; exit 0, empty stderr,
**graded accepted, 4/4 tests**. *"The dangerous part is not the failure, it is
the grade."* The source's response was **`no-delegation` as a first-class outcome** —
which predates this incident rather than being invented for it, and which the
same corpus also files as a **hazard**: *"a plain baseline profile scores 0/8
by definition — even if every run passed pytest. This structurally rigs future
guardrailed-vs-plain comparisons."* The generalization *any run where the
mechanism under test provably did not engage must be labelled, never averaged
in* is this document's paraphrase, not a quotation, and it carries that
double-edge.

### 4.2 A void that can hide a pass

A private companion repository has a recorded case where a cell was scored as
an instrument void while its own underlying grade was a clean pass — a
discard rule voiding a candidate that had actually succeeded. The detail sits
in that repository and is not reproduced here; it is flagged there by its own
authors as open.

The transferable form is the part we need: **a scorer that drops passes is
worse than one that drops fails, because it flatters the result.** If a void
class is adopted here, a test for "a void concealing a pass" is the first one
to write. This is not hypothetical for us — the overnight run produced the
mirror case, a void concealing a *fail*, within one block.

### 4.3 A pre-registration needs a closing ritual

Also observed in that private repository, and stated here only in the
generalizable form: a pre-registered arm can run to completion, with its
decision rules and a regression tripwire fixed in advance, and then have **no
committed document that applies those rules to the result**. The rules do not
enforce themselves.

The lesson: **a pre-registration needs a closing ritual** — a required verdict
written against every rule, including the ones that did not fire — or the
discipline silently degrades into a document nobody checks against.

### 4.4 "The harness, not the model" — counted four times

That repository counts this as a recurring failure class in its own record —
scoring a run, then reading the score as a fact about the model when the
harness dominated it — and reaches at least a fourth instance. Related: a model "pathology"
that reproduced perfectly turned out to be an engine false positive (a 64-byte
comment separator tripping a degeneracy guard; **all 5 voided cells ended on a
one trivial textual cause), struck through in place, with the note that misfiling it was the mistake worth
remembering.

### 4.5 Prompts that make the model wrong

A repair directive asserted an unconditional claim that exactly one file was wrong; the
model **cited that text back verbatim to justify not making the correct
multi-file fix**, across nearly every cell of that arm. The fix deliberately
names **no number at all** — naming a different number would just repeat the original mistake in the other direction
Four instances of under-specified authored prompts were counted in one day.

### 4.6 Determinism ephemera

Two runs at the same seed produced different prompts because of a worktree
UUID in a traceback and pytest's `in 0.20s` timing line — one run repaired where the other failed, differing only by that ephemeral line. **Normalize ephemera before capping**, so byte
offsets don't shift; tail-truncate logs, **middle**-truncate file bodies
(a fix is as likely at the end as the start), and mark the drop inline.

### 4.7 Rounds that were not rounds

`head` never advanced on `.validationFailed`, so multi-round repair collapsed into N independent single-shot attempts from the same base, across a large share of that batch. And exhaustion graded the **pre-repair** tree, so the verdict described
a tree predating every repair round, in **every affected cell** affected cells.

## 5. What this spike re-derived that was already written down

Recorded here because the repeat is the finding.

1. **Detailed AgentClinic ceilings for Gemma.** Already at
   [`2026-08-26-product-path-pilot.md:156`](2026-08-26-product-path-pilot.md) —
   *"the old evidence already places detailed AgentClinic at a 16/16 ceiling
   for it."* We spent eight sessions confirming it.
2. **A spec that omits the framework yields Flask.** Recorded in
   `local-ai-pi` (five of six runs, `TypeError: Flask.__call__()`), corrected
   to *"the withheld fact that matters is the framework, not the filenames"*,
   **and**, independently, in a private companion repository, which lost a
   whole arm the same way. We hit it a third time.
3. **Facts work; rules of conduct do not.** The five interventions and the
   3–2 tally are the source's. **Our claim to have "reproduced this exactly"
   is withdrawn.** The imperative wrapper *did* change behaviour — zero tool
   calls became a complete application — and there was no Flask arm before it,
   so the two interventions are sequential repairs, not a controlled contrast.
   Each fixed the failure it targeted. The tally is also contestable in the
   source's own words: it files one of the five as a rule of conduct while
   describing it as *"a single unambiguous sentence about a checkable
   **fact**"*. And the accompanying word-count figure could not be reproduced
   from any diff in either repository — treat it as unverified.
4. **The user-story suite at 15/16 once the facts are supplied.** Recorded in
   `local-ai-pi`, whose roadmap says that suite *"has no headroom"*. The later
   arm in the spike re-derived it — the fourth instance, and the one that most
   undercuts §3.

The common cause: `BRIEF.md` and `ROADMAP.md` were read; the research
directory was not searched for the task name before probing. **A cheap
pre-probe ritual — grep the research directory for the workload and the model
— would have caught all three.**

The practice worth copying from that repository: **an arm is stopped as soon as
one cause is confirmed for every failure**, rather than run to a larger n
confirming the same bug repeatedly.

## 6. Open questions for the brainstorm

Framed as questions, not proposals.

1. **Do we want a packet at all yet?** The instruction was to start *without*
   the orchestrator. A packet with no orchestrator is just a task manifest
   with `facts` and `redacts` added — is that the useful first step, or is it
   machinery ahead of its contract?
2. **What is the smallest useful subset of the 13 fields?** `facts` and
   `redacts` have incident evidence behind them. `removableSymbols`,
   `preservedBehavior` and `acceptanceStrings` have **no measured incidence
   data in either repo** — design responses to named incidents, not validated
   fields.
3. **Does our `capture` grow a cumulative mode, or do cumulative tasks stay
   hand-authored?** Today's spike found `capture --revert` silently reduces a
   14-test cumulative suite to a 3-test oracle, demonstrated exploitable.
4. **Do we adopt void/fail separation now?** It is the single highest-value
   eval-design import, and it comes with a known defect to test against (§4.2).
5. **Is effort the primary measure on a saturated task?** The 27-word / 0-vs-6
   precedent says success rate "cannot" report on a saturated workload.
6. **Which model is the subject?** Detailed AgentClinic is saturated for
   Gemma (recorded, and replicated). It was **never measured** for DeepSeek
   Flash — an earlier draft asserted it; DeepSeek ran only the user-story arm
   at n=2. Mellum2-12B-A2.5B (~2.5B active) is the model the original
   observation was about; it appears in the local oMLX model list, which is
   not the same as verifying it loads and runs.
7. **More phases, or harder prompts?** Both are in scope. A third axis is the
   repair-role fixtures held in the private companion repository — bugs whose
   traceback does not quote the defective line, and whose obvious correction is
   wrong. The overnight run has since probed these; see the overnight record.

## 7. Refuted — do not rebuild

- **A second model hop between a packet's author and its recipient** —
  **downgraded**: one recorded incident (n=1), in which a parent paraphrased
  `Run Phase 1` into `read the specs and provide a summary` and no implementer
  launched. The source draws a narrower lesson (a handoff packet is
  trustworthy when its author is its sender) and **explicitly retains a
  dedicated orchestrator for production**: *"a dedicated orchestrator and
  mechanical verifier are still worthwhile because they move loop control
  outside the SLM."* Not refuted.
- **A contract-blind path guard.** Built, shipped, removed — it refuses
  contract-authorized renames the engine would admit: a guard with less information than the authoritative layer is not defence in
  depth.
- **A repeat-breaker keyed on failures** — a design caution, never built and
  therefore never refuted by trial. The evidence is 245 identical
  **successful** `ls -R` calls: a breaker counting only failures would never
  fire. The shipped breaker counts regardless. Keep "repeat" and "churn" as
  separate concepts.
- **Full parent-session capture as the primary artifact** for delegating runs
  — a **cost note**, not a refutation: 62 MB for one run, and it still lacks
  the child's stream. Note this collides with our own `BRIEF.md` rule 3, which
  requires transcript persistence; the lesson is about what to treat as
  *primary*, not about dropping capture.
- ~~**Trusting guards to fire.**~~ **Removed from this list on review — it
  does not belong here.** The zero-fire observation is real (24 runs, two
  suites, loading verified by digest, while a composite pipeline's 0/16 → 13/16
  lived elsewhere), but the source's own sentence is *"Carry this as
  calibration, **not as a reason to drop them**."* Guards demonstrably fired
  and arrested runaways once delivered to the child: a loop breaker fired 12
  times across two runs that both still passed, and cycle 10 recorded 10 and 2
  refusals in its children — *"the only intervention that has demonstrably
  arrested a runaway."* The 24-run zero-fire was on ceiling/floor suites where
  there was nothing to fire on.
- **Naming a tool only in prose.** A model ignores a tool that is named only in prose and is absent from the engine's advertised schema — recorded there as zero dispatches across dozens of tool calls

## 8. Where the fixtures live

the private repo's packet type is the best-packaged copy: one cumulative
13-test acceptance suite, full 3-phase reference, `broken/app.py`, three spec
variants (`roadmap.md`, `roadmap-user-story.md`, and a *more* prescriptive
`roadmap-user-story-mellum-decomposed.md`), six seeded `repair/` bugs authored
there rather than transplanted, and a `PROVENANCE.md` recording the recovery
commits (`roadmap.md` ← `8af05f8`, user-story ← `191895e`) and dep pins
(fastapi 0.115.10, pytest 8.3.4, turbohtml 1.5.0).

`local-ai-pi` `main` keeps **only Phase 1**; Phases 2–3 live on
`pre-restructure`.
