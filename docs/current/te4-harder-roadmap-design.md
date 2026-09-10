# TE4 harder roadmap — design

Written 2026-09-10, offline, no inference. Scopes
[the TE plan's](engine-turn-efficiency-plan.md) TE4 starting candidate —
"extend the app with stable complaint identity and a resolve/reopen
lifecycle spanning model, routes and templates, while preserving the
earlier creation, display and ordering behavior. Qualify its feasibility
against the existing app before committing to that design." This
document is that feasibility qualification. It authorizes no inference,
no fixture build, no screen — only the design.

**Built and proven, 2026-09-10.** The task, grader tests, fixtures and
qualification suite described below now exist as designed; see
`src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md`
and the TE4 entry in `ROADMAP.md` for what was verified. This document's
own content is left as written — it was the plan, not a live record —
except "What this document does not do," corrected in place below.

## The new task, not a new task family

A new task directory,
`src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/`, sibling to
`agentclinic-session-phased`, reusing its machinery exactly per house
convention ("reuse the current app, checkpoint grader and fixture
machinery"):

- `base/`: byte-identical copy of the existing task's `base/` — same
  bare scaffold, same pinned `pyproject.toml`/`uv.lock`.
- `session.json`: phases 1–3 copied **verbatim** (prompt, facts,
  `new_feature_selectors`) from `agentclinic-session-phased/session.json`
  — not re-derived, to keep their grading identical — plus one new step,
  `phase-4-resolve-reopen`.
- `grader/overlay/grader_tests/`: `test_phase1_home.py`,
  `test_phase2_board.py`, `test_phase3_add.py`, `_contract.py`,
  `_seed.py` copied verbatim, plus a new `test_phase4_resolve_reopen.py`.
- `fixtures/`: new `checkpoint-4.patch` (extends `checkpoint-3`),
  `known-good` (= checkpoint-4), `known-broken`, `regression`,
  `prompt-faithful`, `contaminated` — see "Fixtures needed," below.
- `manifest.json`: new, pointing at this directory's own `base/`,
  `grader/overlay`, `fixtures/`.

One new phase, not two. The plan's candidate names "a resolve/reopen
lifecycle" as one unit; resolve and reopen share the same identity
mechanism and the same status field, and splitting them into separate
phases would not add a meaningfully different dependency — it would
just add roadmap length. "Add exactly one more demanding roadmap" is
satisfied by one new step with real internal dependencies (identity,
two mutating routes, conditional template logic), not by two thin ones.

## The identity/positional-construction conflict, and its resolution

`agentclinic-session-phased`'s own
[QUALIFICATION-NOTE.md](../../src/satyrn_evals/tasks/agentclinic-session-phased/QUALIFICATION-NOTE.md)
already names this exact risk as an unprobed ambiguity: `Complaint`'s
hidden contract check calls it positionally —
`Complaint("first", "First complaint")` — and "a solver that adds an
`id` field ahead of `agent_name`... fails this check even though the
field list it names is present." A naive identity addition breaks
phase 2's own preserved check.

**Resolution, verified against the actual current model**
(`models.py`, via `known-good.patch`):

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count

_id_counter = count(1)


@dataclass
class Complaint:
    agent_name: str
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int = field(default_factory=lambda: next(_id_counter), kw_only=True)
    status: str = field(default="open", kw_only=True)
```

`kw_only=True` per field (Python ≥3.10; this task pins `>=3.12`) removes
`id`/`status` from positional argument order and count entirely —
`Complaint("first", "First complaint")` continues to construct exactly
as before, with `id` and `status` filled from their defaults. This is
the central preservation proof for the new phase and must be a named,
direct check in `test_phase4_resolve_reopen.py` — not left implicit —
exactly mirroring how `test_complaint_model_contract_is_preserved`
already asserts the positional call today.

`_id_counter` is module-level and shared, so the four seed complaints
(constructed in list-literal order at import) receive ids 1–4 in order,
and every complaint added via `POST /complaints` continues the same
counter. Ids are assigned once, at construction, never recomputed from
list position — this is what "stable" identity means here, and it is
what a resolve/reopen route needs to target one complaint reliably.

## Routes

```python
@app.post("/complaints/{complaint_id}/resolve")
async def resolve_complaint(complaint_id: int):
    for complaint in complaints:
        if complaint.id == complaint_id:
            complaint.status = "resolved"
            break
    return RedirectResponse("/complaints", status_code=303)


@app.post("/complaints/{complaint_id}/reopen")
async def reopen_complaint(complaint_id: int):
    for complaint in complaints:
        if complaint.id == complaint_id:
            complaint.status = "open"
            break
    return RedirectResponse("/complaints", status_code=303)
```

An id that matches nothing is out of scope, deliberately: the existing
task never specifies behavior for malformed input either (e.g., a
missing form field), so this is consistent with the established
contract, not a new gap this task introduces.

## Templates

Each card in `templates/complaints.html` gains a status badge and one
conditional action:

```html
<span class="badge {{ 'text-bg-secondary' if complaint.status == 'open' else 'text-bg-success' }}">
    {{ "Open" if complaint.status == "open" else "Resolved" }}
</span>
{% if complaint.status == "open" %}
<form method="post" action="/complaints/{{ complaint.id }}/resolve" class="d-inline">
    <button type="submit" class="btn btn-sm btn-outline-secondary">Resolve</button>
</form>
{% else %}
<form method="post" action="/complaints/{{ complaint.id }}/reopen" class="d-inline">
    <button type="submit" class="btn btn-sm btn-outline-secondary">Reopen</button>
</form>
{% endif %}
```

**Ordering is explicitly unchanged.** The phase-4 prompt states the
list stays in the same order established by phases 2–3 (creation
order) — resolving a complaint does not move it. This keeps the new
phase's preservation surface to identity/status/routes only, not a
second, independent reordering requirement layered on top.

## Draft phase-4 prompt

Same preamble as phases 1–3 (writable scope, `uv run python -m pytest
tests`, address failures without weakening tests), followed by:

> ## Phase 4 — Resolve and Reopen
>
> - Add a stable `id: int` field to the `Complaint` dataclass in
>   `models.py`, assigned once when a complaint is created, unique and
>   never reused or recomputed from its position in the list
> - Add a `status: str` field to `Complaint`, defaulting to `"open"`
> - Add `POST /complaints/{complaint_id}/resolve` in `app.py`: set
>   that complaint's `status` to `"resolved"`, then redirect to
>   `GET /complaints` (`RedirectResponse`, status 303)
> - Add `POST /complaints/{complaint_id}/reopen` in `app.py`: set that
>   complaint's `status` back to `"open"`, then redirect the same way
> - In `templates/complaints.html`, show each complaint's status as a
>   badge reading exactly "Open" or "Resolved"
> - For an open complaint, show a "Resolve" button (a form posting to
>   its resolve route); for a resolved complaint, show a "Reopen"
>   button instead
> - Complaints stay in the same order they appear today — resolving or
>   reopening a complaint must not move it
> - Write tests in `tests/test_app.py`: resolving an open complaint
>   changes its status and redirects with 303; reopening a resolved
>   complaint changes it back; the complaint list order is unchanged
>   after either action

## Hidden checks needed (draft, `test_phase4_resolve_reopen.py`)

Cumulative scope: phases 1–4, importing `_contract` and `_seed` exactly
as phase 2/3 do.

1. `test_complaint_identity_is_stable_and_keyword_only` — the
   preservation proof above: `fields(Complaint)` has `id`/`status` as
   `kw_only`; `Complaint("first", "First complaint")` still constructs;
   two complaints built in sequence get distinct, increasing `id`s.
2. `test_seed_complaints_have_distinct_ids` — `len({c.id for c in
   SEED_COMPLAINTS}) == len(SEED_COMPLAINTS)`.
3. `test_resolve_route_marks_complaint_resolved_and_redirects` — POST
   to an existing id's resolve route, `follow_redirects=False`, 303,
   then GET shows a "Resolved" badge for that complaint.
4. `test_reopen_route_marks_complaint_open_and_redirects` — resolve
   then reopen the same complaint; badge reads "Open" again.
5. `test_resolve_reopen_does_not_reorder_the_board` — capture
   `GET /complaints` card order before and after a resolve/reopen
   cycle; assert it is unchanged (this is the new phase's own
   cross-cutting preservation check, mirroring how phase 2 checked
   phase 1's layout).
6. Re-run of phase 1–3's own preservation-flavored checks at this
   checkpoint (already implied by cumulative `new_feature_selectors`,
   not a new file) — confirms phase 4 did not disturb doctype, nav,
   seed text, or the add-complaint flow.

## Fixtures needed (not yet built)

Following `agentclinic-session-phased`'s own pattern exactly:

| fixture | purpose |
|---|---|
| `checkpoint-4.patch` | phase-4 tree, extending `checkpoint-3` |
| `known-good.patch` | = `checkpoint-4`, all checks pass |
| `known-broken.patch` | the exact ambiguity named above: `id` declared as a **required positional** field before `agent_name`, breaking `Complaint("first", "First complaint")` — proves the preservation check actually catches the one failure mode this design was built to avoid |
| `regression.patch` | resolve/reopen reorders the board (e.g., resolved items sorted to the bottom) — must fail check 5 above without touching any phase 1–3 check |
| `prompt-faithful.patch` | written from the phase-4 prompt text alone, no check-reading — proves a prompt-conformant solution scores full marks |
| `contaminated.patch` | grader text lifted verbatim into a workspace test, as the existing task's own fixture does |

Each needs its pass/fail counts proven offline via a
`test_agentclinic_complaint_lifecycle_qualification.py`, mirroring
`tests/integration/test_session_phased_qualification.py` exactly:
apply each patch over `base/`, materialize the overlay, run the real
oracle over the cumulative selection, assert exact counts and named
failing checks — never fixture *content*.

## What this document does not do

**Corrected 2026-09-10.** `session.json`, the grader modules, the six
fixtures and the qualification test suite were built after this design
was written and are proven — see the note at the top of this document.
What this design still does not do: it does not authorize any live
inference. TE4's own screen step comes after the offline witnesses
exist and pass (now true) and needs its own separate authorization per
house convention (still not given). Nothing here is a claim that either
configuration will struggle with phase 4 — per the plan, difficulty
must come from real dependencies and preservation, not from picking a
task expected to favor one side.
