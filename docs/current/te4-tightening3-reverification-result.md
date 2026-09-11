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

**Phase-2-board holds: 7 of 7 clean since the guardrail** (5 before
this run, now 7). Engine-02's phase 2 took 29 turns — well above the
recent 6–10 range — but completed normally, through repeated
`run_self_test`-driven repair cycles, not the destructive-edit
signature; a real cost outlier, not a pathology recurrence.

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
`timestamp` — syntactically valid this time, so it collected and ran,
but `Complaint(agent_name=agent_name, text=text)` (phase 3's own
add-complaint route, unmodified from an already-accepted checkpoint)
now fails at runtime for the same reason. That's why this attempt's
failures aren't confined to phase 4: `test_complaint_model_contract_is_preserved`
(check 9, phase 2's own) and both of phase 3's `POST /complaints`
checks fail too, alongside the four phase-4 checks that depend on the
same construction. 7 of 18 checks fail in total.

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
recurrence of the before-agent_name placement) and that phase-2-board
remains solid (7/7). Surfaces a second, related prompt gap
(no-default `id`) and a third distinct behavior pattern (24 identical
reads in a row) not previously observed. Engine-02's own redirect-trap
misdiagnosis (named in the prior re-verification) did not recur here —
this run's failures are entirely attributable to the `id`-default gap.

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
