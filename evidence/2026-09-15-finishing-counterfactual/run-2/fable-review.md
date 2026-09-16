# Deep review: the finishing counterfactual's "not-the-lever" finding

Fable, 2026-09-15. Read-only. Scripts and outputs under `evidence/` beside this file (`audit.py` → `audit.json`/`audit.md`; `trajectory.py` → `trajectory.json` (every reconstructed worktree graded at every turn); `triggers.py` → `triggers.md`; `serverlog.py`; `q3stats.py` → `q3stats.md`). Cell ids are the six-digit attempt suffixes. Grades ran under `evidence/grades/` (no pytest config above it), replay trees under `evidence/work/`; the repository, `~/satyrn-runs` and the committed outputs were not touched.

## Summary and recommendation (one screen)

**The pre-registered instrument was applied correctly, but its own conservative gates decided the result. The honest verdict is not "finishing is not the lever"; it is "undetermined by the pre-registered rules; by inspection, one rescue on docs-linter, which under amendment 7.1 is *Verify on clean tasks* — and either way the effect is too small and too concentrated to build a release on."**

1. **The only would-be rescue is real.** docs-linter 970283 reaches a hidden-suite pass at turn 39 (27,773 tokens) and stays passing to the end (`trajectory.json`); its own-green trigger is turn 40 at 27,892 tokens. It was withheld on two grounds, and both are false positives of the lexical rules, not evidence of a write the replay missed: the three "skipped bash writers" at turns 29, 37 and 38 are (29) a `cp` *from* the source file to `/tmp` plus a `write_text` into a `mkdtemp()` directory, and (37, 38) a python patch of `tools/lint_docs.py` that the *same command* restores from its backup two lines later (`cp /tmp/lint_docs.bak tools/lint_docs.py`); the transcript confirms the restore (the turn-39 `edit` anchor matches text the patch would have split, and the turn-40 pytest output carries none of the inserted `DBG` stderr lines). Replaying those commands segment by segment (`trajectory.py`, `ext` mode) reproduces the same pass. The 21 "unverified-rescue" commands are read-only by inspection (`uv run python - <<EOF` scripts that build temp trees and call `check()`, `find … __pycache__ … rm -rf`, `grep`, `md5`, `dis`). The Engine-arm docs-linter cell 859943 is the same story (pass at its trigger, turn 34 / 27,954 tokens; the 11 withheld commands are `ls`, `cat … 2>/dev/null`, `wc`, `xxd`, `od`, read-only `python3 -c` scans).
2. **The other two triggered budget-shaped cells are not finishing failures, and their "own-green" is not what it looks like.** 519278's green grades `unavailable` because turn 15 edited `errors.py`, outside `source_paths` (the run-record-gate allowlist trap; the filtered patch is also unavailable — `run_record.py` imports the class from `errors.py`). 028222's green grades `fail` on the five `load_run_record` refusal tests (the prompt-ambiguity trap); every reconstructed turn of every run-record-gate cell fails or is unavailable. 147562's green at turn 32 (30,992 tokens) is `unavailable` because turn 9 edited `pyproject.toml`; the filtered patch fails one test (the spec-cap rule). In 082295 (depth-3) the green is the public suite at 12/13 hidden. So "own-green is a weak signal" is true of these cells only in the sense that a green *public* suite cannot see an allowlist rejection or a hidden structural expectation — which release one already named as task defects, not ceilings.
3. **The counting rules that decided the result.** Ruling 11's `_PY_WRITE` + `mentions_source` heuristic (any `write_text(` in a command that also names the source file), Ruling 12 (skips count *through* the trigger turn), and 7.4's read-only list (which rejects `2>/dev/null`, `od`, `xxd`, `md5`, `python3 -c`, `for` loops, `which`) made 8 of 24 cells unmeasured; of 151 unverified bash commands through the triggers, 30 fail only on `2>/dev/null`. None of these rules was chosen to tilt the result, and all were recorded before the run, but together they guaranteed that a rescue on a self-hosted task — where a 9B pokes at the tree with python one-liners — would almost never be *counted*. The guard-prefixes floor task ran **zero** test commands in 8 of 8 cells, so no own-green rule can touch it; its `insufficient` comes from three replay fidelity misses (python-heredoc writes to `guard.py`) and says nothing about harm.
4. **Alternative triggers do not change the picture** (`triggers.md`, section 2): every green-based rule finds the same single docs-linter rescue and no other; the "last green within budget" and the oracle "first hidden-pass turn" add nothing on the decision cells. The only additional pass-state anywhere is the 2026-09-14 run-record-gate cell 511653 (pass from turn 39, 28.2k; last green turn 47 at 31.4k), on the since-fixed prompt; the two 2026-09-14 review-script cells that "rescue" under every rule are manifest drift (`PROVENANCE.md`), not finishing (section 2). Harm is zero under every rule on the 12 floor cells with triggers (7/7 review-script and depth-2 triggers grade pass).
5. **What this means for R0.** Finishing is a real but small class: 2 of 5 docs-linter cells across both arms reached a within-budget pass-state and overran (plus 511653 on the old prompt). It is Engine-addressable, but on one task whose Baseline already passes 1/4; at n = 12 with Baseline 0.25 and Engine 0.5, power is 0.26. depth-3 and run-record-gate are information- and ambiguity-bound at every turn. No Engine-addressable class dominates the current ceiling set because the ceiling set has two task defects and one budget-edge task.

**Recommendation (details in section 4):** record the decision as *Verify* under 7.1 with the by-inspection measurement and the pre-registered `not-the-lever` side by side (the spec's own "bug found afterwards" clause); do **not** build a finish-on-green Engine on this evidence; do not run a GPU night on the current ceiling set. Spend the next day on the harness and task fixes R0 constraints §1 already require (per-turn cap, harvested tripped worktrees, fixed R1 rung and run-record-gate prompt, tool parity), then one **diagnostic-only** Baseline night over 3–4 validity-checked build tasks at n = 6 (~4 GPU-h at the measured k = 3) to classify constraints — and let *that* decide whether a claim exists. If the calendar does not allow that, ship the Engine as a product with honest before/after numbers and no ceiling claim; that is a legitimate end to the eval track.

---

## 1. Is the finding sound?

### 1.1 The instrument reproduces, and the trigger definition matches the transcripts

`audit.py` re-derives every trigger from the transcripts using the committed pure functions and, independently of bash replay, finds the same 10 decision triggers at the same turns and token counts (`audit.md`). The `UsageCounter` budget check, the pytest summary-line parser and the "first green after the first source edit" search all behave as the plan's Rulings say.

Two definitional weaknesses, both pre-registered and both neutral in effect on the decision cells:

- **A green single-test run is a "green."** 511653's own-green (turn 34) is `pytest "…::test_gate_rejects_empty_stop_rule"` — one test passing while 33 others in the same file fail (turn 33). The spec's definition ("at least one pass and no failed count") admits it. On the decision cells the first greens are whole-file or whole-suite runs, so nothing turns on it.
- **The public suite is green before the first source edit on the self-hosted tasks.** 028222 (turn 8, 38 passed) and 147562 (turn 7, 1,474 passed) ran green suites before writing any code; the tasks add new tests, so "green" carries information only about the model's own test file. The "after the first source edit" clause handles this correctly.

### 1.2 The 8 unmeasured cells, cell by cell

| cell | reason recorded | what the flagged commands actually do | measurable? | verdict at trigger |
|---|---|---|---|---|
| 970283 docs-linter | skipped writers 29, 37, 38; unverified-rescue ×21 | t29: `cp tools/lint_docs.py /tmp/lint_docs.bak` + `write_text` into `mkdtemp()`; t37/t38: python patch of `lint_docs.py` **restored by `cp /tmp/lint_docs.bak tools/lint_docs.py` in the same command**; the rest read-only | yes, by inspection and by segment-wise replay (`ext`) | **pass** (turn 39–48 all pass) |
| 519278 run-record-gate | skipped writers 29–31 | t29/t30: BSD `sed -i 's/…/g' file` → "undefined label" error, no write; t31: python `s.replace` on `tests/test_cli.py` (a test file; real write) | yes; irrelevant | unavailable (`errors.py` outside `source_paths`) |
| 028222 run-record-gate | skipped writer 29 | python `s.replace` on `tests/test_cli.py` (test file) | yes; irrelevant | fail (5 `load_run_record` refusals) |
| 870439 guard-prefixes | fidelity pass vs unavailable | t34 python byte-patch of `guard.py` (removes a stray quote); the replay never applied it, so the replayed `guard.py` does not import | yes with python-heredoc replay | no trigger (no test run in the cell) |
| 937944 guard-prefixes | fidelity pass vs fail | t16 python `s.replace` on `guard.py` | same | no trigger |
| 424626 guard-prefixes | fidelity pass vs fail | t27/t29 python `s.replace` on `guard.py` | same | no trigger |
| 688090 review-script | skipped writer 15 | BSD `sed -i 's/…/g' file` → error, no write (transcript: `undefined label 'ests/test_review.py'`) | yes | pass (harness pass) |
| 501161 review-script | skipped writers 11, 18 | t11 `mv tools/review.py …; pytest; mv … back` (net zero); t18 `sed -i '' …` on the test file (real write) | yes | pass |

Every unmeasured cell can be measured by a defensible method the pre-registration did not use: (a) treat a `sed -i` whose tool result is the BSD "undefined label"/"extra characters" error as a non-write; (b) replay `python3 - <<'X'` bodies that do `open(p).read(); s.replace(...); open(p,'w').write(s)` and `cp`/`mv` segments in order, in the scratch tree; (c) accept `2>/dev/null` beside `2>&1`. `trajectory.py` implements (b) as `ext`; its trees agree with `std` on every graded turn of 970283 and repair the guard-prefixes fidelity misses where the harness verdict is pass (`trajectory.md`: 870439 passes from turn 34, 937944 from turn 16, 424626 from turn 29 under `ext`, matching the harness — fidelity 14 of 14 graded decision cells). With (a)–(c) the count is 0 unmeasured decision cells, docs-linter net +1, floor harm 0, no floor task insufficient — **Verify** under section 5 as amended by 7.1 (one budget-shaped task qualifies).

### 1.3 Did any rule tilt the result?

- **Section 3 (trigger)** — neutral. Both routes were exercised; `self_test` never fires because the three route-proof cells never called it.
- **Section 4 skipped-writer rule + Ruling 11 (lexical)** — decisive against the one rescue. The `_PY_WRITE` regex fires on `write_text(` anywhere in the command when the text also names a source file; 970283's temp-tree scripts do exactly that. The plan's own note ("over-flagging costs only unmeasured cells") is where the result was lost.
- **Ruling 12 (through the trigger turn)** — correct in principle (the graded state is the end of the turn); it did not by itself unmeasure any cell whose skips were strictly earlier.
- **7.4 (conservative rescues)** — decisive on 970283 and 859943 for a second, independent reason. Its allowlist is narrower than "provably read-only": `cat x 2>/dev/null`, `od`, `xxd`, `md5`, `which`, `for … done`, and read-only `python3 -c` scans all fail it. It was added after a real defect (the harness can grade `unavailable` on files a skipped command left outside `source_paths`), so it is defensible; but it makes the instrument unable, by construction, to count a rescue on a self-hosted task.
- **Ruling 14 (fidelity)** — correct; it exposed a replay gap (python writes) rather than a counting error. But because it marks the *cell* unmeasured, three floor cells that ran no tests at all became `insufficient`, which is a statement about the replay, not about harm.
- **Ruling 6 / 7.2 (grade outside the checkout)** — correct and necessary; verified by re-grading here.
- **Section 5 / 7.1** — applied correctly to the counted tallies; the decision text is what the counts imply.

### 1.4 Does the conclusion survive the instrument's limits?

"Not the lever" does not; "underpowered and, on this ceiling set, not the dominant class" does. Concretely: of 12 budget-shaped decision cells, 1 is a finishing failure (970283), 1 is a pass, 4 never reached a green, and 6 are information-, ambiguity- or allowlist-bound at every turn (depth-3: 0 of 4 cells ever touch `models.py`'s timestamp; run-record-gate: every graded turn of every cell fails or is unavailable). Adding the Engine column and the 2026-09-14 nights, pass-state-then-overrun appears in 970283, 859943 and 511653 — 3 cells out of the 19 budget-exceeded or timed-out cells across all groups (10 decision, 6 nights, 3 Engine). That is the size of the finishing class on this evidence: real, roughly 1 in 8 of the budget-exceeded cells, concentrated on the one build task the budget line bisects.

## 2. Is "own-green is a weak signal" the right generalisation?

Not as stated. On the decision cells the green-vs-hidden gap is the allowlist and hidden structural expectations, which no *observable* signal can see — the Engine's `scope` would have refused the `errors.py`/`pyproject.toml` writes in its own arm, but that changes earlier calls and cannot be scored from these recordings (R0 constraints §1.4). The alternative triggers, evaluated on every cell where they apply (`triggers.md`; verdicts come from grading the reconstructed worktree at the trigger turn):

Triggers (all prefix-preserving; each names a turn, and the counterfactual verdict is the graded worktree at the end of that turn): T1 the pre-registered own-green; T2 the first green whose invocation is the whole public suite (`uv run pytest -q` / `pytest tests/`, no node id, no `-k`) rather than the model's own file selection; T3 a green preceded by 1 or 2 turns with no write/edit; T4 a green re-confirming an earlier green with no source edit between; T5 the last green within budget (not a stopping rule — it needs foresight — but the ceiling of every green-based rule); T6 the oracle, the first turn whose worktree passes the hidden suite within budget (the ceiling of *any* stopping rule).

| trigger | decision rescues | decision harms | decision unmeasured-by-committed-rules among rescues | debug rescues | debug harms |
|---|---|---|---|---|---|
| T1 own-green (first) | 1 (970283) | 0 () | 1 | 3 (770940, 840545, 859943) | 0 () |
| T2 first whole-suite green | 1 (970283) | 0 () | 1 | 3 (770940, 840545, 859943) | 0 () |
| T3 green after 1 non-editing turn(s) | 1 (970283) | 0 () | 1 | 3 (770940, 840545, 859943) | 0 () |
| T3 green after 2 non-editing turn(s) | 1 (970283) | 0 () | 1 | 3 (770940, 840545, 859943) | 0 () |
| T4 green re-confirmed (no source edit since previous green) | 1 (970283) | 0 () | 1 | 3 (770940, 840545, 859943) | 0 () |
| T5 last green within budget | 1 (970283) | 0 () | 1 | 4 (511653, 770940, 840545, 859943) | 0 () |
| T6 oracle: first hidden-pass turn | 1 (970283) | 0 () | 1 | 4 (511653, 770940, 840545, 859943) | 0 () |

Per-cell turns and verdicts: `evidence/triggers.md`. The three debug-group review-script "rescues" (770940, 840545 on every rule; 714610 under the filtered patch) are the 2026-09-14 night's manifest drift, not finishing: the harness graded them `unavailable` because the task tree did not yet ignore `PROVENANCE.md`; under the current manifest their trees pass from the first edit. 511653 (T5/T6 only) is the old-prompt run-record-gate cell that passed at turn 39 (28.2k) with its own file green at turn 47 (31.4k). One more pass-state hides behind the allowlist: 249635 (2026-09-14 guard-prefixes, `BUDGET_EXCEEDED`) passes from turn 42 once non-source files are filtered out.

Reading: every observable rule finds the same single decision rescue (970283) and the same Engine-column rescue (859943); the whole-suite rule and the "re-confirmed green" rule fire later and cost tokens without changing any verdict; "last green within budget" and the oracle add only 511653 (debug group, old prompt). No rule produces a harm on the 12 floor cells with triggers. The right generalisation is therefore: **own-green is an adequate stopping signal for finishing failures — it never fired on a worktree that would later become a pass and did not yet pass — but finishing failures are a minority class on this ceiling set, and the majority class is invisible to any green.**

Per-cell pass-state trajectory (the oracle any stopping rule is bounded by):

Every reconstructed worktree graded at every turn from the first source edit (std replay; `ext` where it differs). "Stays pass" means every later turn also passes: **no cell that reached a pass-state ever left it**, so the harm risk of stopping at a green is zero on this evidence.

| task | group | attempt | code | 1st source edit | turns graded | first hidden-pass turn (cum. tokens) | pass at final turn | own-green turn:verdict | best filtered (allowlist relaxed) | ext replay differs |
|---|---|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | decision | 971281 | COMMAND_TIMEOUT | - | 0 | never (no source edit) | - | - | - | - |
| agentclinic-repair-depth-3 | decision | 021584 | BUDGET_EXCEEDED | - | 0 | never (no source edit) | - | - | - | - |
| agentclinic-repair-depth-3 | decision | 082295 | OK-fail | t15 | 10 | never | fail | 23:fail | - |  |
| agentclinic-repair-depth-3 | decision | 700050 | BUDGET_EXCEEDED | - | 0 | never (no source edit) | - | - | - | - |
| selfhost-run-record-gate | decision | 388294 | BUDGET_EXCEEDED | t12 | 37 | never | fail | - | - |  |
| selfhost-run-record-gate | decision | 448568 | BUDGET_EXCEEDED | t11 | 19 | never | unavailable | - | - |  |
| selfhost-run-record-gate | decision | 519278 | BUDGET_EXCEEDED | t16 | 33 | never | unavailable | 35:unavailable | - |  |
| selfhost-run-record-gate | decision | 028222 | BUDGET_EXCEEDED | t12 | 37 | never | fail | 33:fail | - |  |
| selfhost-docs-linter | decision | 147562 | BUDGET_EXCEEDED | t8 | 30 | never | unavailable | 32:unavailable | - |  |
| selfhost-docs-linter | decision | 204433 | OK-pass | t8 | 40 | t28 (18711) → stays pass | pass | 35:pass | - |  |
| selfhost-docs-linter | decision | 270586 | BUDGET_EXCEEDED | t10 | 20 | never | unavailable | - | - |  |
| selfhost-docs-linter | decision | 970283 | BUDGET_EXCEEDED | t10 | 39 | t39 (27773) → stays pass | pass | 40:pass | - |  |
| selfhost-guard-prefixes | decision | 812248 | OK-pass | t2 | 3 | t2 (1600) → stays pass | pass | - | - |  |
| selfhost-guard-prefixes | decision | 870439 | OK-pass | t2 | 44 | never | unavailable/ext pass | - | - | ext pass from t34 |
| selfhost-guard-prefixes | decision | 937944 | OK-pass | t2 | 17 | never | fail/ext pass | - | - | ext pass from t16 |
| selfhost-guard-prefixes | decision | 424626 | OK-pass | t2 | 32 | never | fail/ext pass | - | - | ext pass from t29 |
| selfhost-review-script | decision | 688090 | OK-pass | t6 | 19 | t6 (3833) → stays pass | pass | 18:pass | - |  |
| selfhost-review-script | decision | 746232 | OK-pass | t5 | 12 | t8 (3491) → stays pass | pass | 10:pass | - |  |
| selfhost-review-script | decision | 816670 | OK-pass | t6 | 24 | t6 (2858) → stays pass | pass | 17:pass | - |  |
| selfhost-review-script | decision | 501161 | OK-pass | t9 | 21 | t21 (8339) → stays pass | pass | 23:pass | - |  |
| agentclinic-repair-depth-2 | decision | 523251 | OK-pass | t6 | 5 | t6 (3057) → stays pass | pass | 7:pass | - |  |
| agentclinic-repair-depth-2 | decision | 575297 | OK-pass | t7 | 3 | t7 (3517) → stays pass | pass | 8:pass | - |  |
| agentclinic-repair-depth-2 | decision | 634454 | OK-pass | t13 | 3 | t13 (4281) → stays pass | pass | - | - |  |
| agentclinic-repair-depth-2 | decision | 616367 | OK-pass | t7 | 4 | t8 (2882) → stays pass | pass | 9:pass | - |  |
| selfhost-run-record-gate | nights-2026-09-14 | 490384 | BUDGET_EXCEEDED | t18 | 31 | never | unavailable | - | - |  |
| selfhost-run-record-gate | nights-2026-09-14 | 549012 | BUDGET_EXCEEDED | t18 | 31 | never | fail | - | - |  |
| selfhost-run-record-gate | nights-2026-09-14 | 618278 | BUDGET_EXCEEDED | t18 | 25 | never | unavailable | - | - |  |
| selfhost-run-record-gate | nights-2026-09-14 | 511653 | BUDGET_EXCEEDED | t8 | 41 | t39 (28181) → stays pass | pass | 34:fail | - |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 249635 | BUDGET_EXCEEDED | t42 | 7 | never | unavailable | - | pass from t42 |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 305323 | BUDGET_EXCEEDED | t3 | 46 | never | unavailable | - | - |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 372105 | OK-pass | t2 | 4 | t2 (3278) → stays pass | pass | - | - |  |
| selfhost-guard-prefixes | nights-2026-09-14 | 309486 | OK-pass | t2 | 8 | t2 (2101) → stays pass | pass | - | - |  |
| selfhost-review-script | nights-2026-09-14 | 714610 | OK-unavailable | t7 | 14 | never | unavailable | 15:unavailable | pass from t14 |  |
| selfhost-review-script | nights-2026-09-14 | 770940 | OK-unavailable | t10 | 23 | t10 (3749) → stays pass | pass/ext unavailable | 18:pass | - | ext pass from t10 |
| selfhost-review-script | nights-2026-09-14 | 840545 | OK-unavailable | t7 | 21 | t7 (3786) → stays pass | pass | 12:pass | - |  |
| selfhost-review-script | nights-2026-09-14 | 624725 | OK-unavailable | t9 | 14 | never | fail | 14:fail | - |  |
| agentclinic-repair-depth-3 | engine | 808698 | BUDGET_EXCEEDED | - | 0 | never (no source edit) | - | - | - | - |
| selfhost-run-record-gate | engine | 296145 | BUDGET_EXCEEDED | t16 | 33 | never | unavailable | - | - |  |
| selfhost-docs-linter | engine | 859943 | BUDGET_EXCEEDED | t13 | 31 | t28 (25213) → stays pass | pass | 34:pass | - |  |
| agentclinic-repair-misleading-locus | engine | 117091 | OK-pass | t4 | 2 | t4 (1546) → stays pass | pass | 5:pass | - |  |
| agentclinic-repair-misleading-locus | engine | 172304 | OK-pass | t3 | 2 | t3 (874) → stays pass | pass | 4:pass | - |  |
| agentclinic-repair-misleading-locus | engine | 140540 | OK-pass | t8 | 3 | t8 (2126) → stays pass | pass | 9:pass | - |  |
| agentclinic-repair-misleading-locus | engine | 201516 | OK-pass | t3 | 2 | t3 (540) → stays pass | pass | 4:pass | - |  |

## 3. The honest model and budget (R0 question 3)

Sources: `q3stats.md` (per-cell), `serverlog.py` (oMLX `Chat completion` lines for 2026-09-14/15: 1,932 completions at `max_tokens=32000`), `evidence/2026-09-15-release-one-outcome/cells.md`.

**Where the tokens go.** Thinking is 52–88% of output characters by task (median over decision cells: depth-3 88%, run-record-gate 58%, docs-linter 67%, floor tasks 52–69%). Every budget-shaped cell has one planning turn of 6–12k tokens right after reading the code (19–40% of the whole budget in one message: 519278 t13 11.5k, 270586 t7 11.2k, 388294 t9 9.5k, 448568 t6 8.2k). Tool arguments are 29–58% on the self-hosted tasks (the model writes files and heredocs in full). Visible text is 1–4%.

**Finishing versus not, on the same tasks.** docs-linter: the one pass (204433) used 28.5k tokens / 48 turns — inside the budget by 3.5k tokens and 0 turns; the finishing cell 970283 reached pass at 27.8k / t39 and tripped at t49; the Engine cell at 25.2k / t28 and tripped at t44 (32.1k). The two non-finishing cells spent 32k without a green. run-record-gate: median 28.4k / 49 turns; the cells that got a green did so at 21.6–24.8k and the code was wrong anyway. Floor tasks finish at 2–11k / 5–30 turns (guard-prefixes' 870439 spent 27.6k on a one-line regex, hunting a stray quote for 40 turns, and still passed). The budget is not the binding constraint on floor or on run-record-gate/depth-3; it binds exactly on docs-linter, where Baseline's finishing distribution (28–32k, 44–49 turns) straddles it.

**`max_tokens` = budget.** Two completions in the logs hit `finish_reason=length` at exactly 32,000 tokens (021584 t10, 808698 t9; 1,277 s and 940 s of decode), both on depth-3, both arms; 12 more completions exceeded 8k tokens (23–36 tok/s, 4–8 minutes each). A per-turn cap of 8k would have ended neither cell's *reasoning* problem but would have given each 3 more attempts; it would also cut the planning turn in every build cell, with unknown effect on quality. It must be applied to both arms and pre-registered (R0 constraints §1.1).

**Decode rate against context, measured on the cells themselves** (not the probe): median 35.1 tok/s at prompt < 5k, 33.7 at 5–10k, 27.7 at 10–20k, 30.3 at 20–40k, 30.0 at 40–80k, under mixed concurrency; by concurrency at the completion midpoint, k = 1 runs 41.2 tok/s per stream, k = 3 runs 29.8 per stream (~89 tok/s total, 2.2× k = 1) — **k = 3 passes the spec's 1.5× rule on live data**, which resolves release one's item 7. Mean effective rate over all 2026-09-14/15 output was 25.3 tok/s (1.24M output tokens in 13.6 decode-hours). Context reached 8–17k on budget-shaped cells (max input per cell), never the 80–160k where the probe saw 24–33 tok/s; compaction never engaged.

**Wall-clock.** Budget-shaped cells take 13–30 min each at k = 3 (docs-linter median 27 min, run-record-gate 25 min); floor cells 1–9 min. The 43 retained cells cost 8.2 cell-hours, ~3 GPU-hours at k = 3.

**Is Ornith 1.5 9B at 32k/48 an honest setting?** For the *product* claim as worded ("delivers a passing candidate within budget more often"), the evidence says: the model can do the floor tasks and the build tasks' *code* (docs-linter 3 of 5 pass-states; run-record-gate 8 of 9 cells reach 15/20 with the class placed where the prompt said); what it cannot do is infer a stripped fact (depth-3) or a hidden structural choice (run-record-gate), and neither is a budget or a model question — a 26B fails them the same way under identical prompts. The budget is honest for docs-linter-shaped tasks only in the sense that it bisects the finishing distribution, which is what makes the claim measurable there and nowhere else. The evidence points to a **different task shape, not a different model**: build tasks whose known-good finishing cost is 20–28k (so the budget leaves 4–12k of headroom for finishing to matter and Baseline sits at 0.1–0.3), with prompts that pass the task-validity check. A different model (26B) would raise floor pass rates and shrink the class further; a bigger budget (48k) would make docs-linter a floor task and remove the only finishing signal.

**What I would pre-register next, and its cost.** Not an Engine claim. A **Baseline-only diagnostic night**: 3–4 build tasks cut from later Phase commits, each passing R0 constraints §1.2 (a solution from the prompt alone passes hidden), n = 6, per-turn cap 8k, tripped worktrees harvested and graded (§1.1), every cell classified by constraint (information / ambiguity / capability / budget / finishing) with the pass-state turn. Decision rule written first: a task enters the ceiling set only if ≥ 3 of 6 cells are finishing- or budget-classified and Baseline within-budget passes ≤ 1 of 6. Cost: 24 cells × ~25 min at k = 3 ≈ 3.5–4 GPU-hours, one night, plus half a day cutting and validity-checking tasks. If two tasks qualify, the offline counterfactual at that point is the finishing estimate the constraints demand before any Engine work.

## 4. What R0 should do — decision tree

**Day 0 (today, no GPU):**

1. **Correct the record without re-running.** Under the spec's own status line ("a bug found afterwards is fixed and re-run only with the bug and both results recorded beside each other"): record that the section 4 skip rule and 7.4 mis-classified write-and-restore and read-only commands in 970283 and 859943; record the by-inspection measurement (pass at trigger, 27.9k / turn 40) beside the pre-registered `not-the-lever`; state the decision as **Verify on clean tasks (7.1)** with the caveat that it rests on one cell. Do not edit `cells.json`; add a `run-2/` or a README section. This is honesty, not tuning — the direction is against the operator's convenience.
2. **Do not build a finish-on-green Engine yet.** One rescue in 12 budget-shaped cells (+1 Engine, +1 old-prompt) is not an effect a release can be powered on (§3 power 0.26 at pb 0.25 / pe 0.5). R0 constraints §1.4 says a remedy is built only when its estimate clears the threshold.
3. **Fix what release one already listed** (harness validity, §1.1): per-turn cap, harvest-and-grade tripped worktrees, keep pytest's explanation line in the AgentClinic rung, tool parity (multi-edit, prompt collapse, writable paths from `Files:` only). These are product fixes and measurement fixes regardless of any claim; half a day to a day.

**Then one of three branches:**

- **A. Diagnostic night (recommended if a claim is still wanted; ~4 GPU-h, one night + half a day of task cutting).** The pre-registration in §3. It answers R0 questions 1–2 with measured classes instead of a counterfactual on defective tasks. Go to an Engine counterfactual only if ≥ 2 tasks qualify.
- **B. No claim: ship the Engine as a product with honest before/after numbers.** Report what the Engine measurably does on the live model (bounded every command, redirected 24 → 3 ad-hoc pytest runs, cut a 1,800 s hunt to 120 s, scope refusals) and what it does not (outcomes unchanged on the ceiling set), with the counterfactual's honest reading. Zero GPU. This is the right branch if the calendar is "days not weeks" and the next night cannot be attended.
- **C. Stop the eval track.** Legitimate if B is taken and no further claim is planned: the harness, tasks and records are a complete, reproducible negative with a named class size. Say so in the roadmap and freeze.

**What I would refuse to do, and why:** re-run the decision phase with loosened rules and publish only the new number (that is post-hoc tuning; both must appear); run the Phase 4 night or any Engine-vs-Baseline comparison on the current ceiling set (two of three tasks are task defects — the comparison cannot win and cannot lose informatively); build a hard "stop at own-green" (511653's own suite was green at t34 with the hidden suite failing 33 tests; it was fixed by t39 and green again at t47 — a hard stop harms exactly the cells it is meant to help; keep it a nudge); change the budget or the stipulated effect after seeing these numbers; and treat guard-prefixes' `insufficient` as evidence about harm when the task never ran a test.

## Appendix: reproduce

```
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
uv run --project . python <this dir>/evidence/audit.py         # triggers and per-turn usage from transcripts
uv run --project . python <this dir>/evidence/trajectory.py    # replay + grade every unique worktree, std and ext
python3 <this dir>/evidence/triggers.py                         # alternative triggers over trajectory.json
python3 <this dir>/evidence/serverlog.py                        # decode rate vs context and concurrency
python3 <this dir>/evidence/q3stats.py                          # token / thinking / context statistics
```
