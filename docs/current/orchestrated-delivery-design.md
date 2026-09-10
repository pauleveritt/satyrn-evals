# Orchestrated delivery: adapting SwiftStar's exercised design to Satyrn

Proposed 2026-09-09, revised the same day. **This authorizes no
implementation, no merge, no commit and no inference.**

Two things it supersedes. It replaces Part 2 of
[the next-agent brief](next-agent-brief-engine-on-phased.md), which scoped
Engine holding one long conversation; that survives only as a comparison
condition. And it replaces this document's own first revision, which proposed
designing an orchestrator architecture. **That was the wrong shape of work.**
SwiftStar has already built and exercised this architecture. The remaining
question is not whether it can work; it is whether a Satyrn implementation
makes real development better, and which part earns its cost.

## The design, in one line, already written

`WorktreeTransaction` states it exactly: each phase runs in a disposable
worktree branched from the **prior phase's commit** rather than `HEAD`, so
"the code folds forward through the checkout, while context folds forward
through the packet"
(`swiftstar/Sources/SwiftStarAppKit/WorktreeTransaction.swift:4-12`). On a
phase receipt the transaction stops with no partial chain.

That is the property this phase is for, and **satyrn-engine should borrow the
isolation, not re-derive it.** The engine already produces a candidate change
without touching the caller's tree (`satyrn-engine/BRIEF.md:15`); what it
lacks is the chaining of one candidate onto the last.

## What already exists, and where

Verified by reading the implementation, not by recall:

| Capability | Where |
|---|---|
| Typed handoff packet: objective, writable files, validation command, optional worker self-test command, per-file baselines, turn and tool-call budgets | `swiftstar/Sources/SwiftStarKit/HandoffPacket.swift:62-72` |
| Host-enriched packet building from the orchestrator's own tool call | `swiftstar/Sources/SwiftStarKit/DispatchPacketBuilder.swift:1-12` |
| Phase-chained isolation ending in one candidate ref | `swiftstar/Sources/SwiftStarAppKit/WorktreeTransaction.swift:4-20` |
| Per-file baselines as the worker's mutation guard | `swiftstar/Sources/SwiftStarKit/HandoffPacket.swift:66-69` |
| Model-driven loop: decompose, dispatch, read receipts, validate, write | `swiftstar/docs/superpowers/specs/2026-08-27-p20-orchestrate-loop-design.md:74` |

The worker gets `read`, `write` and `edit` and **no** `bash`, with every
mutation revision-checked against the packet's writable files
(`HandoffPacket.swift:67-69`).

## The live evidence, recomputed here

Five orchestration result files, tallied by outcome. These are separate
conditions and reruns, **not** a pooled success rate, and they must never be
added together.

| Campaign | pass | fail | harness-void |
|---|---|---|---|
| Initial roadmap | 23 | 2 | 5 |
| Roadmap timeout reruns | 4 | 0 | 1 |
| Initial user story | 0 | 3 | 1 |
| User-story context fix | 0 | 0 | 5 |
| Later user story | 6 | 3 | 1 |

Recompute, from a `swiftstar` checkout:

```bash
awk -F '\t' 'FNR>1 {n[FILENAME FS $4]++} END {for (k in n) print k,n[k]}' docs/superpowers/research/experiment-results-orchestrate*.tsv
```

**`harness-void` is a historical classification and is not audited here.**
**Thirteen** of the 54 rows carry it — corrected 2026-09-09 from "eleven",
which was written rather than computed; the table above sums to thirteen and
so does the recompute. One whole campaign, the user-story context fix that
was meant to confirm the Flask repair, is **5 of 5 void**, so that repair is
confirmed only by the later arm. Whether each void deserves exclusion is
unestablished, and by this repository's own standard a void that hides a fail
is a named instrument defect. Any Satyrn record citing these counts must
carry the void column and this sentence with them.

## Two limits that shape the whole phase

**Limit 1 — the campaign does not exercise the full application path.** The
headless driver reuses the harness's global writable scope and vetted
commands rather than the model's own per-phase `writableFiles` and
`validationCommand`, and says so in place: a "harness simplification (verdict
caveat)" comment naming the app's real path as the one that respects them
(`swiftstar/Sources/swiftstar-agenttest/main.swift:1297-1305`). So the
campaign demonstrates a working orchestration workflow. It does **not**
jointly validate packet authoring, isolation and candidate integration.

**Limit 2 — workflow success does not establish implementer contribution.**
Seed 221 passed after dispatching three phases, and all three phases report
**0 mutations**
(`swiftstar/captures/agenttest/20260829-212715-roadmap-user-story-directive/campaign-stdout.txt:14-16`).
The retained lines show zero worker mutations and a pass. **That the
orchestrator issued the writes is an inference** from the loop being
model-driven with the orchestrator writing files, not something those lines
state. An orchestrator that delivers the application is a useful product; it is not evidence that delegation
improved quality or reduced cost. **A Satyrn result that cannot separate "the
workflow delivered" from "the implementer delivered" is not a result.**

**A related trap, recorded by SwiftStar against itself.** Its pool notes that
recording a packet's declared `think` while not sending it on the wire "was
itself a new capture-integrity lie"
(`swiftstar/Sources/SwiftStarAppKit/PoolOrchestrator.swift:70-78`). Packet
declarations and effective settings are two different facts. Satyrn already
knows this failure family: an arm record must match the live configuration.
`AGENTS.md` states the live form as "freeze execution conditions before a
budgeted run"; the older four-condition publishability check that named this
as 0c is archived, at
`archive/2026-09-07-pre-reset/CLAUDE.md` (search it with `rg --no-ignore`).

## The one path being evaluated

Everything outside this line is out of scope for the phase:

**inspected packet → bounded implementer → isolated candidate → explicit
integration → cumulative validation.**

Only the gaps on that path get closed. No pool, no UI, no historical
machinery is carried over.

> **Amended 2026-09-09.** The first word of that line read
> *orchestrator-authored*. It overstated the phase. `satyrn-engine`'s
> deferred `facts` field carries the measurement: machine-made **bounds** do
> confine an implementer and packet **content** does move outcomes floor to
> ceiling, but a system **authoring and gating that content autonomously**
> scored **3/8 against 8/8 by hand**, and a remediated authoring prompt
> **collapsed to 0/8, all no-op** (`local-ai-pi/ROADMAP.md:386-402`, verified
> at source; the deferral is `satyrn-engine` commit `7b847eb`, still
> unmerged). local-ai-pi re-scoped its own phase around a main agent
> authoring the contract for exactly this reason.
>
> So Phase HP runs an **inspected** packet: built deterministically from the
> task and reviewed before dispatch. That isolates execution defects from
> packet-authoring defects, which is what makes an HP2 failure readable.
> **Autonomous packet authoring is out of scope for the phase.**
>
> **Corrected 2026-09-09.** This first said that decision reopens "on an
> experiment that isolates contract content from contract delivery". That is
> the reopen condition of the **`facts` field**, not of autonomous authoring.
> The authoring entry reopens "on a deterministic authoring path, or on
> evidence that a newer model closes the 3/8-versus-8/8 gap" (`7b847eb`,
> added lines 49-51). HP1's builder **is** a deterministic authoring path, so
> that condition is arguably already met. Keeping autonomous authoring out of
> Phase HP is a **scope judgment for this phase**, not a claim the condition
> is unmet, and it is the maintainer's to revisit.

## Workload: the one that already exists

`src/satyrn_evals/tasks/agentclinic-session-phased/` supplies the roadmap —
three ordered development requests over one growing checkout, graded
cumulatively against 13 hidden checks split 4/6/3, with the acceptance
assertions in three independently collectable modules. Its phase boundaries
are the decomposition. **No agent invents a decomposition, and no second
workload is authored.**

## The incident every packet field answers to

SwiftStar's `runDirectiveOnce` built the **orchestrator's own prompt** from
the task alone, while its non-directive loop always included the shared
project context in its packets.
On a business-outcome phrasing of the same target application, the
orchestrator built **the entire application in Flask instead of FastAPI**,
passed its own phase validation, and failed the acceptance suite at import
(`swiftstar/ROADMAP.md:410-425`) — recorded there as the fourth instance of
one defect family.

**Corrected 2026-09-09.** This section first said the context was dropped
from the *packets*, which framed it as an argument about the implementer's
packet alone. The role starved of context was the **orchestrator**. The
constraint therefore lands in two places, and D6 carries the second.

Three consequences bind the deliverables:

1. **A packet omitting project constraints is a defect, not a shorter
   packet.**
2. **Phase-local validation passing is not acceptance.** The orchestrator's
   accept decision and the hidden per-phase grading stay separate, as
   `BRIEF.md` invariant 1 already requires of capture and grading. **The
   packet therefore carries no parent validation command at all** — see the
   HP1 spec, where sourcing one from the task's `oracle` was refused because
   it would put the hidden oracle hook in a document the implementer reads.
3. **The orchestrator's own instructions carry the project constraints too.**
   Not only the packet. D6 retains those instructions so a Flask-shaped
   failure is attributable to the role that lost the context.

## Deliverables

Each names its acceptance evidence. Per `BRIEF.md` invariant 5, every refusal
check ships with the sibling success that proves it can pass, and every check
is shown to work in both directions.

**D1 — The packet, mapped rather than invented.** Take SwiftStar's field set
as the starting point and map it onto Satyrn's existing contract rendering
(`src/satyrn_evals/engine_contract.py`). Carry each field with the record
that justifies it; drop what this path does not need.
*Acceptance:* a versioned schema; one golden packet built from the phased
task's phase 2, asserted byte-for-byte; a packet with the project-constraint
fields removed is **refused** and the complete packet **accepted**; and a
contamination check proves no hidden grader selector reaches a packet
(`src/satyrn_evals/contamination.py` already owns that job).

**D2 — One inspected packet executed offline, with no model.** A fake
implementer on the same seam, per `BRIEF.md`'s rule that a fake command must
satisfy the engine seam so eval development never waits on the real engine.
*Acceptance:* three phases end to end against scripted implementer results;
the task's `known-good` witness **accepted** and `known-broken`
**rejected**, each cited by fixture name; the application state carries
forward from the accepted predecessor; no model, no network.

**D3 — Chained isolation, borrowed from `WorktreeTransaction`.** Phase N
starts from phase N-1's accepted commit. A refused phase stops the chain
rather than leaving a partial one.
*Acceptance:* phase 3's checkout contains phases 1 and 2's committed code,
shown by fixture; and a rejected phase 2 leaves **no** candidate ref and no
partial chain. This is the behaviour to re-earn in `satyrn-engine`, which
owns candidate production.

**D4 — Legitimate file creation, and a writable scope that can say so.**
`writable_paths` infers directory-ness by probing `base/` with `is_dir`
(`src/satyrn_evals/engine_contract.py:43-46`), which cannot distinguish an
empty-skeleton directory from a creation target. The deferred entry is
**"Declared directory source paths"**
(`docs/superpowers/plans/2026-09-09-agentclinic-phased-session.md:750-754`),
whose reopen condition is "when an Engine session arm exists"; a bounded
implementer running against a rendered contract is that condition in a
different shape. A trailing slash is one candidate spelling, **not** what the
plan says.
*Acceptance:* phase 1 creates `app.py`, `templates/base.html` and
`tests/test_app.py` with **zero** scope violations, and a write outside the
declared scope is still refused, from the same fixture.

**D5 — Role attribution, which is what limit 2 makes non-negotiable.** Every
mutation in the retained chain is attributable to the role that made it,
orchestrator or implementer, from retained events rather than from prose.
*Acceptance:* a fixture chain in which the orchestrator makes every mutation
is reported as **zero implementer mutations** — the seed-221 shape, detected
rather than passed — while a chain where the implementer delivers reports its
mutations to the implementer. A detector that cannot show both directions on
the current batch does not ship (`BRIEF.md` invariant 5).

**D6 — The whole chain retained and re-scorable.** Orchestrator instructions,
every packet, the implementer's own tool events, the candidate change, the
validation output, and the accept-or-reject decision **with its reason** —
plus cost recorded separately per role, and any orchestrator fallback work
labelled as such.
*Acceptance:* every acceptance decision recomputes from retained artifacts
with no further inference (`BRIEF.md` invariant 1); a chain with an implementer
step carrying no retained events **fails** the chain check, which is the
2026-09-08 detached-worker gap written as a test; and every packet
declaration that the runtime does not actually apply is recorded as declared
**and** not applied, never as applied.

> **Corrected 2026-09-10, by the Astra-style acceptance review of the HP6
> implementation.** "Recomputes from retained artifacts" is met only in a
> narrower sense than the sentence claims. What HP6 retains is mutation
> **paths and kinds**, never patch content, so there is nothing to re-grade a
> decision's correctness against; `decisions_from_record` reads each phase's
> stored fields back losslessly rather than independently re-deriving them,
> and by construction cannot disagree with what was stored. What the
> acceptance line actually proves — the document alone, with no task
> directory, no manifest and no grader, carries every field the accept/reject
> sequence needs, across all three exit paths `run_phases` can take — still
> holds and is BRIEF.md invariant 1's real content. Re-scoring the retained
> **candidate** from its own bytes is not attempted by HP6 and stays out of
> scope; the HP6 plan's own correction block (`2026-09-09-hp6-chain-retention.md`,
> HP6.7) carries the full accounting.
>
> **Corrected again 2026-09-10, same review pass.** The line above is no
> longer accurate as written: `run_and_record_chain` now captures each
> phase's actual candidate file content before grading, durably, and a
> default-tier test reconstructs a phase's workspace from nothing but that
> retained content and re-grades it, matching the original decision. The
> lower-level `build_chain_record` still does not — it has no workspace to
> read from, and a record built only through it is not held to that
> standard. Worker tool events remain retained only as the implementer
> adapter's own transcript file, not referenced per-phase from the chain
> record; and this still runs in one plain workspace across the whole chain,
> not HP3's chained, isolated checkouts, which is a separate, still-open
> composition gap the HP7 pre-run record names.

**D7 — One bounded live route proof.** One orchestrated delivery of the three
phases, `n` frozen at 1, the Baseline model, the adopted verification
instruction on the implementer.
*Acceptance:* a pre-run record written first, stating that the run
establishes **operability and not superiority**, reporting orchestrator and
implementer cost separately, and reporting implementer mutation counts even
when the workflow passes. Needs its own budget authorization.

**D8 — Then, separately authorized, the workflow comparison.** The
orchestrated route against the existing continuous-session route, same
roadmap, same requirements, same verification sentence. Triage first at **two
attempts per configuration**, per `BRIEF.md`'s development feedback policy
(`BRIEF.md:44`). Costs declared separately, and **never** a wall-clock
comparison between contiguous arms — a standing rule that survived the
2026-09-07 reset only in the archive, at
`archive/2026-09-07-pre-reset/BRIEF.md:44`, where two retracted figures are
the reason.

## The confound to state before D8 runs

The two routes must not differ in tool surface while claiming to differ in
workflow. V13d found that removing `bash` and `write` cost 8 of 12 successes
on one task. The primary record adds two things the engine's own comment
omits: Engine recovered 2 of those 8, indistinguishable from chance, and **on
`misleading-locus` the sign was opposite**
(`archive/2026-09-07-pre-reset/ROADMAP.md:154`, the primary;
`satyrn-engine/packages/engine/runner.ts:22-30` restates only the first
half). A separate self-test command is therefore **necessary to avoid the
confound, not shown sufficient to remove it.** SwiftStar's shape is the one
to adopt: a worker self-test command, distinct from whatever decides
acceptance (`HandoffPacket.swift:62-68`).

**A second confound, and it is not tool surface.** The packet's declared
scope and the session route's enforced scope match differently.
`engine_contract.writable_paths` renders fnmatch patterns and leaves a path
absent from `base/` as an exact filename
(`src/satyrn_evals/engine_contract.py:32-46`), while the session route
enforces prefix matching through `patch.within_source`
(`src/satyrn_evals/patch.py:166-178`). On this task's empty skeleton the two
disagree about whether `templates/base.html` is in scope. **Until HP4 the
packet's declared scope is not the enforced scope**, and any comparison says
so.

## Deliberately out of scope

- A worker pool, parallel dispatch, generalized routing, or any UI.
- Any automatic retry or repair campaign. SwiftStar shipped one-shot-first
  for a measured reason.
- **An orchestrator that silently repairs what an implementer failed to
  deliver.** A failed handoff is an outcome to retain, and D5 exists so it
  cannot be absorbed silently. If orchestrator repair is studied, it is an
  explicitly separate, labelled condition.
- A second workload or task directory.
- Any new pathology detector beyond D5's attribution, which limit 2 names.
- Auditing SwiftStar's `harness-void` classification. Cite it with its
  caveat; do not re-adjudicate it here.

## Settled by the maintainer, 2026-09-09

**Ownership.** `satyrn-engine` owns packet execution, chained isolation and
candidate production — it already owns the contract seam, and `BRIEF.md:29`
puts contract authoring outside it. `satyrn-evals` owns the packet schema,
the arm, capture, grading, attribution and comparison, and still must not
import engine internals.

**The phase is `HP`**, the handoff packet, and it runs as a sequence of
feature cycles under Superpowers spec-driven development rather than as one
change. The cycle table, its ordering, and which cycles earn a spec against
which are plan-only are in `ROADMAP.md`'s Phase HP section. The deliverables
above map one-to-one: D1→HP1, D2→HP2, D3→HP3, D4→HP4, D5→HP5, D6→HP6,
D7→HP7, D8→HP8.

**Engine-side cycles need their own roadmap entry** in `satyrn-engine`. This
document does not govern that repository, and HP3's acceptance has to be
re-earned there rather than asserted from here.
