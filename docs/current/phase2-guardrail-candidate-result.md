# Phase-2-board guardrail candidate — result

Run and retained 2026-09-10, under
[the pre-run record](phase2-guardrail-candidate-pre-run-record.md). 3
Engine attempts, 1 Baseline attempt, as authorized. No further
inference beyond what that record authorized.

## Outcome

| Attempt | Outcome | Turns (whole-attempt) | Phase-2 hidden checks |
|---|---|---|---|
| Baseline-01 | COMPLETE | 17 | 10/10 |
| Engine-01 | COMPLETE | 14 | 10/10 |
| Engine-02 | COMPLETE | 13 | 10/10 |
| Engine-03 | COMPLETE | 16 | 10/10 |

**3 of 3 Engine attempts completed phase-2-board cleanly.** No timeout,
no `check_chain` finding, no runaway write loop. Model identity
confirmed `gemma-4-12B-it-MLX-8bit` on every turn of all four
transcripts.

## The mechanism, not just the count

The investigation's hypothesis was specific: the runaway follows a
destructive `edit` that deletes the phase-1 home route while adding
the phase-2 complaints route. This screen checked the mechanism, not
only the outcome:

- **Engine-01, Engine-03**: wrote `app.py` fresh in one `write` call
  each (no separate `edit` at all) — the same shape as HP7's own clean
  pass.
- **Engine-02**: used `edit app.py`, and did so **additively** — the
  retained diff keeps the existing `home` route (lines 10–11) intact
  and inserts the new `complaints` route after it, the same shape as
  TE2/HP8's own passing Engine-02. This is the one attempt that
  exercised the exact fork the guardrail targets, and it took the safe
  branch.

**Zero destructive edits occurred across all three Engine attempts.**
This is stronger evidence than the raw pass count alone: it is not
merely "3 attempts happened to finish," it is "the specific behavior
hypothesized to cause the runaway did not occur, in the one case that
reached the decision point at all."

## What this does and does not establish

**Does not establish, at this `n`:** that the guardrail eliminates the
runaway with high confidence. Against the 50% base rate named in the
pre-run record, 3 of 3 passing has probability 0.125 under the
null hypothesis that the guardrail changes nothing — not below any
conventional significance threshold, and this screen was explicitly
not designed to reach one (TE3/TE5-style confirmation design was
deliberately not invoked). A fourth or fifth attempt could still run
away; this screen doesn't rule that out.

**Does establish:** the specific failure mechanism the investigation
named (destructive whole-block edit) did not recur in three
opportunities, once in a case that reached the exact decision point.
Combined with the mechanistic read, this is more informative than the
raw 3/3 vs. 2/4 pass-rate comparison on its own, though neither alone
is conclusive.

**Does not establish, and is not claimed:** anything about Baseline
vs. Engine turn efficiency or completion reliability — this screen's
observations stay outside every TE confirmation denominator, per the
pre-run record's own scope, and outside TE4's screen specifically.

## What happens next — not decided here

This result is favorable enough to be worth a decision, not favorable
enough to make one automatically. Per the pre-run record and the TE
plan's Repair Ownership rule, adopting the guardrail into either
accepted task's own frozen prompt (`agentclinic-session-phased`,
`agentclinic-complaint-lifecycle`) would be a treatment amendment, not
an instrument fix — it needs its own explicit proposal and separate
authorization, regardless of how favorable this screen looks. This
document does not propose that amendment; it reports what the probe
found.
