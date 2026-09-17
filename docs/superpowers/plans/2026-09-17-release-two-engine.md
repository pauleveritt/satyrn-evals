# Release two — the Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-17 against the maintainer's approval of the Engine design the same day. The open design questions are decided below as Rulings, for the maintainer to review before Task 1 starts.** Planned against engine `release-one` at `ea49666` (last code commit `8049d73`) and evals `release-one` at `5310ccb`. **Unlike the Phase 3b plan, the code blocks below were written, not executed** — no scratch clone was built while planning, because the planning session was budgeted for the design reading only. Treat every "Expected" line as a prediction the implementer must confirm, and report any divergence in the task report rather than editing the expectation away.

**Goal:** Build the three Engine components the census diagnosed (finish-on-green, runaway resume, the self_test explanation line), close the four parity defects that make the identical-tools premise false today, add the medium-class size boundary, teach evals to count the two new firings, re-pin the arm, and hand the operator three excluded route-proof records that read the components for behaviour.

**Architecture:** Components A and B live in `packages/engine/runner.ts`, which already owns `self_test`, the mutation generation counter and the completion gate. Component C is a pure change to `compact_output` in `src/satyrn_engine/runner.py` plus one receipt field in `delivery.py`. Parity is three small changes (`mutator.ts` + `mutation.py`/`protocol.py` for multi-edit; `attempt.py` for the prompt; `derive.py` for writable paths) and one evals change (the deliver timeout follows the record). The size boundary is a pure predicate in `derive.py` that is **advisory**: it writes the contract and refuses on stderr, so the developer sees the boundary and the route proof can still run an Engine cell on a large-tier task. Evals learns the two new guard kinds and two evidence counters, and the arm is re-pinned to the frozen engine commit before the export.

**Tech Stack:** TypeScript under Node's `--experimental-strip-types` (`node:test`), Pi 0.85.1's extension API, Python 3.14, uv, pytest, ruff, just, git.

**Spec:** `docs/superpowers/specs/2026-09-17-release-two-engine-design.md` (approved 2026-09-17). Bound by `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`. Evidence: `evidence/2026-09-16-census/README.md` and `classes-summary.md` (signed 2026-09-17), and the frozen census records `records/2026-09-16-census-*.json` and `records/2026-09-17-census2-*.json`. House style: `docs/superpowers/plans/2026-09-15-phase-3b-self-test-enforcement.md`, the last Engine change built, pinned, exported and measured this way.

---

## Rulings

Each names its reason and its cost if wrong. The maintainer reviews these before Task 1.

1. **The steer and resume texts are the spec's, byte for byte, and the steer names no test path.** Component A sends §2's paragraph verbatim; Component B sends §3's. The steer does **not** list the developer's tests by path. Four reasons: the census's harm is the model running *extra* gates and rewriting *its own* tests, and naming paths invites it to go open them; the carried `preserve` set is already in the prompt and `self_test` restores it before every run, so a path list adds no fact the model lacks; a fixed string keeps the go criterion in §7 readable against the approved words; and a path list built from `contract.preserve` would put the developer's real test filenames into a model-visible message — on a self-hosted task that is the 2026-09-15 export-leak shape, where a hidden suite's basename reached a cell. Cost if wrong: a model that does not know which suite "self_test passes" refers to may re-run the whole repository suite anyway; the reading template's question 1 catches that.

2. **A "source mutation" is a landed Engine `edit` or a non-error `write` whose path is not a test path. Bash writes do not count.** A test path is one whose basename matches `test_*.py` or `*_test.py`, or whose basename is `conftest.py`, or which has a `tests` path segment. This is a second counter, `sourceGeneration`, beside the existing `generation`; the completion gate keeps using `generation` unchanged. Reasons: the ten finishing cells all mutate through the Engine's `edit` tool, so the Engine sees them; bash writes have no path the Engine can read without parsing arbitrary shell, and Phase 3b Ruling 3 already settled that bash-made mutations are not counted; and excluding test paths is what makes the steer fire once per real source generation rather than re-arming every time the cell fiddles with its own tests — which is exactly the post-green behaviour 453263 and 470484 show. Cost if wrong: a cell that edits only through bash never gets a steer. The completion gate still covers it.

3. **The steer is suppressed when the enforced gate produced the green.** Component A fires only on a self-test that completed inside a turn — the model's own `self_test` tool call, or a bash call redirected into it — never on `self_test_enforced`. Reason: the enforced gate runs at `turn_end` on a turn that already had no tool call, i.e. the model was already stopping. The behaviour the steer exists to cause has happened; sending it there would reopen a finished session and spend turns to reach the same state. Nothing is recorded in that case. Cost if wrong: a cell whose only green came from the gate is not told it may stop — but it was stopping anyway.

4. **On a length-cut final turn the completion gate fires first, and it suppresses the resume for that turn.** Both live in the one `turn_end` handler, in this order: the gate (unchanged), then the resume. If the gate queued its follow-up, the resume does not send and does not consume one of its two. Reasons: two Engine messages in one turn is noise the model reads as contradiction; the enforced follow-up already says "your tree is red, here is why", which gets a tool call as surely as the resume would; and a length-cut turn *before any mutation* leaves the public suite green, so the gate sends nothing and the resume is the only message — which is the eight cells' exact shape (§3). Cost if wrong: a runaway after a red tree gets the gate's message instead of the resume's; `runaway_resumed` under-counts and the reading template's question 3 must read `self_test_enforced` beside it.

5. **The resume is delivered as `followUp`; the steer as `steer`.** Verified in Pi 0.85.1 `pi-agent-core/dist/agent-loop.js` `runLoop`: a `stopReason: "length"` message is not `error` or `aborted`, so it does not take the early-return at the top of the turn; with no tool call, `hasMoreToolCalls` is false, `turn_end` is emitted, `getSteeringMessages` is polled, the inner loop's condition is re-tested, and only then is `getFollowUpMessages` polled — and a non-empty follow-up queue re-enters the same loop with one `agent_end`. Both paths therefore run after a length-cut tool-free turn. The resume uses `followUp` because that is the queue that reopens a finished loop and is the path Phase 3b already proved with a fixture; the steer uses `steer` because it is queued from a `tool_result` mid-turn, where the steering poll before the next assistant response is the earliest delivery. `agent-session.js` `sendCustomMessage` maps `deliverAs: "steer"` to `agent.steer()` and `"followUp"` to `agent.followUp()`, neither emitting `queue_update` (Phase 3b Ruling 4 stands). Cost if wrong: a steer that arrives a turn late still lands before the model's next action.

6. **The medium-class predicate is two clauses, and the spec's own predicate is not one of them.** A request is above the medium class when its `Files:` block names more than **two** non-test paths, **or** its `Interfaces:` `Produces:` line names more than **ten** symbols. The spec's stated rule — "one module named in `Files:`, one test module" — was checked against the six self-hosted tasks and **refuses `selfhost-run-record-gate`**, a claim task, whose `Files:` block names `src/satyrn_evals/run_record.py` and `src/satyrn_evals/cli.py`. It also admits `selfhost-cell-loop` and `selfhost-speed-probe`, which name one module each. So the file count cannot separate the census's tiers in either direction. What does separate them is the declared interface: `Produces:` names 5 symbols on run-record-gate, 2 on docs-linter, 7 on review-script, 1 on guard-prefixes, 0 on depth-3 (no `Interfaces:` block), against 24 on cell-loop and 16 on speed-probe. The threshold sits in that gap. The file clause is kept at two because a request naming three or more modules is above the tier on its face, and because keeping it means the refusal still reads as the spec's "measure the request against the medium class". **This is a deviation from the approved spec's §6 wording and needs the maintainer's ratification before Task 4 commits.** Cost if wrong: a hand-written request with a terse `Interfaces:` block is admitted above the tier; the refusal is advisory (Ruling 7), so nothing is lost but the warning.

7. **The size refusal is advisory: the contract is written, the refusal goes to stderr and onto the receipt, and the model still runs.** §6 says derive "returns the contract with a refusal that asks the developer to split the request" — the contract is returned. Making it a hard stop would also make §7 impossible: the runaway resume is measured on `selfhost-cell-loop`, which is large-tier, so a hard refusal would leave three route-proof cells unrun. The refusal text is **not** put into the model's prompt: it is the developer's message, and adding it would confound the runaway-resume reading with a prompt change on the one task that measures it. Cost if wrong: a developer who ignores stderr gets a large-tier attempt anyway. The receipt records it.

8. **Multi-edit is one protocol exchange, applied all-or-nothing, capped at sixteen replacements.** `mutator.ts`'s `maxItems: 1` becomes `maxItems: 16, minItems: 1`; the `replace` request carries an `edits` array; `mutation.replace_many` applies them in order and writes once, or writes nothing and refuses naming the failing index. Reasons: a half-applied multi-edit leaves a tree neither the model nor the grader can reason about, and `_atomic_replace` already gives the atomic write; one exchange means one revision bump and one `generation`/`sourceGeneration` increment, so the steer's generation stays meaningful; the cap of sixteen bounds one exchange, and a turn cut at 16,000 tokens can emit an arbitrarily long `edits` array. The single-replacement `old_text`/`new_text` request stays accepted, so nothing that speaks the old protocol breaks. Cost if wrong: a model wanting a seventeenth replacement gets a schema refusal it can split.

9. **The deliver timeout is the record's `command_backstop_s` minus a 60-second margin.** `DELIVER_TIMEOUT_SECONDS = 1800` is replaced by a value the cell computes from the record. The margin makes the Engine's own deliver stop *just before* the harness's per-command backstop, so the Engine writes its receipt and leaves its candidate rather than being killed with no evidence. Sixty seconds is ample for deliver's git operations and receipt write and is 1.25% of the 4,800 s backstop. Cost if wrong: on a pathological git operation the backstop still fires; that is today's behaviour.

10. **The route proof runs in `batch` mode, not attended.** `run_record.gate` refuses a record whose `command_backstop_s + DEADLINE_MARGIN_S` exceeds `max_minutes * 60`. At the census's 4,800 s backstop that is 5,100 s, against an attended ceiling of 3,600 s — attended is arithmetically impossible, whatever the cell count. Batch allows n ≤ 12 and 720 minutes. Three records at `--max-minutes 120` clear 5,100 s with room and stay inside the batch cap. Seven cells at k = 3 is one wave per record, about 80 minutes each in the worst case. Cost if wrong: none; batch is the cadence the census nights already used.

11. **The route-proof cells are marked excluded in four places.** `--purpose route-proof`, which is a deciding purpose distinct from `campaign`, so no comparison denominator can pick them up by purpose; each record's `authority` naming the spec's 2026-09-17 approval and saying in words that the cells are excluded from every comparison denominator; each record's `decision_rule` carrying §7's go criterion marked "behaviour only, no outcome"; and an operator-written row on the census page naming the three record paths. The census page row is written after the records exist, by the operator, not by a build task — the page is signed, and a plan task cannot name a record that has not been frozen. Cost if wrong: a later reader pools them; the purpose field and the authority line both stop that mechanically.

12. **Nothing in this plan writes under `docs/results/` or `docs/reviews/`, touches `/Users/Shared/satyrn-cells`, or runs a model.** The export and the three launches are the operator's, at the end. `PROVENANCE.md` in the evals tree is being edited concurrently by another agent for the authored-task plan; this plan's evals-side new files are fixtures only in the engine tree, and the evals tree gains **no new file**, so no evals `PROVENANCE.md` row is needed and the concurrent agent's edit is not contended.

---

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews the scoped fix diff. No haiku. No Fable.** One fresh implementer per task; one Opus review before the next task starts. A **whole-path review by Opus** runs after Task 8 and before any operator record is written.
- **No inference while building.** No `launch` of a real model, no request to oMLX, from any task. The operator section at the end is the operator's.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **Default test tiers use no model, no network, no subprocess.** Engine `tests/conftest.py` forbids subprocesses in the default pytest tier; node tests use fake `pi` objects and fake exchanges; the evals audit hook in `tests/conftest.py` does the same. Anything that spawns is `@pytest.mark.integration`.
- **Every Engine component is proven by replay or fixture before any live cell, both directions.** Every new detector gets a firing row and a silent row; every refusal test gets a sibling success test.
- **Every task ends with `just gates` exit 0 in the tree it changed.** Read the exit code; never pipe a gate. Engine gates: pytest, ruff, the node tests, `replay_guards`, `replay_events`, `lint-docs`, provenance. Evals gates: pytest, ruff, `lint-docs`, provenance. Run `uv run ruff check --fix` before gates. New files get `PROVENANCE.md` rows in their own tree (`uv run python tools/provenance.py new <paths>`).
- **One commit per task, in that task's tree, on `release-one`, with explicit paths.** Never `--amend`, never merge, never push.
- **Docs caps stand:** evals spec ≤ 400 lines, `ROADMAP.md` ≤ 150; `just lint-docs` exit 0 in both trees.
- **Nothing is written to `/tmp` or `/private/tmp`** except under the session scratchpad `$SCR`. Integration runs pass `--basetemp "$SCR/bt"` and `TMPDIR="$SCR/bt"`.
- **Scratch clones for any experiment**; never the main checkouts.
- **Checkouts and starting points.** `ENGINE=/Users/pauleveritt/projects/pauleveritt/satyrn-engine` at `release-one` `ea49666`; `EVALS=/Users/pauleveritt/projects/pauleveritt/satyrn-evals` at `release-one` `5310ccb`. Another agent is concurrently writing `docs/superpowers/plans/2026-09-18-authored-task-preflight-quiet.md` and `PROVENANCE.md` in `$EVALS`: touch neither.
- **Live cells come first.** Before any isolated integration row, `ls /Users/Shared/satyrn-cells | grep satyrn-attempt` must print nothing. No task in this plan needs an isolated row.
- **The engine commit freezes before the export.** Task 8 pins whatever `git -C "$ENGINE" rev-parse release-one` is after Task 6; no engine commit lands after Task 8.

---

## File structure

```
satyrn-engine (Tasks 1-6)
src/satyrn_engine/runner.py        # T1: compact_output keeps the E lines after the assertion; RunnerResult.compact_bytes   (modify)
src/satyrn_engine/protocol.py      # T1: compact_bytes on the test response; T2: the `edits` array on the replace request   (modify)
src/satyrn_engine/delivery.py      # T1: receipt field validation_output_bytes; T4: receipt field size_refusal             (modify)
src/satyrn_engine/mutation.py      # T2: replace_many, all-or-nothing                                                       (modify)
packages/engine/mutator.ts         # T2: maxItems 16, edits array through the exchange                                      (modify)
src/satyrn_engine/attempt.py       # T3: prompt collapse (PROMPT_LIST_CAP), carried files not called writable              (modify)
src/satyrn_engine/derive.py        # T3: writable paths from the `Files:` block only; T4: files_block/produces_names/size_refusal (modify)
src/satyrn_engine/cli.py           # T4: derive prints the refusal on stderr, exit 0                                        (modify)
packages/engine/runner.ts          # T5: sourceGeneration, finishSteerText, finish-on-green; T6: resumeText, runaway resume (modify)
src/satyrn_engine/budget.py        # T5/T6: GUARD_KINDS + finish_nudged, runaway_resumed                                    (modify)
tools/replay_events.mjs            # T5: `steer` delivery in replayTurnEnd/tool_result; T6: stopReason on turn_end events   (modify)
tests/fixtures/events/finish-on-green-steered.json, finish-on-green-not-steered.json (T5)                                    (new)
tests/fixtures/events/runaway-resumed.json, runaway-not-resumed.json (T6)                                                    (new)
tests/test_runner.py, tests/test_mutation.py, tests/test_protocol.py, tests/test_derive.py, tests/test_attempt.py,
tests/test_delivery.py, tests/test_budget.py, tests/fixtures/delivery/*.json, tests/test_runner.mjs, tests/test_mutator.mjs  (modify)
docs/usage.md                      # one sentence per component                                                             (modify)

satyrn-evals (Tasks 7-8)
src/satyrn_evals/pathology.py      # T7: GUARD_KINDS + finish_nudged, runaway_resumed                                       (modify)
src/satyrn_evals/cell_evidence.py  # T7: finish_nudges, runaway_resumes, stopped_within_turns_of_nudge                       (modify)
src/satyrn_evals/attempt_engine.py # T7: deliver timeout from the record's backstop, minus DELIVER_MARGIN_SECONDS           (modify)
src/satyrn_evals/cell_engine.py    # T7: the backstop reaches deliver_argv                                                  (modify, if the call site needs it)
tests/test_pathology.py, tests/test_cell_evidence.py, tests/test_attempt_engine.py                                           (modify)
arms/engine-ornith15-9b.json, tests/test_arms.py, tests/test_launch_record.py (T8)                                           (modify)
```

---

## Task 1: `compact_output` carries pytest's explanation, and the receipt reports its size (engine)

Component C, §4. Class: information. Cells: the seven depth-3 cells of release one at R1 against six of six at R2, whose only difference is the line `where None = first.timestamp.tzinfo`.

**Files:**
- Modify: `$ENGINE/src/satyrn_engine/runner.py` (`compact_output`, `RunnerResult`, `_run_once`, `run_tests`)
- Modify: `$ENGINE/src/satyrn_engine/protocol.py` (`render_test_response`)
- Modify: `$ENGINE/src/satyrn_engine/delivery.py` (`DeliveryReceipt.validation_output_bytes`)
- Modify: `$ENGINE/tests/test_runner.py`, `$ENGINE/tests/test_protocol.py`, `$ENGINE/tests/test_delivery.py`
- Modify: `$ENGINE/tests/fixtures/delivery/receipt-*.json` (five files, the new key)
- Modify: `$ENGINE/packages/engine/runner.ts` (`TestResult.compact_bytes`), `$ENGINE/tests/test_runner.mjs`, `$ENGINE/tools/replay_events.mjs` (`fakeExchange`'s test result)

**Interfaces:**
- Produces: `runner.EXPLANATION_LINES = 3`; `compact_output(text: str) -> str` (unchanged signature, more output); `RunnerResult(exit_code, output, truncated, timed_out, compact_bytes)`; the protocol test response's `result.compact_bytes: int`; the receipt's `validation_output_bytes: int | None`; the TS `TestResult.compact_bytes: number`.
- Consumes: nothing from a later task.

- [ ] **Step 1: Write the failing tests.** Append to `$ENGINE/tests/test_runner.py`:

```python
FAILING_Q_OUTPUT = """\
F
=================================== FAILURES ===================================
_______________________ test_complaint_model_contract __________________________

    def test_complaint_model_contract():
        first = load_first()
>       assert first.timestamp.tzinfo is not None
E       assert None is not None
E        +  where None = datetime.datetime(2026, 9, 1, 0, 0).tzinfo
E        +    where datetime.datetime(2026, 9, 1, 0, 0) = <Complaint id=1>.timestamp
E        +      where <Complaint id=1> = load_first()

tests/test_models.py:14: AssertionError
=========================== short test summary info ============================
FAILED tests/test_models.py::test_complaint_model_contract - assert None is not None
1 failed in 0.31s
"""


def test_compact_output_keeps_three_explanation_lines_after_the_assertion():
    compact = compact_output(FAILING_Q_OUTPUT)
    assert "FAILED tests/test_models.py::test_complaint_model_contract" in compact
    assert "1 failed in 0.31s" in compact
    assert "where None = datetime.datetime(2026, 9, 1, 0, 0).tzinfo" in compact
    assert "where <Complaint id=1> = load_first()" in compact
    assert compact.count("+  where") + compact.count("+    where") + compact.count("+      where") == 3


def test_compact_output_drops_the_fourth_explanation_line():
    text = FAILING_Q_OUTPUT.replace(
        "tests/test_models.py:14: AssertionError",
        "E        +        where 1 = <Complaint id=1>.id\ntests/test_models.py:14: AssertionError",
    )
    compact = compact_output(text)
    assert "where 1 = <Complaint id=1>.id" not in compact


def test_compact_output_of_a_passing_run_is_unchanged():
    passing = "....\n4 passed in 0.10s\n"
    assert compact_output(passing) == passing


def test_compact_output_keeps_the_assertion_line_itself_once():
    compact = compact_output(FAILING_Q_OUTPUT)
    assert compact.count("assert None is not None") == 1
```

Append to `$ENGINE/tests/test_protocol.py`:

```python
def test_test_response_reports_the_compact_size():
    receipt = RunnerReceipt(
        RunnerCode.OK,
        result=RunnerResult(exit_code=1, output="FAILED a::b\n", truncated=False, timed_out=False,
                            compact_bytes=13),
    )
    payload = json.loads(render_test_response(receipt))
    assert payload["result"]["compact_bytes"] == 13
```

Append to `$ENGINE/tests/test_delivery.py`:

```python
def test_receipt_reports_the_validation_output_size():
    receipt = DeliveryReceipt(outcome=DeliveryOutcome.CANDIDATE_CREATED, code=DeliveryCode.OK,
                              message="candidate created", validation_output="FAILED a::b\n",
                              validation_output_bytes=13)
    assert receipt.payload()["validation_output_bytes"] == 13


def test_receipt_without_validation_reports_no_size():
    receipt = DeliveryReceipt(outcome=DeliveryOutcome.CANDIDATE_CREATED, code=DeliveryCode.OK,
                              message="candidate created")
    assert receipt.payload()["validation_output_bytes"] is None
```

Add `"validation_output_bytes":null` to each of the five `$ENGINE/tests/fixtures/delivery/receipt-*.json` files, immediately after `"validation_output"`.

- [ ] **Step 2: Run them and watch them fail for the missing implementation only.**

```bash
cd "$ENGINE" && uv run pytest -q tests/test_runner.py tests/test_protocol.py tests/test_delivery.py; echo "EXIT: $?"
# Expected: failures naming `compact_bytes` (TypeError: unexpected keyword argument) and the four
# compact_output assertions; no collection errors. EXIT: 1
```

- [ ] **Step 3: Implement.** In `$ENGINE/src/satyrn_engine/runner.py`, add beside `COMPACT_TAIL_LINES`:

```python
#: How many `E ` lines after each traceback block's assertion line are kept
#: (Component C, design §4). The depth-3 cells of release one found the seam
#: at R2 and not at R1, and the only difference was one such line
#: (`where None = first.timestamp.tzinfo`). Three is the design's number: it
#: covers pytest's usual `+  where` / `+    where` chain without carrying a
#: whole traceback into the model's context.
EXPLANATION_LINES = 3
_BLOCK = re.compile(r"^_{3,}.+_{3,}$")
```

Replace `compact_output` with:

```python
def _explanations(lines: list[str]) -> list[str]:
    """Per traceback block, the block header and up to `EXPLANATION_LINES`
    `E ` lines *after* that block's first `E ` line.

    The first `E ` line is pytest's assertion, which the ``FAILED`` summary
    line already carries; what release one's R1/R2 pair showed to matter is
    the lines after it. Blocks are delimited by pytest's ``___ name ___``
    rule. A block with no `E ` line, or only the assertion, contributes
    nothing -- not even its header -- so a passing run is untouched.
    """
    kept: list[str] = []
    header: str | None = None
    seen_assertion = False
    taken = 0
    for line in lines:
        if _BLOCK.match(line.strip()):
            header, seen_assertion, taken = line.strip(), False, 0
            continue
        stripped = line.lstrip()
        if not (stripped == "E" or stripped.startswith("E ")):
            continue
        if not seen_assertion:
            seen_assertion = True
            continue
        if taken >= EXPLANATION_LINES:
            continue
        if header is not None:
            kept.append(header)
            header = None
        kept.append(line.rstrip())
        taken += 1
    return kept


def compact_output(text: str) -> str:
    """Failed and errored test ids with their first assertion line, each
    failure's explanation lines, and the summary line.

    Against real ``pytest -q`` output: keep every line starting with
    ``FAILED `` or ``ERROR ``, the final summary line (fenced or not, with
    or without pytest's ``(H:MM:SS)`` suffix past 60s -- m7), and for each
    traceback block up to `EXPLANATION_LINES` ``E `` lines after that
    block's assertion, under the block's own header (Component C). When
    nothing matches, the last `COMPACT_TAIL_LINES` lines stand in, so a
    passing ``-q`` run keeps its progress dots (m3).
    """
    lines = text.splitlines()
    kept = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
    summary = next((line for line in reversed(lines) if _SUMMARY.match(line)), None)
    if kept:
        return "\n".join([*kept, *_explanations(lines), *([summary] if summary else [])]) + "\n"
    return "\n".join(lines[-COMPACT_TAIL_LINES:]) + ("\n" if lines else "")
```

Add `compact_bytes: int = 0` as the last field of `RunnerResult`, and in `run_tests`'s final return compute it:

```python
    output = "".join(outputs)
    return RunnerReceipt(
        RunnerCode.OK,
        result=RunnerResult(
            exit_code=exit_code,
            output=output,
            truncated=truncated,
            timed_out=timed_out,
            compact_bytes=len(output.encode("utf-8")),
        ),
    )
```

In `$ENGINE/src/satyrn_engine/protocol.py`, `render_test_response` adds `"compact_bytes": receipt.result.compact_bytes` to the result object it renders. In `$ENGINE/src/satyrn_engine/delivery.py`, add `validation_output_bytes: int | None = None` beside `validation_output` on the receipt dataclass, add it to `payload()` right after `"validation_output"`, and set it wherever `validation_output` is set (`_with_validation`, and the two `pending`-copy sites at lines ~748 and ~1305) as `None if validation_output is None else len(validation_output.encode("utf-8"))`.

In `$ENGINE/packages/engine/runner.ts`, add `readonly compact_bytes: number;` to `TestResult`, accept and copy it in `parseTestResponse` (`typeof response.result.compact_bytes !== "number"` joins the shape check), and in `$ENGINE/tools/replay_events.mjs` add `compact_bytes: FAKE_TEST_OUTPUT.length` to `fakeExchange`'s test result.

- [ ] **Step 4: Run the tests, then the gates.**

```bash
cd "$ENGINE" && uv run ruff check --fix && uv run pytest -q tests/test_runner.py tests/test_protocol.py tests/test_delivery.py; echo "EXIT: $?"   # EXIT: 0
just gates; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Commit** (engine tree).

```bash
cd "$ENGINE" && git add src/satyrn_engine/runner.py src/satyrn_engine/protocol.py src/satyrn_engine/delivery.py packages/engine/runner.ts tools/replay_events.mjs tests/test_runner.py tests/test_protocol.py tests/test_delivery.py tests/fixtures/delivery
git commit -m "Release two Component C: the self_test result carries pytest's explanation lines

Design 2026-09-17 section 4. Class: information; cells: release one's seven
depth-3 R1 cells against six of six at R2, whose only difference was one
'where None = first.timestamp.tzinfo' line. The receipt reports the compact
result's size so 'compact' stays a measurement.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Multi-edit — the schema takes many replacements, the Python apply is all-or-nothing (engine)

Parity §5.1. Baseline's `edit` already allows many replacements; the Engine's `maxItems: 1` is one of the four reasons the identical-tools premise is not met today.

**Files:**
- Modify: `$ENGINE/packages/engine/mutator.ts` (the `edits` schema, `EditInput`, `buildReplacementRequest`, `createMutator`)
- Modify: `$ENGINE/src/satyrn_engine/mutation.py` (`replace_many`)
- Modify: `$ENGINE/src/satyrn_engine/protocol.py` (the `replace` request's optional `edits`)
- Modify: `$ENGINE/tests/test_mutation.py`, `$ENGINE/tests/test_protocol.py`, `$ENGINE/tests/test_mutator.mjs`

**Interfaces:**
- Consumes: Task 1's `compact_bytes` only in the sense that `protocol.py` is edited again; no behaviour is shared.
- Produces: `mutation.MAX_REPLACEMENTS = 16`; `mutation.replace_many(root, contract, path, expected_sha256, replacements: Sequence[tuple[str, str]]) -> MutationReceipt`; the protocol `replace` request's optional `edits: [{old_text, new_text}, ...]`; the TS `EditInput.edits: readonly EditReplacement[]`.

- [ ] **Step 1: Write the failing tests.** Append to `$ENGINE/tests/test_mutation.py`:

```python
def test_replace_many_applies_every_replacement_in_order(tmp_path, contract):
    target = tmp_path / "app.py"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    digest = file_sha256(target.read_bytes())
    receipt = replace_many(tmp_path, contract, "app.py", digest,
                           [("alpha", "ALPHA"), ("gamma", "GAMMA")])
    assert receipt.ok
    assert target.read_text(encoding="utf-8") == "ALPHA\nbeta\nGAMMA\n"


def test_replace_many_writes_nothing_when_one_replacement_fails(tmp_path, contract):
    target = tmp_path / "app.py"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    digest = file_sha256(target.read_bytes())
    receipt = replace_many(tmp_path, contract, "app.py", digest,
                           [("alpha", "ALPHA"), ("nowhere", "X")])
    assert not receipt.ok
    assert "replacement 2" in receipt.message
    assert target.read_text(encoding="utf-8") == "alpha\nbeta\n"


def test_replace_many_refuses_more_than_the_cap(tmp_path, contract):
    target = tmp_path / "app.py"
    target.write_text("x\n", encoding="utf-8")
    digest = file_sha256(target.read_bytes())
    pairs = [(f"a{i}", f"b{i}") for i in range(MAX_REPLACEMENTS + 1)]
    receipt = replace_many(tmp_path, contract, "app.py", digest, pairs)
    assert not receipt.ok
    assert str(MAX_REPLACEMENTS) in receipt.message


def test_replace_many_with_one_replacement_matches_replace_once(tmp_path, contract):
    target = tmp_path / "app.py"
    target.write_text("alpha\n", encoding="utf-8")
    digest = file_sha256(target.read_bytes())
    receipt = replace_many(tmp_path, contract, "app.py", digest, [("alpha", "ALPHA")])
    assert receipt.ok
    assert target.read_text(encoding="utf-8") == "ALPHA\n"
```

Append to `$ENGINE/tests/test_protocol.py`:

```python
def test_replace_request_accepts_an_edits_array():
    request = parse_request(json.dumps({
        "version": 1, "operation": "replace", "repo": "/w", "contract": "/w/c.yaml",
        "path": "app.py", "expected_sha256": "a" * 64,
        "edits": [{"old_text": "a", "new_text": "b"}, {"old_text": "c", "new_text": "d"}],
    }))
    assert request.replacements == (("a", "b"), ("c", "d"))


def test_replace_request_still_accepts_one_old_text_new_text_pair():
    request = parse_request(json.dumps({
        "version": 1, "operation": "replace", "repo": "/w", "contract": "/w/c.yaml",
        "path": "app.py", "expected_sha256": "a" * 64, "old_text": "a", "new_text": "b",
    }))
    assert request.replacements == (("a", "b"),)


def test_replace_request_refuses_both_forms_at_once():
    with pytest.raises(ProtocolError, match="edits"):
        parse_request(json.dumps({
            "version": 1, "operation": "replace", "repo": "/w", "contract": "/w/c.yaml",
            "path": "app.py", "expected_sha256": "a" * 64, "old_text": "a", "new_text": "b",
            "edits": [{"old_text": "c", "new_text": "d"}],
        }))
```

Append to `$ENGINE/tests/test_mutator.mjs`:

```javascript
test("the edit schema takes up to sixteen replacements", () => {
	const schema = EditParameters.properties.edits;
	assert.equal(schema.maxItems, 16);
	assert.equal(schema.minItems, 1);
});

test("a two-replacement edit becomes one replace request carrying both", () => {
	const request = JSON.parse(buildReplacementRequest(CONTEXT, {
		path: "app.py",
		edits: [{ oldText: "a", newText: "b" }, { oldText: "c", newText: "d" }],
	}, "a".repeat(64)));
	assert.deepEqual(request.edits, [
		{ old_text: "a", new_text: "b" },
		{ old_text: "c", new_text: "d" },
	]);
	assert.equal(request.old_text, undefined);
});
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd "$ENGINE" && uv run pytest -q tests/test_mutation.py tests/test_protocol.py; echo "EXIT: $?"
# Expected: ImportError / NameError on `replace_many` and `MAX_REPLACEMENTS`, and three
# ProtocolError assertions. EXIT: 1
node --test --experimental-strip-types tests/test_mutator.mjs; echo "EXIT: $?"
# Expected: "does not provide an export named 'EditParameters'" or maxItems 1 != 16. EXIT: 1
```

- [ ] **Step 3: Implement.** In `$ENGINE/src/satyrn_engine/mutation.py`, add beside the other module constants and after `replace_once`:

```python
#: The most replacements one ``replace`` exchange may carry (design §5.1,
#: Ruling 8). Baseline's edit tool already allows many; unbounded is not the
#: parity being restored -- a turn cut at the 16,000-token per-turn cap can
#: emit an arbitrarily long `edits` array, and one exchange should stay one
#: bounded unit of work.
MAX_REPLACEMENTS = 16


def replace_many(
    root: Path,
    contract: Contract,
    path: str,
    expected_sha256: str | None,
    replacements: Sequence[tuple[str, str]],
) -> MutationReceipt:
    """Apply every replacement in order, then write once -- or write nothing.

    All-or-nothing: the replacements are applied to an in-memory copy and
    the file is written only if every one succeeded, so a failure at
    replacement *k* cannot leave a tree that is neither the model's nor the
    base's. The refusal names the 1-based index, because a model that sent
    four replacements needs to know which one it must fix. One exchange, one
    revision, one mutation generation.
    """
    if not replacements:
        return MutationReceipt(MutationCode.MUTATION_FAILED, "no replacements were supplied")
    if len(replacements) > MAX_REPLACEMENTS:
        return MutationReceipt(
            MutationCode.MUTATION_FAILED,
            f"{len(replacements)} replacements exceeds the limit of {MAX_REPLACEMENTS}; send fewer",
        )
    receipt = replace_once(root, contract, path, expected_sha256, *replacements[0])
    if not receipt.ok:
        return MutationReceipt(receipt.code, f"replacement 1: {receipt.message}")
    for index, (old_text, new_text) in enumerate(replacements[1:], start=2):
        follow = replace_once(root, contract, path, receipt.result.sha256, old_text, new_text)
        if not follow.ok:
            _restore(root, path, receipt)
            return MutationReceipt(follow.code, f"replacement {index}: {follow.message}")
        receipt = follow
    return receipt
```

Implementing `_restore` by re-writing the original bytes requires holding them; the simplest correct form reads the file once at entry and, on any failure after the first successful write, writes the original bytes back through the same `_atomic_replace` path. The implementer writes `_restore(root, path, original_bytes)` accordingly and the second test above proves it: `test_replace_many_writes_nothing_when_one_replacement_fails` asserts the file is byte-identical to its original content.

In `$ENGINE/src/satyrn_engine/protocol.py`, `ReplaceRequest` gains `replacements: tuple[tuple[str, str], ...]` in place of `old_text`/`new_text`; `parse_request`'s `case "replace"` accepts either an `edits` list of `{old_text, new_text}` objects or the single pair, raises `ProtocolError("a replace request carries either edits or one old_text/new_text pair, not both")` when both are present, and `handle_protocol` calls `replace_many(..., request.replacements)`.

In `$ENGINE/packages/engine/mutator.ts`, export the schema object as `EditParameters` with `edits: { type: "array", minItems: 1, maxItems: 16, items: {...} }`, widen `EditInput.edits` to `readonly EditReplacement[]`, and make `buildReplacementRequest` emit `edits: input.edits.map(({oldText, newText}) => ({old_text: oldText, new_text: newText}))` instead of `old_text`/`new_text`.

- [ ] **Step 4: Run the tests and the gates.**

```bash
cd "$ENGINE" && uv run ruff check --fix && uv run pytest -q; echo "EXIT: $?"   # EXIT: 0
node --test --experimental-strip-types tests/test_mutator.mjs; echo "EXIT: $?"   # EXIT: 0
just gates; echo "EXIT: $?"   # EXIT: 0
TMPDIR="$SCR/bt" uv run pytest -m integration -q --basetemp "$SCR/bt/t2" tests/test_integration_mutator.py tests/test_integration_protocol.py; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Commit** (engine tree).

```bash
cd "$ENGINE" && git add packages/engine/mutator.ts src/satyrn_engine/mutation.py src/satyrn_engine/protocol.py tests/test_mutation.py tests/test_protocol.py tests/test_mutator.mjs
git commit -m "Release two parity: the edit tool takes many replacements, applied all-or-nothing

Design 2026-09-17 section 5.1. Baseline's edit already allows it; maxItems 1
was one of the four reasons the identical-tools premise was not met. Ruling 8:
one exchange, sixteen at most, nothing written unless every replacement lands.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: The prompt collapses, and writable paths come from the `Files:` block only (engine)

Parity §5.2 and §5.3. The Engine prompt was three to four times Baseline's; and derive admits paths the grader rejects because it tokenizes the whole request.

**Files:**
- Modify: `$ENGINE/src/satyrn_engine/attempt.py` (`build_prompt`, `PROMPT_LIST_CAP`)
- Modify: `$ENGINE/src/satyrn_engine/derive.py` (`files_block`, `_writable_paths`)
- Modify: `$ENGINE/tests/test_attempt.py`, `$ENGINE/tests/test_derive.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `attempt.PROMPT_LIST_CAP = 8`; `derive.files_block(request: str) -> str | None` (the `Files:` block's text, or `None` when the request has no such block).

- [ ] **Step 1: Write the failing tests.** Append to `$ENGINE/tests/test_derive.py`:

```python
FILES_REQUEST = """\
Task 8: The run-record gate

Files:
- Create: `src/satyrn_evals/run_record.py`, `tests/`
- Modify: `src/satyrn_evals/cli.py` (add `launch --check RECORD`)

Interfaces:
- Produces: `RunRecord`, `gate(record)`.

Step 3: Implement. First check `src/satyrn_evals/errors.py` and do not change it.
"""


def test_files_block_is_the_block_and_stops_at_the_next_header():
    block = files_block(FILES_REQUEST)
    assert "run_record.py" in block
    assert "cli.py" in block
    assert "errors.py" not in block
    assert "RunRecord" not in block


def test_writable_paths_come_from_the_files_block_only():
    tracked = ("src/satyrn_evals/cli.py", "src/satyrn_evals/errors.py", "tests/test_cli.py")
    paths = _writable_paths(FILES_REQUEST, tracked, preserve=("tests/test_cli.py",), checks=())
    assert "src/satyrn_evals/errors.py" not in paths
    assert "src/satyrn_evals/cli.py" in paths
    assert "src/satyrn_evals/run_record.py" in paths


def test_a_request_without_a_files_block_still_reads_the_whole_request():
    tracked = ("app.py", "models.py", "tests/test_app.py")
    paths = _writable_paths("Repair the seeded bug in app.py and models.py.", tracked,
                            preserve=("tests/test_app.py",), checks=())
    assert "app.py" in paths
    assert "models.py" in paths
```

Append to `$ENGINE/tests/test_attempt.py`:

```python
def test_a_long_carried_list_collapses_to_patterns():
    contract = Contract(id="c", task="t", writable_paths=("src/*",),
                        preserve=tuple(f"tests/test_{i}.py" for i in range(30)),
                        test_command=("pytest",))
    prompt = build_prompt(contract, existing=(), tracked=())
    assert "tests/test_0.py" not in prompt
    assert "30 files" in prompt
    assert "restored before every self-test" in prompt


def test_a_short_carried_list_is_still_listed():
    contract = Contract(id="c", task="t", writable_paths=("src/*",),
                        preserve=("tests/test_a.py", "tests/test_b.py"), test_command=("pytest",))
    prompt = build_prompt(contract, existing=(), tracked=())
    assert "tests/test_a.py" in prompt


def test_a_writable_pattern_with_many_matches_reports_a_count():
    existing = tuple(f"src/m{i}.py" for i in range(30))
    contract = Contract(id="c", task="t", writable_paths=("src/*",), test_command=("pytest",))
    prompt = build_prompt(contract, existing=existing, tracked=existing)
    assert "src/m0.py" not in prompt
    assert "30 existing files" in prompt


def test_a_writable_pattern_with_few_matches_still_names_them():
    existing = ("src/a.py", "src/b.py")
    contract = Contract(id="c", task="t", writable_paths=("src/*",), test_command=("pytest",))
    prompt = build_prompt(contract, existing=existing, tracked=existing)
    assert "src/a.py" in prompt


def test_carried_files_are_not_described_as_writable():
    contract = Contract(id="c", task="t", writable_paths=("tests/*",),
                        preserve=("tests/test_a.py",), test_command=("pytest",))
    prompt = build_prompt(contract, existing=("tests/test_a.py",), tracked=("tests/test_a.py",))
    writable_section = prompt.split("Tests carried")[0]
    assert "tests/test_a.py" not in writable_section
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd "$ENGINE" && uv run pytest -q tests/test_derive.py tests/test_attempt.py; echo "EXIT: $?"
# Expected: ImportError on `files_block`, and the five prompt assertions failing because
# the current build_prompt enumerates everything. EXIT: 1
```

- [ ] **Step 3: Implement.** In `$ENGINE/src/satyrn_engine/derive.py`, add:

```python
_FILES_HEADER = re.compile(r"^Files:\s*$", re.MULTILINE)
_NEXT_HEADER = re.compile(r"^[A-Z][A-Za-z ]{0,40}:\s*$", re.MULTILINE)


def files_block(request: str) -> str | None:
    """The text of the request's ``Files:`` block, or ``None``.

    The block runs from the line after ``Files:`` to the next header line
    (``Word:`` alone on a line) or to the end. Design §5.3: derive must
    admit only the paths the request's ``Files:`` block names, so it cannot
    admit a path the grader rejects -- release one's run-record-gate cells
    were invited into ``errors.py``, which is outside the task's
    ``source_paths``, purely because the word appeared later in the prompt.
    A request with no ``Files:`` block (an AgentClinic repair, say) reads as
    before: the whole request is tokenized.
    """
    header = _FILES_HEADER.search(request)
    if header is None:
        return None
    rest = request[header.end():]
    following = _NEXT_HEADER.search(rest)
    return rest[: following.start()] if following else rest
```

and make `_writable_paths` read `source = files_block(request) or request` and tokenize `source` instead of `request`. The `_is_test_only` fallback is unchanged: a `Files:` block naming only tests still falls back to the top-level entries.

In `$ENGINE/src/satyrn_engine/attempt.py`, add beside `BASH_BOUND_SECONDS`:

```python
#: How many paths a prompt list names before it collapses to a count
#: (design §5.2). The Engine prompt was 3 to 4 times Baseline's, almost all
#: of it the tracked test files enumerated twice -- once under a writable
#: pattern's "(existing: ...)" and once in the carried block. Eight is
#: enough to name a real task's files and short enough that a self-hosted
#: base's hundreds collapse.
PROMPT_LIST_CAP = 8
```

Replace `writable_line` and the carried `block` call with:

```python
    def writable_line(pattern: str) -> str:
        beneath = sorted(path for path in existing if fnmatch(path, pattern)
                         and path not in contract.preserve and path not in contract.checks)
        if len(beneath) > PROMPT_LIST_CAP:
            return f"- {pattern}  ({len(beneath)} existing files)"
        if beneath:
            return f"- {pattern}  (existing: {', '.join(beneath)})"
        is_exact = not any(char in pattern for char in "*?[")
        if is_exact and pattern not in tracked:
            return f"- {pattern}  (new file)"
        return f"- {pattern}"

    def block(title: str, items: Sequence[str]) -> str:
        if not items:
            return ""
        if len(items) > PROMPT_LIST_CAP:
            return f"{title}\n- {len(items)} files under tests/\n\n"
        return f"{title}\n" + "\n".join(f"- {item}" for item in items) + "\n\n"
```

The `and path not in contract.preserve and path not in contract.checks` clause is §5.2's second half: a carried file is restored before every self-test, so listing it as writable is a false statement the prompt was making.

- [ ] **Step 4: Run the tests and the gates.**

```bash
cd "$ENGINE" && uv run ruff check --fix && uv run pytest -q; echo "EXIT: $?"   # EXIT: 0
just gates; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Measure the collapse, and put the number in the task report.** No inference; this only renders a prompt.

```bash
cd "$ENGINE" && uv run python - <<'PY'
from pathlib import Path
import json
from satyrn_engine.derive import RepoFacts, derive_contract
from satyrn_engine.attempt import build_prompt
manifest = json.loads(Path(
    "/Users/pauleveritt/projects/pauleveritt/satyrn-evals/src/satyrn_evals/tasks/"
    "selfhost-run-record-gate/manifest.json").read_text())
base = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/src/satyrn_evals/tasks/"
            "selfhost-run-record-gate/base")
tracked = tuple(sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()))
facts = RepoFacts(tracked=tracked, pyproject=(base / "pyproject.toml").read_text(), head="0" * 40)
contract = derive_contract(manifest["contract"], facts)
prompt = build_prompt(contract, existing=tracked, tracked=tracked)
print("prompt characters:", len(prompt))
print("writable paths:", len(contract.writable_paths))
print("preserve:", len(contract.preserve))
PY
```

Report the character count before and after (run the same block at `HEAD~1` in a scratch clone for the before). Expected: a large fall, driven by the carried block.

- [ ] **Step 6: Commit** (engine tree).

```bash
cd "$ENGINE" && git add src/satyrn_engine/attempt.py src/satyrn_engine/derive.py tests/test_attempt.py tests/test_derive.py
git commit -m "Release two parity: the prompt collapses its lists, and writable paths come from Files: only

Design 2026-09-17 sections 5.2 and 5.3. The Engine prompt was 3 to 4 times
Baseline's and listed carried files as writable; derive admitted paths the
grader rejects because it tokenized the whole request, which is how release
one's run-record-gate cells were invited into errors.py.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: The medium-class boundary — derive refuses above the tier, advisorily (engine)

Design §6. The large tier is 18 of 18 cells with no pass state; the Engine says so rather than trying. Rulings 6 and 7 govern the predicate and the advisory form. **The maintainer ratifies Ruling 6 before this task commits.**

**Files:**
- Modify: `$ENGINE/src/satyrn_engine/derive.py` (`produces_names`, `size_refusal`, the two caps)
- Modify: `$ENGINE/src/satyrn_engine/cli.py` (the `derive` subcommand prints the refusal on stderr)
- Modify: `$ENGINE/src/satyrn_engine/delivery.py` (`size_refusal` on the receipt)
- Modify: `$ENGINE/tests/test_derive.py`, `$ENGINE/tests/test_check_cli.py`, `$ENGINE/tests/test_delivery.py`, `$ENGINE/tests/fixtures/delivery/receipt-*.json`

**Interfaces:**
- Consumes: Task 3's `files_block`.
- Produces: `derive.MEDIUM_MODULE_CAP = 2`; `derive.MEDIUM_PRODUCES_CAP = 10`; `derive.produces_names(request: str) -> tuple[str, ...]`; `derive.size_refusal(request: str) -> str | None`; the receipt's `size_refusal: str | None`.

- [ ] **Step 1: Write the failing tests.** Add a new test module `$ENGINE/tests/test_derive_size.py`, which is also the place the six self-hosted tasks are pinned:

```python
"""The medium-class boundary (design §6, plan Ruling 6).

The six self-hosted tasks and depth-3 are read from the evals task tree, so
the predicate is measured against the real requests rather than a paraphrase.
If that tree is absent the rows skip with the reason; the pure rows below
still run.
"""

import json
from pathlib import Path

import pytest

from satyrn_engine.derive import (
    MEDIUM_MODULE_CAP,
    MEDIUM_PRODUCES_CAP,
    produces_names,
    size_refusal,
)

TASKS = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/src/satyrn_evals/tasks")
ADMITTED = (
    "selfhost-run-record-gate", "selfhost-docs-linter", "selfhost-guard-prefixes",
    "selfhost-review-script", "agentclinic-repair-depth-3",
)
REFUSED = ("selfhost-cell-loop", "selfhost-speed-probe")


def request_for(name: str) -> str:
    manifest = TASKS / name / "manifest.json"
    if not manifest.is_file():
        pytest.skip(f"the evals task tree is not present: {manifest}")
    return json.loads(manifest.read_text(encoding="utf-8"))["contract"]


@pytest.mark.parametrize("name", ADMITTED)
def test_every_medium_and_floor_task_is_admitted(name):
    assert size_refusal(request_for(name)) is None


@pytest.mark.parametrize("name", REFUSED)
def test_every_large_tier_task_is_refused(name):
    refusal = size_refusal(request_for(name))
    assert refusal is not None
    assert "split" in refusal


@pytest.mark.parametrize("name", ADMITTED + REFUSED)
def test_the_produces_count_is_on_the_expected_side_of_the_cap(name):
    count = len(produces_names(request_for(name)))
    assert (count > MEDIUM_PRODUCES_CAP) == (name in REFUSED), f"{name}: {count}"


def test_three_modules_in_files_are_refused_whatever_the_interfaces_say():
    request = "Files:\n- Create: `a.py`, `b.py`, `c.py`, `tests/`\n\nInterfaces:\n- Produces: `f`.\n"
    assert "3 non-test paths" in (size_refusal(request) or "")


def test_two_modules_in_files_are_admitted():
    request = "Files:\n- Create: `a.py`, `tests/`\n- Modify: `b.py`\n\nInterfaces:\n- Produces: `f`.\n"
    assert size_refusal(request) is None


def test_a_request_with_no_files_block_is_admitted():
    assert size_refusal("Repair the seeded bug in app.py.") is None


def test_produces_names_skips_paths_and_prose():
    request = ("Interfaces:\n- Produces: `RunRecord`, `load_run_record(path: Path) -> RunRecord`, "
               "`src/x/run_record.py`, `errors.py`, `satyrn-evals launch --check R.json`.\n")
    assert produces_names(request) == ("RunRecord", "load_run_record")


def test_produces_names_strips_a_leading_class_or_type_keyword():
    request = "Interfaces:\n- Produces: `class Status(StrEnum)`, `type Spawn = Callable`.\n"
    assert produces_names(request) == ("Status", "Spawn")


def test_the_caps_are_the_plans_numbers():
    assert (MEDIUM_MODULE_CAP, MEDIUM_PRODUCES_CAP) == (2, 10)
```

Append to `$ENGINE/tests/test_delivery.py`:

```python
def test_the_receipt_carries_a_size_refusal_when_one_was_raised():
    receipt = DeliveryReceipt(outcome=DeliveryOutcome.CANDIDATE_CREATED, code=DeliveryCode.OK,
                              message="candidate created", size_refusal="above the medium class")
    assert receipt.payload()["size_refusal"] == "above the medium class"


def test_the_receipt_carries_no_size_refusal_by_default():
    receipt = DeliveryReceipt(outcome=DeliveryOutcome.CANDIDATE_CREATED, code=DeliveryCode.OK,
                              message="candidate created")
    assert receipt.payload()["size_refusal"] is None
```

Add `"size_refusal":null` to each of the five `$ENGINE/tests/fixtures/delivery/receipt-*.json` files.

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd "$ENGINE" && uv run pytest -q tests/test_derive_size.py tests/test_delivery.py; echo "EXIT: $?"
# Expected: ImportError on size_refusal/produces_names/the caps; the two receipt rows failing on
# an unexpected keyword argument. EXIT: 1
```

- [ ] **Step 3: Implement.** In `$ENGINE/src/satyrn_engine/derive.py`:

```python
#: The medium class, measured mechanically (design §6; plan Ruling 6). Two
#: clauses, because the design's stated predicate ("one module named in
#: `Files:`, one test module") was checked against the six self-hosted tasks
#: and refuses `selfhost-run-record-gate`, a claim task whose `Files:` block
#: names two modules, while admitting `selfhost-cell-loop` and
#: `selfhost-speed-probe`, which name one each. The field that does separate
#: the census's tiers is the declared interface: `Produces:` names 5, 2, 7, 1
#: and 0 symbols on the five admitted tasks against 24 and 16 on the two
#: large-tier ones. The file clause is kept because three or more modules is
#: above the tier on its face.
MEDIUM_MODULE_CAP = 2
MEDIUM_PRODUCES_CAP = 10
_PRODUCES = re.compile(r"^-?\s*Produces[^:]*:(.*)$", re.MULTILINE)
_SPAN = re.compile(r"`([^`]+)`")
_KEYWORD = re.compile(r"^(?:class|type|def|@dataclass)\s+")
_DOTTED = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z")


def produces_names(request: str) -> tuple[str, ...]:
    """The symbols the request's ``Interfaces:`` ``Produces:`` lines name.

    Each backticked span has a leading ``class``/``type``/``def``/
    ``@dataclass`` keyword stripped, is cut at the first ``(``, space,
    ``=`` or ``:``, and is kept when what remains is a dotted identifier
    that neither ends in ``.py`` nor holds a ``/`` -- so a module path, a
    shell command or a quoted literal never counts as a produced symbol.
    Order-preserving and deduplicated.
    """
    names: list[str] = []
    for line in _PRODUCES.findall(request):
        for span in _SPAN.findall(line):
            candidate = _KEYWORD.sub("", span.strip())
            for stop in ("(", " ", "=", ":"):
                candidate = candidate.split(stop, 1)[0]
            candidate = candidate.strip()
            if not _DOTTED.match(candidate) or candidate.endswith(".py") or "/" in candidate:
                continue
            if candidate not in names:
                names.append(candidate)
    return tuple(names)


def _files_paths(request: str) -> tuple[str, ...]:
    block = files_block(request)
    if block is None:
        return ()
    found: list[str] = []
    for span in _SPAN.findall(block):
        token = span.strip().strip("`")
        if "/" not in token and "." not in token:
            continue
        if token not in found:
            found.append(token)
    return tuple(found)


def size_refusal(request: str) -> str | None:
    """The developer-facing refusal when a request is above the medium class.

    ``None`` when the request is within it. Advisory (plan Ruling 7): the
    caller still writes the contract and still runs, because §7's runaway
    resume is measured on a large-tier task, and because §6 says the Engine
    "returns the contract with a refusal", not instead of it.
    """
    modules = tuple(p for p in _files_paths(request)
                    if not _is_test_file(p) and not p.rstrip("/").endswith("tests"))
    if len(modules) > MEDIUM_MODULE_CAP:
        return (f"This request names {len(modules)} non-test paths in its Files: block "
                f"({', '.join(modules)}). The Engine is built for one or two modules and their "
                "tests; above that, 18 of 18 measured cells reached no passing state. Split the "
                "request into one bounded change per module and run them in order.")
    produced = produces_names(request)
    if len(produced) > MEDIUM_PRODUCES_CAP:
        return (f"This request's Interfaces: block declares {len(produced)} symbols "
                f"({', '.join(produced[:5])}, ...). The Engine is built for a change of up to "
                f"{MEDIUM_PRODUCES_CAP}; above that, 18 of 18 measured cells reached no passing "
                "state. Split the request into bounded changes and run them in order.")
    return None
```

In `$ENGINE/src/satyrn_engine/cli.py`, the `derive` subcommand calls `size_refusal(request)` after `derive_contract` succeeds, writes the contract as before, and when the refusal is not `None` prints `satyrn-engine: {refusal}` to stderr and exits 0. In `$ENGINE/src/satyrn_engine/delivery.py`, add `size_refusal: str | None = None` to the receipt dataclass and to `payload()`.

- [ ] **Step 4: Run the tests, then the gates.**

```bash
cd "$ENGINE" && uv run ruff check --fix && uv run pytest -q; echo "EXIT: $?"   # EXIT: 0
just gates; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Print the separation table for the task report.**

```bash
cd "$ENGINE" && uv run python - <<'PY'
import json
from pathlib import Path
from satyrn_engine.derive import produces_names, size_refusal
tasks = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/src/satyrn_evals/tasks")
for name in sorted(p.name for p in tasks.iterdir() if (p / "manifest.json").is_file()):
    request = json.loads((tasks / name / "manifest.json").read_text())["contract"]
    print(f"{name:42} produces={len(produces_names(request)):3}  "
          f"{'REFUSED' if size_refusal(request) else 'admitted'}")
PY
```

Expected: `selfhost-cell-loop` and `selfhost-speed-probe` REFUSED; every other task admitted. Any other outcome stops the task and goes back to the maintainer with Ruling 6.

- [ ] **Step 6: Commit** (engine tree).

```bash
cd "$ENGINE" && git add src/satyrn_engine/derive.py src/satyrn_engine/cli.py src/satyrn_engine/delivery.py tests/test_derive_size.py tests/test_check_cli.py tests/test_delivery.py tests/fixtures/delivery
git commit -m "Release two: the Engine says when a request is above the medium class

Design 2026-09-17 section 6, with plan Rulings 6 and 7. The design's stated
predicate refuses a claim task and admits both large-tier ones; the separating
field is the declared Produces: count. Advisory, so the contract is still
written and section 7's runaway-resume cells still run.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Component A — the finish-on-green steer (engine)

Design §2. Class: finishing. Cells: run-record-gate 470484, 533788, 609675, 275888, 891860, 949626, 016509; docs-linter 374751, 453263, 845472 (`evidence/2026-09-16-census/classes-summary.md`).

**Files:**
- Modify: `$ENGINE/packages/engine/runner.ts` (`FINISH_STEER`, `isTestPath`, `sourceGeneration`, `nudged`, the `tool_result` handler)
- Modify: `$ENGINE/src/satyrn_engine/budget.py` (`GUARD_KINDS` + `finish_nudged`), `$ENGINE/src/satyrn_engine/delivery.py` (`GuardFirings.finish_nudged`)
- Modify: `$ENGINE/tools/replay_events.mjs` (`expect.steer`; a `tool_exec` event may queue a message)
- Create: `$ENGINE/tests/fixtures/events/finish-on-green-steered.json`, `$ENGINE/tests/fixtures/events/finish-on-green-not-steered.json`
- Modify: `$ENGINE/tests/test_runner.mjs`, `$ENGINE/tests/test_budget.py`, `$ENGINE/tests/test_delivery.py`, `$ENGINE/tests/fixtures/delivery/receipt-*.json`, `$ENGINE/docs/usage.md`

**Interfaces:**
- Consumes: Task 1's `TestResult.compact_bytes` (the runner's result shape).
- Produces: `runner.ts` exports `FINISH_STEER: string` and `isTestPath(path: string): boolean`; the `finish_nudged` entry `{generation: number}`; `budget.GUARD_KINDS` and `delivery.GuardFirings` gain `finish_nudged`.

- [ ] **Step 1: Write the failing tests.** Append to `$ENGINE/tests/test_runner.mjs`:

```javascript
test("a test path is any test module, conftest, or anything under tests/", () => {
	assert.equal(isTestPath("tests/test_app.py"), true);
	assert.equal(isTestPath("tests/conftest.py"), true);
	assert.equal(isTestPath("src/pkg/app_test.py"), true);
	assert.equal(isTestPath("tests/helpers/data.json"), true);
	assert.equal(isTestPath("src/pkg/app.py"), false);
	assert.equal(isTestPath("contests/app.py"), false);
});

test("the steer text is the design's paragraph and names no path", () => {
	assert.match(FINISH_STEER, /^self_test passes on the current tree\./);
	assert.match(FINISH_STEER, /Do not commit, add provenance rows/);
	assert.equal(FINISH_STEER.includes(".py"), false);
});
```

Create `$ENGINE/tests/fixtures/events/finish-on-green-steered.json`. A source `write` lands, the model runs `self_test`, the fake exchange is made to pass for this fixture (`"exit_code": 0` — the replay tool gains a per-fixture `testExitCode`), and one steer is expected; a second `self_test` in the same source generation steers nothing; after a second source `write` it steers again:

```json
{
  "name": "finish-on-green-steered",
  "extension": "runner.ts",
  "testExitCode": 0,
  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {"app.py": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "writable_paths": ["app.py", "tests/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
  "expectedHandlers": {"tool_call": 1, "tool_result": 1, "turn_end": 1},
  "events": [
    {"type": "tool_result", "toolCallId": "w1", "toolName": "write", "input": {"path": "app.py"}, "isError": false, "content": [{"type": "text", "text": "ok"}], "details": {}, "expect": {"patched": false}},
    {"type": "tool_result", "toolCallId": "s1", "toolName": "self_test", "input": {}, "isError": false, "content": [{"type": "text", "text": "Test command exited 0"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"exit_code": 0, "output": "4 passed in 0.1s\n", "truncated": false, "timed_out": false, "compact_bytes": 18}}, "expect": {"steer": "self_test passes on the current tree."}},
    {"type": "tool_result", "toolCallId": "s2", "toolName": "self_test", "input": {}, "isError": false, "content": [{"type": "text", "text": "Test command exited 0"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"exit_code": 0, "output": "4 passed in 0.1s\n", "truncated": false, "timed_out": false, "compact_bytes": 18}}, "expect": {"steer": false}},
    {"type": "tool_result", "toolCallId": "w2", "toolName": "write", "input": {"path": "app.py"}, "isError": false, "content": [{"type": "text", "text": "ok"}], "details": {}, "expect": {"patched": false}},
    {"type": "tool_result", "toolCallId": "s3", "toolName": "self_test", "input": {}, "isError": false, "content": [{"type": "text", "text": "Test command exited 0"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"exit_code": 0, "output": "4 passed in 0.1s\n", "truncated": false, "timed_out": false, "compact_bytes": 18}}, "expect": {"steer": "self_test passes on the current tree."}}
  ],
  "expectedEntries": [
    {"kind": "finish_nudged", "data": {"generation": 1}},
    {"kind": "finish_nudged", "data": {"generation": 2}}
  ]
}
```

Create `$ENGINE/tests/fixtures/events/finish-on-green-not-steered.json`, the silent direction: a green with no mutation at all; a green whose only mutation was a test file; and a red self_test after a source write:

```json
{
  "name": "finish-on-green-not-steered",
  "extension": "runner.ts",
  "testExitCode": 0,
  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {"app.py": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "writable_paths": ["app.py", "tests/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
  "expectedHandlers": {"tool_call": 1, "tool_result": 1, "turn_end": 1},
  "events": [
    {"type": "tool_result", "toolCallId": "s0", "toolName": "self_test", "input": {}, "isError": false, "content": [{"type": "text", "text": "Test command exited 0"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"exit_code": 0, "output": "4 passed in 0.1s\n", "truncated": false, "timed_out": false, "compact_bytes": 18}}, "expect": {"steer": false}},
    {"type": "tool_result", "toolCallId": "w1", "toolName": "write", "input": {"path": "tests/test_app.py"}, "isError": false, "content": [{"type": "text", "text": "ok"}], "details": {}, "expect": {"patched": false}},
    {"type": "tool_result", "toolCallId": "s1", "toolName": "self_test", "input": {}, "isError": false, "content": [{"type": "text", "text": "Test command exited 0"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"exit_code": 0, "output": "4 passed in 0.1s\n", "truncated": false, "timed_out": false, "compact_bytes": 18}}, "expect": {"steer": false}},
    {"type": "tool_result", "toolCallId": "e1", "toolName": "edit", "input": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}, "isError": false, "content": [{"type": "text", "text": "1 b"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"path": "app.py", "sha256": "1111111111111111111111111111111111111111111111111111111111111111", "region": "1 b"}}, "expect": {"patched": false}},
    {"type": "tool_result", "toolCallId": "s2", "toolName": "self_test", "input": {}, "isError": false, "content": [{"type": "text", "text": "Test command exited 1"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"exit_code": 1, "output": "FAILED a::b\n", "truncated": false, "timed_out": false, "compact_bytes": 13}}, "expect": {"steer": false}}
  ],
  "expectedEntries": []
}
```

Append to `$ENGINE/tests/test_budget.py` a row asserting `"finish_nudged" in GUARD_KINDS`, and to `$ENGINE/tests/test_delivery.py` a row asserting `GuardFirings().payload()["finish_nudged"] == 0`. Add `"finish_nudged":0` to `guard_firings` in each of the five receipt fixtures.

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd "$ENGINE" && node --test --experimental-strip-types tests/test_runner.mjs; echo "EXIT: $?"
# Expected: "does not provide an export named 'FINISH_STEER'". EXIT: 1
node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"
# Expected: replay_events: finish-on-green-steered: expectedEntries.length 2 != 0 (and the
# unknown `expect.steer` key ignored until Step 3 teaches the tool). EXIT: 1
uv run pytest -q tests/test_budget.py tests/test_delivery.py; echo "EXIT: $?"   # EXIT: 1
```

- [ ] **Step 3: Implement.** In `$ENGINE/packages/engine/runner.ts`, add after `enforcedMessage`:

```typescript
/**
 * Component A, finish-on-green (design §2). Ten census cells held a
 * hidden-suite pass inside the 32k/48 line and none stopped there: they ran
 * coverage and lint gates the task never asked for, repaired their own
 * scaffolding, deleted their own tests to reach a count, and in four cells
 * regressed the tree. When a self-test run inside a turn exits 0 and at
 * least one *source* mutation has landed since the last green, the Engine
 * steers once. A nudge, never a hard stop: release one's cell 511653 had
 * its own suite green with the hidden suite at 19 of 20 and fixed the last
 * case five turns later.
 *
 * The text is the design's, byte for byte, and names no test path (plan
 * Ruling 1): the prompt already lists the carried set, and a path list
 * built from the contract would put the developer's real test filenames
 * into a model-visible message.
 */
export const FINISH_STEER =
	"self_test passes on the current tree. If the requested change is complete, stop now and " +
	"report what you changed. Do not commit, add provenance rows, run the full repository suite, " +
	"run linters or type checkers, or change your tests to match a count; the developer reviews " +
	"the candidate and does those. If something in the request is still missing, say which part " +
	"and continue.";

/** A path whose mutation is not a source mutation (plan Ruling 2). */
export function isTestPath(path: string): boolean {
	const segments = path.split("/");
	if (segments.slice(0, -1).includes("tests")) return true;
	const name = segments[segments.length - 1];
	return name === "conftest.py" || name.startsWith("test_") || name.endsWith("_test.py");
}
```

In `registerRunner`, add beside `generation`/`checked`:

```typescript
	// A second generation counting only source mutations (plan Ruling 2):
	// the completion gate keeps using `generation`, which counts every
	// landed mutation, while the steer must not re-arm when a cell rewrites
	// its own tests -- which is exactly what 453263 and 470484 did after
	// their green. `nudged` is the source generation the last steer went
	// out for (null: none has).
	let sourceGeneration = 0;
	let nudged: number | null = null;
```

In the `tool_result` handler, the `edit` and `write` arms increment `sourceGeneration` as well when the path is not a test path:

```typescript
		if (event.toolName === "edit" && isRecord(event.details) && event.details.satyrn === true && event.details.ok === true) {
			generation += 1;
			const path = isRecord(event.input) && typeof event.input.path === "string" ? event.input.path : null;
			if (path !== null && !isTestPath(path)) sourceGeneration += 1;
			return undefined;
		}
		if (event.toolName === "write" && event.isError !== true) {
			generation += 1;
			const path = isRecord(event.input) && typeof event.input.path === "string" ? event.input.path : null;
			if (path !== null && !isTestPath(path)) sourceGeneration += 1;
			return undefined;
		}
```

and a shared helper, called from both the `self_test` arm and the redirected-bash arm, after the result is known:

```typescript
	/** One steer per source generation, on a green that happened inside a
	 * turn. Never on the enforced route (plan Ruling 3): that gate only runs
	 * when the model was already stopping. */
	const maybeSteer = async (details: RunnerToolDetails): Promise<void> => {
		if (!details.ok || details.result.exit_code !== 0 || details.result.timed_out) return;
		if (sourceGeneration === 0 || nudged === sourceGeneration) return;
		nudged = sourceGeneration;
		await note("finish_nudged", { generation: sourceGeneration });
		pi.sendMessage(
			{ customType: "finish_nudged", content: FINISH_STEER, display: true, details: undefined },
			{ deliverAs: "steer" },
		);
	};
```

The redirected-bash arm calls `await maybeSteer(result.details)` after `run()`; the `self_test` arm calls `await maybeSteer(event.details)` before its existing return. The `turn_end` handler is untouched by this task.

In `$ENGINE/src/satyrn_engine/budget.py` add `"finish_nudged"` to `GUARD_KINDS` and in `delivery.py` add `finish_nudged: int = 0` to `GuardFirings`.

In `$ENGINE/tools/replay_events.mjs`: read `fixture.testExitCode ?? 1` and use it in `fakeExchange`'s test result (with `output` and `compact_bytes` following from it: a zero exit yields `"4 passed in 0.1s\n"`); record `sent` across `tool_result` replays as well as `turn_end`; and add to `replayToolResult` the same `expect.steer` checks `replayTurnEnd` has for `followUp`, matching `options?.deliverAs === "steer"`.

- [ ] **Step 4: Run the tests and the gates.**

```bash
cd "$ENGINE" && uv run ruff check --fix && node --test --experimental-strip-types tests/test_runner.mjs; echo "EXIT: $?"   # EXIT: 0
node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"
# Expected: a line per fixture, including
# {"name":"finish-on-green-not-steered","events":5,"entries":0}
# {"name":"finish-on-green-steered","events":5,"entries":2}
# EXIT: 0
uv run python tools/provenance.py new tests/fixtures/events/finish-on-green-steered.json tests/fixtures/events/finish-on-green-not-steered.json
just gates; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Add one sentence to `docs/usage.md`** under the guards: "When `self_test` passes and a source file has changed since the last pass, the Engine sends one message saying the change may be complete and that commits, provenance rows, repository-wide suites, linters and test-count edits are the developer's."

- [ ] **Step 6: Commit** (engine tree).

```bash
cd "$ENGINE" && git add packages/engine/runner.ts src/satyrn_engine/budget.py src/satyrn_engine/delivery.py tools/replay_events.mjs tests/test_runner.mjs tests/test_budget.py tests/test_delivery.py tests/fixtures/events tests/fixtures/delivery docs/usage.md PROVENANCE.md
git commit -m "Release two Component A: one finish-on-green steer per source generation

Design 2026-09-17 section 2. Class: finishing; cells run-record-gate 470484,
533788, 609675, 275888, 891860, 949626, 016509 and docs-linter 374751, 453263,
845472. Offline estimate: run 2's method rescues 5 of 9 and 2 of 6 at the
32k/48 line, harm 0 in 39; run 1's rules count 0. Whether a 9B model obeys the
steer is section 7's measurement.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Component B — the runaway resume (engine)

Design §3. Class: runaway. Cells: cell-loop 442168, 346861, 332393, 225004, 507079; speed-probe 691593, 524583, 771490. All eight ended at exactly 16,000 tokens with no tool call, on a design think that opened on one detail.

**Files:**
- Modify: `$ENGINE/packages/engine/runner.ts` (`RESUME_MESSAGE`, `MAX_RESUMES`, `isLengthCut`, the `turn_end` handler)
- Modify: `$ENGINE/src/satyrn_engine/budget.py`, `$ENGINE/src/satyrn_engine/delivery.py` (`runaway_resumed`)
- Modify: `$ENGINE/tools/replay_events.mjs` (a `turn_end` event's message carries `usage`)
- Create: `$ENGINE/tests/fixtures/events/runaway-resumed.json`, `$ENGINE/tests/fixtures/events/runaway-not-resumed.json`
- Modify: `$ENGINE/tests/test_runner.mjs`, `$ENGINE/tests/test_budget.py`, `$ENGINE/tests/test_delivery.py`, `$ENGINE/tests/fixtures/delivery/receipt-*.json`, `$ENGINE/docs/usage.md`

**Interfaces:**
- Consumes: Task 5's `sourceGeneration`/`nudged` state and the unchanged `generation`/`checked` pair.
- Produces: `runner.ts` exports `RESUME_MESSAGE: string`, `MAX_RESUMES = 2`, `isLengthCut(message: unknown): boolean`; the `runaway_resumed` entry `{resume: number, output_tokens: number | null}`; `budget.GUARD_KINDS` and `delivery.GuardFirings` gain `runaway_resumed`.

- [ ] **Step 1: Write the failing tests.** Append to `$ENGINE/tests/test_runner.mjs`:

```javascript
test("a length-cut tool-free assistant turn is a runaway", () => {
	assert.equal(isLengthCut({ role: "assistant", stopReason: "length", content: [{ type: "text", text: "..." }] }), true);
	assert.equal(isLengthCut({ role: "assistant", stopReason: "stop", content: [{ type: "text", text: "..." }] }), false);
	assert.equal(isLengthCut({ role: "assistant", stopReason: "length", content: [{ type: "toolCall", id: "t", name: "edit" }] }), false);
	assert.equal(isLengthCut({ role: "user", stopReason: "length", content: [] }), false);
});

test("the resume text is the design's paragraph and asks for one tool call", () => {
	assert.match(RESUME_MESSAGE, /^Your last turn hit the per-turn output cap/);
	assert.match(RESUME_MESSAGE, /Do not restate the plan\./);
	assert.equal(MAX_RESUMES, 2);
});
```

Create `$ENGINE/tests/fixtures/events/runaway-resumed.json`: three length-cut tool-free turns before any mutation, the first two resumed and the third not (the cap):

```json
{
  "name": "runaway-resumed",
  "extension": "runner.ts",
  "testExitCode": 0,
  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {"app.py": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "writable_paths": ["app.py", "tests/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
  "expectedHandlers": {"tool_call": 1, "tool_result": 1, "turn_end": 1},
  "events": [
    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "length", "content": [{"type": "text", "text": "The identity mapping is..."}], "usage": {"output": 16000}}, "expect": {"followUp": "Your last turn hit the per-turn output cap"}},
    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "length", "content": [{"type": "text", "text": "Continuing the design..."}], "usage": {"output": 16000}}, "expect": {"followUp": "Your last turn hit the per-turn output cap"}},
    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "length", "content": [{"type": "text", "text": "Still thinking..."}], "usage": {"output": 16000}}, "expect": {"followUp": false}}
  ],
  "expectedEntries": [
    {"kind": "self_test_enforced", "data": {"generation": 0, "code": "OK", "exit_code": 0, "follow_up": false}},
    {"kind": "runaway_resumed", "data": {"resume": 1, "output_tokens": 16000}},
    {"kind": "runaway_resumed", "data": {"resume": 2, "output_tokens": 16000}}
  ]
}
```

Note the first entry: the completion gate runs once at generation 0 and passes (a green public suite before any mutation), sending nothing — which is §3's "the gate lets the session end, which is what happened in all eight cells". The resume is what changes that. On the second and third turns `checked === generation`, so the gate is silent.

Create `$ENGINE/tests/fixtures/events/runaway-not-resumed.json`, the silent direction: a clean stop is not a runaway; a length-cut turn *with* a tool call is not a runaway; and a length-cut tool-free turn whose completion gate found the tree red gets the gate's follow-up and no resume (Ruling 4):

```json
{
  "name": "runaway-not-resumed",
  "extension": "runner.ts",
  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {"app.py": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}, "writable_paths": ["app.py", "tests/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {}, "carried": [], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
  "expectedHandlers": {"tool_call": 1, "tool_result": 1, "turn_end": 1},
  "events": [
    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "length", "content": [{"type": "toolCall", "id": "e1", "name": "edit", "arguments": {}}], "usage": {"output": 16000}}, "expect": {"followUp": false}},
    {"type": "tool_result", "toolCallId": "e1", "toolName": "edit", "input": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}, "isError": false, "content": [{"type": "text", "text": "1 b"}], "details": {"satyrn": true, "ok": true, "code": "OK", "result": {"path": "app.py", "sha256": "1111111111111111111111111111111111111111111111111111111111111111", "region": "1 b"}}, "expect": {"patched": false}},
    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "length", "content": [{"type": "text", "text": "Now I will..."}], "usage": {"output": 16000}}, "expect": {"followUp": "Test command exited 1"}},
    {"type": "turn_end", "message": {"role": "assistant", "stopReason": "stop", "content": [{"type": "text", "text": "Done."}], "usage": {"output": 400}}, "expect": {"followUp": false}}
  ],
  "expectedEntries": [
    {"kind": "self_test_enforced", "data": {"generation": 1, "code": "OK", "exit_code": 1, "follow_up": true}}
  ]
}
```

Append to `$ENGINE/tests/test_budget.py` a row asserting `"runaway_resumed" in GUARD_KINDS`; to `$ENGINE/tests/test_delivery.py` a row asserting `GuardFirings().payload()["runaway_resumed"] == 0`; add `"runaway_resumed":0` to `guard_firings` in the five receipt fixtures.

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd "$ENGINE" && node --test --experimental-strip-types tests/test_runner.mjs; echo "EXIT: $?"
# Expected: "does not provide an export named 'RESUME_MESSAGE'". EXIT: 1
node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"
# Expected: runaway-resumed: expect.followUp "..." not one follow-up in []; expectedEntries.length 3 != 1
# EXIT: 1
```

- [ ] **Step 3: Implement.** In `$ENGINE/packages/engine/runner.ts`, add after `isFinalTurn`:

```typescript
/**
 * Component B, runaway resume (design §3). Eight of 33 build cells over two
 * census nights ended on one 16,000-token design think with no tool call,
 * each opening on a single detail the cell decided to reason out instead of
 * act on. The completion gate does not catch them: on a length-cut turn
 * before any mutation the public suite is green, so the gate lets the
 * session end, which is what happened in all eight.
 */
export const RESUME_MESSAGE =
	"Your last turn hit the per-turn output cap with no tool call, so nothing was done. Do not " +
	"restate the plan. Make the next concrete change with a tool call: read the one file you " +
	"need, or edit.";

/** Two resumes bound the cost at two more turns (design §3). */
export const MAX_RESUMES = 2;

/** An assistant turn cut by the per-turn output cap with no tool call. */
export function isLengthCut(message: unknown): boolean {
	if (!isRecord(message) || message.role !== "assistant") return false;
	if (message.stopReason !== "length") return false;
	const content = Array.isArray(message.content) ? message.content : [];
	return !content.some((part) => isRecord(part) && part.type === "toolCall");
}

/** The turn's output token count, when Pi's usage block carries one. */
function outputTokens(message: unknown): number | null {
	if (!isRecord(message) || !isRecord(message.usage)) return null;
	const output = message.usage.output;
	return typeof output === "number" ? output : null;
}
```

In `registerRunner`, add `let resumes = 0;` beside the other state, and extend the `turn_end` handler. The gate keeps its existing body; the change is that it records whether it sent, and the resume runs after it:

```typescript
	pi.on("turn_end", async (event) => {
		let gated = false;
		if (isFinalTurn(event.message) && checked !== generation) {
			const at = generation;
			const result = await runner.execute("self_test_enforced", {});
			checked = at;
			const details = result.details;
			const passed = details.ok && details.result.exit_code === 0 && !details.result.timed_out;
			const followUp = details.ok && !passed;
			await note("self_test_enforced", {
				generation: at,
				code: details.code,
				exit_code: details.ok ? details.result.exit_code : null,
				follow_up: followUp,
			});
			if (followUp) {
				gated = true;
				pi.sendMessage(
					{ customType: "self_test_enforced", content: enforcedMessage(result.content[0].text), display: true, details: undefined },
					{ deliverAs: "followUp" },
				);
			}
		}
		// Plan Ruling 4: the gate goes first and suppresses the resume for
		// this turn. Two Engine messages in one turn read as contradiction,
		// and the gate's "your tree is red, here is why" gets a tool call as
		// surely as the resume would. A runaway before any mutation leaves
		// the public suite green, so the gate is silent and the resume is
		// the only message -- the eight cells' exact shape.
		if (gated || !isLengthCut(event.message) || resumes >= MAX_RESUMES) return;
		resumes += 1;
		await note("runaway_resumed", { resume: resumes, output_tokens: outputTokens(event.message) });
		pi.sendMessage(
			{ customType: "runaway_resumed", content: RESUME_MESSAGE, display: true, details: undefined },
			{ deliverAs: "followUp" },
		);
	});
```

Add `"runaway_resumed"` to `budget.GUARD_KINDS` and `runaway_resumed: int = 0` to `delivery.GuardFirings`. In `$ENGINE/tools/replay_events.mjs`, `replayTurnEnd` passes the fixture's `message` through unchanged (it already does) and must allow **more than one** queued message across the fixture, comparing only the slice queued by this event (it already slices) — the change needed is that `expect.followUp` as a string accepts the queued message when `queued.length === 1`, which holds in both fixtures because the gate and the resume never both send.

- [ ] **Step 4: Run the tests and the gates.**

```bash
cd "$ENGINE" && uv run ruff check --fix && node --test --experimental-strip-types tests/test_runner.mjs; echo "EXIT: $?"   # EXIT: 0
node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"
# Expected, among the others:
# {"name":"runaway-not-resumed","events":4,"entries":1}
# {"name":"runaway-resumed","events":3,"entries":3}
# EXIT: 0
uv run python tools/provenance.py new tests/fixtures/events/runaway-resumed.json tests/fixtures/events/runaway-not-resumed.json
just gates; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: The extensions load in real Pi 0.85.1, without a model.** Extensions load before the model is resolved, so an unresolvable model ends the run before any request. No inference.

```bash
cd "$ENGINE" && SATYRN_ENGINE_REPO="$PWD" pi --print --mode json --no-session --model nope/nope --no-extensions \
  --extension "$PWD/packages/engine/engine.ts" --extension "$PWD/packages/engine/mutator.ts" \
  --extension "$PWD/packages/engine/scope.ts" --extension "$PWD/packages/engine/bounds.ts" \
  --extension "$PWD/packages/engine/runner.ts" --no-skills --no-prompt-templates hi; echo "EXIT: $?"
# Expected: Error: Model "nope/nope" not found. ... EXIT: 1, and no "Failed to load extension" line.
```

- [ ] **Step 6: Add one sentence to `docs/usage.md`**: "When a turn hits the per-turn output cap with no tool call, the Engine asks once for a concrete next step, at most twice per session."

- [ ] **Step 7: Commit** (engine tree). **This is the last engine commit; the engine freezes here.**

```bash
cd "$ENGINE" && git add packages/engine/runner.ts src/satyrn_engine/budget.py src/satyrn_engine/delivery.py tools/replay_events.mjs tests/test_runner.mjs tests/test_budget.py tests/test_delivery.py tests/fixtures/events tests/fixtures/delivery docs/usage.md PROVENANCE.md
git commit -m "Release two Component B: one follow-up on a length-cut turn with no tool call, twice at most

Design 2026-09-17 section 3. Class: runaway; cells cell-loop 442168, 346861,
332393, 225004, 507079 and speed-probe 691593, 524583, 771490, all ending at
exactly 16,000 tokens on a design think. No offline estimate is replayable:
the intervention changes the events after it. Section 7 measures it live.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Evals counts the two firings and follows the record's backstop (evals)

Two things: without `finish_nudged` and `runaway_resumed` in `pathology.GUARD_KINDS`, every cell where either fires reads `unknown_event` and the record is void; and §5.4's deliver timeout, the open arm-parity defect `STATE.md` names ("the Engine's `DELIVER_TIMEOUT_SECONDS` is 1800 while the record's backstop is 3,000, so an Engine cell stops earlier than Baseline's").

**Files:**
- Modify: `$EVALS/src/satyrn_evals/pathology.py` (`GUARD_KINDS`)
- Modify: `$EVALS/src/satyrn_evals/cell_evidence.py` (`finish_nudges`, `runaway_resumes`, `turns_after_nudge`)
- Modify: `$EVALS/src/satyrn_evals/attempt_engine.py` (`DELIVER_MARGIN_SECONDS`, `deliver_argv`'s `backstop_s`)
- Modify: `$EVALS/src/satyrn_evals/cell_engine.py` (or whichever module calls `deliver_argv`) to pass the record's backstop
- Modify: `$EVALS/tests/test_pathology.py`, `$EVALS/tests/test_cell_evidence.py`, `$EVALS/tests/test_attempt_engine.py`

**Interfaces:**
- Consumes: Tasks 5 and 6's entry kinds and payload shapes (`finish_nudged {generation}`, `runaway_resumed {resume, output_tokens}`).
- Produces: `CellEvidence.finish_nudges: int`, `CellEvidence.runaway_resumes: int`, `CellEvidence.turns_after_nudge: int | None`; `attempt_engine.DELIVER_MARGIN_SECONDS = 60`; `deliver_argv(args, worktree, contract, *, no_sync=False, backstop_s: int)`.

- [ ] **Step 1: Write the failing tests.** Append to `$EVALS/tests/test_pathology.py`:

```python
def test_the_two_new_engine_entries_are_measured_guard_kinds():
    assert {"finish_nudged", "runaway_resumed"} <= GUARD_KINDS


def test_a_cell_with_a_finish_nudge_is_not_unknown_event():
    transcript = "\n".join([
        json.dumps({"type": "agent_start"}),
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "entry_appended", "entry": {"customType": "finish_nudged",
                                                        "data": {"generation": 1}}}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "agent_end"}),
    ])
    assert measure(transcript).measured is True


def test_an_entry_kind_the_engine_never_appends_is_still_unknown_event():
    transcript = "\n".join([
        json.dumps({"type": "agent_start"}),
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "entry_appended", "entry": {"customType": "invented_kind", "data": {}}}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "agent_end"}),
    ])
    measured = measure(transcript)
    assert measured.measured is False and measured.reason == "unknown_event"
```

Append to `$EVALS/tests/test_cell_evidence.py`:

```python
def test_evidence_counts_both_new_firings_and_the_turns_after_the_first_nudge():
    lines = [
        json.dumps({"type": "agent_start"}),
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "entry_appended", "entry": {"customType": "finish_nudged",
                                                        "data": {"generation": 1}}}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "entry_appended", "entry": {"customType": "runaway_resumed",
                                                        "data": {"resume": 1, "output_tokens": 16000}}}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "agent_end"}),
    ]
    evidence = collect_evidence("\n".join(lines))
    assert evidence.finish_nudges == 1
    assert evidence.runaway_resumes == 1
    assert evidence.turns_after_nudge == 2


def test_a_cell_with_no_nudge_reports_none_for_the_turns_after():
    lines = [
        json.dumps({"type": "agent_start"}),
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "agent_end"}),
    ]
    evidence = collect_evidence("\n".join(lines))
    assert evidence.finish_nudges == 0
    assert evidence.turns_after_nudge is None
```

Append to `$EVALS/tests/test_attempt_engine.py`:

```python
def test_the_deliver_timeout_is_the_records_backstop_less_the_margin():
    argv = deliver_argv(ENGINE_ARGS, Path("/w"), Path("/w/c.yaml"), backstop_s=4800)
    assert argv[argv.index("--timeout") + 1] == str(4800 - DELIVER_MARGIN_SECONDS)


def test_a_backstop_at_or_below_the_margin_still_leaves_a_positive_timeout():
    argv = deliver_argv(ENGINE_ARGS, Path("/w"), Path("/w/c.yaml"), backstop_s=30)
    assert int(argv[argv.index("--timeout") + 1]) > 0


def test_the_module_no_longer_carries_a_fixed_half_hour():
    import satyrn_evals.attempt_engine as module
    assert not hasattr(module, "DELIVER_TIMEOUT_SECONDS")
```

- [ ] **Step 2: Run them and watch them fail.**

```bash
cd "$EVALS" && uv run pytest -q tests/test_pathology.py tests/test_cell_evidence.py tests/test_attempt_engine.py; echo "EXIT: $?"
# Expected: the GUARD_KINDS assertion, unknown_event on both new kinds, AttributeError on
# finish_nudges/runaway_resumes/turns_after_nudge, and TypeError on backstop_s. EXIT: 1
```

- [ ] **Step 3: Implement.** In `$EVALS/src/satyrn_evals/pathology.py`, extend `GUARD_KINDS` and its comment:

```python
GUARD_KINDS = frozenset(
    {
        "loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out",
        "self_test_redirected", "self_test_enforced",
        # Release two: the finish-on-green steer (design §2) and the runaway
        # resume (design §3). Without them every cell where either fires
        # reads `unknown_event` and the record is void.
        "finish_nudged", "runaway_resumed",
    }
)
```

In `$EVALS/src/satyrn_evals/cell_evidence.py`, `guard_firings` already counts every `GUARD_KINDS` entry generically, so `finish_nudges` and `runaway_resumes` are named projections of it; `turns_after_nudge` is the count of `turn_start` events strictly after the first `finish_nudged` entry, or `None` when none fired. Add the three fields to the dataclass, to the `to_block()` payload, and compute them in the same pass that builds `guard_firings`.

In `$EVALS/src/satyrn_evals/attempt_engine.py`, replace the constant and widen the signature:

```python
#: How far below the record's per-attempt-command backstop the Engine's own
#: deliver timeout sits (design §5.4; plan Ruling 9). Parity: until release
#: two, `DELIVER_TIMEOUT_SECONDS = 1800` stopped an Engine cell earlier than
#: Baseline's 3,000 or 4,800 s backstop, which `STATE.md` lists as an open
#: arm-parity defect. The margin makes the Engine's own deliver stop just
#: before the harness kills the command, so the Engine writes its receipt and
#: leaves its candidate rather than dying with no evidence.
DELIVER_MARGIN_SECONDS = 60


def deliver_timeout(backstop_s: int) -> int:
    return max(backstop_s - DELIVER_MARGIN_SECONDS, 1)
```

and `deliver_argv(args, worktree, contract, *, no_sync=False, backstop_s: int)` uses `str(deliver_timeout(backstop_s))`. Its caller (`cell_engine.py`, or `cell.py` where the Engine command is assembled) already holds the record's `command_backstop_s`; thread it through as a required keyword so no call site can silently keep the old number.

- [ ] **Step 4: Run the tests and the gates.**

```bash
cd "$EVALS" && uv run ruff check --fix && uv run pytest -q; echo "EXIT: $?"   # EXIT: 0
just gates; echo "EXIT: $?"   # EXIT: 0
```

- [ ] **Step 5: Commit** (evals tree). No new file, so `PROVENANCE.md` is not touched — the concurrent authored-task agent owns it.

```bash
cd "$EVALS" && git add src/satyrn_evals/pathology.py src/satyrn_evals/cell_evidence.py src/satyrn_evals/attempt_engine.py src/satyrn_evals/cell_engine.py tests/test_pathology.py tests/test_cell_evidence.py tests/test_attempt_engine.py
git commit -m "Release two: evals counts the two new Engine firings and follows the record's backstop

The design's Components A and B append finish_nudged and runaway_resumed;
without them in GUARD_KINDS every cell where either fires reads unknown_event.
Section 5.4 closes the arm-parity defect STATE.md names: the Engine's deliver
timeout was a fixed 1800 s against a 3,000 or 4,800 s record backstop.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: The Engine arm pins the frozen release-two commit (evals)

**Files:**
- Modify: `$EVALS/arms/engine-ornith15-9b.json` (`argv[2]`, `pins.engine_commit`, `pins.digests`), `$EVALS/tests/test_arms.py`, `$EVALS/tests/test_launch_record.py`

**Interfaces:**
- Consumes: Task 6's engine commit (`git -C "$ENGINE" rev-parse release-one`).
- Produces: the arm at that commit. `mutator.ts`, `runner.ts` and the four others that Tasks 1–6 touched change digest; `ENGINE_SOURCES` is unchanged, still the seven files.

- [ ] **Step 1: Re-pin.** From `$EVALS`, with the engine checkout at Task 6's commit and no engine change outstanding:

```bash
cd "$EVALS" && git -C "$ENGINE" status --porcelain; echo "clean if nothing above"
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
git diff --stat
# Expected: arms/engine-ornith15-9b.json with argv, engine_commit and the digests for
# mutator.ts and runner.ts changed (engine.ts, scope.ts, bounds.ts, orchestrator.ts and
# paths.ts were not edited by this plan and must be unchanged); one line in each test file.
```

- [ ] **Step 2: Gates and the pin check.**

```bash
cd "$EVALS" && just gates; echo "EXIT: $?"   # EXIT: 0
SATYRN_V4_ENGINE_REPO="$ENGINE" TMPDIR="$SCR/bt" uv run pytest -m integration -q --basetemp "$SCR/bt/t8" tests/integration/test_engine_arm_pins.py; echo "EXIT: $?"   # EXIT: 0 (git reads only; not an isolated row)
```

- [ ] **Step 3: Commit** (evals tree).

```bash
cd "$EVALS" && git add arms/engine-ornith15-9b.json tests/test_arms.py tests/test_launch_record.py
git commit -m "Release two: the Engine arm pins engine ${NEW:0:7} (finish-on-green, runaway resume, parity)

mutator.ts and runner.ts change digest; the other five pinned sources are
unchanged. The engine is frozen at this commit for the route proof.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Whole-path review, before any record is written

Opus reviews the whole path across both trees before the operator section runs. Not a per-task review: the question is whether the eight commits together leave a system whose route proof can be read. The reviewer runs both `just gates`, reads the two trees' diffs against `ea49666` and `5310ccb`, and answers, in writing:

1. Does every Engine component have a firing fixture **and** a silent fixture, and does the silent one fail if the component is disabled? (Disable each in a scratch clone and confirm the replay goes red.)
2. Do Components A and B ever both send in one turn? Ruling 4 says no; `runaway-not-resumed`'s third event is the proof.
3. Does the size refusal change anything the model sees? Ruling 7 says no; grep the prompt for the refusal text.
4. Do the parity changes (Tasks 2 and 3) change what Baseline can do? They must not: Baseline runs no Engine extension.
5. Is `arms/engine-ornith15-9b.json` pinned to a commit that exists on `release-one` and holds every change?
6. Is Ruling 6 ratified by the maintainer? Task 4 does not stand without it.

---

## Operator: the export, the three route-proof records, and the reading

Not run by the controller: the export changes the real cells root and the launches spend inference. Run from `$EVALS` after the whole-path review, one record at a time. `launch` exits 0 complete, 1 preflight problems, 2 usage error, 3 infrastructure/interrupted, 4 capped at the sitting limit. Exit 4: run the same `launch` again, committing nothing first. Exit 1, 2 or 3: stop, report the result's `reason` and the launcher's stderr verbatim, commit nothing.

The 2026-09-15 `--no-sync` lesson applies: the export is read-only to the cell, and an isolated row that makes a real protocol exchange against it stays green because `derive` and `deliver` run out of the export's own synced `.venv`, never syncing at run time.

```bash
cd "$EVALS"
# 0. No cell is running, and the chain's tail is the census-2 speed-probe result.
ls /Users/Shared/satyrn-cells | grep satyrn-attempt; echo "none running if nothing above"
CHAIN=records/2026-09-17-census2-selfhost-speed-probe.result.json
test -f "$CHAIN" && echo "chain tail present"

# 1. The cells root holds only the current export.
NEW=$(python3 -c 'import json; print(json.load(open("arms/engine-ornith15-9b.json"))["pins"]["engine_commit"])')
mv /Users/Shared/satyrn-cells/engine-8049d739799c8b40978e0cbc3d76a1beb49e1bd1 ~/.Trash/
uv run satyrn-evals cell-engine --engine-repo "$ENGINE" --commit "$NEW"
uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell; echo "EXIT: $?"   # EXIT: 0

ARM=arms/engine-ornith15-9b.json
AUTH="maintainer: route proof on the claim tasks, approved in 2026-09-17-release-two-engine-design.md section 7 on 2026-09-17; these cells are read for behaviour only and are excluded from every comparison denominator"
RULE="section 7 go criterion, behaviour only, no outcome: the steer fires in 3 of 4 own-green cells and the model stops within three turns in 2 of those 3; a resume produces a tool call in 2 of 3. Below that, the design returns to the maintainer."

# 2. One record per task, run in order, each chained to the previous result.
# n = 2 on the two claim tasks (design §7), n = 3 on cell-loop for the resume.
# Mode is batch, not attended: gate() refuses attended when command_backstop_s + 300 > max_minutes*60,
# and 4800 + 300 = 5100 s against attended's 3600 s ceiling (plan Ruling 10).
route_proof() {
  local TASK="$1" N="$2" PREV="$3" OUT RUNG rc
  OUT="records/2026-09-17-route-proof-engine-$TASK.json"
  RUNG=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["rung"] or "contract")' \
         "records/2026-09-16-census-$TASK.json")

  uv run satyrn-evals record new --output "$OUT" --task "$TASK" --rung "$RUNG" --arm engine \
    --n "$N" --k 3 --purpose route-proof --isolation isolated --mode batch --max-minutes 120 \
    --token-budget 48000 --turn-budget 72 --command-backstop 4800 \
    --previous-result "$PREV" --authority "$AUTH" --decision-rule "$RULE"

  uv run satyrn-evals launch --preflight "$OUT" --arm $ARM; rc=$?
  if [ "$rc" -ne 0 ]; then echo "$TASK: preflight EXIT $rc; commit nothing"; return "$rc"; fi
  git add "$OUT" && git commit -m "Release two route-proof record: $TASK (Engine at ${NEW:0:7}, n=$N, k=3, isolated, excluded)"

  uv run satyrn-evals launch "$OUT" --arm $ARM & wait $!; rc=$?
  while [ "$rc" -eq 4 ]; do
    echo "$TASK: EXIT 4 (sitting cap); running the same launch again, nothing committed yet"
    uv run satyrn-evals launch "$OUT" --arm $ARM & wait $!; rc=$?
  done
  if [ "$rc" -ne 0 ]; then echo "$TASK: launch EXIT $rc; report reason and stderr verbatim; commit nothing"; return "$rc"; fi
  git add "${OUT%.json}.result.json" && git commit -m "Release two route-proof result: $TASK ($(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${OUT%.json}.result.json"))"
}

route_proof selfhost-run-record-gate 2 "$CHAIN"
route_proof selfhost-docs-linter    2 records/2026-09-17-route-proof-engine-selfhost-run-record-gate.result.json
route_proof selfhost-cell-loop      3 records/2026-09-17-route-proof-engine-selfhost-docs-linter.result.json

# 3. The reading table. Retained transcripts only; writes nothing.
uv run python - 2026-09-17-route-proof-engine-selfhost-run-record-gate \
                2026-09-17-route-proof-engine-selfhost-docs-linter \
                2026-09-17-route-proof-engine-selfhost-cell-loop <<'PY'
import json
import sys
from pathlib import Path

from satyrn_evals.cell_evidence import collect_evidence

print("night | cell | code | verdict | turns | out_tokens | nudges | turns_after_nudge | "
      "resumes | enforced | first_pass (turn, tokens, route)")
for stem in sys.argv[1:]:
    arm = Path.home() / "satyrn-runs" / stem / "engine"
    if not arm.is_dir():
        print(f"{stem} | no night directory")
        continue
    for cell in sorted(p for p in arm.iterdir() if (p / "attempt.json").is_file()):
        attempt = json.loads((cell / "attempt.json").read_text(encoding="utf-8"))
        transcript = cell / "transcript.txt"
        if not transcript.is_file():
            print(f"{stem} | {cell.name} | {attempt['code']} | {attempt['verdict']} | no transcript")
            continue
        ev = collect_evidence(transcript.read_text(encoding="utf-8"))
        first = ev.first_passing_self_test
        shown = "-" if first is None else f"{first['turn']}, {first['output_tokens']}, {first['route']}"
        print(f"{stem} | {cell.name} | {attempt['code']} | {attempt['verdict']} | {ev.turns} | "
              f"{ev.output_tokens} | {ev.finish_nudges} | {ev.turns_after_nudge} | "
              f"{ev.runaway_resumes} | {ev.guard_firings.get('self_test_enforced', 0)} | {shown}")
PY
```

- [ ] **4. The census page gains the exclusion row.** After the three results are committed, the operator appends to `evidence/2026-09-16-census/README.md`, under "Deviations, stated", and commits it:

> **Three route-proof records are excluded from every comparison denominator,** by the maintainer's choice of §7's first option on 2026-09-17: `records/2026-09-17-route-proof-engine-selfhost-run-record-gate.json` (n = 2), `…-selfhost-docs-linter.json` (n = 2) and `…-selfhost-cell-loop.json` (n = 3), all Engine at the release-two commit, `--purpose route-proof`. They are read for behaviour only — did the steer fire at own-green, did the model stop within three turns of it, did a resume produce a tool call — and never for an outcome.

### Reading template for the route-proof cells

One line per question, from the table and the result files. These cells decide no task outcome.

1. **Did the steer fire at own-green?** Per claim-task cell: `nudges`, and the turn each `finish_nudged` entry sits on against the turn of that cell's first passing self-test. The steer fired at own-green when the two are the same turn. Denominator: the cells that reached a green self-test at all; say so, and name any cell that never went green, which is a cell the question cannot be asked of.
2. **Did the model stop within three turns of it?** `turns_after_nudge` per nudged cell. "Stopped" is the session ending (`agent_end`) within three `turn_start` events of the nudge. Quote what the model did in those turns from the transcript — a cell that stopped because it hit the token budget did not stop because of the steer, and must be read as not stopping.
3. **Did a resume produce a tool call?** Per cell-loop cell: `resumes`, and for each `runaway_resumed` entry whether the next turn holds a `tool_execution_start`. Denominator 3 cells; a cell that never ran away is a cell the question cannot be asked of, and is named, not counted as a failure.
4. **Did the gate and the resume ever both fire on one turn?** They must not (Ruling 4). Read `self_test_enforced` beside `runaway_resumed` per turn; any co-firing is an implementation defect, not a finding.
5. **Side effects.** `code` and `verdict` per cell; the result's `pathology` block. A cell reading `unknown_event` or `malformed` points at Task 7 or at a `sendMessage` path — `finish_nudged` as a `steer` is the one delivery Phase 3b never exercised live, and Ruling 5's reading of `runLoop` is the only evidence it behaves. Also watch the `size_refusal` on cell-loop's receipts: it must be present and must not appear in any transcript.
6. **The decision.** The §7 go criterion, read from lines 1–3: the steer fires in 3 of 4 own-green cells and the model stops within three turns in 2 of those 3; a resume produces a tool call in 2 of 3. Above it, the comparison is sized at the R0 sitting (§8). Below it, the design returns to the maintainer. Either way the three records stay excluded from every denominator.

---

## Self-review against the spec

- **§2 Component A** — Task 5, with the spec's text verbatim (Ruling 1), once per source mutation generation (Ruling 2), `deliverAs: "steer"`, `finish_nudged` recorded, counted by evals in Task 7. Not fired on a red self_test or with no mutation: `finish-on-green-not-steered`. Suppressed on the enforced route: Ruling 3.
- **§3 Component B** — Task 6, `stopReason: "length"` with no tool call, at most twice per cell, `runaway_resumed` with the turn's token count, counted in Task 7. Pi 0.85.1's follow-up path on a length-cut tool-free turn is verified against `agent-loop.js` `runLoop` and cited in Ruling 5.
- **§4 Component C** — Task 1, three `E ` lines per failed test after the assertion, and the receipt's `validation_output_bytes`.
- **§5 parity** — Task 2 (multi-edit, schema and Python apply), Task 3 (prompt collapse; writable paths from `Files:` only), Task 7 (deliver timeout = the record's `command_backstop_s`, less Ruling 9's margin).
- **§6 the boundary** — Task 4, a refusal asking the developer to split, with the medium class defined mechanically in Ruling 6 and pinned against all seven tasks in `test_derive_size.py`. Advisory per Ruling 7.
- **§7 route proof** — the operator section: Engine arm, `--purpose route-proof`, isolated, batch (Ruling 10), n = 2 on the two claim tasks and n = 3 on cell-loop, 48,000/72, `--command-backstop 4800`, k = 3, chained from the census-2 speed-probe result, the §7 go criterion as the decision rule read for behaviour only, the authority naming the approval and the exclusion, and four exclusion markers (Ruling 11). The reading template answers §7's three questions.
- **§10 rules carried** — replay fixtures both directions per component (Tasks 5 and 6), both trees' gates per task, whole-path review before any record, commits with explicit paths, no push/merge/amend, the engine frozen at Task 6 and pinned at Task 8 before the export.
- **Placeholders:** none. Every name used in a later task is defined in an earlier one: `FINISH_STEER`, `isTestPath`, `sourceGeneration`, `RESUME_MESSAGE`, `MAX_RESUMES`, `isLengthCut`, `finish_nudged`, `runaway_resumed`, `replace_many`, `MAX_REPLACEMENTS`, `files_block`, `produces_names`, `size_refusal`, `PROMPT_LIST_CAP`, `EXPLANATION_LINES`, `DELIVER_MARGIN_SECONDS`, `finish_nudges`, `runaway_resumes`, `turns_after_nudge`.

## What this plan does not have

**The code blocks were not executed.** Phase 3b's plan was prototyped in scratch clones and every expected output in it was observed; this one was written from the sources. The implementer treats each "Expected" line as a prediction: a divergence is reported in the task report, and a task that fails acceptance twice stops, per `AGENTS.md`.
