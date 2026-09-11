# TE4 guardrail re-verification — result

Run and retained 2026-09-10, under
[the pre-run record](te4-guardrail-reverification-pre-run-record.md). 2
Engine attempts, as authorized. No further inference beyond what that
record authorized.

## Outcome

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns |
|---|---|---|---|---|---|
| Engine-01 | pass | pass | pass | **rejected** (hidden grader) | 46 (6/9/7/24) |
| Engine-02 | pass | pass | pass | **voided** (timeout) | 44 started, 1 open |

**Both attempts reached phase 4 for the first time in this task's
history**, on either route. Both attempts' phases 1–3 passed cleanly.
Neither completed the full task. Model identity confirmed
`gemma-4-12B-it-MLX-8bit` on every turn of both transcripts.

## The guardrail holds: 5 of 5 clean since adoption

Phase-2-board passed cleanly in both attempts — no destructive edit,
no runaway. Combined with the candidate probe's own 3 of 3, that is
**5 of 5 clean Engine phase-2-board attempts since the guardrail
landed**, against 2 of 4 clean before it. This run adds no new
evidence *against* the guardrail; it extends the record the candidate
already established.

## Phase 4 failed twice, for two different real reasons — neither a repeat of the phase-2-board pathology

**Engine-01: a real, substantive grading rejection**, not a timeout.
16 of 18 hidden checks passed; the two that failed are exactly what
`known-broken.patch` was built to catch:
`test_complaint_model_contract_is_preserved` and
`test_complaint_identity_is_stable_and_keyword_only`. The retained
`models.py`:

```python
@dataclass
class Complaint:
    id: int
    agent_name: str
    text: str
    ...
```

`id` is declared as a required positional field *before*
`agent_name`/`text` — precisely the ambiguity named as an open,
unprobed risk in
[the sibling task's own `QUALIFICATION-NOTE.md`](../../src/satyrn_evals/tasks/agentclinic-session-phased/QUALIFICATION-NOTE.md)
and carried forward as a named risk in
[the TE4 design](te4-harder-roadmap-design.md). This is the first live
observation of a model actually choosing that reading. The phase-4
prompt says the field must be "assigned once... unique... never
recomputed from its position" but never says where in the field order
it goes — a real prompt gap, not a grader defect (the earlier `kw_only`
issue was the check demanding one specific *mechanism*; this check
demands the actual *behavior*, and the behavior genuinely broke).

**Engine-02: a real self-test failure, followed by a misdiagnosed
fix attempt, then a timeout** — not the destructive-edit-and-repeat
signature (phase-2-board's own pathology). The implementer's own
`tests/test_app.py`:

```python
response = client.post(f"/complaints/{original_id}/resolve")
assert response.status_code == 303
```

omits `follow_redirects=False` — the exact "known semantic trap" this
task family's own grader code has warned about since before this
session
(`grader_tests/test_phase3_add.py`'s docstring: "TestClient follows
redirects by default, so a test for the 303 MUST pass
follow_redirects=False or it will silently assert against the followed
page"). `run_self_test` correctly caught it (`exit code 1`,
`assert 200 == 303`). The implementer then tried adding a
`request: Request` parameter to the route handlers — twice, with
identical `oldText`/`newText`, so the second attempt was reported "No
changes made... produced identical content" — a fix that does not
address the actual cause. The transcript ends mid-turn at the 600s
timeout, still on the wrong diagnosis. This is a real recovery
attempt that ran out of time, not a degenerate write-loop: 20 varied
tool calls (`read`/`edit`/`write`/`run_self_test`), zero repeated
identical writes.

## What this does and does not establish

**Does not establish** that Engine reliably completes this task — 0 of
2 in this run. **Does establish** that the phase-2-board fix is
holding under real conditions (now including the fourth phase's
presence, not just the isolated two-phase probe), and that phase 4
carries at least two distinct, real sources of friction: a genuine
prompt ambiguity (id field ordering) and a known trap this model can
still fall into even when self-test correctly catches it (redirect
following in its own test). Neither failure resembles the phase-2-board
pathology; naming them the same thing would be wrong.

**No turn ceiling is proposed.** Per the pre-run record's own
condition, Engine has still completed the full task zero times — one
rejected, one voided, neither an ordinary clean pass to check a number
against.

## What happens next — not decided here

Two candidate follow-ups, named, neither implemented or authorized:

1. Tighten the phase-4 prompt to specify `id` comes after
   `agent_name`/`text` (a third tightening in this family's pattern,
   like the two already documented in the sibling task's own
   `QUALIFICATION-NOTE.md`) — or accept the ambiguity as real,
   evidenced difficulty this harder roadmap is allowed to have, per
   the TE4 design's own instruction that difficulty should come from
   real dependencies, not misleading instructions. This one reads
   closer to "misleading instructions" than "meaningful dependency."
2. Nothing to fix about Engine-02's failure — the self-test loop
   worked as designed (caught a real bug); the model's own diagnosis
   was wrong. This is exactly the kind of harder-roadmap friction TE4
   exists to observe, not an infrastructure gap.

TE4's own two-per-configuration screen is still not proposed or
authorized by this result.

**Follow-up, 2026-09-10.** Item 1 is done — see the task's own
[`QUALIFICATION-NOTE.md`](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md),
"Tightening 3." Item 2 stands as written; nothing was changed for it.
This section's own numbers (Engine-01's transcript, its digests) are
frozen for the pre-tightening prompt this run actually used — not
retroactively edited.
