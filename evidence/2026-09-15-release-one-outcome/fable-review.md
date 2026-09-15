# Deep review: why the Engine does not lift Ornith on the ceiling tasks, and what to do before Phase 4

Fable, 2026-09-15. Read-only. Evidence scripts and outputs under `evidence/` (see `evidence/README.md`). Cell ids are the last six digits of the attempt directory.

## Summary and recommendation (one screen)

**The claim as posed will not hold, and no Engine remediation buildable in a day changes that.** Each ceiling task fails for a reason the Engine cannot reach:

1. **`agentclinic-repair-depth-3` (R1) is information-bound, not budget-bound.** The third seam is `first.timestamp.tzinfo is not None` (`overlay/test_acceptance.py:150`); the R1 text gives the model only "assert None is not None" because the rung strips pytest's `+ where None = ....tzinfo` line. Of 7 measured cells (4 Baseline, 3 Engine), 0 found it; 5 never wrote the words timezone/tzinfo; 2 reached 12/13 (`082295`, `719334`) and both said "I left models.py untouched". Two cells (one per arm) burned the whole budget in a single 32,000-token turn (`stopReason: length`) circling that seam. Identical prompts across arms means the Engine cannot add the missing fact.
2. **`selfhost-run-record-gate` (R1-plan) is spec-ambiguity-bound.** Reconstructing every cell's worktree from its transcript and grading it offline (`evidence/recon.log`): 5 of 9 cells (4 Baseline, the Engine one) defined `RunRecordError` in `errors.py`, as the prompt's "a `UsageError` subclass from `errors.py`" invites; `errors.py` is outside `source_paths`, so `check_allowlist` rejects the whole patch (`src/satyrn_evals/patch.py:181-184`). With `errors.py` allowed, 8 of 9 cells reach 15/20 and stall on the second trap: the prompt's "Gate rules" section reads as `gate()` rules, but the hidden suite expects digest/mode/condition/empty-rule refusals from `load_run_record` (`overlay/test_run_record.py:58-110`) -- the same five tests fail in every one of those cells ("DID NOT RAISE"). The plan's code that disambiguated both (`from satyrn_evals.run_record import RunRecordError`; validation in the loader) is exactly what R1-plan strips. One Baseline cell (`511653`) avoided both traps and had a passing worktree at turn 39 (28.2k tokens), then spent 10 turns polishing its own tests and tripped the turn budget. The Engine's derived contract makes trap 1 worse: it lists `src/satyrn_evals/errors.py` as writable, and the Engine cell edited it twice.
3. **`selfhost-docs-linter` is a budget-edge task where Baseline is too good to power a win.** Pass-state reached in 3 of 5 cells (Baseline `204433` at turn 28/18.7k tokens, graded pass at turn 48; Baseline `970283` at turn 39/27.8k, tripped at 49; Engine `859943` at turn 28/25.2k, tripped at 44). After reaching it, the cells spent 10-20 turns and 2.6-9.8k tokens on the plan's Steps 4-5 (real-tree lint, the 1,483-test full suite, ruff, provenance rows, `git commit`) and edge-case re-verification. Even a perfect "finish on green" Engine gives maybe 0.4-0.5 here, and the Baseline within-budget rate is 0.15-0.3: at n = 12 the Baseline lands at >= 2/12 with probability 0.56-0.84, which by the spec's own rule makes the task "under-powered, supplies no win".

Under the rule (>= 2 of 3 tasks reject), the win probability after any one-day remediation is a few percent. The honest completion is the spec's own: **stop with a stated negative**, keep the engine at 8049d73 (or the hygiene fixes below), and spend GPU only if a numbered negative is wanted.

**Decision tree (next 1-2 days):**

- **Branch A (recommended, 0 GPU hours, half a day):** write the negative now from the admission, route-proof and reconstruction evidence; freeze 8049d73; file the task and harness defects listed in section 5 as release-two work. Commit the hygiene fixes to the Engine as product bugs regardless (multi-edit, prompt collapse, writable paths from the request's `Files:` block only) -- they are not measured claims.
- **Branch B (a numbered negative, ~5-6 GPU hours, one night):** run night one only to the pre-registered futility look (6 + 6 per task, 36 cells) and stop every task that fails it. This stays inside the design and produces a result page per task. Predicted: all three stop at futility.
- **Branch C (a real shot at the claim, 3+ days, not "days not weeks"):** fix the two task defects (drop or re-rung depth-3; reword run-record-gate's Interfaces line or widen its `source_paths`), cut and admit at least one replacement ceiling task, build the finish-on-green nudge plus hygiene fixes, measure them on a fresh dev cut at n = 4-6, then Phase 4. Win probability even then ~20-30%, because docs-linter cannot supply a win and run-record-gate's Baseline rate after the fix is unknown.

Go to C only if the calendar allows three more days and a 70-80% chance of a negative at the end is acceptable. Otherwise A, with B if a measured number is worth a night.

---

## 1. Diagnosis: where ceiling cells spend tokens and turns

Sources: `evidence/cells.md` (every cell), `evidence/phases.md` (ceiling cells), transcripts under `~/satyrn-runs`.

### 1.1 Output tokens are mostly thinking; the visible work is small

Estimated split of output tokens (proportional to characters inside each assistant message; `usage.output` is per message):

| task | arm | cells | thinking share | tool-args share | visible text share |
|---|---|---|---|---|---|
| depth-3 | Baseline | 4 | 87-97% (two runaway turns: 50%) | 1-9% | <1% (runaway: 45%) |
| depth-3 | Engine | 2 | 87% / 56% (runaway) | 11% / <1% | 3% / 44% |
| run-record-gate | Baseline | 8 | 41-63% | 35-58% | 1-3% |
| run-record-gate | Engine | 1 | 63% | 36% | 2% |
| docs-linter | Baseline | 4 | 57-81% | 18-42% | 1-4% |
| docs-linter | Engine | 1 | 69% | 29% | 2% |

Every ceiling cell has one dominant planning turn of 4-12k thinking tokens right after reading the code: run-record-gate Baseline `t13:9.5k`, `t10:10.5k`, `t13:11.5k`, `t9:9.4k`, `t6:8.1k`; Engine `t11:8.5k`; docs-linter Baseline `t7:6.0k`, `t5:5.6k`, `t7:11.1k`, `t9:7.0k`; Engine `t12:7.5k` (`evidence/phases.md`). That single turn is 15-35% of the 32k budget, in both arms.

### 1.2 depth-3: two failure shapes, neither budget-shaped

- Runaway turn: Baseline `021584` turn 10 and Engine `808698` turn 9 each emitted exactly 32,000 tokens with `stopReason: "length"` (`max_tokens` is 32,000 = the whole budget, `arms/*-ornith15-9b.json` `inference.max_tokens`). The thinking closes around 130k characters and the model keeps reasoning in visible text (149 fenced code blocks, `def test_complaint_model_contract_is_preserved():` written out 65 times in `021584`; "Passes." 96 times in `808698`). Both are stuck on the same sentence: "for the error to be exactly `assert None is not None`, the value X ... must be None". Pi fails every tool call in a length-cut message, so the cell ends there.
- Two-seam fix: `082295` (Baseline, 25 turns, 24.1k) and `719334` (Engine, 28 turns, 32.7k) fixed `lang="en"` and the 303 redirect and graded/reconstructed at 12/13, failing only `test_complaint_model_contract_is_preserved`. `082295`'s final text: "I left `models.py` untouched to keep every existing behavior intact." `700050` (Baseline, 35 turns, 41.9k) considered the timestamp at turn 9 ("That works.") and dismissed it; `719334` did the same at turn 11.
- Search for the words `timezone|tzinfo|utc|aware` in thinking and text: 0 hits in `971281`, `021584`, `082295` (1 hit, a test the model wrote asserting `timestamp is not None`), `808698`; hits in `700050` and `719334` only in the dismissed form.

The clue that would decide it is pytest's own explanation line, which the R1 rung removes (`manifest.json` R1: "the third fails assert None is not None"; R3 says "the timestamp lost its timezone"). No budget makes the model guess `tzinfo` from "None is not None". Guard 4 worked (`command_bounded` 6-18, one `command_timed_out`), the loop breaker never fired, `self_test` was called once in three cells.

### 1.3 run-record-gate: exploration, one big think, piecemeal edits, then a trap

Per cell (`evidence/phases.md`, `evidence/recon.log`):

| cell | arm | turns | tokens | turns to 1st mutation | tokens to 1st mutation | edit calls (consecutive same file) | best hidden state (allowlist) | with errors.py allowed |
|---|---|---|---|---|---|---|---|---|
| 490384 | B | 49 | 29.7k | 17 | 14.9k | 16 (9) | rejected | 15/20 |
| 549012 | B | 49 | 25.9k | 18 | 9.5k | 15 (9) | 15/20 | 15/20 |
| 618278 | B | 43 | 32.4k | 14 | 12.3k | 9 (6) | rejected | 15/20 |
| 511653 | B | 49 | 32.5k | 8 | 7.6k | 16 (10) | **20/20 at turn 39 (28.2k)** | same |
| 388294 | B | 49 | 27.5k | 12 | 10.7k | 15 (11) | 15/20 | 15/20 |
| 448568 | B | 30 | 32.1k | 10 | 9.8k | 10 (7) | rejected | 15/20 |
| 519278 | B | 49 | 29.2k | 15 | 12.7k | 9 (5) | rejected | 15/20 |
| 028222 | B | 49 | 24.9k | 12 | 5.3k | 14 (8) | 15/20 | 15/20 |
| 296145 | E | 49 | 31.3k | 14 | 11.1k | 16 (11), all single-replacement | rejected | rejected (tests never written; module still mid-edit at t45) |

- Exploration before the first mutation costs 8-18 turns and 5-15k tokens (16-46% of the token budget) in both arms. The Engine cell read Pi's own `node_modules` first (turn 1 -- four Baseline cells did the same, so it is Pi's system prompt, not the Engine), then `AGENTS.md`, `BRIEF.md`, `errors.py`, `cli.py` twice, `census.py`, `capture_record.py`, `ROADMAP.md`, `pyproject.toml`, `conftest.py`, `tests/test_cli.py`, a grep, the plans directory: 13 turns, 22 read commands.
- Edits are one hunk per call. Baseline cells batched 0-5 calls with 2+ replacements; the Engine schema forbids it (`mutator.ts:121-153`, `maxItems: 1`), so the Engine cell spent turns 18-25 on eight consecutive single edits to `cli.py`.
- Time to a failing-test signal from the model's own tests: turns 16-33 (Baseline), never (Engine; it tested with `python -c` and never called `self_test`). None of those signals could reveal the hidden suite's expectations, because the traps are about where a class and a validation live.
- The five tests every 15/20 cell fails: `test_a_bad_digest_is_refused`, `test_an_unknown_condition_is_refused`, `test_an_unknown_mode_is_refused`, `test_an_empty_rule_field_is_refused[stop_rule|decision_rule]` -- all "DID NOT RAISE" from `load_run_record`, while the same cells' `gate()` does raise (`549012`: `RunRecordError task_tree_sha256 must be 64 lowercase hex digits`). The models implemented the prompt's "Gate rules" in `gate`.
- `511653` after its passing state (turn 39): "Now let me fix the test helper to bypass eager validation", three test edits, three pytest runs, "All 71 pass. Now let me add CLI tests" -- 10 turns, 4.3k tokens, tripped at turn 49.

### 1.4 docs-linter: the budget-edge task

| cell | arm | turns | tokens | 1st mutation | pass-state turn (tokens) | spend after pass-state | end state |
|---|---|---|---|---|---|---|---|
| 204433 | B | 48 | 28.5k | 6 | 28 (18.7k) | 20 turns / 9.8k | graded pass |
| 970283 | B | 49 | 30.4k | 10 | 39 (27.8k) | 10 turns / 2.6k | BUDGET_EXCEEDED |
| 859943 | E | 44 | 32.1k | 13 | 28 (25.2k) | 16 turns / 6.9k | BUDGET_EXCEEDED |
| 147562 | B | 38 | 32.2k | 8 | never; 14/15 (spec cap vs plan) | - | BUDGET_EXCEEDED |
| 270586 | B | 30 | 32.1k | 10 | never; 14/15 (13-results count) | - | BUDGET_EXCEEDED |

What the post-pass turns contain (transcripts): `204433` t29-t48: trims its own tests "to exactly 9" (the plan says "9 passed"), `just lint-docs`, full suite (1,483 tests), provenance rows, `git config`, `git commit`, "final verification of all steps", summary. `859943` (Engine) t29-t44: test fixes, `just lint-docs`, full suite twice (the first bounded at 115 s), ruff, five `python -c` edge-case checks, "check the provenance gate status before committing (Step 5)". `970283` t40-t48: "The task targets exactly 9. Let me remove the redundant fence-ok test", full suite, edge cases. The model is executing the plan's Steps 4-5 literally; the Engine prompt's "Stop when the task is complete" does not compete with a five-step recipe that ends in "Record and commit".

### 1.5 Engine route-proof cells versus Baseline on the same tasks

No qualitative difference in shape. Same exploration length (13-14 turns), same one-hunk-per-turn editing (worse in the Engine: schema-enforced), same ceremony, same runaway on depth-3. Engine-specific costs observed:

- Prompt 12,421 chars (docs-linter) and 13,725 chars (run-record-gate) against 2,976 and 4,267 for Baseline: `build_prompt` expands `tests/*` into every tracked test file (`attempt.py:353-356`) and then lists the same files again as carried (`attempt.py:385-389`). Prefill only, but it is ~3k tokens of noise on every turn and it contradicts scope (carried files appear as writable, then `scope.ts:41-47` refuses them).
- Derived writable paths include `src/satyrn_evals/errors.py` because the request names it (`derive.py:149-150`); the grader's allowlist does not. The Engine cell edited it twice.
- Edit refusals: docs-linter 3 `ANCHOR_MISSING` (one identical edit retried twice) + 1 schema `maxItems` refusal; run-record-gate 1 `INVALID_REQUEST: path must be relative` (scope admits absolute in-repo paths, `scope.ts:40,49`, then the protocol refuses them, `mutation.py:114`).
- `self_test`: 0 calls in the three route-proof cells; bash pytest 2-9 per cell. The completion gate (316432c) fires only when the model stops without a tool call (`runner.ts:497`); none of these cells ever stopped.
- Guards fired where the spec said they would (`command_bounded` 6-38 per cell) and nowhere the outcome turned.

### 1.6 What binds, per task

| task | binding constraint | budget-bound? | Engine-addressable? |
|---|---|---|---|
| depth-3 | R1 assertion text hides the seam; a 9B cannot infer `tzinfo` | no (24-42k cells never found it either) | no (identical prompts) |
| run-record-gate | prompt ambiguity (class location, validation location) + allowlist | residually (1 of 9 got there and overran) | no; the Engine's derive makes trap 1 more likely |
| docs-linter | 48-turn/32k budget vs the plan's Steps 4-5 ceremony after a passing state | yes | partly (a finish nudge), but Baseline is too good for a win |

## 2. Would any Engine remediation move 0-1/12 to >= 4-6/12 on two of three tasks?

No. Per remediation (mechanism; what it targets; evidence; expected effect; cost; floor risk):

| remediation | targets | evidence it targets the binding constraint | expected effect on ceiling passes | build + measure cost | floor-parity risk |
|---|---|---|---|---|---|
| **Early automatic `self_test` after the first mutation batch** (plan design 3) | time to first failing-test signal | the signal comes from the model's own tests; in every 15/20 and 14/15 cell the miss was a hidden expectation the model's tests did not encode; depth-3's public suite is 4/4 green at 12/13 | ~0 | half a day; needs a dev task with tests (misleading-locus is too easy: 5-11 turns) | low; adds a 30 s suite run per generation on self-hosted tasks |
| **Context seeding** (contents/outlines of the files the request names) | exploration before the first mutation (8-18 turns, 5-15k tokens) | real sink in both arms, but the dominant cost inside it is the one planning think (5-12k), which seeding does not remove; the Engine cell would still have read AGENTS/BRIEF/tests | saves ~3-5 turns and 1-3k tokens; does not create pass-states; on depth-3 nothing | half a day (derive has the file list; `build_prompt`) | moderate: bigger prompts on floor tasks cost nothing in output tokens but the secondary claim is tokens+turns, fine; risk is the model re-reading anyway |
| **Edit batching** (lift `maxItems: 1`, `mutator.ts:121-153`, `mutation.py` apply-many) | turns lost to consecutive single edits (Engine: 11 and 7 consecutive same-file edits) | Baseline already batches 0-5 calls per cell; this is parity, not lift | +2-8 turns of headroom per cell; converts nothing by itself | small (schema + Python apply + tests) | none |
| **Planning / decomposition step** | the 5-12k planning think | the model already plans once, at length; a forced step adds a second | negative | - | - |
| **Turn-budget-aware nudge / finish-on-green** (steer message when `self_test` exits 0 after a source mutation: "self_test passes; if the task is complete stop now -- do not commit, record provenance or re-run suites, the developer reviews the candidate") | post-pass overrun (10-20 turns, 2.6-9.8k tokens in all four pass-state cells) | the largest identifiable waste on the two build tasks; both arms do it | docs-linter: pass-state 3/5 -> maybe 0.4-0.5 pass rate if a 9B obeys the steer over the plan's Step 5 (unknown); run-record-gate: 1/9 -> ~0.15; depth-3: 0 | small (runner.ts `sendMessage` `deliverAs: "steer"`, generation already tracked at `runner.ts:468-475`); measuring needs a build-shaped dev task where Baseline overruns | real if made a hard stop: `511653`'s own suite was green at turn 34 with the hidden suite at 19/20, and it fixed the last case by turn 39; on floor tasks own-green coincided with hidden-pass in 7/7 cells that ran tests. Keep it a nudge |
| **Writable paths from the request's `Files: Create/Modify` block only** (not every path token; `derive.py:149-165`) | the errors.py trap in the Engine arm | the Engine cell edited `errors.py`; the grader rejects such patches | removes an Engine-only loss mode on run-record-gate; no lift | small | none |
| **Prompt collapse** (patterns, not file lists; `attempt.py:353-356, 385-389`) | ~3k tokens of prefill per turn and a writable/carried contradiction | prefill only; decode slows with context (probe: 55.9 -> 33.8 tok/s from 5k to 160k) | wall-clock only | small; three tests pin the format (`tests/test_attempt.py:171,252,297`) | none |
| **Per-turn output cap below the budget** (e.g. 8k) | the 32,000-token runaway turns (2 of 7 depth-3 cells) | real, but a sampling setting that must be identical across arms -- not an Engine change | none on the claim by itself | trivial to set; requires re-admission | n/a |

Stacked, the addressable items (batching, seeding, finish nudge, writable-path fix) plausibly take the Engine's docs-linter rate to 0.4-0.5 and run-record-gate to ~0.15. Against the thresholds (Baseline 0/12 needs >= 4/12; 1/12 needs >= 6/12; 2/12 needs >= 7/12 -- `evidence/stats.txt`), power at pe = 0.5 is 0.93 only if Baseline is 0/12, 0.60 at pb = 0.10, 0.26 at pb = 0.25; docs-linter's Baseline is not 0. Two tasks must reject; depth-3 cannot. P(win) after the day is a few percent.

## 3. Is the claim design the problem?

Partly. What is sound: fixing thinking level and sampling across arms; the Fisher rule; the futility look; the held-out tripwire; isolation.

What is not:

1. **The R1 rung for AgentClinic strips the one line that makes seam 3 solvable.** pytest's assertion explanation (`+ where None = datetime.datetime(...).tzinfo`) is assertion text, not location; including it would be a legitimate rung definition. It would probably turn depth-3 into a floor task for Ornith (depth-2 is 4/4 in 10-16 turns with the same two seams). Either way depth-3 does not discriminate arms.
2. **R1-plan on run-record-gate encodes decisions only the stripped code made.** Two of them (class location, validation location) decide 8 of 9 cells. That is a generator defect, not a ceiling. A ceiling task must be one the known-good author could reconstruct from the prompt alone; the qualification step ("the R1-plan prompt names no path outside base/ and files") does not check that the prompt determines the hidden suite's structural choices.
3. **The budget was set at the build tasks' finishing cost.** The spec's own note: "the build tasks' finishing cells used 27-38k tokens and 44-49 turns"; the budget is 32k/48. So the build "ceiling" is the budget line drawn through the middle of Baseline's finishing distribution. That is a legitimate thing to claim against ("delivers within budget more often") but it makes Baseline's rate 0.15-0.3, not <= 0.10, and the stipulated effect (0.10 vs 0.60) is far from anything the evidence supports.
4. **`max_tokens` per turn equals the whole budget.** A single runaway think ends a cell. Both arms, so not a bias; but it makes depth-3 outcomes a coin toss on whether turn 9 or 10 runs away. A per-turn cap (8k) applied to both arms, pre-registered, is legitimate and would need re-admission of every task.
5. **k = 3 fails the spec's own criterion** if the probe numbers in the brief are the whole story: total 60.7 tok/s at k = 3 versus 55.9 single-stream is 1.09x, and the spec requires >= 1.5x for k > 1. At equal total throughput k = 1 costs no wall-clock and removes the prefill-contention caveat. Verify against the probe record before changing.
6. **n and power.** n = 12 is fine for 0.10 vs 0.60; the effects on offer are <= 0.3. Also `P(Baseline >= 2/12 | p = 0.25) = 0.84`, so docs-linter is more likely than not to be declared under-powered.
7. **BUDGET_EXCEEDED discards the worktree.** The harness tears down without harvesting or grading (no `patch.diff` in any BUDGET_EXCEEDED cell; `workspace.py:1198-1220`), so the campaign cannot tell "never got there" from "got there and kept polishing". Retaining and grading the tripped worktree as a declared, reported-only secondary ("pass-state reached") is legitimate if written into the campaign record before night one; it does not touch the win rule.

A legitimate redesign, at a credibility cost of one paragraph in the campaign record: pre-register (a) the rung fix for AgentClinic, (b) a generator qualification check that the prompt determines the structural choices the hidden suite asserts, (c) a per-turn cap, (d) k per the probe rule, (e) the pass-state secondary; then re-admit. Cost: a day of harness work plus admission GPU (4 cells per candidate, ~25 min each at k = 3; less at k = 1 per cell but the same total). Changing the stipulated effect or the budget after seeing these numbers would be tuning; leave them.

## 4. Recommendation and decision tree

Day 0 (now): choose a branch.

**Branch A -- stated negative (recommended).** Half a day, no GPU. Result pages: one per ceiling task stating the binding constraint with the numbers above; one against the rule; the Phase 3b record (redirect fired 23 -> 2 bash pytest runs, gate 0 firings, outcomes unchanged) stands as is. Engine freezes at 8049d73, or at 8049d73 plus the three hygiene commits (multi-edit, prompt collapse, writable paths from `Files:`) reviewed as product fixes and not measured -- state which. Release-two backlog: sections 3 and 5.

**Branch B -- numbered negative.** One night, ~36 cells to the futility look (6 + 6 per task), ~5 h at k = 3. Stop rule already pre-registered. Justified only if a measured Engine rate per task is worth a night; the prediction is all three stop at futility (Engine <= 1/6). If any task shows >= 2/6 Engine with Baseline <= 1/6, continue that task to 12 the next day (the design allows it) -- but one task cannot win the release.

**Branch C -- real attempt.** Only with three or more days:

1. Day 1 (attended, ~2 h build, ~3 h GPU): fix run-record-gate's Interfaces line in the plan text (or widen `source_paths` to include `errors.py` and say where validation lives) and re-qualify; re-rung depth-3 (assertion explanation line) and re-admit it (expect it to move to the floor); cut one or two replacement ceiling candidates from later phase commits and admit them (4 Baseline cells each). Keep the held-out pair untouched.
2. Day 1-2 (Engine, Phase 3b): finish-on-green nudge, multi-edit, prompt collapse, writable-paths fix; Opus review; pin. Measure on one fresh build-shaped dev cut (not misleading-locus, not complaint-lifecycle: one is 5-turn easy, the other has no tests and no hidden suite, so neither can show the target behaviour) at n = 4 Engine + 4 Baseline. Go criterion: Engine finishes within budget in >= 2 of 4 where Baseline finishes in <= 1 of 4, and the finish nudge is visible in transcripts (a stop within 3 turns of the first green after a source mutation) in >= 3 of 4.
3. Day 3+: campaign record, Phase 4 night, held-out and floor day. Stop criterion at the futility look as designed.

Predicted P(win) for C: 20-30%, dominated by whether a replacement task exists whose Baseline is <= 1/12 and whose failure is budget-shaped.

## 5. Harness and evidence problems to fix or state

- **run-record-gate is not a valid ceiling task** (section 1.3). Its admission result (0/4 twice) measures the traps, not the model. State this on its result page even under Branch A.
- **depth-3 at R1 is not a valid ceiling task for the claim** (section 1.2): admission 0/4 measures an unguessable seam. The spec's "hunting is Ornith's dominant ceiling mechanism on depth-3" was true under contamination; under isolation the mechanism is a runaway think or a two-seam fix.
- **Engine derive lists paths the grader will reject** (`derive.py:149-150` vs manifest `source_paths`). Any Engine cell that edits a mentioned-but-not-listed file loses on `check_allowlist` (`patch.py:181-184`). This is an Engine-arm-only loss mode on every self-hosted task whose prompt mentions a file outside `Files:`.
- **Engine prompt is 3-4x Baseline's** and lists carried files as writable (`attempt.py:353-356, 385-389`; scope refuses them at `scope.ts:41-47`).
- **Engine edit schema forbids what Baseline's edit allows** (`mutator.ts:121-153` `maxItems: 1`); the "identical tools" premise is not quite met, to the Engine's disadvantage.
- **`self_test` on the self-hosted tasks runs the whole 1,900-test suite twice per call** (declared command, then command + preserve paths, `runner.py:302-324`), ~30 s each; with the 120 s deadline and k = 3 contention this is close to the bound. The redirect (128ce82) turns every `pytest tests/test_x.py -q` into that.
- **The completion gate cannot fire in a cell that never stops**; the ledger says so. It is a correct guard for a different failure mode than the ceiling cells show.
- **BUDGET_EXCEEDED worktrees are discarded** (section 3.7). The offline reconstruction here is a stand-in; the harness should retain and grade them as a reported secondary.
- **`max_tokens` = budget** (section 3.4).
- **k = 3 vs the 1.5x rule** (section 3.5) -- verify.
- **Phase 3b dev tasks cannot show the target behaviour**: misleading-locus passes in 5-11 turns; complaint-lifecycle has no tests and no hidden suite (`self_test` exit 5), so "self_test enforcement" had nothing to enforce. The ledger already notes this.
- **The ledger's "Engine 8049d73 is a safe improvement"** is right about behaviour (bash pytest 23 -> 2, all redirected) and says nothing about outcomes; keep that wording.
- **Evidence method caveat:** the reconstruction replays `write`, `edit` and heredoc/`sed -i` bash writes; it reproduced the harness verdict for 11 of 14 graded cells, missing 3 guard-prefixes cells whose decisive edits went through other bash forms. False negatives are possible on ceiling cells (a pass-state missed); false positives are not (a replay cannot invent passing code). Every ceiling pass-state named above is therefore a lower bound.

## Appendix: reproduce

```
python3 evidence/cells.py            # per-cell spend over ~/satyrn-runs -> cells.md/json
python3 evidence/reconstruct.py      # replay + offline grade every mutation snapshot -> recon.log/json, snapshots/
python3 evidence/stats.py            # thresholds, power, futility, P(>=2 of 3)
```
