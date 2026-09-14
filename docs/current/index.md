# Current work

This directory contains the current designs and ordered execution plans.
It is deliberately small: use these pages for this work, and use
the repository's archive only to retrieve evidence, code history, or a named
past artifact. Archived material does not set current policy.

- [AgentClinic suite brief](agentclinic-suite-brief.md) proposes the next bounded
  sequence: finish existing repairs, qualify one useful additional condition,
  verify its live route, run a matched four-attempt Engine/Baseline screen, and
  decide what the evidence warrants.
- [misleading-locus R1 comparison design](misleading-locus-r1-comparison-design.md)
  is the proposed next experiment: a disclosed replication at `n=36` per arm,
  with its power, assumptions, checkpoint rule and stopping rules fixed in
  advance. It authorizes no spending.
- [Overnight cycle protocol](overnight-cycle-protocol.md) is the loop the
  authorized overnight work runs under: find a reproducer, remedy it, have it
  reviewed, close the cycle.
- [Proposal: build the phased application as a session](agentclinic-phase-session-proposal.md)
  argues the next multi-prompt workload should be the AgentClinic phases rather
  than a synthetic task, and names two prerequisites measured over twelve
  sessions. It authorizes nothing.
- [Pre-run record: the bounded Baseline session](session-ordering-baseline-pre-run-record.md)
  freezes the conditions for one Baseline session on the cross-prompt witness
  task, and states what a single session cannot establish.
- [Orchestrated delivery](orchestrated-delivery-design.md) proposes the next
  phase as an **adaptation of SwiftStar's exercised design**, not a new
  orchestration design: the existing phased roadmap carried through bounded
  implementer handoffs over chained isolated checkouts, with role attribution
  required so a passing workflow cannot hide a silent implementer. It
  supersedes the brief's Part 2 and authorizes nothing.
- [After HP: turn efficiency and harder work](engine-turn-efficiency-plan.md)
  sequences two focused claims: fewer total model turns without sacrificing
  easy-roadmap quality, then more reliable completion of one harder roadmap
  within a shared turn ceiling. It separates confirmation from exploratory
  screens and from the hypothesis that reduced looping explains an advantage.
- [Next-agent brief: correct the screen, then put Engine on the phased
  workload](next-agent-brief-engine-on-phased.md) is the current handoff: six
  documentation corrections that need no new run — **applied 2026-09-09** —
  then the Engine session capability, which is the open work.
- [Triage screen: the verification instruction](agentclinic-verification-triage-screen.md)
  freezes four sessions, two per prompt condition, and states what a screen
  that size cannot establish.
- [Pre-run record: the verification instruction](agentclinic-session-phased-verification-pre-run-record.md)
  freezes the second phased session, which asks only whether an explicit
  verification instruction is usable — not whether it improves behaviour.
- [Pre-run record: the phased AgentClinic session](agentclinic-session-phased-pre-run-record.md)
  freezes the arm, digests, n and observables for one Baseline session on the
  phased workload, and records the fairness limitation it carries in.
- [Pre-run record: misleading-locus R1](misleading-locus-r1-pre-run-record.md)
  fixes that design's concrete values, measures, disclosure and stopping rules.
- [Pre-run record: misleading-locus R3](misleading-locus-r3-pre-run-record.md)
  freezes the conditions, per-arm surfaces, limits, and stopping rules for the
  route verification and the four-attempt screen, before anything is spent.
- [Pre-run record: HP7 live route proof](hp7-live-route-proof-pre-run-record.md)
  freezes one bounded packet-route chain and states it establishes
  operability, not superiority. Corrected 2026-09-10 before any inference to
  the HP3-composed route; both named blocking gaps closed the same day.
- [HP7 live route proof — result](hp7-live-route-proof-result.md) reports
  the one run this record authorized: all three phases accepted, real
  chained isolation, zero `check_chain` findings, model identity verified
  from the transcript.
- [Pre-run record: TE2/HP8 screen](te2-hp8-screen-pre-run-record.md)
  instantiates the TE plan's decided "HP8 is this screen" design: two
  attempts per configuration, frozen questions on completion and turn
  efficiency, and a public-test-quality review alongside the hidden pass
  count. Decides whether a confirmation is worth running, not superiority.
- [TE2/HP8 screen — result](te2-hp8-screen-result.md) reports the four
  attempts, corrected 2026-09-10 after review: Baseline completed both;
  Engine completed one of two, the other a genuine runaway loop. Turn
  efficiency is inconclusive on completed work and unfavorable on
  all-launched-attempts expenditure. TE3 is not pursued, not reopened
  without new evidence; TE4 scoping starts separately.
- [TE4 harder roadmap — design](te4-harder-roadmap-design.md) qualifies
  the feasibility of extending the app with stable complaint identity
  and a resolve/reopen lifecycle, resolving the one real preservation
  conflict it creates (a kw_only `id`/`status` field, so the existing
  positional `Complaint` contract check still holds). Grader tests,
  fixtures and the offline qualification suite are now built and
  proven; no inference yet.
- [Pre-run record: TE4 route proof](te4-route-proof-pre-run-record.md)
  freezes one attempt per configuration on the new task, proving it
  resolves and grades correctly live and grounding a turn ceiling in a
  real transcript. Establishes neither completion reliability nor
  turn efficiency, and does not authorize TE4's own screen.
- [TE4 route proof — result](te4-route-proof-result.md) reports the
  two attempts: Baseline completed all four phases but a phase-4 check
  rejected a valid solution (a grader defect, **fixed** 2026-09-10), and
  Engine's phase-2-board timeout reproduced with the same signature as
  TE2/HP8's own Engine-01 — 2 of Engine's 4 live phase-2-board attempts
  have now run away, the other 2 completed in 8–9 turns. Recommends
  investigating that pathology before TE4's screen, which is not
  authorized by this result.
- [Phase-2-board runaway — investigation](phase-2-board-runaway-investigation.md)
  compares all four real Engine phase-2-board transcripts on record and
  finds a specific, reproducible mechanism: a destructive `edit` that
  deletes the phase-1 home route, converging on a file with an import
  bug never caught because `run_self_test` is never called. Names a
  candidate remedy; authorizes no test of it.
- [Pre-run record: phase-2-board guardrail candidate](phase2-guardrail-candidate-pre-run-record.md)
  freezes a bounded probe of the one testable candidate remedy — a
  one-sentence prompt guardrail, on a two-phase task built for this
  test alone, not amending either accepted task. Proposes 3 Engine +
  1 Baseline attempt; names the 50% base rate this is being read
  against. Authorizes nothing yet.
- [Guardrail candidate — result](phase2-guardrail-candidate-result.md)
  reports 3 of 3 Engine attempts completing cleanly, zero destructive
  edits observed (one attempt reached the exact decision point and
  took the safe, additive branch). Not statistically conclusive at
  this `n` against the 50% base rate. **Adopted 2026-09-10 into
  `agentclinic-complaint-lifecycle` only** — see that task's own
  `QUALIFICATION-NOTE.md`; `agentclinic-session-phased` is untouched.
- [Pre-run record: TE4 guardrail re-verification](te4-guardrail-reverification-pre-run-record.md)
  freezes 2 Engine attempts on the full, guardrail-amended task —
  phase 4 has never been reached live before, on either route, and no
  turn ceiling exists yet since Engine has completed this task zero
  times. Authorizes nothing yet.
- [Guardrail re-verification — result](te4-guardrail-reverification-result.md)
  reports both attempts reaching phase 4 for the first time ever, both
  failing there for two different real reasons (an `id`-field-ordering
  ambiguity; a redirect-following trap in the model's own test,
  correctly caught by self-test but misdiagnosed) — neither a repeat
  of the phase-2-board pathology, which held clean 2 of 2. No ceiling
  proposed; TE4's screen still not authorized. The ordering ambiguity
  is since closed by tightening 3.
- [Pre-run record: tightening-3 re-verification](te4-tightening3-reverification-pre-run-record.md)
  proposes 2 more Engine attempts to see whether the id-ordering fix
  actually lets Engine complete the full task — never yet achieved
  across any attempt on this task family. Authorizes nothing yet.
- [Tightening-3 re-verification — result](te4-tightening3-reverification-result.md),
  corrected twice after Fable's review: phase-2-board 7/7 pass, the
  before-`agent_name` mistake gone — but (second correction) its own
  Engine-02 shows the guarded-against edit occurred there too and
  self-corrected; "pass" never meant "the edit never happened."
  `id`-no-default recurred, and Engine-02's failures also trace to a
  separate destructive `edit` that deleted its phase-3 route — phase
  2's own former mechanism, recurring at an unguarded phase. Named
  candidate tightening 4.
- [Pre-run record: tightening-4 re-verification](te4-tightening4-reverification-pre-run-record.md)
  and its
  [result](te4-tightening4-reverification-result.md), corrected then
  resolved: tightening 4 applied and validated — one attempt gets the
  `id` design entirely right. But 3 of 4 graded phase-4 attempts on
  record destroyed the phase-3 route the same way phase 2 needed its
  own guardrail for — too high a rate to call variance. **Phase-4
  guardrail applied** (see the task's own `QUALIFICATION-NOTE.md`).
  Engine has completed the full task 0 of 8 times (0 of 7 that reached
  phase 4). Re-verifying the guardrail is next.
- [Pre-run record: TE4 completion-rate check](te4-completion-rate-check-pre-run-record.md)
  — **superseded** before its second and third attempts ran; its
  premise (no prompt change needed) was the mischaracterization the
  phase-4 guardrail corrects. Its one completed attempt is retained as
  the third confirming occurrence of the route-deletion pattern.
- [Pre-run record: TE4 phase-4-guardrail re-verification](te4-phase4-guardrail-reverification-pre-run-record.md)
  freezes 3 Engine attempts testing whether the phase-4 guardrail stops
  the destructive route deletion. Authorizes nothing yet.
- [Phase-4-guardrail re-verification — result](te4-phase4-guardrail-reverification-result.md),
  **corrected twice** (a first pass fixed an extraction bug that
  silently dropped every `run_self_test` call and missed two named
  mechanisms entirely; a second, narrower pass fixed remaining
  misattributions and an undercounted redirect-trap tally): zero of
  three complete; two reach phase 4 for the first time under the
  guardrail, both hitting the recurring `assert status_code == 303`
  redirect trap (now confirmed in 6 of 9 phase-4-reaching attempts,
  resolved correctly in only 1). One voids on ordinary time exhaustion
  with no destructive edit; the other reproduces the route-deletion
  mechanism the guardrail was applied to stop, and also drops the one
  inherited test that would have caught the loss. The third times out
  at phase-2-board via the *original* import-bug runaway — but
  re-checked across every post-guardrail attempt, that guardrail's own
  edit still occurs in 5 of 10 attempts, just self-correcting in all
  but this one. Phase 4's edit now recurs in 7 of 9 phase-4-reaching
  attempts, 4 of 9 never self-correcting. Not enough evidence to call
  the phase-4 guardrail settled either way.
- [Pre-run record: TE4 phase-4-guardrail re-verification, round 2](te4-phase4-guardrail-reverification-round2-pre-run-record.md)
  freezes 2 more Engine attempts, bringing the phase-4-guardrail-era
  total to 4 phase-4-reaching attempts — enough to move past round 1's
  single data point on whether the guardrail changed the
  destructive-edit rate. Explicitly does not propose a fifth tightening
  for the redirect-trap pattern, classifying it as testing friction
  outside what a design-ambiguity closure should touch. Authorizes
  nothing yet.
- [Round 2 — result](te4-phase4-guardrail-reverification-round2-result.md),
  **corrected after review**: **the first two full completions ever on
  this task family**, 18/18 hidden checks each. Both attempts still
  made the destructive edit the guardrail targets and both restored
  it — but restoring it is not new (found, on correction, in 2 earlier
  attempts that restored the same way and still timed out); what
  actually distinguishes these two is only that they finished within
  budget afterward, unexplained by anything in this record. Across all
  4 phase-4-guardrail-era attempts, the edit still occurs 3 of 4 (same
  as pre-guardrail). 2 of 13 cumulative; not a completion rate.
- [Pre-run record: TE4 completion-recurrence check](te4-completion-recurrence-check-pre-run-record.md)
  freezes 3 more Engine attempts at the unchanged post-guardrail
  prompt, asking only whether round 2's two completions recur at all —
  no further prompt change. Authorizes nothing yet.
- [Completion-recurrence check — result](te4-completion-recurrence-check-result.md),
  **corrected after review**: 2 more full completions (18/18 each) and
  one phase-2-board runaway recurrence (the *original* import-bug
  pathology, not a phase-4 issue). A first draft's clean 4-of-4-vs-2-of-2
  split was cherry-picked (restricted to the guardrail era, missing 3
  attempts on record that also restored and still failed). Restated
  against all 13 phase-4-reaching Engine attempts: restoring the
  destructively-edited route is necessary for completion (0 of 6
  non-restorations pass) but not sufficient (4 of 7 restorations pass;
  the other 3 all time out, none is submitted-and-rejected) — turn
  budget, not correctness, is the remaining bottleneck, unexplained
  here. Cumulative: 4 of 16.
- [Pre-run record: TE4 screen](te4-screen-pre-run-record.md) freezes a
  2-per-configuration screen (per the TE plan's own TE4 step) now that
  every named blocking ambiguity is closed and Engine has completed
  the task 4 times. Baseline gets its first attempt under the current,
  fully-fixed prompt state. Declares a thin, explicitly-caveated
  75-turn shared ceiling from Engine's 4 completions alone. A screen,
  not a confirmation — its outcome is not pooled into any later one.
- [TE4 screen — result](te4-screen-result.md), **corrected after
  review**: both configurations pass the hidden grader both times
  (18/18 each), but neither screen Engine attempt's own required
  verification (`uv run python -m pytest tests`) ever passed at phase
  4 — the redirect-trap pattern, unfixed — and **one fabricated an
  invented "2 passed" pytest transcript while its own last tool call
  showed two failures**, a new, distinct behavior the first draft
  missed by only checking test-file structure. Per-phase turns: Engine
  used fewer on phases 1–3 (the original TE hypothesis) and far more on
  phase 4 alone (23 vs Baseline's 6–8) — the whole-attempt gap is
  entirely phase 4. Baseline's first data under the current,
  fully-fixed prompt is clean both times, tests included. Per the
  plan's own rule for a "both pass" screen: report it, don't enlarge
  the budget or shop for a harder variant.
- [TE6 — explain the result and decide](te6-explain-and-decide.md)
  closes Phase TE's two claims against the full evidence assembled.
  Claim 1 (easy work) is inconclusive, closed, not reopened. Claim 2
  (harder work) is **not supported**: Baseline is 3 of 3 on
  `agentclinic-complaint-lifecycle`, Engine 6 of 18. **Corrected
  2026-09-11 (V1):** an earlier draft read "— the opposite of 'Engine
  completes harder work more reliably.'" The supported conclusion is
  narrower and is `te6-explain-and-decide.md:255`'s: Engine's proposed
  reliability and efficiency advantages were not demonstrated, not that Baseline is the more
  reliable configuration. A verification-honesty
  finding (one Engine attempt fabricated a passing test report) shows
  the hidden-grader pass rate alone would have missed a real quality
  gap. No further live spending or TE5 confirmation is proposed;
  broader generalization is separately authorized work only if a
  development need warrants it.
- [Phase PD — prompt delivery](prompt-delivery-design.md) reads the
  2026-09-12 overnight result (Baseline 12 of 12, Engine 6 of 12,
  p=0.0069) as evidence about one over-hinted, inlined prompt condition
  rather than a verdict on either architecture, closes the
  `overnight-phase4-context` worktree as retained evidence, and proposes
  SDD-style spec-file delivery, an easy and a user-story hard variant on
  one grader, and an `n=2` screen. PD1 done; PD2–PD5 authorize nothing.
- [Phase PD, unattended: brief for a new agent](phase-pd-unattended-brief.md)
  authorizes PD2–PD5 to run once, unattended, as three roles per cycle —
  Opus steers, Sonnet implements, Fable reviews at each cycle's close — with
  the design's own exclusions restated as hard stops and no merge to `main`
  at the end.
- [Pre-run record: run_self_test live verification](self-test-tool-live-verification-pre-run-record.md)
  proposes one bounded `pi` invocation proving the self-test tool is
  reachable and its content legible, outside every TE denominator, and
  names the unresolved pi version mismatch as a blocking precondition.
  Authorizes nothing.
- [First useful engine comparison](first-engine-comparison-plan.md) is paused,
  not queued. Its live smoke is complete; further comparison requires a useful
  question and its own frozen, authorized budget.
- [Stage 3.1 triage candidate](triage-candidate.md) records the rejected
  loop-breaker candidate and the paused post-edit region candidate.
- [First smoke run record](first-smoke-run-record.md) retains the conditions and
  evidence from the completed bounded live smoke.
- [First-milestone design](first-milestone-design.md) defines the offline outcome,
  scope, evidence policy, and artifact contracts.
- [First-milestone execution plan](first-milestone-plan.md) gives the
  implementation sequence and acceptance witnesses.
- [Whole-attempt deadline design](whole-attempt-deadline-design.md) defines
  the bounded-live-work prerequisite. It does not authorize a live run.
- [Whole-attempt deadline plan](whole-attempt-deadline-plan.md) sequences the
  implementation and verification of that prerequisite.

The repository brief and the relevant designs own policy. Plans own the ordered
work; they do not create a second policy source.

```{toctree}
:hidden:

whole-attempt-deadline-design
whole-attempt-deadline-plan
agentclinic-suite-brief
overnight-cycle-protocol
misleading-locus-r1-comparison-design
misleading-locus-r1-pre-run-record
agentclinic-session-phased-pre-run-record
agentclinic-session-phased-verification-pre-run-record
agentclinic-verification-triage-screen
next-agent-brief-engine-on-phased
orchestrated-delivery-design
engine-turn-efficiency-plan
session-ordering-baseline-pre-run-record
agentclinic-phase-session-proposal
misleading-locus-r3-pre-run-record
hp7-live-route-proof-pre-run-record
hp7-live-route-proof-result
te2-hp8-screen-pre-run-record
te2-hp8-screen-result
te4-harder-roadmap-design
te4-route-proof-pre-run-record
te4-route-proof-result
phase-2-board-runaway-investigation
phase2-guardrail-candidate-pre-run-record
phase2-guardrail-candidate-result
te4-guardrail-reverification-pre-run-record
te4-guardrail-reverification-result
te4-tightening3-reverification-pre-run-record
te4-tightening3-reverification-result
te4-tightening4-reverification-pre-run-record
te4-tightening4-reverification-result
te4-completion-rate-check-pre-run-record
te4-phase4-guardrail-reverification-pre-run-record
te4-phase4-guardrail-reverification-result
te4-phase4-guardrail-reverification-round2-pre-run-record
te4-phase4-guardrail-reverification-round2-result
te4-completion-recurrence-check-pre-run-record
te4-completion-recurrence-check-result
te4-screen-pre-run-record
te4-screen-result
te6-explain-and-decide
self-test-tool-live-verification-pre-run-record
first-engine-comparison-plan
first-smoke-run-record
triage-candidate
phase-v-design
phase-v-claim-inventory
phase-v-engine-gap-register
phase-v-track-b-gate
prompt-delivery-design
phase-pd-unattended-brief
ornith-9b-pathology-probe-brief
ornith-9b-pathology-probe-pre-run-record
ornith-9b-pathology-probe-result
ornith-9b-ceiling-probe-brief
selfhost-headroom-probe-brief
ornith-9b-pathology-probe-result-addendum
```
