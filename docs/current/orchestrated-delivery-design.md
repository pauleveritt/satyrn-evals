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
Eleven of the 54 rows carry it. Whether each void deserves exclusion is
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
The orchestrator issued the writes and edits. An orchestrator that delivers
the application is a useful product; it is not evidence that delegation
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

**orchestrator-authored packet → bounded implementer → isolated candidate →
explicit integration → cumulative validation.**

Only the gaps on that path get closed. No pool, no UI, no historical
machinery is carried over.

## Workload: the one that already exists

`src/satyrn_evals/tasks/agentclinic-session-phased/` supplies the roadmap —
three ordered development requests over one growing checkout, graded
cumulatively against 13 hidden checks split 4/6/3, with the acceptance
assertions in three independently collectable modules. Its phase boundaries
are the decomposition. **No agent invents a decomposition, and no second
workload is authored.**

## The incident every packet field answers to

SwiftStar's orchestrate path dropped shared project context from its packets.
On a business-outcome phrasing of the same target application, the
orchestrator built **the entire application in Flask instead of FastAPI**,
passed its own phase validation, and failed the acceptance suite at import
(`swiftstar/ROADMAP.md:410-425`) — recorded there as the fourth instance of
one defect family. Two consequences bind the deliverables:

1. **A packet omitting project constraints is a defect, not a shorter
   packet.**
2. **Phase-local validation passing is not acceptance.** The orchestrator's
   accept decision and the hidden per-phase grading stay separate, as
   `BRIEF.md` rule 3 already requires of capture and grading.

## Deliverables

Each names its acceptance evidence. Per `BRIEF.md` rule 6, every refusal
check ships with the sibling success check that proves it can pass.

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
the current batch does not ship (`BRIEF.md` rule 8).

**D6 — The whole chain retained and re-scorable.** Orchestrator instructions,
every packet, the implementer's own tool events, the candidate change, the
validation output, and the accept-or-reject decision **with its reason** —
plus cost recorded separately per role, and any orchestrator fallback work
labelled as such.
*Acceptance:* every acceptance decision recomputes from retained artifacts
with no further inference (`BRIEF.md` rule 3); a chain with an implementer
step carrying no retained events **fails** the chain check, which is the
2026-09-08 detached-worker gap written as a test; and every packet
declaration that the runtime does not actually apply is recorded as declared
**and** not applied, never as applied.

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
workflow. V13d found an implementer restricted to `read,edit` lost 8 of 12
successes against a `bash`-carrying baseline
(`satyrn-engine/packages/engine/runner.ts:22-30`). SwiftStar's answer is
already in the packet: a worker **self-test command**, distinct from the
parent's validation command (`HandoffPacket.swift:62-68`). Adopt that shape.
The implementer's validation capability is required, not optional.

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
