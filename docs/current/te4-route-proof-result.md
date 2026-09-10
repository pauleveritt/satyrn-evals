# TE4 route proof — result

Run and retained 2026-09-10, under
[the pre-run record](te4-route-proof-pre-run-record.md). One attempt per
configuration, as frozen. No further inference beyond what that record
authorized.

## Completion

| Attempt | Outcome |
|---|---|
| Baseline-01 | **COMPLETE** — all 4 phases ran; phases 1–3 pass (4/4, 10/10, 13/13); phase 4 **fails hidden grading, 17/18** |
| Engine-01 | **VOIDED** — phase-2-board's implementer exceeded the 600s timeout; `check_chain`: "implementer window was never observed" |

## Finding 1: Baseline's phase-4 failure looks like a grader defect, not a real requirement violation

Baseline-01's only failing check is
`test_complaint_identity_is_stable_and_keyword_only`, specifically its
assertion that `id`/`status` are declared `kw_only`. The model's actual
`models.py`:

```python
@dataclass
class Complaint:
    agent_name: str
    text: str
    id: int = field(default_factory=get_next_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "open"
```

`id`/`status` are plain fields with defaults, placed *after* the two
required fields — not `kw_only`, but positionally valid all the same,
because every field after `agent_name`/`text` carries a default. The
actual behavioral check this was meant to protect —
`test_complaint_model_contract_is_preserved`, which calls
`Complaint("first", "First complaint")` positionally — **passed**. So
did every resolve/reopen/ordering/seed-identity check. The implementation
is correct; it just satisfies "positional construction still works" by
field ordering instead of by `kw_only`. **Corrected attribution**: the
[design doc](te4-harder-roadmap-design.md) itself *prescribed* the
`kw_only` assertion as "the central preservation proof" (its own
wording) — it did not name this as one of two valid answers. It was
[`QUALIFICATION-NOTE.md`](../../src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/QUALIFICATION-NOTE.md)
that later flagged, correctly, that "`kw_only` is not itself a prompt
line" and left it an open question — this transcript is what actually
exercised that open question and found it real.

**This is a fixture defect, found by the first real transcript ever run
against it — reported, not silently patched.** The check's assertion
order means it never reaches the behavioral part: `field_map["id"]
.kw_only is True` fails before the `Complaint("first", "First
complaint")` call two lines later ever runs, so the check effectively
tests only the mechanism, not the behavior it exists to protect. The
fix is to delete the two `kw_only` assertions and keep (optionally
strengthen, e.g. asserting `first.agent_name == "first"`) the
positional-construction lines already present — the same shape
`test_complaint_model_contract_is_preserved` already uses.

**Fixed 2026-09-10.** The two `kw_only` assertions are removed;
`test_complaint_identity_is_stable_and_keyword_only` now also asserts
`first.agent_name`/`first.text`. The qualification suite (8 tests)
still passes in full, `known-broken` still fails the same way (its
`id` field has no default at all, a behavioral break the corrected
check still catches), and Baseline-01's own real `models.py` — the
concrete case that motivated this — now re-grades 18/18 through
`satyrn_evals.grade` directly. Until this landed,
least one valid solution.

## Finding 2: Engine's phase-2-board timeout reproduced, same signature, second independent occurrence

Engine-01 timed out on **phase-2-board** — a phase byte-identical to
`agentclinic-session-phased`'s own phase 2, unrelated to anything new
in phase 4, which this attempt never reached. The failure shape matches
[the TE2/HP8 screen's Engine-01](te2-hp8-screen-result.md#the-runaway-loop-engine-01-phase-2)
closely enough to name as the same pathology, not a coincidence:

| | TE2/HP8's Engine-01 (phase-2-board) | This run's Engine-01 (phase-2-board) |
|---|---|---|
| Turns before timeout | 65 | 61 |
| Tool executions | 64 | 60 |
| `write app.py` calls | 60 | 56 |
| Byte-identical repeats | 58 | 53 |
| Converged after call # | 3 | 4 |
| Assistant text on any turn | none | none |
| `run_self_test` invoked | never | never |

Both attempts stall on the same phase, both converge to a stable
`app.py` and then rewrite it dozens of times unchanged, both produce
zero assistant text and never invoke `run_self_test`, both are killed
only by the wall-clock timeout since `turn_budget`/`tool_call_budget`
are declared but never enforced. **Stated with its actual denominator**:
Engine has now run phase-2-board live four times total — HP7 (8 turns,
passed), TE2/HP8's Engine-02 (9 turns, passed), TE2/HP8's Engine-01
(this exact runaway), and this run (this exact runaway). **2 of 4
Engine attempts at phase-2-board have run away; the other 2 completed
it in 8–9 turns.** Baseline has completed the same phase 9 of 9 times,
5–8 turns each — the runaway is specific to the Engine arm, not to
phase-2-board's difficulty in general. Whatever the cause, it does not
appear specific to `agentclinic-complaint-lifecycle` — phase-2-board is
verbatim-identical prompt text on both tasks, and the first occurrence
predates this task's existence.

## Turn counts, `turn_ledger`, whole-attempt unit

| Attempt | Started | Ended (normal) | Open at capture end |
|---|---|---|---|
| Baseline-01 | 28 | 28 | 0 |
| Engine-01 (voided) | 67 | 66 | 1 |

Baseline-01 per phase: 9 / 8 / 5 / 6. Its whole-attempt total (28) is
inside the 3-phase task's Baseline range on record (15–41 across eight
transcripts: 15/20/15/25/22/20 from TE1's own six, plus TE2/HP8's 20
and 41) despite carrying a fourth phase — but above TE1's own checked
range (15–25, from six transcripts before TE2/HP8 ran). Descriptive
only, not evidence either way about phase 4's own cost, since this is
one attempt.

Engine-01 per phase: 6 (phase 1) / 61 (phase 2, timed out; phase 4
never reached). Not usable for any ceiling figure — it is the same
runaway shape as before, not a representative cost for phase-2-board
when it completes normally (HP7 and TE2/HP8's Engine-02 both completed
phase 2 in 8–9 turns). **Engine's handling of phase 4 remains entirely
unproven live** — across every Engine attempt run against this task
family, none has ever reached it.

## Preconditions, as retained

**Model identity, from each transcript's own field:** every `turn_end`
in Baseline-01 (28 of 28) and Engine-01 (66 of 66) reads
`gemma-4-12B-it-MLX-8bit`, the pinned model — none observed otherwise.

**Pinned versions:** both attempts' receipts show `fastapi==0.115.10`,
`turbohtml==1.5.0`, `pytest==8.3.4`, unchanged.

**Commit this run started from:** `127e254` (the last commit before
this record), with `scripts/hp7_live_route.py`'s `--task`/
`--task-tree-sha256` generalization already applied but **uncommitted**
at run time. The pre-run record's own "What this run retains" section
said that change should "land first, under its own small review" or be
a one-off script; neither happened — it ran uncommitted, and this
review is after the fact, not before. The task tree itself (digest
`aa19f92e...`) was unmodified since that commit, so the drift check
was live and meaningful regardless.

**Not verified or not recorded:** whether the offline qualification
suite was re-run on this exact commit immediately before the live
attempts (it was run earlier the same session on the same code, not
re-confirmed at this specific moment); machine quietness; pi's own
version. Named here rather than silently assumed satisfied.

**Task materialization and grading, live:** confirmed working through
phases 1–4 for Baseline and phases 1–2 for Engine. **Engine's handling
of phase 4 is unproven live** — no Engine attempt across this task's
entire history has reached it.

## What this means for the shared turn ceiling

**Not declared here.** The pre-run record's own instruction was not to
pick a number if either attempt's completion status would make it look
arbitrary — this is exactly that case. Engine has now completed
`agentclinic-complaint-lifecycle` zero times across the only attempt
run against it; Baseline's one completed attempt (28 turns) is the sole
data point, and one point does not check a ceiling against "every real
transcript on record" the way TE1's 40 was checked. A ceiling proposal
for this task needs at least one Engine completion to reason about, not
just an implementer-side extrapolation from the 3-phase figures.

## Recommendation

**Do not move to TE4's two-per-configuration screen next.** Spending it
now would very likely spend both Engine attempts re-hitting the same
phase-2-board pathology this route proof and the TE2/HP8 screen have
now both independently produced, at real cost, without new information
— the thing the TE plan calls "search[ing] for a favorable task" from
the other direction: running to try to get past a wall rather than
address it. The phase-2-board pathology is the higher-priority open
item; investigating it (offline, against the two retained transcripts
already in hand, no new inference needed) was proposed after TE2/HP8's
own correction and not yet done. Fixing the grader's `kw_only`
assertion is small and separate, and worth doing regardless of the
above.

Neither finding changes TE4's own status: no completion-reliability or
turn-efficiency claim was ever on the table for this bounded proof, and
none is claimed here. **TE4's screen is not proposed or authorized by
this result.**

**Follow-up, 2026-09-10.** The recommended offline investigation is
done — see
[the phase-2-board runaway investigation](phase-2-board-runaway-investigation.md):
a specific, reproducible mechanism (a destructive `edit` that deletes
the phase-1 home route, converging on a file with an import bug never
caught because `run_self_test` is never called), found by comparing
this attempt against the three other real Engine phase-2-board
transcripts on record.
