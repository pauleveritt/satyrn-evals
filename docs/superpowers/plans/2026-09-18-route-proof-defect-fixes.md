# Route-proof defect fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Engine defects that made the 2026-09-18 route proof void, stage the census exclusion row, and pre-register the second route proof.

**Architecture:** The route proof was read as "steer 0 of 4", but the steer's trigger could not fire: the Engine's `self_test` returns exit 2 on this repo because `run_tests` appends the contract's `preserve` paths and pytest collects the fixture trees the repo's `norecursedirs` excludes. The launcher preflight must run the task's own self-test on the unmodified base and on the known-good patch and require exit 0. The Engine's budget follows the record (48,000/72) on both arms, wired like the backstop, because the Engine must have no stop the record does not name. The redirect is not widened by parsing commands: an unredirected command runs as written, and the Engine detects pytest's summary line in the output, then runs its own self-test once when a source mutation has landed since the last observed one.

**Tech Stack:** Python 3.14 (`satyrn-engine`, `satyrn-evals`), TypeScript (Engine extension), pytest, node:test, uv.

**Spec:** the maintainer's 2026-09-18 route-proof review and rulings, and `docs/superpowers/specs/2026-09-17-release-two-engine-design.md` §7. Evidence: `records/2026-09-17-route-proof-engine-*.result.json`, `~/satyrn-runs/2026-09-17-route-proof-engine-*`.

## Global Constraints

- The default test tier uses no model, network, or subprocess; the tripwire in each repo's `tests/conftest.py` enforces it. Process behaviour is the `integration` tier.
- Every refusal test has a sibling success test.
- Grade from hook-written evidence, never stdout or exit status. Count events from `tool_execution_start`.
- Commits with explicit paths; never merge, push, or amend.
- Every new engine file has a row in the engine's `PROVENANCE.md`; `just gates` fails without one.
- The engine repo is unfrozen at `9f80935`. The re-freeze needs a whole-path review scoped to the delta from `0b496d8`, and that review must run one live self-test on a real task base. Then the re-pin and the maintainer's export.
- The second route proof reports beside the first and never replaces it. The launch is the maintainer's, or a fresh recorded authorization.
- No Engine design before diagnosed admission and an offline estimate; these are harness fixes, so the second route proof must be re-read on the fixed harness.

## Rulings carried (maintainer, 2026-09-18)

- **The Engine's budget follows the record, 48,000 tokens and 72 turns, on both arms.** The contract's limits come from the record, wired the way the backstop was wired; an absent value is a hard error. The Engine has no stop the record does not name. The product default stays 32,000 for developers; only the eval contract changes.
- **The win rule reads the verdict at the 32,000 line, per arm, by the classifier's reconstruction, never by the exit code.** Both docs-linter route-proof cells "passed" at about 32,166 tokens, over the line; under identical budgets the line is a reconstruction reading. Put this in the R0 sitting's rules.
- **Do not parse shell to redirect a segment.** An unredirected command runs exactly as the model wrote it; the Engine detects pytest's summary line in the output, and when a source mutation has landed since the last observed self-test it runs its own self-test once and appends the compact result. A green result with a pending generation fires the steer. The cost is about 35 s, at most once per mutation generation. This changes model-visible text: the design gains one sentence and the numbers page discloses it.

---

### Task 1 (done, engine `41ddd1b`): `preserve` honours the repo's pytest-excluded directories

`derive_contract` drops any tracked `preserve` path under a `norecursedirs` entry. Default-tier test plus a mutation probe.

### Task 2 (done, engine `9f80935`): an excluded fixture tree self-tests green

Integration test: a repo whose own suite is green but whose `tests/data` fixture cannot import exits 0 through `run_tests`; RED when the Task 1 exclusion is removed.

### Task 4 (done, evals `8134c0d`): the census exclusion row, marked trigger unreachable

Also `9a05c81`: fixed the pre-existing red gate where the route-proof `.result.json` companions matched the "no fourth record" guard.

---

### Task 3: Evals — preflight the task's own self-test, per task base

**Files:**
- Modify: `satyrn-evals/src/satyrn_evals/cell_preflight.py` and/or `launch_record.py`'s preflight facts
- Modify: `satyrn-evals/scripts/census_night_3.sh` (and the route-proof launch scripts): run the evals gates after the result is committed
- Test: `satyrn-evals/tests/test_cell_preflight.py` (both directions), and the integration tier for a real base

**Interfaces:**
- Consumes: the task manifest's `public_suite`, the task's `base/` tree, `fixtures/known-good.patch`, the task-materialization machinery.
- Produces: a preflight problem when the unmodified base's self-test exits non-zero, or when the known-good patch is applied and the self-test still exits non-zero; empty when both exit 0. The record is refused on any problem.

- [ ] **Step 1:** Find how a task base is materialized and how `fixtures/known-good.patch` is applied in the integration tier; reuse that seam.
- [ ] **Step 2:** Write failing fixture tests both directions: a base whose suite exits 0 and whose known-good patch keeps it green adds no problem; a base whose suite exits 2 adds a problem naming the task and the exit code; a known-good patch that leaves the suite red adds its own problem.
- [ ] **Step 3:** Implement the check per task base, for every task an Engine record can name.
- [ ] **Step 4:** Run it on every Engine-nameable task base in the integration tier.
- [ ] **Step 5:** Add the gates-after-result step to the night/launch scripts.
- [ ] **Step 6:** Commit.

---

### Task 5: Engine — the contract budget comes from the record

**Files:**
- Modify: `satyrn-engine/src/satyrn_engine/attempt_engine.py` (read the env strictly), `attempt.py` (set it from the record, beside `SATYRN_COMMAND_BACKSTOP_S`), `derive.py`/CLI (the eval path passes the record's limits; the product default stays 32,000)
- Test: `satyrn-engine/tests/test_attempt_engine.py`, `tests/test_attempt.py`, and the evals-side integration row

**Interfaces:**
- Consumes: the record's `token_budget`/`turn_budget`, threaded the same way as `command_backstop_s`.
- Produces: the Engine's derived contract carries the record's limits; absent or unparseable env raises `AdapterError` on the eval path.

- [ ] **Step 1:** Read the backstop wiring (`SATYRN_COMMAND_BACKSTOP_S`) and mirror it for the two limits.
- [ ] **Step 2:** Failing test: the eval adapter refuses when the limit env is absent (refusal) and uses the record's value when present (sibling success).
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Confirm the product `derive` default is unchanged at 32,000.
- [ ] **Step 5:** Run the engine gates and integration; commit.

---

### Task 6: Engine — detect the test run in the output, leave the command alone

**Files:**
- Modify: `satyrn-engine/packages/engine/runner.ts` (remove the command-text redirect; add output-summary detection), `budget.py` (a guard kind), `docs/usage.md`
- Test: `satyrn-engine/tests/test_runner.mjs`, `tools/replay_events.mjs`
- Fixtures: `satyrn-engine/tests/fixtures/events/` for each form, both directions

**Forms (both directions each):** the compound with `git status`; the heredoc Python wrapper; a later bare run of that wrapper. Plus a silent row: output that quotes a summary line with no mutation generation must not fire.

- [ ] **Step 1:** Failing node tests: a `bash` result carrying pytest's summary line with a pending source generation runs self_test once and appends the compact result; without a generation it does not; a second run of the wrapper is detected on its own output.
- [ ] **Step 2:** Implement output detection; keep the completion gate and the steer as designed.
- [ ] **Step 3:** Replay fixtures; prove both directions for every form.
- [ ] **Step 4:** Run the engine gates and integration; commit.

---

### Task 7: Evals — design and numbers-page text

**Files:**
- Modify: `docs/superpowers/specs/2026-09-17-release-two-engine-design.md` (the output-detection sentence, the budget-follows-the-record rule), the R0 sitting's rules (win rule reads at the line by reconstruction), and the numbers page disclosure.

- [ ] **Step 1:** Add the one sentence naming the output-detection behaviour.
- [ ] **Step 2:** Add the budget rule and the win-rule rule to the R0 sitting's constraints.
- [ ] **Step 3:** Disclose the new model-visible text on the numbers page.
- [ ] **Step 4:** Commit.

---

### Task 8 (attended, out of this plan): whole-path review, re-freeze, re-pin, export, second route proof

Scoped whole-path review of the engine delta from `0b496d8`, including one live self-test on a real task base; then re-freeze, re-pin the arm, the maintainer's export, and one quiet night. Report the second route proof beside the void one.

## Self-review

- **Spec coverage:** item 1 → Tasks 1-3; item 2 → Task 6; item 3 → Tasks 5 and 7; item 4 → Task 8; item 5 → Task 4; the preflight self-test and the known-good row → Task 3; gates-after-result → Task 3.
- **Decisions recorded, not guessed:** the two rulings are in "Rulings carried" and drive Tasks 5-7.
- **Type consistency:** `derive_contract`, `Contract.preserve`, `RepoFacts`, `run_tests`, `CellPreflight`, `SATYRN_COMMAND_BACKSTOP_S` are the names used throughout.
