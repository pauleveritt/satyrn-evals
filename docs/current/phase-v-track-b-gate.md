# Phase V — Track B gate

Every inventory claim carries exactly one final status, and no carrier lags its source. The table below is the enumerated inventory — a status for every entry — that Track B opens on.

| claim_id | level | status | gap_kind | gap |
|---|---|---|---|---|
| u-baseline-01-per-phase-turns | unit | confirmed | — | — |
| u-baseline-02-per-phase-turns | unit | confirmed | — | — |
| u-engine-01-per-phase-turns | unit | confirmed | — | — |
| u-engine-02-per-phase-turns | unit | confirmed | — | — |
| u-completion-turn-distribution | unit | confirmed | — | — |
| u-recurrence-01-per-phase-turns | unit | confirmed | — | — |
| u-recurrence-03-per-phase-turns | unit | confirmed | — | — |
| c-engine-population | claim | not_derivable | unimplemented_measure | a measure that binds the population statement to an attempt set |
| c-baseline-3-of-3 | claim | not_derivable | absent_artifact | matched-repeat Baseline attempts under the final prompt |
| c-contemporaneous-screen-tie-2-of-2 | claim | not_derivable | unimplemented_measure | an outcome measure executable from transcripts |
| c-completion-6-of-18 | claim | not_derivable | absent_artifact | hidden-grader verdicts across all 18 Engine attempts |
| c-completion-4-of-16 | claim | not_derivable | absent_artifact | hidden-grader verdicts for the 16 pre-screen attempts |
| c-destroyed-13-of-15 | claim | claim_measure_mismatch | — | — |
| c-restored-9-of-15 | claim | claim_measure_mismatch | — | — |
| c-redirect-fixed-1-of-9 | claim | not_derivable | unimplemented_measure | a redirect-trap resolution classifier |
| c-nonrestore-0-of-6 | claim | not_derivable | absent_artifact | a completion verdict per non-restoring attempt |
| c-restore-4-of-7 | claim | not_derivable | absent_artifact | a completion verdict per restoring attempt |
| c-phase4-denominator-6-of-10 | claim | not_derivable | absent_artifact | prompt-state membership for the pre-phase-4 chains |
| c-redirect-6-of-9 | claim | not_derivable | unimplemented_measure | a redirect-trap occurrence classifier |
| c-fabricated-report-n1 | claim | confirmed | — | — |

**Status:** 8 confirmed, 0 corrected, 10 not_derivable, 2 claim_measure_mismatch, of 20 records.

**Carrier lag:** none.

<!-- hand-written below; do not regenerate -->

## Reopen decisions

One decision per `claim_measure_mismatch` record, per the bound in
`phase-v-design.md`'s Governance: at most one reopen per claim per
reconciliation. A `confirmed` or `not_derivable` record reopens nothing, so the
other 18 records leave every recorded phase decision standing. Neither record
below carries a carrier in this repository, so no reopen owes a carrier update
here.

- **`c-destroyed-13-of-15` — not reopened.** Recorded decision it supported:
  TE6's attribution of destructive-edit-then-restore as a characterized Engine
  failure mechanism (`te6-explain-and-decide.md`, `## Attribution`). The
  committed `destructive_edit` classifier is transcript-level and finds 15 of
  15 — broader, and in the same direction — so the attribution loses no support.
  The record's `claim_measure_mismatch` status is final.
- **`c-restored-9-of-15` — reopened, once.** Recorded decision it supported:
  TE6's trace-backed reading that the pattern is "mostly, but not purely,
  productive recovery" (`te6-explain-and-decide.md`, `## Trace-backed
  examples`), which cites exactly "9 were restored before the phase ended and 6
  of those 9 completed." That derivation is ad hoc (cause 1) and the committed
  `restoration` classifier returns 3 of 15 under a different operation, so the
  reading may not be cited again until a narrowed classifier or a restated claim
  exists. The reopen publishes this corrected record and authorizes no live
  spending; it spends the bound's single reopen for this claim in this
  reconciliation. TE6's Claim-2 decision is unaffected — it rests on the screen
  tie and the per-phase turns, not on this count.

## Carrier review

`quote_drift` lists carriers whose text no longer contains the record's fixed
quote. A review list, not a failure: a legitimate carrier may paraphrase. Six
entries, none passed silently — five carry the figure without its literal
string, and one is a hard line wrap rather than drift.

| claim_id | carrier | reading |
|---|---|---|
| u-baseline-01-per-phase-turns | ROADMAP.md:289 | "(43, 32 turns)" carries 43 without the per-phase breakdown — paraphrase. |
| u-baseline-02-per-phase-turns | ROADMAP.md:289 | the same sentence carries 32 without the per-phase breakdown — paraphrase. |
| c-baseline-3-of-3 | ROADMAP.md:292 | "Baseline is 3 of 3" carries the figure, reworded. |
| c-fabricated-report-n1 | ROADMAP.md:282 | "fabricated an invented '2 passed' pytest transcript" — the same finding, reworded. |
| c-fabricated-report-n1 | docs/current/te4-screen-result.md:20 | "fabricates a fully invented passing pytest output" — the same finding, reworded. |
| c-nonrestore-0-of-6 | ROADMAP.md:272 | the figure is split by a hard line wrap — "(0" / "of 6 non-restorations pass)" — so it is present, not drifted. |

**Written by hand, not generated.** `scripts/publish_gate.py` writes the
inventory table and the carrier-lag line above; `## Reopen decisions` and this
section — the drift list is `quote_drift()`'s output read by hand — are V3's
recorded decisions, preserved automatically below the marker above on
regeneration.
