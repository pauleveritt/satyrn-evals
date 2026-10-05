Approved 2026-10-03: the maintainer ruled D1-D7 in session ("go with D1-D7 recommendations"). Tasks 1-4 may be executed on the engine branch; Task 5 is attended and waits for C4's verdict.

# Engine Re-pin: Confinement Root, Red-stop Receipts, `edit` Parity (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One satyrn-engine commit that (1) moves the inner Pi's confinement root to the Engine's own worktree, (2) counts `self_test_red_stop` in receipts and drops the retired `self_test_redirected`, and (3) gives the Engine's `edit` what Pi 0.85.1's native `edit` has. After that, one attended evals task re-pins the three Engine arms to it and writes the ledger entry, before the first post-C4 Engine measurement.

**Architecture:** Tasks 1-4 are engine-only, test-first, one commit each, on an engine branch in its own git worktree. The sibling checkout stays detached at `1869397`, so evals launches still pass `engine_checkout_problems`. Task 5 is attended and does the evals side: arm pins, the evals guard vocabulary, one confinement fixture, `_engine/` sync, the ledger, and the smoke cell the design's "done when" names.

**Tech Stack:** Python 3.14, uv, pytest; Node `--experimental-strip-types` tests; Pi 0.85.1.

**Spec:** `docs/superpowers/specs/2026-10-02-engine-budget-design.md`: the ruling "Parity is not a remedy", the §3 rows "confinement fixes" and "R2 parity", and §7. Evidence: `evidence/2026-10-02-engine-budget/README.md` §3, §8, §8a, §8b; `evidence/2026-10-03-eb1-read/README.md` §2, §5; `evidence/2026-10-02-cleanup-audit/README.md` §2. Read both repositories' `AGENTS.md` before Task 1.

**Out of scope:** every EB2 remedy (the contract's test lines, edit-result echo trimming, self-test dedup and note hygiene, the light path, a scratch path); the parked engine branch `derive-new-top-level-module`; any model run other than Task 5's attended smoke cell.

**State of the checkouts (read 2026-10-03):** satyrn-engine is detached at `1869397`. `main` is `f9436aa`, which changes only `.github/workflows/gates.yml`, `AGENTS.md` and `BRIEF.md`. `BACKLOG.md` carries an **uncommitted change made by another session** (+25 lines, the cleanup-audit items). No task here touches it, stashes it, or commits it. Evals: `phase-c1` is checked out, and this plan sits on `worktree-engine-budget`.

## Rulings, 2026-10-03

**D1. Where the engine work lands.**
- Options: (A) branch `eb-confinement-parity` from `main` `f9436aa`, in a new worktree `../satyrn-engine-eb` (`git worktree add`). (B) Branch from `1869397`. (C) Work in the sibling checkout.
- **Ruled: A.** The `1869397..f9436aa` diff is docs and CI only (`git diff --stat`: 3 files, 5+/4-). The re-pin then targets a commit on `main` that the maintainer merges and pushes. That follows `f877551`, which pinned a merge commit, and `tools.engine_sync fetch` clones from GitHub, so the pin must be pushed.
- C is ruled out. It would move HEAD off the pin, so every Engine launch would refuse by name, and it would share a tree with the uncommitted `BACKLOG.md`.
- If wrong: B leaves the docs drift for a later re-pin. Nothing behavioural changes.
- Fact: the branch `eb-confinement-parity` and the worktree `../satyrn-engine-eb` were created by the controller on 2026-10-03 from `f9436aa`.

**D2. Who owns the confinement-root fix (item 1).**
- What each process knows, and when:
  - The harness exports `SATYRN_CONFINEMENT_ROOT` = the eval worktree before `deliver` starts (evals `src/satyrn_evals/attempt.py:427-436`).
  - `deliver` allocates `$TMPDIR/satyrn-engine-*/worktree` later, with `mkdtemp` on the realpath'd temp dir (`delivery.py:1705-1724`). It runs the implementer there with the environment passed through (`delivery.py:854-857`).
  - `attempt` resolves that worktree as `context.repo` (`git rev-parse --show-toplevel`). It builds `child_environment` (`attempt.py:1209-1211`) and spawns Pi with `cwd=context.repo` (`attempt.py:410, 478`). `context.repo` is also the mutation context's `repo`, the root `scope.ts` and the mutator key by.
  - The harness never learns the path before Pi starts, so the harness cannot export it.
- Options:
  - (A) Engine. In `attempt._run`, when `SATYRN_CONFINEMENT_ROOT` is present, overwrite it with `os.fspath(context.repo)`. When it is absent, leave it absent.
  - (B) Harness. Stop exporting the root on the Engine arm, so `confinement.ts:51` falls back to `process.cwd()`, which is `context.repo`.
  - (C) Engine pops the variable, and the same fallback applies.
- **Ruled: A.** It is explicit, it is testable in the engine's default tier with `FakePi` (which records `environment`), and it does not depend on Pi's cwd or on a fallback that no fixture tests.
- A *moves* the root and never adds one. Today the inner Pi may `write` the eval worktree by absolute path, because that path is inside the old root. After A it may not.
- The cost: the engine names an eval variable. It already names `SATYRN_EXTRA_EXTENSIONS` for the same seam, so add it beside that one with the same docstring.
- If wrong: B is a two-line harness change. It is a harness fix, and it re-opens the same decisions as A (Task 5 Step 6).

**D3. The open item schema or a normalizer, and which shapes.**
- Pi's own behaviour, read from the code:
  - `edit.js:11-22`: TypeBox objects are open, but top-level `path` is **required**.
  - `prepareEditArguments` (`edit.js:44-72`) repairs three shapes: `edits` as a JSON string, a bare edit object, and legacy top-level `oldText`/`newText`.
  - Pi runs `prepareArguments` before validation, and `tool_call` hooks see the prepared, validated args (`agent-loop.js:387-411`; `agent-session.js:224-235`). Transcripts log the raw args (`agent-loop.js:298-302`).
- Engine schema rejections by shape, from `~/satyrn-runs/*/engine/*/transcript.txt`, counted from `tool_execution_end` errors that read "Validation failed":

| shape | EB0 (18 E cells) | R2 comparison (54) | Pi 0.85.1 | recommendation |
|---|---|---|---|---|
| per-item `path`, no top-level, one file | 17 | 67 | **refuses** (`path` required) | defer (remedy) |
| nested `{path, edits:[…]}`, one file | 5 | 16 | refuses | defer (remedy) |
| multi-file (nested or per-item) | 3 | 4 | refuses | stays refused |
| `edits` as a string | 1, unparseable | 5, all unparseable | repairs only if it parses | take Pi's repair; rescues 0 recorded |
| bare edit object / legacy top-level | 0 | 0 | repairs | take Pi's repair; rescues 0 recorded |
| no path anywhere | 0 | 3 | refuses | stays refused |

- Options:
  - (A) A `prepareArguments` that is Pi's three repairs exactly; schema unchanged.
  - (B) A plus hoisting the per-item path when every item names the same path string, and unwrapping the nested one-file shape.
  - (C) Open the schema (drop the top-level `required: path`).
- **Ruled: A (Pi's three repairs exactly; schema unchanged).** B is not taken; it is a remedy for EB2. C stays rejected. B goes beyond Pi, so under the ruling it is a remedy. EB1 §5 already gives it an estimate: rank 3, median 536 / mean 796 on guard-prefixes, mean 1,176 on review-script, an upper bound, partly scorable by replay.
- **Reject C.** With no top-level `path`, `scope.ts:39` and `confinement.ts` return `undefined` for a non-string path, so both guards would pass the call unseen. That widens confinement.
- A normalizer keeps the schema strict, as Pi's own docs advise, and lets the guards see a top-level path.
- If A is wrong: the post-C4 Engine read still carries schema retries until EB2. That costs at most those means per pass.
- If B were taken now: a parity read would include a remedy's effect, which confounds EB3's attribution (R0 §1.4).

**D4. Pi's fuzzy anchor fallback.**
- What Pi does (`edit-diff.js:31-49, 141-176, 215-262`):
  - It NFKC-normalizes, strips trailing whitespace per line, and folds smart quotes, dashes and special spaces.
  - It matches *every* edit against the original file.
  - It rewrites touched lines from the normalized base.
  - It also normalizes CRLF to LF and strips a BOM (`edit.js:118-122`).
- What the Engine does: exact bytes, applied in order, all-or-nothing, revision-checked (`mutation.py:388-416`). Engine spec E8 ruled "the engine still applies only an exact unique anchor" (`mutation.py:395`; E8 spec on tag `pre-release-one-2026-09-13`, evidence, not guidance).
- Options: (A) port it whole; (B) decline it and record a stated parity gap; (C) an offline count first.
- **Ruled: B (decline; a stated parity gap).** A writes bytes the model never sent onto a sha-checked revision. With in-order application, a fuzzy rewrite of item 1 also changes the base that item 2 is matched against, and Pi never has that case.
- Evidence: 6 `ANCHOR_MISSING` in 18 EB0 Engine cells (depth-3 2, guard 3, review 1). EB1 §7 says whether they would match fuzzily "cannot be measured from these cells".
- If wrong: at most the `ANCHOR_MISSING` retry means, guard 220 and review 237 output tokens per pass (EB1 §2, upper bounds).
- C is an instrument-only piece, and choosing it would count toward the two-piece stop.

**D5. Descriptions and guidelines: verbatim from Pi 0.85.1, or adapted.**
- Pi's text says edits are "matched against the original file, not incrementally" in three places: the `edits` description, guideline 3, and `oldText`'s "unique in the original file". The Engine applies items in order against the evolving buffer (`replace_many`). A verbatim copy would tell the model something false.
- **Ruled: adapt only those three sentences and the tool description; everything else verbatim.** Task 3 lists every line. If wrong, a verbatim copy invites overlapping-anchor plans that get `ANCHOR_MISSING`.
- Adding the guidelines grows every Engine request. The −125-token saving in README §3 *is* the missing text. State that in the ledger.

**D6. The timing rule.**
- ROADMAP C4 says "before any Engine build". The design says parity and the confinement fixes "may land in the same re-pin … before the first post-C4 Engine measurement".
- **Ruled:** Tasks 1-4 are built now on the branch; no re-pin and no Engine cell before C4's verdict; C4's "before any Engine build" is read as remedies. Building is not measuring, and the arm keeps pinning `1869397` until Task 5.
- If the maintainer reads C4 literally, Tasks 1-4 wait. Nothing else changes.

**D7. The receipt key.**
- Options: (A) replace `self_test_redirected` with `self_test_red_stop` in `GUARD_KINDS` and `GuardFirings`. (B) Add red-stop and keep the fossil at 0.
- **Ruled: A**, as the audit names it.
- The cost lands on evals. `test_the_two_trees_guard_kinds_sets_agree` (evals `tests/integration/test_engine_arm_pins.py`) requires the two sets to be equal, and evals keeps `self_test_redirected` so old transcripts classify (`pathology.py:59-77`). Task 5 splits out `RETIRED_GUARD_KINDS`.
- No evals source reads a receipt's `guard_firings`: `cell_evidence.py:629` counts from the transcript.

## Open questions (not established from the files)

1. Whether Pi's descriptions and guidelines alone remove the per-item-path shape. Baseline, which runs under them, has 0 such rejections in 18 EB0 cells and 0 in R2's 54. Only a model run answers this, after the re-pin.
2. Whether the engine's integration tier can import Pi 0.85.1's `validateToolArguments` from the volta install without an `npm install` (Task 4 Step 6 skips when it cannot). The default tier cannot run Pi's validator.
3. Whether a model would spell the Engine worktree `/var/folders/…` when the root is `/private/var/folders/…`. `inside()` is lexical. Pi reports `process.cwd()`, the realpath, to the model, so it should not.
4. Whether throwing from `prepareArguments` is a supported Pi contract. Pi 0.85.1 catches it as an error result (`agent-loop.js:409-411, 451-456`), but its docs do not say. Moot under the D3 ruling; it matters only to a later hoisting remedy.

## Design text the code contradicts

- **README §3 and design §2 item 2:** "82 of 95 are shapes Pi's own edit accepts or repairs". Pi 0.85.1 requires top-level `path` and never hoists one. Its own Baseline rejection in EB0 reads "path: must have required properties path". Pi refuses the per-item and nested shapes too. Its repairs rescue **0** of 26 EB0 Engine rejections and 0 of 95 in R2.
- **Design §3 "R2 parity" row:** it lists "single agreed per-item path, nested one-file" as parity. On the code, they are a remedy (D3).
- **Design §3 "confinement fixes":** the row describes refusals only. Today the inner Pi can also *write the eval worktree* by absolute path, because the root names it. The fix closes a widening as well as a false refusal.
- **Not in the design:** evals `pathology.py` `GUARD_KINDS` lacks `self_test_red_stop`, so a red-stop firing would make an Engine cell `unknown_event` (`pathology.py:260`). The integration agreement test passes only because both lists are equally stale. EB0 is unaffected: 0 `self_test_red_stop` entries in 18 Engine transcripts.

## Global Constraints

- Engine default tier: no model, network or subprocess (`tests/conftest.py`). Node `--test` files run under `just gates`. Run named integration files only when a step says so; none of them runs a model.
- Every refusal test has a sibling success test. Guards are proven by replay before they run live.
- Read every gate's exit code (`just gates; echo "exit $?"`). Never pipe a gate.
- Every new engine file gets a `PROVENANCE.md` row (`created in EB re-pin`), checked by `tools/provenance.py check` in `just gates`.
- Never merge, push or launch. Never touch engine `BACKLOG.md`. Never run a model.
- Stop at anything this plan did not foresee, at a step that fails acceptance twice, or at a red gate whose fix is not here.

## Review Focus

1. **A re-export that widens instead of moving.** Setting the root when the harness did not, or leaving the eval worktree inside it. Task 1 tests both, plus `SATYRN_CONFINEMENT_ROOTS` passing through untouched.
2. **A copied guideline that contradicts in-order application.** Task 3 pins the three adapted sentences and asserts that no registered string contains "original file".
3. **A normalizer that guesses.** Under A it never touches `path`. Hoisting is not taken (D3); it is an EB2 remedy.
4. **A normalizer that mutates its input.** Pi's own `prepareEditArguments` assigns `args.edits` in place. The Engine's must return a new object, so the session history keeps what the model sent. Task 4 tests `Object.isFrozen` input.
5. **The receipt key drift recurring.** Task 2 adds a source scan: every kind `packages/engine/*.ts` emits is in `GUARD_KINDS`, and every `GUARD_KINDS` entry is emitted.
6. **Digests pinned to the wrong bytes.** Task 5 computes them with `git show <commit>:packages/engine/<name>`, never from a working tree, and runs `test_engine_arm_pins.py`.
7. **The evals audit is blind to hoisted paths.** The transcript logs raw args, so `confinement.audit` and `cell_evidence` would not see a path that only a normalizer put at top level. Moot under D3 = A, where the repairs never touch `path`; it is a blocker for any later hoisting remedy until evals reads item paths.

---

### Task 1: The inner Pi's confinement root is the attempt worktree (engine)

**Files:** modify `src/satyrn_engine/attempt.py` (constants block at lines 31-40; `_run` at lines 1209-1211); `tests/test_attempt.py` (beside `test_attempt_loads_the_extra_extensions_named_in_the_environment`, line 362, whose setup this copies).

- [ ] **Step 1: Write the failing tests (both directions).**
  - (a) `test_attempt_moves_the_confinement_root_to_its_own_worktree`. The environment holds `CONFINEMENT_ROOT_ENV: "/evals/worktree"` and `"SATYRN_CONFINEMENT_ROOTS": "/evals/tasks:/evals/tasks/t"`. Assert `pi.environment[CONFINEMENT_ROOT_ENV] == os.fspath(repo)`, `!= "/evals/worktree"`, and `ROOTS` unchanged.
  - (b) The sibling, `test_attempt_without_a_confinement_root_adds_none`: assert `CONFINEMENT_ROOT_ENV not in pi.environment`.
  - (c) `test_the_moved_root_is_the_mutation_contexts_repo`: assert `json.loads(pi.environment[MUTATION_CONTEXT_ENV])["repo"] == pi.environment[CONFINEMENT_ROOT_ENV]`.
- [ ] **Step 2:** Run `uv run pytest -q tests/test_attempt.py -k confinement; echo "exit $?"`. Expected: exit 1, `AttributeError: … CONFINEMENT_ROOT_ENV`.
- [ ] **Step 3: The change.**
  - Add `CONFINEMENT_ROOT_ENV = "SATYRN_CONFINEMENT_ROOT"` under `EXTRA_EXTENSIONS_ENV`. Its comment: the caller's confinement extension names a root; the Pi it confines runs here, so the root this process hands Pi is `context.repo`; present only when the caller set it.
  - In `_run`, after line 1211: `if CONFINEMENT_ROOT_ENV in child_environment: child_environment[CONFINEMENT_ROOT_ENV] = os.fspath(context.repo)`.
- [ ] **Step 4:** Run `uv run pytest -q tests/test_attempt.py; echo "exit $?"` (exit 0), then `just gates; echo "exit $?"` (exit 0).
- [ ] **Step 5: Commit.** `attempt: hand the inner Pi its own worktree as the confinement root`. The body cites design §3 and evidence README §8, says it moves the root and never adds one, and ends with the attribution line.

### Task 2: Red-stop firings reach receipts (engine)

**Files:** modify `src/satyrn_engine/budget.py:16-27`, `src/satyrn_engine/delivery.py:255-279`, `tests/test_budget.py:104-127`, `tests/test_delivery.py:237-262`, and `tests/test_integration_delivery.py` (four payload literals, lines 194, 521, 818, 910).

- [ ] **Step 1: Write the failing tests.**
  - (a) `test_guard_kinds_carries_self_test_red_stop`.
  - (b) The refusal sibling, `test_guard_kinds_no_longer_carries_the_retired_redirect`: `"self_test_redirected" not in GUARD_KINDS`.
  - (c) In `test_counter_sums_…`: feed `_entry("self_test_red_stop")` and `_entry("self_test_redirected")`. Expect `self_test_red_stop: 1` and no `self_test_redirected` key. The retired kind is now dropped like `unknown_kind`.
  - (d) `test_every_emitted_guard_kind_is_counted_and_every_counted_kind_is_emitted`. Read `packages/engine/*.ts` as text (a file read, no subprocess). Collect `note\("(\w+)"` and `appendEntry\("(\w+)"`, plus `loop_broken`, which `engine.ts:168` emits through a decision object. Assert the set equals `set(GUARD_KINDS)`.
  - (e) In `test_delivery.py`: the payload expectation lists `self_test_red_stop: 0` in place of `self_test_redirected`.
- [ ] **Step 2:** Run `uv run pytest -q tests/test_budget.py tests/test_delivery.py; echo "exit $?"`. Expected: exit 1 on (a), (b), (c), (d) and (e).
- [ ] **Step 3: The change.**
  - Replace `"self_test_redirected"` with `"self_test_red_stop"` in `GUARD_KINDS`, keeping it after `self_test_enforced`.
  - Rename the `GuardFirings` field to match.
  - Update the four integration payload literals and the budget docstring.
  - The count is one per gate run, pass or follow-up, as `self_test_enforced` counts. Say so in the field's comment (`runner.ts:590-600` appends on every run).
- [ ] **Step 4:** Run `uv run pytest -q tests/test_budget.py tests/test_delivery.py; echo "exit $?"` (exit 0). Run `uv run pytest -q -m integration tests/test_integration_delivery.py tests/test_integration_steered_session.py; echo "exit $?"` (exit 0). Then run `just gates; echo "exit $?"` (exit 0).
- [ ] **Step 5: Commit.** `receipts: count self_test_red_stop, drop the retired self_test_redirected`. Cite cleanup audit §2. Do not edit `BACKLOG.md`: closing that entry is the maintainer's, after the other session's change lands.

### Task 3: `edit` descriptions and guidelines (engine)

**Files:** modify `packages/engine/mutator.ts:127-159` (`EditParameters`) and `:394-406` (`registerMutator`); `tests/test_mutator.mjs` (beside "the bounded edit registers a prompt snippet…", line 601).

Text. *V* = verbatim from Pi 0.85.1 `edit.js:11-30`; *A* = adapted, with the reason.
- `path`: "Path to the file to edit (relative or absolute)" *V*.
- `newText`: "Replacement text for this targeted edit." *V*.
- `oldText`: "Exact text for one targeted replacement. It must appear exactly once in the file as the earlier replacements in this call left it." *A*: in-order application (`mutation.py` `replace_many`).
- item `path`: "Optional. If given, it must equal the top-level path." *A*: Engine-only key (`parseEditInput`).
- `edits`: "One to sixteen targeted replacements, applied in order: each oldText is matched against the file as the earlier replacements left it. If two changes touch the same block or nearby lines, merge them into one edit instead." *A*: in-order application and `MAX_EDITS`; Pi's last sentence is kept.
- `description`: "Edit one contract-declared file using exact text replacement. Replacements apply in order and all-or-nothing; each edits[].oldText must match exactly one region of the file as the earlier replacements left it. Do not include large unchanged regions just to connect distant changes." *A*; Pi's last sentence is kept.
- `promptSnippet`: kept as is (it already names the restriction).
- `promptGuidelines`:
  1. "Use edit for precise changes (edits[].oldText must match exactly)" *V*.
  2. "When changing multiple separate locations in one file, use one edit call with multiple entries in edits[] instead of multiple edit calls" *V*.
  3. "edits[] entries are applied in order: each oldText is matched after the earlier entries are applied. Merge nearby changes into one edit." *A*.
  4. "Keep edits[].oldText as small as possible while still being unique in the file. Do not pad with large unchanged regions." *V*.

- [ ] **Step 1: Write the failing tests.**
  - (a) Every `EditParameters` property, at both levels, has a non-empty `description`.
  - (b) The registered tool has `promptGuidelines` of length 4, equal to the list above.
  - (c) The refusal direction: no registered string (description, snippet, guidelines, every property description) matches `/original file|not incrementally/`.
  - (d) The schema is unchanged: `required`, `additionalProperties: false` at both levels, `maxItems: 16`. The existing "the edit item tolerates path and nothing else" test stays.
- [ ] **Step 2:** Run `node --test --experimental-strip-types tests/test_mutator.mjs; echo "exit $?"`. Expected: exit 1 on (a) and (b).
- [ ] **Step 3:** Add the text above.
- [ ] **Step 4:** Run `node --test --experimental-strip-types tests/test_mutator.mjs; echo "exit $?"` (exit 0), then `just gates; echo "exit $?"` (exit 0).
- [ ] **Step 5: Commit.** `edit: Pi's parameter descriptions and guidelines, adapted where the Engine applies in order`. The body names the three adapted sentences and design §3, R2 parity.

### Task 4: Pi's argument repairs, before validation (engine)

**Files:**
- Modify `packages/engine/mutator.ts`: export `prepareEditArguments`, and pass `prepareArguments` in `registerMutator`.
- Create `tests/fixtures/edit-shapes/*.json`, one per shape below.
- Modify `tests/test_mutator.mjs` to load and replay them.
- Add a `PROVENANCE.md` row per fixture.
- Fixture pattern: `tests/fixtures/guards/loop-breaker-edit-schema-retry.json`. That means `name`, a `source` naming the recorded cell, the recorded call's keys and paths verbatim, and `oldText`/`newText` cut to short strings that keep the shape. Add `expected: {prepared: <object or null>, unchanged: bool}`.

Shapes, D3 = A:
- `edits-json-string` (synthetic: none of the recorded strings parse) → parsed array.
- `edits-json-string-unparseable` (source: the EB0 depth-3 Engine cell holding the truncated string) → returned unchanged, so Pi's validator refuses it.
- `bare-edit-object` → wrapped.
- `legacy-top-level` → folded, `edits` last-appended as Pi does.
- `per-item-path-no-top-level` (source: EB0 review-script, 17 such) → unchanged: **stays refused**.
- `nested-one-file` (source: EB0 guard-prefixes, 5 such) → unchanged: **stays refused**.
- `multi-file-nested` (source: EB0 depth-3, 3 such) → unchanged: **stays refused**.
- `canonical` → returned as the same object (Pi's `prepareToolCallArguments` keeps identity).

- [ ] **Step 1: Write the failing tests.**
  - (a) Each fixture: `prepareEditArguments(structuredClone(input))` deep-equals `expected.prepared`, or `input` when `unchanged`.
  - (b) A frozen input is never mutated. That is the success direction for repaired shapes; refused shapes return the same frozen object.
  - (c) The registered tool's `prepareArguments === prepareEditArguments`.
  - (d) For each repaired shape: `createMutator(...).execute` on the prepared object reaches the exchange once. The success sibling of the refused shapes, whose prepared objects still fail `parseEditInput` with `INVALID_REQUEST`, asserted on the model-facing text.
  - (e) Unchanged: "an item path that contradicts the file path is refused before exchange" (line 320) still passes. That is the existing by-name multi-file refusal when a top-level `path` is present.
- [ ] **Step 2:** Run `node --test --experimental-strip-types tests/test_mutator.mjs; echo "exit $?"`. Expected: exit 1, `prepareEditArguments` is not exported.
- [ ] **Step 3: The change.**
  - Port `edit.js:31-72`'s logic as a pure function that copies before it assigns.
  - Register it with `prepareArguments`.
- [ ] **Step 4:** Run `node --test --experimental-strip-types tests/test_mutator.mjs; echo "exit $?"` (exit 0) and `node --experimental-strip-types tools/replay_guards.mjs; echo "exit $?"` (exit 0; the loop breaker sees nothing new).
- [ ] **Step 5: Integration-tier proof against Pi's own validator.** In `tests/test_integration_mutator.py`, add a test that resolves Pi 0.85.1's `pi-ai` from `$(dirname $(readlink -f $(which pi)))/../lib/node_modules/...` and runs `validateToolArguments` on each fixture's prepared object against the registered schema. Repaired shapes validate; refused shapes fail. The test skips, naming the reason, when Pi is absent or not 0.85.1. Run `uv run pytest -q -m integration tests/test_integration_mutator.py; echo "exit $?"`. Expected: exit 0, or a named skip that the report states.
- [ ] **Step 6:** Run `just gates; echo "exit $?"`. Expected: exit 0.
- [ ] **Step 7: Commit.** `edit: Pi's argument repairs before validation; per-item and nested shapes stay refused`. The body carries the D3 table's counts.

**An executing agent stops here.** Report the four engine commits, their gate exits, and any integration skips. Merging, pushing, the re-pin and the smoke cell are the maintainer's.

---

### Task 5: Re-pin the Engine arms and write the ledger (attended, the maintainer)

Runs after C4's verdict (D6), after the maintainer merges the branch to engine `main` and pushes. `<E>` is that merge commit.

**Files (evals):**
- `arms/engine-ornith15-9b.json`, `arms/engine-mellum-class-swe-pi.json`, `arms/engine-mellum-class-swe-pi-redstop.json`
- `tests/test_arms.py:358`, `tests/test_engine_sync.py:32`
- `src/satyrn_evals/pathology.py:59-83`, `tests/test_pathology.py`, `tests/integration/test_engine_arm_pins.py`
- `tests/fixtures/confinement/engine-worktree-root.json`
- `_engine/` (via `just sync-engine`)
- `evidence/2026-09-15-release-one-decision-ledger.md`, `PROVENANCE.md`

Steps:
- [ ] **Step 1: Move the sibling checkout.** `git -C ../satyrn-engine status --short` must show only the other session's `BACKLOG.md` change, or nothing if that has landed. Then run `git -C ../satyrn-engine checkout --detach <E>`.
- [ ] **Step 2: Digests from the commit's bytes.** `for f in engine mutator scope bounds runner orchestrator paths; do printf '%s ' $f.ts; git -C ../satyrn-engine show <E>:packages/engine/$f.ts | shasum -a 256; done`. Write `engine_commit` and the seven digests into all three arms. Also run `git -C ../satyrn-engine ls-tree --name-only <E> packages/engine/`, which must list no new `.ts` file.
- [ ] **Step 3: The evals guard vocabulary.**
  - `GUARD_KINDS` becomes the engine's list at `<E>` (with `self_test_red_stop`, without `self_test_redirected`).
  - A new `RETIRED_GUARD_KINDS = frozenset({"self_test_redirected"})`. The vocabulary accepts `GUARD_KINDS | EVAL_GUARD_KINDS | RETIRED_GUARD_KINDS`.
  - Tests, both directions: a transcript with `self_test_red_stop` is not `unknown_event`; one with `self_test_redirected` (old route proofs) still classifies; an unknown kind is still `unknown_event`.
- [ ] **Step 4: Confinement fixture.** `root: "engine/worktree"`, `roots: ["corpus"]`. Calls:
  - `read {temp}/engine/worktree/app.py`: admitted, the absolute in-root case.
  - `write {temp}/evals/worktree/app.py`: refused, the eval worktree is now outside.
  - `edit app.py`: admitted.
  - `read ../../corpus/x`: refused.

  Expected: `blocked: 2`.
- [ ] **Step 5: Update the pins, then gates.** Update the two pinned-commit test literals and run `just sync-engine`. Then `just gates; echo "exit $?"` (exit 0) and `uv run pytest -q -m integration tests/integration/test_engine_arm_pins.py tests/integration/test_confinement_extension.py; echo "exit $?"` (exit 0).
- [ ] **Step 6: The ledger entry.** Append `## <date> — Engine re-pin <E>: confinement root, red-stop receipts, edit parity`, stating:
  - (a) What changed and D1-D7 as ruled.
  - (b) **Decisions whose evidence the root defect could have produced**, each marked UNCONFIRMED (`<E>`) until re-derived: EB0's Engine admission tally (18 of 18 admitted, 0 `confinement_refused`); spec §7 "admission is arm-asymmetric".
  - (c) The re-derivation that clears (b) offline: every Engine file-tool path in the 18 EB0 cells was relative (README §8b; recount from `tool_execution_start`, one per call). The old root could neither refuse nor wrongly admit them, so the tally stands. State the count found.
  - (d) Evidence that is now about engine `1869397` only and never pools with `<E>` cells: EB0's Engine cells, EB1 §2's retry rows and §5's ranks 3/3b, README §3's rejection counts.
  - (e) Re-measured because the arm changed: EB3's floor read and the primary task (design §3); every EB2 estimate built on EB0 Engine cells names `1869397`.
  - (f) The Engine prompt grew by the guidelines and descriptions (D5).
  - (g) Fuzzy matching is declined as a stated parity gap (D4).
- [ ] **Step 7: The smoke cell (model run, launched by the maintainer only).** Issue a development record mirroring `records/2026-10-02-eb0-smoke-agentclinic-repair-depth-3.json` at `<E>`, frozen, and launch it with `satyrn-evals launch`. Done when the cell passes and is admitted with 0 `confinement_refused`. The absolute-path case is proven by Step 4 and Task 1, not by this cell.
- [ ] **Step 8:** Add PROVENANCE rows, run `just gates; echo "exit $?"` (exit 0), and commit `engine: re-pin the three Engine arms to <E> (confinement root, red-stop receipts, edit parity)`.
