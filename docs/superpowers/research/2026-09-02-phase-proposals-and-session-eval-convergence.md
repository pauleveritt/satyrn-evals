# Phase proposals, and where the spike converges with the session-eval draft

**Date:** 2026-09-02
**Status:** **input to brainstorming. Not an approved plan, not a phase.**
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
