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
  corrected after Fable's review: phase-2-board 7/7 clean, the
  before-`agent_name` mistake gone. `id`-no-default recurred, but
  Engine-02's failures mostly trace to a destructive `edit` that
  deleted its phase-3 route — phase 2's own former mechanism,
  recurring at an unguarded phase. Named candidate tightening 4.
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
self-test-tool-live-verification-pre-run-record
first-engine-comparison-plan
first-smoke-run-record
triage-candidate
```
