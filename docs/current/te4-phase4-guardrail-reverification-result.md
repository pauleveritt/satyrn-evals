# TE4 phase-4-guardrail re-verification — result

Run and retained 2026-09-10, under
[the pre-run record](te4-phase4-guardrail-reverification-pre-run-record.md).
3 Engine attempts, under the maintainer's standing overnight
authorization ("free use of the GPU... keep working through TE").

**Corrected 2026-09-10, in full, after Fable's review found the first
draft's phase-4 tool-call counts, mechanism classifications, and the
phase-2/phase-4 guardrail "N of N clean" framing all wrong** — the
first draft's own extraction script silently dropped every
`run_self_test` call (its args are `{}`, which is falsy in Python, and
the filter used `if e.get('args')`), understating each phase-4
attempt's tool-call count by 4 and its own listed mechanisms by two
entire categories. Every number below is recomputed directly from the
retained transcripts with that bug fixed, and cross-checked against
every other post-guardrail attempt on this task family, not just this
batch's three.

## Outcome

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns |
|---|---|---|---|---|---|
| Engine-01 | pass (6) | pass (20) | pass (10) | **voided** (timeout) | 63 (6/20/10/27) |
| Engine-02 | pass (6) | **voided** (timeout) | — | — | 82 (6/76) |
| Engine-03 | pass (6) | pass (8) | pass (8) | **voided** (timeout) | 52 (6/8/8/30) |

Zero of three complete. Two reach phase 4 for the first time under the
new guardrail and both are voided there by the 600s wall clock, not
graded.

## Engine-02: phase-2-board's first *failed* attempt since the guardrail — but the guardrail's specific edit still occurred, same as in most attempts that passed

**This is the first phase-2-board *failure* since the guardrail's
adoption.** But "failure" and "the destructive edit occurred" are not
the same measure, and conflating them is exactly the error the first
draft of this document made. Reading every one of phase-2-board's 75
tool calls in order (1 `edit`, 1 `read`, 73 `write`, zero
`run_self_test`):

1. **One destructive `edit`**, the phase's 5th tool call, replaced the
   entire `home` route with the new `complaints` route in a single
   `oldText`/`newText` pair — the mechanism the guardrail exists to
   stop, occurring despite the guardrail's preservation bullet being
   present and unchanged in the prompt (digest `362480e8681f118a`).
2. The model then recovered via subsequent full `write` calls: of the
   remaining 69 `write app.py` calls (4 unique variants), most
   re-include both routes — though not all 69: one intermediate
   variant (229 bytes, one occurrence) drops the home route again
   before the dominant, 67-times-repeated variant converges with both
   routes present.
3. **What actually times the attempt out is a different, older
   mechanism**: the dominant, 67-times-repeated content is

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
   imported (only `FastAPI` is imported from `fastapi`) — confirmed by
   executing this exact file under the retained lock: `import app`
   raises `NameError: name 'Request' is not defined`. `run_self_test`
   is never called even once across all 76 turns, so nothing surfaces
   this, and the model regenerates the same broken file dozens of
   times until the wall clock ends the attempt. This is the same
   import-bug/never-self-tests pattern the
   [original phase-2-board runaway investigation](phase-2-board-runaway-investigation.md)
   named, not a new mechanism.

**The destructive edit is not rare, guardrail or not — this batch's
own attempt 1 has it too.** Scanning all 10 post-guardrail
phase-2-board attempts on this task family (this batch's 3 plus the 7
from every prior re-verification round), the identical destructive
`edit` on the home route occurs in **5 of 10**: tightening-3's
Engine-01 and Engine-02, the retained completion-rate-check's
Engine-01, and both of this batch's Engine-01 and Engine-02. **4 of
those 5 recovered and passed**; only this batch's Engine-02 did not.
The guardrail's real record, stated precisely rather than by final
outcome: it does not stop the model from making the destructive edit
in the first place at anything close to a 0% rate — but in every
occurrence except this one, subsequent writes restored the missing
route before the phase ended. **Prior documents in this sequence
(this one's own first draft, and
[the tightening-3 re-verification result](te4-tightening3-reverification-result.md),
corrected separately below) described phase-2-board's pass record as
"N of N clean," which is true only if "clean" means "final content has
both routes" — it is not true if it means "the guarded-against edit
never happened."**

## Engine-03: the phase-4 guardrail's mechanism recurred, and the attempt also destroyed its own accumulated tests

Phase-2-board and phase-3-add are both clean (8 and 8 turns). Phase 4
has 29 tool calls: 14 `edit`, 8 `read`, 3 `write`, and **4
`run_self_test` calls** (the first draft's "zero `run_self_test`"
claim for this attempt is wrong — it came from the args-filtering bug
described above). The phase's 7th tool call, and the *first* of only
two edits ever made to `app.py` in this phase, is:

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
`6c264957e8cdd793`) was applied to stop, occurring despite its
preservation bullet being present and unchanged in this exact prompt.
The route is never restored across the remaining 22 tool calls.

**A second, compounding problem, missed in the first draft: this
attempt also destroyed its own accumulated test coverage.** Tool call
9, `write tests/test_app.py`, replaces the test file inherited from
phases 1–3 with a much smaller one. The next `run_self_test` (call 10)
fails to collect at all (a FastAPI route-registration error from the
new resolve route's parameter style); by the third `run_self_test`
(call 23), pytest reports **"collected 2 items"** — down from the
roughly 7 items phase 4 should be running with (Engine-01, which never
rewrote its test file, still had 7 at the same stage). With only 2 of
its own tests left, the model's self-test tool could never have told
it the phase-3 `POST /complaints` route was missing, even if it had
kept calling it after the deletion. The final `run_self_test` (call
28) shows the **redirect-trap misdiagnosis** (see below), and the
attempt times out mid-edit on `tests/test_app.py`, never returning to
`app.py`.

**This is the seventh occurrence of the destructive-route-deletion
mechanism across the nine phase-4-reaching attempts on record** (every
attempt except the guardrail-reverification's Engine-01 and this
batch's own Engine-01) — **four of those nine never restore the route
before the phase ends** (tightening-3's Engine-02, tightening-4's
Engine-02, the completion-rate-check's Engine-01, and now this
attempt). This attempt is the first occurrence *after* the guardrail
meant to stop it was applied, and it did not stop it.

## Engine-01: no destructive edit, but not "before any test was written or run" either

**Correcting the first draft here too**: phase 4's 26 tool calls are
13 `edit`, 8 `read`, 1 `write`, and **4 `run_self_test` calls** — not
zero, and not "still mid-implementation... before any test was
written or run." A test file is written at call 13, and self-test runs
four times (calls 14, 18, 22, 24). No edit's `oldText`/`newText` on
`app.py` ever removes `@app.post("/complaints")` — the guardrail's
specific job held cleanly here, and `models.py`'s `id`/`status` fields
and `app.py`'s resolve/reopen routes are added additively.

**What the four self-tests actually show: the redirect-trap
misdiagnosis**, the same mechanism named in
[the guardrail re-verification result](te4-guardrail-reverification-result.md)
and confirmed again in Engine-03 above. Three of the four runs fail on

```python
response = client.post("/complaints/1/resolve", data={"complaint_id": 1})
assert response.status_code == 303
E   assert 200 == 303
```

— `client.post` with no `follow_redirects=False` follows the redirect
and lands on 200, and the model never adds the missing flag, instead
editing the route's parameter style (`complaint_id: int` vs.
`Form(...)`) across the remaining edits, chasing the wrong cause. The
attempt times out at 27 phase-4 turns before resolving it.

## Classification against the named-mechanism taxonomy

| Attempt | Phase | Mechanism |
|---|---|---|
| Engine-01 | phase-4 | voided timeout; additive, no destructive deletion; **redirect-trap misdiagnosis** across 3 of 4 self-tests |
| Engine-02 | phase-2-board | voided timeout; the *original* import-bug/never-self-tests runaway; the destructive edit occurred but was self-corrected in the converged content |
| Engine-03 | phase-4 | voided timeout; **destructive-edit route deletion recurred despite the phase-4 guardrail**; own test file also rewritten down to 2 items, masking the loss from self-test; final self-test also hit the **redirect-trap misdiagnosis** |

Both phase-4 attempts hit the redirect-trap misdiagnosis this round —
the first draft's claim that "no attempt hit" it, or any mechanism
beyond bare timeout, was wrong for both.

## What this does and does not establish

**Still 0 of 11 Engine attempts on this task family complete the full
task** (0 of 9 that reached phase 4). Restated precisely rather than
by final-outcome framing:

- **Phase-2-board's destructive edit occurs in about half of
  post-guardrail attempts (5 of 10)**, and self-corrects in all but
  this batch's one. The guardrail measurably changes *what usually
  happens next*, not whether the edit is attempted.
- **Phase-4's destructive edit occurs in most phase-4-reaching
  attempts regardless of the guardrail (7 of 9)**, and now occurs at
  least once *after* the guardrail was applied specifically to stop
  it, without self-correcting. One live post-guardrail data point is
  not enough to say the guardrail changed this rate at all.
- **The redirect-trap misdiagnosis is now confirmed in 4 of 9
  phase-4-reaching attempts** (guardrail-reverification's Engine-02,
  tightening-4's Engine-02, and both of this batch's Engine-01 and
  Engine-03) — a recurring, ordinary implementation-friction mechanism
  independent of either guardrail.

No turn ceiling proposed — still zero clean completions on this task
family to check one against.

## Corrections to prior documents in this sequence

[The tightening-3 re-verification result](te4-tightening3-reverification-result.md)
stated its own Engine-02 "completed normally, not via the
destructive-edit signature." Re-checked directly: that attempt's
phase-2-board *did* contain the identical destructive edit on the home
route (its 10 `edit` calls and 5 `write app.py` calls include it), and
recovered the same way this batch's Engine-01 did. That document is
corrected separately, in place, with its own dated note.

## Next, per the standing instruction

One live post-guardrail failure of the phase-4 guardrail's specific
mechanism is not enough to call the guardrail ineffective — the same
standard applied throughout this sequence (phase 2's own guardrail was
trusted only after 3 clean candidate-probe attempts, then checked
again live). But it is also not evidence the guardrail is working:
phase 2's own guardrail shows the destructive edit still happens about
half the time and mostly self-corrects; phase 4 has one post-guardrail
data point and it did not self-correct. Getting Fable's review of this
corrected result before deciding whether to run more phase-4-guardrail
attempts, treat the redirect-trap misdiagnosis as its own closable
prompt gap (it has now recurred 4 times, arguably at least as
frequent and as closable as the id-field issues tightenings 3 and 4
addressed), or conclude TE4's Engine track needs a different
intervention than incremental prompt guardrails.
