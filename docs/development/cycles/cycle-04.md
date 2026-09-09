# Cycle 4: the loop no consecutive rule can see

Run 2026-09-09, offline. Taken because block-and-readmit proved unreachable —
the shipping breaker has never fired in retained evidence — and this session's
transcript was already on disk.

## What session 11 was doing

194 tool calls, 188 of them `bash`, drawn from **22 distinct calls**. Three
near-identical probes account for **173 of the 194**:

```
python3 -c "... from textkit import summarize; print(summarize(...))"      59x
python3 -c "... from textkit import summarize; print(len(summarize(...)))" 58x
python3 -c "... from textkit import summarize; print(repr(summarize(...)))" 56x
```

Cycled A-B-C-A-B-C, so its **longest identical-consecutive run is 1** while
**89% of its calls repeat something already tried**. It burned the whole 600 s
step timeout, and the consecutive tripwire built in the previous session is
blind to it by construction.

## The remedy

`SessionWindowTripwire` — counts occurrences of a key inside a sliding window,
the way the engine's own breaker does rather than the way the attempt path's
does. Over the twelve sessions, most occurrences of one key in a 20-call window:

| | max in window |
|---|---|
| step timeouts | 6, 9, **20**, **20** |
| everything else | 2, 4, 5, 5, 5, 5, 6, 6 |

A limit of **7** catches three of the four timeouts — including the rotating
one — and fires on **none** of the eight sessions that did not time out.

## The margin is thin, and that is the finding

The nearest healthy session sits at **6** against a limit of 7: a margin of one
call. The engine's consecutive breaker was adopted against a gap of **5 versus
280**. This is not that. A session that legitimately re-runs one test command
seven times in twenty calls would be ended by it.

So the wire ships with a **caller-chosen limit and no default caller**, and the
replay pins all three directions: the three it catches, the eight it spares, and
**session 03, which it cannot reach** — that one peaks at 6, the same value two
healthy sessions reach, so no limit separates it.

## Discovered and not fixed

1. **Two detectors now exist for one job.** Consecutive reaches sessions 2 and
   5; window reaches 2, 5 and 11. The window wire strictly dominates on this
   evidence, which is an argument for retiring the consecutive one — but on
   twelve sessions that is not yet a decision.
2. **Session 03 is a third pathology**: 49 calls, no run above 4, no key above
   6 in a window, and still a timeout. Neither wire reaches it and nothing
   characterises it yet.
3. Neither wire is wired into the session driver. They are detectors with
   replay evidence, not an enforced rule; enabling one is a condition a batch
   declares.
