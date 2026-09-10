# Phase TE: fewer wasted turns, more work within budget

Proposed 2026-09-10, following [Phase HP](orchestrated-delivery-design.md).
This is an execution sequence, not authorization to implement, commit, or
run inference. Each live stage needs its own frozen, authorized budget.
`BRIEF.md` owns evidence and comparison policy; `ROADMAP.md` owns status.

## Goal and the two claims

Determine whether the actual Engine configuration improves development on
AgentClinic in two useful ways:

1. **Easy work:** both configurations reliably complete the roadmap, but
   Engine completes it in fewer total model turns without sacrificing quality.
2. **Harder work:** Engine reliably completes a more demanding roadmap within
   a practical turn ceiling; Baseline completes it substantially less often
   under the same ceiling.

**Fewer turns is the outcome, not a proxy for elapsed speed.** The proposed
explanation is that Engine avoids doom loops, repeated ineffective repairs,
and unnecessary rediscovery, leaving more of the budget for useful work.
The result and its explanation are separate claims: fewer turns can be
established without establishing why. A failing test followed by a successful
correction is productive recovery, not automatically a wasted repair loop.

The target conclusion is bounded:

> Under these model, task, tools and budget conditions, Engine needed fewer
> turns on work both configurations could complete, and completed harder work
> more reliably within the declared turn ceiling. Here are the uncertainty,
> retained checkpoints and traces, including failures and counterexamples.

Either claim may be supported, contradicted, or inconclusive independently.
“Baseline cannot” means failure to complete reliably under the specified
conditions and ceiling, not an absolute capability limit. These two roadmaps
do not establish that Engine is generally better across development work.

## The treatment, resolved 2026-09-10

TE1 found the pair this document was originally written against does not
exist as such. `arms/engine.json` — pinned to `engine_commit: fc22622`,
predating HP3, driving `satyrn-engine attempt` — is the paused engine
comparison's arm, a different campaign, and must not be read as this
phase's Engine configuration. **The actual pair, adopted here as the
treatment:**

- **Baseline:** the continuous Pi session, `adapters/pi_session.py`, one
  conversation carried through all three phases.
- **Engine:** Phase HP's orchestrated packet route —
  `route.run_phases` dispatching bounded per-phase handoffs to a real
  implementer (`adapters/pi_implementer.py`), **with HP3's chained
  isolation composed into it.**

**This tests a workflow bundle — packet-bounded scope, explicit per-phase
facts, and (once composed) isolated worktrees preventing cross-phase
contamination — never Engine's own in-conversation guards.** The loop
breaker and progress rule are Pi extensions; `pi_implementer.py` invokes Pi
with `--no-extensions --no-skills`, so neither loads. This corrects TE1's
own later text below ("Existing Engine breaker behavior is part of the
frozen treatment") — no breaker behavior is in this treatment at all, and
TE draws no conclusion about it. Any turn savings Engine shows here come
from the bundle's structure, not from a mechanism this route never
exercises; attributing a result to a specific mechanism, rather than the
bundle, needs a separately controlled ablation (TE6 already says this).

**HP3 composition is an explicit readiness blocker**, not a detail to
finish quietly alongside confirmation. TE does not launch against the
uncomposed route.
[`hp7-live-route-proof-pre-run-record.md`](hp7-live-route-proof-pre-run-record.md)
already blocks HP7 on this by the same maintainer decision; TE inherits
the block rather than re-deciding it. `satyrn-engine`'s own roadmap names
the concrete external-interface and contract-mapping gap that composition
needs (`satyrn-engine/ROADMAP.md`, "Composing HP3 into satyrn-evals").

**TE's two goals survive this correction; only their attribution changes.**
Fewer turns on easy work both configurations complete, and more reliable
completion of harder work within a shared ceiling, remain the claims
TE2-TE5 test. What changed is what a positive result would mean: not
"Engine's guards prevent doom loops" (untested here, since they are never
loaded), but "this workflow bundle needs fewer turns / completes more
reliably than a continuous session" — the configuration-bundle framing
TE1's own text below already required is not new; this section is what
applying it to the concrete, resolved pair requires.

**The Baseline readiness gap named above is now closed, 2026-09-10.**
`adapters/pi_session.py`'s event filter (`_SESSION_KINDS`) now retains
`turn_start`, `message_start` and `tool_execution_start` (mapped to kind
`"other"`), so a Baseline session captured from here on can answer "how
many turns started" and "was one left open" — not just ended-turn counts.
One honesty caveat survives: `turn_ledger.events_from_session_transcript`'s
`starts_retained` reflects the *live* policy, so reading an
**already-retained** transcript from before this fix (including this
design's own real fixture) still reports `starts_retained=True` while
genuinely containing zero starts — a caller analyzing archived evidence
must track each file's own capture-date policy, not trust the live check
for anything not captured just now
(`tests/test_turn_ledger.py::test_the_real_transcript_now_reads_starts_retained_true_despite_predating_the_fix`).
No fresh Baseline evidence exists yet under the fixed policy; TE1's own
"started model generation request" definition is measurable going
forward, not yet demonstrated against a real post-fix trace.

## Entry: finish HP, do not redefine its acceptance

HP owns the operable route; TE owns confirmation. Do not move unfinished HP
work into a new instrument phase. Before TE launches, verify the composed
route uses the intended Engine execution, predecessor-based isolation and
integration, executable public verification, and enforceable limits. Retain
checkpoint bytes and worker events before grading, including partial chains;
demonstrate independent offline regrading, not stored-verdict read-back.

HP7 supplies route evidence and HP8 supplies exploratory workflow evidence.
Reuse them where their frozen conditions answer the preparation question.
They remain outside every TE confirmation denominator. A packet wrapper
around Baseline Pi is not, by naming it so, an Engine arm; and a workflow
comparison alone is not evidence about a particular Engine mechanism.

## Repair ownership: the initial configuration and follow-on work

**Implementer-local verification and correction are included.** Before handing
back a candidate, the implementer may run the prescribed public pytest command,
inspect failures, correct application code, and rerun within its remaining
budget. One handoff does not mean one model generation or no opportunity to
repair. HP1's [packet spec](../superpowers/specs/2026-09-09-hp1-handoff-packet-design.md)
already gives `self_test_command` to the implementer's own feedback loop;
an adapter that cannot execute it is an HP readiness gap, not a decision to
forbid self-correction. Both configurations need equivalent verification
capabilities; a bounded test tool can supply them without unrestricted `bash`.
Removing tests or weakening assertions must not count as repairing the app;
independent grading still decides whether the requirements were met.

**Orchestrator-directed repair is a different engine change.** After a returned
candidate fails public validation, the orchestrator could dispatch a targeted
repair request. Its hypothesis is that a fresh handoff with useful failure
feedback rescues work in fewer total turns than continued local repair. It
could instead introduce another unproductive loop. Default to studying this
as separately authorized follow-on work, motivated by retained HP/TE failures,
not enabling it silently during a TE screen or confirmation.

If this outer loop is essential to the Engine configuration the maintainer
intends to use, explicitly amend the selected treatment and test the candidate
before TE confirmation. Do not confirm a configuration already intended for
replacement. Use a separately authorized bounded candidate screen, keep its
observations outside confirmation, then freeze the adopted behavior and rerun
only the preparation checks affected by the change. No configuration changes
are allowed within a confirmation batch.

Any outer-loop candidate must use public validation feedback, never hidden
grader output; retain every failed candidate, validation result and dispatch;
and predeclare a redispatch limit inside the shared whole-attempt turn ceiling.
Handoffs do not replenish the budget. **Direct orchestrator-written repair is
a third, explicitly labelled fallback condition**, not an interchangeable
implementation of redispatch. Attribute and count all work in every role;
neither fallback nor a later successful repair erases the earlier failure.

These distinctions preserve [HP's scope](orchestrated-delivery-design.md):
implementer self-testing is part of the initial route; post-handoff repair
campaigns and orchestrator-written fallback are excluded unless separately
selected, reviewed and frozen as the treatment. Earlier SwiftStar repair-loop
and one-shot-first designs are candidate evidence, not one universal policy.

## Sequence and exit evidence

| Step | Work | Exit evidence | GPU/model inference |
| --- | --- | --- | --- |
| TE1 | Identify the actual pair and audit turn accounting against HP artifacts. | Matched configuration record; discriminating counting witnesses; readiness decision. | None. |
| TE2 | Screen the existing easy roadmap, reusing applicable HP8 evidence. | Two attempts per configuration if a fresh screen is needed; a bounded confirmation proposal or a reason not to pursue the easy claim. | Only an authorized new screen, if needed. |
| TE3 | Confirm easy-roadmap turn efficiency with a quality guardrail. | Frozen analysis of fresh attempts; supported, contradicted, or inconclusive easy claim. | Separately authorized fixed batch. |
| TE4 | Qualify one harder roadmap and screen it. | Offline behavior witnesses, then two attempts per configuration and a harder-claim decision. | Only its authorized screen. |
| TE5 | Confirm harder-roadmap completion within budget. | Frozen analysis of fresh attempts; supported, contradicted, or inconclusive harder claim. | Separately authorized fixed batch. |
| TE6 | Review both claims and decide what to adopt or investigate. | Reproducible result and scoped Engine decision, with no automatic follow-on campaign. | None. |

Run in this order. A negative easy result does not logically rule out the
harder claim: record that result and proceed to the separately authorized
harder stage if its development rationale still holds. No stage requires a
positive result to count as completed work.

## TE1 — fix the contrast and the unit of effort

Name the Baseline executable and Engine executable, revisions, configuration
digests and actual enabled Engine features. Default to the same implementer
model, provider, sampling settings and effective tool capabilities. Freeze the
user-visible roadmap, accessible project facts, public tests and verification
instruction, dependencies, workspace scope, acceptance schedule and feedback.
Hidden grading material never reaches either solver.

Explicitly list the intended workflow differences: context continuity,
packet construction, handoff and integration behavior. If these require
different feedback or role models, disclose the difference and label the
result a configuration-bundle comparison, not an isolated component effect.
Do not silently add an orchestrating model to HP's deterministic packet route.

**Turn definition:** one started model generation request, whether it ends
in tool calls, a final answer, a refusal, an error or an interruption. It is
not a user phase, a tool call, or a streaming update. Count retries, restarts,
model-driven compaction and all implementer/orchestrator/fallback generations.
Deterministic orchestration contributes no model turns. Record failed requests
that never started separately; unresolved starts or missing events are unknown,
not zero. Freeze each provider/adapter's mapping from retained events to this
unit and reconcile it against request starts and terminal response identities.

Recompute per-phase, per-role and whole-attempt totals from raw events. Keep
the role breakdown **and** its total; separate accounting does not prohibit
summing comparable units. Streaming snapshots must not multiply requests or
usage. Tool calls, elapsed time, tokens and cache accounting are secondary
diagnostics, never substituted for turns.

Use existing parsers and capture machinery. Add only a demonstrated missing
boundary check: a multi-role trace, duplicated streaming updates, a restarted
request, and missing worker events must distinguish correct counts from
inflated or silently incomplete ones. No general pathology detector is needed.

Freeze a shared whole-attempt turn ceiling per workload, covering all roles
and phases without resets at handoffs, plus a whole-attempt safety deadline
and token/resource limits. Check representative retained traces before
proposing values. Record how concurrent/in-flight calls are bounded; a textual
packet budget is not enforcement. Do not add a harness repeat cutoff when
recovery from repetition is the question. **Corrected 2026-09-10** (see "The
treatment, resolved" above): no Engine breaker behavior is loaded in this
treatment at all, so there is none to call part of the frozen treatment.
Whether recovery from repetition needs a guard neither route currently has
is exactly what confirmation observes, not something to preempt by adding
one now.

**The shared whole-attempt turn ceiling, frozen 2026-09-10: 40 turns.**
Checked against every real `agentclinic-session-phased` Baseline
transcript on record, recomputed through `turn_ledger.count_turns` itself:

| Attempt | Whole-attempt ended turns | phase-1 / phase-2 / phase-3 |
|---|---|---|
| `2026-09-09-session-phased-112550` | 15 | 6 / 5 / 4 |
| `2026-09-09-session-phased-verify-114708` | 20 | 7 / 6 / 7 |
| `2026-09-09-verify-triage-132612/01-control` | 15 | 6 / 5 / 4 |
| `2026-09-09-verify-triage-132612/02-verification` | 25 | 7 / 6 / 12 |
| `2026-09-09-verify-triage-132612/03-verification` | 22 | 9 / 8 / 5 |
| `2026-09-09-verify-triage-132612/04-control` | 20 | 9 / 6 / 5 |

Range 15–25 (mean ≈19.5), max per-phase 12, zero errors or aborts. 40 is
roughly 1.5x the observed maximum — headroom over noise, sized the way
HP7's own pre-run record sized its per-phase figure. **Baseline-side
only**: Engine's real turn counts remain unmeasured (HP7 has not run
live), so this is not yet checked against both sides of the pair; revisit
once Engine-side evidence exists.

**Exit:** the pair really exercises Engine versus Baseline, the turn accounting
is reproducible, and the run can be bounded without hiding failed work. New
operability checks are needed only for changed paths not covered by HP; use
one bounded attempt on each affected path, outside the scored denominator.

## TE2–TE3 — easy-roadmap efficiency

Start with the existing qualified `agentclinic-session-phased` roadmap.
“Easy” is a hypothesis for this exact pair, not a permanent task label or a
conclusion from four passes. Keep the roadmap fixed through confirmation.

Use HP8 as the screen if its actual pair, workload and observables match.
Otherwise declare the mismatch and authorize at most two fresh attempts per
configuration as triage. Inspect completion, total turns and representative
traces, including contrary examples. Do not repeat a screen until a favorable
one appears. A promising result informs the confirmation design; it is not
pooled into it. If no useful efficiency hypothesis survives, close this claim
without a larger run rather than treating repetition as the default remedy.

For confirmation, success means every required phase completes and the
cumulative checks preserve earlier requirements at each checkpoint. Freeze
the rule for within-phase repairs versus a rejected checkpoint. Report final
completion and checkpoint regressions separately; later recovery must not erase
the earlier observation. Ordinary failed attempts stay in the denominator.

Use a joint decision, specified numerically before inference:

- Both configurations meet a stipulated minimum completion reliability, and
  Engine's completion probability is not worse by more than a small,
  explicitly accepted non-inferiority margin.
- Engine reduces mean **observed total model turns across all attempts** by
  at least a stipulated useful amount, with the planned uncertainty bound
  supporting that improvement.
- The budget-penalized turn score below does not worsen under its predeclared
  uncertainty rule, guarding against an apparent saving from early failures.

To prevent early failure masquerading as efficiency, use **budget-penalized
turns** as an additional all-attempt guardrail: a successful attempt uses
its observed total turns; any ordinary unsuccessful attempt is assigned the
shared turn ceiling. This is an analysis score, not fabricated model usage.
Also publish actual turns for every attempt, success-by-turn summaries, and
successful-only turns as descriptive evidence, not the sole comparison.
Missing capture is not an ordinary failure; follow the integrity rules below.
Improving this score alone can reflect higher completion despite using more
actual turns. That is improved budget-penalized performance, not evidence of
the fewer-turns claim; the observed-turn criterion must also pass.

The useful turn reduction, reliability floor, non-inferiority margin and
shared ceiling are maintainer-approved practical choices, not estimates of
the biggest effect in the screen. A lower median among surviving successes
or a non-significant quality difference alone cannot pass the joint decision.

**Exit:** fresh confirmation evidence addresses the easy claim, or a recorded
triage decision closes it. Equal completion can still support turn efficiency.

## TE4–TE5 — one harder roadmap, not an expanding search

Add exactly one more demanding AgentClinic roadmap, selected for a concrete
development requirement rather than an observed Engine-favorable score.
Starting candidate: extend the app with stable complaint identity and a
resolve/reopen lifecycle spanning model, routes and templates, while preserving
the earlier creation, display and ordering behavior. Qualify its feasibility
against the existing app before committing to that design. This is a proposed
requirement, not a claim that either configuration will struggle with it.

Difficulty should come from meaningful dependencies and preservation, not
misleading instructions, unavailable tools, hidden requirements, or grading
ambiguity. Reuse the current app, checkpoint grader and fixture machinery.
Map every requirement to accessible instructions and public/hidden checks;
run base, known-good, incomplete, and realistic regression witnesses offline.
Both configurations receive the same requirements and opportunity to verify.

Declare the practical shared ceiling and run a two-per-configuration screen,
with only necessary route checks for changed execution paths. Disclose any
prior results informing selection. Screen cells stay outside confirmation.
If both pass, both fail, or no useful contrast appears, report that finding;
do not automatically make the task harder, enlarge the budget, or shop among
variants. A further candidate requires a separate development rationale.

Confirm only a justified harder-work hypothesis, with fresh attempts. The
primary outcome is the proportion completing the required roadmap and
preservation checks within the shared total-turn ceiling. The decision needs
both a stipulated minimum Engine reliability and a practically meaningful
completion advantage, supported by the predeclared uncertainty bounds.
Report all actual turns and checkpoint outcomes, including budget exhaustion.
Success only beyond the frozen ceiling does not support this claim.

**Exit:** evidence supports, contradicts, or leaves unresolved “Engine completes
this harder work reliably within budget more often than Baseline.” Zero
Baseline successes in a finite sample never establishes absolute inability.

## Confirmation design and spending, shared by TE3 and TE5

One short pre-run record per confirmation supplies the values this roadmap
deliberately does not guess: practical effect thresholds, reliability/margin
choices, turn/deadline ceilings, exact tests and confidence intervals, sample
size, schedule, output roots and total spending ceiling. Choose a statistical
method matching each estimand: binary completion and turn expenditure are not
the same test. Name the significance level, target power, joint-decision and
multiple-claim handling; calculate sample size for every required guardrail,
not just the easiest endpoint to power. No universal sample size is assumed.

Power against stipulated useful effects, with explicit independence and
distribution assumptions. Use screen/retained data to examine nuisance
variability and ceiling effects, not to power against an inflated observed
win. Show sensitivity to plausible failure rates and heavy-tailed turn costs.
If affordable sample sizes cannot answer the question, report that tradeoff
before spending; do not call underpowered triage confirmation.

The independent unit is a whole roadmap attempt, never its phases or tool
calls. Randomize and interleave the pair within predeclared run blocks; freeze
seeds and model/server configuration. Shared seeds alone do not establish
statistical pairing. Account for block/time variation in design and analysis,
rather than assuming a larger sample removes changing execution conditions.

Analyze once at the fixed end. Checkpoints concern execution integrity, not
which configuration is winning. Ordinary model refusals, loop behavior,
timeouts and failed repairs remain counted outcomes. Diagnose suspected
infrastructure failure before classifying it; preserve affected cells and
missingness. Resume healthy interrupted work. A materially changed condition
needs a separately authorized replacement, with the original partial batch
reported separately; never restart from zero or replace losses by default.

Budget route checks, warm-up/preflight completions and scored runs explicitly
and separately. Derive a duration estimate from applicable measured runs and
state its uncertainty; do not promise hours from an unrelated task. Sol reviews
readiness before spending; the maintainer authorizes the exact live scope.
No live stage is authorized by this roadmap or by a previous stage's budget.

## TE6 — explain the result and decide

Regrade retained checkpoint bytes offline and reconcile the frozen analysis.
For each claim report its population, missingness, effect estimate, uncertainty,
quality guardrail and turn result. Equal grades do not erase a turn difference;
fewer turns with worse completion does not establish the easy claim.

Inspect trace-backed examples of unproductive repetition versus productive
recovery using a small written rubric and reproducible event references.
Repeated reads/tests after relevant edits are not automatically waste; distinguish
state changes, new feedback and useful correction from unchanged failed cycles.
Review counterexamples, not only the most dramatic Baseline lock. Any summaries
state which attempts were inspected and how they were selected. This explains
observations; attributing a win to a particular breaker or handoff mechanism
requires a separately controlled ablation, not a retrospective story.

Astra's final review asks whether the two claims actually follow, whether all
roles and failed work were counted, and whether retained evidence supports
regrading and turn reconstruction. Decide adoption separately for the claims.
A supported task-specific win is useful; an inconclusive or negative result
closes the question without automatic sample extension or replacement task.

No new dashboard, telemetry platform, generic detector, autonomous planner,
model sweep, worker pool or benchmark matrix belongs in TE. Instrument fixes
must unblock a named measurement and use the cheapest existing path; retain
`AGENTS.md`'s cumulative instrument-only limit. Broader generalization across
additional roadmaps/models, or a mechanism ablation, is later separately
authorized work only if a development need warrants it.
