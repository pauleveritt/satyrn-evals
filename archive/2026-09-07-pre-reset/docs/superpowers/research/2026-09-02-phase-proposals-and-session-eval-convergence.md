> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Phase proposals, and where the spike converges with the session-eval draft

**Date:** 2026-09-02
**Status:** **superseded in part by maintainer review, 2026-09-02 — see §5.**
The four-phase shape below is **not** the agreed direction; it is kept because
the review is easier to follow against what it corrected. Input to
brainstorming, not an approved plan.
No code follows from this document until a phase design is proposed and
confirmed separately, per `CLAUDE.md`.

Sources: the overnight run
([record](2026-09-02-overnight-packet-and-isolation-run.md)), the two harvest
documents, the [gap analysis](2026-09-02-not-captured-in-agentclinic-harvest.md),
and a read of the unmerged session-eval work on PR #17
(`docs/superpowers/specs/2026-09-01-svcs-session-eval-design.md` and
`docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md`, both
currently only on that branch and in a local worktree).

## 1. The session-eval draft already specifies what the spike measured

This is the most useful thing found while preparing to plan, and it changes the
status of two proposals from "my idea" to "confirm what is already drafted".

**Convergence.** PR #17's done-when list already requires that grader-only
files be

> stored outside `base/`, overlaid only in a fresh grader workspace, and
> **never named in adapter argv, environment, or prompts**.

The overnight run measured, independently, what happens when each half of that
clause is violated:

- *Stored where the attempt can reach them.* Models located the acceptance
  suite on disk and optimised against it. Two cells did so definitively; more
  read it without copying; one run read up to 49 other cells' directories.
- *Named in the prompt.* The failure evidence supplied to the model named the
  grader file. Unguarded arms then spent their budget hunting for it — and on
  one fixture, simply **not naming it** recovered most of the lost throughput
  (median 219 → 19 turns) with no other change.

So that clause is not housekeeping. Each half of it has an independent measured
consequence, and the second half — *never named in prompts* — is the one a
reasonable implementer would be most tempted to treat as pedantry.

**Divergence, and it matters.** The same document defers a "hostile-command
sandbox". Storing graders outside `base/` defeats a grader reaching the
*patch*; it does not defeat a model **reading the grader off disk**, which is
what actually happened. The deferral was reasonable without evidence; there is
now evidence, and it should be re-decided rather than inherited.

**A third observation, about workload selection.** The session probe records
its own suite as a capability wall (deepest milestone `1,0,0,0` of five), and
this repository's two other probed tasks both floor at 0/4 for bare Pi. Of
everything measured across all of this work, only the AgentClinic repair
fixtures produced a distribution that moves. That is worth stating plainly
because three separate efforts have now each arrived at a wall.

## 2. Proposed phases

Four, in two repositories. Sequencing matters more than the contents.

### E1 (`satyrn-evals`) — instrument integrity. No model required.

Every defect the overnight run produced was in classification or accounting,
and every one is testable with no model, no network, and no subprocess — so
this belongs in the existing fast tier.

- **Two standing tests as the spine.** (a) Every detector must fire on a
  known-bad drawn from the *current* batch and stay silent on a known-good
  from the same batch, both directions, every time. (b) Every reported
  statistic must name the cell set it was computed over, and that set must be
  recomputable by a filter rather than by hand.
- **Two classification fixes, each with a sibling success test.** A collection
  error caused by the model's own broken code is a `fail`, not an instrument
  void. A patch snapshot diffs against the recorded base SHA, never `HEAD`.
- **A content-based grader tripwire** in the default tier: byte identity plus a
  count of real test names. Explicitly *not* filename matching, which produces
  false positives on models writing their own tests.
- **Conditions in the record.** Resolved dependency versions for both the
  attempt environment and the oracle environment. Their divergence silently
  produced six false passes.

Out of scope: sandboxing, and any new workload.

### E2 (`satyrn-engine`) — render one field, after a free measurement first

`Contract` today is `id`, `task`, `writable_paths`, and `build_prompt` renders
no facts. The overnight result says a single host-computed fact outperformed
every other intervention measured. That is a one-field change to a named
dataclass.

**Its first question needs no change at all.** Run the *existing* three-field
contract against the already-qualified, already-floored `magicmock-factory`
task on its unmerged branch. The Engine arm has never been run against either
floored task. If the current product path moves that floor, the field change
gets a real baseline; if it does not, that is the more interesting result and
it reshapes everything after it.

Note `satyrn-engine`'s own brief already excludes contract *authoring* from
scope. This proposal is about **rendering**, not about an authoring agent.

### E3 (`satyrn-evals`) — isolation, as a decision rather than a default

Confirm the session-eval grader-overlay design, then take its deferral head-on:

- A manifest field declaring each task **visible-oracle** or **hidden-oracle**,
  so the two cannot be mixed silently. Every fixture used in the spike assumed
  hidden; the harness is built for visible.
- Hidden tasks refuse to run without containment.
- Containment itself: a whole-process profile is verified to work on macOS with
  no VM and no install, and to leave a local model server reachable.

Two known holes belong in the spec, not the footnotes: a **hard link created
inside the run root still reads the grader** (path-based enforcement), and the
profile as tested **removed the model's own test runner**, so a corrected
profile must grant the run root a working interpreter. **Windows has no
verified no-VM answer** and should be stated as unsolved.

### E4 (`satyrn-evals`) — AgentClinic variations. Last.

Repair fixtures rather than build-from-scratch; **`tests fixed`** rather than
`deepest_pass`, which saturated at both ends while the delta discriminated in
every cell; and a clean lure arm that redacts only the grader's filename,
keeping source paths — the spike's redaction arm removed both and was
confounded as a result.

Last, because it is the only phase whose value depends on the other three.

## 3. Sequencing, and the risk that is not technical

**E1 → E2's Stage 0 → E2 → E3 → E4.**

E1 first because every number the spike produced needs re-deriving through an
instrument that can be trusted, and the spike's own history is the argument:
three review passes each found defects the previous pass missed. Stage 0 next
because it is nearly free and could invalidate the ordering of everything after
it.

**The coordination risk is larger than any technical item here.** There are now
four research efforts in this repository — two floored-task baseline branches,
the session-eval branch, and this spike branch — and the gap analysis found
that none of them referenced the others. E1 and E3 overlap PR #17's design
directly.

So the first question for the brainstorm is not "which phase first" but
**"does PR #17 land first?"** If it does, E1 and E3 are amendments to it rather
than new phases, and proposing them separately would make this spike the fourth
uncoordinated effort rather than the thing that consolidated the other three.

## 4. Open questions for the brainstorm

1. Does PR #17 land before E1/E3, and if so are they amendments?
2. Visible-oracle or hidden-oracle — or declared per task? The answer decides
   whether containment is required or optional.
3. Is the `factonly` result strong enough to justify E2, given the sandbox
   confound (the model could not run tests) was found late and is not fully
   worked through?
4. Is `tests fixed` the right primary measure, or a symptom of fixtures whose
   difficulty is set by how much of the failure the evidence block reveals?
5. What is the durability plan for spike evidence? The 166 capture cells and
   the probe harness exist only in a session-scoped temporary directory.


## 5. Maintainer review, and what it corrected

Recorded beneath the proposal rather than replacing it.

### The verdict: do not make these four phases. Consolidate around PR #17.

Accepted. The sequence the review proposes:

> reconcile/land PR #17's overlay and session foundations → repair instrument
> semantics → make containment genuinely usable, including a test runner →
> reproduce AgentClinic through Evals → then test Engine facts.

Engine facts move to **last**, not second. Every step before it either repairs
an instrument or removes a confound that would otherwise contaminate it.

### Corrections to specific proposals

**E1 was partly aimed at machinery that does not exist.** Its principles hold,
but much of it targets batch and reporting machinery Evals has not got. Two
pieces relocate: the grader tripwire belongs with hidden-oracle support, not as
free-standing instrument work; and collection-error attribution **conflicts with
today's "collection error = unavailable" rule** and needs a design decision
before any fix.

**"Stage 0" rested on a claim that is false, and I propagated it.** The
assertion that the Engine arm has never been run against a floored task is
wrong: the earlier three-arm pilot recorded **Baseline 0/6, Envelope 0/6,
Engine 6/6** on `stringified-annotations`, and that pilot's single
byte-identical patch was later regraded at **125/125** under the strengthened
oracle. Engine moving a floor is therefore **already evidenced**, and better
than the proposed experiment would have shown. What is missing is a
*generalization* test — a weaker claim than the one this document made.

It is also **not nearly free**. `~/.satyrn-authoring/magicmock-factory/` holds
a brief and an upstream checkout but **no `manifest.json`, no `base/`, no
`fixtures/`** — there is no captured task, so the work includes redoing the
two-stage oracle reconstruction and its curator corrections before a cell runs.

This error has the same shape as the re-derivations catalogued in the harvest:
a claim inherited from another document and repeated without checking, while
writing a plan that cites that very lesson.

**Adding `facts` to the Engine contract needs its own specification.** Plausibly
small, but the exact fact and the exact experiment must be stated, and **block 7
cannot be its decisive justification** — see the exposure confound recorded in
the [overnight record](2026-09-02-overnight-packet-and-isolation-run.md).

**E3's declaration and fail-closed behaviour are the strong part; Seatbelt is
not production-ready.** Four blockers: hard-link uncertainty, the missing test
runner, macOS-only support, and — the one that is a design conflict rather than
a gap — **incompatibility with V4's absolute external Engine-contract path**.

**AgentClinic repair is promising, not admitted.** The corrected figure is
**7/12** for `dumb`, not 8/12; `factonly` sits near ceiling; and "pass" still
counts retained patches from timed-out attempts, which conflates completion
with conditional patch quality — the same distinction the `local-pings`
admission work insisted on keeping separate.

**`tests fixed` does not replace `deepest_pass`.** It suits single-shot repair.
For genuine cumulative sessions the deepest-milestone measure stays. This
document over-generalized from a workload where cumulative structure was not
under test.

**Text-contract support and writable-scope experiments are follow-ups, not
prerequisites. An orchestrator remains unjustified.**

### The open questions, updated

1. Does PR #17 land as drafted, or does the isolation evidence amend it first?
   Its overlay clause is confirmed by measurement; its sandbox deferral is
   contradicted by it. Landing unchanged ships hidden-oracle tasks without
   containment.
2. Is collection-error attribution a question of *whose* error it is, or of
   whether a task whose base cannot import should be capturable at all?
3. What is the containment bar — does it become a V4 seam change, or does
   hidden-oracle support wait for a boundary that survives Windows?
4. What preserves the spike evidence, given it lives in a session-scoped
   temporary directory and the two probe bundles live on another machine?
