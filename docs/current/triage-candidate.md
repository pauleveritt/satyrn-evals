# Stage 3.1: the named engine change

This records the candidate the triage screen will test, and the candidates
already closed. Naming a candidate authorizes no spending.

## Closed: whole-attempt duplicate-call retention

**Question asked.** Does retaining duplicate-call history for the whole attempt
reduce eviction-driven cycling and total cost, without disrupting productive
repair and verification?

**Rejected** by the offline recovery guardrail, before any live spending. The
reproducer is retained at
`~/satyrn-smokes/2026-09-08-breaker-window-reproducer/`; it drives the real
`createLoopBreaker` from the pinned engine against a copy whose `WINDOW` alone
is unbounded, with no model and no engine-repo change.

Two findings are kept, both deterministic:

- **The candidate's sparse-repeat regression.** In a sparse repair pattern —
  edit, read back, run the suite, do other work, repeat — the current setting
  admits all 9 read-backs and all 9 test runs with 0 blocks, while
  whole-attempt retention admits 5 and refuses 4 of each. The refusal is
  permanent: `callKey` is `[toolName, canonicalJson(input)]` with no workspace
  version, so a read after an edit is the same key, and a blocked call is never
  pushed to `admitted`, so its count cannot decay. Eviction was the only thing
  that ever removed it. Where the model retries a refusal, consecutive blocks
  reach `CONSECUTIVE_BLOCK_LIMIT` and terminate the turn — 4 terminations
  against 0 today — feeding the restart cycling the change was meant to reduce.
- **The existing dense-repeat limitation.** At high density the current
  `WINDOW=20` already refuses legitimate repeated reads and test runs: 5
  admitted, 4 blocked, identically under both settings. This is a property of
  `THRESHOLD=5` over a 20-call window today, not something the candidate
  introduced. It is recorded because it bounds what any repeat-based lever can
  claim.

The intended effect was real — re-admissions fell from 12 to 5 on the traced
cycling sequence — but it is not separable from the regression by widening
alone.

**Not adopted as corrections.** Versioned keys deserve their own hypothesis: a
global mutation counter could let unrelated edits, or edit-and-revert cycling,
reset protection. A merely larger finite window is not demonstrated lower risk:
it can still block legitimate repeats for the remainder of a bounded attempt,
and eventual eviction does not guarantee timely recovery.

## Named: enlarge the post-edit region

**Question.** Does a larger post-edit region reduce follow-up reads of the
edited file enough to offset its additional tool-result and input tokens, while
preserving repair outcomes?

This is an **efficiency** hypothesis. It predicts no capability improvement.
Tool-result expansion primarily adds model input and context, not output
tokens; the accounting must reflect that rather than assuming output grows.

**The lever.** `src/satyrn_engine/mutation.py` returns a region around a
successful edit, bounded by `REGION_CONTEXT_LINES = 3`,
`REGION_MAX_LINES = 40`, and `REGION_MAX_BYTES = 4_000`. The pair is two
settings of that one engine revision.

**Prior status.** The v14a protocol tested E9's *corrective* half — telling the
model that a change had already been applied — and refuted it. The
*preventive* half, showing a larger region at edit-success time, is a distinct
mechanism its own record flags as untested. This candidate is that half.

## Offline preparation

No live spending is required for any of it.

1. Inspect the traced edits and identify what useful context today's region
   omits. Work from retained transcripts, not from assumption.
2. Choose one concrete larger setting, justified by what step 1 found.
3. Verify the region's content, its truncation behavior, and that responses
   stay bounded.
4. Freeze how follow-up reads and total usage will be counted before any
   comparison.

**Condition.** The task and rung are chosen *after* establishing where this
mechanism actually occurs. The requirement to leave `R3` is not inherited from
the previous candidate: whether post-edit re-reads appear at `R3` is a question
about this mechanism and is answered from evidence, not assumed.
