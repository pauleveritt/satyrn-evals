# TE4 phase-4-guardrail re-verification — result

Run and retained 2026-09-10, under
[the pre-run record](te4-phase4-guardrail-reverification-pre-run-record.md).
3 Engine attempts, under the maintainer's standing overnight
authorization ("free use of the GPU... keep working through TE").

## Outcome

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns |
|---|---|---|---|---|---|
| Engine-01 | pass (6) | pass (20) | pass (10) | **voided** (timeout) | 63 (6/20/10/27) |
| Engine-02 | pass (6) | **voided** (timeout) | — | — | 82 (6/76) |
| Engine-03 | pass (6) | pass (8) | pass (8) | **voided** (timeout) | 52 (6/8/8/30) |

Zero of three complete. Two reach phase 4 for the first time under the
new guardrail and both are voided there by the 600s wall clock, not
graded. The per-attempt classification below is what the pre-run
record's own "What happens after" section requires before deciding
what comes next — and it says plainly what it found, including where
that is a worse signal than hoped.

## Engine-02: the phase-2-board guardrail's first recurrence — but not the mechanism it guards against

**This is the first phase-2-board failure since the guardrail's
adoption** (had been 10 of 10 clean, including this batch's own
attempt 1, before this). Read closely, though, it is not a violation
of the guardrail's own instruction in the way that matters: reading
every tool call in phase-2-board's segment (75 real calls: 1 `edit`, 1
`read`, 73 `write`, zero `run_self_test`) shows

1. **One destructive `edit`** early in the phase (call index 8) that
   replaced the entire `home` route with the new `complaints` route in
   a single `oldText`/`newText` pair — textbook instance of the
   mechanism the guardrail exists to stop, occurring even with the
   guardrail's preservation bullet present and unchanged in the
   prompt (digest `362480e8681f118a`, unaltered).
2. **But the model then recovered from its own destructive edit** —
   every one of the 70 subsequent `write app.py` calls (4 unique
   variants, one occurring 67 times) re-includes both the `/` home
   route and the `/complaints` route. The guardrail's specific
   preservation goal (don't lose an existing route) held in the
   content that actually converged.
3. **What actually times the attempt out is the *original*,
   pre-guardrail runaway mechanism** named in
   [the phase-2-board runaway investigation](phase-2-board-runaway-investigation.md):
   the dominant, 67-times-repeated content is

   ```python
   from fastapi import FastAPI
   from fastapi.templating import Jinja2Templates
   from fastapi.responses import HTMLResponse
   import uvicorn

   app = FastAPI()
   templates = Jinja2Templates(directory="templates")

   from models import complaints

   @app.get("/", response_class=HTMLResponse)
   async def home(request: Request):
       return templates.TemplateResponse("home.html", {"request": request})

   @app.get("/complaints", response_class=HTMLResponse)
   async def complaints_route(request: Request):
       return templates.TemplateResponse("complaints.html", {"request": request, "complaints": complaints})

   if __name__ == "__main__":
       uvicorn.run("app:app", reload=True)
   ```

   `Request` is used in the `home` handler's signature but never
   imported (only `FastAPI` is imported from `fastapi`) — a
   `NameError` at import time that would crash the app before serving
   any route. `run_self_test` is never called even once across all 76
   turns, so nothing ever surfaces this to the model; it just
   regenerates the same broken file dozens of times until the 600s
   wall clock ends the attempt. This is the identical import-bug/
   never-self-tests pattern the original investigation named, not a
   new mechanism, and not the destructive-edit pattern the guardrail
   targets — the guardrail's own instruction was followed in the
   content that converged, even after being transiently violated.

**Honest framing**: the phase-2 guardrail continues to hold against
the specific mechanism it was written for (destructive route deletion
persisting to the final state) — 11 of 11 on that specific measure,
counting this attempt's self-corrected transient violation as not a
failure of the guarded-against outcome. But phase-2-board's older,
broader runaway pathology (never calling self-test, converging on
uncaught import bugs) is not what the guardrail addresses, and it has
now recurred once in 11 attempts. The guardrail was never proposed as
a fix for that broader pathology, and this result does not show it
failing at the job it was given — but it is a reminder that
phase-2-board's runaway risk is not fully retired.

## Engine-03: the phase-4 guardrail's first live test of the specific mechanism — and it did not hold

**Phase-2-board and phase-3-add are both clean** (8 and 8 turns,
matching the task family's typical range). Phase 4 has 29 tool calls
(14 `edit`, 8 `read`, 3 `write`, zero `run_self_test`) before the 600s
timeout. The fourth `edit` call on `app.py` is:

```python
# oldText
@app.post("/complaints")
async def create_complaint(request: Request, agent_name: str = Form(...), text: str = Form(...)):
    new_complaint = Complaint(agent_name=agent_name, text=text)
    complaint...

# newText
@app.post("/complaints/{complaint_id}/resolve")
async def resolve_complaint(request: Request, complaint_id: int = Form(...)):
    for complaint in complaints:
        ...
```

This is the exact mechanism the phase-4 guardrail (digest
`6c264957e8cdd793`, current) was applied to stop: a single
`oldText`/`newText` pair that deletes the already-accepted phase-3
`POST /complaints` route while adding the new resolve route, rather
than inserting it alongside. **The guardrail's preservation bullet was
present, unchanged, in this exact prompt, and the destructive edit
happened anyway.** Unlike the two prior graded occurrences (tightening-3
and tightening-4 re-verification, both of which produced a gradable,
rejected result), this attempt never reaches self-test or grading at
all — it times out mid-edit, still iterating on `app.py`/`models.py`
turns after the deletion, so there is no confirmation either that the
model would have recovered the route the way Engine-02 recovered
phase-2's home route, or that it would not have.

**This is the fourth occurrence of the destructive-route-deletion
mechanism at phase 4 across five graded-or-substantially-progressed
attempts on record** (tightening-3's Engine-02; tightening-4's
Engine-02; the completion-rate-check's retained Engine-01; now this
attempt) — the first occurring *after* the guardrail meant to stop it
was applied. Per the pre-run record's own instruction: **the pattern
recurred once at this `n`, stated plainly** — this is a materially
worse signal than phase 2's own guardrail record, which has never
shown the guarded-against outcome recur in 11 attempts. The phase-4
guardrail, as worded, did not stop this occurrence.

## Engine-01: no destructive edit, ordinary time exhaustion

Phase 4's 26 tool calls (13 `edit`, 8 `read`, 1 `write`, zero
`run_self_test`) show additive, iterative work: `models.py`'s `id`/
`status` fields are edited in place (not replaced), `app.py` gains the
resolve and reopen routes without ever removing `create_complaint`
(checked directly — every edit's `oldText` and `newText` either both
contain `create_complaint` or neither does), and the final edit
produces both:

```python
@app.post("/complaints/{complaint_id}/resolve")
async def resolve_complaint(request: Request, complaint_id: int):
    for complaint in complaints:
        if complaint.id == complaint_id:
            complaint.status = "resolved"
            break
    return RedirectResponse(url="/complaints", status_code=303)

@app.post("/complaints/{complaint_id}/reopen")
async def reopen_complaint(request: Request, complaint_id: int):
    for complaint in complaints:
        if complaint.id == complaint_id:
            complaint.status = "open"
            break
    return RedirectResponse(url="/complaints", status_code=303)
```

No `run_self_test` call happens before the timeout, so this is
unverified by the model's own tooling, but the guardrail's specific
job — don't destroy the existing route — held cleanly here. This
attempt's voiding is ordinary time exhaustion (26 phase-4 turns against
the same shape of work tightening-4's Engine-01 needed 25 for, before
this attempt's own turn budget of 20/30 declared-not-enforced values),
not a route-deletion recurrence.

## Classification against the named-mechanism taxonomy

| Attempt | Phase | Mechanism |
|---|---|---|
| Engine-01 | phase-4 | voided timeout; additive edits, no destructive deletion, no self-test called |
| Engine-02 | phase-2-board | voided timeout; the *original* import-bug/never-self-tests runaway (guardrail's own preservation goal held in the converged content despite one transient violation) |
| Engine-03 | phase-4 | voided timeout; **destructive-edit route deletion recurred despite the phase-4 guardrail** |

No attempt hit the `id`-before-`agent_name`, `id`-no-default,
misplaced-`__post_init__`, redirect-trap-misdiagnosis, or
`stopReason: "length"` mechanisms this round — all three attempts that
reached phase 4 (two of three) were still mid-implementation at
timeout, before any test was written or run.

## What this does and does not establish

**Still 0 of 11 Engine attempts on this task family complete the full
task** (0 of 9 that reached phase 4, counting this batch's two).
Phase-2-board's guardrail-specific record is unchanged at "no
recurrence of the guarded-against outcome" (11 of 11), but its broader
runaway risk is not retired — one recurrence in 11. **Phase-4's
guardrail-specific record is now one failure in its one live test**:
the mechanism it was written to stop happened anyway, in the same
prompt state the guardrail was meant to fix. That is a genuinely
different, worse outcome than what tightenings 3 and 4 showed on their
own first live tests (both held cleanly on their first re-verification
round). No turn ceiling proposed — still zero clean completions on
this task family to check one against, and this batch adds no
completions.

## Next, per the standing instruction

The phase-4 guardrail's single live failure is not enough evidence to
conclude the guardrail sentence itself is wrong — Engine-03's
destructive edit happened at only its fourth phase-4 tool call, well
before self-test or any correction opportunity, so this could be
ordinary attempt-to-attempt variance in whether the model attends to
the preservation bullet, the same way phase 2's own guardrail was
validated on 3 clean attempts before being trusted. But calling it
settled either way on one data point would repeat the exact evidence
error already corrected once in this sequence (the "no fifth
tightening" conclusion, reopened after Fable's review). Getting
Fable's review of this result, per the standing instruction, before
deciding whether to run more phase-4-guardrail attempts or treat this
as inconclusive.
