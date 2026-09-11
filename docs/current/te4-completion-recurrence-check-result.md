# TE4 completion-recurrence check — result

Run and retained 2026-09-11, under
[the pre-run record](te4-completion-recurrence-check-pre-run-record.md).
3 Engine attempts, under the maintainer's standing overnight
authorization ("free use of the GPU... keep working through TE").

## Outcome

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns | Hidden checks |
|---|---|---|---|---|---|---|
| Engine-01 | pass (6) | pass (8) | pass (11) | **pass** | 44 (6/8/11/19) | 18/18 |
| Engine-02 | pass (6) | **voided** (timeout) | — | — | 79 (6/73) | — |
| Engine-03 | pass (6) | pass (8) | pass (8) | **pass** | 36 (6/8/8/14) | 18/18 |

Model identity verified from every transcript
(`gemma-4-12B-it-MLX-8bit`). Zero `check_chain` findings on either
completed attempt; one on the voided attempt ("implementer window was
never observed" — expected for a timeout with no committed final
state). **Two more full completions, 18/18 each.** Completion recurs:
this is not a one-off. Cumulative Engine record on this task family is
now **4 of 16** (0 of 11 before round 2 of the phase-4-guardrail
re-verification; 2 of 13 after round 2; 4 of 16 after this batch).
Baseline is separately 1 of 1 on this same task (the original route
proof, before any of the fixes below existed).

**Corrected 2026-09-11**, after review: the outcome table and the
`Engine-02` mechanism section below held up unchanged. The
cross-attempt pattern section did not — its headline claim relied on
restricting the comparison to only the 6 attempts since the phase-4
guardrail's adoption, silently excluding 3 attempts on record
(`guardrail-reverify-engine-02`, `tightening3-engine-01`,
`tightening4-engine-01`) that also restored the deleted route and
still failed. Rewritten below against the full 13 phase-4-reaching
Engine attempts. Also fixed: two "inert no-op edit" descriptions that
were actually failed edits on different content; a tool-call
arithmetic error in Engine-02's phase 2; and a phase-2/phase-4
guardrail-wording misquote.

## Engine-02: the phase-2-board runaway recurred, not a phase-4 problem

72 tool calls in phase 2: 1 `edit`, 1 `read`, 70 `write` (67 to
`app.py`, 3 to `templates/base.html`/`templates/home.html`/`models.py`
early in the phase), zero `run_self_test` — exactly the shape of round
1's own Engine-02. **Corrected**: the first draft said "1 edit, 1 read,
69 write app.py" (which doesn't sum to 72) and placed the edit first;
it is actually the phase's 5th tool call, after the three other-file
writes. The `edit` destructively replaces the home route with the
complaints route — self-corrected in the converged content, the same
as every other occurrence of this pattern at phase 2. The dominant
`write app.py` content (65 of the 67 `app.py` writes) is:

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/complaints", response_class=HTMLResponse)
async def complaints(request: Request):
    from models import complaints
    return templates.TemplateResponse("complaints.html", {"request": request, "complaints": complaints})

if __name__ == "__main__":
    uvicorn.run("app:app", reload=True)
```

`Request` is used in both `home`'s and `complaints`'s signatures but
never imported — the identical `NameError`-causing import bug named in
[the original investigation](phase-2-board-runaway-investigation.md),
confirmed by executing this exact file under the retained lock
(`import app` raises `NameError: name 'Request' is not defined`).
`run_self_test` is never called, so nothing surfaces it; the model
regenerates the same broken file until the wall clock ends the
attempt. This is the second occurrence of this exact pathology in the
phase-4-guardrail era (the first was round 1's own Engine-02, which
has the same missing-`Request` bug) — a phase-2 problem, unrelated to
anything at phase 4.

## Engine-01 and Engine-03: both destroy and restore the same route, at different points relative to self-test

**Engine-01** (phase 4, tool call 8 of 18): destructively replaces
`create_complaint` with the resolve/reopen routes. **Corrected**: call
10 was described as "an inert no-op edit" — it is not. It is a failed
`edit` on `templates/complaints.html` (unrelated file; the `oldText`
had a stray character the actual file didn't contain, so the edit
tool rejected it as "could not find the exact text"), not a no-op on
`app.py`. Call 13, a full `write app.py`, restores `create_complaint`
in an additive position. The phase's only `run_self_test` call is at
18, *after* this restoration, and passes on the first try — this is a
case of restoring the route before any self-test ran, the same as
round 2's Engine-02.

**Engine-03** (phase 4, tool call 4 of 13): destructively replaces
`create_complaint` the same way, orphaning the file's
`if __name__ == "__main__":` line inside `reopen_complaint`'s body in
the process. Call 8's `run_self_test` fails. **Corrected**: call 10
was also described as "another inert no-op edit" — it too is a failed
`edit` (on `app.py` this time), whose `oldText` includes both the
already-deleted `create_complaint` block and the orphaned
`uvicorn.run(...)` line; it did not match, and the edit was rejected.
Call 12 both restores `create_complaint` and repairs the orphaned
`if __name__` block. This restoration follows a failing self-test, so
— consistent with
[round 2's own correction](te4-phase4-guardrail-reverification-round2-result.md)
about not overclaiming "unprompted" correction — this document does
not claim the fix was independent of self-test feedback. The final
`run_self_test` (call 13) passes.

## What actually predicts completion, checked across every phase-4-reaching attempt on record

**Corrected in full**: the first draft of this section restricted the
comparison to the 6 attempts since the phase-4 guardrail's adoption
and reported a clean 4-of-4-vs-2-of-2 split. That was cherry-picked by
construction — three attempts from *before* this batch, all already on
record in
[the guardrail re-verification](te4-guardrail-reverification-result.md)
and [tightening-4](te4-tightening4-reverification-result.md) results
(themselves corrected earlier in this sequence to note the
destructive edit), also restored the deleted route and still failed.
Restated against all 13 Engine attempts that have ever reached phase 4
on this task family, replaying each transcript's actual `app.py`
content edit-by-edit rather than pattern-matching individual calls:

| Group | n | Passed |
|---|---|---|
| Never destroyed the route | 2 | 0 |
| Destroyed, never restored | 4 | 0 |
| Destroyed, then restored | 7 | **4** |

The 7 "destroyed, then restored" attempts: `guardrail-reverify-engine-02`,
`tightening3-engine-01`, `tightening4-engine-01` (all three restored
the route and still failed — every one of them by hitting the 600s
wall clock, never by a submitted-and-rejected answer), plus this
sequence's four passes (`p4guardrail-round2-engine-01`,
`p4guardrail-round2-engine-02`, this batch's `Engine-01` and
`Engine-03`).

**The honest pattern, stated at the right denominator**: restoring the
deleted route is *necessary* for completion on current evidence — zero
of the 6 attempts that never restored it (2 that never destroyed it in
the first place, 4 that destroyed it and left it gone) passed, though
not all 6 failed the same way (4 were graded and rejected; 2 —
`p4guardrail-engine-01`/`-03` — also timed out) — but restoring is not
*sufficient*: 3 of the 7 restorations still failed, every one by
running out of time before finishing, not by finishing with a wrong
answer. That is a real, checkable distinction (a timeout leaves no
verdict; none of the three timed-out restorations were ever graded and
rejected), but it means the actual bottleneck for a restoring attempt
is turn/time budget, not correctness — and this document has no
account of why four restorations finished in time and three did not.

This still says something about the phase-4 guardrail, more modestly
than the first draft claimed. It does not stop the destructive edit
(11 of 13 phase-4-reaching attempts make it, guardrail or not). What
it may help with — untestable against a no-guardrail baseline without
rerunning that condition, which this document does not do — is making
the deleted route's correct, additive re-insertion point legible (the
phase-4 guardrail's own wording: "insert **them** alongside the
existing routes") once a model notices the gap, whether from a failing
self-test (`guardrail-reverify-engine-02`, `tightening4-engine-01`,
this batch's `Engine-03`) or some other route to noticing (round 2's
`Engine-02`, this batch's `Engine-01`, neither of which has
transcript evidence of what prompted the fix).

## What this does and does not establish

**Establishes**: completion recurs at the current prompt state — not a
one-off fluke from round 2, now 4 completions across 2 separate live
batches. Restoring the deleted route is a necessary condition for
completion in every phase-4-reaching Engine attempt on record (0 of 6
non-restorations passed); it is not sufficient (4 of 7 restorations
passed, the other 3 timing out). Turn counts on record for the 4
completions: 43, 49, 44, 36 — a first, thin distribution (mean ≈43,
range 36–49).

**Does not establish**: a turn ceiling with confidence (4 points, not
TE1's own six), a completion rate with a defensible confidence
interval (13 phase-4-reaching attempts, or 16 counting the ones that
never got there, is still a small sample for a rate — 4 of 16
cumulative), why restorations split 4-passed/3-timed-out, or that the
phase-4 guardrail causes the restoration behavior rather than merely
making a correct restoration legible when the model already intends
one.

## Next, per the standing instruction

This is enough evidence to say TE4's own two-per-configuration screen
is now a live option, not a settled recommendation — the id-field and
route-preservation ambiguities that blocked every earlier attempt are
closed, Engine has completed the task 4 times, and Baseline completed
it once (the original route proof, before any of these fixes existed).
Getting an independent review of this correction before proposing that
screen's frozen design, given the density of corrections every
positive-leaning claim in this sequence has needed so far.
