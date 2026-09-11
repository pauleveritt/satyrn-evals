# TE4 tightening-3 re-verification — result

Run and retained 2026-09-10, under
[the pre-run record](te4-tightening3-reverification-pre-run-record.md).
2 Engine attempts, as authorized. No further inference beyond what
that record authorized.

## Outcome

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns |
|---|---|---|---|---|---|
| Engine-01 | pass | pass (10) | pass | **voided** (timeout) | 65 (6/10/7/42) |
| Engine-02 | pass | pass (29) | pass | **rejected** (11/18) | 56 (6/29/7/14) |

**Phase-2-board holds: 7 of 7 pass since the guardrail** (5 before this
run, now 7). Engine-02's phase 2 took 29 turns — well above the recent
6–10 range — via heavy rewriting (5 wholesale `write app.py` calls, 11
`edit` calls (4 succeeded, 7 returned errors), and rewrites of the
phase-1 templates too) across 4 self-test runs, 2 of them failing
before it converged.

**Corrected 2026-09-10**, after
[the phase-4-guardrail re-verification result](te4-phase4-guardrail-reverification-result.md)
found this line wrong on direct re-check: Engine-02's phase 2 **did**
contain the identical destructive `edit` on the home route (one of its
`edit` calls replaces `home` with `complaints` in a single
`oldText`/`newText` pair, the same pattern named in
[the runaway investigation](phase-2-board-runaway-investigation.md)),
and recovered via a subsequent `write` that restored both routes — the
same self-correcting pattern seen in most other post-guardrail
attempts that pass. "Completed normally, not via the destructive-edit
signature" was wrong; it should have read "the destructive edit
occurred and was self-corrected before the phase ended," which is a
different, weaker claim about what the guardrail achieves. See that
result's own tally: the edit occurs in 5 of 10 post-guardrail
phase-2-board attempts, including this one, and self-corrects in all
but one.

**Tightening 3 worked for what it targeted.** Neither attempt placed
`id` before `agent_name`/`text` this time — that specific mistake did
not recur.

## A new, adjacent problem: tightening 3 didn't require a default

Both attempts wrote `id: int` with **no default value**, positioned
after `agent_name`/`text` but before `timestamp` (which has one).
Python's own dataclass rule requires every field after a defaulted one
to also carry a default; `id` here is a genuinely required argument.
Every downstream requirement built on "2-arg positional construction
still works" now fails a different way:

**Engine-01**: the resulting `models.py` first failed to import at all
(`TypeError: non-default argument 'id' follows default argument
'timestamp'` — the model had originally placed `id` *after*
`timestamp`). It then edited `id` to a valid *position* (before
`timestamp`) but never gave it a default, so the file now imports but
`Complaint("first", "First complaint")` would raise "missing 1
required positional argument: 'id'." This attempt also spent 24
consecutive identical `read app.py` calls mid-phase before finding its
way to that partial fix, then ran out of time at 42 phase-4 turns — a
third distinct behavior pattern, worth naming, not yet seen before.

**Engine-02**: the same `id: int`, no default, positioned before
`timestamp` — syntactically valid this time, so it collected and ran.
But its own phase-3 `POST /complaints` route did not merely fail at
runtime from the `id` gap — **it no longer exists.** A destructive
`edit` (phase-4 tool call index 4) replaced the entire
`create_complaint` handler *and* the `if __name__ == "__main__":`
block with the new resolve route, in one call:

```
oldText: '@app.post("/complaints")\nasync def create_complaint(...)...
          \n\nif __name__ == "__main__":\n    uvicorn.run(...)'
newText: '@app.post("/complaints/{complaint_id}/resolve")\n...'
```

This is the identical mechanism named in
[the phase-2-board runaway investigation](phase-2-board-runaway-investigation.md)
— a destructive `edit` deleting an already-accepted route — recurring
at phase 4, which has no guardrail against it. Of the 7 failing
checks, only 2 (`test_complaint_model_contract_is_preserved`,
`test_complaint_identity_is_stable_and_keyword_only` — both call
`Complaint("first", "First complaint")` directly) trace to the
no-default `id`. The other 5 (both phase-3 `POST /complaints` checks,
plus 3 of the 4 phase-4 route checks, whose own test setup posts a
complaint through that now-missing route) trace to the deleted route.
The three phase-4 checks are overdetermined — they would likely have
failed from the `id` gap too, had the route survived.

**Reading of tightening 3's own wording**: it said `id` goes "after
the existing `agent_name`, `text` and `timestamp` fields" but never
said it needs a default. A model that adds a required field there
satisfies the letter of the instruction and still breaks positional
construction — the same behavioral requirement tightening 3 was
written to protect, reached by a different route. This is not
evidence the tightening was wrong; it's evidence it was incomplete.

## What this does and does not establish

**Does not establish** that Engine can complete this task — 0 of 2 in
this run, 0 of 5 across every Engine attempt on this task family to
date. **Does establish** that tightening 3's specific fix holds (no
recurrence of the before-agent_name placement) and that phase-2-board's
pass rate remains solid (7/7) — see the correction above on what that
does and does not say about the guardrail's mechanism. Surfaces a
second, related prompt gap
(no-default `id`) and a third distinct behavior pattern (24 identical
reads in a row) not previously observed. **Corrected**: this run's
failures are not entirely attributable to the `id`-default gap —
Engine-02 also destroyed its own phase-3 route via the same mechanism
phase 2 needed a guardrail for (above), which accounts for most of its
failing checks; this specific destructive-edit-on-an-existing-route
pattern recurred on a phase with no guardrail against it.

**Corrected 2026-09-11**: this document previously said "Engine-01's
own redirect-trap-style misdiagnosis did not recur" — wrong on two
counts. First, misattribution: the redirect-trap misdiagnosis in
[the guardrail re-verification result](te4-guardrail-reverification-result.md)
belongs to that record's Engine-02, not Engine-01. Second, it did
recur here: Engine-01's own phase-4 self-tests hit the identical
`assert response.status_code == 303` / `assert 200 == 303` failure
twice (its final two self-test runs), with only `read app.py` calls in
between rather than a fix, before the phase timed out — undiagnosed,
not merely absent. See
[the phase-4-guardrail re-verification result](te4-phase4-guardrail-reverification-result.md)'s
own corrected tally, which found this pattern across 6 of 9
phase-4-reaching attempts on this task family.

**No turn ceiling proposed.** Engine has still completed the full task
zero times.

## What happens next — not decided here

A natural **tightening 4** is visible from this evidence: state that
`id` must have an automatic default (an auto-incrementing counter or
equivalent) so it is never required at construction time — closing the
specific gap both attempts fell into. Not applied in this document.
The 24-identical-reads pattern in Engine-01 is also worth its own
offline look, the same way the phase-2-board runaway was, before
deciding whether it is a distinct concern or noise at `n=1`. Neither
is proposed or authorized here. TE4's own two-per-configuration screen
remains unauthorized — Engine has now failed to complete this task
five times in a row, each for a different, progressively narrower
reason, which argues for closing the remaining gap before spending a
screen, not for treating five failures as sufficient information on
their own.
