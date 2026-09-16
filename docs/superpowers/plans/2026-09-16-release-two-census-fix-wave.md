# Release two R0 — post-review fix wave (plan)

**Status: written 2026-09-16, after the maintainer's whole-path review of the census build (`590903e..02f3849`).** Executes the maintainer's four fix items plus the follow-up review. No model runs except the task-validity re-check, which is blocked in this harness (Task 5). Nothing is launched.

**Goal:** remove the two Criticals and the night-relevant Importants the whole-path review found, before the census night.

**Spec:** `docs/superpowers/specs/2026-09-15-release-two-census-design.md` (approved), bound by `...r0-constraints.md`. The maintainer's review of 2026-09-16 is the authority for this wave; where it changes the design's section 3.2 (tripped grading moves offline), the design is superseded for that point and the change is recorded in the ledger.

---

## Rulings (this wave)

1. **Tripped grading moves out of the cell path entirely.** `tripped.diff` is harvested at teardown (bounded git call) on both the normal-exit over-budget branch and the teardown branch; the attempt record no longer grades it. `tripped_verdict` becomes a classifier output (offline, day-after), not a run-record field. The V14 record generation keeps only `tripped_patch_path` (populated when the harvested patch exists), so the record still names the evidence; the verdict is computed where the other offline fields are.
2. **`self_stop` is keyed on the outcome code plus `agent_end`.** The design's Ruling 15 premise (every harness-cut cell lacks `agent_end`) is false on the retained corpus; `self_stop` is null for any cell the harness stopped (`BUDGET_EXCEEDED`, `COMMAND_TIMEOUT`, `REPEAT_LIMIT`, `DEADLINE_EXCEEDED`) even when an `agent_end` is present, and recorded only for a cell that ended on its own.
3. **`allowlist` requires a filtered grade.** A "non-source path" reason from an unfiltered grade is not allowlist evidence; the flag fires only when the patch with the non-source files removed still grades `pass` (the same filter `ignored_paths` uses), so the current four flags are false positives to be removed.
4. **`capability` is off when the tripped worktree grades pass.** A cell that reached a hidden-suite pass state in the torn-down worktree is a finishing/budget case, not capability, even though its delivered verdict is null.
5. **The classifier's census numbers must be comparable with run 2.** `source_edit_indices` is called with run 2's `bash_touched` route, not `{}`.

## Global constraints (carried)

- Roles: fresh implementer per task, a scoped review after each, one whole-path review at the end. No haiku.
- Build-only: no model, network, or `satyrn-evals launch`. The task-validity re-check (Task 5) is a cloud model working from text and is the only exception, and is blocked in this harness.
- Default test tier uses no model/network/subprocess; every refusal test has a sibling success test.
- Commit per task on `release-one` with explicit paths only; never `git add -A`/`.`/`-a`, amend, merge or push; `just gates` exit 0 before each commit, read directly.
- Every new file gets a PROVENANCE row. Nothing under `docs/results/` or `docs/reviews/`; nothing under `/tmp` or `/Users/Shared`; `~/satyrn-runs` is read-only.
- Tests verified in a scratch clone under the session scratchpad.

---

## Task 1 (Critical): take the tripped grade out of the cell's deadline path

**Files:** `src/satyrn_evals/workspace.py`, `src/satyrn_evals/attempt.py`, `src/satyrn_evals/attempt_record.py`; tests `tests/test_workspace_tripped_harvest.py`, `tests/test_attempt_tripped_verdict.py`.

1. `_harvest_tripped` gets a bounded git call (a timeout on the cumulative-patch build), so a teardown can never hang on git.
2. Harvest on the normal-exit over-budget branch (`workspace.py:1226`) as well as the teardown branch: an over-budget-on-normal-exit cell's worktree is the one with the most to say.
3. `attempt.py`: delete `_grade_tripped` and its call from `_finish_attempt`; the attempt record no longer runs the oracle for a tripped cell. `TRIPPED_RECEIPT_NAME` goes with it. The deadline-expiry recovery path can no longer re-enter grading.
4. `attempt_record.py`: the V14 generation is `{"tripped_patch_path"}`; `tripped_verdict` is removed. The writer drops `tripped_patch_path` when null; the loader accepts the shape. `_finish_attempt` sets `tripped_patch_path = "tripped.diff"` when the harvested file exists.
5. Tests: harvest fires on both branches; a tripped cell's attempt record carries `tripped_patch_path` and no verdict; no grading subprocess is spawned in the cell path (default-tier, faked); the deadline-expiry path does not grade; the record round-trips and older generations still load.

## Task 2 (Important): classifier fixes before the day-after review

**Files:** `src/satyrn_evals/census_classify.py`, `evidence/2026-09-16-census/classify.py`; tests `tests/test_census_classify.py`.

1. `Facts` gains `tripped_verdict` and `raised`; `capability` is `not passed and not reached and tripped_verdict != "pass"`; `allowlist` is `bool(facts.allowlist_reason and "non-source path" in ...)` only when the filtered grade is available (Ruling 3).
2. `classify.py` grades `<attempt_dir>/tripped.diff` offline into a `tripped_verdict` column and a filtered allowlist grade; `raised` is a column in both `table.md` and `classes.md`.
3. `self_stop` is nulled for harness-cut codes (Ruling 2).
4. `cf.source_edit_indices` is called with run 2's `bash_touched` route (Ruling 5).
5. Tests: `capability` off when tripped pass; `allowlist` off without a filtered pass; `self_stop` null on a cut cell with an `agent_end`; the driver still reproduces the committed run-2 numbers on the two retained nights.

## Task 3: promote the harvest test and update STATE.md

1. The real harvest test moves into the default tier with the git/patch build faked (both directions), so `just gates` exercises it.
2. `STATE.md` is updated across the range: the current direction, what is proven by this build, and that the census records are frozen and awaiting the night. It currently names the withdrawn ship-as-product direction as decided.

## Task 4: preserve the validity artefacts and correct the recorded commit

1. Copy each task's `solution.diff`, `REPORT.md`, leak-tell result and receipt under `evidence/2026-09-16-census/validity/<task>/`, with a README stating the model that ran and the harness limitation. (Superseded if Task 5 runs on Sonnet.)
2. `selfhost-cell-loop`'s `validity.commit` records the commit that carries the re-cut prompt (`fc870ba`), not `df33336`.

## Task 5 (blocked): re-run the five validity checks with Sonnet

The design names a Sonnet agent. This harness cannot select Sonnet (only `deepseek/deepseek-v4-flash` is configured; the subagent tool has no model selector). Blocked pending the maintainer's decision. If run, preserve `solution.diff`, the report and the tell results under `evidence/`, record the real commit, and treat a Sonnet failure of a task deepseek passed as a finding.

## Task 6: one fresh whole-path review

After A-D, one review by a reviewer who did not see the tasks, tracing a tripped cell from teardown to `classes.md`, plus the deadline path and the validity provenance. Findings adjudicated before the operator steps.
