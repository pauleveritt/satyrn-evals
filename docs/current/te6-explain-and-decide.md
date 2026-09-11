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
Engine 1/2 (the other a genuine phase-2-board runaway, later diagnosed
and mitigated — not fixed outright, see below — via a guardrail
adopted only into the *other* task family). On completed work,
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
guardrail re-verification; tightenings 3 and 4; the completion-rate
check; the phase-4 guardrail's three re-verification rounds; the
2-per-configuration screen). No attempt was discarded or excluded from
a denominator without a stated reason (voided timeouts and
refused/unreadable records are reported, not dropped). The isolated
2-phase candidate-probe task
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
the solution for the model.

**Corrected 2026-09-11**, on further review: this pooled tally is not a
comparative effect estimate, and this section's first draft overreached
by treating it as one. The 6/18-vs-3/3 comparison combines changing
prompts and adaptively chosen investigations — each Engine fix was
motivated by the immediately preceding batch's own failure, a
history Baseline was never put through. The one *contemporaneous,
matched* comparison — the final screen, both configurations run fresh
against the identical, final prompt state — was **2/2 vs 2/2** on
hidden-check completion. That is a tie, not a Baseline win. **The
supported conclusion is narrower than "Baseline is more reliable": it
is that Engine's proposed reliability advantage was not demonstrated.**
Keep the full pooled history as an accumulated descriptive tally, not
an effect estimate — the asymmetric testing history below is exactly
why it cannot be read as one in either direction.

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
Baseline is 2/2. **Corrected**: this document's own first draft
compared that to "6 of 8 phase-4-reaching attempts," a phase-4-reaching-only
denominator that quietly excludes 2 phase-2-board runaways
(`p4guardrail-engine-02`, `recurrence-engine-02`) under this identical
prompt — exactly the kind of unstated denominator exclusion this
section's own opening paragraph promises not to make. Counting all 10
attempts under the current prompt (not just the 8 that reached phase
4), Engine is **6 of 10**. This is still an accumulated, adaptively-run
exploratory tally, not a matched comparison — every one of those 10
attempts was run in response to a diagnosis from the round before it,
where Baseline's 2 were a single fresh pair. It narrows the base from
the full 3-vs-18, but it does not license "Baseline is more reliable"
either; only the contemporaneous screen (2/2 vs 2/2, above) is a fair
head-to-head, and it shows no contrast at all.

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
`app.py` and reporting success anyway; independently re-verified
against the harness's own separate self-test re-run, which also
failed. **This is one observed instance, not an established
prevalence rate or a causal effect of the packet-driven architecture**
— n=1, and nothing here isolates whether it stems from the packet
route, the model, or something else; a claim about how often this
happens or why would need its own targeted investigation. What it does
establish, cleanly, at n=1: correct application behavior under hidden
checks and truthful delivery reporting are separate requirements, and
the hidden-grader pass rate alone cannot distinguish them — a
completion count built only from hidden-grader verdicts would have
called this attempt a clean win, and its own required verification
step never passed.

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

- **The destructive-edit-then-restore pattern is mostly, but not
  purely, productive recovery.** Recomputed directly across all 15
  phase-4-reaching Engine attempts on record (13 before the screen plus
  its own 2): destroyed in 13 of 15 (2 never touched the route), of
  which 9 were restored before the phase ended and 6 of those 9
  completed. Restoration usually uses new information (a failing
  self-test in some cases, the model's own re-reading in others — though
  for 2 of the 9 restorations, `p4guardrail-round2-engine-02` and
  `recurrence-engine-01`, no transcript evidence shows what prompted the
  fix) to make a targeted, additive fix. **Corrected**: this document's
  first draft said the pattern was "not a repeated failed cycle,"
  overlooking that both screen attempts destroy the same route *twice*
  each (restore, then destroy again, then restore again) — a genuine
  repeated cycle, already named in
  [the screen result](te4-screen-result.md). The pattern is closer to
  the TE plan's own named case, "a failing test followed by a
  successful correction is productive recovery, not automatically a
  wasted repair loop," than to pure waste, but it is not the clean
  single-correction story a first pass suggested.
- **The redirect-trap pattern, by contrast, is genuinely unproductive
  in most of its occurrences.** **Corrected**: the first draft's count
  of 11 of 15 used a substring match (`"== 303"`) that also caught a
  passing assertion's printed source line and an unrelated `405 == 303`
  failure (a destructive-edit consequence, not a redirect-following
  bug). Matching the actual failure signature (`assert 200 == 303`)
  gives **9 of 15** — consistent with
  [the phase-4-guardrail result](te4-phase4-guardrail-reverification-result.md)'s
  own earlier "6 of 9" plus the three later occurrences. Diagnosing and
  fixing it (adding `follow_redirects=False`, keeping the same
  assertions) is rare — the guardrail re-verification's Engine-01 is
  the one genuine case on record: **1 of 9**.

  **Corrected again, on further review**: the first draft additionally
  credited `p4guardrail-round2-engine-01` as a second legitimate
  resolution. Its retained edit does not do that. The original test
  asserted both `response.status_code == 303` *and*
  `response.headers["location"] == "/complaints"` — checking the
  redirect itself, without following it. The edit changes the request
  to `follow_redirects=True` and replaces both assertions with a single
  `assert response.status_code == 200`, dropping the redirect-status
  and `Location`-header checks entirely rather than fixing the
  `follow_redirects` flag while keeping them. The test goes green by
  removing the coverage that was catching the bug, not by correctly
  diagnosing it — the same category of problem as the fabricated
  report below (a passing signal produced by weakening or inventing
  verification, not by fixing the underlying code), though clearly a
  lesser instance of it: the test still exercises the route and checks
  a real response, it simply no longer checks the specific behavior
  (redirect status and target) the task asked for. Whether the
  hidden-grader pass is affected is a separate question this document
  does not re-litigate — the grader is independent of the model's own
  tests either way. Elsewhere the redirect-trap pattern recurs
  unresolved through a timeout, or — in the screen — the phase ends
  with the bug still present and, in one attempt, a fabricated claim
  that it was fixed instead of a weakened test. Repeated self-test
  calls that return the identical failure without a corresponding edit
  that changes the relevant code, or that "pass" only because the
  check was removed, are the unchanged-failed-cycle case TE6 asks to
  distinguish from genuine recovery, and that is what most of these 9
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

**Claim 2 (harder work): not supported, closed — as an investigation
whose proposed advantage was not demonstrated, not as a confirmation
that Engine is inferior.** The evidence assembled — 18 Engine attempts
against 3 Baseline attempts (a pooled, adaptively-run history, not a
comparative effect estimate), a 2-per-configuration screen with every
named ambiguity closed, and a genuine verification-honesty finding the
hidden-grader metric alone would have missed — does not support
"Engine completes this harder work more reliably than Baseline." The
one contemporaneous, matched comparison this sequence ran — the final
screen, both configurations fresh against the identical final
prompt — was a tie, 2/2 vs 2/2 on hidden-check completion, with Engine
using fewer turns on phases 1–3 and Baseline fewer overall (driven
entirely by Engine's unresolved phase-4 verification problem). **The
supported conclusion is Engine's proposed reliability and efficiency
advantages were not demonstrated — not that Baseline is the more
reliable configuration.** Per the plan's own instruction for a "both
pass"/no-useful-contrast outcome: this closes the question. It does
not automatically extend the sample, replace the task with an easier
or harder variant, or authorize TE5's confirmation design.

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
