# TE4 phase-4-guardrail re-verification, round 2 — result

Run and retained 2026-09-11, under
[the pre-run record](te4-phase4-guardrail-reverification-round2-pre-run-record.md).
2 Engine attempts, under the maintainer's standing overnight
authorization ("free use of the GPU... keep working through TE").

**Corrected 2026-09-11**, after independent review: the completion
counts, turn counts, tool-call indices, and hidden-grader results below
all held up unchanged. Two interpretive claims did not and are fixed in
place — "both attempts restored the route before self-test ever ran"
was true only for Engine-02, and "the first time this self-correction
pattern has been observed at phase 4" was wrong (it recurred at least
twice before, in attempts that restored the route and still failed).
Both corrections weaken, not strengthen, what this result can claim.

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

## Both attempts made the same destructive edit the guardrail exists to stop, and both restored the route — but restoring it is not new, and is not what distinguishes these from the failures

This is not a case of the guardrail preventing the edit. In both
attempts, phase 4's routes are added by first replacing the entire
`POST /complaints` (`create_complaint`/`post_complaint`) handler with
the new resolve route in a single `oldText`/`newText` edit — the
identical mechanism named throughout this sequence, occurring despite
the guardrail's preservation bullet being present and unchanged.

**Engine-01** (tool call 4 of 20 in phase 4): the destructive edit
removes `create_complaint` entirely. **Corrected**: the first draft of
this document claimed the route was restored "before self-test ever
ran" — wrong for this attempt. A `run_self_test` call happens at call
8, *between* the deletion (call 4) and the restoration (call 13), and
its failure (`assert 200 == 303`, twice) is followed immediately by a
`read app.py` (call 10) and a failed edit attempting to match the
already-deleted block (call 11) before the successful restoration at
call 13. The transcript has no non-empty assistant reasoning text in
phase 4 to confirm what prompted the re-read, so this document cannot
claim the correction was unprompted by self-test feedback — only that
it is consistent with either explanation. Call 13's `newText` reinserts
`@app.post("/complaints")` / `create_complaint` in an additive
position, right after `GET /complaints`. The model separately debugs
an unrelated `TestClient(app, use_client_redirects=True)` `TypeError`
in its own test file (calls 14–18 pass; call 16 hits the invalid
kwarg, call 18 corrects it to `follow_redirects`), and the final
self-test (call 19) exits 0.

**Engine-02** (tool call 6 of 27 in phase 4): the destructive edit
removes `post_complaint` entirely, replacing it with the resolve and
reopen routes together. Fourteen consecutive `read app.py` calls
follow (calls 7–20, corrected from the first draft's "thirteen") — the
same "many identical/near-identical reads in a row" pattern named once
before, in tightening-3's Engine-01, but without run-away consequences
here. Tool call 21 then submits a whole-file `edit` whose `newText`
reinserts `post_complaint` in an additive position between
`GET /complaints` and the resolve route. This one genuinely happens
before any self-test: the phase's only `run_self_test` call is at 26,
after the restoration, and it passes immediately.

**Corrected: restoring the deleted route via a targeted `edit` is not
new, and did not previously lead to completion.** The first draft
claimed this was "the first time this self-correction pattern has been
observed at phase 4 at all." Checked directly against every retained
phase-4 transcript, it is not: the guardrail re-verification's
Engine-02 destroys the route at its own call 5 and restores it via a
targeted `edit` at call 8; tightening-4's Engine-01 destroys it at call
7 and restores it via a targeted `edit` at call 10; tightening-3's
Engine-01 destroys it at call 3 and restores it via a `write` at call
31 (already on record in
[that result](te4-tightening3-reverification-result.md)). **All three
restored the route and still failed** — all three voided by the 600s
timeout (20, 24, and 41 phase-4 tool calls respectively), not by a
graded rejection. Neither prior document recorded the first two of
these as instances of this pattern; the guardrail re-verification
result even describes its own Engine-02 as "not the
destructive-edit-and-repeat signature," which this correction also
flags as wrong.

**Read together with round 1**: across all 4 phase-4-guardrail-era
attempts that reached phase 4 (round 1's Engine-01 and Engine-03,
round 2's Engine-01 and Engine-02), the destructive edit occurred in
**3 of 4** — round 1's Engine-01 is the only one that never deleted the
route (though one of its own edits does rewrite the handler body while
keeping the route name, short of a clean "purely additive" description).
That is not lower than the pre-guardrail rate. **What actually
distinguishes round 2's two completions from the three prior
restore-then-fail attempts is not the restoration itself — it is that
both finished within the time/turn budget after restoring and
resolving their own self-test issues, where the three priors did not.**
Four data points on the destructive-edit-then-restore pattern (this
round's two, plus the two priors just found, not counting
tightening-3's write-based one) is nowhere near enough to say why two
finished in time and two didn't — turn-budget luck is at least as
plausible an explanation as anything about the guardrail or the model's
skill at self-correction.

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
either attempt's behavior at the moment of writing app.py. **Corrected**:
the first draft framed "does the model notice and fix it before
running out of turns" as newly-observed evidence this round. It is
not new — three prior attempts (guardrail re-verification's Engine-02,
tightening-4's Engine-01, tightening-3's Engine-01) also restored the
deleted route and still failed, all by timing out. What is different
about these two attempts is only that they finished within budget
afterward; this document has no evidence for why, and turn-budget
variance is as plausible an account as anything about the model
reliably self-correcting.

**No turn ceiling proposed yet.** Two completions (43, 49) is a
starting point, not a distribution — TE1's own Baseline ceiling
(15–25 range, 40 chosen as ~1.5x the observed max) needed six
transcripts before being set with any confidence.

## Next, per the standing instruction

Independent review has now run and its two substantive findings are
folded in above. What survives: two genuine, fully-passing completions
for the first time on this task family, and no defensible account of
why these two finished within budget when three earlier attempts did
the same restoration and still timed out. That gap — not a guardrail
story, not a self-correction-skill story — is the honest open question.
The task family's cumulative record (2 of 13, no completion before
round 2 of the phase-4-guardrail sequence) is still far too thin for a
turn ceiling or a completion-rate claim. The next useful step is more
attempts at this same configuration (no further prompt change) to see
whether completions recur at all, rather than a fifth tightening or
guardrail aimed at a mechanism (self-correction speed) nothing in the
prompt currently addresses.
