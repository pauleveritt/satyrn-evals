# TE4 tightening-4 re-verification — result

Run and retained 2026-09-10, under
[the pre-run record](te4-tightening4-reverification-pre-run-record.md).
2 Engine attempts, under the maintainer's standing overnight
authorization ("free use of the GPU... keep working through TE").

## Outcome

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns |
|---|---|---|---|---|---|
| Engine-01 | pass | pass (8) | pass | **voided** (timeout) | 46 (6/8/7/25) |
| Engine-02 | pass | pass (8) | pass | **rejected** (13/18) | 41 (6/8/8/19) |

**Phase-2-board holds: 9 of 9 clean since the guardrail.** Neither
attempt reproduced any prior `id`-field mistake.

## Tightenings 3 and 4 both validated

**Engine-02's `models.py`** is exactly the intended pattern:

```python
id: int = field(default_factory=lambda: next(_id_gen))
```

Positioned after `agent_name`/`text`, with a real automatic default.
Every check that depends on the `id` contract —
`test_complaint_model_contract_is_preserved`,
`test_complaint_identity_is_stable_and_keyword_only`,
`test_seed_complaints_have_distinct_ids` — **passed**. Across six
Engine attempts on this task's phase 4, this is the first to get the
`id` design entirely right. Both tightenings did what they were meant
to do.

## The remaining failures are a different kind of problem

**Engine-01: a genuine implementation bug**, not a prompt gap. It
wrote:

```python
id: int = field(default=None, init=False)
status: str = "open"

_id_counter = 1

def __post_init__(self):
    if self.id is None:
        global _id_counter
        self.id = _id_counter
        _id_counter += 1
```

`__post_init__` is written at **module level, not indented into the
class** — it is never called, so `id` stays `None` forever. This is a
real Python mistake (a deferred-assignment pattern, reasonably
conceived, incorrectly nested) that self-test correctly caught
(`AssertionError` comparing complaint counts, later a `422` from a
mismatched test) — the implementer then spent the rest of the phase
making increasingly tangled edits, including writing a
self-acknowledged nonsensical assertion in its own test
(`assert len(complaints) == len(complaints) + 1  # This is wrong, but
let's check logic`), without ever finding the actual bug, and ran out
of time at 25 phase-4 turns.

**Engine-02: a genuine preservation regression**, not a prompt gap.
Its `id` design is correct, but its rewritten `app.py` **omits the
`POST /complaints` route** — the add-complaint route from the
already-accepted phase 3 checkpoint. That single omission cascades:
`test_post_complaint_redirects_to_complaints_board` and
`test_posted_complaint_appears_on_complaints_board` (phase 3's own
checks) fail because the route no longer exists, and this task's own
phase-4 checks that post a fresh complaint before resolving it
(`test_resolve_route_marks_complaint_resolved_and_redirects`, etc.)
fail too, because their own setup depends on that same missing route.
5 of 18 checks fail, all traceable to one dropped route.

## Why these are not candidates for a fifth tightening

Both failures are exactly the kind of difficulty
[the TE4 design](te4-harder-roadmap-design.md) says this roadmap
should have: "difficulty should come from meaningful dependencies and
preservation, not misleading instructions." A misplaced
`__post_init__` is an implementation mistake self-test is supposed to
catch (and did); a dropped route from an earlier phase is exactly the
cumulative-preservation failure mode this whole task family exists to
detect (and did, here through the ordinary hidden checks, not a new
mechanism). Tightening the prompt further to prevent these specific
mistakes would not close an ambiguity — it would start writing the
solution for the model. **No fifth tightening is proposed.**

## Where this leaves the id-field question

Tightenings 3 and 4 are done. Engine-02 proves the corrected
instruction is sufficient to reach a fully-correct `Complaint` design
in at least one live attempt. The `id`-field ambiguity that caused
three of the first four phase-4 failures on this task is closed.

## What this does and does not establish

**Still 0 of 6** full completions across every Engine attempt on this
task family. But the *reason* has moved: the first four failures
traced to one narrow, now-closed prompt gap; these two trace to
ordinary implementation variance (a bug, a regression) — the kind of
outcome variance any nontrivial coding task produces, not a
systematic block. **This is progress, not success** — the id design
finally validated, and neither remaining failure points to anything
left to fix in the prompt or grader.

No turn ceiling proposed yet — still no clean completion to check one
against.

## Next, per the standing instruction

Getting Fable's independent review of this result next, then
proposing a further small batch of Engine attempts (no prompt changes
— the ambiguity is closed) to see whether a clean completion is
reachable at some real rate, which is what a turn ceiling and any
eventual TE4 screen would need. Not run yet.
