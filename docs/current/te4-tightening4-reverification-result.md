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
conceived, incorrectly nested). **Corrected sequencing**: the
implementer wrote a self-acknowledged nonsensical assertion in its own
test (`assert len(complaints) == len(complaints) + 1  # This is
wrong, but let's check logic`) *before* running self-test, not as a
reaction to a caught bug. Self-test then surfaced the real bug as a
`422 Unprocessable Entity` on `/complaints/None/resolve` — the
implementer never connected that `422` to `id` being `None`, made
several more edits chasing the wrong problem, and ran out of time at
25 phase-4 turns.

**Also missed, added 2026-09-11** (found reviewing
[the phase-4-guardrail round-2 result](te4-phase4-guardrail-reverification-round2-result.md)):
this attempt's `app.py` edits also show the destructive-edit-then-restore
pattern — tool call 7 destructively replaces `create_complaint` with
the resolve route, and call 10 restores it via a second targeted
`edit`. The route itself is not what causes this attempt's eventual
timeout (the `__post_init__` bug is), but the pattern was present and
undocumented here; it is not unique to Engine-02 above or to this
document's own classification of it as new there.

**Engine-02: a destructive edit deleted an already-accepted route** —
the same mechanism named in
[the phase-2-board runaway investigation](phase-2-board-runaway-investigation.md),
recurring at phase 4, which has no guardrail against it. **Corrected**:
this was not a side effect of "rewriting" `app.py` — one `edit` call
explicitly replaced the entire `create_complaint` handler and the
`if __name__ == "__main__":` block with the new resolve route in a
single `oldText`/`newText` pair. This is the **second of the last two
graded phase-4 attempts** to do exactly this (the
[tightening-3 re-verification](te4-tightening3-reverification-result.md)'s
Engine-02 did the identical thing, corrected there too). `id`'s own
design is otherwise correct in this attempt. 5 of 18 checks fail, all
traced to the deleted route — phase 3's own two `POST /complaints`
checks directly, and 3 of the 4 phase-4 checks because their own test
setup posts a complaint through that now-missing route first
(overdetermined, not independent evidence).

**Also missed in the first draft of this document**: Engine-02 also
fell into the **redirect-trap misdiagnosis** named in
[the guardrail re-verification](te4-guardrail-reverification-result.md)
— its own test asserts `response.status_code == 303` on a
`client.post(...)` call with no `follow_redirects=False`, the same
trap. And its final turn ended with `stopReason: "length"` — an
8,192-token generation that degenerated into repeating the same
`RedirectResponse(url="/complaints", status_code=303)` line dozens of
times as *text*, not a tool call, until the model's own output cap cut
it off. This is a **fourth, distinct termination mode**, different
from the wall-clock timeout every prior voided attempt hit: the phase
was graded ("delivered") only because generation happened to stop
there, not because the implementer finished. Named here, not
previously classified; the pre-run record's own voiding rule does not
cover a length-cut turn that still produces gradable output, and
whether it should is not decided in this document.

## The fifth-tightening question, reopened

**The first draft of this document concluded no fifth tightening was
needed, on a mischaracterized evidence base — corrected here rather
than left standing.** The actual pattern: 2 of the 3 *graded* phase-4
attempts on record (both this run's Engine-02 and the prior round's)
destroyed the phase-3 route via the identical destructive-edit
mechanism phase 2 needed its own guardrail for. That is not "ordinary
implementation variance" in the sense a misplaced `__post_init__` is —
it is the same defect recurring in a location with no protection
against it, at a rate at least as high as phase 2's own runaway rate
before its guardrail (2 of 4). Phase 2's own prompt now carries a
preservation bullet ("insert it alongside the existing route — do not
remove, replace, or rewrite the route that already works"); phase 4's
prompt carries no equivalent, and the packet's `preserve` field only
protects phase 2's own route by name, not phase 3's.

**Two honest readings, not one settled answer:**

1. Add a phase-4 analog of the phase-2 guardrail, on the same
   reasoning tightenings 3 and 4 used: this is a closable, exploited
   gap in the prompt, not new task difficulty, and leaving it
   unprompted risks confusing "Engine can't preserve routes" with "the
   prompt never told it to."
2. Leave it unprompted deliberately, because unlike phase 2's version
   (which produced an unmeasurable, voided runaway), this one produces
   a clean, gradable rejection — arguably exactly the
   cumulative-preservation signal TE4 exists to measure, and prompting
   it away would remove that signal rather than an accidental
   ambiguity.

This document does not pick between them; the next step does.

## Where this leaves the id-field question

Tightenings 3 and 4 are done, and **validated once, live** — Engine-02
proves the corrected instruction is sufficient to reach a fully
correct `Complaint` design in at least one attempt, not that it is
reliable. The `id`-field ambiguity that caused two of the first four
phase-4 failures (not three — see the correction below) is closed.

## What this does and does not establish

**Still 0 of 7 Engine attempts on this task family complete the full
task** (0 of 6 that reached phase 4). The count of "first four
failures" attributable to the `id` gap is **two**, not three: the
route proof's Engine-01 never reached phase 4 at all (voided at
phase-2-board, pre-guardrail); the guardrail re-verification's
Engine-02 was the redirect-trap misdiagnosis, not the `id` gap. Only
the tightening-3 round's two attempts trace to `id`. What has
genuinely moved: no attempt has repeated the `id`-before-`agent_name`
or `id`-no-default mistakes since tightening 4 landed. What has not
moved: the destructive-edit-on-an-existing-route mechanism, now
observed at two different phases.

No turn ceiling proposed yet — still no clean completion to check one
against.

## Next, per the standing instruction

Decide the fifth-tightening question explicitly (above), rather than
carrying "no fifth tightening" forward as settled. If phase 4 gets its
own guardrail, re-verify it the same way tightenings 3 and 4 were
re-verified before proposing any completion-rate batch — a batch run
against the current, uncorrected prompt would very likely just
reproduce more route deletions, which is not new information.

**Resolved, 2026-09-10.** While deciding this, a third live Engine
attempt (already in flight, launched under the unguarded prompt before
this reopening) finished: same destructive `edit`, same deleted
`POST /complaints` route, same 5 failing checks (13/18) — the third of
four graded phase-4 attempts to do this. That settles reading 1 over
reading 2: three-quarters of every gradable phase-4 attempt on record
hitting the identical mechanism phase 2 already needed a guardrail for
is a closable defect, not a difficulty worth preserving as signal. The
phase-4 guardrail is applied — see the task's own
[`QUALIFICATION-NOTE.md`](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md),
"The phase-4 guardrail." Re-verification is next.
