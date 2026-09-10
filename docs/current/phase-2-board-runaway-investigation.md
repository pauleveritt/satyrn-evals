# Phase-2-board runaway loop — offline investigation

Written 2026-09-10, offline, no inference. Follows the
[TE4 route proof's](te4-route-proof-result.md) recommendation to
investigate the phase-2-board pathology before spending TE4's own
screen. Method: compare all four real Engine attempts ever run against
phase-2-board, using only what is already retained — no new model
generation.

## The population

| Attempt | Outcome | Turns | `edit app.py` used? |
|---|---|---|---|
| HP7 | pass | 8 | no — writes `models.py` then `app.py` directly, no separate edit |
| TE2/HP8 Engine-02 | pass | 9 | yes, additive |
| TE2/HP8 Engine-01 | **runaway** | 65 (timeout) | yes, destructive |
| TE4 route proof Engine-01 | **runaway** | 61 (timeout) | yes, destructive |

Both timeouts follow an `edit app.py` call of one specific shape; both
successful attempts either skip `edit` entirely or use it additively.
This is the first structural difference found, not a restated summary
of turn counts.

## The distinguishing mechanism

All three attempts that call `edit` reach the same point: `app.py` has
the phase-1 home route, and the model adds the phase-2 `/complaints`
route. The two outcomes diverge in how the edit is made.

**TE2/HP8's Engine-02 (passed) — additive**, full retained diff:

```diff
  1 from fastapi import FastAPI, Request
  2 from fastapi.responses import HTMLResponse
  3 from fastapi.templating import Jinja2Templates
  4 import uvicorn
+ 5 from models import complaints
  5
  6 app = FastAPI()
  7 templates = Jinja2Templates(directory="templates")
  8
  9 @app.get("/", response_class=HTMLResponse)
 10 async def read_home(request: Request):
 11     return templates.TemplateResponse("home.html", {"request": request})
 12
+14 @app.get("/complaints", response_class=HTMLResponse)
+15 async def read_complaints(request: Request):
+16     return templates.TemplateResponse("complaints.html", {"request": request, "complaints": complaints})
+17
 13 if __name__ == "__main__":
 14     uvicorn.run("app:app", reload=True)
```

The existing home route (lines 10–11) is untouched; the edit only
inserts. The attempt proceeds normally afterward: `templates/complaints.html`,
`tests/test_app.py`, `run_self_test` (passed), phase accepted.

**Both runaway attempts (TE2/HP8 Engine-01, TE4 Engine-01) —
destructive**, TE4's own diff:

```diff
    ...
  5
  6 app = FastAPI()
  7 templates = Jinja2Templates(directory="templates")
  8
- 9 @app.get("/", response_class=HTMLResponse)
-10 async def read_home(request: Request):
-11     return templates.TemplateResponse("home.html", {"request": request})
+ 9 @app.get("/complaints", response_class=HTMLResponse)
+10 async def read_complaints(request: Request):
+11     return templates.TemplateResponse("complaints.html", {"request": request, "complaints": complaints})
```

The `oldText` matched the entire home-route block and the `newText`
replaced it — the edit tool reported "Successfully replaced 1
block(s)," which is accurate to what was asked, but what was asked
deletes phase 1's preserved route. TE2/HP8's own Engine-01 diff is
structurally identical (different variable names, same shape:
`home`/`get_complaints` swapped in for the home route wholesale).

## What happens after the destructive edit

Both runaway attempts then spend the next several `write app.py` calls
converging on a *repaired* file that restores both routes — and both
converge on a version with the **same bug**: `Request` is used in a
type annotation but never imported.

TE2/HP8 Engine-01's converged (and then repeated 58 times) content:

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
...
async def home(request: Request):
```

TE4's converged (and then repeated 53 times) content has the identical
class of bug, same missing import, different route names. Both would
raise `NameError: name 'Request' is not defined` the moment the module
is imported — a bug `run_self_test` would have caught immediately, the
same way it caught and the model recovered from a real bug in
[TE2/HP8's Engine-02, phase 3](te2-hp8-screen-result.md#self-test-recovery-observed-live-for-the-first-time).
`run_self_test` is never called in either runaway phase. No assistant
text is produced on any turn in either runaway phase either — the
model reasons in tool calls only, here as in every phase-2-board
attempt on record.

## What this does and does not establish

**Does not establish causation.** Two matched pairs (2 destructive → 2
runaway; 1 additive/0 edits → 2 passed) is a clean correlation, not a
controlled experiment, and this repo's own retained artifacts do not
include the per-turn model input/context — only tool-call output is
retained (named as a real, previously-unacknowledged instrumentation
gap in this session's own record). Whether the destructive edit
*causes* the subsequent loop, or both are downstream of some other
per-turn state this investigation cannot see, is not decided here.

**Does establish a reproducible, falsifiable pattern**, not previously
named: every runaway on record follows a destructive full-block
`edit`, converges on a file with an import bug identical in kind
across both occurrences, and never reaches `run_self_test` — a tool
this same route successfully used for recovery elsewhere. That is
concrete enough to test, which the two prior write-ups (informally, by
turn counts alone) were not.

## Candidate remedy — named, not implemented or authorized

Note first what this is *not*: the earlier candidate factor named for
[TE2/HP8's own runaway](te2-hp8-screen-result.md#the-runaway-loop-engine-01-phase-2)
was `write`'s silent success on unchanged content. That does not apply
here — `edit` already reports accurately in both runaway cases
("Successfully replaced 1 block(s)"); the problem is not a silent
failure, it is an accurate report of a *destructive* success the model
does not appear to notice or recover from.

One narrow, testable hypothesis this investigation does support:
detect when an `edit`'s `oldText` spans an entire existing route or
function body (as opposed to a smaller insertion point) and either
flag it to the implementer or require the edit be split into a
narrower insertion. This is a hypothesis worth a bounded, separately
authorized test — not implemented here, and not proposed as a
production fix without first seeing whether it actually changes the
outcome, per this project's standing rule against adding a repeat
guard pre-emptively
([`engine-turn-efficiency-plan.md`](engine-turn-efficiency-plan.md),
TE1: "do not add a harness repeat cutoff when recovery from repetition
is the question").

## Recommendation

Unchanged from the route proof: do not spend TE4's two-per-configuration
screen next. This investigation sharpens *what* to test before that
screen, it does not clear the pathology. A small, separately authorized
probe — e.g., one more live phase-2-board attempt with no code changes,
purely to see whether a third destructive edit reproduces the same
converged-bug signature a third time, or a bounded test of the
candidate remedy above — would do more to inform TE4's screen than
running the screen itself would. Neither is proposed for execution by
this document; both need their own authorization when the maintainer
chooses one.
