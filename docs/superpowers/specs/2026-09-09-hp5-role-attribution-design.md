# HP5 design: role attribution from retained events

Written 2026-09-09. Phase HP, cycle 5. Design only: **it authorizes no
implementation and no inference.** Read with
[the phase design](../../current/orchestrated-delivery-design.md), whose
deliverable D5 this specifies, and with `BRIEF.md`, whose invariants 1 and 5
decide most of what follows.

HP5 answers one question about a completed chain: **which role changed each
file?** It does not answer whether delegation helped, and it adds no
pathology detector. Those are HP8 and, respectively, nothing this phase
plans.

## The incident this exists for, read from its own record

SwiftStar's campaign at seed 221 printed:

```
[agenttest] directive: phase 1 — 0 mutation(s), passed
[agenttest] directive: phase 2 — 0 mutation(s), passed
[agenttest] directive: phase 3 — 0 mutation(s), passed
[agenttest] directive: orchestrator turn 2 …
[agenttest] directive: orchestrator turn 2 ended (stop eos), dispatched 0 phase(s)
[agenttest] directive: PASS — 3 dispatch(es), 2 orchestrator turn(s), acceptance exit 0, 1135s
```

(`swiftstar/captures/agenttest/20260829-212715-roadmap-user-story-directive/campaign-stdout.txt:14-19`,
quoted whole rather than trimmed to the three zeros, because the untrimmed
version is what makes the point.)

Three phases dispatched, three phases passed, and **not one of them changed
a file.** The campaign then reported `PASS` with the acceptance command
exiting 0.

**Where the work happened cannot be read from this log**, and saying it can
would be the same error the record is being cited against. The orchestrator
may have written the files in either of its two turns, or the acceptance
command may have passed on a tree nobody changed. The log records dispatches,
per-dispatch mutation counts and a verdict, and none of those distinguishes
the readings. That indistinguishability *is* the finding.

Two things follow, and only the second is the usual reading.

**SwiftStar did count.** The zeros are in its own output. What it lacked was
not a counter but a rule making the count part of the verdict's record, so a
`PASS` line could not stand beside three zeros without comment.

**SwiftStar counted only one side.** It reported the *implementer's*
mutations per dispatch and never the orchestrator's, so the log shows work
vanishing without showing where it went. A reader who sees three zeros still
cannot tell a silent implementer from a broken capture. Attribution by role
is the addition; counting is not.

## Attribution is observed, never reported

`ImplementerResult.changed_files` is what the implementer **says** it
changed. The route already refuses to treat that claim as a verdict
(`src/satyrn_evals/route.py:57-60`). Attribution must hold the same line, and
for the same reason: a silent implementer that reports three filenames it
never wrote is exactly the failure this cycle exists to catch, and a ledger
built from its claims would report the incident as healthy.

So attribution is computed from **workspace state observed by the harness**,
on both sides of each hand-off:

- the workspace as it stands **before** the packet is handed over;
- the workspace **after** the implementer returns;
- the workspace **before the next packet** is handed over.

The first difference is the implementer's. The second is the orchestrator's:
integration, a fix-up, or a fallback that did the phase's work outright.
Neither is anybody's claim.

**The claim is retained too, and never reconciled away.** Reported and
observed changes are both recorded, per file. Where they differ, both are
kept and the difference is stated. This is D6's rule arriving one cycle
early — a declaration the runtime did not apply is recorded as declared and
not applied, never as applied — and it costs nothing here because both halves
are already in hand.

## What a mutation is

A **mutation** is one path whose observed content differs across a window:
created, deleted, or modified. Not a line count, not a diff size, not a
weight. The seed-221 shape is a count of zero, and a zero is unambiguous
whatever the unit; anything richer invites a threshold, and a threshold is a
budget verdict, which `BACKLOG.md` defers on its own merits.

Content is compared by digest rather than by bytes retained. The chain
retains the candidate change already (D6); the ledger needs to know only
*that* a path differs, and a digest says so without a second copy of the
tree.

## Both directions, or it does not ship

`BRIEF.md` invariant 5, applied to a detector rather than to a refusal. The
attribution report must be shown to discriminate **on the same fixture
family**:

- a chain where the implementer delivers every phase reports those
  mutations to the implementer, and **zero** to the orchestrator;
- a chain where the orchestrator makes every mutation — the seed-221 shape —
  reports **zero implementer mutations**, and reports them rather than
  passing them;
- a mixed chain, where one phase is delivered and one is repaired by the
  orchestrator after the implementer under-delivered, splits correctly.

The third case is the one that separates a working detector from a
coin-flip: the first two are satisfiable by a report that always says
"orchestrator" or always says "implementer".

## Acceptance

1. A chain in which the orchestrator makes every mutation is reported as
   **zero implementer mutations**, from retained artifacts alone, with no
   further inference (`BRIEF.md` invariant 1).
2. A chain in which the implementer delivers reports its mutations to the
   implementer, from the same fixture family.
3. A mixed chain attributes each phase to the role that actually changed the
   file.
4. An implementer that **reports** changed files it did not write is recorded
   as claiming them and not having made them. The report states the
   discrepancy; it does not decide what the discrepancy means.
5. A phase whose implementer window carries **no observation at all** — as
   distinct from an observed zero — is reported as unobserved, never as zero.
   This is the 2026-09-08 detached-worker gap in a new place: absent evidence
   and observed absence are different findings, and a `0` that means "we did
   not look" is the failure that gap already produced once.
6. Every count in the report recomputes from the retained ledger, and a test
   recomputes one rather than transcribing it.

## Out of scope

- **Judging whether delegation helped.** The report says who changed what.
  Whether that is better or worse than a continuous session is HP8, and HP8
  is separately authorized.
- **Any new pathology detector.** Zero implementer mutations is a *reported
  fact*, not a verdict, and nothing here classifies a run as pathological.
- **Thresholds of any kind**, including "too few mutations". `BACKLOG.md`
  defers budget verdicts with a recorded reason.
- **Line-level or hunk-level attribution.** Path-level answers the incident.
  If a later question needs finer grain, it arrives with that question.
- **Attributing a mutation to a model turn.** That needs retained worker
  events keyed to turns, which is D6's shape, not this one's.
- **Changing the route's accept-or-reject decision.** Attribution observes;
  it never gates. A chain that passes with zero implementer mutations still
  passes, and the record says both things.
