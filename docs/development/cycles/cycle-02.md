# Cycle 2: do cycle 1's numbers describe the shipping breaker?

Run 2026-09-09, offline, no inference. Question forced by cycle 1's correction:
the mined batches ran `engine.ts` at `25ca0be` (digest `2e4fc064…`), and the
shipping breaker is `fc22622` (`c3ec10eb…`), which keys the workspace revision
into a call.

> **Correction, 2026-09-09.** This first said **every** mined batch ran
> `25ca0be`. The 2026-09-08 R1 batch ran `fc22622`
> (`…-r1-201314/screen/preflight.json`) — and it recorded **zero** loop-breaker
> refusals, which is itself the more useful fact: the shipping breaker has no
> observed firing in the retained evidence at all.

## Method, and why it is not a whole-run replay

A whole-run replay would be **invalid**. The breaker decides which calls
execute, so the recorded call sequence is endogenous to the breaker that
produced it; after the first differing decision, the remaining transcript is
not a sequence the new breaker would ever have seen. A first attempt did replay
whole runs and produced **1,373 refusals against 532 recorded** — more
refusals from the breaker built to issue fewer, which is the signature of a
counterfactual mistaken for a measurement.

This replays in lockstep and **stops each cell at the first divergence**, so
every decision counted is one both breakers actually faced. `noteChange` is fed
from accepted edit results exactly as `registerLoopBreaker` feeds it.

## Result

| | |
|---|---|
| cells scanned | 236 |
| cells recording a refusal | 98 |
| decisions compared before divergence | 4,257 |
| recorded refusals inside those prefixes | **328** |
| the shipping breaker agrees (still refuses) | **275 (84%)** |
| cells diverging at all | **60 of 236** |
| first divergence: shipping **admits** what was refused | **53** |
| first divergence: shipping refuses what was admitted | 7 |

## What it means

**The fix works in the expected direction.** Revision keying admits a
wrongly-refused call in 53 of the 60 diverging cells — consistent with cycle 1's
finding that 195 of 532 refusals were stale. On the decisions both breakers
faced, **84% of recorded refusals are still refused**.

> **Correction, 2026-09-09.** This first concluded that the pathology "largely
> survives" and that the breaker "still refuses at this volume". Neither
> follows, and both contradict this section's own caveat. **A prefix agreement
> rate cannot establish present-day prevalence**, because the prefixes end at
> the first divergence and the model's subsequent behaviour is unobserved.
> What the number supports is narrow: *where both breakers saw the same call,
> they mostly agreed*. Present-day volume is unmeasured, and the only batches
> on the shipping breaker recorded zero refusals.

## Limits, stated

- Counts cover **pre-divergence prefixes only** — 4,257 of the decisions in
  these transcripts, not all of them. The divergence count is therefore a
  **lower bound**, and the 84% is an agreement rate on a prefix, not a
  whole-run refusal rate.
- Nothing here measures what the model *would have done* with the shipping
  breaker. That needs a live run, and no such run has been authorized or
  budgeted for this question.

## Cycle verdict

**No engine change.** Cycle 1's line of inquiry stays open rather than
retiring: refusals survive, so the discriminator cycle 1 named — telling a call
refused while the turn progresses from one refused while it is stuck — is now
justified by evidence rather than assumed. That is the next cycle.

## Discovered and not fixed

1. **A whole-run replay is an invalid instrument here**, and nothing in the
   repository said so. Worth a lessons entry: an intervention that changes
   which events occur cannot be evaluated by replaying events recorded under a
   different intervention.
2. Two shape errors cost a full wrong answer before this one: `loop_broken`
   lives at `entry.customType`, not `entry.kind`, and a refused call **does**
   receive a `tool_execution_end` carrying the refusal as its result. Both are
   now encoded in the replay script.
