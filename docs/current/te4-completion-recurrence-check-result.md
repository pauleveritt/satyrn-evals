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
this is not a one-off. Cumulative record on this task family is now
**4 of 16** (0 of 11 before round 2 of the phase-4-guardrail
re-verification; 2 of 13 after round 2; 4 of 16 after this batch).

## Engine-02: the phase-2-board runaway recurred, not a phase-4 problem

72 tool calls in phase 2: 1 `edit`, 1 `read`, 69 `write app.py`, zero
`run_self_test`, exactly the shape of round 1's own Engine-02. The
`edit` (call 1 of 72) destructively replaces the home route with the
complaints route — self-corrected in the converged content, the same
as every other occurrence of this pattern at phase 2. The dominant
`write app.py` content (65 of 69 occurrences) is:

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

`Request` is used in `home`'s signature but never imported — the
identical `NameError`-causing import bug named in
[the original investigation](phase-2-board-runaway-investigation.md).
`run_self_test` is never called, so nothing surfaces it; the model
regenerates the same broken file until the wall clock ends the
attempt. This is the second occurrence of this exact pathology in the
phase-4-guardrail era (the first was round 1's own Engine-02) — a
phase-2 problem, unrelated to anything at phase 4.

## Engine-01 and Engine-03: both destroy and restore the same route, at different points relative to self-test

**Engine-01** (phase 4, tool call 7 of 19): destructively replaces
`create_complaint` with the resolve/reopen routes. Call 9 is an
inert no-op edit (`oldText == newText`). Call 12, a full `write
app.py`, restores `create_complaint` in an additive position. The
phase's only `run_self_test` call is at 17, *after* this restoration
and passing on the first try — this is a case of restoring the route
before any self-test ran, the same as round 2's Engine-02.

**Engine-03** (phase 4, tool call 3 of 13): destructively replaces
`create_complaint` the same way. Call 7's `run_self_test` fails; call
9 is another inert no-op edit; call 11 restores `create_complaint`.
This restoration follows a failing self-test, so — consistent with
[round 2's own correction](te4-phase4-guardrail-reverification-round2-result.md)
about not overclaiming "unprompted" correction — this document does
not claim the fix was independent of self-test feedback. The final
`run_self_test` (call 12) passes.

## The pattern that actually predicts completion, checked across every phase-4-guardrail-era attempt

Combining this batch with round 1 and round 2 (6 attempts have now
reached phase 4 under the current, unchanged post-guardrail prompt):

| Attempt | Destructive edit? | Restored? | Outcome |
|---|---|---|---|
| round1-Engine-01 | no | — | voided (redirect-trap chase, ran out of turns) |
| round1-Engine-03 | yes | **no** | voided (never restored) |
| round2-Engine-01 | yes | yes (after a failing self-test) | **pass, 18/18** |
| round2-Engine-02 | yes | yes (before any self-test) | **pass, 18/18** |
| recurrence-Engine-01 | yes | yes (before any self-test) | **pass, 18/18** |
| recurrence-Engine-03 | yes | yes (after a failing self-test) | **pass, 18/18** |

**Every attempt that restored the deleted route went on to pass all 18
hidden checks; every attempt that did not restore it (either because it
never destroyed the route and instead got stuck elsewhere, or because
it destroyed it and never fixed it) failed to complete.** At n=6 this
is a clean, complete split — 4 of 4 restorations completed, 2 of 2
non-restorations did not — not a statistical claim at this sample size,
but a specific, checkable fact worth stating exactly as it is: **on
current evidence, restoring the phase-3 route is the single event that
distinguishes completion from non-completion at phase 4** — more
than whether the redirect trap is hit, more than whether self-test ran
before or after the fix. Whether self-test feedback drives the fix
(as in 2 of the 4 restorations) or the model catches it independently
(the other 2) does not appear to matter to the outcome, at this sample
size.

This reframes what the phase-4 guardrail is and is not doing. It does
not stop the destructive edit (5 of 6 phase-4-reaching attempts still
make it). What it may be doing — untestable against a no-guardrail
baseline without rerunning that condition, which this document does
not do — is keeping the deleted route's correct, additive
re-insertion point obvious enough (the guardrail's own wording:
"insert it alongside the existing routes") that a model which does
notice the gap (via self-test or its own re-reading) reliably restores
it correctly rather than papering over it a different way.

## What this does and does not establish

**Establishes**: completion recurs at the current prompt state — not
a one-off fluke from round 2. 4 of 6 phase-4-guardrail-era
phase-4-reaching attempts now complete cleanly (67%), with a clean,
exactly-replicated destroy-then-restore mechanism behind every one of
them. Turn counts on record for completions: 43, 49, 44, 36 — a first,
thin distribution (mean ≈43, range 36–49).

**Does not establish**: a turn ceiling with confidence (4 points, not
TE1's own six), a completion rate with a defensible confidence
interval (6 phase-4-reaching attempts is still a small sample, and the
6th, phase-2-board-voided attempt reminds us the denominator for a
"real" rate should probably be all attempts, not just phase-4-reaching
ones — 4 of 8 phase-4-guardrail-era attempts complete, if
phase-2-board voids are counted), or that the phase-4 guardrail causes
the restoration behavior rather than merely making a correct
restoration legible when the model already intends one.

## Next, per the standing instruction

This is enough evidence to say TE4's own two-per-configuration screen
is now a live option, not a settled recommendation — the id-field and
route-preservation ambiguities that blocked every earlier attempt are
closed, Engine has completed the task 4 times, and Baseline completed
it once (the original route proof, before any of these fixes existed).
Getting an independent review of this result before proposing that
screen's frozen design, given the density of corrections every
positive-leaning claim in this sequence has needed so far.
