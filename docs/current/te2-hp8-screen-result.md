# TE2/HP8 screen — result

Run and retained 2026-09-10, under
[the pre-run record](te2-hp8-screen-pre-run-record.md). Reports the four
authorized attempts: 2 Baseline, 2 Engine. No further inference beyond
what that record authorized. **Corrected 2026-09-10** after independent
review found the first draft's turn accounting, self-test narrative and
budget framing wrong or incomplete; corrections are noted inline.

## Completion (frozen question 1)

| Attempt | Outcome |
|---|---|
| Baseline-01 | **COMPLETE** — 3/3 phases pass (4/4, 10/10, 13/13 hidden checks) |
| Baseline-02 | **COMPLETE** — 3/3 phases pass (4/4, 10/10, 13/13 hidden checks) |
| Engine-01 | **VOIDED** — phase-2-board's implementer exceeded the 600s timeout; the adapter recorded this as `refused` (its only non-delivered outcome — not a model refusal); `check_chain` reported "implementer window was never observed," the pre-run record's own named voiding condition |
| Engine-02 | **COMPLETE** — 3/3 phases pass (4/4, 10/10, 13/13 hidden checks), `check_chain` findings: 0 |

Baseline completed both attempts. Engine completed one of two; the other
is reported voided, not excluded or silently replaced, per the record's
own rule. The frozen `n=2` denominator per configuration is unchanged —
no replacement attempt was separately authorized. Cumulative preservation
is read from each receipt's `executed_test_ids` (phase 1's four selectors
re-run at phases 2 and 3, all still passing); `preservation_verdict` is
`None` on every Baseline step because this task declares no
`base_preservation_selectors`, not because preservation went unchecked.

**Note on the label, corrected.** The voiding rule targets an unobserved
implementer window — `ChainRecord`'s structured phase entry has no
mutation attribution for phase-2-board. That is not the same as missing
capture: the raw transcript retains the entire window (65 turns, 64 tool
executions, 586s before the 600s kill) — see "Turn counts" below. Both
readings of the attempt agree on **completion**: under the frozen label
the `n=2` denominator stays 2 and Engine delivered 1; under the TE plan's
own rule for confirmations that "ordinary model refusals, loop behavior,
timeouts and failed repairs remain counted outcomes"
([plan](engine-turn-efficiency-plan.md), "Confirmation design and
spending"), it is an ordinary failed attempt, still 1 of 2 — same
answer either way. The readings **diverge on turn expenditure**, handled
in "Turn counts" below rather than glossed over.

**Answer:** contradicted for Engine at this `n`.

## Turn counts (frozen question 2), `turn_ledger`, whole-attempt unit

| Attempt | Started | Ended (normal) | Open at capture end |
|---|---|---|---|
| Baseline-01 | 20 | 20 | 0 |
| Baseline-02 | 41 | 41 | 0 |
| Engine-01 (voided) | 71 | 70 | 1 |
| Engine-02 | 31 | 31 | 0 |

The "open at capture end" row is a state of one of the 71 started turns
(the timeout truncated the stream mid-turn) — not an additional turn on
top of 71. **Corrected**: the first draft's per-phase table and its "69
tool calls" both misattributed whole-attempt totals to phase 2 alone.
Recomputed per phase, implementer role only (the orchestrator role is
null by design — no orchestrating model runs in Phase HP's route):

| Attempt | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Baseline-01 | 9 started/9 ended | 6/6 | 5/5 |
| Baseline-02 | 7/7 | 8/8 | 26/26 |
| Engine-01 (voided) | 6/6 | 65 started/64 ended/1 open | — |
| Engine-02 | 8/8 | 9/9 | 14/14 |

Engine-01's phase 2 alone: 65 started turns, 64 tool executions (60
`write app.py`, 58 of them byte-identical after the third call
converged; see "The runaway loop," below). Two of the four attempts
separately show a repair loop on the same requirement — the
`/complaints` POST route's 303 redirect. Baseline-02's phase 3 (26
turns) ran `pytest` five times, hit two collection errors and two
assertion failures on the 303 status before passing. Engine-02's phase 3
(14 turns) hit one failing `run_self_test` on the same requirement and
recovered (see "Self-test recovery," below). Engine-01's phase 2 is a
different shape entirely — a runaway, not a repair loop, detailed below.
Descriptive only; none of this supports a mechanism claim on its own.

**Two legitimate readings, reported separately rather than picking one:**

- **Completed-work comparison** (only attempts that finished): Baseline's
  average is 30.5 (20, 41); Engine-02's is 31 — one point inside
  Baseline's own range, not fewer. HP7's earlier live run (22 turns) is
  the only other Engine data point on this route/task, also inside
  range. This is the right comparison for "did Engine finish the task in
  fewer turns," since Engine-01 never finished.
- **All-launched-attempts expenditure**, per the TE plan's own rule that
  ordinary failed attempts stay in the denominator: Baseline's average is
  still 30.5; Engine's is `(71 + 31) / 2 = 51`. Descriptive of what was
  actually spent, not a superiority estimate — Engine-01's 71 turns
  produced one accepted phase and one timeout, not completed work.

Baseline-02's 41 also exceeds TE1's frozen 40-turn whole-attempt ceiling
by one turn. Engine-01's 65-turn phase 2 alone exceeds it by 25 turns,
and the packet's own `turn_budget: 20` / `tool_call_budget: 30` were
declared but never enforced (`declaration_ledger` reports both
`declared_not_applied` on every phase of both Engine attempts) — see
"The ceiling was not enforced," below.

**Answer:** inconclusive on the completed-work comparison (one point
inside Baseline's range, not fewer); unfavorable to Engine on
all-launched-attempts expenditure (51 vs. 30.5). Neither reading
supports a turn-efficiency claim for Engine.

## The runaway loop, Engine-01 phase 2

**Corrected**: the first draft reported "69 tool calls" for this phase;
the true figure is 64 (69 was the whole-attempt total, phases 1 and 2
combined). Of phase 2's 64 tool executions, 60 targeted `app.py` with
`write` (one further `edit` also touched `app.py`; `models.py`,
`templates/base.html` and `templates/home.html` were each written once).
The first two `write app.py` calls produced distinct, evolving content
(429 and 384 bytes); starting with the third call, every subsequent
`write app.py` — 58 calls in a row — sent byte-identical 657-byte
content, each answered with a bare `Successfully wrote to app.py`. No
assistant turn in this phase produced any text content; every one ended
`stopReason: toolUse`. `templates/complaints.html` and `tests/test_app.py`
— both required by the phase-2 packet — were never written, and
`run_self_test` was never invoked. The 600s wall-clock timeout, not any
turn or tool-call budget, ended the phase.

**One candidate contributing factor, not a diagnosed root cause**: the
`write` tool's own result never signals whether content actually
changed — unlike `edit`, which explicitly reports "No changes made...
produced identical content" (observed in Engine-02's phase 3, next
section). A model that has, for whatever reason, stopped producing
grounding text and is re-emitting the same tool call gets no
differential feedback from `write` telling it so. This screen's retained
artifacts do not include the per-turn model input/context, so the
underlying cause of the repetition itself (a sampling degeneracy, a
context-construction issue, or something else) is not diagnosable from
what's retained here — only the symptom is. **Not implemented and not
proposed as a fix**: any remedy needs its own narrow, separately
authorized test, per the plan's own instruction not to add a repeat
cutoff pre-emptively ("Do not add a harness repeat cutoff when recovery
from repetition is the question,"
[plan](engine-turn-efficiency-plan.md), TE1). Whether a `write`-side
"no changes" signal would actually help, or would instead be
indistinguishable from Engine-02's legitimate no-op edits below, is
exactly the kind of question that authorized test would need to answer.

## The ceiling was not enforced

TE1 froze a 40-turn whole-attempt ceiling from Baseline evidence,
"checked, not asserted" against one Engine data point (HP7, 22 turns).
This screen adds a second Engine data point, and it does not hold to the
same margin: Engine-01's phase 2 alone ran 65 turns — 25 over the entire
ceiling — with the packet's declared `turn_budget: 20` /
`tool_call_budget: 30` never enforced. This confirms, rather than
contradicts, the TE plan's own prior warning that "a textual packet
budget is not enforcement." **The ceiling holds for attempts that
complete normally** (HP7 22, Engine-02 31, both Baseline attempts); **it
does not hold, and nothing currently enforces it, once a route loops.**
[`engine-turn-efficiency-plan.md`](engine-turn-efficiency-plan.md) and
`ROADMAP.md` are corrected accordingly — TE1's ceiling-check exit
criterion is qualified, not simply "closed," pending whatever this
screen's runaway loop is diagnosed to be.

## Public-test-quality review (every attempt, phase to phase, regardless of outcome)

Each attempt's cumulative-from-base patch for `tests/test_app.py` was
diffed phase to phase and the added test function names/bodies compared.

- **Baseline-01**: purely additive and verbatim —
  `test_read_main` → `+test_read_complaints` → `+test_create_complaint`.
  No finding.
- **Baseline-02**: purely additive and verbatim —
  `test_home_page` → `+test_complaints_page` →
  `+test_post_complaint`/`test_complaint_added`. No finding.
- **Engine-01**: only phase-1 reached (`test_read_home`, 1 test); no
  cross-phase comparison is possible for a voided attempt.
- **Engine-02**: **finding**, structurally similar to HP7's own Finding
  1 but with a materially different result: **no assertion content was
  lost.** Phase 1's `test_home_page` becomes phase 2's `test_home` —
  identical body and assertions, renamed. Phase 2's `test_complaints`
  becomes phase 3's `test_complaints_list` — identical body, renamed.
  HP7 lost coverage between checkpoints; this attempt preserved it. The
  finding is narrowly syntactic — the implementer's own tool calls show
  it never reads `tests/test_app.py` before overwriting it in phase 2 or
  phase 3, so the checkpoint pattern is "regenerate under a new name"
  rather than "extend in place" — reported per the pre-run record's own
  instruction, regardless of the hidden-oracle pass count. **This is not
  evidence that required behavior deteriorated**; it is a separate,
  independent observation from the self-test recovery below, not
  something the recovery offsets or cancels out.

## Self-test recovery, observed live for the first time — corrected

The first draft of this section reversed the failure and misdescribed
the recovery. Corrected against the retained transcript:

[HP7's result](hp7-live-route-proof-result.md) named the failure →
correction → passing-retest half of the self-test loop as never yet
observed live. This screen's Engine-02 phase 3 exercised it. Before the
first `run_self_test`, `app.py` already implemented the POST route with
`RedirectResponse(url="/complaints", status_code=303)` — correct from
its first write. The first `run_self_test` failed: `test_create_complaint`
**asserted `303`, received `200`**
(`assert response.status_code == 303` / `assert 200 == 303`), because
the test's first draft called `client.post(...)` without
`follow_redirects=False`, so `TestClient` followed the redirect and
reported the final page's status rather than the redirect itself. The
implementer then made four `edit app.py` attempts: one added an unused
`request: Request` parameter to the handler (a real but functionally
irrelevant change — it does not touch the redirect or its status code),
and two more were no-ops that the tool itself reported as "No changes
made... produced identical content." **No app.py edit addressed the
actual cause.** The implementer then rewrote `tests/test_app.py` adding
`follow_redirects=False`, and the second `run_self_test` passed (`3
passed`).

This is a genuine, live observation of failure → correction →
passing-retest — closing the gap HP7's result named open. It is **not**
evidence of the implementer rescuing a broken application: the
application was correct throughout, and three of the four
recovery-phase edits were unnecessary or ineffective activity that
happened not to cost the attempt its completion. Both observations are
retained together, not folded into a single "recovery" headline.

## Preconditions, as retained

**Model identity, from each transcript's own field (precondition 4):**
every `message.model` across all four retained transcripts (426 messages
total) reads `gemma-4-12B-it-MLX-8bit`, the pinned model — none observed
otherwise.

**Pinned versions (precondition 1):** every receipt shows `fastapi==
0.115.10`, `turbohtml==1.5.0`, `pytest==8.3.4`, unchanged.

**Live completion, never a listing (precondition 2), and machine state
(precondition 3):** not verifiable from any artifact this screen
retained — neither is written to a session record, chain record, or
transcript. Named here rather than silently assumed satisfied. pi's own
version (`0.85.1` per the pre-run record) is likewise not written to any
retained file for this screen.

**Orchestrator role:** null throughout on the Engine route, by design —
Phase HP runs no orchestrating model, so the implementer counts above
are the whole-attempt total.

## What this screen decides

Completion is contradicted for Engine at `n=2` under either reading of
the voided attempt (see "Note on the label" above). Turn efficiency is
inconclusive on the completed-work comparison and unfavorable on
all-launched-attempts expenditure — neither supports a turn-efficiency
claim. This screen also produced two independent, separately retained
findings worth carrying forward on their own terms, not netted against
each other: a genuine runaway loop in Engine-01 (25 turns over the whole
ceiling in one phase, unenforced, with a candidate contributing factor
identified but not diagnosed), and a genuine live observation of
self-test failure-recovery in Engine-02 (closing a gap HP7 left open,
with no loss of test coverage, alongside real but unnecessary repair
activity). This is a screen, not a confirmation — no joint statistical
decision is computed here, and four attempts do not distinguish a
pattern from a fluke much better than `n=1` does.

**TE3 is not pursued from this screen, and not reopened without new
evidence** — not formally closed: the runaway loop's cause is
undiagnosed, and a narrow, separately authorized amended-treatment
screen could put the easy claim back on the table on its own new
grounds later. That is a distinct future decision, not a reason to hold
this one open as active work; an unfavorable screen is not license to
re-run it, per the pre-run record's own instruction. **TE4 (the
harder-roadmap claim) is not addressed by this screen** under the TE
plan's own rule that a negative easy-work result does not by itself
rule out the harder claim; its offline scoping starts separately (see
`ROADMAP.md`). The runaway loop remains worth investigating on its own,
offline, against retained evidence. Any further live work on this pair
— including a narrow test of a candidate remedy for the runaway loop —
needs its own explicit proposal and authorization.

## What this run did not close

Same named gap as HP7's result: `ChainRecord`'s own cost fields remain
unpopulated on the Engine route. Turn totals above are computed from
each attempt's real retained transcript via `turn_ledger.count_turns`,
not from a cost field neither route populates identically — this is a
reconciliation, not a schema project, per house instruction.
