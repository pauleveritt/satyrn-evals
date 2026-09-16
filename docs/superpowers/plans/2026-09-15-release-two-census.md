# Release two R0 — the pathology census Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-15 against evals `release-one` at `e27d4bc`.** The spec leaves several details open; each is decided below as a Ruling, with its reason, for the maintainer to review. Nothing here was executed: no model was run, no record written, nothing under `/Users/Shared/satyrn-cells` or `~/satyrn-runs` touched, nothing written under `docs/results/` or `docs/reviews/`. Nine tasks.

**Goal:** Put the harness, the five tasks and the five records into the state the approved census design requires, so that one Baseline-only night of thirty cells can be launched by the maintainer and classified the day after by binding constraint.

**Architecture:** Four harness changes (a per-turn output cap in both arm files; a graded `tripped_verdict` for cells torn down at the budget; a `command_backstop_s` run-record field replacing a module constant; the section 6 evidence fields), two task changes (a new `R2` rung for `agentclinic-repair-depth-3`; a recorded `prompt_edits` mechanism in the cut generator, used to fix `selfhost-run-record-gate`), a recorded task-validity check per task, one classification module split between the package (pure rules, tested) and a frozen evidence driver (night-specific, beside its outputs), and finally five frozen records plus the launch script. Everything before the night is deterministic, offline and default-tier.

**Tech Stack:** Python 3.14, uv, pytest, ruff, just, git. Reused evals code: `satyrn_evals.budget.UsageCounter`, `satyrn_evals.cell_evidence.collect_evidence`, `satyrn_evals.session_patch.build_cumulative_patch` and `RESIDUE_EXCLUDES`, `satyrn_evals.grade.grade`, `satyrn_evals.attempt_record`, `satyrn_evals.run_record`, `satyrn_evals.launch_record`, `tools/cut_task.py`, `scripts/preflight_settings.py`.

**Spec:** `docs/superpowers/specs/2026-09-15-release-two-census-design.md` (approved 2026-09-15, six decisions in its section 9). Bound by `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`. Section numbers below are that design's. The release-one design and the earlier phase plans are evidence for a named question, never guidance.

---

## Rulings

Each is a decision the spec left open, with the reason it was decided that way.

1. **`length_stops` counts one per assistant `message_end` whose `message.stopReason` is `"length"`.** Not `turn_end`, not `turn_start`, not a per-turn boolean. Reason: the budget counter already sums `usage.output` off exactly those events (`budget.UsageCounter.feed_event`), so the cap's own counter and its evidence field read the same stream and cannot disagree about which messages were the model's. Under the declared section 3.1 semantics a length-cut turn that carries tool calls continues, so one turn can produce several such messages; counting per turn would report 1 where the cell was cut twice. `turn_end` also carries `stopReason` (`turn_ledger._classify`), and a fixture asserts a `turn_end` with `stopReason: length` does **not** add to the count, so the two event families can never double-count.

2. **`tripped_verdict` is graded through the same `grade()` call the OK path uses, is never a pass, and never touches contamination.** Same task directory, same manifest, so the allowlist, `ignored_paths` and the hidden-suite oracle bite exactly as they do for a delivered patch — the point of the secondary is to say what the tripped worktree *would* have graded, and a different grading path would not answer that. "Never a pass" means three things, all tested: `verdict` stays `null` on the attempt record, so `AttemptCode.BUDGET_EXCEEDED` keeps its `_Presence.FORBIDDEN` verdict policy; `compute_summary`'s pass counts and denominators do not move; and the field is reported as its own column, never folded into a rate (BRIEF invariant 3). Contamination is computed from the transcript's overlay windows, not from the patch, so it is untouched: a tripped cell that is contamination-flagged keeps the flag, and its `tripped_verdict` is printed beside the flag, never in place of it. A contaminated tripped cell is therefore reportable as "would have graded pass, and read grader material" — which is the honest pair.

3. **`command_backstop_s` does not bound the Engine arm's `DELIVER_TIMEOUT_SECONDS`; that constant stays at 1800.** Three reasons. (a) The census is Baseline-only, so no census cell reads it. (b) The run record does not reach the adapter: `attempt` hands the adapter an opaque argv built from the arm file, so wiring the record into the Engine's deliver timeout means a new arm-config seam — an Engine change before the census, which R0 §1 forbids. (c) The asymmetry it leaves is real and is written down rather than fixed here: an Engine cell run under a 3,000 s backstop would have its inner `deliver` stopped at 1,800 s while the Baseline cell runs to 3,000 s, which is not "identical tools across arms". That is a release-two comparison defect, recorded in Task 9's carried-forward list; it must be fixed before the first Engine record, not before this night.

4. **`R2` is `R1` with one clause replaced and nothing else.** Exactly: `the third fails assert None is not None,` becomes `the third fails assert None is not None, where None = first.timestamp.tzinfo,`. Reason: section 4 says "R1 text plus pytest's own explanation of the third failure" and quotes that explanation; keeping R2 − R1 a single-fact difference is what makes the information diagnosis in `KNOWN_DEFECTS.md` testable — if depth-3 cells now find the `models.py` seam, the added fact is why, and nothing else changed. R1 stays in the manifest as evidence (section 4), and `contract` (the default) stays equal to `R3`.

5. **The prompt-edit schema is `{old, new, reason}`, applied in order after the cut, recorded under `generator.prompt_edits`, and checked twice.** `old`, `new` and `reason` are non-empty strings. Each `old` must occur exactly once in the prompt *as it stands when that edit is applied*, so a later edit may depend on an earlier one; otherwise `CutError`. `new` must not contain that edit's own `old` (otherwise `CutError`), which is what makes the pure check below decidable. The applied list is recorded verbatim in the manifest under `generator.prompt_edits`, beside `plan` — the prompt's provenance is already `generator` (tool, rung, files, hidden, plan anchor), and putting the patch anywhere else would separate the plan anchor from the patch applied to it. Two checks, deliberately different: `cut_task.py check` re-derives the whole tree from history and so proves the recorded edits reproduce the prompt from the plan (it needs git, and it is the operator step before records are frozen); `qualify`'s new `judge_prompt_edits` is pure and default-tier — for every recorded edit, `new` occurs exactly once in `contracts["R1-plan"]` and `old` occurs zero times — so the gate a record's admission reads needs neither git nor the plan history.

6. **The validity solver sees a copy of `base/` and the prompt text, and nothing else.** The controller copies `<task>/base/` to `<scratchpad>/validity/<task>/tree`, `git init`s and commits it, and writes `<scratchpad>/validity/<task>/PROMPT.txt` from the manifest's `contracts[rung]`. `overlay/`, `fixtures/`, `manifest.json` and `qualification.json` sit beside `base/` inside the task directory, so copying the task directory would hand the solver the answer; copying only `base/` is the same artefact the census cell gets. The subagent is told that tree is its only readable and writable area, and that the evals checkout, `~/satyrn-runs`, `/Users/Shared` and every path outside it are off limits. The controller, not the agent, harvests `git diff` and runs two leak tells over the diff and the agent's final report: any id from the manifest's `expected_test_ids`, and any of the strings `overlay`, `known-good.patch`, `known-broken.patch`, `manifest.json` or the task directory's path. A hit voids the run; it is redone with a fresh agent and the void is recorded in the result. Grading is `satyrn-evals grade TASK patch.diff --receipt receipt.json` from a grade root with no `pyproject.toml`/`conftest.py` in it or above it (the counterfactual plan's Ruling 9 finding), with `UV_OFFLINE=1`. Matching the known-good patch is *not* a leak tell: a correct solution is supposed to look like the fix.

7. **The task-7 tooling splits three ways: new rules into the package, pre-registered rules imported by path, the night driver under `evidence/`.** The run-2 scripts hardcode cell sets and are excluded from ruff and pyrefly — acceptable for one night, not for the table that picks release two's claim. So the rules the census adds (per-turn arithmetic, the 32k line, one boolean per mechanically decidable class, whole-attempt seconds) go into `src/satyrn_evals/census_classify.py`, where they are linted, typed and tested in the default tier. The replay, own-green and trigger rules do **not** move: they stay in `evidence/2026-09-15-finishing-counterfactual/counterfactual.py`, unmodified, and the driver loads them by path exactly as `run-2/trajectory.py` already does. Reason: section 7 asks for "run 1's pre-registered rules and run 2's replay method" on the new cells, and those rules were pre-registered before run 1, reviewed by Opus line by line, and produced committed outputs — re-implementing or relocating them would make the census a different instrument from the one whose numbers it is being compared with, and would edit old evidence. The night-specific half — reading a night directory and a record, the grade subprocesses, the output files — is `evidence/2026-09-16-census/classify.py`, frozen beside its outputs. `evidence/2026-09-15-finishing-counterfactual/` and its `run-2/` are read, never written.

8. **"Whole-attempt seconds" (section 6) is an offline field, not a new harness clock.** Section 3 says "Nothing else changes in the harness", and the two stamps already exist: the attempt directory's name carries a microsecond UTC timestamp (`attempt.attempt_dir_name`) and `attempt.json` is written last. The census scripts compute whole-attempt seconds as `mtime(attempt.json) − parse(attempt_dir name)`. `timeline.jsonl` is monotonic and holds only tool events, so it gives first-to-last tool seconds and cannot give the whole attempt. Both numbers are reported with that difference stated.

9. **Section 3.1's Pi-loop semantics are declared, not verified by this plan.** No step here runs Pi or a model. The fixtures prove what the *harness* does when a transcript carries a length stop — the budget tripwire still sums `usage.output`, the evidence counts it, the cell is not voided — not what Pi's agent loop does with a truncated tool call. If the first census cells show a length-cut turn with tool calls ending the session, that contradicts section 3.1 and is reported to the maintainer as a finding; it is never worked around mid-night.

10. **No file is written under `docs/results/` or `docs/reviews/`.** The launcher writes `records/<name>.result.json` and the per-arm `summary.json` under the night; it has never written `docs/results/*.md`. Section 7's "one result page per task, written by the launcher into the results directory" is read as those committed `.result.json` files. The census page is `evidence/2026-09-16-census/README.md`, ≤ 120 lines with a fenced recompute block, written by the maintainer from the committed outputs after the night.

11. **The attempt deadline follows the backstop by a constant 300 s: `attempt_timeout = command_backstop_s + 300`.** Today `ATTEMPT_DEADLINE − COMMAND_BACKSTOP` is `2100 − 1800 = 300`. That 300 s is the preserve, grade and cleanup tail the `DeadlinePhase` ladder needs, and it does not grow with the command budget — so the difference is kept, not the ratio. The launcher's per-cell wall-clock estimate is `cell_seconds = attempt_timeout` already (`launch_record.launch_cells(..., cell_seconds=attempt_timeout)`), so it follows the record with no further change. At the census's 3,000 s backstop the estimate is a 3,300 s cell.

12. **The `command_backstop_s` gate is `0 < command_backstop_s` and `command_backstop_s + 300 <= max_minutes * 60`.** The spec asks for "gated like the other fields"; the prompt's cap is `max_minutes * 60`. A bare `<=` cap is vacuous: with `command_backstop_s == max_minutes * 60` the derived 3,300 s cell never fits `max_seconds`, the launcher caps with zero cells finished, exits 4, and an `admit.sh`-shaped loop spins forever. Including the 300 s tail makes the cap mean "at least one cell can start".

13. **`tripped_verdict` and `tripped_patch_path` are one new attempt-record generation (`_V14_FIELDS`), dropped from the JSON when `tripped_verdict` is `None`.** `load_attempt_record` validates the exact field set against a list of generations; a field written unconditionally would invalidate every one of the 36 committed results' cells and every fixture. The `timeout`/`contract_digest`/`deadline` precedent in `write_attempt_record` is followed exactly.

14. **"Exploration turns before the first source mutation" uses the counterfactual's own source-edit rule, and is `null` when there is no mutation.** A mutation is a non-error `write`/`edit` whose worktree-relative path is inside the manifest's `source_paths` and is not a test file (basename `test_*.py` or `*_test.py`, or any parent component `tests`). The field is the number of `turn_start` events strictly before the turn holding that call. A cell that never mutates a source file records `null`, not its whole turn count: "explored for 40 turns, then edited" and "never edited" are different rows of the section 7 table, and a number would merge them.

15. **`self_stop` is recorded when the transcript carries an `agent_end` event, and holds the turns and output tokens counted up to and including it.** It is observable in the transcript, so `collect_evidence` stays pure and the number is recomputable from retained evidence alone; `pathology.py` already treats a missing `agent_end` as a cut-off cell, and every `BUDGET_EXCEEDED` and `COMMAND_TIMEOUT` cell lacks one. `null` means the harness stopped the cell.

16. **The offline fields of section 6 — pass-state turn and tokens, own-green turn, spend after the pass state — are not in `cell_evidence`.** They need the hidden suite and a replay, which is Task 8's work, not the launcher's; section 6 itself says they are offline. `cell_evidence` records only what one transcript plus one timeline can answer.

17. **`prompt_edits` is optional in a task spec, `validity` is a post-cut annotation, and `cut_task.py check` ignores it.** A required `prompt_edits` key would put an empty list in every already-cut task's manifest, moving every task tree's digest and forcing `agentclinic-repair-depth-2` and the floor tasks to be re-cut — which the Global Constraints forbid; Task 5 Step 7 proves the untouched tasks still re-cut byte-identically. `validity` cannot be an input to the cut either, because the check that produces it reads the cut prompt; making it one would force a cut → validate → re-cut cycle that moves three census tasks' trees for a field that describes them rather than defines them. So `check` compares every file but the manifest, plus the manifest with `validity` removed.

18. **`qualify`'s release-one candidate maps are left as they are; the census set is a new constant.** `CEILING_CANDIDATES`, `FLOOR_CANDIDATES` and `HELDOUT_TASKS` name what release one's spec ran and are cited as evidence of that campaign; rewriting `agentclinic-repair-depth-3`'s rung there would change the record of what was measured, not of what will be. `CENSUS_TASKS` is added beside them and is the only map this census reads.

---

## Global Constraints

- **Roles: Sonnet implements each task, Opus reviews it, Sonnet re-reviews the fix diff (scoped). No haiku. Fable only if the maintainer names it.** One fresh implementer per task; the controller blocks on every dispatch and nothing runs in the background.
- **No model inference during building, and no network.** No `launch`, no oMLX request, no GPU. Task 6's validity solver is a cloud model working from text and is the only agent that writes code from a prompt; it never touches the GPU.
- **Nothing under `/Users/Shared` is read or written; `~/satyrn-runs` is read-only; nothing is written to `/tmp` or `/private/tmp`.** Scratch work goes in the session scratchpad. Grade roots go under `$HOME/satyrn-census-grades/`.
- **Tests are verified in a scratch clone under the scratchpad, never in the main checkout.** `git clone --branch release-one <EVALS> "$SCRATCH/evals" && cd "$SCRATCH/evals" && uv sync`.
- **`just gates` exits 0 at the end of every task**, run in the evals tree, reading the exit code and never piping a gate. Known failing before any of this: 4 Xcode-license git integration rows (`/usr/bin/git` needs `sudo xcodebuild -license accept`); they are in the marked integration tier and are not part of `just gates`.
- **Every new file gets a `PROVENANCE.md` row** (`uv run python tools/provenance.py new <paths>`); `just gates` fails without one.
- **Docs caps:** `docs/superpowers/specs/*.md` ≤ 400 lines, `docs/results/*.md` ≤ 120 lines (none written), `ROADMAP.md` ≤ 150 lines. Plans are uncapped.
- **The default test tier uses no model, network or subprocess**; `tests/conftest.py`'s audit hook enforces it. Every refusal test has a sibling success test (BRIEF invariant 5). Every new rule is tested in both directions.
- **Grade from hook-written evidence, never stdout or exit status.** Count events from `tool_execution_start`, one per call; never `grep -c`.
- **Commit per task on evals `release-one` with explicit paths only.** Never `git add -A`, `git add .`, `git commit -a`, `--amend`, merge or push. A task whose gates are red is not committed. End every commit message with the session's attribution trailer.
- **Digests that must not move:** `agentclinic-repair-depth-2` and the floor tasks (`selfhost-guard-prefixes`, `selfhost-review-script`). They are not re-cut and do not run. `agentclinic-repair-depth-3`'s and `selfhost-run-record-gate`'s digests *do* move (Tasks 4 and 5) and are re-pinned by Task 9's records.
- **Census constants, verbatim from the spec:** per-turn cap 16,000 tokens; token budget 48,000; turn budget 72; backstop 3,000 s; k = 3; n = 6 per task; five tasks; Baseline arm only; `--purpose admission`; `--mode batch`; isolated; stop rule "established infrastructure failure only".
- **Evals checkout** `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` (`EVALS`); starting point `release-one` at `e27d4bc`. All commands run from `EVALS`.

---

## File structure

```
arms/baseline-ornith15-9b.json                  # T1: inference.max_tokens 32000 -> 16000            (modify)
arms/engine-ornith15-9b.json                    # T1: the same, both arms                            (modify)
src/satyrn_evals/cell_evidence.py               # T1: length_stops; T7: the section 6 fields         (modify)
src/satyrn_evals/workspace.py                   # T2: harvest at BUDGET_EXCEEDED teardown            (modify)
src/satyrn_evals/attempt.py                     # T2: grade the tripped patch into tripped_verdict   (modify)
src/satyrn_evals/attempt_record.py              # T2: the _V14 generation                            (modify)
src/satyrn_evals/run_record.py                  # T3: command_backstop_s field, gate, new_record     (modify)
src/satyrn_evals/launch_cell.py                 # T3: the constant becomes a default + margin        (modify)
src/satyrn_evals/launch_record.py               # T3: timeout and attempt_timeout from the record    (modify)
src/satyrn_evals/cli.py                         # T3: --command-backstop; launch flag overrides      (modify)
src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json   # T4: the R2 rung                  (modify)
src/satyrn_evals/qualify.py                     # T4: rung map; T5: judge_prompt_edits               (modify)
tools/cut_task.py                               # T5: prompt_edits after the cut, into the manifest  (modify)
tools/task_specs/selfhost-run-record-gate.json  # T5: the two prompt edits                           (modify)
src/satyrn_evals/tasks/selfhost-run-record-gate/                  # T5: re-cut                       (replace)
src/satyrn_evals/tasks/*/manifest.json          # T6: the validity block, five tasks                 (modify)
src/satyrn_evals/manifest.py                    # T6: load and validate validity                     (modify)
docs/superpowers/specs/2026-09-15-release-two-task-validity.md    # T6: the procedure, <= 400 lines  (create)
src/satyrn_evals/rescore.py                     # T7: pass source_paths into collect_evidence        (modify)
src/satyrn_evals/census_classify.py             # T8: the pure rules                                 (create)
evidence/2026-09-16-census/classify.py           # T8: the night driver                              (create)
evidence/2026-09-16-census/.gitignore            # T8: work/                                          (create)
tests/test_cell_evidence.py                     # T1, T7: fixtures                                    (modify)
tests/test_budget.py                            # T1: the tripwire under a length stop                (modify)
tests/test_workspace_tripped_harvest.py         # T2                                                  (create)
tests/test_attempt_tripped_verdict.py           # T2                                                  (create)
tests/test_run_record.py                        # T3                                                  (modify)
tests/test_record_new.py                        # T3                                                  (modify)
tests/test_launch_record.py                     # T3                                                  (modify)
tests/test_agentclinic_manifests.py             # T4                                                  (modify)
tests/test_cut_task.py                          # T5                                                  (modify)
tests/test_qualify.py                           # T5                                                  (modify)
tests/test_manifest.py                          # T6                                                  (modify)
tests/test_census_classify.py                   # T8                                                  (create)
records/2026-09-16-census-<task>.json            # T9, five records                                    (create)
scripts/census_night.sh                          # T9: the launch script                               (create)
PROVENANCE.md                                    # every task                                          (modify)
ROADMAP.md                                       # T9: the R0 row                                      (modify)
```

Names later tasks rely on:

| name | kind | task |
|---|---|---|
| `CellEvidence.length_stops: int` | field | T1 |
| `AttemptRecord.tripped_verdict: Verdict | None`, `.tripped_patch_path: str | None` | fields | T2 |
| `workspace.TRIPPED_PATCH_NAME = "tripped.diff"`; `run_prepared_command(..., tripped_patch: Path | None = None)` | constant, parameter | T2 |
| `RunRecord.command_backstop_s: int`; `run_record.DEADLINE_MARGIN_S = 300`; `attempt_deadline_s(record) -> float` | field, constant, function | T3 |
| `qualify.CENSUS_TASKS: dict[str, str]` | constant | T4 |
| `cut_task.PromptEdit(old, new, reason)`; `apply_prompt_edits(prompt, edits) -> str` | dataclass, function | T5 |
| `qualify.judge_prompt_edits(manifest_body) -> Check` | function | T5 |
| `manifest.TaskManifest.validity: dict | None` | field | T6 |
| `CellEvidence.tool_span_seconds`, `.exploration_turns`, `.biggest_turn`, `.self_stop` | fields | T7 |
| `census_classify.TurnRow`, `per_turn`, `CLASSES`, `class_flags`, `evidence_row` | module API | T8 |

---

### Task 1: The per-turn output cap, and `length_stops` in the evidence block

Design section 3.1. Both arm files drop `inference.max_tokens` from 32,000 to 16,000, and every cell records how many assistant messages the cap cut.

**Files:**
- Modify: `arms/baseline-ornith15-9b.json`, `arms/engine-ornith15-9b.json`
- Modify: `src/satyrn_evals/cell_evidence.py`
- Test: `tests/test_cell_evidence.py`, `tests/test_budget.py`

**Interfaces:**
- Produces: `CellEvidence.length_stops: int`, in `to_block()` under the key `length_stops`. Task 8 reads it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cell_evidence.py`, after the existing helpers (`_line`, `_bash`, `_transcript`, `CWD`):

```python
def _assistant(output: int, *, stop: str | None = None, content: list[dict] | None = None) -> str:
    """One assistant `message_end`, optionally with the stop reason Pi recorded."""
    message: dict = {"role": "assistant", "usage": {"output": output}, "content": content or []}
    if stop is not None:
        message["stopReason"] = stop
    return _line({"type": "message_end", "message": message})


def test_a_length_cut_turn_that_carries_tool_calls_is_counted_and_the_cell_continues() -> None:
    """Design section 3.1: the cap fails that turn's tool calls and the loop goes on.
    The harness must count the cut and keep reading, not void the cell."""
    text = _transcript(
        _assistant(16000, stop="length", content=[{"type": "toolCall", "arguments": {"path": "app.py"}}]),
        *_bash("b1", "uv run python -m pytest tests/ -q"),
        _line({"type": "turn_start"}),
        _assistant(900, stop="end_turn"),
        *_bash("b2", "git status"),
    )
    block = collect_evidence(text).to_block()
    assert block["length_stops"] == 1
    assert (block["turns"], block["output_tokens"]) == (2, 16900)
    assert (block["tool_calls"], block["bash_test_runs"]) == (2, 1)


def test_a_length_cut_turn_with_no_tool_call_is_counted_the_same_way() -> None:
    text = _transcript(_assistant(16000, stop="length"))
    block = collect_evidence(text).to_block()
    assert (block["length_stops"], block["turns"], block["output_tokens"]) == (1, 1, 16000)


def test_a_turn_that_ended_on_its_own_is_not_a_length_stop() -> None:
    text = _transcript(_assistant(5000, stop="end_turn"), *_bash("b1", "ls"))
    assert collect_evidence(text).to_block()["length_stops"] == 0


def test_an_assistant_message_with_no_stop_reason_is_not_a_length_stop() -> None:
    assert collect_evidence(_transcript(_assistant(5000))).to_block()["length_stops"] == 0


def test_a_turn_end_carrying_the_same_stop_reason_does_not_add_to_the_count() -> None:
    """Ruling 1: `turn_end` also carries `stopReason` (`turn_ledger._classify`).
    Counting both families would report 2 where the model was cut once."""
    text = _transcript(
        _assistant(16000, stop="length"),
        _line({"type": "turn_end", "message": {"role": "assistant", "stopReason": "length"}}),
    )
    assert collect_evidence(text).to_block()["length_stops"] == 1


def test_a_non_assistant_message_end_is_never_a_length_stop() -> None:
    text = _transcript(
        _line({"type": "message_end", "message": {"role": "user", "stopReason": "length", "usage": {"output": 10}}})
    )
    assert collect_evidence(text).to_block()["length_stops"] == 0


def test_two_length_cuts_inside_one_turn_count_twice() -> None:
    """A turn whose tool calls were failed and retried can be cut more than once;
    a per-turn boolean would report 1 (Ruling 1)."""
    text = _transcript(_assistant(16000, stop="length"), _assistant(16000, stop="length"))
    block = collect_evidence(text).to_block()
    assert (block["length_stops"], block["turns"], block["output_tokens"]) == (2, 1, 32000)
```

Append to `tests/test_budget.py` (it already imports `json`, `AttemptBudget` and `BudgetTripwire`; add whichever of those is missing):

```python
def test_a_length_cut_assistant_message_still_counts_its_output_tokens() -> None:
    """Design section 3.1: the tripwire still sums `usage.output` under the cap."""
    wire = BudgetTripwire(AttemptBudget(output_tokens=16000, turns=72))
    cut = json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "length", "usage": {"output": 16000}}})
    assert not wire.feed(cut)
    assert wire.usage.output_tokens == 16000
    assert wire.feed(json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "length", "usage": {"output": 1}}}))
    assert wire.over == "output_tokens"


def test_an_ordinary_turn_under_the_cap_does_not_trip() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=16000, turns=72))
    assert not wire.feed(json.dumps({"type": "message_end", "message": {"role": "assistant", "stopReason": "end_turn", "usage": {"output": 5999}}}))
    assert wire.over is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cell_evidence.py tests/test_budget.py -q`
Expected: FAIL. The `cell_evidence` tests fail with `KeyError: 'length_stops'`; the two `test_budget.py` tests pass already (they assert behaviour the tripwire has, and are here as the cap's regression floor).

- [ ] **Step 3: Implement**

In `src/satyrn_evals/cell_evidence.py`:

1. Add to the module docstring's rule list, after the "first passing self-test" bullet:

```
- a **length stop** is one assistant ``message_end`` whose ``stopReason`` is
  ``"length"``: the per-turn output cap cut that message. It is counted on the
  same events the budget counter sums ``usage.output`` from, so the two can
  never disagree about which messages were the model's; ``turn_end`` carries
  the same field and is not counted.
```

2. Add the field to `CellEvidence`, after `bash_test_runs`:

```python
    length_stops: int = 0
```

and to `to_block()`, after `"bash_test_runs"`:

```python
            "length_stops": self.length_stops,
```

3. Add the predicate beside `_passing_route`:

```python
def _length_stop(event: dict) -> bool:
    """One assistant ``message_end`` cut at the per-turn output cap (module docstring)."""
    if event.get("type") != "message_end":
        return False
    message = event.get("message")
    return (
        isinstance(message, dict)
        and message.get("role") == "assistant"
        and message.get("stopReason") == "length"
    )
```

4. In `collect_evidence`, pass it to the constructor, after `bash_test_runs=...`:

```python
        length_stops=sum(1 for event in events if _length_stop(event)),
```

5. In both `arms/baseline-ornith15-9b.json` and `arms/engine-ornith15-9b.json`, change `"max_tokens": 32000` to `"max_tokens": 16000`. Change nothing else in either file: `context_window`, `compaction_reserve_tokens`, sampling and pins stay as they are.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_cell_evidence.py tests/test_budget.py -q`
Expected: PASS, no failures.

Run: `uv run python -c "import json;print([json.load(open(p))['inference']['max_tokens'] for p in ('arms/baseline-ornith15-9b.json','arms/engine-ornith15-9b.json')])"`
Expected: `[16000, 16000]`.

- [ ] **Step 5: Gates and commit**

```bash
just gates; echo "gates=$?"
git add arms/baseline-ornith15-9b.json arms/engine-ornith15-9b.json src/satyrn_evals/cell_evidence.py tests/test_cell_evidence.py tests/test_budget.py
git commit -m "Census harness 1: a 16,000-token per-turn output cap on both arms, and length stops in the evidence block"
```

Expected: `gates=0` before the commit.

**Operator note, not part of this task.** The cap is only enforced where the server applies it. Before any record launches, the maintainer changes `maxTokens` to 16000 in the cell user's Pi `models.json` and `max_tokens` to 16000 in the `Ornith-1.5-9B-MLX-8bit` entry of `~/.omlx/model_settings.json`, restarts oMLX, and confirms `scripts/preflight_settings.py --cell` exits 0 for both arms. The exact commands are in "Operator commands" at the end. `launch` re-runs the settings check itself and refuses on a disagreement, so a forgotten restart stops the night rather than silently measuring the old cap.

---

### Task 2: Grade the tripped worktree into `tripped_verdict`

Design section 3.2. At `BUDGET_EXCEEDED` teardown the worktree's cumulative diff against `workspace_base_sha` is harvested; the attempt then grades it exactly as it grades a delivered patch, into a declared secondary that is never a pass.

**Files:**
- Modify: `src/satyrn_evals/workspace.py` (the `elif tripped is not None:` branch of `_run_command`, and `run_prepared_command`)
- Modify: `src/satyrn_evals/attempt.py` (`_attempt`'s `run_prepared_command` call, `_finish_attempt`)
- Modify: `src/satyrn_evals/attempt_record.py` (the `_V14` generation)
- Test: `tests/test_workspace_tripped_harvest.py` (create), `tests/test_attempt_tripped_verdict.py` (create)

**Interfaces:**
- Consumes: `satyrn_evals.session_patch.build_cumulative_patch`, `RESIDUE_EXCLUDES`; `satyrn_evals.grade.grade`.
- Produces: `workspace.TRIPPED_PATCH_NAME = "tripped.diff"`, `attempt.TRIPPED_RECEIPT_NAME = "tripped-receipt.json"`; `run_prepared_command(..., tripped_patch: Path | None = None)`; `AttemptRecord.tripped_verdict: Verdict | None` and `.tripped_patch_path: str | None`. Task 8 reads `tripped_verdict` off `attempt.json`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workspace_tripped_harvest.py`:

```python
"""The BUDGET_EXCEEDED teardown harvests the worktree it is about to release.

Pure but for git: marked `integration`, because a cumulative patch needs a real
repository. The both-directions pair is a tripped tree with changes and a
tripped tree with none.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.budget import AttemptBudget
from satyrn_evals.workspace import TRIPPED_PATCH_NAME, WorkspaceCode, prepare_workspace, release_workspace, run_prepared_command

pytestmark = pytest.mark.integration

OVER = json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"output": 99}}})


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    (base / "src").mkdir(parents=True)
    (base / "src" / "app.py").write_text("value = 1\n")
    return base


def _command(script: str) -> list[str]:
    return ["/bin/sh", "-c", script]


def _trip(tmp_path: Path, script: str) -> tuple[WorkspaceCode, str]:
    workspace = prepare_workspace(base=_base(tmp_path), parent=tmp_path / "work")
    out = tmp_path / TRIPPED_PATCH_NAME
    try:
        result = run_prepared_command(
            workspace,
            command=_command(script),
            timeout=60.0,
            transcript=tmp_path / "t.jsonl",
            budget=AttemptBudget(output_tokens=1, turns=48),
            tripped_patch=out,
        )
    finally:
        release_workspace(workspace)
    return result.code, (out.read_text() if out.is_file() else "")


def test_a_tripped_worktree_with_changes_is_harvested(tmp_path: Path) -> None:
    code, patch = _trip(
        tmp_path,
        f"printf 'value = 2\\n' > src/app.py; printf '%s\\n' '{OVER}' >> \"$SATYRN_TRANSCRIPT\"; sleep 30",
    )
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert "src/app.py" in patch and "+value = 2" in patch


def test_a_tripped_worktree_with_no_change_writes_no_patch(tmp_path: Path) -> None:
    code, patch = _trip(tmp_path, f"printf '%s\\n' '{OVER}' >> \"$SATYRN_TRANSCRIPT\"; sleep 30")
    assert code is WorkspaceCode.BUDGET_EXCEEDED
    assert patch == ""
```

Create `tests/test_attempt_tripped_verdict.py`:

```python
"""`tripped_verdict` on a BUDGET_EXCEEDED record: the declared secondary.

Default tier: `_grade_tripped` is called directly with a fake grader, and the
record shapes are built by hand. Design section 3.2's two fixtures are the two
directions -- a tripped worktree holding a passing state, and one with no patch.
"""

from pathlib import Path

import pytest

from satyrn_evals.attempt import TRIPPED_RECEIPT_NAME, _grade_tripped
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord, load_attempt_record, write_attempt_record
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict

SHA = "0" * 40
DIGEST = "1" * 64


def _record(**overrides: object) -> AttemptRecord:
    fields: dict = dict(
        version=1, outcome=AttemptOutcome.REFUSED, code=AttemptCode.BUDGET_EXCEEDED,
        message="attempt command spent 48001 output tokens, over the budget of 48000",
        task="t", command=("pi",), command_exit=None, patch_path=None, transcript_path="transcript.txt",
        patch_digest=None, transcript_digest=DIGEST, verdict=None, receipt_path=None, timeout=3000.0,
        rung="R1", contract_digest=DIGEST, workspace_base_sha=SHA, attempt_dir="t-1",
    )
    return AttemptRecord(**(fields | overrides))


def test_a_tripped_worktree_holding_a_passing_state_grades_pass_with_verdict_still_null(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    patch = tmp_path / "tripped.diff"
    patch.write_text("diff --git a/src/app.py b/src/app.py\n")
    monkeypatch.setattr(
        "satyrn_evals.attempt.grade",
        lambda task_dir, patch_path, receipt_path, **kw: Receipt("t", DIGEST, Verdict.PASS, "ok", None),
    )
    verdict, name = _grade_tripped(tmp_path, tmp_path, patch, deadline=None)
    assert (verdict, name) == (Verdict.PASS, "tripped.diff")
    record = _record(tripped_verdict=verdict, tripped_patch_path=name)
    assert record.verdict is None
    write_attempt_record(tmp_path / "attempt.json", record)
    assert load_attempt_record(tmp_path / "attempt.json").tripped_verdict is Verdict.PASS


def test_a_tripped_worktree_with_no_patch_grades_unavailable(tmp_path: Path) -> None:
    verdict, name = _grade_tripped(tmp_path, tmp_path, tmp_path / "absent.diff", deadline=None)
    assert (verdict, name) == (Verdict.UNAVAILABLE, None)


def test_an_empty_tripped_patch_grades_unavailable(tmp_path: Path) -> None:
    patch = tmp_path / "tripped.diff"
    patch.write_text("   \n")
    assert _grade_tripped(tmp_path, tmp_path, patch, deadline=None) == (Verdict.UNAVAILABLE, None)


def test_a_grader_failure_is_unavailable_and_keeps_the_patch_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from satyrn_evals.errors import SatyrnError

    patch = tmp_path / "tripped.diff"
    patch.write_text("diff --git a/x b/x\n")

    def boom(*args: object, **kwargs: object) -> Receipt:
        raise SatyrnError("oracle exploded")

    monkeypatch.setattr("satyrn_evals.attempt.grade", boom)
    assert _grade_tripped(tmp_path, tmp_path, patch, deadline=None) == (Verdict.UNAVAILABLE, "tripped.diff")


def test_a_record_that_is_not_budget_exceeded_may_not_carry_a_tripped_verdict() -> None:
    with pytest.raises(ValueError, match="tripped_verdict"):
        _record(code=AttemptCode.COMMAND_TIMEOUT, tripped_verdict=Verdict.PASS, tripped_patch_path="tripped.diff")


def test_a_record_without_a_tripped_verdict_writes_the_older_field_set(tmp_path: Path) -> None:
    """Ruling 13: every committed result's cells must keep loading."""
    import json

    write_attempt_record(tmp_path / "attempt.json", _record())
    body = json.loads((tmp_path / "attempt.json").read_text())
    assert "tripped_verdict" not in body and "tripped_patch_path" not in body
    assert load_attempt_record(tmp_path / "attempt.json").tripped_verdict is None


def test_the_receipt_name_is_not_the_delivered_one() -> None:
    assert TRIPPED_RECEIPT_NAME == "tripped-receipt.json"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_attempt_tripped_verdict.py -q`
Expected: FAIL with `ImportError: cannot import name 'TRIPPED_RECEIPT_NAME'`.

Run: `uv run pytest -m integration tests/test_workspace_tripped_harvest.py -q`
Expected: FAIL with `ImportError: cannot import name 'TRIPPED_PATCH_NAME'`.

- [ ] **Step 3: Implement the harvest in `workspace.py`**

Add the constant beside `DEFAULT_TEARDOWN_GRACE`:

```python
#: Where a BUDGET_EXCEEDED teardown leaves the worktree's cumulative diff
#: (design section 3.2). Written beside the attempt's own artifacts.
TRIPPED_PATCH_NAME = "tripped.diff"
```

Add the harvester above `_run_command`:

```python
def _harvest_tripped(
    state: _WorkspaceState, environment: Mapping[str, str], destination: Path
) -> None:
    """Write the worktree's cumulative diff against ``base_sha`` to ``destination``.

    Preserve before judging (BRIEF invariant 1). This runs at the teardown, not
    in ``_finish_attempt``, because a whole-attempt deadline can expire in
    preservation or cleanup and return without ever reaching the finalizer --
    the tripped evidence must already be on disk by then, so a later regrade
    can read it. Any failure is swallowed: a missing tripped patch is a missing
    secondary, never a lost cell, and the primary outcome must not change
    because a secondary could not be taken.
    """
    # Imported here, not at module scope: `session_patch` imports
    # `GIT_SAFETY_CONFIG` from this module, so a top-level import is a cycle.
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch

    if state.base_sha is None:
        return
    try:
        capture = build_cumulative_patch(
            state.worktree, state.base_sha, environment, exclude=RESIDUE_EXCLUDES
        )
        if capture.patch_text.strip():
            destination.write_text(capture.patch_text, encoding="utf-8")
    except (OSError, subprocess.SubprocessError, ValueError):
        return
```

In `_run_command`, add the keyword-only parameter `tripped_patch: Path | None = None` to the signature (after `timeline`), and in the `elif tripped is not None:` branch, immediately **before** the `try: safe, detail = _teardown(...)` call, insert:

```python
                    if isinstance(tripped, BudgetTripwire) and tripped_patch is not None:
                        _harvest_tripped(state, environment, tripped_patch)
```

Harvest before the teardown, not after: the model's process is already past its budget and nothing it writes after this point is inside the budget, and a teardown that ends `CLEANUP_FAILED` must not cost the secondary.

In `run_prepared_command`, add `tripped_patch: Path | None = None` to the signature (after `timeline`) and pass it through to `_run_command`.

- [ ] **Step 4: Implement the grade in `attempt.py`**

Add beside `TIMELINE_NAME`'s import block:

```python
from satyrn_evals.workspace import TRIPPED_PATCH_NAME  # with the other workspace imports

#: The receipt the tripped secondary writes. Never `receipt.json`: that name is
#: the delivered patch's, and `regrade` reads it as the cell's own verdict.
TRIPPED_RECEIPT_NAME = "tripped-receipt.json"
```

In `_attempt`, pass the destination to the command (the call that already passes `timeline=attempt_dir / TIMELINE_NAME`):

```python
                        timeline=attempt_dir / TIMELINE_NAME,
                        tripped_patch=attempt_dir / TRIPPED_PATCH_NAME,
```

Add the grader beside `_workspace_refusal`:

```python
def _grade_tripped(
    task_dir: Path,
    attempt_dir: Path,
    patch_path: Path,
    *,
    deadline: AttemptDeadline | None,
) -> tuple[Verdict, str | None]:
    """The declared secondary (design section 3.2): what the torn-down worktree grades.

    The same `grade` call the delivered patch takes, against the same task
    directory and manifest, so the allowlist, `ignored_paths` and the hidden
    suite bite identically -- a different path would answer a different
    question. It is never a pass in the record's own sense: `verdict` stays
    null and the attempt stays REFUSED (Ruling 2). A missing or empty tripped
    patch is `unavailable`, exactly as the grader answers an empty delivered
    patch, and so is a grader failure -- but the patch name is still recorded
    then, because the evidence exists and can be regraded.
    """
    if not patch_path.is_file():
        return Verdict.UNAVAILABLE, None
    try:
        text = patch_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return Verdict.UNAVAILABLE, TRIPPED_PATCH_NAME
    if not text.strip():
        return Verdict.UNAVAILABLE, None
    receipt_path = attempt_dir / TRIPPED_RECEIPT_NAME
    try:
        receipt = (
            grade(task_dir, patch_path, receipt_path, deadline=deadline)
            if deadline is not None
            else grade(task_dir, patch_path, receipt_path)
        )
    except SatyrnError:
        return Verdict.UNAVAILABLE, TRIPPED_PATCH_NAME
    return receipt.verdict, TRIPPED_PATCH_NAME
```

In `_finish_attempt`, inside the `if code is not None:` branch, after `deadline.remaining(DeadlinePhase.PRESERVATION)` and before `message = (...)`, insert:

```python
        tripped_verdict: Verdict | None = None
        tripped_name: str | None = None
        if code is AttemptCode.BUDGET_EXCEEDED:
            tripped_verdict, tripped_name = _grade_tripped(
                task_dir, attempt_dir, attempt_dir / TRIPPED_PATCH_NAME, deadline=deadline
            )
```

and add to that branch's `AttemptRecord(...)` construction, after `attempt_timeout=...`:

```python
            tripped_verdict=tripped_verdict,
            tripped_patch_path=tripped_name,
```

`AttemptDeadlineExceeded` from the tripped grade is not caught: it propagates exactly as the existing `deadline.remaining(DeadlinePhase.PRESERVATION)` above it does, and `_attempt`'s caller turns it into `_retain_expired_record`. A tripped secondary must never be the reason a cell's record is lost.

- [ ] **Step 5: Implement the record generation in `attempt_record.py`**

Beside `_V13_FIELDS`:

```python
# V14 records add the tripped-worktree secondary (design section 3.2). Written
# only on a BUDGET_EXCEEDED record that has one, so every earlier record's
# field set -- and every committed result's cells -- still loads (Ruling 13).
_V14_FIELDS = frozenset({"tripped_verdict", "tripped_patch_path"})
```

Add to `AttemptRecord`, after `attempt_timeout: float | None = None` and before `_legacy`:

```python
    tripped_verdict: Verdict | None = None
    tripped_patch_path: str | None = None
```

In `__post_init__`, after the `verdict` coercion, add:

```python
        if self.tripped_verdict is not None:
            object.__setattr__(self, "tripped_verdict", Verdict(self.tripped_verdict))
```

and, after the `policy.verdict` checks, add:

```python
        if self.tripped_verdict is not None and self.code is not AttemptCode.BUDGET_EXCEEDED:
            raise ValueError(f"{self.code} cannot carry a tripped_verdict")
        if self.tripped_patch_path is not None:
            if self.tripped_verdict is None:
                raise ValueError("attempt record tripped_patch_path requires a tripped_verdict")
            if not _nonempty_text(self.tripped_patch_path):
                raise ValueError("attempt record tripped_patch_path must be non-empty or null")
```

In `write_attempt_record`, beside the other generational drops:

```python
    if data.get("tripped_verdict") is None:
        for name in _V14_FIELDS:
            data.pop(name, None)
```

In `load_attempt_record`, after `v13_fields = ...`:

```python
    v14_fields = v13_fields | _V14_FIELDS
```

add `v14_fields` to the accepted `fields not in {...}` set, change the `unexpected := fields - v13_fields` guard to `fields - v14_fields`, and pass to the constructor:

```python
            tripped_verdict=Verdict(data["tripped_verdict"]) if data.get("tripped_verdict") is not None else None,
            tripped_patch_path=data.get("tripped_patch_path"),
```

A V14 record may also omit `tripped_patch_path` when the verdict is `unavailable` with no patch; accept the `v13_fields | {"tripped_verdict"}` set too, since `asdict` writes both or neither — verify with `test_a_tripped_worktree_with_no_patch_grades_unavailable`'s record round-trip and, if the set differs, extend the accepted sets rather than making the writer emit a null field.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_attempt_tripped_verdict.py tests/test_attempt.py tests/test_attempt_record.py tests/test_rescore.py -q`
Expected: PASS.

Run: `uv run pytest -m integration tests/test_workspace_tripped_harvest.py -q`
Expected: PASS, 2 tests.

- [ ] **Step 7: Provenance, gates and commit**

```bash
uv run python tools/provenance.py new tests/test_workspace_tripped_harvest.py tests/test_attempt_tripped_verdict.py
just gates; echo "gates=$?"
git add src/satyrn_evals/workspace.py src/satyrn_evals/attempt.py src/satyrn_evals/attempt_record.py tests/test_workspace_tripped_harvest.py tests/test_attempt_tripped_verdict.py PROVENANCE.md
git commit -m "Census harness 2: harvest and grade the tripped worktree into tripped_verdict, a secondary that is never a pass"
```

Expected: `gates=0` before the commit.

---

### Task 3: `command_backstop_s` as a run-record field

Design section 3.3. The wall-clock backstop stops being a module constant and becomes a gated record field, default 1800; the census records 3,000. The launcher's per-cell estimate follows it.

**Files:**
- Modify: `src/satyrn_evals/run_record.py`, `src/satyrn_evals/launch_cell.py`, `src/satyrn_evals/launch_record.py`, `src/satyrn_evals/cli.py`
- Test: `tests/test_run_record.py`, `tests/test_record_new.py`, `tests/test_launch_record.py`

**Interfaces:**
- Produces: `run_record.DEFAULT_COMMAND_BACKSTOP_S = 1800`, `run_record.DEADLINE_MARGIN_S = 300`, `RunRecord.command_backstop_s: int`, `run_record.attempt_deadline_s(record) -> float`, `record new --command-backstop N`. Task 9 writes records with `--command-backstop 3000`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_run_record.py` (it already defines a `BODY`-shaped dict at line 29 and a helper that writes and loads it; reuse whatever that file calls them — below they are `BODY` and `_write`):

```python
def test_a_record_without_the_field_keeps_the_default_backstop(tmp_path: Path) -> None:
    """Every committed record predates the field and must still load."""
    record = _write(tmp_path, BODY)
    assert record.command_backstop_s == DEFAULT_COMMAND_BACKSTOP_S == 1800
    assert attempt_deadline_s(record) == 2100.0


def test_a_recorded_backstop_is_read_and_carries_the_deadline_margin(tmp_path: Path) -> None:
    record = _write(tmp_path, BODY | {"command_backstop_s": 3000, "max_minutes": 240, "mode": "batch", "n": 6})
    assert record.command_backstop_s == 3000
    assert attempt_deadline_s(record) == 3300.0


@pytest.mark.parametrize("value", [0, -1, 1800.0, True, "1800"])
def test_a_backstop_that_is_not_a_positive_integer_is_refused(tmp_path: Path, value: object) -> None:
    with pytest.raises(RunRecordError, match="command_backstop_s"):
        _write(tmp_path, BODY | {"command_backstop_s": value})


def test_a_backstop_that_leaves_no_room_for_one_cell_is_gated(tmp_path: Path) -> None:
    """Ruling 12: `max_minutes * 60` alone is vacuous -- the derived 300 s tail
    must fit too, or the launcher caps with zero cells and the script loops."""
    record = _write(tmp_path, BODY | {"command_backstop_s": 3600, "max_minutes": 60})
    with pytest.raises(RunRecordError, match="leaves no room"):
        gate(record, previous_result_committed=None)


def test_a_backstop_that_fits_passes_the_gate(tmp_path: Path) -> None:
    record = _write(tmp_path, BODY | {"command_backstop_s": 3000, "max_minutes": 240, "mode": "batch", "n": 6})
    gate(record, previous_result_committed=None)
```

Append to `tests/test_record_new.py`:

```python
def test_record_new_defaults_the_backstop_and_writes_it(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    assert load_run_record(tmp_path / "records" / "depth-3.json").command_backstop_s == 1800


def test_record_new_takes_a_backstop(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--command-backstop", "3000", "--mode", "batch", "--max-minutes", "240")) == 0
    assert load_run_record(tmp_path / "records" / "depth-3.json").command_backstop_s == 3000


def test_record_new_refuses_a_backstop_that_does_not_fit_the_wall_clock(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="leaves no room"):
        main(_new(tmp_path, "--command-backstop", "3600", "--max-minutes", "60"))
    assert not (tmp_path / "records" / "depth-3.json").exists()
```

Append to `tests/test_launch_record.py` (reusing its existing record-writing helper and `FakeFacts`):

```python
def test_the_cell_spec_takes_its_timeouts_from_the_record(tmp_path: Path) -> None:
    _record(tmp_path, command_backstop_s=3000, max_minutes=240, mode="batch", n=6)
    launch_record(tmp_path / "records" / "depth-3.json", [ARM], tasks_root=TASKS, runs_root=tmp_path / "runs", facts=FakeFacts())
    spec = json.loads((tmp_path / "runs" / "depth-3" / SLOTS_DIR / "00.spec.json").read_text())
    assert (spec["timeout"], spec["attempt_timeout"]) == (3000.0, 3300.0)


def test_a_deciding_record_refuses_a_timeout_override(tmp_path: Path) -> None:
    _record(tmp_path, command_backstop_s=3000, max_minutes=240, mode="batch", n=6, purpose="admission")
    with pytest.raises(RunRecordError, match="--timeout"):
        launch_record(tmp_path / "records" / "depth-3.json", [ARM], tasks_root=TASKS, runs_root=tmp_path / "runs", timeout=1800.0, facts=FakeFacts())


def test_a_development_record_may_override_the_timeout(tmp_path: Path) -> None:
    _record(tmp_path, purpose="development", isolation="local")
    launch_record(tmp_path / "records" / "depth-3.json", [ARM], tasks_root=TASKS, runs_root=tmp_path / "runs", timeout=60.0, attempt_timeout=90.0, facts=FakeFacts())
    spec = json.loads((tmp_path / "runs" / "depth-3" / SLOTS_DIR / "00.spec.json").read_text())
    assert (spec["timeout"], spec["attempt_timeout"]) == (60.0, 90.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_run_record.py tests/test_record_new.py tests/test_launch_record.py -q`
Expected: FAIL with `ImportError: cannot import name 'DEFAULT_COMMAND_BACKSTOP_S'`.

- [ ] **Step 3: Implement in `run_record.py`**

Beside `CAPS`:

```python
#: The per-attempt-command wall-clock backstop, seconds. A record field since
#: the 2026-09-16 census (design section 3.3); 1800 is the value every record
#: written before it ran under, so it is the default an older record loads with.
DEFAULT_COMMAND_BACKSTOP_S = 1800
#: What the whole-attempt deadline adds on top of the command backstop: the
#: preserve, grade and cleanup tail the DeadlinePhase ladder needs. It does not
#: grow with the command budget, so the difference is kept, not the ratio
#: (2100 - 1800 at the release-one setting).
DEADLINE_MARGIN_S = 300
```

Add to `RunRecord`, beside `k`:

```python
    command_backstop_s: int = DEFAULT_COMMAND_BACKSTOP_S
```

Add to `_OPTIONAL`: `"command_backstop_s": int,`.

In `load_run_record`, after the `k` check:

```python
    backstop = body.get("command_backstop_s", DEFAULT_COMMAND_BACKSTOP_S)
    if backstop < 1:
        raise RunRecordError(f"run record {path}: command_backstop_s must be a positive integer")
```

(The `_OPTIONAL` type loop above already rejects a float, a bool and a string.)

Add the derivation beside `attempt_budget`:

```python
def attempt_deadline_s(record: RunRecord) -> float:
    """The whole-attempt deadline this record's backstop implies (Ruling 11)."""
    return float(record.command_backstop_s + DEADLINE_MARGIN_S)
```

In `gate`, after the `CAPS` check:

```python
    if record.command_backstop_s + DEADLINE_MARGIN_S > record.max_minutes * 60:
        raise RunRecordError(
            f"a {record.command_backstop_s} s backstop plus the {DEADLINE_MARGIN_S} s deadline margin "
            f"leaves no room for one cell in {record.max_minutes} minutes"
        )
```

In `new_record`, add the keyword `command_backstop_s: int = DEFAULT_COMMAND_BACKSTOP_S` and write `"command_backstop_s": command_backstop_s,` into the body beside `"k": k`.

- [ ] **Step 4: Implement in `launch_cell.py`, `launch_record.py` and `cli.py`**

`launch_cell.py`: delete the two constants and their comment, and re-export the defaults so existing importers keep working:

```python
from satyrn_evals.run_record import DEADLINE_MARGIN_S, DEFAULT_COMMAND_BACKSTOP_S

#: Defaults only. The value a cell actually runs under is the record's
#: `command_backstop_s` (design section 3.3); these name what a record that
#: does not say gets.
COMMAND_BACKSTOP = float(DEFAULT_COMMAND_BACKSTOP_S)
ATTEMPT_DEADLINE = float(DEFAULT_COMMAND_BACKSTOP_S + DEADLINE_MARGIN_S)
```

`launch_record.py`:
- import `attempt_deadline_s` from `run_record`;
- change the signature to `timeout: float | None = None, attempt_timeout: float | None = None`;
- after `record = load_run_record(record_path)` add:

```python
    # The record is the source; a flag is an override, and an override is a
    # seam a deciding record refuses (below), exactly as --no-hunt is.
    backstop = float(record.command_backstop_s) if timeout is None else timeout
    deadline_s = attempt_deadline_s(record) if attempt_timeout is None else attempt_timeout
```

- change the two seam rows to `(f"--timeout {backstop:g}", timeout is not None)` and `(f"--attempt-timeout {deadline_s:g}", attempt_timeout is not None)`;
- in `spawn`, use `"timeout": backstop, "attempt_timeout": deadline_s`;
- in the `launch_cells(...)` call, `cell_seconds=deadline_s`. Nothing else changes: the capped-night message already reads `f"...another {cell_seconds:g} s cell..."`, so at the census setting it prints `3300 s cell`.

`cli.py`:
- `launch_p.add_argument("--timeout", type=positive_finite_timeout, default=None, help="override the record's command_backstop_s, seconds (development records only)")`, and the same shape for `--attempt-timeout`;
- add `record_new_p.add_argument("--command-backstop", type=positive_int, default=DEFAULT_COMMAND_BACKSTOP_S, help="per-attempt-command wall-clock backstop, seconds")`, importing `DEFAULT_COMMAND_BACKSTOP_S` from `run_record`;
- `_record_new` passes `command_backstop_s=args.command_backstop`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_run_record.py tests/test_record_new.py tests/test_launch_record.py tests/test_cli.py tests/test_cell_preflight.py -q`
Expected: PASS.

Run: `uv run satyrn-evals launch --check records/2026-09-15-admission-selfhost-docs-linter.json; echo "EXIT: $?"`
Expected: `EXIT: 0` — a committed record written before the field still loads and gates.

- [ ] **Step 6: Gates and commit**

```bash
just gates; echo "gates=$?"
git add src/satyrn_evals/run_record.py src/satyrn_evals/launch_cell.py src/satyrn_evals/launch_record.py src/satyrn_evals/cli.py tests/test_run_record.py tests/test_record_new.py tests/test_launch_record.py
git commit -m "Census harness 3: the wall-clock backstop becomes a gated run-record field, with the attempt deadline following it"
```

Expected: `gates=0` before the commit.

---

### Task 4: `agentclinic-repair-depth-3` gains the `R2` rung

Design section 4. `R2` is `R1` plus pytest's own explanation of the third failure. `R1` stays in the manifest as evidence.

**Files:**
- Modify: `src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json`
- Modify: `src/satyrn_evals/qualify.py`
- Test: `tests/test_agentclinic_manifests.py`

**Interfaces:**
- Produces: `manifest.contracts["R2"]` on that task; `qualify.CENSUS_TASKS: dict[str, str]`. Task 9's depth-3 record uses `--rung R2`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_agentclinic_manifests.py`:

```python
#: Design section 4: R2 is R1 plus pytest's own explanation of the third
#: failure, the line R1 strips (`tasks/KNOWN_DEFECTS.md`, depth-3).
R2_EXPLANATION = "assert None is not None, where None = first.timestamp.tzinfo"


def test_depth_3_ships_r2_and_keeps_r1() -> None:
    manifest = load_manifest(resolve_task("agentclinic-repair-depth-3"))
    assert set(manifest.contracts) == {"R0", "R1", "R1b", "R2", "R3"}


def test_r2_is_r1_with_the_tzinfo_explanation_and_nothing_else() -> None:
    """Ruling 4: R2 - R1 is one fact. If anything else differs, the information
    diagnosis the census tests is no longer isolated."""
    manifest = load_manifest(resolve_task("agentclinic-repair-depth-3"))
    r1, r2 = manifest.contracts["R1"], manifest.contracts["R2"]
    assert R2_EXPLANATION in r2
    assert R2_EXPLANATION not in r1
    assert r2.replace(", where None = first.timestamp.tzinfo", "", 1) == r1


def test_r2_does_not_name_the_file_or_the_fix() -> None:
    """The added fact is pytest's assertion text, not a location (section 4)."""
    r2 = load_manifest(resolve_task("agentclinic-repair-depth-3")).contracts["R2"]
    assert "models.py" not in r2
    assert "timezone-aware" not in r2


def test_the_default_contract_is_still_r3() -> None:
    manifest = load_manifest(resolve_task("agentclinic-repair-depth-3"))
    assert manifest.contract == manifest.contracts["R3"]


def test_the_census_rung_map_names_five_tasks_that_exist() -> None:
    from satyrn_evals.qualify import CENSUS_TASKS

    assert len(CENSUS_TASKS) == 5
    for task, rung in CENSUS_TASKS.items():
        assert rung in load_manifest(resolve_task(task)).contracts, task
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_agentclinic_manifests.py -q -k "r2 or census_rung"`
Expected: FAIL with `KeyError: 'R2'` and `ImportError: cannot import name 'CENSUS_TASKS'`.

- [ ] **Step 3: Write `R2` into the manifest, derived rather than typed**

Run exactly this, from `EVALS`, so `R2` cannot drift from `R1` by a typo:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

path = Path("src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json")
body = json.loads(path.read_text(encoding="utf-8"))
old = "the third fails assert None is not None,"
new = "the third fails assert None is not None, where None = first.timestamp.tzinfo,"
r1 = body["contracts"]["R1"]
assert r1.count(old) == 1, r1.count(old)
assert "R2" not in body["contracts"]
contracts = {}
for key, text in body["contracts"].items():
    contracts[key] = text
    if key == "R1b":
        contracts["R2"] = r1.replace(old, new, 1)
body["contracts"] = contracts
path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(contracts["R2"])
PY
```

Expected output, verbatim (one line):

```
Repair the seeded bug in the AgentClinic complaints app. A separate acceptance suite, not present in this workspace, reports four failing checks, test_home_html_element_declares_english_language, test_complaints_board_preserves_the_shared_layout, test_complaint_model_contract_is_preserved, test_post_complaint_redirects_to_complaints_board: the first two raise AttributeError: 'NoneType' object has no attribute 'casefold', the third fails assert None is not None, where None = first.timestamp.tzinfo, and the fourth fails assert 307 == 303. Your workspace has a runnable public suite under tests/ (uv run python -m pytest tests/); a fix must keep every existing behavior intact.
```

Then run `git diff --stat src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json`. Exactly one file, and `git diff` shows one added line. If the rewrite reordered or re-indented anything else, revert and fix the writer rather than committing the churn.

- [ ] **Step 4: Add the census rung map to `qualify.py`**

After `HELDOUT_TASKS`, add:

```python
#: The census set and the rung each task runs at (design section 4). The three
#: maps above name what release one's spec ran and are left as they are: they
#: are cited as evidence of that campaign, and rewriting them would change the
#: record of what was measured, not what will be.
CENSUS_TASKS: dict[str, str] = {
    "agentclinic-repair-depth-3": "R2",
    "selfhost-run-record-gate": PLAN_RUNG,
    "selfhost-docs-linter": PLAN_RUNG,
    "selfhost-cell-loop": PLAN_RUNG,
    "selfhost-speed-probe": PLAN_RUNG,
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_agentclinic_manifests.py tests/test_manifest.py tests/test_engine_contract.py -q`
Expected: PASS.

Run: `uv run python -c "
from satyrn_evals.engine_contract import render_engine_contract
from satyrn_evals.manifest import load_manifest, resolve_task
d = resolve_task('agentclinic-repair-depth-3'); m = load_manifest(d)
print(len(render_engine_contract(d, m, rung='R2', contract_text=m.contracts['R2'])))
"`
Expected: a byte count, no exception — the new rung renders an Engine contract like every other shipped rung.

- [ ] **Step 6: Gates and commit**

```bash
just gates; echo "gates=$?"
git add src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json src/satyrn_evals/qualify.py tests/test_agentclinic_manifests.py
git commit -m "Census tasks 1: depth-3 gains rung R2, R1 plus pytest's tzinfo explanation, and the census rung map"
```

Expected: `gates=0`. The task's `task_tree_sha256` moves; no committed record is relaunched, and Task 9's record pins the new digest.

---

### Task 5: Recorded prompt edits in the generator, and the re-cut `selfhost-run-record-gate`

Design section 4's prompt-edit mechanism. The plan document is never edited; the prompt's provenance becomes the historical plan plus a named patch.

**Files:**
- Modify: `tools/cut_task.py`
- Modify: `tools/task_specs/selfhost-run-record-gate.json`
- Modify: `src/satyrn_evals/qualify.py`
- Replace (re-cut): `src/satyrn_evals/tasks/selfhost-run-record-gate/`
- Test: `tests/test_cut_task.py`, `tests/test_qualify.py`

**Interfaces:**
- Consumes: `cut_task.r1_plan_prompt`, `cut_task.manifest_body`.
- Produces: `cut_task.PromptEdit(old, new, reason)`, `cut_task.apply_prompt_edits(prompt, edits) -> str`; the manifest key `generator.prompt_edits`; `qualify.judge_prompt_edits(manifest_body) -> Check`.

**`prompt_edits` is optional in a task spec, and written into the manifest only when non-empty.** Otherwise every already-cut task's manifest would gain an empty list, every task tree's digest would move, and `agentclinic-repair-depth-2` and the floor tasks would have to be re-cut — which the Global Constraints forbid. `docs-linter`, `cell-loop` and `speed-probe` therefore re-cut byte-identically after this task, and Step 7 proves it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cut_task.py`:

```python
from tools.cut_task import CutError, PromptEdit, apply_prompt_edits, load_spec, manifest_body

EDITS = (
    PromptEdit(old="Gate rules:", new="Validation rules enforced by load_run_record:", reason="r1"),
    PromptEdit(old="enforced by load_run_record", new="enforced by load_run_record and re-checked by gate", reason="r2"),
)


def test_edits_apply_in_order_and_may_depend_on_an_earlier_one() -> None:
    assert apply_prompt_edits("Gate rules: a\n", EDITS) == (
        "Validation rules enforced by load_run_record and re-checked by gate: a\n"
    )


def test_an_old_string_that_is_absent_is_refused() -> None:
    with pytest.raises(CutError, match="occurs 0 times"):
        apply_prompt_edits("nothing here\n", EDITS[:1])


def test_an_old_string_that_occurs_twice_is_refused() -> None:
    with pytest.raises(CutError, match="occurs 2 times"):
        apply_prompt_edits("Gate rules: a\nGate rules: b\n", EDITS[:1])


def test_a_new_string_containing_its_own_old_string_is_refused_at_load(tmp_path: Path, spec_body: dict) -> None:
    """Ruling 5: qualification decides `new` present / `old` absent; an edit
    whose replacement re-introduces its own anchor makes that undecidable."""
    body = spec_body | {"prompt_edits": [{"old": "Gate rules", "new": "Gate rules, restated", "reason": "r"}]}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(body))
    with pytest.raises(CutError, match="must not contain its own old text"):
        load_spec(path)


@pytest.mark.parametrize(
    "edit",
    [
        {"old": "", "new": "x", "reason": "r"},
        {"old": "a", "new": "", "reason": "r"},
        {"old": "a", "new": "b", "reason": ""},
        {"old": "a", "new": "b"},
        {"old": "a", "new": "b", "reason": "r", "extra": 1},
    ],
)
def test_a_malformed_edit_is_refused_at_load(tmp_path: Path, spec_body: dict, edit: dict) -> None:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec_body | {"prompt_edits": [edit]}))
    with pytest.raises(CutError, match="prompt_edits"):
        load_spec(path)


def test_a_spec_without_prompt_edits_still_loads_and_writes_no_manifest_key(tmp_path: Path, spec_body: dict) -> None:
    """The compatibility direction: every already-cut task must re-cut byte-identically."""
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec_body))
    spec = load_spec(path)
    assert spec.prompt_edits == ()
    body = manifest_body(spec, "prompt\n", ["tests/test_x.py::test_y"], "0" * 64)
    assert "prompt_edits" not in body["generator"]


def test_recorded_edits_land_in_the_generator_block(tmp_path: Path, spec_body: dict) -> None:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec_body | {"prompt_edits": [{"old": "a", "new": "b", "reason": "r"}]}))
    body = manifest_body(load_spec(path), "b\n", ["tests/test_x.py::test_y"], "0" * 64)
    assert body["generator"]["prompt_edits"] == [{"old": "a", "new": "b", "reason": "r"}]
```

`spec_body` is a fixture returning a minimal valid spec dict; `tests/test_cut_task.py` already builds one for its `load_spec` tests — promote that literal to a fixture rather than duplicating it.

Append to `tests/test_qualify.py`:

```python
from satyrn_evals.qualify import judge_prompt_edits

PROMPT = "Validation rules enforced by load_run_record: mode is attended.\n"


def _body(edits: list[dict] | None, prompt: str = PROMPT) -> dict:
    generator: dict = {"tool": "tools/cut_task.py", "rung": "R1-plan"}
    if edits is not None:
        generator["prompt_edits"] = edits
    return {"generator": generator, "contracts": {"R1-plan": prompt}}


def test_a_manifest_with_no_recorded_edits_passes() -> None:
    assert judge_prompt_edits(_body(None)).passed


def test_recorded_edits_that_are_in_the_prompt_pass() -> None:
    check = judge_prompt_edits(_body([{"old": "Gate rules:", "new": "Validation rules enforced by load_run_record:", "reason": "r"}]))
    assert check.passed, check.detail


def test_an_edit_whose_old_text_is_still_in_the_prompt_fails() -> None:
    check = judge_prompt_edits(_body([{"old": "mode is attended", "new": "Validation rules", "reason": "r"}]))
    assert not check.passed and "old text is still" in check.detail


def test_an_edit_whose_new_text_is_absent_fails() -> None:
    check = judge_prompt_edits(_body([{"old": "Gate rules:", "new": "nowhere", "reason": "r"}]))
    assert not check.passed and "occurs 0 times" in check.detail


def test_an_edit_whose_new_text_occurs_twice_fails() -> None:
    check = judge_prompt_edits(_body([{"old": "x", "new": "rules", "reason": "r"}], "rules and rules\n"))
    assert not check.passed and "occurs 2 times" in check.detail


def test_recorded_edits_with_no_plan_prompt_fail() -> None:
    body = _body([{"old": "a", "new": "b", "reason": "r"}])
    body["contracts"] = {}
    assert not judge_prompt_edits(body).passed
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cut_task.py tests/test_qualify.py -q`
Expected: FAIL with `ImportError: cannot import name 'PromptEdit'` and `cannot import name 'judge_prompt_edits'`.

- [ ] **Step 3: Implement the mechanism in `tools/cut_task.py`**

Add beside `_SPEC_KEYS`:

```python
#: Optional in a spec, so every already-cut task re-cuts byte-identically
#: (a required key would move every task tree's digest).
_OPTIONAL_SPEC_KEYS = frozenset({"prompt_edits"})
_EDIT_KEYS = frozenset({"old", "new", "reason"})
```

Add the dataclass beside `PlanAnchor`:

```python
@dataclass(frozen=True, slots=True)
class PromptEdit:
    """One recorded patch to the cut prompt (design section 4).

    The plan document is never edited; the prompt's provenance is the
    historical plan plus this named patch, recorded in the manifest.
    """

    old: str
    new: str
    reason: str
```

Add to `TaskSpec`: `prompt_edits: tuple[PromptEdit, ...] = ()`.

In `load_spec`, replace the key check with:

```python
    if not isinstance(body, dict) or not (_SPEC_KEYS <= set(body) <= _SPEC_KEYS | _OPTIONAL_SPEC_KEYS):
        raise CutError(
            f"spec {path}: keys must be exactly {sorted(_SPEC_KEYS)}, optionally with {sorted(_OPTIONAL_SPEC_KEYS)}"
        )
```

and add, before the `return TaskSpec(...)`:

```python
    raw_edits = body.get("prompt_edits", [])
    if not isinstance(raw_edits, list):
        raise CutError(f"spec {path}: prompt_edits must be a list of {{old, new, reason}}")
    edits: list[PromptEdit] = []
    for index, item in enumerate(raw_edits, 1):
        if not isinstance(item, dict) or set(item) != _EDIT_KEYS:
            raise CutError(f"spec {path}: prompt_edits[{index}] must have exactly {sorted(_EDIT_KEYS)}")
        if not all(isinstance(item[key], str) and item[key] for key in _EDIT_KEYS):
            raise CutError(f"spec {path}: prompt_edits[{index}] fields must be non-empty strings")
        if item["old"] in item["new"]:
            raise CutError(
                f"spec {path}: prompt_edits[{index}] new text must not contain its own old text "
                "(qualification asks whether the old text is gone from the prompt)"
            )
        edits.append(PromptEdit(item["old"], item["new"], item["reason"]))
```

with `prompt_edits=tuple(edits)` in the constructor call.

Add the applier beside `r1_plan_prompt`:

```python
def apply_prompt_edits(prompt: str, edits: Sequence[PromptEdit]) -> str:
    """Apply each edit in order; each ``old`` must occur exactly once when its turn comes.

    Order matters and is part of the record: a later edit may anchor on text an
    earlier one introduced, which is why the count is checked against the text
    as it stands rather than against the original.
    """
    text = prompt
    for index, edit in enumerate(edits, 1):
        count = text.count(edit.old)
        if count != 1:
            raise CutError(f"prompt edit {index}: its old text occurs {count} times in the prompt, want 1")
        text = text.replace(edit.old, edit.new, 1)
    return text
```

In `cut`, change the prompt line to:

```python
    prompt = apply_prompt_edits(
        r1_plan_prompt(plan_section(read_plan(repo, spec.plan), spec.plan.heading), spec.hidden, spec.formats),
        spec.prompt_edits,
    )
```

In `manifest_body`, build the generator block as a local and add the key only when there are edits:

```python
    generator: dict[str, object] = {
        "tool": "tools/cut_task.py",
        "rung": RUNG,
        "files": list(spec.files),
        "hidden": list(spec.hidden),
        "plan": {"path": spec.plan.path, "heading": spec.plan.heading, "commit": spec.plan.commit},
    }
    if spec.prompt_edits:
        generator["prompt_edits"] = [
            {"old": edit.old, "new": edit.new, "reason": edit.reason} for edit in spec.prompt_edits
        ]
```

and use `"generator": generator,` in the returned body.

Extend the module docstring's bullet list with one line: "``prompt_edits`` in the spec are applied to the cut prompt in order, each ``old`` required exactly once, and recorded in the manifest's ``generator`` block; the plan document is never edited."

- [ ] **Step 4: Implement `judge_prompt_edits` in `qualify.py`**

Add after `judge_prompt`:

```python
def judge_prompt_edits(manifest_body: dict) -> Check:
    """Every recorded prompt edit is the one the shipped prompt carries (Ruling 5).

    Pure, and deliberately weaker than ``cut_task.py check``: the plan's history
    is that command's business. The question here is only whether the manifest's
    record of the patch matches the prompt it ships beside, so a reader can
    trust ``generator.prompt_edits`` as provenance without a git checkout.
    """
    generator = manifest_body.get("generator")
    edits = (generator or {}).get("prompt_edits") or []
    if not edits:
        return Check("prompt-edits", True, "no recorded prompt edits")
    prompt = (manifest_body.get("contracts") or {}).get(PLAN_RUNG)
    if not isinstance(prompt, str):
        return Check("prompt-edits", False, f"{len(edits)} recorded edits but no {PLAN_RUNG} prompt")
    problems: list[str] = []
    for index, edit in enumerate(edits, 1):
        if not isinstance(edit, dict) or not all(
            isinstance(edit.get(key), str) and edit.get(key) for key in ("old", "new", "reason")
        ):
            problems.append(f"edit {index} is not {{old, new, reason}} of non-empty strings")
            continue
        if (count := prompt.count(edit["new"])) != 1:
            problems.append(f"edit {index}: its new text occurs {count} times, want 1")
        if edit["old"] in prompt:
            problems.append(f"edit {index}: its old text is still in the prompt")
    detail = "; ".join(problems) if problems else f"{len(edits)} recorded edits are in the prompt"
    return Check("prompt-edits", not problems, detail)
```

In `qualify()`, the body is already read for the `generator` probe; keep one read and use it for both:

```python
        manifest_body = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
        checks.append(judge_prompt_edits(manifest_body))
        generated = "generator" in manifest_body
```

- [ ] **Step 5: Write the two prompt edits into the task spec**

The two `old` strings must be copied out of the committed manifest, not retyped — the prompt carries an em dash and exact backtick spacing. Run, from `EVALS`:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path("src/satyrn_evals/tasks/selfhost-run-record-gate/manifest.json").read_text(encoding="utf-8"))
prompt = manifest["contracts"]["R1-plan"]
old1 = next(line for line in prompt.splitlines() if line.startswith("- Produces: `RunRecord`"))
old1 = old1[old1.index("`load_run_record(path: Path) -> RunRecord`") : old1.index("ill-typed field)") + len("ill-typed field)")]
old2 = next(line for line in prompt.splitlines() if line.startswith("Gate rules:"))
new1 = (
    "`load_run_record(path: Path) -> RunRecord` (raises `RunRecordError`, which you define in "
    "`src/satyrn_evals/run_record.py` as a subclass of the existing `UsageError`, imported from `errors.py`; "
    "`errors.py` is already correct and is not one of the files you may change, so add nothing to it; the "
    "exception names the first missing or ill-typed field)"
)
new2 = (
    "Validation rules. `load_run_record` enforces these as it reads the file, raising `RunRecordError`: "
    "`condition` is `cold` or `warm`; `mode` is `attended` or `batch`; `task_tree_sha256` is 64 lowercase hex; "
    "`stop_rule` and `decision_rule` are non-empty. `gate` then enforces the cadence on an already-loaded "
    "record, raising `RunRecordError`: `attended` is n ≤ 8 and `max_minutes` ≤ 60, `batch` is n ≤ 12 "
    "and `max_minutes` ≤ 720; and when `previous_result` is a path, `previous_result_committed` must be "
    "`True` (the CLI computes it; the pure gate is told)."
)
assert prompt.count(old1) == 1 and prompt.count(old2) == 1
assert old1 not in new1 and old2 not in new2
spec_path = Path("tools/task_specs/selfhost-run-record-gate.json")
spec = json.loads(spec_path.read_text(encoding="utf-8"))
spec["prompt_edits"] = [
    {
        "old": old1,
        "new": new1,
        "reason": "release-one admission: 5 of 9 cells put RunRecordError in errors.py, outside source_paths, and the patch was rejected (tasks/KNOWN_DEFECTS.md)",
    },
    {
        "old": old2,
        "new": new2,
        "reason": "release-one admission: with errors.py allowed, 8 of 9 cells read every rule here as gate()'s and left load_run_record permissive, while the hidden suite asserts load_run_record refuses (tasks/KNOWN_DEFECTS.md)",
    },
]
spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(spec["prompt_edits"], indent=2, ensure_ascii=False))
PY
```

Read the printed edits before going on: `old1` must end with `ill-typed field)` and `old2` must be the whole `Gate rules:` line including its trailing full stop. If either assertion fired, stop and report — the committed prompt is not what this plan read.

- [ ] **Step 6: Re-cut the task**

```bash
rm -rf src/satyrn_evals/tasks/selfhost-run-record-gate
uv run python tools/cut_task.py cut tools/task_specs/selfhost-run-record-gate.json
uv run python tools/cut_task.py check tools/task_specs/selfhost-run-record-gate.json; echo "check=$?"
uv run python -c "
import json
b = json.load(open('src/satyrn_evals/tasks/selfhost-run-record-gate/manifest.json'))
p = b['contracts']['R1-plan']
print('edits', len(b['generator']['prompt_edits']))
print('errors.py invitation gone:', 'a \`UsageError\` subclass from \`errors.py\`' not in p)
print('gate rules heading gone:', 'Gate rules:' not in p)
print('load_run_record enforces:', 'load_run_record\` enforces these' in p)
"
```

Expected: `check=0`, `edits 2`, and three `True` lines. `cut_task.py check` exiting 0 is the proof that the recorded edits reproduce the prompt from the historical plan (Ruling 5).

- [ ] **Step 7: Prove the untouched tasks still re-cut byte-identically**

```bash
for s in selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe selfhost-guard-prefixes selfhost-review-script; do
  uv run python tools/cut_task.py check "tools/task_specs/$s.json"; echo "$s=$?"
done
git status --porcelain -- src/satyrn_evals/tasks/selfhost-docs-linter src/satyrn_evals/tasks/selfhost-cell-loop src/satyrn_evals/tasks/selfhost-speed-probe src/satyrn_evals/tasks/selfhost-guard-prefixes src/satyrn_evals/tasks/selfhost-review-script
```

Expected: five `=0` lines and no output from `git status`. Any drift here means `prompt_edits` was not optional; stop and fix that before committing.

- [ ] **Step 8: Qualify all five census tasks**

```bash
uv run pytest tests/test_cut_task.py tests/test_qualify.py -q
for t in agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe; do
  uv run satyrn-evals qualify "$t"; echo "$t=$?"
done
```

Expected: the unit tests pass, and every `qualify` line is `=0` with each `Check` printed `ok`. `qualify` runs the oracle, so it spawns — run it outside the default tier, as here, from the command line. A failing check is a finding, not something to work around: stop and report which check failed on which task.

- [ ] **Step 9: Provenance, gates and commit**

```bash
uv run python tools/provenance.py check; echo "provenance=$?"
just gates; echo "gates=$?"
git add tools/cut_task.py tools/task_specs/selfhost-run-record-gate.json src/satyrn_evals/qualify.py src/satyrn_evals/tasks/selfhost-run-record-gate tests/test_cut_task.py tests/test_qualify.py
git commit -m "Census tasks 2: recorded prompt edits in the generator, and run-record-gate re-cut with the two section 4 edits"
```

Expected: `provenance=0` (a re-cut task's files are already rowed; `provenance.py new` is needed only if the cut adds a file the old tree lacked — check its output and add rows if it asks) and `gates=0`.

---

### Task 6: The task-validity check, its procedure, and the `validity` block

R0 §1.2 and design section 4. A solution written from the prompt alone, by someone other than the task's author and without the plan's code, passes the hidden suite. Recorded per task; a task that fails does not get a census record.

**Files:**
- Create: `docs/superpowers/specs/2026-09-15-release-two-task-validity.md` (≤ 400 lines)
- Modify: `src/satyrn_evals/manifest.py`, `tools/cut_task.py` (`check` ignores the annotation)
- Modify: the five census tasks' `manifest.json`
- Modify: `src/satyrn_evals/tasks/KNOWN_DEFECTS.md`
- Test: `tests/test_manifest.py`, `tests/test_cut_task.py`

**Interfaces:**
- Produces: `TaskManifest.validity: dict | None`, shaped `{"by": str, "commit": 40-hex, "passed": bool}`. Task 9 refuses to write a record for a task whose `validity.passed` is not `True`.

**The `validity` block is a post-cut annotation, and `cut_task.py check` ignores it.** The check that produces it needs the cut prompt, so it cannot be an input to the cut; making it one would force a cut → validate → re-cut cycle that moves three census tasks' trees for a field that describes them rather than defines them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_manifest.py` (reusing its `_write_task` helper):

```python
VALID = {"by": "sonnet-subagent", "commit": "a" * 40, "passed": True}


def test_a_manifest_without_validity_loads_with_none(tmp_path: Path) -> None:
    task = _write_task(tmp_path)
    assert load_manifest(task).validity is None


def test_a_well_formed_validity_block_loads(tmp_path: Path) -> None:
    task = _write_task(tmp_path, extra={"validity": VALID})
    assert load_manifest(task).validity == VALID


@pytest.mark.parametrize(
    "block",
    [
        {"by": "x", "commit": "a" * 40},
        {"by": "x", "commit": "a" * 40, "passed": True, "extra": 1},
        {"by": "", "commit": "a" * 40, "passed": True},
        {"by": "x", "commit": "A" * 40, "passed": True},
        {"by": "x", "commit": "a" * 39, "passed": True},
        {"by": "x", "commit": "a" * 40, "passed": "yes"},
        [],
    ],
)
def test_a_malformed_validity_block_is_refused(tmp_path: Path, block: object) -> None:
    task = _write_task(tmp_path, extra={"validity": block})
    with pytest.raises(ManifestError, match="validity"):
        load_manifest(task)


def test_a_failed_validity_block_still_loads(tmp_path: Path) -> None:
    """A failed check is evidence and must be readable; refusing to record it
    would make the only durable trace of a generator defect unwritable."""
    task = _write_task(tmp_path, extra={"validity": VALID | {"passed": False}})
    assert load_manifest(task).validity == VALID | {"passed": False}
```

Append to `tests/test_cut_task.py`:

```python
def test_check_ignores_a_post_cut_validity_annotation(tmp_path: Path) -> None:
    """A cut task annotated with `validity` still matches a fresh cut."""
    from tools.cut_task import comparable

    committed = tmp_path / "task"
    (committed / "base").mkdir(parents=True)
    (committed / "base" / "app.py").write_text("x = 1\n")
    body = {"name": "t", "contract": "c"}
    (committed / "manifest.json").write_text(json.dumps(body))
    before = comparable(committed)
    (committed / "manifest.json").write_text(json.dumps(body | {"validity": {"by": "s", "commit": "a" * 40, "passed": True}}))
    assert comparable(committed) == before


def test_check_still_sees_any_other_manifest_change(tmp_path: Path) -> None:
    from tools.cut_task import comparable

    committed = tmp_path / "task"
    (committed / "base").mkdir(parents=True)
    (committed / "base" / "app.py").write_text("x = 1\n")
    (committed / "manifest.json").write_text(json.dumps({"name": "t", "contract": "c"}))
    before = comparable(committed)
    (committed / "manifest.json").write_text(json.dumps({"name": "t", "contract": "d"}))
    assert comparable(committed) != before
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_manifest.py tests/test_cut_task.py -q`
Expected: FAIL — `TaskManifest` has no `validity`, and `cut_task` has no `comparable`.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/manifest.py`, add to `TaskManifest` after `ignored_paths`:

```python
    #: The R0 §1.2 task-validity record, added after the cut: a solution
    #: written from this prompt alone, by someone other than the task's author
    #: and without the plan's code, was graded by the hidden suite.
    #: ``{"by": str, "commit": 40-hex, "passed": bool}``; ``None`` means the
    #: check has not run. A failed check is recorded, not omitted.
    validity: dict | None = None
```

and a validator beside `_validate_source_dirs`:

```python
_VALIDITY_KEYS = frozenset({"by", "commit", "passed"})
_HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")


def _validate_validity(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != _VALIDITY_KEYS:
        raise ManifestError(f"validity must be an object with exactly {sorted(_VALIDITY_KEYS)}")
    if not isinstance(value["by"], str) or not value["by"]:
        raise ManifestError("validity.by must be a non-empty string")
    if not isinstance(value["commit"], str) or not _HEX40.match(value["commit"]):
        raise ManifestError("validity.commit must be 40 lowercase hex")
    if type(value["passed"]) is not bool:
        raise ManifestError("validity.passed must be a boolean")
    return dict(value)
```

(`re` is already imported in `manifest.py`; if it is not, add it.) Pass `validity=_validate_validity(data.get("validity"))` in `load_manifest`'s `TaskManifest(...)` construction.

In `tools/cut_task.py`, add:

```python
#: Manifest keys a cut does not produce and `check` therefore ignores. The
#: R0 §1.2 validity record is written after the cut, from the cut prompt.
POST_CUT_MANIFEST_KEYS = ("validity",)


def comparable(task_dir: Path) -> tuple[str, object]:
    """A task tree's identity for `check`: every file but the manifest, plus the
    manifest without its post-cut annotations."""
    body = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
    for key in POST_CUT_MANIFEST_KEYS:
        body.pop(key, None)
    return tree_digest(task_dir, exclude={"manifest.json"}), json.dumps(body, sort_keys=True)
```

and rewrite `main`'s `check` branch to compare `comparable(fresh_dir)` with `comparable(committed)` instead of `tree_digest`, keeping the same message and exit code. Note `cut` returns the created directory, so keep its return value rather than only its digest.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_manifest.py tests/test_cut_task.py -q`
Expected: PASS.

Run the five re-cut checks again (Task 5 Step 7's loop plus `selfhost-run-record-gate`); every one must still be `=0`.

- [ ] **Step 5: Write the procedure document**

Create `docs/superpowers/specs/2026-09-15-release-two-task-validity.md`, at most 400 lines, with exactly these sections. It is a procedure the controller follows, not code.

1. `# Release two R0 — the task-validity check (procedure)` and one paragraph: what R0 §1.2 asks, what design section 4 records, and that this document is the recipe the controller runs once per census task.
2. `## What the solver sees, and what it must not` — Ruling 6, written out: a copy of `<task>/base/` at `<scratchpad>/validity/<task>/tree`, `git init` and one commit; `PROMPT.txt` from `manifest.json`'s `contracts[rung]` for the rung in `qualify.CENSUS_TASKS`; nothing else. The evals checkout, `~/satyrn-runs`, `/Users/Shared`, `overlay/`, `fixtures/`, `manifest.json`, `qualification.json` and `docs/superpowers/plans/` are off limits, named individually so the instruction is checkable.
3. `## The dispatch` — one Sonnet subagent per task, blocking, given `PROMPT.txt`'s text and the tree path and nothing else; it writes a solution in the tree; it does not run the hidden suite (it has no access to one) and may run whatever public suite the base carries. Its final report says what it changed and why. No haiku, no GPU, no network beyond the model itself.
4. `## Harvest` — the controller, not the agent: `git add -A && git diff --cached` in the tree, written to `<scratchpad>/validity/<task>/solution.diff`.
5. `## The two leak tells` — any id from the manifest's `expected_test_ids` appearing in the diff or the report; any of `overlay`, `known-good.patch`, `known-broken.patch`, `manifest.json`, or the task directory's path appearing there. State plainly that matching the known-good patch is **not** a tell: a correct solution is supposed to look like the fix. A tell voids the run; redo with a fresh agent and record the void.
6. `## Grading` — `satyrn-evals grade TASK solution.diff --receipt receipt.json` from `$HOME/satyrn-census-grades/validity/<task>/`, with `UV_OFFLINE=1`, after confirming no `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`, `setup.cfg` or `conftest.py` sits in that directory or above it. The verdict is read from the receipt, never from the exit status.
7. `## What is recorded` — `validity: {by, commit, passed}` in the task's `manifest.json`: `by` is the model that wrote the solution (for example `sonnet-4.6`), `commit` is `git rev-parse HEAD` of the evals tree the prompt was read from, `passed` is `receipt.verdict == "pass"`. A failed check is recorded with `passed: false` and the task does not get a census record until it is fixed and re-checked.
8. `## Recompute` — a fenced block showing the whole sequence for one task, so a reader can repeat it.

- [ ] **Step 6: Run the check for all five tasks (controller steps)**

For each of `agentclinic-repair-depth-3` (rung `R2`), `selfhost-run-record-gate`, `selfhost-docs-linter`, `selfhost-cell-loop`, `selfhost-speed-probe` (rung `R1-plan`), follow the document. Record the receipt path, the verdict and the leak-tell result for each. Then write the block into each manifest:

```bash
uv run python - <<'PY'
import json, subprocess
from pathlib import Path

commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
# PASSED: fill in from the five receipts, verdict == "pass" only.
PASSED = {}  # e.g. {"selfhost-docs-linter": True, ...}
BY = "sonnet-4.6"
for task, passed in PASSED.items():
    path = Path("src/satyrn_evals/tasks") / task / "manifest.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["validity"] = {"by": BY, "commit": commit, "passed": bool(passed)}
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(task, body["validity"])
PY
```

**A task whose `passed` is false gets no census record** (design section 4). Stop and report it to the maintainer; do not fix the prompt inside this task.

- [ ] **Step 7: The `pyproject.toml` decision for `selfhost-docs-linter`**

Design section 4 leaves this to the validity check. Read the docs-linter receipt and its `solution.diff`, then take exactly one branch and write the reason into `KNOWN_DEFECTS.md`:

- **C — the expected branch.** The solution passes and its diff touches nothing outside `source_paths`. `pyproject.toml` was cell 147562's own detour, not something the prompt requires. **No change**; record that the check found the prompt determines the choice without it.
- **A — `ignored_paths`.** The solution passes but its diff touches `pyproject.toml`, and removing that hunk still passes. The file is incidental to the answer. Add an optional `ignored_extra` list to the task-spec schema exactly as `prompt_edits` was added in Task 5 (optional key, written into `manifest_body`'s `ignored_paths` as `[*IGNORED_PATHS, *spec.ignored_extra]` only when non-empty), put `"pyproject.toml"` in the docs-linter spec, re-cut docs-linter, and re-run `cut_task.py check` and `qualify` for it.
- **B — `source_paths`.** The solution only passes with its `pyproject.toml` hunk. The file is part of the answer. Add `"pyproject.toml"` to that spec's `files`, re-cut, and re-run `cut_task.py check` and `qualify`. Note that this also changes `fixtures/known-good.patch` (the GOOD diff is restricted to `files`), so re-read the fixture before committing.

In every branch: no other task's spec changes, and the floor tasks are not re-cut.

- [ ] **Step 8: Update `KNOWN_DEFECTS.md`**

Under `agentclinic-repair-depth-3`, append: the defect is addressed by rung `R2` (Task 4's commit), and the validity check's verdict and commit. Under `selfhost-run-record-gate`, append: the defect is addressed by the two recorded prompt edits (Task 5's commit), and the validity check's verdict and commit. Under `## Admission rule`, append one sentence saying both were re-qualified under R0 §2 and naming the two `validity` blocks. Do not delete the original diagnoses: they are the evidence the fixes answer.

- [ ] **Step 9: Provenance, gates and commit**

```bash
uv run python tools/provenance.py new docs/superpowers/specs/2026-09-15-release-two-task-validity.md
uv run python tools/lint_docs.py; echo "lint-docs=$?"
just gates; echo "gates=$?"
git add docs/superpowers/specs/2026-09-15-release-two-task-validity.md src/satyrn_evals/manifest.py tools/cut_task.py src/satyrn_evals/tasks/KNOWN_DEFECTS.md src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json src/satyrn_evals/tasks/selfhost-run-record-gate/manifest.json src/satyrn_evals/tasks/selfhost-docs-linter/manifest.json src/satyrn_evals/tasks/selfhost-cell-loop/manifest.json src/satyrn_evals/tasks/selfhost-speed-probe/manifest.json tests/test_manifest.py tests/test_cut_task.py PROVENANCE.md
git commit -m "Census tasks 3: the R0 task-validity check, its procedure, and the recorded validity block for the five census tasks"
```

If branch A or B was taken in Step 7, its spec and re-cut tree are staged in the same commit, with the branch and its reason in the message.

Expected: `lint-docs=0` (the new spec is ≤ 400 lines) and `gates=0`.

---

### Task 7: The section 6 evidence fields

Design section 6, minus the offline fields (Ruling 16). Everything here is answerable from one transcript plus one `timeline.jsonl`.

**Files:**
- Modify: `src/satyrn_evals/cell_evidence.py`, `src/satyrn_evals/rescore.py`
- Test: `tests/test_cell_evidence.py`, `tests/test_rescore.py`

**Interfaces:**
- Consumes: `CellEvidence.length_stops` (Task 1), `manifest.TaskManifest.source_paths`.
- Produces: `collect_evidence(..., source_paths: Sequence[str] = ())`; `CellEvidence.tool_span_seconds: float | None`, `.exploration_turns: int | None`, `.biggest_turn: dict | None`, `.self_stop: dict | None`, all in `to_block()`. Task 8 reads them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cell_evidence.py` (`_assistant` from Task 1 is in scope):

```python
SOURCES = ("src/satyrn_evals/run_record.py", "tools/lint_docs.py", "tests")


def _write(call_id: str, path: str, *, error: bool = False) -> list[str]:
    return [
        _line({"type": "tool_execution_start", "toolCallId": call_id, "toolName": "write", "args": {"path": path, "content": "x\n"}}),
        _line({"type": "tool_execution_end", "toolCallId": call_id, "toolName": "write",
               "result": {"content": [{"type": "text", "text": ""}]}, "isError": error}),
    ]


def test_exploration_turns_counts_the_turns_before_the_first_landed_source_edit() -> None:
    text = _transcript(
        _assistant(100),
        *_bash("b1", "ls"),
        _line({"type": "turn_start"}),
        _assistant(200),
        *_bash("b2", "cat tools/lint_docs.py"),
        _line({"type": "turn_start"}),
        _assistant(300),
        *_write("w1", "tools/lint_docs.py"),
    )
    assert collect_evidence(text, source_paths=SOURCES).to_block()["exploration_turns"] == 2


def test_a_cell_that_never_mutates_a_source_file_records_null_not_its_turn_count() -> None:
    """Ruling 14: 'explored for 40 turns then edited' and 'never edited' are
    different rows; a number would merge them."""
    text = _transcript(_assistant(100), *_bash("b1", "ls"))
    assert collect_evidence(text, source_paths=SOURCES).to_block()["exploration_turns"] is None


def test_a_test_file_edit_is_not_a_source_mutation() -> None:
    text = _transcript(_assistant(100), *_write("w1", "tests/test_lint_docs.py"), _line({"type": "turn_start"}), *_write("w2", "tools/lint_docs.py"))
    assert collect_evidence(text, source_paths=SOURCES).to_block()["exploration_turns"] == 1


def test_an_edit_outside_source_paths_is_not_a_source_mutation() -> None:
    text = _transcript(_assistant(100), *_write("w1", "pyproject.toml"))
    assert collect_evidence(text, source_paths=SOURCES).to_block()["exploration_turns"] is None


def test_a_failed_edit_is_not_a_source_mutation() -> None:
    text = _transcript(_assistant(100), *_write("w1", "tools/lint_docs.py", error=True))
    assert collect_evidence(text, source_paths=SOURCES).to_block()["exploration_turns"] is None


def test_an_absolute_path_inside_the_worktree_is_a_source_mutation() -> None:
    text = _transcript(_assistant(100), *_write("w1", f"{CWD}/tools/lint_docs.py"))
    assert collect_evidence(text, source_paths=SOURCES).to_block()["exploration_turns"] == 0


def test_with_no_source_paths_nothing_is_a_source_mutation() -> None:
    text = _transcript(_assistant(100), *_write("w1", "tools/lint_docs.py"))
    assert collect_evidence(text).to_block()["exploration_turns"] is None


def test_the_biggest_turn_and_its_share() -> None:
    text = _transcript(
        _assistant(1000),
        _line({"type": "turn_start"}),
        _assistant(3000),
        _line({"type": "turn_start"}),
        _assistant(1000),
    )
    assert collect_evidence(text).to_block()["biggest_turn"] == {"turn": 2, "output_tokens": 3000, "share": 0.6}


def test_a_transcript_with_no_assistant_tokens_has_no_biggest_turn() -> None:
    assert collect_evidence(_transcript(*_bash("b1", "ls"))).to_block()["biggest_turn"] is None


def test_self_stop_is_recorded_when_the_loop_ended_on_its_own() -> None:
    text = _transcript(_assistant(1200), *_bash("b1", "ls"), _line({"type": "agent_end"}))
    assert collect_evidence(text).to_block()["self_stop"] == {"turn": 1, "output_tokens": 1200}


def test_a_cell_the_harness_cut_has_no_self_stop() -> None:
    """Ruling 15: every BUDGET_EXCEEDED and COMMAND_TIMEOUT transcript lacks `agent_end`."""
    text = _transcript(_assistant(48001), *_bash("b1", "ls"))
    assert collect_evidence(text).to_block()["self_stop"] is None


def test_tool_span_seconds_is_first_start_to_last_end() -> None:
    timeline = "\n".join([
        json.dumps({"at": 10.0, "event": "start", "toolCallId": "a", "toolName": "bash"}),
        json.dumps({"at": 12.5, "event": "end", "toolCallId": "a", "toolName": "bash"}),
        json.dumps({"at": 20.0, "event": "start", "toolCallId": "b", "toolName": "read"}),
        json.dumps({"at": 31.0, "event": "end", "toolCallId": "b", "toolName": "read"}),
    ])
    assert collect_evidence(_transcript(), timeline=timeline).to_block()["tool_span_seconds"] == 21.0


def test_an_unfinished_last_command_still_spans_to_its_start() -> None:
    timeline = "\n".join([
        json.dumps({"at": 10.0, "event": "start", "toolCallId": "a", "toolName": "bash"}),
        json.dumps({"at": 12.5, "event": "end", "toolCallId": "a", "toolName": "bash"}),
        json.dumps({"at": 40.0, "event": "start", "toolCallId": "b", "toolName": "bash"}),
    ])
    assert collect_evidence(_transcript(), timeline=timeline).to_block()["tool_span_seconds"] == 30.0


def test_no_timeline_means_no_tool_span() -> None:
    assert collect_evidence(_transcript()).to_block()["tool_span_seconds"] is None
```

Append to `tests/test_rescore.py` one test asserting `compute_evidence` passes the manifest's `source_paths` through — build a cell whose transcript writes a file inside `source_paths` and assert the rebuilt block's `exploration_turns` is not `None`, beside a sibling whose write is outside it and is `None`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cell_evidence.py tests/test_rescore.py -q`
Expected: FAIL with `TypeError: collect_evidence() got an unexpected keyword argument 'source_paths'`.

- [ ] **Step 3: Implement in `cell_evidence.py`**

Add to the module docstring's rule list:

```
- a **source mutation** is a ``write`` or ``edit`` whose ``tool_execution_end``
  is not an error and whose worktree-relative path is inside the manifest's
  ``source_paths`` and is not a test file (basename ``test_*.py`` or
  ``*_test.py``, or any parent component ``tests``). This is the finishing
  counterfactual's own rule, so the two instruments agree;
- **exploration turns** are the ``turn_start`` events strictly before the turn
  holding the first source mutation, and ``null`` when there is none;
- the **biggest turn** is the turn with the most assistant output tokens, with
  its share of the cell's total;
- a **self stop** is an ``agent_end`` event: the loop ended on its own rather
  than being torn down. Its turn and token counts are those at that event.
```

Add the fields to `CellEvidence` (after `overlay_windows`) and to `to_block()` in the same order:

```python
    tool_span_seconds: float | None = None
    exploration_turns: int | None = None
    biggest_turn: dict[str, object] | None = None
    self_stop: dict[str, int] | None = None
```

Add the helpers beside `outside`:

```python
def _worktree_relative(path: str, cwd: str | None) -> str | None:
    """A file tool's path as a worktree-relative POSIX path, or None if it leaves."""
    if outside(cwd, path):
        return None
    if not posixpath.isabs(path):
        return posixpath.normpath(path)
    if cwd is None:
        return None
    return posixpath.relpath(_canonical(path), _canonical(cwd))


def _in_source_paths(path: str, source_paths: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    return any(
        candidate == PurePosixPath(entry) or candidate.is_relative_to(PurePosixPath(entry))
        for entry in source_paths
    )


def _is_test_path(path: str) -> bool:
    """The finishing counterfactual's rule exactly (module docstring, Ruling 14)."""
    parts = PurePosixPath(path).parts
    if "tests" in parts[:-1]:
        return True
    name = parts[-1] if parts else ""
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py")
```

Replace the single `for event in events:` pass in `collect_evidence` with one that also accumulates the new numbers:

```python
    usage = UsageCounter()
    first_pass: dict[str, object] | None = None
    per_turn: dict[int, int] = {}
    self_stop: dict[str, int] | None = None
    mutation_turn: int | None = None
    pending_mutations: dict[str, int] = {}
    for event in events:
        before = usage.output_tokens
        usage.feed_event(event)
        if usage.output_tokens != before:
            per_turn[usage.turns] = per_turn.get(usage.turns, 0) + (usage.output_tokens - before)
        if first_pass is None and (route := _passing_route(event)) is not None:
            first_pass = {"turn": usage.turns, "output_tokens": usage.output_tokens, "route": route}
        if self_stop is None and event.get("type") == "agent_end":
            self_stop = {"turn": usage.turns, "output_tokens": usage.output_tokens}
        if mutation_turn is None:
            mutation_turn = _track_mutation(event, usage.turns, cwd, source_paths, pending_mutations)
```

with

```python
def _track_mutation(
    event: dict, turn: int, cwd: str | None, source_paths: Sequence[str], pending: dict[str, int]
) -> int | None:
    """The turn of the first landed source mutation, once its end event arrives.

    Pi runs one tool call at a time, so a call's start and end bracket nothing
    else; when they do not, this answers with the first mutation that *landed*,
    which is what "mutation" means.
    """
    call_id = event.get("toolCallId")
    if not isinstance(call_id, str):
        return None
    match event.get("type"):
        case "tool_execution_start" if event.get("toolName") in ("write", "edit"):
            args = event.get("args")
            path = args.get("path") if isinstance(args, dict) else None
            if isinstance(path, str):
                relative = _worktree_relative(path, cwd)
                if relative is not None and _in_source_paths(relative, source_paths) and not _is_test_path(relative):
                    pending[call_id] = turn
        case "tool_execution_end" if call_id in pending:
            start_turn = pending.pop(call_id)
            if not event.get("isError"):
                return start_turn
    return None
```

After the loop, before the `return CellEvidence(...)`:

```python
    total = usage.output_tokens
    biggest_turn: dict[str, object] | None = None
    if per_turn and total:
        turn, tokens = max(per_turn.items(), key=lambda item: (item[1], -item[0]))
        biggest_turn = {"turn": turn, "output_tokens": tokens, "share": round(tokens / total, 3)}
    all_spans = read_timeline(timeline or "")
    tool_span_seconds = None
    if all_spans:
        starts = [span.started for span in all_spans.values()]
        ends = [span.ended if span.ended is not None else span.started for span in all_spans.values()]
        tool_span_seconds = max(ends) - min(starts)
```

and change the bash-span line to reuse it: `spans = [span for span in all_spans.values() if span.tool_name == "bash"]`. Pass the four new values into the constructor, with

```python
        exploration_turns=None if mutation_turn is None else mutation_turn - 1,
```

Finally add the parameter to the signature: `source_paths: Sequence[str] = ()`, documented as "the manifest's, so a mutation can be told from a detour; empty means no path is a source path".

- [ ] **Step 4: Implement in `rescore.py`**

In `compute_evidence`, pass it through:

```python
        evidence = collect_evidence(
            text,
            timeline=timeline,
            overlay=overlay,
            visible_texts=visible_texts or [],
            source_paths=manifest.source_paths,
        )
```

`launch_record.write_arm_summaries` already forwards `manifest` in its `kwargs`, so the launcher picks this up with no further change.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_cell_evidence.py tests/test_rescore.py tests/test_launch_record.py -q`
Expected: PASS.

The retained nights are read-only evidence and are **not** re-summarized by this task: `satyrn-evals summarize` rewrites a night's `summary.json`, and rewriting a committed night's summary under a changed evidence block would overwrite the numbers a committed result cites. Task 8 reads those nights without writing to them. Confirm nothing under `~/satyrn-runs` changed: `find ~/satyrn-runs -newer src/satyrn_evals/cell_evidence.py -name 'summary.json' | head` must print nothing.

- [ ] **Step 6: Gates and commit**

```bash
just gates; echo "gates=$?"
git add src/satyrn_evals/cell_evidence.py src/satyrn_evals/rescore.py tests/test_cell_evidence.py tests/test_rescore.py
git commit -m "Census harness 4: the section 6 evidence fields -- tool span, exploration turns, biggest turn, self stop"
```

Expected: `gates=0`.

---

### Task 8: The classification tooling

Design section 7. One night directory and one record in; the classified table, the section 6 offline fields and the finish-on-green counterfactual at the 32k line out, under both run 1's rules and run 2's method.

**Files:**
- Create: `src/satyrn_evals/census_classify.py` (the new pure rules)
- Create: `evidence/2026-09-16-census/classify.py` (the night driver), `evidence/2026-09-16-census/.gitignore`
- Test: `tests/test_census_classify.py`

**Interfaces:**
- Consumes: `satyrn_evals.budget.UsageCounter`; `satyrn_evals.cell_evidence.collect_evidence`; `satyrn_evals.session_patch.build_cumulative_patch` and `RESIDUE_EXCLUDES`; the `satyrn-evals grade` CLI; and, **by path and unmodified**, `evidence/2026-09-15-finishing-counterfactual/counterfactual.py` for `parse_events`, `session_cwd`, `steps_of`, `source_edit_indices`, `summary_lines`, `is_green`, `is_test_run`, `find_trigger`, `plan_bash`, `tree_path`, `in_source_paths`, `could_write_source`, `replay`, `project_markers` (Ruling 7).
- Produces: `census_classify.CLASSES`, `TurnRow`, `per_turn`, `flags`, `within_32k`, `whole_attempt_seconds`, `row`; and the CLI `uv run --project . python evidence/2026-09-16-census/classify.py --night DIR --record PATH [--out DIR] [--grade-root DIR]`, writing `cells.json`, `table.md` and `classes.md` under `evidence/2026-09-16-census/<task>/`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_census_classify.py`:

```python
"""The census's pure classification rules. Default tier: synthetic events, no subprocess.

The eight classes of design section 7 are columns a reviewer fills, not values
this module computes (a count without a class does not admit a task, AGENTS.md).
What is computed is the *evidence* each class is argued from, and each flag has
a firing row and a silent row.
"""

import json

import pytest

from satyrn_evals.census_classify import (
    CLASSES,
    Facts,
    TurnRow,
    flags,
    per_turn,
    whole_attempt_seconds,
    within_32k,
)


def _assistant(output: int, *, stop: str | None = None) -> dict:
    message: dict = {"role": "assistant", "usage": {"output": output}, "content": []}
    if stop is not None:
        message["stopReason"] = stop
    return {"type": "message_end", "message": message}


TURN = {"type": "turn_start"}


def test_the_eight_classes_are_the_specs_and_in_its_order() -> None:
    assert CLASSES == (
        "information", "ambiguity", "capability", "budget",
        "finishing", "runaway", "hunting", "allowlist",
    )


def test_per_turn_carries_tokens_cumulative_tokens_and_length_stops() -> None:
    rows = per_turn([TURN, _assistant(1000), TURN, _assistant(16000, stop="length"), _assistant(500)])
    assert rows == [
        TurnRow(turn=1, output_tokens=1000, cumulative_output_tokens=1000, length_stops=0),
        TurnRow(turn=2, output_tokens=16500, cumulative_output_tokens=17500, length_stops=1),
    ]


def test_per_turn_of_an_empty_stream_is_empty() -> None:
    assert per_turn([]) == []


@pytest.mark.parametrize(
    ("tokens", "turn", "expected"),
    [(32_000, 48, True), (32_001, 48, False), (32_000, 49, False), (0, 1, True)],
)
def test_within_32k_is_the_pre_registered_line(tokens: int, turn: int, expected: bool) -> None:
    assert within_32k(tokens, turn) is expected


def _facts(**overrides: object) -> Facts:
    base: dict = dict(
        code="BUDGET_EXCEEDED", verdict=None, tripped_verdict=None, length_stops=0, root_searches=0,
        tool_reported_timeouts=0, first_pass_turn=None, first_pass_tokens=None, self_stop_turn=None,
        allowlist_reason=None,
    )
    return Facts(**(base | overrides))


def test_a_pass_state_inside_the_line_that_the_cell_worked_past_flags_finishing() -> None:
    assert flags(_facts(first_pass_turn=20, first_pass_tokens=18_000))["finishing"] is True


def test_a_pass_state_outside_the_line_flags_budget_not_finishing() -> None:
    row = flags(_facts(first_pass_turn=60, first_pass_tokens=41_000))
    assert (row["budget"], row["finishing"]) == (True, False)


def test_no_pass_state_at_all_flags_capability() -> None:
    row = flags(_facts())
    assert (row["capability"], row["budget"], row["finishing"]) == (True, False, False)


def test_a_cell_that_passed_flags_none_of_the_three() -> None:
    row = flags(_facts(code="OK", verdict="pass", first_pass_turn=8, first_pass_tokens=6000, self_stop_turn=9))
    assert not any(row[name] for name in ("capability", "budget", "finishing"))


def test_a_length_stop_flags_runaway_and_none_flags_it_silent() -> None:
    assert flags(_facts(length_stops=1))["runaway"] is True
    assert flags(_facts(length_stops=0))["runaway"] is False


def test_a_root_search_or_a_bounded_command_flags_hunting() -> None:
    assert flags(_facts(root_searches=1))["hunting"] is True
    assert flags(_facts(tool_reported_timeouts=1))["hunting"] is True
    assert flags(_facts())["hunting"] is False


def test_a_non_source_path_reason_flags_allowlist() -> None:
    assert flags(_facts(allowlist_reason="patch touches non-source path: pyproject.toml"))["allowlist"] is True
    assert flags(_facts(allowlist_reason="no patch"))["allowlist"] is False


def test_information_and_ambiguity_are_never_flagged_mechanically() -> None:
    """R0 §2: both are task defects argued from the reconstruction, never counted."""
    row = flags(_facts(first_pass_turn=None))
    assert row["information"] is None and row["ambiguity"] is None


def test_whole_attempt_seconds_comes_from_the_directory_stamp_and_the_record_mtime() -> None:
    """Ruling 8: no new harness clock; the two stamps already exist."""
    name = "selfhost-docs-linter-20260916-013000-500000"
    assert whole_attempt_seconds(name, 1_000_000.0 + 0.0) is not None


def test_a_directory_name_without_a_stamp_has_no_whole_attempt_seconds() -> None:
    assert whole_attempt_seconds("not-a-stamp", 1_000_000.0) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_census_classify.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satyrn_evals.census_classify'`.

- [ ] **Step 3: Write `src/satyrn_evals/census_classify.py`**

```python
"""The census's classification arithmetic: what each of the eight classes is argued from.

Design section 7. The classes themselves are columns a reviewer fills, by turn,
from the reconstruction -- "a count without a class does not admit a task"
(AGENTS.md), and information and ambiguity are task defects under R0 §2 that no
counter can decide. What this module computes is the evidence: per-turn tokens,
the pre-registered 32,000-token / 48-turn line, and one boolean per mechanically
decidable class. `information` and `ambiguity` are always None: the reviewer
fills them or nothing does.

Pure: dicts and numbers in, dicts and numbers out. No filesystem, no process.
The replay and own-green rules are not here -- they are the pre-registered,
Opus-reviewed ones in
`evidence/2026-09-15-finishing-counterfactual/counterfactual.py`, which the
night driver loads by path so the census reads the same instrument run 1 and
run 2 read (Ruling 7).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from satyrn_evals.budget import UsageCounter

#: Design section 7's table, in its order.
CLASSES: tuple[str, ...] = (
    "information", "ambiguity", "capability", "budget",
    "finishing", "runaway", "hunting", "allowlist",
)
#: The two a reviewer argues and a counter never decides (R0 §2).
REVIEWER_ONLY: tuple[str, ...] = ("information", "ambiguity")
#: The pre-registered comparison line, from
#: `2026-09-15-release-two-finishing-counterfactual.md` section 3.
TOKEN_LINE = 32_000
TURN_LINE = 48
#: `attempt.attempt_dir_name`: ``<task>-YYYYmmdd-HHMMSS-ffffff``.
_STAMP = re.compile(r"-(\d{8}-\d{6}-\d{6})\Z")


@dataclass(frozen=True, slots=True)
class TurnRow:
    turn: int
    output_tokens: int
    cumulative_output_tokens: int
    length_stops: int


def per_turn(events: list[dict]) -> list[TurnRow]:
    """One row per turn, counted exactly as the budget counts (`UsageCounter`).

    Tokens an assistant message carries before the first `turn_start` belong to
    turn 0 and are dropped from the rows but not from the cumulative totals, so
    a row's cumulative figure always matches the tripwire's at that point.
    """
    usage = UsageCounter()
    rows: dict[int, list[int]] = {}
    for event in events:
        before = usage.output_tokens
        usage.feed_event(event)
        if usage.turns >= 1:
            row = rows.setdefault(usage.turns, [0, 0, 0])
            row[0] += usage.output_tokens - before
            row[1] = usage.output_tokens
            row[2] += 1 if _is_length_stop(event) else 0
    return [
        TurnRow(turn=turn, output_tokens=row[0], cumulative_output_tokens=row[1], length_stops=row[2])
        for turn, row in sorted(rows.items())
    ]


def _is_length_stop(event: dict) -> bool:
    message = event.get("message")
    return (
        event.get("type") == "message_end"
        and isinstance(message, dict)
        and message.get("role") == "assistant"
        and message.get("stopReason") == "length"
    )


def within_32k(output_tokens: int, turn: int) -> bool:
    """The pre-registered line: cumulative output tokens <= 32,000 and turn <= 48."""
    return output_tokens <= TOKEN_LINE and turn <= TURN_LINE


@dataclass(frozen=True, slots=True)
class Facts:
    """What one cell offers the classifier, all of it already recorded.

    `first_pass_*` come from the driver's turn-by-turn grading, not from the
    cell's own test runs: a pass state is the hidden suite's, an own-green is
    the model's, and section 7 distinguishes them.
    """

    code: str | None
    verdict: str | None
    tripped_verdict: str | None
    length_stops: int
    root_searches: int
    tool_reported_timeouts: int
    first_pass_turn: int | None
    first_pass_tokens: int | None
    self_stop_turn: int | None
    allowlist_reason: str | None


def flags(facts: Facts) -> dict[str, bool | None]:
    """One entry per class: True/False where a record decides it, None where only a reviewer can."""
    passed = facts.code == "OK" and facts.verdict == "pass"
    reached = facts.first_pass_turn is not None and facts.first_pass_tokens is not None
    inside = reached and within_32k(facts.first_pass_tokens or 0, facts.first_pass_turn or 0)
    return {
        "information": None,
        "ambiguity": None,
        "capability": not passed and not reached,
        "budget": not passed and reached and not inside,
        "finishing": not passed and bool(inside),
        "runaway": facts.length_stops > 0,
        "hunting": facts.root_searches > 0 or facts.tool_reported_timeouts > 0,
        "allowlist": bool(facts.allowlist_reason and "non-source path" in facts.allowlist_reason),
    }


def whole_attempt_seconds(attempt_dir: str, record_mtime: float) -> float | None:
    """Ruling 8: the directory's microsecond UTC stamp to `attempt.json`'s mtime.

    No new harness clock. `timeline.jsonl` is monotonic and holds only tool
    events, so it gives the tool span and never the whole attempt; these two
    stamps already exist and bracket setup, command, preservation and grading.
    """
    match = _STAMP.search(attempt_dir)
    if match is None:
        return None
    started = datetime.strptime(match.group(1), "%Y%m%d-%H%M%S-%f").replace(tzinfo=UTC)
    return record_mtime - started.timestamp()
```

`row(...)` is deliberately not in this module: assembling an output row is the driver's job, and putting it here would drag the night's directory layout into the package.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_census_classify.py -q`
Expected: PASS. Adjust `test_whole_attempt_seconds_comes_from_the_directory_stamp_and_the_record_mtime` to assert the exact difference once the helper exists (compute the expected epoch in the test rather than asserting `is not None`).

- [ ] **Step 5: Write the night driver**

Create `evidence/2026-09-16-census/.gitignore` holding `work/`, and `evidence/2026-09-16-census/classify.py`. It is a script, not a package: pyproject excludes `evidence/` from ruff and pyrefly, and it is frozen beside its outputs.

Its shape, in order:

1. **Header and imports.** Load `counterfactual.py` by path into `sys.modules["cf"]` exactly as `run-2/trajectory.py` does, and import `satyrn_evals.census_classify` and `satyrn_evals.cell_evidence` by name. Set `cf.WORK` to `HERE / "work"`.
2. **`cells(night, record)`.** Read `<night>/launch.json`'s `slots`, and for each finished slot the `attempt_dir` under `<night>/<arm>/`. Refuse a night whose `record_sha256` is not the given record's (`launch.json`'s `identity`), and refuse a record whose `task` is not the night's. No hard-coded cell lists: the night and the record are the arguments, which is the whole point of generalising the run-2 scripts.
3. **`audit(cell)`** — `run-2/audit.py`'s row, with the cell set replaced by the argument, plus `census_classify.per_turn` instead of its private `per_turn`, plus the section 6 fields taken from `cell_evidence.collect_evidence(transcript, timeline=..., source_paths=manifest.source_paths)` rather than recomputed, so the launcher's numbers and the census's are the same numbers.
4. **`trajectory(cell)`** — `run-2/trajectory.py`'s std replay, grading the reconstructed worktree at the end of every turn from the first source edit, cached by patch digest. `cf.replay`, `build_cumulative_patch(..., exclude=RESIDUE_EXCLUDES)`, `satyrn-evals grade` under `--grade-root` with `UV_OFFLINE=1` and `TMPDIR` inside the receipt folder, refusing a grade root with any `cf.project_markers`. The `ext` replay of run 2 is **not** carried over: it executed model-written Python in a scratch tree, which needs its own review, and the census's question is answered by the std replay.
5. **`offline_fields(cell, turns)`** — section 6's offline four: the first turn whose graded verdict is `pass` and the cumulative tokens there (pass state); the own-green turn from `cf.find_trigger`; and the spend after the pass state (turns and tokens from it to the end).
6. **`counterfactual(cell, turns)`** — the finish-on-green reading at the 32k line, twice: run 1's pre-registered rules (`cf.find_trigger` plus `cf.within_budget`, with `cf.unmeasured_reasons` recorded), and run 2's method (the graded worktree at the end of the trigger turn, from the trajectory above). Both are reported per cell and totalled per task as rescues, harms and net, with unmeasured cells listed. Nothing pools across tasks.
7. **Outputs, under `evidence/2026-09-16-census/<task>/`**: `cells.json` (every number, stamped with the evals commit, a dirty flag and the command line), `table.md` (one row per cell: code, verdict, `tripped_verdict`, turns, tokens, length stops, exploration turns, biggest turn and share, tool span seconds, whole-attempt seconds, self-stop turn and tokens, pass-state turn and tokens, own-green turn, post-pass spend), and `classes.md` — the same rows with **eight empty class columns** (`CLASSES`) plus a `primary` column and a `cited turns` column, and the mechanical `flags` printed beneath each row as `evidence: …` so the reviewer sees what a class would be argued from without the file pretending to have decided it.
8. **`main`** with `--night`, `--record`, `--out` (default `HERE`), `--grade-root` (default `$HOME/satyrn-census-grades`), `--cell` (repeatable, for verification). Exit 0 on success, 2 on any refusal.

- [ ] **Step 6: Verify the driver on retained cells only**

The census cells do not exist yet. Verify on a retained night whose record is committed, read-only:

```bash
mkdir -p "$HOME/satyrn-census-grades"
uv run --project . python evidence/2026-09-16-census/classify.py \
  --night "$HOME/satyrn-runs/2026-09-15-admission-selfhost-docs-linter" \
  --record records/2026-09-15-admission-selfhost-docs-linter.json \
  --out "$SCRATCH/census-verify" --grade-root "$SCRATCH/census-grades" ; echo "exit=$?"
```

Expected: `exit=0`, and `$SCRATCH/census-verify/selfhost-docs-linter/table.md` with one row per cell of that night. Then check three things against committed evidence and report any difference rather than tuning a rule to it:

- the per-cell `code`/`verdict` pairs match `records/2026-09-15-admission-selfhost-docs-linter.result.json`;
- the own-green turns for any cell that also appears in `evidence/2026-09-15-finishing-counterfactual/table.md` or `debug/table.md` are the same turns;
- `classes.md`'s eight class columns are empty, and no row carries a filled primary.

Run it once more against a second retained night (`~/satyrn-runs/2026-09-15-admission-selfhost-run-record-gate` with its record) to prove the night and record are really arguments. Nothing is written into `~/satyrn-runs`, into `evidence/2026-09-15-finishing-counterfactual/`, or into the checkout outside `$SCRATCH`; confirm with `git status --porcelain` printing nothing.

- [ ] **Step 7: Clean the verification outputs, then provenance, gates and commit**

```bash
rm -rf "$SCRATCH/census-verify" "$SCRATCH/census-grades" evidence/2026-09-16-census/work
uv run python tools/provenance.py new src/satyrn_evals/census_classify.py evidence/2026-09-16-census/classify.py evidence/2026-09-16-census/.gitignore tests/test_census_classify.py
just gates; echo "gates=$?"
git add src/satyrn_evals/census_classify.py evidence/2026-09-16-census/classify.py evidence/2026-09-16-census/.gitignore tests/test_census_classify.py PROVENANCE.md
git commit -m "Census classification: the pure class evidence in the package, and a night driver that takes a night and a record"
```

Expected: `gates=0`. No census output is committed here — the night has not run.

---

### Task 9: The five records, the launch script, and the operator checklist

Design section 5. Frozen and committed in daylight; the maintainer starts the script.

**Files:**
- Create: `records/2026-09-16-census-agentclinic-repair-depth-3.json` and four more
- Create: `scripts/census_night.sh`
- Modify: `ROADMAP.md` (the R0 row), `PROVENANCE.md`

**Interfaces:**
- Consumes: Tasks 1–7's harness, Tasks 4–6's tasks and their `validity` blocks.
- Produces: five frozen records and one script the maintainer runs.

- [ ] **Step 1: Refuse to write a record for a task that did not pass validity**

Before anything else, run:

```bash
uv run python - <<'PY'
import json, sys
from pathlib import Path
from satyrn_evals.qualify import CENSUS_TASKS

bad = []
for task in CENSUS_TASKS:
    body = json.loads((Path("src/satyrn_evals/tasks") / task / "manifest.json").read_text(encoding="utf-8"))
    validity = body.get("validity")
    if not validity or validity.get("passed") is not True:
        bad.append((task, validity))
for task, validity in bad:
    print(f"no census record for {task}: validity {validity}", file=sys.stderr)
raise SystemExit(1 if bad else 0)
PY
echo "validity=$?"
```

Expected: `validity=0`. A non-zero exit stops this task: design section 4 says a task that fails the check does not run in the census.

- [ ] **Step 2: Write the five records**

One per task, in this order, each chaining to the previous one's result. `PREV0` is the most recently committed result in `records/` before the census — find it with `git log -1 --name-only -- records | grep result` and paste the path.

```bash
AUTH='maintainer-approved census, spec 2026-09-15-release-two-census-design.md'
RULE='none for outcomes: release-two admission is decided in section 8 of 2026-09-15-release-two-census-design.md from the classified table, not from a pass count'
PREV0='records/2026-09-15-route-proof-selfhost-run-record-gate.result.json'   # replace with the real last committed result

new() {  # new TASK RUNG PREVIOUS
  uv run satyrn-evals record new \
    --output "records/2026-09-16-census-$1.json" --task "$1" --rung "$2" \
    --arm baseline --model omlx/Ornith-1.5-9B-MLX-8bit \
    --n 6 --k 3 --purpose admission --isolation isolated --mode batch \
    --max-minutes 240 --token-budget 48000 --turn-budget 72 --command-backstop 3000 \
    --previous-result "$3" --authority "$AUTH" --decision-rule "$RULE"
}

new agentclinic-repair-depth-3 R2       "$PREV0"
new selfhost-run-record-gate   R1-plan  records/2026-09-16-census-agentclinic-repair-depth-3.result.json
new selfhost-docs-linter       R1-plan  records/2026-09-16-census-selfhost-run-record-gate.result.json
new selfhost-cell-loop         R1-plan  records/2026-09-16-census-selfhost-docs-linter.result.json
new selfhost-speed-probe       R1-plan  records/2026-09-16-census-selfhost-cell-loop.result.json
```

`--max-minutes 240`: six cells at k = 3 is two waves, and the launcher starts a wave only while `elapsed + 3300 s` fits the wall clock, so 240 minutes holds both waves with room for the resume the design allows. It is well inside `batch`'s 720-minute cap and satisfies Ruling 12's gate (`3000 + 300 <= 14400`).

Then check every one:

```bash
for r in records/2026-09-16-census-*.json; do uv run satyrn-evals launch --check "$r"; echo "$r=$?"; done
uv run python -c "
import json, glob
for p in sorted(glob.glob('records/2026-09-16-census-*.json')):
    b = json.load(open(p))
    print(b['task'], b['rung'], b['n'], b['k'], b['token_budget'], b['turn_budget'], b['command_backstop_s'], b['mode'], b['isolation'], b['purpose'])
"
```

Expected: every `=0`, and five lines reading `<task> <rung> 6 3 48000 72 3000 batch isolated admission`. `launch --check` on records 2–5 reports the previous result is not committed; that is correct and expected before the night — the check that matters here is that each record loads and is inside its cadence. Record 1 must be clean.

- [ ] **Step 3: Write the launch script**

Create `scripts/census_night.sh`, of `admit.sh`'s shape, and `chmod +x` it:

```sh
#!/bin/sh
# census_night.sh -- run the 2026-09-16 pathology census, in order, from the evals checkout.
# One record per task; each record's result is committed before the next record launches,
# because a chained record's `previous_result` must be committed at launch.
# Exits with the last launcher exit code, or 2 before any launch.
set -u
TRAILER="Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
ARM=arms/baseline-ornith15-9b.json
TASKS="agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe"

# Settings provenance, both arms, as the cell user. A disagreement here means the
# oMLX entry or the cell's models.json was not moved to 16,000; nothing launches.
for a in arms/baseline-ornith15-9b.json arms/engine-ornith15-9b.json; do
  uv run python scripts/preflight_settings.py "$a" --cell > /dev/null || {
    echo "census: preflight_settings failed for $a" >&2; exit 2; }
done

S=2
for T in $TASKS; do
  R="records/2026-09-16-census-$T.json"; RES="records/2026-09-16-census-$T.result.json"
  [ -f "$R" ] || { echo "census: missing $R" >&2; exit 2; }
  if [ -f "$RES" ] && [ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")" = "complete" ]; then
    echo "census: $T already complete"; continue
  fi
  S=4
  while [ "$S" -eq 4 ]; do          # 4 is CAPPED: the launcher resumes the same record
    uv run satyrn-evals launch "$R" --arm "$ARM"; S=$?
  done
  if [ -f "$RES" ]; then
    STATUS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")
    git add "$RES" && { git diff --cached --quiet || git commit -qm "Census result: $T ($STATUS)

$TRAILER"; }
  fi
  [ "$S" -eq 0 ] || { echo "census: $T stopped with $S; the remaining records are not launched" >&2; break; }
done
echo "census EXIT: $S"; exit "$S"
```

Two deliberate differences from `admit.sh`: the record is never created by the script (records are frozen and committed in daylight, design section 5), and a non-zero launcher exit stops the remaining records rather than continuing — an established infrastructure failure is the only stop rule, and it is the launcher that establishes it.

- [ ] **Step 4: Prove the script's gates without launching**

```bash
sh -n scripts/census_night.sh; echo "syntax=$?"
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell > /dev/null; echo "settings=$?"
```

Expected: `syntax=0`. `settings` will be non-zero until the operator has changed the oMLX entry and the cell's `models.json` and restarted oMLX — that is the point of the check, and it is the operator's step, not this task's. Record which it printed.

- [ ] **Step 5: Record the state in `ROADMAP.md`**

Re-read `ROADMAP.md` first. In the R0 row's "Done when" cell, append one sentence: `Census: five records frozen 2026-09-16 (48,000 tokens, 72 turns, 3,000 s, k = 3, n = 6, Baseline only); the claim shape is chosen from the classified table (docs/superpowers/specs/2026-09-15-release-two-census-design.md section 8).` Nothing else changes. `wc -l ROADMAP.md` must print at most 150.

- [ ] **Step 6: Carry forward what this plan did not fix**

Append to `docs/superpowers/specs/2026-09-15-release-two-task-validity.md` a short `## Carried forward` section, or add it to the census page when it is written, naming exactly these:

1. **The Engine's `DELIVER_TIMEOUT_SECONDS` is 1800 and the record's backstop is not wired to it** (Ruling 3). An Engine cell under a 3,000 s backstop is stopped at 1,800 s inside `deliver` while a Baseline cell runs to 3,000 s. Fix before the first Engine record of release two; it is an arm-parity defect, not a census defect.
2. **Section 3.1's Pi-loop semantics are declared, not measured** (Ruling 9). The first census cell that shows a length-cut turn with tool calls ending a session contradicts them and is a finding.
3. **The census's `tripped_verdict` is a secondary with no denominator rule yet.** Section 8 decides whether it enters the claim; until then it is reported beside `verdict`, never instead of it.

- [ ] **Step 7: Provenance, gates and commit**

```bash
uv run python tools/provenance.py new scripts/census_night.sh records/2026-09-16-census-agentclinic-repair-depth-3.json records/2026-09-16-census-selfhost-run-record-gate.json records/2026-09-16-census-selfhost-docs-linter.json records/2026-09-16-census-selfhost-cell-loop.json records/2026-09-16-census-selfhost-speed-probe.json
just gates; echo "gates=$?"
git add scripts/census_night.sh records/2026-09-16-census-agentclinic-repair-depth-3.json records/2026-09-16-census-selfhost-run-record-gate.json records/2026-09-16-census-selfhost-docs-linter.json records/2026-09-16-census-selfhost-cell-loop.json records/2026-09-16-census-selfhost-speed-probe.json ROADMAP.md docs/superpowers/specs/2026-09-15-release-two-task-validity.md PROVENANCE.md
git commit -m "Census night: five frozen Baseline records at 48,000 tokens and 72 turns, and the launch script"
```

Expected: `gates=0`. Nothing is launched by this task.

---

## Operator commands

Everything in this section is the maintainer's, attended, after Task 9 is committed. No agent runs any of it.

**1. Move the served per-turn cap to 16,000 (design section 3.1).** The arm files are in git; the two configs below are local state and are not.

```bash
# oMLX: the config the server actually applies.
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home() / ".omlx" / "model_settings.json"
b = json.loads(p.read_text())
entry = b["models"]["Ornith-1.5-9B-MLX-8bit"]
print("before:", entry.get("max_tokens"))
entry["max_tokens"] = 16000
p.write_text(json.dumps(b, indent=2) + "\n")
print("after:", entry["max_tokens"])
PY

# Pi, as the cell user: maxTokens on the same model entry.
sudo -u satyrn-cell python3 - <<'PY'
import json, pathlib
p = pathlib.Path("~satyrn-cell/.pi/agent/models.json").expanduser()
b = json.loads(p.read_text())
for provider in b.get("providers", {}).values():
    for model in provider.get("models", []):
        if model.get("id") == "Ornith-1.5-9B-MLX-8bit":
            print("before:", model.get("maxTokens"))
            model["maxTokens"] = 16000
            print("after:", model["maxTokens"])
p.write_text(json.dumps(b, indent=2) + "\n")
PY
```

Adjust the Pi shape to whatever that file actually holds — read it first, change only `maxTokens` on that model entry, and leave `contextWindow` and `samplingParams` alone.

**2. Restart oMLX**, then prove both agree with both arms:

```bash
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell > /dev/null; echo "baseline=$?"
uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell > /dev/null; echo "engine=$?"
```

Expected: `baseline=0` and `engine=0`. A non-zero exit names the field and the two values; fix the config, never the arm file. **Nothing launches until both are 0.**

**3. Preflight the cell, and hunt.**

```bash
uv run satyrn-evals launch --preflight records/2026-09-16-census-agentclinic-repair-depth-3.json --arm arms/baseline-ornith15-9b.json; echo "preflight=$?"
```

Expected: `preflight=0`, and the printed JSON's `problems` is empty. This runs the root-anchored hunt as the cell user; a hit is grader material reachable from `/` and stops the night.

**4. Confirm the cells root is empty and the tree is clean.**

```bash
sudo ls -la /Users/Shared/satyrn-cells/ | head
git status --porcelain; echo "dirty=$?"
git log --oneline -1
```

Expected: no leftover worktree parents under the cells root beyond the committed engine export; `git status --porcelain` prints nothing; the head is Task 9's commit. A record must be frozen — tracked and unchanged against `HEAD` — or `launch` refuses it.

**5. Start the night.**

```bash
sh scripts/census_night.sh 2>&1 | tee "$HOME/satyrn-census-night.log"
```

Expected: about 7–8 hours for thirty cells (design section 5). The script commits each task's result before launching the next, because a chained record's `previous_result` must be committed at launch. A capped record resumes on the next launch of the same record; nothing restarts from zero and no cell is replaced. An `EXIT:` other than 0 means the launcher established an infrastructure failure and the remaining records were not launched — diagnose, repair, re-run the script, and it skips the tasks already complete.

**6. In the morning: commit the results, then classify.**

```bash
git status --porcelain -- records
git add records/2026-09-16-census-*.result.json && git commit -m "Census results: five Baseline records, 2026-09-16"
for T in agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py \
    --night "$HOME/satyrn-runs/2026-09-16-census-$T" \
    --record "records/2026-09-16-census-$T.json" \
    --grade-root "$HOME/satyrn-census-grades"
  echo "$T=$?"
done
```

Expected: five `=0` lines, and `evidence/2026-09-16-census/<task>/{cells.json,table.md,classes.md}` for each. The eight class columns in `classes.md` are empty: filling them is the attended review, argued from the reconstruction and cited by turn (design section 7). Then the census page, `evidence/2026-09-16-census/README.md`, ≤ 120 lines with a fenced recompute block (Ruling 10), and the section 8 decision sitting.

---

## Self-review against the spec

- **Section 3.1, per-turn cap.** Task 1: both arm files, `length_stops`, fixtures in both directions including the `turn_end` non-double-count. The Pi-loop semantics are declared, not verified (Ruling 9). Operator commands 1–2 carry the oMLX and Pi halves and the `preflight_settings --cell` gate.
- **Section 3.2, tripped worktrees graded.** Task 2: harvest at teardown, grade through the OK path, `tripped_verdict` never a pass, both of the spec's fixtures.
- **Section 3.3, the backstop as a record field.** Task 3, with the launcher's per-cell estimate following it (Ruling 11) and a non-vacuous gate (Ruling 12).
- **Section 3.4, k = 3.** Carried unchanged; the census records write `--k 3` (Task 9). Nothing re-measures it.
- **Section 4, task changes.** Task 4 (R2), Task 5 (the prompt-edit mechanism and the two edits, the re-cut, `cut_task.py check` and `qualify` for all five), Task 6 (validity, and the `pyproject.toml` branch). Digests of depth-2 and the floor tasks are proved unmoved by Task 5 Step 7.
- **Section 5, the night.** Task 9: five records with every value from the table, the launch script, the operator checklist. The design's `admit.sh` shape is kept; the record-creating half is deliberately dropped (records are frozen in daylight).
- **Section 6, what every cell records.** Task 1 (`length_stops`), Task 7 (tool span, exploration turns, biggest turn and share, self stop), Task 2 (`tripped_verdict`). The offline four are Task 8's (Ruling 16). Whole-attempt seconds is offline (Ruling 8).
- **Section 7, the day after.** Task 8: the pure evidence in the package, the night driver under `evidence/2026-09-16-census/`, eight empty class columns, both readings of the finish-on-green counterfactual at the 32k line, verified on retained cells only.
- **Section 8, the decision.** Not in this plan: it is the maintainer's attended sitting after the night.
- **Section 10, rules carried.** Isolation, launcher-only inference, frozen committed records, no Docker or sandbox, results written only by their tools, commit per task with explicit paths, never push or merge — all in the Global Constraints.
