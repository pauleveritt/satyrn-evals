# Cycle 3: a discriminator, and a trade smaller than first claimed

Run 2026-09-09, offline. Engine commit `83ae0f9`, corrected after review.

## The discriminator

Cycle 1's remedy failed because it fired on cells whose pass-rate was ordinary.
The question it left: can *refused while stuck* be told from *refused while
progressing*, using only what the breaker holds at decision time?

A first attempt classified a refusal by whether an accepted edit **followed**
it. That is look-ahead and unusable — the breaker cannot see the future. Rebuilt
backward-looking, over 236 retained Engine transcripts:

| at the moment of refusal | refusals | eventual pass-rate |
|---|---|---|
| no accepted edit yet | 103 | **0.09** (80 produced nothing) |
| 1–2 accepted | 100 | 0.74 |
| 3 or more | 329 | 0.42 |

That is a genuine separation, and `acceptedEdits` is already available where the
decision is made.

## The remedy, and its real size

Shipped as **opt-in, off by default** — `SATYRN_BREAKER_REQUIRE_PROGRESS=1` —
because a rule that ends turns changes what can be observed.

**The trade was first stated as "76% of the produced-nothing population against
3% of the passes". That describes the population, not the margin.** Review
recomputed the margin, and it is much smaller: of the 26 produced-nothing cells,
**22 were already ended two calls later** by the existing
`CONSECUTIVE_BLOCK_LIMIT`. The rule's incremental saving is:

- **4 cells and 162 calls** — 149 of them a single timed-out cell —
- against **5 passes** that did **65 calls of real repair** after the trigger.

On that accounting the rule is close to break-even, and it stays off.

**And it has never fired on the instrument it ships in.** The only batches on
the shipping breaker `fc22622` recorded **zero** refusals, so every number above
comes from earlier breakers.

## Corrections this cycle produced

1. **Cycle 2's record is wrong** that every mined batch ran `25ca0be`: the
   2026-09-08 R1 batch ran `fc22622`. Corrected there.
2. **The shipped-suite gate's pinned test count was already stale.** It asserted
   `pass 33` while cycles 1 and 2 had taken the suite to 34, and nobody saw it
   because the integration tier is not in CI and the protocol did not require
   running it. The protocol now does.
3. **The preflight fix of 2026-09-09 was in the wrong place.** Its declaration
   sat inside the `else` branch it was meant to guard against, so it was dead
   for the no-engine case and the `${VAR:-}` default was doing the work while
   the comment claimed otherwise. Moved to the branch that runs.
4. **`acceptedEdits` scope overpromises in its name**: it is per-registration,
   not per-turn, and counts only Satyrn-mutator edits — so with the flag on in a
   plain Pi session, every refusal terminates. Now stated at the definition.

## Discovered and not fixed

- The rule has no reachable trigger on current evidence. Whether it should ever
  be enabled cannot be settled from retained transcripts; it needs a batch on
  the shipping breaker that actually breaks a loop.
- 25 of the 26 produced-nothing cells are `NO_PATCH` on `read,edit`-only
  surfaces from v13c/v13d. The population the rule targets may be an artifact of
  a tool surface that has since changed.

## Cycle verdict

**Ship the rule off, and do not cite the 76%/3% framing.** The discriminator is
real; the remedy built on it is marginal against the limit already in place, and
untested on the current breaker.
