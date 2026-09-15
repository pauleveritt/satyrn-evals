# Phase 3b — `self_test` enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-15 under the maintainer's approval of Phase 3b and this first remediation; the open design questions are decided below as Rulings, for the maintainer to review afterwards.** Planned against engine `release-one` at `56f4ac0` and evals `release-one` at `91b6da8`. Every test below was run in scratch clones before hand-back (see "Test verification"). Four tasks, about two hours.

**Goal:** When the Engine's model tests through bash, or stops without testing, the Engine answers with `self_test` itself. Each firing is counted on the receipt and in the evals evidence, so the development cells can show whether `self_test` use moved.

**Architecture:** Both mechanisms live in `packages/engine/runner.ts`, which already owns `self_test`. Task 1 is the redirect. A bash command that only runs pytest (with `cd`, `echo` or an output filter after a pipe, and nothing else) becomes `true`. Its result is replaced by the self-test's compact result under one sentence, and it is recorded as `self_test_redirected`. Task 2 is the completion gate. At the `turn_end` of a turn with no tool call, if no self-test has completed since the last landed `edit` or `write` (or none ever ran), the Engine runs `self_test`. It records `self_test_enforced`, and a failing run goes back to the model as one custom follow-up message, once per mutation generation. Task 3 is the evals side: `pathology.GUARD_KINDS` learns both kinds, and `cell_evidence` adds `self_test_calls`, `bash_test_runs` and `first_passing_self_test`. Task 4 re-pins the Engine arm to the new engine commit. The operator section after it runs the "after" development records and the reading against the operator's "before" records.

**Tech Stack:** TypeScript under Node's `--experimental-strip-types` (node:test), Pi 0.85.1's extension API, Python 3.14, uv, pytest, ruff, just, git.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md`: the phase table's row 3b ("each change shows its target behaviour moving on development cells; the engine commit freezes after it"), guard 2 in "The product" ("never running its own tests … self-test command in the loop"), "Measures, per cell" (guard firings), "The eval" (identical prompts). Evidence: the route-proof records `records/2026-09-15-route-proof-b-agentclinic-repair-depth-3*`, `…-selfhost-run-record-gate*` and `…-selfhost-docs-linter*`, with their cells under `~/satyrn-runs/2026-09-15-route-proof-*/engine/*/transcript.txt`, and the Baseline admission cells under `~/satyrn-runs/2026-09-1[45]-admission-*`. House style: the engine-arm route-proof plan.

## Rulings

1. **Design 1, the redirect, is adopted for pure test runs only.** A bash command is redirected when every simple command in it is a pytest invocation, or `cd`/`echo`/`printf`/`true`, or `tail`/`head`/`grep`/`egrep` on the receiving side of a pipe, and at least one is a pytest invocation. A pytest invocation is `pytest`, `py.test` or `python[3[.N]] -m pytest`. Each may carry leading `NAME=value`, `env`, a `timeout DURATION` wrapper, `uv run [options]` and any path or flag. Output redirection to `/dev/null` or another descriptor is allowed. Anything else voids the redirect: another program, a heredoc or `<`, a subshell, backticks, `$(…)` other than `$(pwd)`, a background `&`, or a redirection to a file. Such commands run untouched, because the Engine never drops work the model asked for. Evidence: over the 835 bash commands in the 44 retained cells of 2026-09-14 and 2026-09-15 (admission, first turn, route proof), 159 name pytest. The rule redirects 103 of them and fires on none of the other 676. The 56 it leaves are mixed with `ruff check`, `cat`, heredoc probes or `ls`. Mechanics: the `tool_call` handler sets `input.command = "true"` (Pi allows it; see the facts below) and appends the entry. The `tool_result` handler replaces the content with `redirectSentence(test_command)` plus the self-test's text. `isError` is set only on an engine refusal, as for the `self_test` tool itself. Blocking was rejected: a blocked call is an immediate error result that never reaches `tool_result`, so a passing suite would read as an error. Cost if wrong: a targeted probe (`pytest tests/_probe.py -k x`) loses its own selection, because the whole suite runs. The sentence says so. Evals counts the leftover pytest runs (`bash_test_runs` minus `self_test_redirected`).
2. **`python -c` probes and heredoc scripts are left alone.** They are not the test runner, and replacing them would destroy what the model asked to see. A nudge is already in place and already failed: `bounds.ts` appends "run it with the self_test tool" to every bash result. That sentence reached the docs-linter cell 31 times and the run-record-gate cell 38 times (their `command_bounded` counts), with no `self_test` call. The completion gate (Ruling 3) catches the end state instead.
3. **Design 2, the completion gate, is adopted: the Engine runs `self_test` itself and returns a failure as one follow-up.** The gate fires at `turn_end` when the turn's assistant message has no `toolCall` and its `stopReason` is not `error` or `aborted`. It fires only if `checked !== generation`. `generation` counts landed `edit`s (`details.satyrn && ok`) and non-error `write`s. `checked` is the generation that the last completed self-test (the model's tool, a redirect, or the gate) started against, and it is null until one completes. When the gate fires it runs `self_test`, sets `checked`, and appends `self_test_enforced {generation, code, exit_code, follow_up}`. A non-zero exit or a timeout sends `enforcedMessage(result)` as a custom message with `deliverAs: "followUp"`. A pass or an engine refusal sends nothing, and the session ends as it would have. So the gate fires at most once per generation and never loops on a broken engine. Bash-made mutations are not counted. A cell that edits only through bash still gets the "never checked" run once. Running the suite rather than asking for it saves the model a turn, and a passing run costs the model nothing. Cost if wrong: a model that saw its own failing `self_test` and then stops without changing anything is not gated again. It saw the failure.
4. **`turn_end` and `pi.sendMessage`, not `agent_end` and `pi.sendUserMessage`.** A follow-up queued from `agent_end` continues through a second `agent_start`/`agent_end` pair. Evals `pathology` reads more than one `agent_end` as `malformed`, which would void every gated cell. A follow-up queued from `turn_end` is drained by the same loop, so the run keeps one `agent_end` (Task 3's pathology row proves the shape measures). `sendUserMessage` goes through `_queueFollowUp`, which emits `queue_update` session events. Print mode writes every session event into the `--mode json` transcript, and `queue_update` is not in `pathology.EVENT_TYPES`. `sendMessage` with a custom type reaches the model as a user message, emits no `queue_update`, and names the Engine as its author in the transcript (`customType: "self_test_enforced"`).
5. **Design 3 (automatic `self_test` after a mutation batch) is not in this iteration.** Of the three route-proof cells, only run-record-gate would have fired it and not Design 1. It costs a suite run (about 30 s) at every edit-to-read transition, and docs-linter's edits interleaved with reads nine times. Measure 1 + 2 first. If the after cells still show edits followed by `python -c` probes and no self-test, Design 3 is the next remediation, with this evidence behind it.
6. **Design 4: the prompt is unchanged.** `attempt.build_prompt` already says "Verify with the self_test tool before finishing", and the route proof shows that wording alone does not move the model. The redirect sentence and the follow-up are the Engine's own tool results and messages, which the identical-prompt rule lets differ. An unchanged prompt keeps before and after comparable: only the mechanism moves.
7. **Firings are guard kinds in both trees.** The engine adds `self_test_redirected` and `self_test_enforced` to `budget.GUARD_KINDS` and to `delivery.GuardFirings`, so the receipt's `guard_firings` carries both (the five committed receipt fixtures gain the keys). Evals adds both to `pathology.GUARD_KINDS`. Without them every cell where either fires reads `unknown_event`. `cell_evidence` adds `self_test_calls` (`self_test` tool starts), `bash_test_runs` (any simple command runs pytest: broader than Ruling 1, so the leftover is measurable) and `first_passing_self_test` (`{turn, output_tokens, route}` with route `tool`, `redirected` or `enforced`). Before and after cells are both read with this code (the reading template), so the old export's cells get the same fields.
8. **Everything lives in `runner.ts`; no new module.** `arms.ENGINE_SOURCES` stays the seven files, `attempt.build_pi_command` is unchanged (`runner.ts` loads whenever the contract declares `test_command`, which `derive` always does), and only `runner.ts`'s digest changes in the arm (Task 4). The replay tool learns the self-test exchange and a `turn_end` event, so both guards are proven by replay like guards 1–3.
9. **The after measurement mirrors the operator's before, record for record.** The operator is running the before now: Engine at `56f4ac0`, `agentclinic-repair-misleading-locus` and `agentclinic-complaint-lifecycle`, n = 2 each, k = 3, isolated, `--purpose development`. The after reads each before record's `task`, `rung`, `n` and `k` and writes the same record at the new commit, with `--previous-result` set to that before result. The before is needed: neither development task has an Engine cell at `56f4ac0`, and the target is a change. No fresh self-hosted task is cut. The before sitting has none, so a cut would have no before, and a cut with offline qualification is a task of its own (the held-out cut added a `formats` text per hidden suite and thousands of provenance rows). Cost if wrong: build-shaped evidence rests on `complaint-lifecycle` alone, which is weak. Its `launch` contract is the manifest's one-sentence summary over a bare base with no tests (the four requests live in `session.json`, which only `session` runs), so its cells read for behaviour, not passes. Expect `self_test` to exit 5 there until the model writes tests, and expect the gate to fire after its writes.
10. **`misleading-locus`'s hidden suite is byte-identical to `depth-3`'s (spec, risks).** Development cells retain transcripts like any other, the overlay scan runs on them, and nothing in this change reads task content. This is an observation for the reading, not a remediation.
11. **No spec or roadmap edit; the freeze is the reading's.** Row 3b stays "in progress" until the maintainer reads the after records. The engine commit that freezes is Task 2's commit only if the reading shows the target moving. The spec is at 399 of 400 lines.

## Pi 0.85.1 facts relied on (read from the installed package, `~/.volta/tools/image/packages/@earendil-works/pi-coding-agent/lib/node_modules/@earendil-works/pi-coding-agent/`)

- `dist/core/extensions/types.d.ts` (`ToolCallEvent`): "`event.input` is mutable … Later `tool_call` handlers see earlier mutations. No re-validation is performed after mutation." `ToolCallEventResult` is `{block, reason, terminate}` only: a `tool_call` handler cannot supply a result.
- `dist/core/extensions/runner.js` `emitToolCall` runs every extension's handlers in load order (the `--extension` argv order: engine, mutator, scope, bounds, runner) and returns at the first `block`. `emitToolResult` runs all handlers over one event, merging each returned `content`/`details`/`isError`.
- `node_modules/@earendil-works/pi-agent-core/dist/agent-loop.js` `prepareToolCall`: a blocked call becomes `createErrorToolResult(reason)` with `isError: true` as an "immediate" result, which `executeToolCalls*` finalizes without `afterToolCall`, so no `tool_result` handler sees it (Ruling 1).
- Same file, `runLoop`: after each turn it `await emit({type: "turn_end"})`, then polls `getSteeringMessages`, and when the inner loop ends, `getFollowUpMessages`. A non-empty queue continues the same loop with a new `turn_start`, and `agent_end` is emitted once, when both queues are empty. `agent.js` `processEvents` awaits every listener, and `AgentSession._handleAgentEvent` awaits the extension emit (Ruling 4).
- `dist/core/agent-session.js`: `_handlePostAgentRun` says "Any messages here were queued by agent_end extension handlers and need a continuation" and calls `agent.continue()`, which runs a fresh `runAgentLoop` (a second `agent_start`/`agent_end`). `sendUserMessage` → `prompt` → `_queueFollowUp` → `_emitQueueUpdate` (`type: "queue_update"`). `sendCustomMessage` with `deliverAs: "followUp"` while `isStreaming` (`_isAgentRunActive`, true for the whole run) calls `agent.followUp` directly, with no queue event. The extension-facing `sendMessage`/`sendUserMessage` wrappers call these synchronously up to the enqueue.
- `dist/modes/print-mode.js`: in `--mode json` every session event is written to stdout (`session.subscribe` → `writeRawStdout(JSON.stringify(toJsonEvent(event)))`), and `session.prompt` is awaited before the runtime is disposed, so a continuation inside the run is part of the transcript.
- `dist/core/messages.js` `convertToLlm`: `case "custom"` becomes `{role: "user", content}`.
- Load order, checked live without a model: `pi --print … --model nope/nope --extension <a throwing extension>` prints `Failed to load extension … LOADED-BROKEN` before `Model "nope/nope" not found`. The same command with the five engine extensions at Task 2 prints only the model error (Task 2, Step 5).

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer per task; one Opus review per task before the next starts.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **No inference.** No `launch` of a real model, no request to oMLX. Task 2's load check runs `pi --print` with a model name Pi cannot resolve, which exits before any request. The operator commands at the end are the operator's, not the controller's.
- **Default test tiers: no model, no network.** Engine: `tests/conftest.py` forbids subprocesses in the default pytest tier. Node tests use fake `pi` objects and fake exchanges. Evals: the audit hook in `tests/conftest.py`. Anything that spawns is `@pytest.mark.integration`.
- **Every refusal test has a sibling success test; every detector has a firing row and a silent row.**
- **Every task ends with `just gates` exit 0 in the tree it changes** (read the exit code; never pipe a gate). Engine gates: pytest, ruff, the node tests, `replay_guards`, `replay_events`, `lint-docs`, provenance. Evals gates: pytest, ruff, `lint-docs`, provenance. New files get `PROVENANCE.md` rows (`uv run python tools/provenance.py new <paths>`); edited files keep theirs. Run `uv run ruff check --fix` before gates.
- **Commit at the end of every task** in the task's tree on `release-one`, with the plan's message. Never `--amend`, merge or push. A task whose gates are red is not committed.
- **Live cells come first.** Isolated `satyrn-cell` development cells may be running. Before any isolated integration row, `ls /Users/Shared/satyrn-cells | grep satyrn-attempt` must print nothing and no non-system `satyrn-cell` process may run. This plan's tasks need no isolated row. Never touch `/Users/Shared/satyrn-cells` or its `engine-56f4ac0…` export; only the operator changes the cells root. Tasks 1 and 2 (engine tree) may be built while the operator's before sitting runs. Tasks 3 and 4 commit to the evals checkout the launcher runs from, so they start only after the before sitting has ended and its results are committed.
- **Isolated rows run serially, never beside another cell-user run**, and skip with the reason when `sudo -n -u satyrn-cell true` fails.
- **Nothing is written to `/tmp` or `/private/tmp`** except under the session scratchpad `$SCR` (`/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/selftest-exec/`). Integration runs pass `--basetemp "$SCR/bt"` and `TMPDIR="$SCR/bt"`.
- **Engine checkout** `/Users/pauleveritt/projects/pauleveritt/satyrn-engine` (`ENGINE`), **evals checkout** `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` (`EVALS`). Starting points: engine `release-one` at `56f4ac0694be0abbf04fa61d4d1f49ddc20abd8a`; evals `release-one` at `91b6da8` plus whatever record and result commits the operator's before sitting added (this plan touches no record). The diff blocks apply with `git apply` from the tree's root. If one does not apply, apply it by hand to the same effect and say so in the task report.
- **Docs caps stand:** evals spec ≤ 400 lines, `ROADMAP.md` ≤ 150; `just lint-docs` exit 0 in both trees.

---

## File structure

```
satyrn-engine (Tasks 1, 2)
packages/engine/runner.ts                         # redirect (T1): shellSegments, isTestRunner, isTestRunCommand, redirectSentence;
                                                  # gate (T2): isFinalTurn, enforcedMessage, generation/checked, turn_end   (modify)
src/satyrn_engine/budget.py                       # GUARD_KINDS + self_test_redirected (T1), self_test_enforced (T2)        (modify)
src/satyrn_engine/delivery.py                     # GuardFirings fields, same two (T1, T2)                                  (modify)
tools/replay_events.mjs                           # fake `test` exchange (T1); `turn_end` events and sendMessage (T2)       (modify)
tests/test_runner.mjs                             # fakePi records every handler; redirect rows (T1); gate rows (T2)        (modify)
tests/fixtures/events/self-test-redirected.json, self-test-not-redirected.json (T1)                                          (new)
tests/fixtures/events/self-test-enforced.json, self-test-not-enforced.json (T2)                                              (new)
tests/test_budget.py, tests/test_delivery.py, tests/test_integration_delivery.py, tests/fixtures/delivery/*.json (T1, T2)    (modify)
docs/usage.md                                     # one sentence on both (T2)                                               (modify)

satyrn-evals (Tasks 3, 4)
src/satyrn_evals/pathology.py                     # GUARD_KINDS + both (T3)                                                 (modify)
src/satyrn_evals/cell_evidence.py                 # runs_pytest; self_test_calls, bash_test_runs, first_passing_self_test (T3) (modify)
tests/test_pathology.py, tests/test_cell_evidence.py (T3)                                                                    (modify)
arms/engine-ornith15-9b.json, tests/test_arms.py, tests/test_launch_record.py (T4: the new engine commit)                    (modify)
```

---

### Task 1: A bash command that only runs pytest is answered by `self_test` (engine)

**Files:**
- Modify: `packages/engine/runner.ts` (new exports above `registerRunner`; `registerRunner` gains a `tool_call` handler and a redirect branch in its `tool_result` handler), `src/satyrn_engine/budget.py` (`GUARD_KINDS`), `src/satyrn_engine/delivery.py` (`GuardFirings`), `tools/replay_events.mjs` (`fakeExchange` answers `operation: "test"`)
- Create: `tests/fixtures/events/self-test-redirected.json`, `tests/fixtures/events/self-test-not-redirected.json`
- Test: `tests/test_runner.mjs`, `tests/test_budget.py`, `tests/test_delivery.py`, `tests/test_integration_delivery.py`, `tests/fixtures/delivery/*.json`

**Interfaces:**
- Consumes: `createRunner(context, exchangeRequest)`, `RunnerToolResult`, `MutationContext.test_command`, `pi.appendEntry`.
- Produces (runner.ts): `REDIRECTED_COMMAND = "true"`; `shellSegments(command: string): {words: string[]; piped: boolean}[] | null`; `isTestRunner(words: readonly string[]): boolean`; `isTestRunCommand(command: string): boolean`; `redirectSentence(testCommand: readonly string[]): string`, which returns `The Engine ran self_test in place of this command: it runs "<test command>" over the whole suite, whatever paths or flags the command named.`. Entry `self_test_redirected {toolCallId}`. Python: `GUARD_KINDS` ends `"command_timed_out", "self_test_redirected"`; `GuardFirings.self_test_redirected: int = 0`. Replay: `FAKE_TEST_OUTPUT = "FAILED tests/test_app.py::test_home - assert 404 == 200"`, returned with `exit_code: 1` for every `test` request.

- [ ] **Step 1: Write the failing tests.** In `$ENGINE`, save this block as `$SCR/t1-tests.diff` and run `git apply "$SCR/t1-tests.diff"`, then add the new receipt key to the five committed receipts:

```diff
diff --git a/tests/fixtures/events/self-test-not-redirected.json b/tests/fixtures/events/self-test-not-redirected.json
new file mode 100644
index 0000000..03ed695
--- /dev/null
+++ b/tests/fixtures/events/self-test-not-redirected.json
@@ -0,0 +1,11 @@
+{
+  "name": "self-test-not-redirected",
+  "extension": "runner.ts",
+  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {}, "writable_paths": ["src/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
+  "expectedHandlers": {"tool_call": 1, "tool_result": 1},
+  "events": [
+    {"type": "tool_call", "toolCallId": "c1", "toolName": "bash", "input": {"command": "uv run pytest tests/test_review.py -q 2>&1 | tail -5; uv run ruff check", "timeout": 120}, "expect": {"blocked": false, "input": {"command": "uv run pytest tests/test_review.py -q 2>&1 | tail -5; uv run ruff check", "timeout": 120}}},
+    {"type": "tool_result", "toolCallId": "c1", "toolName": "bash", "input": {"command": "uv run pytest tests/test_review.py -q 2>&1 | tail -5; uv run ruff check", "timeout": 120}, "isError": false, "content": [{"type": "text", "text": "3 passed\nAll checks passed!"}], "details": {}, "expect": {"patched": false}}
+  ],
+  "expectedEntries": []
+}
diff --git a/tests/fixtures/events/self-test-redirected.json b/tests/fixtures/events/self-test-redirected.json
new file mode 100644
index 0000000..1c1dd05
--- /dev/null
+++ b/tests/fixtures/events/self-test-redirected.json
@@ -0,0 +1,11 @@
+{
+  "name": "self-test-redirected",
+  "extension": "runner.ts",
+  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {}, "writable_paths": ["src/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
+  "expectedHandlers": {"tool_call": 1, "tool_result": 1},
+  "events": [
+    {"type": "tool_call", "toolCallId": "c1", "toolName": "bash", "input": {"command": "cd /w && timeout 115 uv run python -m pytest tests/ -q 2>&1 | tail -30", "timeout": 120}, "expect": {"blocked": false, "input": {"command": "true", "timeout": 120}}},
+    {"type": "tool_result", "toolCallId": "c1", "toolName": "bash", "input": {"command": "true", "timeout": 120}, "isError": false, "content": [{"type": "text", "text": "(no output)"}], "details": {}, "expect": {"contentEndsWith": "Test command exited 1\nFAILED tests/test_app.py::test_home - assert 404 == 200"}}
+  ],
+  "expectedEntries": [{"kind": "self_test_redirected", "data": {"toolCallId": "c1"}}]
+}
diff --git a/tests/test_budget.py b/tests/test_budget.py
index 33fe478..ba07be1 100644
--- a/tests/test_budget.py
+++ b/tests/test_budget.py
@@ -111,11 +111,12 @@ def test_counter_sums_assistant_usage_tool_calls_and_guard_firings_only() -> Non
         '{"type":"tool_execution_start","toolName":"bash"}', _assistant(20, 70),
         '{"type":"message_update","usage":{"output":5000}}',
         _entry("loop_broken"), _entry("command_bounded"), _entry("command_bounded"), _entry("unknown_kind"),
+        _entry("self_test_redirected"),
     ):
         counter.feed(line)
     assert (counter.turns, counter.tokens_in, counter.tokens_out, counter.tool_calls) == (1, 120, 120, 1)
     assert counter.guard_firings == {"loop_broken": 1, "scope_refused": 0, "symbol_preserved": 0,
-                                     "command_bounded": 2, "command_timed_out": 0}
+                                     "command_bounded": 2, "command_timed_out": 0, "self_test_redirected": 1}


 def test_a_token_limit_trips_on_the_limit_plus_one() -> None:
diff --git a/tests/test_delivery.py b/tests/test_delivery.py
index 3110f9b..319b344 100644
--- a/tests/test_delivery.py
+++ b/tests/test_delivery.py
@@ -244,6 +244,7 @@ def test_guard_firings_come_from_the_counter_and_render_every_kind() -> None:
         "symbol_preserved": 0,
         "command_bounded": 2,
         "command_timed_out": 0,
+        "self_test_redirected": 0,
     }


diff --git a/tests/test_integration_delivery.py b/tests/test_integration_delivery.py
index 4bf5e62..12a201f 100644
--- a/tests/test_integration_delivery.py
+++ b/tests/test_integration_delivery.py
@@ -188,6 +188,7 @@ def test_clean_root_reaches_no_changes_without_touching_source(tmp_path: Path) -
             "symbol_preserved": 0,
             "command_bounded": 0,
             "command_timed_out": 0,
+            "self_test_redirected": 0,
         },
         "carried": {
             "preserve": [],
@@ -455,6 +456,7 @@ def test_success_creates_candidate_with_exact_parent_and_paths(tmp_path: Path) -
             "symbol_preserved": 0,
             "command_bounded": 0,
             "command_timed_out": 0,
+            "self_test_redirected": 0,
         },
         "carried": {
             "preserve": [],
@@ -744,6 +746,7 @@ def test_failed_attempt_is_discarded_without_candidate(
             "symbol_preserved": 0,
             "command_bounded": 0,
             "command_timed_out": 0,
+            "self_test_redirected": 0,
         },
         "carried": {
             "preserve": [],
@@ -803,6 +806,7 @@ def test_timeout_kills_same_process_group_descendant(tmp_path: Path) -> None:
             "symbol_preserved": 0,
             "command_bounded": 0,
             "command_timed_out": 0,
+            "self_test_redirected": 0,
         },
         "carried": {
             "preserve": [],
diff --git a/tests/test_runner.mjs b/tests/test_runner.mjs
index f260ff8..6b8b332 100644
--- a/tests/test_runner.mjs
+++ b/tests/test_runner.mjs
@@ -7,6 +7,9 @@ import runnerExtension, {
 	buildTestRequest,
 	createRunner,
 	parseTestResponse,
+	REDIRECTED_COMMAND,
+	isTestRunCommand,
+	redirectSentence,
 	registerRunner,
 } from "../packages/engine/runner.ts";
 import { createEngineExchange, parseMutationContext } from "../packages/engine/mutator.ts";
@@ -202,6 +205,91 @@ test("registered tool marks a refusal as an error but not a failing suite", asyn
 	assert.equal(await pi.resultHandler({ toolName: "read", details: null }), undefined);
 });

+// Phase 3b: guard 2 enforced. Commands observed in the route-proof and
+// admission transcripts (~/satyrn-runs/2026-09-1[45]-*), worktree paths shortened.
+const TEST_RUNS = [
+	"uv run python -m pytest -q",
+	"pytest",
+	'cd "$(pwd)"; uv run pytest tests/test_lint_docs.py -q 2>&1 | tail -25',
+	"cd /w/worktree; timeout 115 uv run python -m pytest -q 2>&1 | tail -40",
+	"cd /w/worktree\nuv run pytest tests/ -q 2>&1 | tail -15",
+	"cd /w/worktree && uv run pytest tests/its.py -q 2>&1 | tail -6",
+	'uv run python -m pytest tests/_probe.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR"',
+	"PYTHONPATH=src python3 -m pytest -x tests/test_a.py::test_b",
+	'.venv/bin/pytest -q >/dev/null 2>&1; echo "EXIT: $?"',
+	"uv run --frozen pytest -k lint",
+];
+
+const NOT_TEST_RUNS = [
+	'uv run pytest tests/test_review.py -q 2>&1 | tail -5; echo "===RUFF==="; uv run ruff check tools/review.py',
+	"cat tests/conftest.py; uv run pytest -q",
+	"head -20 tests/test_provenance.py; uv run pytest tests/test_provenance.py -q",
+	"cd /w && cat > /tmp/probe_test.py <<'EOF'\ndef test_x():\n    assert True\nEOF\nuv run pytest /tmp/probe_test.py",
+	'uv run python -c "import app; print(app)"',
+	"uv run pytest -q > out.txt",
+	"uv run pytest -q &",
+	"uv run pytest -q | tee log.txt",
+	"echo $(uv run pytest -q)",
+	"grep -rn pytest tests/",
+	"just test",
+	"timeout uv run pytest",
+	"uv run pytest 'tests/test_a.py",
+];
+
+test("a bash command that only runs the test runner is a test run; one doing anything else is not", () => {
+	for (const command of TEST_RUNS) assert.equal(isTestRunCommand(command), true, command);
+	for (const command of NOT_TEST_RUNS) assert.equal(isTestRunCommand(command), false, command);
+});
+
+test("a test run through bash becomes true, is recorded, and its result is the self-test's under one sentence", async () => {
+	const pi = fakePi();
+	const requests = [];
+	registerRunner(pi.api, context(), async (request) => {
+		requests.push(JSON.parse(request));
+		return success({ exit_code: 1, output: "FAILED tests/test_a.py::test_b - assert 1 == 2" });
+	});
+	const [onCall] = pi.handlers.tool_call;
+	const [onResult] = pi.handlers.tool_result;
+	const call = { toolCallId: "c1", toolName: "bash", input: { command: "uv run pytest tests/test_a.py -q 2>&1 | tail -5", timeout: 120 } };
+	assert.equal(await onCall(call), undefined);
+	assert.deepEqual(call.input, { command: REDIRECTED_COMMAND, timeout: 120 });
+	assert.deepEqual(pi.entries, [{ kind: "self_test_redirected", data: { toolCallId: "c1" } }]);
+	const patch = await onResult({ toolCallId: "c1", toolName: "bash", input: call.input, isError: false,
+		content: [{ type: "text", text: "(no output)" }], details: undefined });
+	assert.deepEqual(patch, {
+		content: [{ type: "text", text: `${redirectSentence(context().test_command)}\nTest command exited 1\nFAILED tests/test_a.py::test_b - assert 1 == 2` }],
+		isError: false,
+	});
+	assert.equal(redirectSentence(context().test_command),
+		'The Engine ran self_test in place of this command: it runs "uv run python -m pytest -q" over the whole suite, whatever paths or flags the command named.');
+	assert.equal(requests.length, 1);
+	assert.equal(requests[0].operation, "test");
+	// Consumed once: a second result for the same id is not redirected again.
+	assert.equal(await onResult({ toolCallId: "c1", toolName: "bash", content: [], details: undefined }), undefined);
+});
+
+test("a redirected run the engine refuses is an error result; any other bash call is untouched", async () => {
+	const pi = fakePi();
+	let exchanges = 0;
+	registerRunner(pi.api, context(), async () => {
+		exchanges += 1;
+		return { version: 1, ok: false, code: "TEST_COMMAND_UNAVAILABLE", message: "gone", result: null };
+	});
+	const [onCall] = pi.handlers.tool_call;
+	const [onResult] = pi.handlers.tool_result;
+	await onCall({ toolCallId: "r1", toolName: "bash", input: { command: "pytest" } });
+	const refused = await onResult({ toolCallId: "r1", toolName: "bash", content: [], details: undefined });
+	assert.equal(refused.isError, true);
+	assert.match(refused.content[0].text, /TEST_COMMAND_UNAVAILABLE: gone$/);
+	const other = { toolCallId: "o1", toolName: "bash", input: { command: "uv run ruff check" } };
+	assert.equal(await onCall(other), undefined);
+	assert.deepEqual(other.input, { command: "uv run ruff check" });
+	assert.equal(await onResult({ toolCallId: "o1", toolName: "bash", content: [{ type: "text", text: "ok" }], details: undefined }), undefined);
+	assert.equal(await onCall({ toolCallId: "x1", toolName: "read", input: { path: "pytest" } }), undefined);
+	assert.equal(exchanges, 1);
+	assert.deepEqual(pi.entries.map((entry) => entry.kind), ["self_test_redirected"]);
+});
+
 test("default extension leaves the tool set alone without explicit context", () => {
 	const pi = fakePi();
 	runnerExtension(pi.api, {});
@@ -316,22 +404,27 @@ test("base response parser rejects non-object JSON without leaking a type error"

 function fakePi() {
 	let tool;
-	let resultHandler;
+	const handlers = {};
+	const entries = [];
 	return {
 		api: {
 			registerTool(candidate) {
 				tool = candidate;
 			},
 			on(event, handler) {
-				assert.equal(event, "tool_result");
-				resultHandler = handler;
+				(handlers[event] ??= []).push(handler);
+			},
+			async appendEntry(kind, data) {
+				entries.push({ kind, data });
 			},
 		},
+		handlers,
+		entries,
 		get tool() {
 			return tool;
 		},
 		get resultHandler() {
-			return resultHandler;
+			return handlers.tool_result?.[0];
 		},
 	};
 }
diff --git a/tools/replay_events.mjs b/tools/replay_events.mjs
index 7161b6b..8fab717 100644
--- a/tools/replay_events.mjs
+++ b/tools/replay_events.mjs
@@ -58,9 +58,22 @@ function fakePi() {

 /** Resolves `{version:1, ok:true, code:"OK", message:"", result:{...}}` from
  * whatever `path` the request named, with a fixed digest -- exactly enough
- * shape for a guard fixture that never inspects the engine's real reply. */
+ * shape for a guard fixture that never inspects the engine's real reply. A
+ * `test` request (Phase 3b's redirected and enforced self-tests) gets one
+ * failing test with its assertion line. */
+export const FAKE_TEST_OUTPUT = "FAILED tests/test_app.py::test_home - assert 404 == 200";
+
 async function fakeExchange(request) {
 	const parsed = JSON.parse(request);
+	if (parsed.operation === "test") {
+		return {
+			version: 1,
+			ok: true,
+			code: "OK",
+			message: "",
+			result: { exit_code: 1, output: FAKE_TEST_OUTPUT, truncated: false, timed_out: false },
+		};
+	}
 	return {
 		version: 1,
 		ok: true,
```

```bash
sed -i '' 's/"command_timed_out":0}/"command_timed_out":0,"self_test_redirected":0}/' tests/fixtures/delivery/*.json
grep -c self_test_redirected tests/fixtures/delivery/*.json   # 1 in each of the five
```

- [ ] **Step 2: Run them and watch them fail for the missing implementation only.**

```bash
node --test --experimental-strip-types tests/test_runner.mjs 2>&1 | grep -E "SyntaxError|ℹ fail"
# SyntaxError: The requested module '../packages/engine/runner.ts' does not provide an export named 'REDIRECTED_COMMAND'
node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"
# replay_events: self-test-not-redirected: expectedHandlers.tool_call 1 != 0   EXIT: 1
uv run pytest -q tests/test_budget.py tests/test_delivery.py 2>&1 | tail -1
# 7 failed, 83 passed
```

- [ ] **Step 3: Implement.** Save this block as `$SCR/t1-impl.diff` and run `git apply "$SCR/t1-impl.diff"`:

```diff
diff --git a/packages/engine/runner.ts b/packages/engine/runner.ts
index 591470a..e7625ae 100644
--- a/packages/engine/runner.ts
+++ b/packages/engine/runner.ts
@@ -233,8 +233,180 @@ export function createRunner(context: MutationContext, exchangeRequest: Exchange
 	};
 }

+/**
+ * Guard 2, enforced (Phase 3b). The route proof's three Engine cells never
+ * called `self_test` although the prompt named it and every bash result
+ * repeated it (`bounds.ts`); Baseline admission cells ran pytest through
+ * bash 0-16 times per self-hosted cell. A bash command that only runs the
+ * repository's test runner is answered by `self_test` instead: the command
+ * becomes `true`, and its result is the self-test's compact result under
+ * one sentence saying so. A command that does anything else as well runs
+ * untouched -- the Engine never drops work the model asked for.
+ */
+export const REDIRECTED_COMMAND = "true";
+
+const RUNNER_PROGRAMS = new Set(["pytest", "py.test"]);
+const PYTHON = /^python(?:3(?:\.\d+)?)?$/;
+/** Segments that may accompany a test run anywhere: they change nothing a test reads. */
+const ALONGSIDE = new Set(["cd", "echo", "printf", "true"]);
+/** Output filters, allowed only on the receiving side of a pipe. */
+const FILTERS = new Set(["tail", "head", "grep", "egrep"]);
+/** `uv run` options that take a separate value. */
+const UV_RUN_VALUE_FLAGS = new Set([
+	"--with", "--with-requirements", "--project", "--directory", "--python", "-p", "--group",
+	"--extra", "--package", "--env-file", "--index",
+]);
+
+interface Segment {
+	readonly words: string[];
+	readonly piped: boolean;
+}
+
+/**
+ * Split a bash command into simple commands, quote-aware. Returns null for
+ * anything this reading cannot vouch for: command substitution (other than
+ * `$(pwd)`), backticks, subshells, input redirection, a background `&`, an
+ * output redirection to anything but `/dev/null` or another descriptor, or
+ * an unclosed quote. Null means "not a pure test run".
+ */
+export function shellSegments(command: string): Segment[] | null {
+	if (command.replaceAll("$(pwd)", "").includes("$(") || command.includes("`")) return null;
+	const segments: { words: string[]; piped: boolean }[] = [{ words: [], piped: false }];
+	let word = "";
+	let inWord = false;
+	let quote: "'" | '"' | null = null;
+	const endWord = () => {
+		if (inWord) segments[segments.length - 1].words.push(word);
+		word = "";
+		inWord = false;
+	};
+	const next = (piped: boolean) => {
+		endWord();
+		segments.push({ words: [], piped });
+	};
+	for (let i = 0; i < command.length; i++) {
+		const c = command[i];
+		if (quote === "'") {
+			if (c === "'") quote = null;
+			else word += c;
+			continue;
+		}
+		if (quote === '"') {
+			if (c === '"') quote = null;
+			else if (c === "\\" && i + 1 < command.length) word += command[++i];
+			else word += c;
+			continue;
+		}
+		if (c === "'" || c === '"') {
+			quote = c;
+			inWord = true;
+		} else if (c === "\\") {
+			if (command[i + 1] === "\n") i++;
+			else if (i + 1 < command.length) {
+				word += command[++i];
+				inWord = true;
+			}
+		} else if (c === " " || c === "\t") {
+			endWord();
+		} else if (c === "\n" || c === ";") {
+			next(false);
+		} else if (c === "|") {
+			if (command[i + 1] === "|") {
+				i++;
+				next(false);
+			} else next(true);
+		} else if (c === "&" && command[i + 1] === "&") {
+			i++;
+			next(false);
+		} else if (c === ">" || (c === "&" && command[i + 1] === ">")) {
+			if (inWord && !/^\d+$/.test(word)) return null;
+			word = "";
+			inWord = false;
+			let j = c === "&" ? i + 2 : i + 1;
+			if (command[j] === ">") j++;
+			if (command[j] === "&") {
+				j++;
+				const start = j;
+				while (j < command.length && /\d/.test(command[j])) j++;
+				if (j === start) return null;
+			} else {
+				while (command[j] === " " || command[j] === "\t") j++;
+				const start = j;
+				while (j < command.length && !" \t\n;|&".includes(command[j])) j++;
+				if (command.slice(start, j) !== "/dev/null") return null;
+			}
+			i = j - 1;
+		} else if (c === "&" || c === "<" || c === "(" || c === ")") {
+			return null;
+		} else {
+			word += c;
+			inWord = true;
+		}
+	}
+	if (quote !== null) return null;
+	endWord();
+	return segments.filter((segment) => segment.words.length > 0);
+}
+
+function basename(word: string): string {
+	return word.slice(word.lastIndexOf("/") + 1);
+}
+
+/** Leading `NAME=value` assignments, `env`, and a `timeout [flags] DURATION` wrapper. */
+function unwrap(words: readonly string[]): string[] {
+	let rest = [...words];
+	while (rest.length > 0 && (rest[0] === "env" || /^[A-Za-z_][A-Za-z0-9_]*=/.test(rest[0]))) rest = rest.slice(1);
+	if (rest[0] === "timeout") {
+		rest = rest.slice(1);
+		while (rest.length > 0 && rest[0].startsWith("-")) rest = rest.slice(1);
+		if (rest.length === 0 || !/^\d+(?:\.\d+)?[smhd]?$/.test(rest[0])) return [];
+		rest = rest.slice(1);
+	}
+	return rest;
+}
+
+/** `pytest`, `py.test`, `python[3[.N]] -m pytest`, each optionally under `uv run [options]`. */
+export function isTestRunner(words: readonly string[]): boolean {
+	let rest = unwrap(words);
+	if (rest.length >= 2 && basename(rest[0]) === "uv" && rest[1] === "run") {
+		rest = rest.slice(2);
+		while (rest.length > 0 && rest[0].startsWith("-")) {
+			const flag = rest[0];
+			rest = rest.slice(UV_RUN_VALUE_FLAGS.has(flag) ? 2 : 1);
+		}
+		rest = unwrap(rest);
+	}
+	if (rest.length === 0) return false;
+	if (RUNNER_PROGRAMS.has(basename(rest[0]))) return true;
+	return PYTHON.test(basename(rest[0])) && rest[1] === "-m" && rest[2] === "pytest";
+}
+
+/** True only for a command whose every segment is a test run, a harmless companion, or a filter after a pipe. */
+export function isTestRunCommand(command: string): boolean {
+	const segments = shellSegments(command);
+	if (segments === null) return false;
+	let runs = false;
+	for (const { words, piped } of segments) {
+		if (isTestRunner(words)) runs = true;
+		else if (!ALONGSIDE.has(words[0]) && !(piped && FILTERS.has(words[0]))) return false;
+	}
+	return runs;
+}
+
+export function redirectSentence(testCommand: readonly string[]): string {
+	return `The Engine ran self_test in place of this command: it runs "${testCommand.join(" ")}" over the whole suite, whatever paths or flags the command named.`;
+}
+
 export function registerRunner(pi: ExtensionAPI, context: MutationContext, exchangeRequest: ExchangeRequest): void {
 	const runner = createRunner(context, exchangeRequest);
+	const redirected = new Set<string>();
+	const note = async (kind: string, data: Record<string, unknown>): Promise<void> => {
+		try {
+			await pi.appendEntry(kind, data);
+		} catch {
+			// Evidence, not permission.
+		}
+	};
 	pi.registerTool({
 		name: "self_test",
 		label: "Run the contract's self-test",
@@ -252,7 +424,24 @@ export function registerRunner(pi: ExtensionAPI, context: MutationContext, excha
 		parameters: TestParameters,
 		execute: runner.execute,
 	});
+	pi.on("tool_call", async (event) => {
+		// Pi: `event.input` is mutable and later handlers and the tool see the
+		// mutation (core/extensions/types.d.ts, ToolCallEvent).
+		if (event.toolName !== "bash" || !isRecord(event.input) || typeof event.input.command !== "string") return undefined;
+		if (!isTestRunCommand(event.input.command)) return undefined;
+		event.input.command = REDIRECTED_COMMAND;
+		redirected.add(event.toolCallId);
+		await note("self_test_redirected", { toolCallId: event.toolCallId });
+		return undefined;
+	});
 	pi.on("tool_result", async (event) => {
+		if (event.toolName === "bash" && redirected.delete(event.toolCallId)) {
+			const result = await runner.execute(event.toolCallId, {});
+			return {
+				content: [{ type: "text", text: `${redirectSentence(context.test_command)}\n${result.content[0].text}` }],
+				isError: result.details.ok !== true,
+			};
+		}
 		if (event.toolName !== "self_test" || !isRecord(event.details) || event.details.satyrn !== true) {
 			return undefined;
 		}
diff --git a/src/satyrn_engine/budget.py b/src/satyrn_engine/budget.py
index fe1d991..fc77aef 100644
--- a/src/satyrn_engine/budget.py
+++ b/src/satyrn_engine/budget.py
@@ -19,6 +19,7 @@ GUARD_KINDS: tuple[str, ...] = (
     "symbol_preserved",
     "command_bounded",
     "command_timed_out",
+    "self_test_redirected",
 )


diff --git a/src/satyrn_engine/delivery.py b/src/satyrn_engine/delivery.py
index f04ecee..87d74c0 100644
--- a/src/satyrn_engine/delivery.py
+++ b/src/satyrn_engine/delivery.py
@@ -261,6 +261,7 @@ class GuardFirings:
     symbol_preserved: int = 0
     command_bounded: int = 0
     command_timed_out: int = 0
+    self_test_redirected: int = 0

     @classmethod
     def from_counter(cls, counter: TurnCounter) -> GuardFirings:
```

- [ ] **Step 4: Run the tests, then the gates.**

```bash
node --test --experimental-strip-types tests/test_runner.mjs 2>&1 | grep -E "ℹ (pass|fail)"   # pass 23, fail 0
node --experimental-strip-types tools/replay_events.mjs | grep self-test
# {"name":"self-test-not-redirected","events":2,"entries":0}
# {"name":"self-test-redirected","events":2,"entries":1}
uv run python tools/provenance.py new tests/fixtures/events/self-test-redirected.json tests/fixtures/events/self-test-not-redirected.json
uv run ruff check --fix
just gates; echo "EXIT: $?"   # EXIT: 0; pytest 494 passed; node ℹ pass 146
TMPDIR="$SCR/bt" uv run pytest -m integration -q --basetemp "$SCR/bt/t1" tests/test_integration_delivery.py tests/test_integration_runner_tool.py tests/test_integration_implement.py; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Commit** (engine tree).

```bash
git add packages/engine/runner.ts src/satyrn_engine/budget.py src/satyrn_engine/delivery.py tools/replay_events.mjs tests/test_runner.mjs tests/test_budget.py tests/test_delivery.py tests/test_integration_delivery.py tests/fixtures/delivery tests/fixtures/events/self-test-redirected.json tests/fixtures/events/self-test-not-redirected.json PROVENANCE.md
git commit -m "Phase 3b: a bash command that only runs pytest is answered by self_test (self_test_redirected)"
```

---

### Task 2: When the model stops untested, the Engine runs `self_test` and returns a failure once (engine)

**Files:**
- Modify: `packages/engine/runner.ts` (`enforcedMessage`, `isFinalTurn`; `registerRunner` tracks `generation`/`checked`, wraps the tool's `execute`, counts landed `edit`/`write`, and adds a `turn_end` handler), `src/satyrn_engine/budget.py`, `src/satyrn_engine/delivery.py`, `docs/usage.md`, `tools/replay_events.mjs` (`turn_end` events; fake `sendMessage`)
- Create: `tests/fixtures/events/self-test-enforced.json`, `tests/fixtures/events/self-test-not-enforced.json`
- Test: `tests/test_runner.mjs`, `tests/test_budget.py`, `tests/test_delivery.py`, `tests/test_integration_delivery.py`, `tests/fixtures/delivery/*.json`

**Interfaces:**
- Consumes: Task 1's `registerRunner`, `REDIRECTED_COMMAND`, the redirect branch, and `note`.
- Produces (runner.ts): `enforcedMessage(resultText: string): string`, which returns `Before you finish: the Engine ran self_test because nothing had run it since the last change, and it did not pass.\n<resultText>`; `isFinalTurn(message: unknown): boolean`. Entry `self_test_enforced {generation: number, code: string, exit_code: number | null, follow_up: boolean}`. The follow-up is `pi.sendMessage({customType: "self_test_enforced", content: enforcedMessage(text), display: true, details: undefined}, {deliverAs: "followUp"})`. Python: `GUARD_KINDS` ends `"self_test_redirected", "self_test_enforced"`; `GuardFirings.self_test_enforced: int = 0`. Replay fixture vocabulary: `{"type": "turn_end", "message": …, "expect": {"followUp": false | "<text the one follow-up contains>"}}`.

- [ ] **Step 1: Write the failing tests.** Save as `$SCR/t2-tests.diff`, `git apply "$SCR/t2-tests.diff"`, then extend the receipts:

```diff
diff --git a/tests/fixtures/events/self-test-enforced.json b/tests/fixtures/events/self-test-enforced.json
new file mode 100644
index 0000000..0961f73
--- /dev/null
+++ b/tests/fixtures/events/self-test-enforced.json
@@ -0,0 +1,13 @@
+{
+  "name": "self-test-enforced",
+  "extension": "runner.ts",
+  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {"app.py": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "writable_paths": ["app.py", "tests/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
+  "expectedHandlers": {"tool_call": 1, "tool_result": 1, "turn_end": 1},
+  "events": [
+    {"type": "tool_result", "toolCallId": "e1", "toolName": "edit", "input": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}, "isError": false, "content": [{"type": "text", "text": "1 b"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"path": "app.py", "sha256": "1111111111111111111111111111111111111111111111111111111111111111", "region": "1 b"}}, "expect": {"patched": false}},
+    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "toolUse", "content": [{"type": "toolCall", "id": "e1", "name": "edit", "arguments": {}}]}, "expect": {"followUp": false}},
+    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": "The fix is in app.py."}]}, "expect": {"followUp": "Test command exited 1\nFAILED tests/test_app.py::test_home - assert 404 == 200"}},
+    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": "The fix is in app.py."}]}, "expect": {"followUp": false}}
+  ],
+  "expectedEntries": [{"kind": "self_test_enforced", "data": {"generation": 1, "code": "OK", "exit_code": 1, "follow_up": true}}]
+}
diff --git a/tests/fixtures/events/self-test-not-enforced.json b/tests/fixtures/events/self-test-not-enforced.json
new file mode 100644
index 0000000..c7575bd
--- /dev/null
+++ b/tests/fixtures/events/self-test-not-enforced.json
@@ -0,0 +1,13 @@
+{
+  "name": "self-test-not-enforced",
+  "extension": "runner.ts",
+  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {"app.py": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "writable_paths": ["app.py", "tests/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
+  "expectedHandlers": {"tool_call": 1, "tool_result": 1, "turn_end": 1},
+  "events": [
+    {"type": "tool_result", "toolCallId": "e1", "toolName": "edit", "input": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}, "isError": false, "content": [{"type": "text", "text": "1 b"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"path": "app.py", "sha256": "1111111111111111111111111111111111111111111111111111111111111111", "region": "1 b"}}, "expect": {"patched": false}},
+    {"type": "tool_call", "toolCallId": "b1", "toolName": "bash", "input": {"command": "uv run python -m pytest -q 2>&1 | tail -5", "timeout": 120}, "expect": {"blocked": false, "input": {"command": "true", "timeout": 120}}},
+    {"type": "tool_result", "toolCallId": "b1", "toolName": "bash", "input": {"command": "true", "timeout": 120}, "isError": false, "content": [{"type": "text", "text": "(no output)"}], "details": {}, "expect": {"contentEndsWith": "assert 404 == 200"}},
+    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": "The fix is in app.py."}]}, "expect": {"followUp": false}}
+  ],
+  "expectedEntries": [{"kind": "self_test_redirected", "data": {"toolCallId": "b1"}}]
+}
diff --git a/tests/test_budget.py b/tests/test_budget.py
index ba07be1..4862bdc 100644
--- a/tests/test_budget.py
+++ b/tests/test_budget.py
@@ -111,12 +111,13 @@ def test_counter_sums_assistant_usage_tool_calls_and_guard_firings_only() -> Non
         '{"type":"tool_execution_start","toolName":"bash"}', _assistant(20, 70),
         '{"type":"message_update","usage":{"output":5000}}',
         _entry("loop_broken"), _entry("command_bounded"), _entry("command_bounded"), _entry("unknown_kind"),
-        _entry("self_test_redirected"),
+        _entry("self_test_redirected"), _entry("self_test_enforced"),
     ):
         counter.feed(line)
     assert (counter.turns, counter.tokens_in, counter.tokens_out, counter.tool_calls) == (1, 120, 120, 1)
     assert counter.guard_firings == {"loop_broken": 1, "scope_refused": 0, "symbol_preserved": 0,
-                                     "command_bounded": 2, "command_timed_out": 0, "self_test_redirected": 1}
+                                     "command_bounded": 2, "command_timed_out": 0, "self_test_redirected": 1,
+                                     "self_test_enforced": 1}


 def test_a_token_limit_trips_on_the_limit_plus_one() -> None:
diff --git a/tests/test_delivery.py b/tests/test_delivery.py
index 319b344..bb0dfeb 100644
--- a/tests/test_delivery.py
+++ b/tests/test_delivery.py
@@ -245,6 +245,7 @@ def test_guard_firings_come_from_the_counter_and_render_every_kind() -> None:
         "command_bounded": 2,
         "command_timed_out": 0,
         "self_test_redirected": 0,
+        "self_test_enforced": 0,
     }


diff --git a/tests/test_integration_delivery.py b/tests/test_integration_delivery.py
index 12a201f..276908c 100644
--- a/tests/test_integration_delivery.py
+++ b/tests/test_integration_delivery.py
@@ -189,6 +189,7 @@ def test_clean_root_reaches_no_changes_without_touching_source(tmp_path: Path) -
             "command_bounded": 0,
             "command_timed_out": 0,
             "self_test_redirected": 0,
+            "self_test_enforced": 0,
         },
         "carried": {
             "preserve": [],
@@ -457,6 +458,7 @@ def test_success_creates_candidate_with_exact_parent_and_paths(tmp_path: Path) -
             "command_bounded": 0,
             "command_timed_out": 0,
             "self_test_redirected": 0,
+            "self_test_enforced": 0,
         },
         "carried": {
             "preserve": [],
@@ -747,6 +749,7 @@ def test_failed_attempt_is_discarded_without_candidate(
             "command_bounded": 0,
             "command_timed_out": 0,
             "self_test_redirected": 0,
+            "self_test_enforced": 0,
         },
         "carried": {
             "preserve": [],
@@ -807,6 +810,7 @@ def test_timeout_kills_same_process_group_descendant(tmp_path: Path) -> None:
             "command_bounded": 0,
             "command_timed_out": 0,
             "self_test_redirected": 0,
+            "self_test_enforced": 0,
         },
         "carried": {
             "preserve": [],
diff --git a/tests/test_runner.mjs b/tests/test_runner.mjs
index 6b8b332..db0a47d 100644
--- a/tests/test_runner.mjs
+++ b/tests/test_runner.mjs
@@ -8,6 +8,8 @@ import runnerExtension, {
 	createRunner,
 	parseTestResponse,
 	REDIRECTED_COMMAND,
+	enforcedMessage,
+	isFinalTurn,
 	isTestRunCommand,
 	redirectSentence,
 	registerRunner,
@@ -290,6 +292,110 @@ test("a redirected run the engine refuses is an error result; any other bash cal
 	assert.deepEqual(pi.entries.map((entry) => entry.kind), ["self_test_redirected"]);
 });

+const FINAL = { role: "assistant", stopReason: "stop", content: [{ type: "text", text: "Done." }] };
+const CALLING = { role: "assistant", stopReason: "toolUse", content: [{ type: "toolCall", id: "t", name: "read", arguments: {} }] };
+
+test("a final turn is an assistant message with no tool call that did not error or abort", () => {
+	assert.equal(isFinalTurn(FINAL), true);
+	assert.equal(isFinalTurn({ ...FINAL, stopReason: "length" }), true);
+	assert.equal(isFinalTurn(CALLING), false);
+	assert.equal(isFinalTurn({ ...FINAL, stopReason: "error" }), false);
+	assert.equal(isFinalTurn({ ...FINAL, stopReason: "aborted" }), false);
+	assert.equal(isFinalTurn({ role: "user", content: [] }), false);
+	assert.equal(isFinalTurn(undefined), false);
+});
+
+function gated(responses) {
+	const pi = fakePi();
+	let exchanges = 0;
+	registerRunner(pi.api, context(), async () => responses[Math.min(exchanges++, responses.length - 1)]);
+	return {
+		pi,
+		exchanges: () => exchanges,
+		turnEnd: (message) => pi.handlers.turn_end[0]({ type: "turn_end", turnIndex: 0, message, toolResults: [] }),
+		result: (event) => pi.handlers.tool_result[0](event),
+		call: (event) => pi.handlers.tool_call[0](event),
+	};
+}
+
+const LANDED_EDIT = { toolCallId: "e1", toolName: "edit", input: {}, isError: false, content: [],
+	details: { satyrn: true, ok: true, code: "OK", result: { path: "app.py", sha256: "1".repeat(64), region: "" } } };
+
+test("a session that ends without a self-test gets one enforced run, and a failure goes back as one follow-up", async () => {
+	const gate = gated([success({ exit_code: 1, output: "FAILED tests/test_app.py::test_home - assert 404 == 200" })]);
+	assert.equal(await gate.turnEnd(CALLING), undefined);
+	assert.equal(gate.exchanges(), 0);
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 1);
+	assert.deepEqual(gate.pi.entries, [
+		{ kind: "self_test_enforced", data: { generation: 0, code: "OK", exit_code: 1, follow_up: true } },
+	]);
+	assert.deepEqual(gate.pi.sent, [{
+		message: {
+			customType: "self_test_enforced",
+			content: enforcedMessage("Test command exited 1\nFAILED tests/test_app.py::test_home - assert 404 == 200"),
+			display: true,
+			details: undefined,
+		},
+		options: { deliverAs: "followUp" },
+	}]);
+	assert.equal(enforcedMessage("R"),
+		"Before you finish: the Engine ran self_test because nothing had run it since the last change, and it did not pass.\nR");
+	// Once per generation: ending again with no new change runs nothing.
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 1);
+	assert.equal(gate.pi.sent.length, 1);
+});
+
+test("a self-test the model ran after its last change satisfies the gate; a landed edit re-arms it and a pass sends nothing", async () => {
+	const gate = gated([success({ exit_code: 0, output: "3 passed" })]);
+	await gate.pi.tool.execute("s1", {});
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 1);
+	assert.deepEqual(gate.pi.entries, []);
+	await gate.result(LANDED_EDIT);
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 2);
+	assert.deepEqual(gate.pi.entries, [
+		{ kind: "self_test_enforced", data: { generation: 1, code: "OK", exit_code: 0, follow_up: false } },
+	]);
+	assert.deepEqual(gate.pi.sent, []);
+});
+
+test("a redirected bash test run satisfies the gate; a successful write re-arms it; a refused write does not", async () => {
+	const gate = gated([success({ exit_code: 0, output: "3 passed" })]);
+	await gate.call({ toolCallId: "b1", toolName: "bash", input: { command: "uv run pytest -q" } });
+	await gate.result({ toolCallId: "b1", toolName: "bash", input: { command: REDIRECTED_COMMAND }, isError: false, content: [], details: undefined });
+	await gate.result({ toolCallId: "w0", toolName: "write", input: { path: "app.py", content: "x" }, isError: true, content: [], details: undefined });
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 1);
+	await gate.result({ toolCallId: "w1", toolName: "write", input: { path: "app.py", content: "x" }, isError: false, content: [], details: undefined });
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 2);
+	assert.deepEqual(gate.pi.entries.map((entry) => entry.kind), ["self_test_redirected", "self_test_enforced"]);
+});
+
+test("an enforced run the engine refuses is recorded and sends nothing; an errored or aborted turn is never gated", async () => {
+	const gate = gated([{ version: 1, ok: false, code: "TEST_COMMAND_UNAVAILABLE", message: "gone", result: null }]);
+	await gate.turnEnd({ ...FINAL, stopReason: "error" });
+	await gate.turnEnd({ ...FINAL, stopReason: "aborted" });
+	assert.equal(gate.exchanges(), 0);
+	await gate.turnEnd(FINAL);
+	assert.deepEqual(gate.pi.entries, [
+		{ kind: "self_test_enforced", data: { generation: 0, code: "TEST_COMMAND_UNAVAILABLE", exit_code: null, follow_up: false } },
+	]);
+	assert.deepEqual(gate.pi.sent, []);
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.exchanges(), 1);
+});
+
+test("a timed-out enforced run is a failure and goes back to the model", async () => {
+	const gate = gated([success({ exit_code: -1, output: "still running", timed_out: true })]);
+	await gate.turnEnd(FINAL);
+	assert.equal(gate.pi.entries[0].data.follow_up, true);
+	assert.match(gate.pi.sent[0].message.content, /timed out/);
+});
+
 test("default extension leaves the tool set alone without explicit context", () => {
 	const pi = fakePi();
 	runnerExtension(pi.api, {});
@@ -406,8 +512,12 @@ function fakePi() {
 	let tool;
 	const handlers = {};
 	const entries = [];
+	const sent = [];
 	return {
 		api: {
+			sendMessage(message, options) {
+				sent.push({ message, options });
+			},
 			registerTool(candidate) {
 				tool = candidate;
 			},
@@ -420,6 +530,7 @@ function fakePi() {
 		},
 		handlers,
 		entries,
+		sent,
 		get tool() {
 			return tool;
 		},
diff --git a/tools/replay_events.mjs b/tools/replay_events.mjs
index 8fab717..df6062d 100644
--- a/tools/replay_events.mjs
+++ b/tools/replay_events.mjs
@@ -4,7 +4,9 @@
 // fake engine exchange -- so no `uv run satyrn-engine protocol` is ever
 // spawned under `just gates` (M5). See tests/*-brief.md's fixture shape for
 // the event and expectation vocabulary this understands: `tool_call`,
-// `tool_result`, `tool_exec`, and `expectedEntries`.
+// `tool_result`, `tool_exec`, `turn_end` (Phase 3b: `expect.followUp` is
+// false, or a string the one queued follow-up message contains), and
+// `expectedEntries`.

 import { readFile, readdir } from "node:fs/promises";
 import assert from "node:assert/strict";
@@ -38,8 +40,12 @@ function fakePi() {
 	const handlers = {};
 	const tools = {};
 	const entries = [];
+	const sent = [];
 	return {
 		pi: {
+			sendMessage(message, options) {
+				sent.push({ message, options });
+			},
 			on(event, handler) {
 				(handlers[event] ??= []).push(handler);
 			},
@@ -53,6 +59,7 @@ function fakePi() {
 		handlers,
 		tools,
 		entries,
+		sent,
 	};
 }

@@ -195,6 +202,23 @@ async function replayToolExec(tools, event) {
 	return problems;
 }

+async function replayTurnEnd(handlers, sent, event) {
+	const before = sent.length;
+	for (const handler of handlers ?? []) await handler({ type: "turn_end", turnIndex: 0, message: event.message, toolResults: [] });
+	const queued = sent.slice(before);
+	const expect = event.expect ?? {};
+	const problems = [];
+	if (expect.followUp === false && queued.length > 0) {
+		problems.push(`expect.followUp false but ${queued.length} message(s) were queued`);
+	}
+	if (typeof expect.followUp === "string") {
+		if (queued.length !== 1 || queued[0].options?.deliverAs !== "followUp" || !String(queued[0].message?.content).includes(expect.followUp)) {
+			problems.push(`expect.followUp ${JSON.stringify(expect.followUp)} not one follow-up in ${JSON.stringify(queued)}`);
+		}
+	}
+	return problems;
+}
+
 function checkExpectedHandlers(fixture, handlers) {
 	const problems = [];
 	for (const [event, count] of Object.entries(fixture.expectedHandlers ?? {})) {
@@ -227,7 +251,7 @@ function checkExpectedEntries(fixture, entries) {
 export async function replayFixture(fixture) {
 	const extensionUrl = pathToFileURL(resolve(engineDirectory, fixture.extension));
 	const { default: registerExtension } = await import(extensionUrl);
-	const { pi, handlers, tools, entries } = fakePi();
+	const { pi, handlers, tools, entries, sent } = fakePi();
 	const environment =
 		fixture.context === null
 			? {}
@@ -247,6 +271,9 @@ export async function replayFixture(fixture) {
 			case "tool_exec":
 				problems.push(...(await replayToolExec(tools, event)));
 				break;
+			case "turn_end":
+				problems.push(...(await replayTurnEnd(handlers.turn_end, sent, event)));
+				break;
 			default:
 				problems.push(`unknown event type ${event.type}`);
 		}
```

```bash
sed -i '' 's/"self_test_redirected":0}/"self_test_redirected":0,"self_test_enforced":0}/' tests/fixtures/delivery/*.json
grep -c self_test_enforced tests/fixtures/delivery/*.json   # 1 in each of the five
```

- [ ] **Step 2: Run them and watch them fail for the missing implementation only.**

```bash
node --test --experimental-strip-types tests/test_runner.mjs 2>&1 | grep -E "SyntaxError|ℹ fail"
# SyntaxError: … does not provide an export named 'enforcedMessage'
node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"
# replay_events: self-test-enforced: expectedHandlers.turn_end 1 != 0; expect.followUp "Test command exited 1\nFAILED …" not one follow-up in []; expectedEntries.length 1 != 0   EXIT: 1
uv run pytest -q tests/test_budget.py tests/test_delivery.py 2>&1 | tail -1
# 7 failed, 83 passed
```

- [ ] **Step 3: Implement.** Save as `$SCR/t2-impl.diff`, `git apply "$SCR/t2-impl.diff"`:

```diff
diff --git a/docs/usage.md b/docs/usage.md
index 7544cd1..6bc416a 100644
--- a/docs/usage.md
+++ b/docs/usage.md
@@ -267,7 +267,11 @@ One fresh Pi runs in a worktree branched from `HEAD` with the guards loaded
 child): the loop breaker; `edit`/`write` refused outside `writable_paths`; an
 `edit` or `write` that would remove a symbol the base defines refused with
 what to do instead; bash `timeout` set to 120 s when absent and clamped at
-300 s, the result naming the bound and the self-test. `preserve`, `checks`,
+300 s, the result naming the bound and the self-test; a bash command that
+only runs pytest answered by `self_test` instead (`self_test_redirected`);
+and, when the model stops with no self-test since its last `edit` or
+`write`, one run by the Engine whose failure goes back to the model as a
+single follow-up message (`self_test_enforced`). `preserve`, `checks`,
 tracked `conftest.py` files and tracked pytest configuration
 (`pyproject.toml`, `pytest.ini`, `setup.cfg`, `tox.ini`) are restored from the
 base into the worktree before every `self_test` run and before validation, so
diff --git a/packages/engine/runner.ts b/packages/engine/runner.ts
index e7625ae..9db5517 100644
--- a/packages/engine/runner.ts
+++ b/packages/engine/runner.ts
@@ -397,9 +397,39 @@ export function redirectSentence(testCommand: readonly string[]): string {
 	return `The Engine ran self_test in place of this command: it runs "${testCommand.join(" ")}" over the whole suite, whatever paths or flags the command named.`;
 }

+/**
+ * The completion gate (Phase 3b). When the model's turn ends with no tool
+ * call -- Pi is about to stop -- and no self-test has completed through the
+ * Engine since the last landed `edit` or `write` (or none ever ran), the
+ * Engine runs `self_test` itself, once per mutation generation. A failing or
+ * timed-out run goes back to the model as one follow-up message; a pass, or
+ * a run the engine refuses, ends the session as it would have.
+ */
+export function enforcedMessage(resultText: string): string {
+	return `Before you finish: the Engine ran self_test because nothing had run it since the last change, and it did not pass.\n${resultText}`;
+}
+
+/** An assistant message that ends the agent loop: no tool call, and not an error or an abort. */
+export function isFinalTurn(message: unknown): boolean {
+	if (!isRecord(message) || message.role !== "assistant") return false;
+	if (message.stopReason === "error" || message.stopReason === "aborted") return false;
+	const content = Array.isArray(message.content) ? message.content : [];
+	return !content.some((part) => isRecord(part) && part.type === "toolCall");
+}
+
 export function registerRunner(pi: ExtensionAPI, context: MutationContext, exchangeRequest: ExchangeRequest): void {
 	const runner = createRunner(context, exchangeRequest);
 	const redirected = new Set<string>();
+	// A generation counts landed mutations; `checked` is the generation the
+	// last completed self-test ran against (null: none has).
+	let generation = 0;
+	let checked: number | null = null;
+	const run = async (toolCallId: string): Promise<RunnerToolResult> => {
+		const at = generation;
+		const result = await runner.execute(toolCallId, {});
+		if (result.details.ok) checked = at;
+		return result;
+	};
 	const note = async (kind: string, data: Record<string, unknown>): Promise<void> => {
 		try {
 			await pi.appendEntry(kind, data);
@@ -422,7 +452,7 @@ export function registerRunner(pi: ExtensionAPI, context: MutationContext, excha
 			"paths, checks, and tracked test infrastructure -- are restored first, so edits to them never count. " +
 			"Any argument supplied is ignored; the contract's own command always runs.",
 		parameters: TestParameters,
-		execute: runner.execute,
+		execute: (toolCallId: string) => run(toolCallId),
 	});
 	pi.on("tool_call", async (event) => {
 		// Pi: `event.input` is mutable and later handlers and the tool see the
@@ -435,8 +465,16 @@ export function registerRunner(pi: ExtensionAPI, context: MutationContext, excha
 		return undefined;
 	});
 	pi.on("tool_result", async (event) => {
+		if (event.toolName === "edit" && isRecord(event.details) && event.details.satyrn === true && event.details.ok === true) {
+			generation += 1;
+			return undefined;
+		}
+		if (event.toolName === "write" && event.isError !== true) {
+			generation += 1;
+			return undefined;
+		}
 		if (event.toolName === "bash" && redirected.delete(event.toolCallId)) {
-			const result = await runner.execute(event.toolCallId, {});
+			const result = await run(event.toolCallId);
 			return {
 				content: [{ type: "text", text: `${redirectSentence(context.test_command)}\n${result.content[0].text}` }],
 				isError: result.details.ok !== true,
@@ -447,6 +485,35 @@ export function registerRunner(pi: ExtensionAPI, context: MutationContext, excha
 		}
 		return event.details.ok === true ? undefined : { isError: true };
 	});
+	pi.on("turn_end", async (event) => {
+		// Pi awaits turn_end listeners before it polls its steering and
+		// follow-up queues (pi-agent-core agent-loop.js runLoop), so a
+		// follow-up queued here continues the same run: one agent_end. A
+		// custom message, not `sendUserMessage`: that path emits
+		// `queue_update` events into the --mode json stream
+		// (agent-session.js _queueFollowUp), and the custom type names the
+		// Engine as the message's author; Pi hands it to the model as a
+		// user message (core/messages.js convertToLlm).
+		if (!isFinalTurn(event.message) || checked === generation) return;
+		const at = generation;
+		const result = await runner.execute("self_test_enforced", {});
+		checked = at;
+		const details = result.details;
+		const passed = details.ok && details.result.exit_code === 0 && !details.result.timed_out;
+		const followUp = details.ok && !passed;
+		await note("self_test_enforced", {
+			generation: at,
+			code: details.code,
+			exit_code: details.ok ? details.result.exit_code : null,
+			follow_up: followUp,
+		});
+		if (followUp) {
+			pi.sendMessage(
+				{ customType: "self_test_enforced", content: enforcedMessage(result.content[0].text), display: true, details: undefined },
+				{ deliverAs: "followUp" },
+			);
+		}
+	});
 }

 export default function runnerExtension(
diff --git a/src/satyrn_engine/budget.py b/src/satyrn_engine/budget.py
index fc77aef..296f30f 100644
--- a/src/satyrn_engine/budget.py
+++ b/src/satyrn_engine/budget.py
@@ -20,6 +20,7 @@ GUARD_KINDS: tuple[str, ...] = (
     "command_bounded",
     "command_timed_out",
     "self_test_redirected",
+    "self_test_enforced",
 )


diff --git a/src/satyrn_engine/delivery.py b/src/satyrn_engine/delivery.py
index 87d74c0..d126017 100644
--- a/src/satyrn_engine/delivery.py
+++ b/src/satyrn_engine/delivery.py
@@ -262,6 +262,7 @@ class GuardFirings:
     command_bounded: int = 0
     command_timed_out: int = 0
     self_test_redirected: int = 0
+    self_test_enforced: int = 0

     @classmethod
     def from_counter(cls, counter: TurnCounter) -> GuardFirings:
```

- [ ] **Step 4: Run the tests and the gates.**

```bash
node --test --experimental-strip-types tests/test_runner.mjs 2>&1 | grep -E "ℹ (pass|fail)"   # pass 29, fail 0
node --experimental-strip-types tools/replay_events.mjs | grep self-test   # four lines, enforced and not-enforced with "entries":1
uv run python tools/provenance.py new tests/fixtures/events/self-test-enforced.json tests/fixtures/events/self-test-not-enforced.json
uv run ruff check --fix
just gates; echo "EXIT: $?"   # EXIT: 0; pytest 494 passed; node ℹ pass 152
TMPDIR="$SCR/bt" uv run pytest -m integration -q --basetemp "$SCR/bt/t2"; echo "EXIT: $?"
# expected 118 passed, 1 skipped. In the planning scratch clones this was 117 passed, 1 skipped, 1 failed:
# test_pi_installs_and_dispatches_package_extension_in_temporary_settings fails there at 56f4ac0 too
# (Pi records the package by a relative path that resolves differently at the clone's depth); report it if $ENGINE shows it
```

- [ ] **Step 5: The extensions load in real Pi 0.85.1, without a model.** Extensions load before the model is resolved (see the facts above), and a model name Pi cannot resolve ends the run before any request:

```bash
mkdir -p "$SCR/pi-load/repo" "$SCR/bt" && cd "$SCR/pi-load/repo"
CTX=$(python3 -c "import json,os; r=os.getcwd(); print(json.dumps({'version':1,'repo':r,'contract':r+'/c.yaml','revisions':{},'writable_paths':['*'],'test_command':['uv','run','python','-m','pytest','-q'],'symbols':{},'carried':[],'base_commit':'b'*40}))")
E="$ENGINE/packages/engine"
TMPDIR="$SCR/bt" SATYRN_MUTATION_CONTEXT="$CTX" SATYRN_ENGINE_REPO="$ENGINE" pi --print --mode json --no-session --model nope/nope --no-extensions \
  --extension "$E/engine.ts" --extension "$E/mutator.ts" --extension "$E/scope.ts" --extension "$E/bounds.ts" --extension "$E/runner.ts" \
  --no-skills --no-prompt-templates --no-themes --no-context-files --tools read,bash,edit,write,self_test "hi"; echo "EXIT: $?"
# Error: Model "nope/nope" not found. Use --list-models to see available models.   EXIT: 1
# and no "Failed to load extension" line
cd "$ENGINE"
```

- [ ] **Step 6: Commit** (engine tree).

```bash
git add packages/engine/runner.ts src/satyrn_engine/budget.py src/satyrn_engine/delivery.py docs/usage.md tools/replay_events.mjs tests/test_runner.mjs tests/test_budget.py tests/test_delivery.py tests/test_integration_delivery.py tests/fixtures/delivery tests/fixtures/events/self-test-enforced.json tests/fixtures/events/self-test-not-enforced.json PROVENANCE.md
git commit -m "Phase 3b: when the model stops untested, the Engine runs self_test and returns a failure once (self_test_enforced)"
```

---

### Task 3: Evals counts both firings and reads `self_test` use per cell (evals)

Starts only when the operator's before sitting has ended and its results are committed (Global Constraints).

**Files:**
- Modify: `src/satyrn_evals/pathology.py` (`GUARD_KINDS`), `src/satyrn_evals/cell_evidence.py` (docstring rules; `runs_pytest`; `_passing_route`; three `CellEvidence` fields in `to_block` order after `guard_firings`)
- Test: `tests/test_pathology.py`, `tests/test_cell_evidence.py`

**Interfaces:**
- Consumes: Task 1's `redirectSentence` opening (`The Engine ran self_test in place of this command`) and runner.ts `successResult`'s first line (`Test command exited 0`); Task 2's entry data (`exit_code`).
- Produces: `pathology.GUARD_KINDS` holds the seven kinds; `cell_evidence.runs_pytest(command: str) -> bool`; `CellEvidence.self_test_calls: int`, `.bash_test_runs: int` and `.first_passing_self_test: dict[str, object] | None` (`{"turn": int, "output_tokens": int, "route": "tool" | "redirected" | "enforced"}`); `to_block()` keys in order `…, guard_firings, self_test_calls, bash_test_runs, first_passing_self_test, timeline, …`.

- [ ] **Step 1: Write the failing tests.** In `$EVALS`, save as `$SCR/t3-tests.diff`, `git apply "$SCR/t3-tests.diff"`:

```diff
diff --git a/tests/test_cell_evidence.py b/tests/test_cell_evidence.py
index c3bf537..93ea14e 100644
--- a/tests/test_cell_evidence.py
+++ b/tests/test_cell_evidence.py
@@ -17,6 +17,7 @@ from satyrn_evals.cell_evidence import (
     outside,
     outside_paths,
     root_search,
+    runs_pytest,
 )
 from satyrn_evals.overlay import OverlaySpec

@@ -141,7 +142,8 @@ def test_a_timed_out_cell_without_agent_end_still_yields_every_count() -> None:
     assert block == {
         "turns": 1, "output_tokens": 1500, "tool_calls": 3, "root_searches": 1, "bash_outside_paths": 1,
         "file_tool_escapes": 1, "git_commits": 1, "tool_reported_timeouts": 0,
-        "guard_firings": {"command_bounded": 1}, "timeline": False, "commands_over_120s": 0,
+        "guard_firings": {"command_bounded": 1}, "self_test_calls": 0, "bash_test_runs": 0,
+        "first_passing_self_test": None, "timeline": False, "commands_over_120s": 0,
         "unfinished_commands": 0, "longest_command_seconds": None, "overlay_windows": None,
     }

@@ -184,3 +186,107 @@ def test_overlay_windows_are_scanned_for_hidden_tasks_only() -> None:
     assert collect_evidence(_transcript(leak), overlay=spec).overlay_windows == 1
     assert collect_evidence(_transcript(*_bash("b1", "ls")), overlay=spec).overlay_windows == 0
     assert collect_evidence(_transcript(leak)).overlay_windows is None
+
+
+# --- Phase 3b: self-test use -------------------------------------------------
+
+_REDIRECT = (
+    'The Engine ran self_test in place of this command: it runs "uv run python -m pytest -q" '
+    "over the whole suite, whatever paths or flags the command named."
+)
+
+
+@pytest.mark.parametrize(
+    "command",
+    [
+        "uv run python -m pytest -q",
+        'cd "$(pwd)"; uv run pytest tests/test_lint_docs.py -q 2>&1 | tail -25',
+        "cd /w; timeout 115 uv run python -m pytest -q 2>&1 | tail -40",
+        "uv run pytest tests/test_review.py -q 2>&1 | tail -5; uv run ruff check",
+        "PYTHONPATH=src python3 -m pytest -x tests/test_a.py",
+        "uv run --with httpx pytest -k home",
+        ".venv/bin/pytest -q",
+    ],
+)
+def test_a_bash_command_that_runs_pytest_anywhere_counts(command: str) -> None:
+    assert runs_pytest(command)
+
+
+@pytest.mark.parametrize(
+    "command",
+    [
+        'uv run python -c "import app"',
+        "grep -rn pytest tests/",
+        "cat pyproject.toml | grep pytest",
+        "uv run ruff check",
+        "just test",
+        "python3 -m http.server",
+    ],
+)
+def test_a_bash_command_that_never_runs_pytest_does_not_count(command: str) -> None:
+    assert not runs_pytest(command)
+
+
+def _assistant(tokens: int) -> str:
+    return _line({"type": "message_end", "message": {"role": "assistant", "usage": {"output": tokens}}})
+
+
+def _end(call_id: str, tool: str, text: str) -> str:
+    return _line({"type": "tool_execution_end", "toolCallId": call_id, "toolName": tool,
+                  "result": {"content": [{"type": "text", "text": text}]}})
+
+
+def test_self_test_calls_bash_test_runs_and_the_first_passing_self_test_through_the_tool() -> None:
+    text = _transcript(
+        _assistant(100),
+        *_bash("b1", "uv run pytest -q 2>&1 | tail -5"),
+        _line({"type": "tool_execution_start", "toolCallId": "s1", "toolName": "self_test", "args": {}}),
+        _end("s1", "self_test", "Test command exited 1\nFAILED tests/test_a.py::test_b - assert 1 == 2"),
+        _line({"type": "turn_start"}),
+        _assistant(250),
+        _line({"type": "tool_execution_start", "toolCallId": "s2", "toolName": "self_test", "args": {}}),
+        _end("s2", "self_test", "Test command exited 0\n3 passed"),
+        _line({"type": "turn_start"}),
+        _assistant(40),
+    )
+    block = collect_evidence(text).to_block()
+    assert (block["self_test_calls"], block["bash_test_runs"]) == (2, 1)
+    assert block["first_passing_self_test"] == {"turn": 2, "output_tokens": 350, "route": "tool"}
+
+
+def test_a_redirected_bash_run_and_an_enforced_run_are_passing_routes() -> None:
+    redirected = _transcript(
+        _assistant(70),
+        _line({"type": "tool_execution_start", "toolCallId": "b1", "toolName": "bash", "args": {"command": "pytest"}}),
+        _line({"type": "entry_appended", "entry": {"type": "custom", "customType": "self_test_redirected", "data": {"toolCallId": "b1"}}}),
+        _end("b1", "bash", f"{_REDIRECT}\nTest command exited 0\n3 passed"),
+    )
+    block = collect_evidence(redirected).to_block()
+    assert block["first_passing_self_test"] == {"turn": 1, "output_tokens": 70, "route": "redirected"}
+    assert (block["bash_test_runs"], block["self_test_calls"]) == (1, 0)
+    assert block["guard_firings"] == {"self_test_redirected": 1}
+    enforced = _transcript(
+        _assistant(90),
+        _line({"type": "entry_appended", "entry": {"type": "custom", "customType": "self_test_enforced",
+               "data": {"generation": 2, "code": "OK", "exit_code": 0, "follow_up": False}}}),
+    )
+    assert collect_evidence(enforced).to_block()["first_passing_self_test"] == {
+        "turn": 1, "output_tokens": 90, "route": "enforced"
+    }
+
+
+def test_failing_runs_and_look_alike_text_are_not_a_passing_self_test() -> None:
+    text = _transcript(
+        _assistant(10),
+        _line({"type": "tool_execution_start", "toolCallId": "s1", "toolName": "self_test", "args": {}}),
+        _end("s1", "self_test", "Test command exited 1\nTest command exited 0 was expected"),
+        *_bash("b0", "echo x"),
+        _end("b0", "bash", "Test command exited 0"),
+        _end("b1", "bash", f"{_REDIRECT}\nTest command exited 2\nFAILED t"),
+        _line({"type": "entry_appended", "entry": {"type": "custom", "customType": "self_test_enforced",
+               "data": {"generation": 0, "code": "OK", "exit_code": 1, "follow_up": True}}}),
+        _line({"type": "entry_appended", "entry": "not an object"}),
+    )
+    block = collect_evidence(text).to_block()
+    assert block["first_passing_self_test"] is None
+    assert block["self_test_calls"] == 1
diff --git a/tests/test_pathology.py b/tests/test_pathology.py
index 7c7b762..461e9c2 100644
--- a/tests/test_pathology.py
+++ b/tests/test_pathology.py
@@ -1070,12 +1070,37 @@ def test_a_multi_session_concatenation_is_named_not_malformed() -> None:


 def test_every_engine_guard_entry_is_measured() -> None:
-    for kind in ("loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out"):
+    for kind in (
+        "loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out",
+        "self_test_redirected", "self_test_enforced",
+    ):
         block = count_transcript(_LOOP_BROKEN_DOC.replace('"loop_broken"', f'"{kind}"'), had_patch=True)
         assert (block.measured, block.reason) == (True, None), kind
         assert block.loop_broken == (1 if kind == "loop_broken" else 0), kind


+def test_the_engine_follow_up_after_an_enforced_run_is_one_measured_run() -> None:
+    """Phase 3b: a failing enforced self-test queues a custom follow-up message
+    at turn_end; Pi continues the same run (one agent_end, alternating turns)."""
+    turn_end = '{"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}}'
+    doc = _UPDATE_DOC.replace(
+        turn_end,
+        "\n".join([
+            turn_end,
+            '{"type": "entry_appended", "entry": {"type": "custom", "customType": "self_test_enforced", '
+            '"data": {"generation": 1, "code": "OK", "exit_code": 1, "follow_up": true}}}',
+            '{"type": "turn_start"}',
+            '{"type": "message_start", "message": {"role": "custom", "customType": "self_test_enforced", '
+            '"content": "Before you finish", "display": true}}',
+            '{"type": "message_end", "message": {"role": "custom", "customType": "self_test_enforced", '
+            '"content": "Before you finish", "display": true}}',
+            turn_end,
+        ]),
+    )
+    block = count_transcript(doc, had_patch=True)
+    assert (block.measured, block.reason) == (True, None)
+
+
 def test_the_self_test_tool_is_a_known_tool() -> None:
     doc = _UPDATE_DOC.replace('"toolName": "bash"', '"toolName": "self_test"')
     block = count_transcript(doc, had_patch=True)
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
uv run pytest -q tests/test_cell_evidence.py 2>&1 | grep -m1 ImportError   # ImportError while importing test module …/tests/test_cell_evidence.py (runs_pytest)
uv run pytest -q tests/test_pathology.py 2>&1 | tail -1
# 2 failed, 71 passed (test_every_engine_guard_entry_is_measured, test_the_engine_follow_up_after_an_enforced_run_is_one_measured_run)
```

- [ ] **Step 3: Implement.** Save as `$SCR/t3-impl.diff`, `git apply "$SCR/t3-impl.diff"`:

```diff
diff --git a/src/satyrn_evals/cell_evidence.py b/src/satyrn_evals/cell_evidence.py
index 9211755..c4f9536 100644
--- a/src/satyrn_evals/cell_evidence.py
+++ b/src/satyrn_evals/cell_evidence.py
@@ -21,6 +21,17 @@ The escape rules are lexical and stated so a reader can recompute them:
   ``mdfind`` search the disk and always count);
 - relative escapes in bash text (``cd .. && find .``) are not counted; a
   file tool's ``..`` path is.
+- a **bash test run** is a ``bash`` command with any simple command whose
+  program, after leading ``NAME=value`` words, ``env`` and a ``timeout
+  DURATION`` wrapper, and after ``uv run`` and its options, is ``pytest`` or
+  ``py.test``, or ``python``/``python3[.N]`` followed by ``-m pytest``; the
+  Engine's redirect (a narrower rule: nothing else in the command) is read
+  from ``guard_firings``;
+- the **first passing self-test** is the first of: a ``self_test`` result
+  whose text starts ``Test command exited 0``; a ``bash`` result whose text
+  starts with the Engine's redirect sentence and holds that line; a
+  ``self_test_enforced`` entry with ``exit_code`` 0. It records the turns and
+  output tokens counted up to that event, and which route it took;
 - an unquoted newline ends a simple command exactly like ``;``; a newline
   inside a quoted argument stays part of that argument's text.
 - a heredoc body (``<<WORD`` / ``<<-WORD``, ``WORD`` optionally quoted; not
@@ -58,6 +69,14 @@ _DISK_SEARCH_PROGRAMS = frozenset({"locate", "mdfind"})
 _RECURSIVE_FLAGS = {"grep": "rR", "egrep": "rR", "fgrep": "rR", "ls": "R"}
 _FILE_TOOLS = frozenset({"read", "edit", "write"})
 _TIMED_OUT = re.compile(r"Command timed out after \d+(?:\.\d+)? seconds")
+_PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?")
+#: satyrn-engine runner.ts: `successResult`'s first line and `redirectSentence`'s opening.
+_SELF_TEST_PASSED = "Test command exited 0"
+_REDIRECTED = "The Engine ran self_test in place of this command"
+_UV_RUN_VALUE_FLAGS = frozenset(
+    {"--with", "--with-requirements", "--project", "--directory", "--python", "-p", "--group",
+     "--extra", "--package", "--env-file", "--index"}
+)
 _SEPARATORS = frozenset("|&;()")


@@ -72,6 +91,9 @@ class CellEvidence:
     git_commits: int = 0
     tool_reported_timeouts: int = 0
     guard_firings: dict[str, int] = field(default_factory=dict)
+    self_test_calls: int = 0
+    bash_test_runs: int = 0
+    first_passing_self_test: dict[str, object] | None = None
     timeline: bool = False
     commands_over_120s: int = 0
     unfinished_commands: int = 0
@@ -89,6 +111,9 @@ class CellEvidence:
             "git_commits": self.git_commits,
             "tool_reported_timeouts": self.tool_reported_timeouts,
             "guard_firings": dict(sorted(self.guard_firings.items())),
+            "self_test_calls": self.self_test_calls,
+            "bash_test_runs": self.bash_test_runs,
+            "first_passing_self_test": self.first_passing_self_test,
             "timeline": self.timeline,
             "commands_over_120s": self.commands_over_120s,
             "unfinished_commands": self.unfinished_commands,
@@ -284,6 +309,55 @@ def _program(words: Sequence[str]) -> tuple[str, list[str]]:
     return posixpath.basename(words[index]), list(words[index + 1 :])


+def _unwrap(words: Sequence[str]) -> list[str]:
+    rest = list(words)
+    while rest and (rest[0] == "env" or re.match(r"^[A-Za-z_]\w*=", rest[0])):
+        rest = rest[1:]
+    if rest[:1] == ["timeout"]:
+        rest = rest[1:]
+        while rest and rest[0].startswith("-"):
+            rest = rest[1:]
+        rest = rest[1:]
+    return rest
+
+
+def runs_pytest(command: str) -> bool:
+    """Whether any simple command in a bash command runs pytest (module docstring)."""
+    for segment in _segments(command):
+        words = _unwrap(segment)
+        if len(words) >= 2 and posixpath.basename(words[0]) == "uv" and words[1] == "run":
+            words = words[2:]
+            while words and words[0].startswith("-"):
+                words = words[2:] if words[0] in _UV_RUN_VALUE_FLAGS else words[1:]
+            words = _unwrap(words)
+        if not words:
+            continue
+        program = posixpath.basename(words[0])
+        if program in ("pytest", "py.test") or (_PYTHON.fullmatch(program) and words[1:3] == ["-m", "pytest"]):
+            return True
+    return False
+
+
+def _passing_route(event: dict) -> str | None:
+    match event.get("type"):
+        case "tool_execution_end":
+            text = _result_text(event)
+            if event.get("toolName") == "self_test" and text.split("\n", 1)[0] == _SELF_TEST_PASSED:
+                return "tool"
+            if event.get("toolName") == "bash" and text.startswith(_REDIRECTED) and _SELF_TEST_PASSED in text.split("\n")[1:2]:
+                return "redirected"
+        case "entry_appended":
+            entry = event.get("entry")
+            if (
+                isinstance(entry, dict)
+                and entry.get("customType") == "self_test_enforced"
+                and isinstance(entry.get("data"), dict)
+                and entry["data"].get("exit_code") == 0
+            ):
+                return "enforced"
+    return None
+
+
 def root_search(command: str, cwd: str | None) -> bool:
     for segment in _segments(command):
         program, rest = _program(segment)
@@ -339,8 +413,11 @@ def collect_evidence(
         None,
     )
     usage = UsageCounter()
+    first_pass: dict[str, object] | None = None
     for event in events:
         usage.feed_event(event)
+        if first_pass is None and (route := _passing_route(event)) is not None:
+            first_pass = {"turn": usage.turns, "output_tokens": usage.output_tokens, "route": route}
     starts = [e for e in events if e.get("type") == "tool_execution_start" and isinstance(e.get("toolName"), str)]
     commands = [
         e["args"]["command"]
@@ -376,6 +453,9 @@ def collect_evidence(
         git_commits=sum(1 for command in commands if git_commit(command)),
         tool_reported_timeouts=timeouts,
         guard_firings=dict(guard_firings),
+        self_test_calls=sum(1 for e in starts if e["toolName"] == "self_test"),
+        bash_test_runs=sum(1 for command in commands if runs_pytest(command)),
+        first_passing_self_test=first_pass,
         timeline=timeline is not None,
         commands_over_120s=sum(1 for seconds in finished if seconds > LONG_COMMAND_SECONDS),
         unfinished_commands=sum(1 for span in spans if span.ended is None),
diff --git a/src/satyrn_evals/pathology.py b/src/satyrn_evals/pathology.py
index c30a13e..9164279 100644
--- a/src/satyrn_evals/pathology.py
+++ b/src/satyrn_evals/pathology.py
@@ -58,9 +58,15 @@ RUNNER_NAMES = frozenset({"pytest"})
 #: The engine's guard-firing entries (satyrn-engine Phase 1 Task 2,
 #: `budget.GUARD_KINDS`), each a `pi.appendEntry` custom entry the stream
 #: carries as `entry_appended` (Phase 1 Ruling 7). Counted as nothing here;
-#: `cell_evidence` counts them.
+#: `cell_evidence` counts them. `self_test_redirected` and `self_test_enforced`
+#: added in Phase 3b (a bash test run answered by `self_test`; the Engine's own
+#: run when the model stops untested): without them every cell where either
+#: fires would read `unknown_event`.
 GUARD_KINDS = frozenset(
-    {"loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out"}
+    {
+        "loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out",
+        "self_test_redirected", "self_test_enforced",
+    }
 )

 type PathologyReason = Literal[
```

- [ ] **Step 4: Run the tests and the gates.**

```bash
uv run pytest -q tests/test_cell_evidence.py tests/test_pathology.py 2>&1 | tail -1   # 127 passed
uv run ruff check --fix
just gates; echo "EXIT: $?"   # EXIT: 0; 2,131 passed
```

- [ ] **Step 5: Commit** (evals tree).

```bash
git add src/satyrn_evals/pathology.py src/satyrn_evals/cell_evidence.py tests/test_pathology.py tests/test_cell_evidence.py
git commit -m "Phase 3b: evals counts self_test_redirected and self_test_enforced, and reads self_test calls, bash test runs and the first passing self-test per cell"
```

---

### Task 4: The Engine arm pins the enforcement commit (evals)

**Files:**
- Modify: `arms/engine-ornith15-9b.json` (`argv[2]`, `pins.engine_commit`, `pins.digests`), `tests/test_arms.py:342`, `tests/test_launch_record.py:422`

**Interfaces:**
- Consumes: Task 2's engine commit (`git -C $ENGINE rev-parse release-one`).
- Produces: the arm at that commit; only `runner.ts`'s digest differs from `56f4ac0`'s; `ENGINE_SOURCES` unchanged.

- [ ] **Step 1: Re-pin.** From `$EVALS`, with the engine checkout at Task 2's commit:

```bash
NEW=$(git -C "$ENGINE" rev-parse release-one); echo "$NEW"
uv run python - "$ENGINE" "$NEW" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path

engine, commit = sys.argv[1], sys.argv[2]
path = Path("arms/engine-ornith15-9b.json")
arm = json.loads(path.read_text(encoding="utf-8"))
old = arm["pins"]["engine_commit"]
for name in arm["pins"]["digests"]:
    blob = subprocess.run(
        ["git", "-C", engine, "show", f"{commit}:packages/engine/{name}"], capture_output=True, check=True
    ).stdout
    arm["pins"]["digests"][name] = hashlib.sha256(blob).hexdigest()
arm["pins"]["engine_commit"] = commit
arm["argv"][2] = f"/Users/Shared/satyrn-cells/engine-{commit}"
path.write_text(json.dumps(arm, indent=2) + "\n", encoding="utf-8")
for test in ("tests/test_arms.py", "tests/test_launch_record.py"):
    source = Path(test)
    text = source.read_text(encoding="utf-8")
    assert text.count(old) == 1, test
    source.write_text(text.replace(old, commit), encoding="utf-8")
print(old, "->", commit)
PY
git diff --stat   # arms/engine-ornith15-9b.json 3 lines (argv, engine_commit, runner.ts), tests/test_arms.py 1, tests/test_launch_record.py 1
```

- [ ] **Step 2: Gates and the pins row.**

```bash
just gates; echo "EXIT: $?"   # EXIT: 0; 2,131 passed
SATYRN_V4_ENGINE_REPO="$ENGINE" TMPDIR="$SCR/bt" uv run pytest -m integration -q --basetemp "$SCR/bt/t4" tests/integration/test_engine_arm_pins.py; echo "EXIT: $?"   # 4 passed (git reads only; not an isolated row)
```

- [ ] **Step 3: Commit** (evals tree).

```bash
git add arms/engine-ornith15-9b.json tests/test_arms.py tests/test_launch_record.py
git commit -m "Phase 3b: the Engine arm pins engine ${NEW:0:7} (self_test redirected and enforced)

runner.ts's digest changes; the other six pinned sources are unchanged."
```

---

## Operator: the after records and the reading

Not executed by the controller: the export changes the real cells root, and the launches spend inference. Run from `$EVALS` after Task 4, one record at a time, each launch in the background. Exit 4 means the sitting's 60 minutes capped it: run the same `launch` again. Exit 1, 2 or 3 stops; report the result's `reason` and the launcher's stderr verbatim. If a preflight names a stale `(mdworker_shared)` cell process, wait a minute and rerun it.

```bash
# 0. The before sitting is over and committed; no cell is running.
ls /Users/Shared/satyrn-cells | grep satyrn-attempt; echo "none running if nothing above"
BEFORE_ML=$(git log --format= --name-only -- 'records/*.result.json' | grep -m1 'misleading-locus')      # the before results the operator committed
BEFORE_CL=$(git log --format= --name-only -- 'records/*.result.json' | grep -m1 'complaint-lifecycle')
echo "$BEFORE_ML $BEFORE_CL"   # check both are the 56f4ac0 development results before going on

# 1. The cells root holds only the current export: trash the old one deliberately, export the pinned commit.
NEW=$(python3 -c 'import json; print(json.load(open("arms/engine-ornith15-9b.json"))["pins"]["engine_commit"])')
mv /Users/Shared/satyrn-cells/engine-56f4ac0694be0abbf04fa61d4d1f49ddc20abd8a ~/.Trash/
uv run satyrn-evals cell-engine --engine-repo ~/projects/pauleveritt/satyrn-engine --commit "$NEW"
uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell; echo "EXIT: $?"   # EXIT: 0

AUTH="maintainer: Phase 3b self_test enforcement, after, 2026-09-15"
ARM=arms/engine-ornith15-9b.json

# 2. One after record per before record: same task, rung, n and k; previous_result is that before result.
for BEFORE in "$BEFORE_ML" "$BEFORE_CL"; do
  REC="${BEFORE%.result.json}.json"
  read TASK RUNG N K <<<"$(python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["task"], r["rung"] or "contract", r["n"], r["k"])' "$REC")"
  OUT="records/2026-09-15-dev-selftest-after-$TASK.json"
  uv run satyrn-evals record new --output "$OUT" --task "$TASK" --rung "$RUNG" --arm engine --n "$N" --k "$K" --purpose development --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --authority "$AUTH" --previous-result "$BEFORE"
  uv run satyrn-evals launch --preflight "$OUT" --arm $ARM; echo "EXIT: $?"   # EXIT: 0 and "problems": []
  git add "$OUT" && git commit -m "Phase 3b development record: $TASK after (Engine at ${NEW:0:7}, n=$N, k=$K, isolated; $AUTH)"
  uv run satyrn-evals launch "$OUT" --arm $ARM; echo "EXIT: $?"
  git add "${OUT%.json}.result.json" && git commit -m "Phase 3b development result: $TASK after ($(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${OUT%.json}.result.json"))"
done

# 3. The reading table: before and after read by the same evidence code (Task 3), from retained transcripts only; writes nothing.
uv run python - "$(basename "${BEFORE_ML%.result.json}")" "$(basename "${BEFORE_CL%.result.json}")" 2026-09-15-dev-selftest-after-agentclinic-repair-misleading-locus 2026-09-15-dev-selftest-after-agentclinic-complaint-lifecycle <<'PY'
import json
import sys
from pathlib import Path

from satyrn_evals.cell_evidence import collect_evidence

print("night | cell | code | verdict | turns | out_tokens | self_test_calls | bash_test_runs | redirected | enforced | follow_ups | first_pass (turn, tokens, route)")
for stem in sys.argv[1:]:
    arm = Path.home() / "satyrn-runs" / stem / "engine"
    for cell in sorted(p for p in arm.iterdir() if (p / "attempt.json").is_file()):
        attempt = json.loads((cell / "attempt.json").read_text(encoding="utf-8"))
        transcript = cell / "transcript.txt"
        if not transcript.is_file():
            print(f"{stem} | {cell.name} | {attempt['code']} | {attempt['verdict']} | no transcript")
            continue
        text = transcript.read_text(encoding="utf-8")
        ev = collect_evidence(text)
        follow_ups = sum(
            1 for line in text.splitlines()
            if '"customType":"self_test_enforced"' in line and '"follow_up":true' in line
        )
        first = ev.first_passing_self_test
        shown = "-" if first is None else f"{first['turn']}, {first['output_tokens']}, {first['route']}"
        print(
            f"{stem} | {cell.name} | {attempt['code']} | {attempt['verdict']} | {ev.turns} | {ev.output_tokens} | "
            f"{ev.self_test_calls} | {ev.bash_test_runs} | {ev.guard_firings.get('self_test_redirected', 0)} | "
            f"{ev.guard_firings.get('self_test_enforced', 0)} | {follow_ups} | {shown}"
        )
PY
```

### Reading template

Fill one line per question, from the table and the result files. Development records decide no task outcome.

1. **Target: `self_test` use.** Before: the cells with `self_test_calls + redirected + enforced > 0`, out of 4. After: the same count, out of 4. The change moved its target if every after cell that landed a mutation shows use, and the before did not.
2. **Target: ad-hoc test runs replaced.** Before `bash_test_runs` per cell. After `bash_test_runs`, `redirected` and the leftover (`bash_test_runs − redirected`), with the leftover commands quoted from the transcripts. A leftover that is a pure test run is a Ruling 1 defect; a mixed command is Ruling 1 working.
3. **The gate.** After cells with `enforced > 0`: how many sent a follow-up (`follow_ups`), what the model did next (turns after the follow-up, a further `self_test` or edit), and whether any cell ended right after a passing enforced run.
4. **Secondary: cost to first passing self-test.** `first_pass` turn and output tokens, before against after, per task, with the route. No comparison across tasks.
5. **Side effects.** `code` and `verdict` before against after (e.g. more `BUDGET_EXCEEDED` from follow-up turns); the result's `pathology` block. An after cell reading `unknown_event` or `malformed` where its before did not points at Task 3 or Ruling 4.
6. **Decision for the maintainer.** Freeze the engine at Task 2's commit, or take Ruling 5's Design 3 next, citing lines 1–5.

---

## Self-review against the brief

- **Design space:** Design 1 redirect (Ruling 1, Task 1). `python -c` left alone (Ruling 2). Design 2 gate, with how `sendUserMessage`, `agent_end` and `turn_end` behave in `-p --mode json` (Rulings 3 and 4, Pi facts, Task 2). Design 3 deferred with its evidence (Ruling 5). Design 4, wording unchanged (Ruling 6). Recommendation 1 + 2 adopted, with firings recorded by `appendEntry` under the new custom types. They are counted in the receipt's `guard_firings` (Tasks 1 and 2) and in evals `pathology.GUARD_KINDS` and evidence (Task 3).
- **Measurement:** the Engine arm is re-pinned to the new commit (Task 4). The after records are isolated `--purpose development`, mirroring the operator's before for n and k. The before is kept, and no fresh cut is made (Ruling 9). The reading template covers the target (calls > 0, ad-hoc runs replaced) and the secondary (turns and tokens to first passing self-test). The last section lists the operator commands.
- **Rules:** four tasks. Each tree's gates run per task. Provenance rows cover the four new fixtures. One commit per task. No isolated row in any task. No `/tmp` writes. The cells root is changed by the operator only, keeping only the current export. The prompt is identical across before and after.
- **Placeholders:** none. The operator's before result paths are read from git (`BEFORE_ML`, `BEFORE_CL`), not invented. Names agree across tasks: `REDIRECTED_COMMAND`, `isTestRunCommand`, `redirectSentence`, `enforcedMessage`, `isFinalTurn`, `self_test_redirected`, `self_test_enforced`, `runs_pytest`, `self_test_calls`, `bash_test_runs`, `first_passing_self_test`.

## Test verification (plan writing, 2026-09-15)

Every test this plan specifies was run with no inference and no isolated row, in scratch clones under `.../scratchpad/selftest-plan/`, never the main checkouts. The prototype clones were `engine` (branch `rebuild2`, commits `p1` and `p2` on `56f4ac0`) and `evals` (`p3`, `p4` on `91b6da8`). The six diff blocks above were extracted from those commits, with trailing whitespace stripped for the docs lint. They were then extracted back out of this file and applied with `git apply` to fresh clones (`.../repro/`), following each task's steps literally.

- **Before each task, its new tests fail for the missing implementation only.** T1: `SyntaxError … does not provide an export named 'REDIRECTED_COMMAND'`; `replay_events: self-test-not-redirected: expectedHandlers.tool_call 1 != 0`; Python 7 failed, 83 passed (the receipt fixtures, the firing payload and the counter). T2: the same shape for `enforcedMessage`, and `self-test-enforced: expectedHandlers.turn_end 1 != 0; …`; Python 7 failed. T3: `ImportError` collecting `tests/test_cell_evidence.py`; `tests/test_pathology.py` 2 failed, 71 passed.
- **After each task.** T1: `test_runner.mjs` 23 pass; both new replay fixtures pass; engine `just gates` EXIT 0 (pytest 494 passed, node 146 pass, up from 143); `test_integration_delivery.py`, `test_integration_runner_tool.py` and `test_integration_implement.py` 63 passed, 1 skipped. T2: `test_runner.mjs` 29 pass; four `self-test-*` fixtures pass; `just gates` EXIT 0 (node 152 pass); the engine integration tier 117 passed, 1 skipped, 1 failed. The failure is the scratch-depth row named in Task 2 Step 4, which fails identically at `56f4ac0` in the same clone. T3: 127 passed across the two files; evals `just gates` EXIT 0 with 2,131 passed (2,114 at `91b6da8`). T4: the re-pin script against the reproduced engine commit changed exactly `argv[2]`, `engine_commit` and `runner.ts`'s digest, plus one line in each test file; `just gates` EXIT 0 with 2,131 passed; `tests/integration/test_engine_arm_pins.py` 4 passed with `SATYRN_V4_ENGINE_REPO` at that clone.
- **The plan text reproduces the prototypes.** In the fresh engine clone, T1's steps gave a tree identical to `p1` (`git diff --stat` empty). T2's steps gave a tree identical to `p2`. In the fresh evals clone, T3's steps gave a tree identical to `p3`.
- **Real Pi 0.85.1 loads the five extensions at Task 2** (Step 5's command, run against the reproduced engine): only `Model "nope/nope" not found`, exit 1. A deliberately throwing extension and a syntax error each print `Failed to load extension …` before the model error, so the check can fail.
- **The redirect rule against retained evidence.** `isTestRunCommand` at T1 was run over every bash command in `~/satyrn-runs/2026-09-1[45]-*/*/*/transcript.txt`: 835 commands, 159 naming pytest, 103 redirected, 0 redirected among the other 676 (Ruling 1).
- **The reading table** (Operator step 3) was run with T3's code over the three route-proof nights as stand-ins. depth-3 b: `self_test_calls` 0, `bash_test_runs` 2. docs-linter: 0 and 9. run-record-gate: 0 and 0. No first passing self-test in any. This matches the ledger's reading of those cells.
- **The after records' shape:** `record new --task agentclinic-repair-misleading-locus --rung R1` and `--task agentclinic-complaint-lifecycle --rung contract`, each `--arm engine --n 2 --k 3 --purpose development --isolation isolated`, exited 0 into scratch and `launch --check` accepted both. The files were deleted.
- **Not run:** any isolated integration row or `launch --preflight` (live development cells were running; no task needs one), and the operator section's export and launches (inference and the real cells root).

Found by running the draft, and fixed here. The first gate queued its follow-up with `sendUserMessage`; reading `agent-session.js` showed `queue_update` events in the json stream, which `pathology` reads as `unknown_event`, so the gate uses `sendMessage` (Ruling 4). The first `agent_end` design would have written two `agent_end` events, which `pathology` reads as `malformed`, so it moved to `turn_end`. `complaint-lifecycle`'s `launch` contract turned out to be a one-sentence summary over a bare base (Ruling 9). The evidence helper was first named `test_run`, which pytest would collect when imported into a test module; it is `runs_pytest`. A malformed `entry` (not an object) crashed `_passing_route`; a silent row now covers it.
