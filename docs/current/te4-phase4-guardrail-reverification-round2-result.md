# TE4 phase-4-guardrail re-verification, round 2 — result

Run and retained 2026-09-11, under
[the pre-run record](te4-phase4-guardrail-reverification-round2-pre-run-record.md).
2 Engine attempts, under the maintainer's standing overnight
authorization ("free use of the GPU... keep working through TE").

## Outcome — the first two full completions ever on this task family

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns | Hidden checks |
|---|---|---|---|---|---|---|
| Engine-01 | pass (6) | pass (8) | pass (8) | **pass** | 43 (6/8/8/21) | 18/18 |
| Engine-02 | pass (6) | pass (8) | pass (7) | **pass** | 49 (6/8/7/28) | 18/18 |

Both attempts completed all four phases and passed every hidden check
(18/18 each — `id`-field design, preservation, status badges, ordering,
resolve/reopen behavior, all correct). Model identity verified from
each transcript (`gemma-4-12B-it-MLX-8bit`). Zero `check_chain`
findings on either. **This is the first time any Engine attempt on
this task family has completed the full task**, after 11 prior
attempts (0 of 11) across the route proof, the phase-2 guardrail's
re-verification, both `id`-field tightenings, the completion-rate
check, and round 1 of this same phase-4-guardrail re-verification.

## Both attempts made the same destructive edit the guardrail exists to stop — and both caught it themselves, before self-test

This is not a case of the guardrail preventing the edit. In both
attempts, phase 4's routes are added by first replacing the entire
`POST /complaints` (`create_complaint`/`post_complaint`) handler with
the new resolve route in a single `oldText`/`newText` edit — the
identical mechanism named throughout this sequence, occurring despite
the guardrail's preservation bullet being present and unchanged.

**Engine-01** (tool call 4 of 20 in phase 4): the destructive edit
removes `create_complaint` entirely. Two further edits are inert
(`oldText == newText`, no actual change). Tool call 13 then rewrites a
larger block of `app.py`, and its `newText` reinserts
`@app.post("/complaints")` / `create_complaint` in an additive
position, right after the `GET /complaints` route — the same place the
guardrail's own instruction describes. This happens *before* any
`run_self_test` call resolves the question either way; the model's own
self-tests (calls 8, 14, 16, 19) show it separately debugging an
unrelated `TestClient(app, use_client_redirects=True)` `TypeError` (it
tried an invalid kwarg name for exactly the redirect-following problem
this sequence has repeatedly named, then presumably corrected it by
the final self-test, which exits 0).

**Engine-02** (tool call 6 of 27 in phase 4): the destructive edit
removes `post_complaint` entirely, replacing it with the resolve and
reopen routes together. Thirteen consecutive `read app.py` calls
follow (calls 7–20) — the same "many identical/near-identical reads in
a row" pattern named once before, in tightening-3's Engine-01, but
without run-away consequences here. Tool call 21 then submits a
whole-file `edit` whose `newText` reinserts `post_complaint` in an
additive position between `GET /complaints` and the resolve route.
Only one `run_self_test` call happens in this whole phase (call 26,
after the restoration), and it passes on the first try.

**Read together with round 1**: across all 4 phase-4-guardrail-era
attempts that reached phase 4 (round 1's Engine-01 and Engine-03,
round 2's Engine-01 and Engine-02), the destructive edit occurred in
**3 of 4** — round 1's Engine-01 is the only one that added the routes
purely additively from the start. That is not lower than the
pre-guardrail rate (3 of 4 graded attempts, per
[the tightening-4 result](te4-tightening4-reverification-result.md)).
**What changed is not whether the edit happens, but what happens
after it**: in round 1's one occurrence it was never undone; in both
of round 2's occurrences the model caught and reversed its own mistake
before self-test ever ran, restoring the missing route in an additive
position consistent with the guardrail's own wording. Four data points
is not enough to call this a reliable behavior the guardrail causes —
it could just as easily be attempt-to-attempt variance in whether the
model happens to re-read and reconcile its own work before finishing.
It is, however, the first time this self-correction pattern has been
observed at phase 4 at all (phase 2's runaway self-corrections were
always via a full `write` rewrite, never a targeted `edit`).

## What this does and does not establish

**Establishes, for the first time on this task family**: Engine can
complete the full 4-phase task, including a correct `id`-field design
and a correctly preserved route set, within the declared turn budget
(43 and 49 whole-attempt turns — both above HP7's easy-roadmap 22 and
Baseline's easy-roadmap range 15–25, but this is a harder, 4-phase
roadmap with no completed comparison point yet on this exact task).

**Does not establish**: a completion rate. 2 of 2 in this small batch
is not evidence of a reliable rate — it follows one round with 0 of 3,
and the task family's cumulative record is now **2 of 13** (0 of 11
before this round). It also does not establish that the phase-4
guardrail is responsible: the destructive edit still happened in both
attempts; nothing about the guardrail's own text visibly changed
either attempt's behavior at the moment of writing app.py. The honest
account is that phase 4's real recurring risk is not "does the model
delete the route" (it does, at about the same rate with or without the
guardrail) but "does the model notice and fix it before running out of
turns or handing back" — and this round is the first evidence that it
sometimes does, unprompted by any guardrail wording addressing
recovery specifically.

**No turn ceiling proposed yet.** Two completions (43, 49) is a
starting point, not a distribution — TE1's own Baseline ceiling
(15–25 range, 40 chosen as ~1.5x the observed max) needed six
transcripts before being set with any confidence.

## Next, per the standing instruction

Getting an independent review of this result, consistent with every
prior stage in this sequence and especially warranted here: this is
the first positive result in the sequence, the highest-stakes place
for optimistic misreading to slip in unchecked, given every prior
result in this sequence needed at least one correction after review.
