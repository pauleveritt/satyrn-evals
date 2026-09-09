# Cycle 1: engine messages that fail to redirect the model

Run 2026-09-08 under `docs/current/overnight-cycle-protocol.md`. Entirely
offline; no inference, no spending.

## Candidate found

Mined 236 retained Engine-cell transcripts, pairing every `tool_execution_end`
with the call that produced it and asking what the model did **next**.

| engine message | calls | next call identical |
|---|---|---|
| loop breaker, "already appeared… will not change the result" | **532** | **174 (33%)** |
| mutator schema, "must not have additional properties" | 969 | 99% |
| `NO_CHANGE_REQUESTED` | 55 | 25% |

The schema refusals are **pre-fix history** — they appear only in v11c and v13,
and were remedied in engine `b977941`. `NO_CHANGE_REQUESTED` survives
measurement poorly: 65% of the time the model does the sensible thing and
re-reads the file.

The loop breaker was the candidate: 532 firings across 13 batches, a 33%
immediate re-send, present in current engine code.

## What the mechanism turned out to be

Not a message problem. The refusal already says "take a different concrete
action", and V14a has already shown that improving a refusal's wording does not
move the re-send fraction (57% against a 53% reference). The mechanism is that
the turn terminates after `CONSECUTIVE_BLOCK_LIMIT` **consecutive** blocks, and
`consecutiveBlocks` resets on **any** admitted call — so one different call
between re-sends keeps the turn alive indefinitely. The breaker tracks
`blockedSoFar` per key and does not use it.

Measured: in **49 of the 100** cells that broke a loop at all, one key was
blocked more than three times. One cell blocked the same key **30 times**.

## The remedy, written and then refuted

Terminate on the per-key count the breaker already keeps. A reproducer was
written, it failed as predicted, and the change made it pass.

It also broke two existing tests — "an admitted call resets the consecutive
blocked-call termination count" and its fail-open sibling — which pin the
behaviour deliberately. Checking the evidence rather than the tests:

> Of the 49 cells that block one key more than three times, **27 passed** and
> 17 failed.

**The remedy would have terminated 27 successful attempts.** A model that
re-sends one call while otherwise making progress is not in a loop worth
killing, and the two tests are load-bearing. The change is reverted.

## What landed

One characterization test in `tests/test_loop_breaker.mjs`, pinning that a
repeatedly refused call does **not** terminate a progressing turn, and carrying
the measurement — so the next reader who notices `blockedSoFar` reaching 30
finds the evidence instead of repeating the cycle. 34 tests pass.

## Discovered and deliberately not fixed

Per the protocol, a cycle records what it finds and fixes none of it:

1. **A discriminator is missing.** A call refused many times while the turn
   makes *no other progress* is a different thing from one refused while the
   turn advances, and neither `consecutiveBlocks` nor `blockedSoFar` separates
   them. That is the shape a real remedy would need.
2. **`NO_CHANGE_REQUESTED` is emitted at all.** 55 occurrences of an edit whose
   `old_text` equals its `new_text`. Refusing it is right; the model producing
   it is a separate question.
3. **My batch-level counting inflated by ~10x on the first pass** — 466 raw
   string matches against 47 actual refusals — the streaming-duplication trap
   already recorded twice in `docs/development/lessons.md`. It was caught by
   re-counting per call, and it is the third appearance today.

## Cycle verdict

**No engine change.** The pathology is real and the obvious remedy is worse
than the disease. The cycle's product is the measurement, the characterization
test, and a sharper statement of what a remedy would have to do.
