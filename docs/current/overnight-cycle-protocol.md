# Overnight cycle protocol

Authorized 2026-09-08: engine-repository writes, live budget, and autonomy over
cycle selection after the first. This file is the protocol those cycles run
under, written before the first one.

## The shape of a cycle

1. **Find a candidate offline.** Mine retained evidence for a pathology.
   **Entry gate: a deterministic reproducer.** No reproducer, no candidate —
   a thing that cannot be replayed is an anecdote.
2. **Write the reproducer as a failing test**, in whichever repository owns
   the behaviour.
3. **Smallest remedy that makes it pass**, with a sibling showing it stays
   silent on the healthy case.
4. **Fable reviews the cycle** — the reproducer, the remedy, and whether the
   pathology is real or an artifact of how it was measured.
5. **Record and close.** The next cycle starts clean.

## Stopping rules

- **A cycle closes before the next opens.** V11d opened with six findings and
  reached nine while the run they were for stayed held. A cycle that discovers
  three further things **records them and fixes none of them**.
- **Offline iterates freely; spending does not.** Analysis, authoring and
  re-scoring may loop. Any live batch has frozen conditions written first, is
  one-shot, and is not extended after its result is read.
- **A remedy is allowed ahead of an authorized run only if it blocks that run
  or cannot be re-scored afterwards.** Everything else waits.
- **Machine state is a precondition, not a slice.** Quiet the machine before an
  unattended batch; the one voided probe in this project's history was a GPU
  out-of-memory, and no code fix reaches that.

## What a cycle may and may not conclude

May: that a message, refusal or behaviour is reproducibly wrong, and that a
named remedy makes a named test pass.

May not: that the remedy improves outcomes. That needs a comparison, which
needs its own frozen conditions and its own authorization. **A passing
reproducer is a software fact, not a model-quality claim.**

## Cycle 1, agreed in advance

**Mine the retained Engine transcripts for engine-emitted messages that failed
to redirect the model.**

Chosen because it is the method with a record: the mutator schema rejection,
the loop-breaker post-edit staleness and the post-edit region defect were all
found by reading what the engine says to the model, not by running batches. The
evidence is already on disk — 36 Engine cells from the R1 batch plus earlier
Engine batches — and the work is entirely offline until a candidate has a
reproducer.

Method: extract every engine-originated message (mutator refusals, runner
results, loop-breaker notices), classify what the model did next, and look for
messages with a high rate of *the model repeating the same call*. A message
that leaves the model doing the same thing again is a message that failed.

Recorded hypothesis to test against, from the V14a result: the runner refusal
that worked **named what to do instead**, while E9's corrective message named
**what already happened** and left the next action unspecified.

## Per-cycle record

Each cycle writes one short record: the candidate, its reproducer, the remedy
or the decision not to remedy, Fable's verdict, and what the cycle discovered
but did not fix.
