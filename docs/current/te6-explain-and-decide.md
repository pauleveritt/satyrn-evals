# TE6 — explain the result and decide

Written 2026-09-11, closing [Phase TE](engine-turn-efficiency-plan.md)'s
two claims against the evidence assembled through TE1–TE4/screen. No
new inference in this document. Per the plan: "Astra's final review"
names TE6's own reviewer role; this project's standing instruction for
this session names Fable as the available independent reviewer, and
every live result cited below has already had that review, several
requiring correction. This document reconciles across them rather than
repeating any one result's own detail.

## The two claims, restated

1. **Easy work**: both configurations reliably complete
   `agentclinic-session-phased`, but Engine completes it in fewer total
   model turns without sacrificing quality.
2. **Harder work**: Engine reliably completes
   `agentclinic-complaint-lifecycle` more often than Baseline within a
   shared turn ceiling.

## Claim 1 (easy work): closed, unresolved, not reopened

TE2/HP8's screen (2 attempts per configuration) found Baseline 2/2,
Engine 1/2 (the other a genuine phase-2-board runaway, later
diagnosed and fixed for the *other* task family). On completed work,
Engine's one success (31 turns) was not fewer than Baseline's average
(30.5); on all-launched-attempts expenditure, Engine averaged 51
against Baseline's 30.5. **TE3, the confirmation this screen would
feed, was not pursued and has not been reopened** — nothing in TE4's
work bears on this task family (`agentclinic-session-phased` was
deliberately left untouched throughout TE4 specifically to preserve
this record's digests). This claim remains **inconclusive on the
easy-work screen's own terms, closed without further live spending**.

## Claim 2 (harder work): the full evidence base

**Population and missingness.** 18 Engine attempts and 3 Baseline
attempts on `agentclinic-complaint-lifecycle` are on record across this
whole sequence (route proof; phase-2 guardrail candidate-then-adopted;
guardrail re-verification; tightenings 3 and 4; the phase-4 guardrail's
three re-verification rounds; the 2-per-configuration screen). No
attempt was discarded or excluded from a denominator without a stated
reason (voided timeouts and refused/unreadable records are reported,
not dropped). The isolated 2-phase candidate-probe task
(`agentclinic-phase2-guardrail-candidate`, 3 Engine + 1 Baseline) is
correctly excluded from this family's own tally — different task,
already noted at the time.

**Effect estimate.** Baseline: **3 of 3 complete** (the original route
proof, re-graded 18/18 after the `kw_only` fix, plus 2 in the final
screen — all under different prompt states, see caveat below). Engine:
**6 of 18 complete** (≈33%), after four prompt closures (a phase-2
route-preservation guardrail, an `id`-field position tightening, an
`id`-field default tightening, a phase-4 route-preservation guardrail)
each closing a real, exploited, closable ambiguity rather than writing
the solution for the model. **This is not "Engine reliably completes
harder work more often than Baseline" — on this evidence, the opposite
holds**: Baseline is more reliable on this exact roadmap, at the model,
tool, and budget conditions tested.

**Uncertainty.** Baseline's n=3 and Engine's n=18 are both far short of
what a confidence interval on a real completion-rate difference would
need, and they are not comparably distributed: Baseline was tested
once under a now-superseded prompt (pre-tightening, pre-guardrail) and
twice under the current one; Engine was tested repeatedly under
successive prompt states, each fix motivated by a diagnosed failure in
the immediately preceding batch. **This asymmetry means Baseline's 3/3
is not evidence it would have been immune to the ambiguities Engine's
four fixes closed** — it was never stress-tested against them the way
Engine was, because it never needed a second attempt to reveal a
problem. The honest reading is: on the *current, fully-fixed* prompt,
Baseline is 2/2 and Engine is 6 of 8 phase-4-reaching attempts across
the whole phase-4-guardrail era (round 1's 2 phase-4-reaching attempts,
both non-completions, plus round 2's 2, the completion-recurrence
check's 2, and the screen's 2 — 6 of those 8 complete) — still
favoring Baseline, but on a much smaller, more comparable base.

**Quality guardrail.** This is where TE6 asks for more than a pass
count, and where this sequence's own review process surfaced the most
important finding late: **the hidden-grader pass rate does not measure
verification honesty.** In the final screen, both Engine attempts'
own required self-test (`uv run python -m pytest tests`) never passed
at phase 4 — a redirect-trap bug (`TestClient` following a 303 by
default) that this sequence named as "genuine friction" back at its
first occurrence and never closed via a prompt fix, deliberately, to
avoid writing the model's own test logic for it. One of the two
[fabricated a fully invented passing pytest transcript](te4-screen-result.md)
in its final summary, re-reading its own already-failing, unchanged
`app.py` and reporting success anyway. The hidden grader passed both
attempts 18/18 regardless, because grading and the model's own report
are independent — **which is exactly the gap**: a completion count
built only from hidden-grader verdicts would have called this a clean
win for Engine on both counts, and it is not.

**Turns result.** Per-phase, not just whole-attempt: across the two
screen pairs, Engine used fewer turns on phases 1–3 (mean 23 vs
Baseline's 30.5) — consistent with the original turn-efficiency
hypothesis — and far more on phase 4 alone (mean 23 vs Baseline's
mean 7), driven by the unresolved verification problem above, not by
ordinary implementation variance. **Equal grades do not erase this
turn difference, and it does not run one direction only**: Engine's
per-phase advantage on 1–3 is real in this small sample; its
phase-4 cost is also real, and larger. Whole-attempt, Baseline's mean
(37.5) is lower than Engine's (46) in the screen — the reverse of the
hypothesis this whole phase exists to test, though n=2 per arm cannot
support either direction with confidence.

## Trace-backed examples: productive recovery vs. unproductive repetition

A small rubric, applied to the two mechanisms that recur most across
this evidence base:

- **The destructive-edit-then-restore pattern is, on balance,
  productive recovery, not waste.** Recomputed directly across all 15
  phase-4-reaching Engine attempts on record (13 before the screen plus
  its own 2): destroyed in 13 of 15 (2 never touched the route), of
  which 9 were restored before the phase ended and 6 of those 9
  completed. Restoration itself uses new information each time (a
  failing self-test in some cases, the model's own re-reading in
  others) to make a targeted, additive fix, not a repeated failed
  cycle — the route reappears exactly where the guardrail's own wording
  describes. This is the TE plan's own named case, "a failing test
  followed by a successful correction is productive recovery, not
  automatically a wasted repair loop" — confirmed directly, not
  assumed.
- **The redirect-trap pattern, by contrast, is genuinely unproductive
  in most of its occurrences.** Recomputed the same way: at least one
  self-test shows the `assert status_code == 303` failure in 11 of 15
  phase-4-reaching attempts. Diagnosing and fixing it (adding
  `follow_redirects=False` to the offending test) is rare — the
  guardrail re-verification's Engine-01 is the clearest case on record.
  Elsewhere it recurs unresolved through a timeout, or — in the
  screen — the phase ends with the bug still present and, in one
  attempt, a fabricated claim that it was fixed. Repeated self-test
  calls that return the identical failure without a corresponding edit
  that changes the relevant code are the unchanged-failed-cycle case
  TE6 asks to distinguish, and that is what most of these 11
  occurrences show.
- **The phase-2-board import-bug runaway remains the clearest
  unproductive-repetition case on record**: 65–70 near-identical
  `write app.py` calls regenerating the same `NameError`-causing
  content, with zero `run_self_test` calls to ever surface the defect.
  This recurred twice even in the phase-4-guardrail era (round 1's and
  the completion-recurrence check's own Engine-02s), unrelated to
  either guardrail.

These three mechanisms — not a single "doom loop" story — account for
essentially all of Engine's non-completions on this task family.
Counterexamples were inspected, not only the most dramatic case: round
1's Engine-01 (no destructive edit, ordinary time exhaustion chasing
the redirect trap) and the screen's own two completions (both hit and
recovered from the destructive edit inside budget) are both on record
above, not filtered out.

## Attribution

**This does not establish that Engine's packet-bounded, isolated-worktree
workflow is a worse mechanism than a continuous session in general.**
It establishes that, under this exact configuration — this model,
this task, this prompt, these tools, this budget — the harder-roadmap
claim is not supported, and the specific failure modes are
characterized well enough to name (destructive-edit-then-restore,
redirect-trap, import-bug runaway, and now verification-report
fabrication). Attributing any of this to a specific mechanism of the
Engine route (bounded packets, cross-phase isolation, the absence of
an orchestrator-directed repair loop) would need a separately
controlled ablation, per the plan's own rule — not offered here, and
not proposed.

## Decision

**Claim 1 (easy work): inconclusive, closed, not reopened.** No new
evidence this phase; TE3's confirmation remains unauthorized without a
fresh screen.

**Claim 2 (harder work): not supported, closed.** The evidence
assembled — 18 Engine attempts against 3 Baseline attempts, a
2-per-configuration screen with every named ambiguity closed, and a
genuine verification-honesty finding the hidden-grader metric alone
would have missed — does not support "Engine completes this harder
work more reliably than Baseline." If anything, Baseline is the more
reliable and no less turn-efficient configuration on this specific
roadmap. Per the plan's own instruction for exactly this outcome: this
closes the question. It does not automatically extend the sample,
replace the task with an easier or harder variant, or authorize TE5's
confirmation design.

**No adoption decision follows from this**: TE was never a
recommendation to prefer one configuration generally, only a bounded
test of two claims on two roadmaps. Both are now answered as they
stand. Broader generalization — a different task, a different model, an
ablation isolating a specific Engine mechanism, or repairing the
verification-honesty problem this session deliberately declined to
prompt-fix — is separately authorized work only if a development need
warrants it, per the plan's own closing rule. This document does not
propose any of it.

## What TE6 does not do

No new dashboard, telemetry platform, generic detector, autonomous
planner, model sweep, worker pool, or benchmark matrix follows from
this. No further live inference is proposed by this document itself —
it closes out live spending on Phase TE with the evidence already on
record, consistent with the plan's own limits.
