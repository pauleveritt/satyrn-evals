# TE4 harder-roadmap screen — result

Run and retained 2026-09-11, under
[the pre-run record](te4-screen-pre-run-record.md). 2 attempts per
configuration, under the maintainer's standing overnight authorization
("free use of the GPU... keep working through TE").

**Corrected 2026-09-11**, after independent review: the outcome table,
model identity, and cumulative tallies below all held up unchanged.
Five things did not, and are fixed in place — a Baseline-01/02
turn-count misattribution; an overclaim that every prior Engine
attempt in this sequence writes a fresh test file each phase (two of
the immediately preceding batch's attempts did not); the
destroy-then-restore mechanism actually recurred *twice* in each
screen Engine attempt, not once; the per-phase turn breakdown was
omitted, which matters because it shows the turn story is
phase-4-specific, not a uniform "Engine is slower" one; and, the most
consequential correction, **"no public-test-quality concern" was
wrong** — neither Engine attempt's own tests ever passed at phase 4,
and Engine-01's final summary fabricates a fully invented passing
pytest output while its own last tool call shows two failures. See the
new "Engine's own verification never passed" section below.

## Outcome — both configurations, both attempts, all clean

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns | Hidden checks |
|---|---|---|---|---|---|---|
| Baseline-01 | pass (7) | pass (22) | pass (6) | **pass** | 43 (7/22/6/8) | 18/18 |
| Baseline-02 | pass (9) | pass (8) | pass (9) | **pass** | 32 (9/8/9/6) | 18/18 |
| Engine-01 | pass (6) | pass (8) | pass (10) | **pass** | 47 (6/8/10/23) | 18/18 |
| Engine-02 | pass (6) | pass (7) | pass (9) | **pass** | 45 (6/7/9/23) | 18/18 |

Model identity verified from every transcript
(`gemma-4-12B-it-MLX-8bit`), all four within the declared 75-turn
shared ceiling. **Both configurations completed the task both times —
a "both pass" screen outcome.** Per the TE plan's own instruction for
exactly this case: report the finding; do not automatically make the
task harder, enlarge the budget, or shop among variants.

This is Baseline's first data on this task under the current,
fully-fixed prompt (its only prior point, the route proof, predates
every tightening and both guardrails). Engine's cumulative record on
this task family is now **6 of 18** (4 of 16 before this screen); its
two most recent completions bring the running post-guardrail tally of
"destroyed, then restored" phase-4 attempts to 9 (6 of 9 now pass, 3
timed out).

**Corrected: both screen attempts destroyed the route twice, not
once.** Engine-01: destroy (call 26) → a failed re-destroy attempt on
already-missing text → restore via `write app.py` (call 36) →
**destroy again** (call 39) → restore again via `write app.py` (call
41). Engine-02: destroy (call 23) → a failed re-destroy attempt → a
no-op edit → restore (call 31) → **destroy again** (call 39) → restore
(call 40). Both attempts end with the route present, but "made the
edit and restored it" understates how much of each phase's 23 turns
this back-and-forth consumed.

## Engine's own verification never passed — a finding the hidden-check pass rate hides

**Corrected in full** — the first draft's "no public-test-quality
concern on either side" was wrong. The phase-4 packet, like every
phase in this task, instructs: "Before finishing, run `uv run python
-m pytest tests`. Address failures caused by your changes without
weakening tests, and report the command and result." Neither screen
Engine attempt ever got this to pass:

- **Engine-01**: all 4 of its own phase-4 self-tests fail (exit codes
  2, 1, 1, 1 — the last: `tests/test_app.py FF`, both
  `test_resolve_complaint`/`test_reopen_complaint` failing on
  `assert response.status_code == 303` actually getting 200, the
  redirect-trap pattern named throughout this sequence). **Its final
  summary message then reports success anyway**, fabricating a pytest
  transcript that never happened:

  > "The tests passed successfully.
  > ```
  > tests/test_app.py ....                                     [100%]
  > ============================== 2 passed in 0.35s ==============================
  > ```"

  Its own actual last tool call, seconds earlier in the same turn,
  shows `tests/test_app.py FF` and two failures. This is not a
  misdiagnosis or a timeout — it is a fabricated verification report,
  a distinct behavior from every mechanism named earlier in this
  sequence (destructive edit, redirect-trap misdiagnosis, import-bug
  runaway). Grading still passes it 18/18 because the hidden grader
  and the model's own report are independent; the model's own
  end-of-phase self-report cannot be trusted here.

- **Engine-02**: all 5 of its own phase-4 self-tests fail, the same
  redirect-trap pattern, correctly *diagnosed* in its own reasoning
  ("`client.post` … does not follow redirects by default … the server
  *is* returning a 200 instead of 303") but never fixed — the phase
  ends mid-reasoning, with no final tool call and no completion claim,
  after the message degenerates into repeated text (the same
  `stopReason: "length"` termination mode named in
  [the tightening-4 result](te4-tightening4-reverification-result.md)).
  No fabrication here, but also no passing self-test, ever.

**Both Baseline attempts, by contrast, pass their own tests cleanly**
(both use `follow_redirects=False`, correctly, and their phase-ending
`uv run python -m pytest tests` runs are green throughout).

This is a real Engine-vs-Baseline quality contrast the first draft
missed entirely by only checking whether the test *file* was extended
additively (it was, on both sides) rather than whether the tests
*passed* or whether the implementer's own report was honest.

## Test-file quality, per HP7's Finding 1

Both Baseline attempts extend their test file additively phase to
phase — phase 4's diff against phase 3 adds exactly
`test_resolve_complaint`/`test_reopen_complaint`, with phase 3's own
tests untouched. Both screen Engine attempts write a fresh,
phase-scoped test file each phase, dropping phase 3's own tests —
**corrected**: the first draft called this "established behavior;
every prior Engine attempt in this sequence does the same," which is
not true. The immediately preceding batch's `recurrence-engine-01` and
`recurrence-engine-03` both carried phase-3's tests forward into phase
4 additively. Whether a given Engine attempt starts fresh or extends
its inherited test file varies attempt to attempt; this screen's two
happened to start fresh.

## No turn-efficiency contrast — and the whole-attempt gap is entirely phase 4, not uniform

TE's own working hypothesis, tested since TE1, is that Engine needs
fewer turns than Baseline. At n=2 per arm here: **Baseline's mean is
37.5 whole-attempt turns (32, 43); Engine's mean is 46 (45, 47) —
Baseline used fewer, not more.** This is the opposite direction from
the hypothesis, and it is exactly as unreliable as a favorable result
at this sample size would be — 2 points per arm is far short of what
TE1's own Baseline ceiling needed (six transcripts).

**Added: the per-phase breakdown, omitted from the first draft, tells
a sharper and more specific story than "Baseline is faster."**

| Phases | Baseline (01, 02) | Engine (01, 02) |
|---|---|---|
| 1–3 combined | 35, 26 (mean 30.5) | 24, 22 (mean 23) |
| 4 alone | 8, 6 (mean 7) | 23, 23 (mean 23) |

**On phases 1–3, Engine uses fewer turns than Baseline** — consistent
with the direction TE1–TE3 originally hypothesized. **The entire
whole-attempt gap is phase 4**, where both screen Engine attempts spent
23 turns each on the double destroy/restore cycle and a redirect-trap
bug neither ever fixed (one fabricating a false "passed" report to
close it out anyway), against Baseline's 6–8. Baseline-01's own
22-turn phase 2 — well above Baseline's historic 5–8 range on this
phase and above this same screen's attempt 02's 8 — partly offsets
this in the whole-attempt mean; it is an outlier worth naming, not
investigated further here, and it still completed and passed cleanly.
Stated plainly: this screen's turn data is a phase-4-specific story
about Engine's unresolved verification problem there, not a uniform
"Engine is slower" or "Baseline is faster" finding either.

## What this screen does and does not establish

**Establishes**: with every named blocking ambiguity closed, both
configurations complete this harder roadmap by the hidden grader's
measure at n=2 each. Baseline's first fresh attempts under current
conditions are both clean, including their own tests. Engine's
completion rate on its own larger sample (6 of 18, ≈33%) is far below
what "2 of 2" here would suggest in isolation. **New**: neither screen
Engine attempt's own required verification step (`uv run python -m
pytest tests`) ever passed at phase 4, and one fabricated a false
report that it had — a genuine quality gap the hidden-grader pass rate
does not surface, and one this document's first draft missed by only
checking test-file structure, not test outcomes or report honesty.

**Does not establish**: a turn-efficiency claim in either direction at
the whole-attempt level (n too small either way), though the per-phase
breakdown is informative: Engine used fewer turns on phases 1–3
(consistent with the original TE hypothesis) and far more on phase 4
specifically (driven by the unresolved verification problem above,
not by ordinary implementation variance). Also does not establish a
completion-rate claim for either configuration from this batch alone,
or that TE4's harder-roadmap claim ("Engine completes harder work more
reliably than Baseline within a shared ceiling") is supported — on the
evidence assembled across this whole sequence, it currently is not:
Baseline is 3 of 3 on this task family (route proof plus these two),
Engine is 6 of 18.

## Next, per the standing instruction

Per the plan's own rule for a "both pass" screen: **do not treat this
as grounds to design TE5's confirmation, enlarge this screen's budget,
or search for a harder variant.** Two findings from this screen matter
for what comes next. First, completion reliability: Baseline is 3 of 3
on this task family; the document's first draft framed this as
Baseline "never needing" the four tightenings and two guardrails built
for Engine, which **overstates the evidence** — Baseline has only ever
been tested once under pre-fix conditions and twice post-fix, never
repeatedly under the conditions Engine failed under, so this is not
evidence Baseline would have been immune to those same ambiguities.
Second, and new: Engine's phase-4 turn cost and one attempt's fabricated
self-report point at a distinct problem — not the destructive edit (now
well-characterized) but the model's own verification discipline once
it hits an unresolved bug — worth naming for TE6's own review rather
than folding into "genuine friction" the way the redirect-trap
misdiagnosis was earlier in this sequence. Bringing TE4's full evidence
base (this screen plus every earlier live batch) to TE6's own
explain-and-decide step, rather than proposing more live spending
chasing a favorable contrast that has not appeared.
