# Finishing counterfactual — analysis script and decision run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-15 against evals `release-one` at `3f5a8a9` (the pre-registration commit).** The spec left some details open; each is decided below as a Ruling for the maintainer to review. Every test and the whole debug phase below were run in a scratch clone at `3f5a8a9`, reading `~/satyrn-runs` read-only, before hand-back (see "Verification before hand-back"). No decision cell was replayed, graded or parsed while planning. Two tasks.

**Goal:** One offline script answers the pre-registered question: if a retained cell had stopped at its first Engine-observable green, how many within-budget passes would that add and how many would it break? The script writes `cells.json`, `table.md` and `decision.txt`, and one attended run turns them into the section 5 decision.

**Architecture:** `evidence/2026-09-15-finishing-counterfactual/counterfactual.py` extends the release-one `reconstruct.py` replay. It has a pure top half: event steps, the section 3 source-edit, own-green and budget rules, bash replay planning, the section 4 outcome, fidelity and unmeasured rules, and the section 5 tally and decision. The impure bottom half copies the task base into a git-ignored scratch tree, replays landed writes, harvests the patch with the harness's own `build_cumulative_patch`, and grades it with `satyrn-evals grade` outside any Python project. `tests/test_finishing_counterfactual.py` loads the script by path and tests only the pure half, in the default tier. Task 1 builds and verifies it on the debug set. Task 2 holds the attended steps: Opus's line-by-line review, the one decision run, and the result.

**Tech Stack:** Python 3.14, uv, pytest, ruff, just, git. Reused evals code: `satyrn_evals.cell_evidence.runs_pytest` (plus its lexer `_segments`, `_program`, `_UV_RUN_VALUE_FLAGS`), `satyrn_evals.budget.UsageCounter`, `satyrn_evals.session_patch.build_cumulative_patch` and `RESIDUE_EXCLUDES`, `satyrn_evals.workspace.GIT_SAFETY_CONFIG`, and the `satyrn-evals grade` CLI.

**Spec:** `docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md` (commit `3f5a8a9`). Sections 2–5 are frozen and this plan implements them as written; section numbers are cited throughout. Bound by `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`. Starting code: `evidence/2026-09-15-release-one-outcome/reconstruct.py` (method in its `README.md`) and `cells.py`.

## Rulings

1. **Tests live in `tests/test_finishing_counterfactual.py`, loading the script by path.** The evidence directory is not a package, its name is not importable, and `pyproject.toml` excludes `evidence` from ruff and pyrefly. A test under `tests/` runs in `just gates`, is linted, and inherits the spawn tripwire, so the pure functions are proven with no subprocess. There is precedent for tests importing non-package tooling (`tests/test_doc_caps.py` imports `tools.lint_docs`). The script registers itself in `sys.modules` before `exec_module`, which slotted dataclasses need.
2. **"The first test run after the first source edit whose recorded result is green" means the first green run.** Among test runs whose `tool_execution_end` comes after the first source edit's `tool_execution_end` in stream order, the trigger is the first that is green. An earlier non-green run does not end the search.
3. **Source edit (section 3).** A `write` or `edit` counts only when its `tool_execution_end` is not an error ("landed" applies to both). The path is taken from `tool_execution_start` args and made worktree-relative against the transcript's `session` cwd (with the `/private` alias), falling back to the `/worktree/` split `reconstruct.py` used. The test-file rule is the spec's exactly: basename `test_*.py` or `*_test.py`, or any parent component `tests`. It is not `diff_filter.is_test_path`, which also names `conftest.py`. A replayed bash write counts when the file digests of the scratch tree before and after its replay differ on a non-test source file.
4. **A green `self_test` (section 3, "ok true and no failed ids").** The Engine's `self_test` details carry `{satyrn, ok, code, result: {exit_code, output, truncated, timed_out}}` and no failed-id list (`satyrn-engine packages/engine/runner.ts`, `successResult`), and `ok` is true for any completed run. So green means: not `isError`, `details.ok` true, `result.exit_code` 0, not `timed_out`, and no pytest summary line in the text with a failed or error count. A bash command the Engine redirected to `self_test` is judged by the bash rule, from its original command and its result text.
5. **The pytest summary line.** A summary line is a line, ANSI colour stripped, of the form `[=…] N word[, N word…] in S.SSs …`. Green needs at least one such line, at least one with `passed` ≥ 1, and no line with `failed`, `error` or `errors` above 0. `xfailed`, `xpassed`, `skipped`, `deselected` and `warnings` are not failures. When a command prints several summary lines, all must be clean.
6. **The budget check is evals' own count at the green's end event.** `UsageCounter` is fed every event up to and including the green's `tool_execution_end`: turns are `turn_start` events, and tokens are the assistant `message_end` `usage.output` sum. This includes the trigger turn's own assistant message. Within budget is tokens ≤ 32,000 and turn ≤ 48. A first green over budget means no trigger; there is no search for a later one, which could only be further over.
7. **"The worktree as it stood at the end of the trigger turn"** is every step whose turn count equals the trigger's, including calls that finished after the green in that turn.
8. **Harvest and grade exactly as the harness does.** The patch is `build_cumulative_patch(work, base, os.environ, exclude=RESIDUE_EXCLUDES)` over the whole scratch tree, as `attempt_pi.harvest_patch` does. It is not restricted to `source_paths`, as `reconstruct.py` was, so the allowlist and `ignored_paths` bite as they did in the harness. `satyrn-evals grade TASK patch.diff --receipt receipt.json` then grades it with the current manifest. The verdict is read from the receipt, never from the exit status. Every decision record's `task_tree_sha256` matches the current task tree (checked at `3f5a8a9`), so "current manifest" is the manifest the decision cells ran under.
9. **Grading runs outside any Python project; replay trees stay under the script's directory.** pytest reads the nearest ancestor config and every ancestor `conftest.py`. In verification, grading under the checkout made every agentclinic grade `unavailable`: node ids came back prefixed with the evals path. Receipts, patches and the grader's scratch therefore go under `--grade-root`, default `~/satyrn-counterfactual-grades/<phase>/`. The script refuses a root with any `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`, `setup.cfg` or `conftest.py` in it or above it. Section 6's "scratch worktrees under the script's own directory, git-ignored" still holds for the replay trees (`work/`). Each tree is deleted as soon as its patch is harvested, and `work/` is removed at start and exit, because a leftover base copy under the checkout breaks `just gates` collection (verified). Grading sets `UV_OFFLINE=1` (no network) and `TMPDIR` to the receipt folder (nothing in `/tmp`).
10. **Bash replay is `reconstruct.py`'s forms, narrowed to one write.** Two forms replay. The first is a `cat >`/`cat >>` heredoc in either word order (`cat > f <<EOF` or `cat <<EOF > f`), up to its terminator line. The second is a single simple `sed -i`, `printf … >` or `echo … >` command. Either way, the target must be relative and inside the tree once the worktree prefix is removed, and a leading `cd` is stripped only when it enters the worktree itself (`.`, `"$(pwd)"`, `$PWD` or the session cwd). The replay runs under `/bin/bash -c` in the scratch tree with `PATH`, `HOME` set to the tree and `TMPDIR` set to `work/`, and a 10 s timeout. Whatever follows a heredoc terminator is the remainder, and it is never run. A replayable write is replayed even when the tool result is an error, because the exit status belongs to the whole command, typically a later test run. A replay that exits non-zero where the original did not is a skipped writer.
11. **"A bash command … that could have written inside `source_paths`" (section 4)** is decided lexically per simple command, with quoted arguments and heredoc bodies treated as data. These always could write: a `git` subcommand in `apply am checkout restore reset stash mv rm cherry-pick revert merge pull switch clean`, and `ruff format` or `ruff check --fix` without `--check`/`--diff`. These could when a target resolves inside `source_paths`: a redirection target, a `tee mv rm touch truncate patch` operand, a `cp install ln rsync` destination, a `sed -i`/`perl -i` operand, or a `dd of=`. Resolution follows `cd`s earlier in the same command, and `/`-paths resolve against the session cwd. A Python file write anywhere in the text (`write_text(`, `write_bytes(`, `.write(` other than `stdout`/`stderr`, `open(…'w'|'a'|'x')`, `shutil.`, `os.rename|replace|remove|unlink(`) could write when the text names a source path. This is conservative: over-flagging costs only unmeasured cells, and unmeasured cells are listed.
12. **Skips and anchor misses count through the end of the trigger turn, and only when a counted trigger exists.** The spec says "before the trigger turn". The graded state is the end of that turn, so a skip inside it is just as able to change the verdict. With no counted trigger the cell keeps its actual outcome, whatever the replay skipped.
13. **An edit whose tool result succeeded but whose anchor the replay cannot find is "replay raises" (section 4).** It is recorded per turn and counted like a skip (Ruling 12). Any exception in replay or grading is caught per cell and recorded as `raised: …`.
14. **Fidelity (section 4)** compares the receipt verdict string with `attempt.json`'s `verdict`. "Graded" means that verdict is `pass`, `fail` or `unavailable`. It is checked for every graded cell, with or without a trigger. A failed fidelity check is unmeasured and counts as no change.
15. **Section 5 gap, resolved before the run.** The case "no budget-shaped task qualifies, yet one has net rescues ≥ 1 while `insufficient`" is **Verify**, by the maintainer's pre-run amendment (spec section 7.1). `decide` implements it and a test covers it.
16. **The cell sets are the spec's constants, and the decision phase checks them against the records before measuring.** Section 2's attempt ids, recorded `(code, verdict)` pairs, budget-shaped tasks and floor tasks are literals. `--phase decision` refuses to measure unless every `attempt.json` matches its row and the codes select exactly the spec's budget-shaped tasks. It also refuses when `cells.json` already exists: section 6 allows one run, and a re-run after a bug is a deliberate, recorded act. `--phase debug` refuses any decision id before reading anything, and the module asserts the two sets are disjoint.
17. **The Engine column comes from the debug phase.** Engine cells are "reported, outside the decision" (section 2). `--phase debug` writes `debug/cells.json` and `debug/table.md` with the same stamp. Task 2 runs it at the reviewed commit just before the decision phase, and both are committed together.
18. **The stamp** is `git rev-parse HEAD`, a dirty flag (uncommitted changes under `src/` or to the script), and the command line. It heads `cells.json`, `table.md` and `decision.txt`. A dirty stamp on a decision output is a review failure.
19. **The lexer is reused, not copied.** Beside `runs_pytest`, the script imports `cell_evidence`'s private `_segments`, `_program` and `_UV_RUN_VALUE_FLAGS`, so heredoc and quoting rules match the evidence code. `cell_evidence` itself is not modified.

## Global Constraints

- **Roles: Sonnet implements, Opus reviews, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer for Task 1. Opus's review in Task 2 is line by line against spec sections 3–5 and gates the decision run.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **Decision cells are never touched before the review gate.** The 24 attempt ids in spec section 2 (`971281 021584 082295 700050 388294 448568 519278 028222 147562 204433 270586 970283 812248 870439 937944 424626 688090 746232 816670 501161 523251 575297 634454 616367`) are not replayed, graded, parsed for own-green, or printed from, except by Task 2's decision-run step. Prototyping and checking use the debug set only: the 2026-09-14 self-hosted nights (run-record-gate `490384 549012 618278 511653`, guard-prefixes `249635 305323 372105 309486`, review-script `714610 770940 840545 624725`) and the Engine cells (route-proof-b depth-3 `808698`, route-proof run-record-gate `296145`, route-proof docs-linter `859943`, misleading-locus dev `117091 172304 140540 201516`).
- **No inference, no network.** No model, no `launch`, no oMLX request. Grades run with `UV_OFFLINE=1`.
- **Nothing under `/Users/Shared` is read or written; `~/satyrn-runs` is read-only; nothing is written to `/tmp` or `/private/tmp`.** Replay trees go under `evidence/2026-09-15-finishing-counterfactual/work/` (git-ignored, deleted after use). Receipts go under `~/satyrn-counterfactual-grades/` (Ruling 9).
- **Old evidence is untouched.** `evidence/2026-09-15-release-one-outcome/` and every earlier worktree or scratch directory stay as they are.
- **Default test tier: no subprocess.** The audit hook in `tests/conftest.py` enforces it. The new tests call only the script's pure functions, and `main` only on paths that return before any subprocess.
- **Every rule is tested in both directions.** That covers green and not green, within and over budget, rescue, harm and no change, fidelity pass and fail, sufficient and insufficient, each decision outcome, and the debug refusal next to a debug acceptance.
- **`evidence/` is excluded from ruff and pyrefly (`pyproject.toml`); `tests/` is not.** Run `uv run ruff check --fix tests/test_finishing_counterfactual.py` before gates.
- **Every task ends with `just gates` exit 0** (pytest, ruff, lint-docs, provenance; read the exit code, never pipe a gate). New files get `PROVENANCE.md` rows (`uv run python tools/provenance.py new <paths>`).
- **Commit per task on evals `release-one` with explicit paths only.** Another agent is committing docs to the same branch, so never `git add -A`, `git add .` or `git commit -a`. Never `--amend`, merge or push. A task whose gates are red is not committed. End each commit message with the session's attribution trailer.
- **Budget, verbatim from spec section 3:** "cumulative output tokens at that turn ≤ 32,000 and the turn number ≤ 48".
- **Result caps:** `evidence/2026-09-15-finishing-counterfactual/README.md` at most 120 lines with a fenced recompute command (spec section 6.4). The launcher-only results directory under `docs/` is not written. `ROADMAP.md` stays ≤ 150 lines.
- **Evals checkout** `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` (`EVALS`); starting point `release-one` at `3f5a8a9` plus whatever docs commits the other agent adds. All commands run from `EVALS`.

---

## File structure

```
evidence/2026-09-15-finishing-counterfactual/
  counterfactual.py    # T1: the script (pure rules above "# --- impure", replay/harvest/grade/CLI below)   (create)
  .gitignore           # T1: work/                                                                           (create)
  debug/cells.json     # T2: --phase debug output, the Engine column and the 2026-09-14 nights               (generated)
  debug/table.md       # T2: same, as a table                                                               (generated)
  cells.json           # T2: --phase decision output, 24 rows, stamped                                       (generated)
  table.md             # T2: the per-cell table, stamped                                                     (generated)
  decision.txt         # T2: per-task tallies and the section 5 decision, stamped                            (generated)
  README.md            # T2: the result, <= 120 lines                                                        (create)
tests/test_finishing_counterfactual.py   # T1: pure-rule tests, default tier                                  (create)
PROVENANCE.md                            # T1, T2: rows for new files                                         (modify)
ROADMAP.md                               # T2: one note in the R0 row                                         (modify)
```

The script's public names, used by the tests and by Task 2's reviewer:

| name | kind | purpose (spec section) |
|---|---|---|
| `CellSpec(task, run, arm, attempt, group)` | dataclass | one cell (2) |
| `DECISION`, `DEBUG`, `DECISION_IDS`, `RECORDED`, `BUDGET_SHAPED`, `FLOOR` | constants | the cell sets and recorded codes (2) |
| `select_cells(phase, only=()) -> tuple[CellSpec, ...]`; `DecisionCellRefused` | function; exception | phase selection and refusal (6.2) |
| `Step(index, turn, output_tokens, name, args, is_error, text, details)`; `parse_events`, `session_cwd`, `steps_of` | dataclass; functions | tool completions with evals' counts (3) |
| `tree_path`, `is_test_file`, `in_source_paths`, `is_source_file`, `source_edit_indices` | functions | source edit (3) |
| `summary_lines`, `pytest_output_green`, `self_test_green`, `is_test_run`, `is_green` | functions | own-green (3) |
| `Trigger(step, turn, output_tokens, route, within_budget)`; `within_budget`, `find_trigger` | dataclass; functions | trigger and budget (3) |
| `strip_cd`, `BashPlan(replay, remainder)`, `plan_bash`, `mentions_source`, `could_write_source` | functions | replay forms and skipped writers (3, 4) |
| `actual_pass`, `fidelity`, `unmeasured_reasons`, `counterfactual_pass`, `change` | functions | outcomes, fidelity, unmeasured (4) |
| `TaskTally(task, cells, rescues, harms, unmeasured)` with `.net`, `.insufficient`; `tally`, `budget_shaped`, `decide` | dataclass; functions | net rescues and decision (4, 5) |
| `project_markers`, `replay`, `grade`, `cell_dir`, `measure`, `stamp`, `table`, `main` | functions | impure half and CLI (6.2) |

---

### Task 1: The counterfactual script, its pure-rule tests, and a verified debug phase

**Files:**
- Create: `evidence/2026-09-15-finishing-counterfactual/counterfactual.py`
- Create: `evidence/2026-09-15-finishing-counterfactual/.gitignore`
- Create: `tests/test_finishing_counterfactual.py`
- Modify: `PROVENANCE.md` (three rows)

**Interfaces:**
- Consumes: `satyrn_evals.cell_evidence.runs_pytest(command: str) -> bool`, `_segments(command: str) -> list[list[str]]`, `_program(words) -> tuple[str, list[str]]`, `_UV_RUN_VALUE_FLAGS`; `satyrn_evals.budget.UsageCounter` (`feed_event`, `.turns`, `.output_tokens`); `satyrn_evals.session_patch.build_cumulative_patch(worktree, base_commit, environment, *, exclude) -> PatchCapture` and `RESIDUE_EXCLUDES`; `satyrn_evals.workspace.GIT_SAFETY_CONFIG`; the `satyrn-evals grade TASK PATCH --receipt RECEIPT` CLI (verdict in the receipt JSON's `verdict`).
- Produces: the CLI `uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase debug|decision [--cell SUFFIX]... [--grade-root DIR]`, exit 0 on a completed run and 2 on any refusal. It also produces the output files named in "File structure". The row keys in `cells.json` → `cells[]` are `task group run arm attempt code harness_verdict actual applied trigger trigger_verdict final_replay_verdict fidelity counterfactual change unmeasured skipped_writer_turns anchor_miss_turns`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_finishing_counterfactual.py`:

```python
"""Pure rules of evidence/2026-09-15-finishing-counterfactual/counterfactual.py.

The script lives in a dated evidence directory (not an importable package),
so it is loaded by path. Every test here is default tier: synthetic event
streams and strings, no subprocess, no ~/satyrn-runs.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "evidence" / "2026-09-15-finishing-counterfactual" / "counterfactual.py"
_SPEC = importlib.util.spec_from_file_location("finishing_counterfactual", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
cf = importlib.util.module_from_spec(_SPEC)
sys.modules["finishing_counterfactual"] = cf
_SPEC.loader.exec_module(cf)

CWD = "/Users/Shared/satyrn-cells/a/worktree"
SOURCES = ("src/satyrn_evals/run_record.py", "src/satyrn_evals/cli.py", "tests")


# --- synthetic Pi --mode json streams ------------------------------------------


def turn() -> dict:
    return {"type": "turn_start"}


def assistant(output: int) -> dict:
    return {"type": "message_end", "message": {"role": "assistant", "usage": {"output": output}, "content": []}}


def call(call_id: str, name: str, args: dict, text: str = "", *, error: bool = False, details: object = None) -> list[dict]:
    result: dict = {"content": [{"type": "text", "text": text}]}
    if details is not None:
        result["details"] = details
    return [
        {"type": "tool_execution_start", "toolCallId": call_id, "toolName": name, "args": args},
        {"type": "tool_execution_end", "toolCallId": call_id, "toolName": name, "result": result, "isError": error},
    ]


def self_test_details(exit_code: int, *, ok: bool = True, timed_out: bool = False) -> dict:
    return {"satyrn": True, "ok": ok, "code": "OK", "result": {"exit_code": exit_code, "output": "", "truncated": False, "timed_out": timed_out}}


def stream(*chunks: dict | list[dict]) -> list[dict]:
    events: list[dict] = [{"type": "session", "cwd": CWD}]
    for chunk in chunks:
        events.extend(chunk if isinstance(chunk, list) else [chunk])
    return events


EDIT_SOURCE = {"path": "src/satyrn_evals/run_record.py", "edits": [{"oldText": "a", "newText": "b"}]}
PYTEST = {"command": "uv run pytest tests/test_run_record.py -q"}


# --- phase selection -----------------------------------------------------------


def test_debug_phase_refuses_a_decision_attempt_id() -> None:
    with pytest.raises(cf.DecisionCellRefused, match="971281"):
        cf.select_cells("debug", ("971281",))


def test_debug_phase_refuses_a_decision_id_mixed_with_debug_ids() -> None:
    with pytest.raises(cf.DecisionCellRefused, match="028222"):
        cf.select_cells("debug", ("490384", "028222"))


def test_debug_phase_accepts_a_debug_id() -> None:
    assert [c.attempt for c in cf.select_cells("debug", ("490384",))] == ["490384"]


def test_debug_phase_without_a_filter_reads_only_debug_cells() -> None:
    cells = cf.select_cells("debug")
    assert len(cells) == 19
    assert not {c.attempt for c in cells} & cf.DECISION_IDS


def test_the_cli_refuses_a_decision_id_in_debug_before_reading_anything(capsys: pytest.CaptureFixture[str]) -> None:
    assert cf.main(["--phase", "debug", "--cell", "616367"]) == 2
    assert "refuses decision attempt ids: 616367" in capsys.readouterr().err


def test_decision_phase_is_exactly_the_spec_table_and_takes_no_filter() -> None:
    cells = cf.select_cells("decision")
    assert len(cells) == 24 and {c.attempt for c in cells} == cf.DECISION_IDS
    with pytest.raises(ValueError, match="refused"):
        cf.select_cells("decision", ("971281",))


# --- section 3: source edits ---------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/test_cli.py", True),
        ("tools/hooks/test_guard.py", True),
        ("pkg/guard_test.py", True),
        ("tests/conftest.py", True),
        ("src/satyrn_evals/cli.py", False),
        ("tools/testing.py", False),
    ],
)
def test_test_file_rule(path: str, expected: bool) -> None:
    assert cf.is_test_file(path) is expected


def test_a_source_file_is_inside_source_paths_and_not_a_test() -> None:
    assert cf.is_source_file("src/satyrn_evals/cli.py", SOURCES)
    assert not cf.is_source_file("tests/test_cli.py", SOURCES)
    assert not cf.is_source_file("src/satyrn_evals/errors.py", SOURCES)


def test_tree_path_relativizes_the_worktree_and_drops_outside_paths() -> None:
    assert cf.tree_path(f"{CWD}/src/satyrn_evals/cli.py", CWD) == "src/satyrn_evals/cli.py"
    assert cf.tree_path(f"/private{CWD}/app.py", CWD) == "app.py"
    assert cf.tree_path("./app.py", CWD) == "app.py"
    assert cf.tree_path("/tmp/dbg.py", CWD) is None
    assert cf.tree_path("../escape.py", CWD) is None


def test_landed_writes_and_edits_to_source_files_are_source_edits() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(10),
        call("a", "write", {"path": f"{CWD}/src/satyrn_evals/cli.py", "content": "x"}, "Successfully wrote"),
        call("b", "edit", EDIT_SOURCE, "Successfully replaced"),
    ))
    assert cf.source_edit_indices(steps, SOURCES, CWD, {}) == [0, 1]


def test_test_files_errors_and_outside_paths_are_not_source_edits() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(10),
        call("a", "write", {"path": "tests/test_cli.py", "content": "x"}),
        call("b", "edit", EDIT_SOURCE, "ANCHOR_MISSING", error=True),
        call("c", "write", {"path": "/tmp/dbg.py", "content": "x"}),
        call("d", "write", {"path": "src/satyrn_evals/cli.py", "content": "x"}, "failed", error=True),
    ))
    assert cf.source_edit_indices(steps, SOURCES, CWD, {}) == []


def test_a_replayed_bash_write_counts_only_when_it_touched_a_source_file() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(10),
        call("a", "bash", {"command": "cat > tests/test_x.py <<EOF\nx\nEOF\n"}),
        call("b", "bash", {"command": "cat > src/satyrn_evals/cli.py <<EOF\nx\nEOF\n"}),
    ))
    touched = {0: ("tests/test_x.py",), 1: ("src/satyrn_evals/cli.py",)}
    assert cf.source_edit_indices(steps, SOURCES, CWD, touched) == [1]


# --- section 3: own-green ------------------------------------------------------


@pytest.mark.parametrize(
    ("output", "green"),
    [
        ("....\n4 passed, 4 warnings in 0.49s\n", True),
        ("===== 10 passed, 2 xfailed in 1.20s =====", True),
        ("F...\n1 failed, 3 passed in 0.20s\n", False),
        ("===== 2 passed, 1 error in 1.00s =====", False),
        ("3 passed, 2 errors in 0.3s", False),
        ("5 deselected in 0.10s", False),
        ("no tests ran in 0.01s", False),
        ("....\n[100%]\n", False),
        ("2 passed in 0.1s\n1 failed, 1 passed in 0.1s", False),
    ],
)
def test_a_pytest_summary_is_green_only_with_a_pass_and_no_failure(output: str, green: bool) -> None:
    assert cf.pytest_output_green(output) is green


def test_a_bash_pytest_run_with_a_green_summary_is_green() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "bash", PYTEST, "4 passed in 0.5s")))
    assert cf.is_test_run(step) and cf.is_green(step)


def test_an_errored_bash_pytest_run_is_not_green_even_with_a_passing_summary() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "bash", PYTEST, "4 passed in 0.5s", error=True)))
    assert cf.is_test_run(step) and not cf.is_green(step)


def test_a_bash_command_that_does_not_run_pytest_is_not_a_test_run() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "bash", {"command": "cat log.txt"}, "4 passed in 0.5s")))
    assert not cf.is_test_run(step) and not cf.is_green(step)


def test_a_self_test_that_exited_zero_is_green() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "self_test", {}, "Test command exited 0\n4 passed in 0.5s", details=self_test_details(0))))
    assert cf.is_test_run(step) and cf.is_green(step)


@pytest.mark.parametrize(
    "details",
    [self_test_details(1), self_test_details(0, ok=False), self_test_details(0, timed_out=True), None],
)
def test_a_self_test_that_failed_refused_or_timed_out_is_not_green(details: dict | None) -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "self_test", {}, "Test command exited 1\n1 failed in 0.5s", details=details)))
    assert cf.is_test_run(step) and not cf.is_green(step)


def test_steps_carry_evals_turn_and_output_token_counts_at_their_end() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "bash", {"command": "ls"}),
        turn(), assistant(250), call("b", "bash", {"command": "ls"}),
        {"type": "message_end", "message": {"role": "user", "usage": {"output": 999}}},
    ))
    assert [(s.turn, s.output_tokens) for s in steps] == [(1, 100), (2, 350)]


# --- section 3: trigger and budget ---------------------------------------------


def test_the_trigger_is_the_first_green_run_after_the_first_source_edit() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "bash", PYTEST, "3 passed in 0.1s"),
        turn(), assistant(100), call("b", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("c", "bash", PYTEST, "1 failed, 2 passed in 0.1s", error=True),
        turn(), assistant(100), call("d", "bash", PYTEST, "3 passed in 0.1s"),
        turn(), assistant(100), call("e", "bash", PYTEST, "3 passed in 0.1s"),
    ))
    trigger = cf.find_trigger(steps, cf.source_edit_indices(steps, SOURCES, CWD, {}))
    assert trigger == cf.Trigger(step=3, turn=4, output_tokens=400, route="bash", within_budget=True)


def test_no_source_edit_means_no_trigger() -> None:
    steps = cf.steps_of(stream(turn(), assistant(100), call("a", "bash", PYTEST, "3 passed in 0.1s")))
    assert cf.find_trigger(steps, cf.source_edit_indices(steps, SOURCES, CWD, {})) is None


def test_no_green_run_after_the_edit_means_no_trigger() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("b", "bash", PYTEST, "1 failed in 0.1s", error=True),
    ))
    assert cf.find_trigger(steps, [0]) is None


@pytest.mark.parametrize(
    ("tokens", "turns", "within"),
    [(32_000, 48, True), (32_001, 3, False), (100, 49, False), (31_999, 47, True)],
)
def test_a_trigger_counts_only_within_the_budget(tokens: int, turns: int, within: bool) -> None:
    chunks: list[dict | list[dict]] = [turn(), assistant(tokens), call("a", "edit", EDIT_SOURCE, "ok")]
    chunks += [turn(), assistant(0)] * (turns - 1)
    chunks.append(call("b", "bash", PYTEST, "3 passed in 0.1s"))
    steps = cf.steps_of(stream(*chunks))
    trigger = cf.find_trigger(steps, [0])
    assert trigger is not None and (trigger.turn, trigger.output_tokens) == (turns, tokens)
    assert trigger.within_budget is within


# --- replay rules ----------------------------------------------------------------


def test_a_heredoc_write_replays_up_to_its_terminator_and_keeps_the_rest() -> None:
    plan = cf.plan_bash(f"cd {CWD} && cat > tools/hooks/guard.py << 'EOF'\nprint(1)\nEOF\nuv run pytest -q", CWD)
    assert plan.replay == "cat > tools/hooks/guard.py << 'EOF'\nprint(1)\nEOF\n"
    assert plan.remainder == "uv run pytest -q"


def test_a_word_first_heredoc_and_a_single_sed_replay() -> None:
    assert cf.plan_bash("cat <<EOF > app.py\nx\nEOF", CWD).replay == "cat <<EOF > app.py\nx\nEOF\n"
    assert cf.plan_bash("sed -i '' 's/a/b/' app.py", CWD).replay == "sed -i '' 's/a/b/' app.py"


@pytest.mark.parametrize(
    "command",
    [
        "cat > /tmp/dbg.py <<EOF\nx\nEOF",
        "cd tests && cat > test_x.py <<EOF\nx\nEOF",
        "echo x > app.py && uv run pytest",
        "cat > app.py <<EOF\nnever terminated",
        "python3 -c \"open('app.py','w').write('x')\"",
    ],
)
def test_other_bash_forms_do_not_replay(command: str) -> None:
    assert cf.plan_bash(command, CWD).replay is None


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -- .",
        "git stash",
        "uv run ruff format .",
        "uv run ruff check --fix src/",
        "echo x > src/satyrn_evals/cli.py && true",
        f"printf 'x' >> {CWD}/src/satyrn_evals/run_record.py; ls",
        "python3 -c \"open('src/satyrn_evals/cli.py','w').write(s)\"",
        "cp /tmp/fixed.py src/satyrn_evals/run_record.py",
        "sed -i '' 's/a/b/' src/satyrn_evals/cli.py && uv run pytest",
        "cd src/satyrn_evals && perl -i -pe 's/a/b/' cli.py && cd ../.. && uv run pytest",
        "mv src/satyrn_evals/run_record.py /tmp/r.bak; uv run pytest; mv /tmp/r.bak src/satyrn_evals/run_record.py",
        "uv run python - <<'EOF'\nfrom pathlib import Path\nPath('src/satyrn_evals/cli.py').write_text(s)\nEOF",
    ],
)
def test_unreplayed_bash_that_could_write_a_source_path(command: str) -> None:
    assert cf.could_write_source(command, SOURCES, CWD)


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest tests/ -q 2>&1 | tail -30",
        "cat src/satyrn_evals/cli.py > /tmp/cli.txt",
        "grep -n def src/satyrn_evals/cli.py > /dev/null",
        "python3 -c \"import sys; sys.stdout.write('hi')\"",
        "echo done > notes.txt",
        "sed -i 's/x/y/' /dev/null; grep -c to_dict tests/test_run_record.py",
        "touch .testfile && ls tools/hooks/guard.py && rm .testfile",
        "uv run python - <<'EOF'\nprint(decide('cp docs x'))\nEOF",
        "uv run ruff format --check src/",
        "cd /tmp && echo x > cli.py",
        "cp tests/its.py its.py",
    ],
)
def test_unreplayed_bash_that_could_not_write_a_source_path(command: str) -> None:
    assert not cf.could_write_source(command, SOURCES, CWD)


# --- section 4: outcomes, fidelity, unmeasured ----------------------------------


def test_actual_pass_needs_ok_and_pass() -> None:
    assert cf.actual_pass("OK", "pass")
    assert not cf.actual_pass("OK", "fail")
    assert not cf.actual_pass("BUDGET_EXCEEDED", None)


@pytest.mark.parametrize(
    ("harness", "replayed", "expected"),
    [
        ("pass", "pass", "pass"),
        ("fail", "fail", "pass"),
        ("unavailable", "unavailable", "pass"),
        ("pass", "fail", "fail"),
        ("fail", None, "fail"),
        (None, "pass", "unverifiable"),
    ],
)
def test_fidelity(harness: str | None, replayed: str | None, expected: str) -> None:
    assert cf.fidelity(harness, replayed) == expected


TRIGGER = cf.Trigger(step=5, turn=10, output_tokens=20_000, route="bash", within_budget=True)
NONE_SKIPPED = {"skipped_writer_turns": [], "anchor_miss_turns": [], "raised": None}


def test_a_failed_fidelity_check_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(fidelity_result="fail", harness_verdict="pass", final_verdict="fail", trigger=None, **NONE_SKIPPED)
    assert reasons == ["fidelity: harness pass, replay fail"]


def test_a_passing_fidelity_check_with_nothing_skipped_is_measured() -> None:
    assert cf.unmeasured_reasons(fidelity_result="pass", harness_verdict="pass", final_verdict="pass", trigger=TRIGGER, **NONE_SKIPPED) == []


def test_a_skipped_writer_or_anchor_miss_through_the_trigger_turn_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER,
        skipped_writer_turns=[4, 10], anchor_miss_turns=[7], raised=None,
    )
    assert reasons == ["skipped bash writer at turn 4", "skipped bash writer at turn 10", "replay raised: edit anchor missing at turn 7"]


def test_a_skipped_writer_after_the_trigger_or_without_a_counted_trigger_is_measured() -> None:
    late = {"skipped_writer_turns": [11], "anchor_miss_turns": [12], "raised": None}
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER, **late) == []
    early = {"skipped_writer_turns": [2], "anchor_miss_turns": [], "raised": None}
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=None, **early) == []
    over = cf.Trigger(step=5, turn=10, output_tokens=40_000, route="bash", within_budget=False)
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=over, **early) == []


def test_a_raise_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=None, skipped_writer_turns=[], anchor_miss_turns=[], raised="CalledProcessError: git")
    assert reasons == ["raised: CalledProcessError: git"]


def test_rescue_harm_and_no_change() -> None:
    assert cf.change(False, cf.counterfactual_pass(False, TRIGGER, [], "pass")) == "rescue"
    assert cf.change(True, cf.counterfactual_pass(True, TRIGGER, [], "fail")) == "harm"
    assert cf.change(True, cf.counterfactual_pass(True, TRIGGER, [], "pass")) == "none"
    assert cf.change(False, cf.counterfactual_pass(False, TRIGGER, [], "unavailable")) == "none"


def test_no_trigger_an_over_budget_trigger_or_unmeasured_keeps_the_actual_outcome() -> None:
    over = cf.Trigger(step=5, turn=10, output_tokens=40_000, route="bash", within_budget=False)
    assert cf.counterfactual_pass(False, None, [], None) is False
    assert cf.counterfactual_pass(False, over, [], "pass") is False
    assert cf.counterfactual_pass(True, TRIGGER, ["fidelity: harness pass, replay fail"], "fail") is True


# --- section 5 ---------------------------------------------------------------------


def test_budget_shaped_needs_two_budget_or_timeout_codes() -> None:
    assert cf.budget_shaped(["COMMAND_TIMEOUT", "BUDGET_EXCEEDED", "OK", "OK"])
    assert not cf.budget_shaped(["BUDGET_EXCEEDED", "OK", "OK", "OK"])


def test_the_spec_codes_select_the_spec_budget_shaped_tasks() -> None:
    shaped = [
        task for task in (*cf.BUDGET_SHAPED, *cf.FLOOR)
        if cf.budget_shaped([cf.RECORDED[c.attempt][0] for c in cf.DECISION if c.task == task])
    ]
    assert shaped == list(cf.BUDGET_SHAPED)


def test_more_than_one_unmeasured_cell_makes_a_task_insufficient() -> None:
    assert cf.tally("t", ["none"] * 4, [True, True, False, False]).insufficient
    assert not cf.tally("t", ["none"] * 4, [True, False, False, False]).insufficient
    assert cf.tally("t", ["rescue", "rescue", "harm", "none"], [False] * 4).net == 1


def tallies(**overrides: tuple[int, int, int]) -> dict:
    """task -> (rescues, harms, unmeasured); every other task all zeros."""
    return {t: cf.TaskTally(t, 4, *overrides.get(t.replace("-", "_"), (0, 0, 0))) for t in (*cf.BUDGET_SHAPED, *cf.FLOOR)}


def test_go_needs_two_qualifying_tasks_low_floor_harm_and_no_insufficient_floor() -> None:
    outcome, _ = cf.decide(tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_docs_linter=(2, 1, 1), selfhost_review_script=(0, 1, 1)))
    assert outcome == "go"


def test_verify_when_exactly_one_task_qualifies() -> None:
    assert cf.decide(tallies(selfhost_run_record_gate=(1, 0, 0)))[0] == "verify"


def test_verify_when_two_qualify_but_floor_harm_reaches_two() -> None:
    t = tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_run_record_gate=(1, 0, 0), selfhost_guard_prefixes=(0, 1, 0), agentclinic_repair_depth_2=(0, 1, 0))
    assert cf.decide(t)[0] == "verify"


def test_verify_when_two_qualify_but_a_floor_task_is_insufficient() -> None:
    t = tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_run_record_gate=(1, 0, 0), agentclinic_repair_depth_2=(0, 0, 2))
    assert cf.decide(t)[0] == "verify"


def test_an_insufficient_task_does_not_qualify() -> None:
    t = tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_run_record_gate=(2, 0, 2))
    assert cf.decide(t)[0] == "verify"


def test_not_the_lever_when_no_budget_shaped_task_nets_a_rescue() -> None:
    assert cf.decide(tallies(agentclinic_repair_depth_3=(1, 1, 0), selfhost_guard_prefixes=(3, 0, 0)))[0] == "not-the-lever"


def test_verify_when_the_only_net_rescue_is_on_an_insufficient_task() -> None:
    outcome, reason = cf.decide(tallies(selfhost_docs_linter=(1, 0, 2)))
    assert outcome == "verify" and "section 7.1" in reason


def test_the_table_row_marks_an_over_budget_trigger_and_joins_reasons() -> None:
    row = {
        "task": "t", "group": "engine", "attempt": "000001", "code": "BUDGET_EXCEEDED", "harness_verdict": None,
        "trigger": {"step": 1, "turn": 50, "output_tokens": 30_000, "route": "bash", "within_budget": False},
        "actual": "not-pass", "counterfactual": "not-pass", "change": "none", "fidelity": "unverifiable",
        "unmeasured": ["a", "b"],
    }
    text = cf.table([row], {"evals_commit": "abc", "evals_dirty": False, "command": "counterfactual.py --phase debug"})
    assert "| 50 (over budget) | 30000 |" in text and "| a; b |" in text
    assert json.dumps(row)  # rows stay JSON-serializable


def test_a_grade_root_under_a_python_project_is_found(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "grades").mkdir()
    assert cf.project_markers(tmp_path / "grades") == [tmp_path / "pyproject.toml"]


def test_a_grade_root_with_no_project_above_it_is_clean(tmp_path: Path) -> None:
    (tmp_path / "grades").mkdir()
    assert [m for m in cf.project_markers(tmp_path / "grades") if m.is_relative_to(tmp_path)] == []


def test_the_cli_refuses_a_grade_root_inside_the_evals_checkout(capsys: pytest.CaptureFixture[str]) -> None:
    assert cf.main(["--phase", "debug", "--cell", "490384", "--grade-root", str(cf.HERE / "work")]) == 2
    assert "pytest would read it while grading" in capsys.readouterr().err
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_finishing_counterfactual.py -q`
Expected: collection error, `FileNotFoundError: [Errno 2] No such file or directory: '…/evidence/2026-09-15-finishing-counterfactual/counterfactual.py'`.

- [ ] **Step 3: Write the script and its ignore file**

Create `evidence/2026-09-15-finishing-counterfactual/.gitignore` with exactly one line:

```
work/
```

Create `evidence/2026-09-15-finishing-counterfactual/counterfactual.py`:

```python
#!/usr/bin/env python3
"""The finishing counterfactual (pre-registration
docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md).

If a retained cell had stopped at its first Engine-observable green (spec
section 3), would the hidden suite have passed? Offline, from retained
transcripts only: no model, no network, nothing under /Users/Shared.
Scratch worktrees live under this directory's ``work/`` (git-ignored).

Run from the evals checkout:

    uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase debug
    uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase decision

``--phase debug`` reads only the cells outside the decision set and refuses
any decision attempt id. ``--phase decision`` reads exactly the 24 decision
cells, once, and writes cells.json, table.md and decision.txt.

Extends evidence/2026-09-15-release-one-outcome/reconstruct.py: the same
write/edit/heredoc replay, with the harvest and grade the harness uses.
Pure functions sit above the ``# --- impure ---`` line; the tests in
tests/test_finishing_counterfactual.py exercise only those.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from satyrn_evals.budget import UsageCounter
from satyrn_evals.cell_evidence import (
    _UV_RUN_VALUE_FLAGS,
    _program,
    _segments,
    runs_pytest,
)

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[1]
TASKS = EVALS / "src" / "satyrn_evals" / "tasks"
RUNS = Path.home() / "satyrn-runs"
WORK = HERE / "work"
# Grading runs where the harness grades: under no Python project. pytest reads
# the nearest ancestor config and every ancestor conftest.py, so a grade under
# this checkout would run the hidden suite with evals' own pytest settings.
DEFAULT_GRADE_ROOT = Path.home() / "satyrn-counterfactual-grades"
PROJECT_MARKERS = ("pyproject.toml", "pytest.ini", ".pytest.ini", "tox.ini", "setup.cfg", "conftest.py")

# Spec section 3: the budget a trigger must fall within.
TOKEN_BUDGET = 32_000
TURN_BUDGET = 48


@dataclass(frozen=True, slots=True)
class CellSpec:
    task: str
    run: str
    arm: str
    attempt: str  # the attempt directory's six-digit suffix
    group: str  # "decision", "nights-2026-09-14" or "engine"


def _cells(task: str, run: str, arm: str, group: str, attempts: str) -> tuple[CellSpec, ...]:
    return tuple(CellSpec(task, run, arm, a, group) for a in attempts.split())


# Spec section 2, decision table, in its row order.
DECISION: tuple[CellSpec, ...] = (
    *_cells("agentclinic-repair-depth-3", "2026-09-14-admission-agentclinic-repair-depth-3", "baseline", "decision", "971281 021584 082295 700050"),
    *_cells("selfhost-run-record-gate", "2026-09-15-admission-selfhost-run-record-gate", "baseline", "decision", "388294 448568 519278 028222"),
    *_cells("selfhost-docs-linter", "2026-09-15-admission-selfhost-docs-linter", "baseline", "decision", "147562 204433 270586 970283"),
    *_cells("selfhost-guard-prefixes", "2026-09-15-admission-selfhost-guard-prefixes", "baseline", "decision", "812248 870439 937944 424626"),
    *_cells("selfhost-review-script", "2026-09-15-admission-selfhost-review-script", "baseline", "decision", "688090 746232 816670 501161"),
    *_cells("agentclinic-repair-depth-2", "2026-09-14-admission-agentclinic-repair-depth-2", "baseline", "decision", "523251 575297 634454 616367"),
)
# Spec section 2, "recorded codes", as (code, verdict) in the same order.
RECORDED: dict[str, tuple[str, str | None]] = dict(
    zip(
        (c.attempt for c in DECISION),
        (
            ("COMMAND_TIMEOUT", None), ("BUDGET_EXCEEDED", None), ("OK", "fail"), ("BUDGET_EXCEEDED", None),
            *[("BUDGET_EXCEEDED", None)] * 4,
            ("BUDGET_EXCEEDED", None), ("OK", "pass"), ("BUDGET_EXCEEDED", None), ("BUDGET_EXCEEDED", None),
            *[("OK", "pass")] * 12,
        ),
        strict=True,
    )
)
BUDGET_SHAPED = ("agentclinic-repair-depth-3", "selfhost-run-record-gate", "selfhost-docs-linter")
FLOOR = ("selfhost-guard-prefixes", "selfhost-review-script", "agentclinic-repair-depth-2")

# Spec section 2, "reported, outside the decision".
DEBUG: tuple[CellSpec, ...] = (
    *_cells("selfhost-run-record-gate", "2026-09-14-admission-selfhost-run-record-gate", "baseline", "nights-2026-09-14", "490384 549012 618278 511653"),
    *_cells("selfhost-guard-prefixes", "2026-09-14-admission-selfhost-guard-prefixes", "baseline", "nights-2026-09-14", "249635 305323 372105 309486"),
    *_cells("selfhost-review-script", "2026-09-14-admission-selfhost-review-script", "baseline", "nights-2026-09-14", "714610 770940 840545 624725"),
    *_cells("agentclinic-repair-depth-3", "2026-09-15-route-proof-b-agentclinic-repair-depth-3", "engine", "engine", "808698"),
    *_cells("selfhost-run-record-gate", "2026-09-15-route-proof-selfhost-run-record-gate", "engine", "engine", "296145"),
    *_cells("selfhost-docs-linter", "2026-09-15-route-proof-selfhost-docs-linter", "engine", "engine", "859943"),
    *_cells("agentclinic-repair-misleading-locus", "2026-09-15-dev-before-agentclinic-repair-misleading-locus", "engine", "engine", "117091 172304"),
    *_cells("agentclinic-repair-misleading-locus", "2026-09-15-dev-after-agentclinic-repair-misleading-locus", "engine", "engine", "140540 201516"),
)
DECISION_IDS = frozenset(c.attempt for c in DECISION)
assert len(DECISION) == 24 and len(DECISION_IDS) == 24
assert not DECISION_IDS & {c.attempt for c in DEBUG}


class DecisionCellRefused(ValueError):
    """A debug-phase request named a decision attempt id."""


def select_cells(phase: str, only: tuple[str, ...] = ()) -> tuple[CellSpec, ...]:
    """The cells a phase may read. Debug refuses any decision id; decision takes no filter."""
    if phase == "debug":
        refused = sorted(set(only) & DECISION_IDS)
        if refused:
            raise DecisionCellRefused(f"--phase debug refuses decision attempt ids: {', '.join(refused)}")
        unknown = sorted(set(only) - {c.attempt for c in DEBUG})
        if unknown:
            raise ValueError(f"not a debug attempt id: {', '.join(unknown)}")
        return tuple(c for c in DEBUG if not only or c.attempt in only)
    if phase == "decision":
        if only:
            raise ValueError("--phase decision runs exactly the 24 decision cells; --cell is refused")
        return DECISION
    raise ValueError(f"unknown phase: {phase}")


# --- transcript steps ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Step:
    """One finished tool call, with the budget counted up to its end event."""

    index: int
    turn: int
    output_tokens: int
    name: str
    args: dict
    is_error: bool
    text: str
    details: object


def parse_events(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def session_cwd(events: list[dict]) -> str | None:
    return next(
        (e["cwd"] for e in events if e.get("type") == "session" and isinstance(e.get("cwd"), str) and e["cwd"]),
        None,
    )


def result_text(result: object) -> str:
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list):
        return ""
    return "\n".join(p["text"] for p in content if isinstance(p, dict) and isinstance(p.get("text"), str))


def steps_of(events: list[dict]) -> list[Step]:
    """Every ``tool_execution_end``, joined to its start's arguments, in stream order.

    Turns and output tokens are evals' own count (``budget.UsageCounter``) at
    the end event: one ``turn_start`` is a turn, an assistant ``message_end``
    adds ``usage.output``.
    """
    usage = UsageCounter()
    starts: dict[str, dict] = {}
    steps: list[Step] = []
    for event in events:
        usage.feed_event(event)
        kind = event.get("type")
        if kind == "tool_execution_start" and isinstance(event.get("toolCallId"), str):
            starts[event["toolCallId"]] = event.get("args") if isinstance(event.get("args"), dict) else {}
        elif kind == "tool_execution_end" and isinstance(event.get("toolName"), str):
            result = event.get("result")
            steps.append(
                Step(
                    index=len(steps),
                    turn=usage.turns,
                    output_tokens=usage.output_tokens,
                    name=event["toolName"],
                    args=starts.get(event.get("toolCallId"), {}),
                    is_error=event.get("isError") is True,
                    text=result_text(result),
                    details=result.get("details") if isinstance(result, dict) else None,
                )
            )
    return steps


# --- section 3: source edits --------------------------------------------------


def tree_path(path: str, cwd: str | None) -> str | None:
    """A tool path as a worktree-relative POSIX path, or None when outside the tree."""
    if not isinstance(path, str) or not path:
        return None
    if path.startswith("/"):
        canonical = posixpath.normpath(path.removeprefix("/private"))
        if cwd:
            root = posixpath.normpath(cwd.removeprefix("/private"))
            if canonical == root:
                return "."
            if canonical.startswith(root + "/"):
                return canonical[len(root) + 1 :]
        if "/worktree/" in canonical:
            return canonical.split("/worktree/", 1)[1]
        return None
    relative = posixpath.normpath(path)
    if relative == ".." or relative.startswith("../"):
        return None
    return relative


def is_test_file(path: str) -> bool:
    """Spec section 3: basename test_*.py or *_test.py, or a path under a tests directory."""
    parts = path.split("/")
    base = parts[-1]
    return (base.startswith("test_") and base.endswith(".py")) or base.endswith("_test.py") or "tests" in parts[:-1]


def in_source_paths(path: str, source_paths: tuple[str, ...]) -> bool:
    return any(path == entry or path.startswith(entry.rstrip("/") + "/") for entry in source_paths)


def is_source_file(path: str, source_paths: tuple[str, ...]) -> bool:
    return in_source_paths(path, source_paths) and not is_test_file(path)


def source_edit_indices(
    steps: list[Step], source_paths: tuple[str, ...], cwd: str | None, bash_touched: dict[int, tuple[str, ...]]
) -> list[int]:
    """Spec section 3 "source edit": a landed write, a non-error edit, or a replayed bash
    write, of a non-test file inside source_paths. ``bash_touched`` maps a replayed bash
    step's index to the tree paths its replay changed."""
    found = []
    for step in steps:
        if step.name in ("write", "edit"):
            path = tree_path(step.args.get("path", ""), cwd)
            if not step.is_error and path is not None and is_source_file(path, source_paths):
                found.append(step.index)
        elif step.name == "bash" and any(is_source_file(p, source_paths) for p in bash_touched.get(step.index, ())):
            found.append(step.index)
    return found


# --- section 3: own-green -----------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_SUMMARY = re.compile(r"^=*\s*((?:\d+ [a-z]+(?:, )?)+) in \d+(?:\.\d+)?s\b.*$")


def summary_lines(output: str) -> list[dict[str, int]]:
    """Each pytest summary line in ``output`` ("3 passed, 1 warning in 0.4s") as word -> count."""
    found = []
    for line in _ANSI.sub("", output).splitlines():
        match = _SUMMARY.match(line.strip())
        if match:
            counts = {}
            for part in match.group(1).split(", "):
                number, word = part.split(" ", 1)
                counts[word] = int(number)
            found.append(counts)
    return found


def pytest_output_green(output: str) -> bool:
    """A summary line exists, one reports at least one pass, and none reports failed or error."""
    lines = summary_lines(output)
    bad = ("failed", "error", "errors")
    return (
        bool(lines)
        and any(c.get("passed", 0) >= 1 for c in lines)
        and all(c.get(word, 0) == 0 for c in lines for word in bad)
    )


def self_test_green(step: Step) -> bool:
    """A self_test whose details say ok, exit 0, not timed out, and whose output names no failure."""
    details = step.details if isinstance(step.details, dict) else {}
    result = details.get("result") if isinstance(details.get("result"), dict) else {}
    return (
        step.name == "self_test"
        and not step.is_error
        and details.get("ok") is True
        and result.get("exit_code") == 0
        and result.get("timed_out") is not True
        and all(c.get(word, 0) == 0 for c in summary_lines(step.text) for word in ("failed", "error", "errors"))
    )


def is_test_run(step: Step) -> bool:
    return step.name == "self_test" or (step.name == "bash" and runs_pytest(str(step.args.get("command", ""))))


def is_green(step: Step) -> bool:
    if step.name == "self_test":
        return self_test_green(step)
    return (
        step.name == "bash"
        and runs_pytest(str(step.args.get("command", "")))
        and not step.is_error
        and pytest_output_green(step.text)
    )


@dataclass(frozen=True, slots=True)
class Trigger:
    step: int
    turn: int
    output_tokens: int
    route: str  # "self_test" or "bash"
    within_budget: bool


def within_budget(output_tokens: int, turn: int) -> bool:
    return output_tokens <= TOKEN_BUDGET and turn <= TURN_BUDGET


def find_trigger(steps: list[Step], source_edits: list[int]) -> Trigger | None:
    """Spec section 3: the first green test run after the first source edit."""
    if not source_edits:
        return None
    first_edit = min(source_edits)
    for step in steps:
        if step.index > first_edit and is_test_run(step) and is_green(step):
            return Trigger(step.index, step.turn, step.output_tokens, step.name, within_budget(step.output_tokens, step.turn))
    return None


# --- replay rules (pure) ------------------------------------------------------

_CD_PREFIX = re.compile(r"""^\s*cd\s+("[^"]*"|'[^']*'|\S+)\s*(?:;|&&)\s*""")
_HEREDOC_TARGET_FIRST = re.compile(r"""^cat\s*(?P<op>>>?)\s*(?P<target>\S+)\s*<<(?P<dash>-?)\s*(?P<q>['"]?)(?P<word>\w+)(?P=q)[ \t]*\n""")
_HEREDOC_WORD_FIRST = re.compile(r"""^cat\s*<<(?P<dash>-?)\s*(?P<q>['"]?)(?P<word>\w+)(?P=q)\s*(?P<op>>>?)\s*(?P<target>\S+)[ \t]*\n""")
_SIMPLE_WRITE = re.compile(r"""^(?:sed\s+-i|printf\s|echo\s)""")
_PY_WRITE = re.compile(r"write_text\(|write_bytes\(|(?<!stdout)(?<!stderr)\.write\(|open\([^)]*['\"][wax]|shutil\.|os\.(?:rename|replace|remove|unlink)\(")
_REDIRECTS = frozenset({">", ">>", ">|", "&>", "&>>"})
_LAST_OPERAND_WRITERS = frozenset({"cp", "install", "ln", "rsync"})
_EVERY_OPERAND_WRITERS = frozenset({"mv", "rm", "touch", "truncate", "tee", "patch"})
_GIT_WRITERS = frozenset({"apply", "am", "checkout", "restore", "reset", "stash", "mv", "rm", "cherry-pick", "revert", "merge", "pull", "switch", "clean"})


def strip_cd(command: str, cwd: str | None) -> str | None:
    """Drop a leading ``cd`` into the worktree itself; None when it enters anywhere else."""
    match = _CD_PREFIX.match(command)
    if not match:
        return command
    target = match.group(1).strip("'\"")
    if target in (".", "$(pwd)", "$PWD") or (cwd and tree_path(target, cwd) == "."):
        return command[match.end() :]
    return None


@dataclass(frozen=True, slots=True)
class BashPlan:
    """How a bash command replays: the shell text to run in the scratch tree (or
    None), and the remainder the replay does not run."""

    replay: str | None
    remainder: str


def plan_bash(command: str, cwd: str | None) -> BashPlan:
    """reconstruct.py's replayable forms, narrowed to one write: a ``cat >``/``cat >>``
    heredoc up to its terminator line, or a single simple ``sed -i``/``printf >``/
    ``echo >`` command. The target must be a relative path inside the tree once the
    worktree prefix is removed."""
    stripped = strip_cd(command, cwd)
    if stripped is None:
        return BashPlan(None, command)
    stripped = stripped.lstrip()
    if cwd:
        stripped = _unroot_head(stripped, cwd)
    heredoc = _HEREDOC_TARGET_FIRST.match(stripped) or _HEREDOC_WORD_FIRST.match(stripped)
    if heredoc:
        target = heredoc.group("target").strip("'\"")
        tabs = r"\t*" if heredoc.group("dash") else ""
        terminator = re.compile(rf"^{tabs}{re.escape(heredoc.group('word'))}[ \t]*$", re.M)
        end = terminator.search(stripped, heredoc.end())
        if end is None or not _inside(target):
            return BashPlan(None, command)
        cut = end.end() + 1 if end.end() < len(stripped) else end.end()
        return BashPlan(stripped[: end.end()] + "\n", stripped[cut:])
    if _SIMPLE_WRITE.match(stripped) and len(_segments(stripped)) == 1 and "\n" not in stripped.strip():
        targets = _write_targets(_segments(stripped)[0])[2]
        if targets and all(_inside(t) for t in targets):
            return BashPlan(stripped, "")
    return BashPlan(None, command)


def _unroot_head(command: str, cwd: str) -> str:
    head, sep, body = command.partition("\n")
    for root in {cwd, "/private" + cwd, cwd.removeprefix("/private")}:
        head = head.replace(root + "/", "").replace(root, ".")
    return head + sep + body


def _inside(target: str) -> bool:
    return tree_path(target, None) is not None and not target.startswith(("/", "~", "$"))


def mentions_source(text: str, source_paths: tuple[str, ...]) -> bool:
    """Whether text names a source path: a file entry by path or basename, a directory entry as ``name/``."""
    for entry in source_paths:
        name = entry.rstrip("/")
        if "." in posixpath.basename(name):
            if name in text or re.search(rf"(?<![\w.]){re.escape(posixpath.basename(name))}\b", text):
                return True
        elif re.search(rf"(?<![\w/.-]){re.escape(name)}/", text):
            return True
    return False


def _write_targets(words: list[str]) -> tuple[str, list[str], list[str]]:
    """A simple command's program (past env/timeout/uv run wrappers), its arguments, and
    the operands it could write, before cwd resolution."""
    program, rest = _program(words)
    while program in ("timeout", "env", "nice", "uv") and rest:
        if program == "uv":
            if rest[0] != "run":
                break
            rest = rest[1:]
            while rest and rest[0].startswith("-"):
                rest = rest[2:] if rest[0] in _UV_RUN_VALUE_FLAGS else rest[1:]
        elif program == "timeout":
            while rest and rest[0].startswith("-"):
                rest = rest[1:]
            rest = rest[1:]
        else:
            while rest and (rest[0].startswith("-") or "=" in rest[0]):
                rest = rest[1:]
        program, rest = (posixpath.basename(rest[0]), rest[1:]) if rest else ("", [])
    targets = [rest[i + 1] for i, w in enumerate(rest[:-1]) if w in _REDIRECTS]
    redirection = set()
    for i, w in enumerate(rest):
        if w in _REDIRECTS or w in (">&", "<", "<<", "<<<"):
            redirection.update((i, i + 1))
            if i and rest[i - 1].isdigit():
                redirection.add(i - 1)
    operands = [w for i, w in enumerate(rest) if i not in redirection and w and not w.startswith("-")]
    if program in _LAST_OPERAND_WRITERS and operands:
        targets.append(operands[-1])
    elif program in _EVERY_OPERAND_WRITERS or (
        program in ("sed", "perl") and any(re.fullmatch(r"-[a-zA-Z0-9]*i\S*", w) for w in rest)
    ):
        targets.extend(operands)
    elif program == "dd":
        targets.extend(w[3:] for w in rest if w.startswith("of="))
    return program, rest, targets


def could_write_source(command: str, source_paths: tuple[str, ...], cwd: str | None) -> bool:
    """Spec section 4: whether bash text the replay did not run could have written inside
    source_paths. Per simple command (quoted arguments and heredoc bodies are data): a git
    subcommand that rewrites the tree, or ``ruff format``/``ruff check --fix`` without
    ``--check``/``--diff``, always could; a redirection, ``tee``/``mv``/``rm``/``touch``/
    ``truncate``/``patch`` operand, ``cp``/``install``/``ln``/``rsync`` destination, or
    ``sed -i``/``perl -i`` operand could when it resolves (after any ``cd`` earlier in the
    command) inside source_paths. Python file writes anywhere in the text (heredoc bodies
    included) could when the text names a source path."""
    if _PY_WRITE.search(command) and mentions_source(command, source_paths):
        return True
    directory: str | None = "."
    for words in _segments(command):
        program, rest, targets = _write_targets(words)
        if program == "cd":
            destination = rest[0] if rest else "~"
            if destination.startswith(("/", "~", "$")):
                directory = tree_path(destination, cwd) if destination.startswith("/") else None
            elif directory is not None:
                directory = posixpath.normpath(posixpath.join(directory, destination))
            continue
        if program == "git" and any(w in _GIT_WRITERS for w in rest if not w.startswith("-")):
            return True
        if program == "ruff" and (rest[:1] == ["format"] or "--fix" in rest) and not {"--check", "--diff"} & set(rest):
            return True
        for target in targets:
            target = target.strip("'\"")
            if target.startswith("/"):
                resolved = tree_path(target, cwd)
            elif directory is None or target.startswith(("~", "$")):
                resolved = None
            else:
                resolved = tree_path(posixpath.join(directory, target), None)
            if resolved is not None and in_source_paths(resolved, source_paths):
                return True
    return False


# --- section 4: outcomes, fidelity, unmeasured --------------------------------

GRADED = ("pass", "fail", "unavailable")


def actual_pass(code: str | None, verdict: str | None) -> bool:
    return code == "OK" and verdict == "pass"


def fidelity(harness_verdict: str | None, replay_verdict: str | None) -> str:
    if harness_verdict not in GRADED:
        return "unverifiable"
    return "pass" if replay_verdict == harness_verdict else "fail"


def unmeasured_reasons(
    *,
    fidelity_result: str,
    harness_verdict: str | None,
    final_verdict: str | None,
    trigger: Trigger | None,
    skipped_writer_turns: list[int],
    anchor_miss_turns: list[int],
    raised: str | None,
) -> list[str]:
    """Spec section 4 "unmeasured". Skips and anchor misses count through the end of the
    trigger turn, the state the counterfactual grades."""
    reasons = []
    if raised:
        reasons.append(f"raised: {raised}")
    if fidelity_result == "fail":
        reasons.append(f"fidelity: harness {harness_verdict}, replay {final_verdict}")
    if trigger is not None and trigger.within_budget:
        for turn in sorted(set(skipped_writer_turns)):
            if turn <= trigger.turn:
                reasons.append(f"skipped bash writer at turn {turn}")
        for turn in sorted(set(anchor_miss_turns)):
            if turn <= trigger.turn:
                reasons.append(f"replay raised: edit anchor missing at turn {turn}")
    return reasons


def counterfactual_pass(actual: bool, trigger: Trigger | None, unmeasured: list[str], trigger_verdict: str | None) -> bool:
    """A cell with no counted trigger, or an unmeasured one, keeps its actual outcome."""
    if unmeasured or trigger is None or not trigger.within_budget:
        return actual
    return trigger_verdict == "pass"


def change(actual: bool, counterfactual: bool) -> str:
    if not actual and counterfactual:
        return "rescue"
    if actual and not counterfactual:
        return "harm"
    return "none"


# --- section 5: tallies and the decision --------------------------------------


@dataclass(frozen=True, slots=True)
class TaskTally:
    task: str
    cells: int
    rescues: int
    harms: int
    unmeasured: int

    @property
    def net(self) -> int:
        return self.rescues - self.harms

    @property
    def insufficient(self) -> bool:
        return self.unmeasured > 1


def tally(task: str, changes: list[str], unmeasured_flags: list[bool]) -> TaskTally:
    return TaskTally(task, len(changes), changes.count("rescue"), changes.count("harm"), sum(unmeasured_flags))


def budget_shaped(codes: list[str | None]) -> bool:
    """Spec section 2: at least 2 of 4 decision cells ended BUDGET_EXCEEDED or COMMAND_TIMEOUT."""
    return sum(1 for code in codes if code in ("BUDGET_EXCEEDED", "COMMAND_TIMEOUT")) >= 2


def decide(tallies: dict[str, TaskTally]) -> tuple[str, str]:
    """Spec section 5 and its pre-run amendment (section 7.1). Returns
    (outcome, reason); outcome is "go", "verify" or "not-the-lever"."""
    qualifying = [t for t in BUDGET_SHAPED if not tallies[t].insufficient and tallies[t].net >= 1]
    floor_harm = sum(tallies[t].harms for t in FLOOR)
    floor_insufficient = [t for t in FLOOR if tallies[t].insufficient]
    detail = f"qualifying budget-shaped tasks {qualifying or 'none'}; floor harm cells {floor_harm}; insufficient floor tasks {floor_insufficient or 'none'}"
    if len(qualifying) >= 2 and floor_harm < 2 and not floor_insufficient:
        return "go", detail
    if qualifying:
        return "verify", detail
    if all(tallies[t].net < 1 for t in BUDGET_SHAPED):
        return "not-the-lever", detail
    return "verify", detail + "; a budget-shaped task has net rescues >= 1 but is insufficient (section 7.1)"


def project_markers(path: Path) -> list[Path]:
    """Config files pytest could pick up from ``path`` or any ancestor."""
    return [folder / name for folder in (path, *path.parents) for name in PROJECT_MARKERS if (folder / name).is_file()]


# --- impure: replay, harvest, grade -------------------------------------------


@dataclass(slots=True)
class Replay:
    patch: str = ""
    bash_touched: dict[int, tuple[str, ...]] = field(default_factory=dict)
    skipped_writer_turns: list[int] = field(default_factory=list)
    anchor_miss_turns: list[int] = field(default_factory=list)
    applied: dict[str, int] = field(default_factory=lambda: {"write": 0, "edit": 0, "bash": 0})


def _git(work: Path, *args: str) -> str:
    from satyrn_evals.workspace import GIT_SAFETY_CONFIG

    return subprocess.run(["git", *GIT_SAFETY_CONFIG, *args], cwd=work, capture_output=True, text=True, check=True).stdout


def _digests(work: Path) -> dict[str, str]:
    found = {}
    for path in work.rglob("*"):
        rel = path.relative_to(work).as_posix()
        if path.is_file() and not rel.startswith(".git/") and "/.venv/" not in f"/{rel}" and "__pycache__" not in rel:
            found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def replay(spec: CellSpec, steps: list[Step], cwd: str | None, source_paths: tuple[str, ...], stop_after_turn: int | None) -> Replay:
    """Apply the cell's landed writes to a fresh copy of the task base, through the end
    of ``stop_after_turn`` (None: every step), and harvest the patch as the harness does."""
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch

    assert spec.attempt not in DECISION_IDS or spec.group == "decision"
    work = WORK / f"{spec.attempt}-{'final' if stop_after_turn is None else f'turn-{stop_after_turn:02d}'}"
    if work.exists():
        shutil.rmtree(work)
    try:
        shutil.copytree(TASKS / spec.task / "base", work, symlinks=True)
        _git(work, "init", "-q")
        _git(work, "add", "-A")
        _git(work, "-c", "user.email=replay@localhost", "-c", "user.name=replay", "commit", "-q", "-m", "base")
        base = _git(work, "rev-parse", "HEAD").strip()
        out = Replay()
        for step in steps:
            if stop_after_turn is not None and step.turn > stop_after_turn:
                break
            if step.name == "write" and not step.is_error:
                path = tree_path(step.args.get("path", ""), cwd)
                if path is not None:
                    target = work / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(str(step.args.get("content", "")))
                    out.applied["write"] += 1
            elif step.name == "edit" and not step.is_error:
                path = tree_path(step.args.get("path", ""), cwd)
                if path is None:
                    continue
                target = work / path
                edits = step.args.get("edits") or (
                    [{"oldText": step.args.get("oldText", ""), "newText": step.args.get("newText", "")}] if step.args.get("oldText") else []
                )
                text = target.read_text() if target.is_file() else None
                for edit in edits:
                    old, new = str(edit.get("oldText", "")), str(edit.get("newText", ""))
                    if text is not None and old and old in text:
                        text = text.replace(old, new, 1)
                    else:
                        out.anchor_miss_turns.append(step.turn)
                if text is not None:
                    target.write_text(text)
                    out.applied["edit"] += 1
            elif step.name == "bash":
                command = str(step.args.get("command", ""))
                plan = plan_bash(command, cwd)
                if plan.replay is not None:
                    before = _digests(work)
                    done = subprocess.run(
                        ["/bin/bash", "-c", plan.replay], cwd=work, capture_output=True, timeout=10,
                        env={"PATH": os.environ["PATH"], "HOME": os.fspath(work), "TMPDIR": os.fspath(WORK)},
                    )
                    after = _digests(work)
                    out.bash_touched[step.index] = tuple(sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p)))
                    out.applied["bash"] += 1
                    if done.returncode != 0 and not step.is_error:
                        out.skipped_writer_turns.append(step.turn)
                if plan.remainder and could_write_source(plan.remainder, source_paths, cwd):
                    out.skipped_writer_turns.append(step.turn)
        tempfile.tempdir = os.fspath(WORK)
        out.patch = build_cumulative_patch(work, base, os.environ, exclude=RESIDUE_EXCLUDES).patch_text
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def grade(task: str, patch: str, grade_root: Path, name: str) -> str:
    """``satyrn-evals grade`` on the harvested patch; the receipt's verdict."""
    folder = grade_root / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    (folder / "patch.diff").write_text(patch)
    subprocess.run(
        [os.fspath(Path(sys.executable).parent / "satyrn-evals"), "grade", task, "patch.diff", "--receipt", "receipt.json"],
        cwd=folder, capture_output=True, text=True, timeout=900,
        env={**os.environ, "UV_OFFLINE": "1", "TMPDIR": os.fspath(folder)},
    )
    receipt = json.loads((folder / "receipt.json").read_text())
    return receipt["verdict"]


def cell_dir(spec: CellSpec) -> Path:
    matches = sorted((RUNS / spec.run / spec.arm).glob(f"*-{spec.attempt}"))
    if len(matches) != 1:
        raise FileNotFoundError(f"{spec.run}/{spec.arm}: {len(matches)} directories end in {spec.attempt}")
    return matches[0]


def measure(spec: CellSpec, grade_root: Path) -> dict:
    manifest = json.loads((TASKS / spec.task / "manifest.json").read_text())
    source_paths = tuple(manifest["source_paths"])
    folder = cell_dir(spec)
    attempt = json.loads((folder / "attempt.json").read_text())
    code, harness_verdict = attempt.get("code"), attempt.get("verdict")
    actual = actual_pass(code, harness_verdict)
    row: dict = {"task": spec.task, "group": spec.group, "run": spec.run, "arm": spec.arm, "attempt": spec.attempt,
                 "code": code, "harness_verdict": harness_verdict, "actual": "pass" if actual else "not-pass"}
    trigger = None
    final_verdict = trigger_verdict = raised = None
    skipped: list[int] = []
    misses: list[int] = []
    try:
        events = parse_events((folder / "transcript.txt").read_text())
        cwd = session_cwd(events)
        steps = steps_of(events)
        full = replay(spec, steps, cwd, source_paths, None)
        skipped, misses = full.skipped_writer_turns, full.anchor_miss_turns
        row["applied"] = full.applied
        trigger = find_trigger(steps, source_edit_indices(steps, source_paths, cwd, full.bash_touched))
        if harness_verdict in GRADED:
            final_verdict = grade(spec.task, full.patch, grade_root, f"{spec.attempt}-final")
        if trigger is not None and trigger.within_budget:
            at = replay(spec, steps, cwd, source_paths, trigger.turn)
            skipped = sorted(set(skipped) | set(at.skipped_writer_turns))
            misses = sorted(set(misses) | set(at.anchor_miss_turns))
            trigger_verdict = grade(spec.task, at.patch, grade_root, f"{spec.attempt}-turn-{trigger.turn:02d}")
    except Exception as exc:  # spec section 4: replay or grading raises -> unmeasured
        raised = f"{type(exc).__name__}: {exc}"[:200]
    fid = fidelity(harness_verdict, final_verdict)
    reasons = unmeasured_reasons(
        fidelity_result=fid, harness_verdict=harness_verdict, final_verdict=final_verdict, trigger=trigger,
        skipped_writer_turns=skipped, anchor_miss_turns=misses, raised=raised,
    )
    counter = counterfactual_pass(actual, trigger, reasons, trigger_verdict)
    row.update({
        "trigger": asdict(trigger) if trigger else None,
        "trigger_verdict": trigger_verdict,
        "final_replay_verdict": final_verdict,
        "fidelity": fid,
        "counterfactual": "pass" if counter else "not-pass",
        "change": change(actual, counter),
        "unmeasured": reasons,
        "skipped_writer_turns": sorted(set(skipped)),
        "anchor_miss_turns": sorted(set(misses)),
    })
    return row


def stamp(argv: list[str]) -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=EVALS, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "evidence/2026-09-15-finishing-counterfactual/counterfactual.py"], cwd=EVALS, capture_output=True, text=True).stdout.strip())
    return {"evals_commit": commit, "evals_dirty": dirty, "command": " ".join(["counterfactual.py", *argv])}


def table(rows: list[dict], header: dict) -> str:
    lines = [
        f"<!-- evals {header['evals_commit']}{' (dirty)' if header['evals_dirty'] else ''}; {header['command']} -->",
        "",
        "| task | group | attempt | code | trigger turn | tokens at trigger | actual | counterfactual | rescue | harm | fidelity | unmeasured |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        t = r["trigger"]
        turn = "-" if t is None else f"{t['turn']}{'' if t['within_budget'] else ' (over budget)'}"
        tokens = "-" if t is None else str(t["output_tokens"])
        lines.append(
            f"| {r['task']} | {r['group']} | {r['attempt']} | {r['code']}{'-' + r['harness_verdict'] if r['harness_verdict'] else ''} "
            f"| {turn} | {tokens} | {r['actual']} | {r['counterfactual']} | {'1' if r['change'] == 'rescue' else ''} "
            f"| {'1' if r['change'] == 'harm' else ''} | {r['fidelity']} | {'; '.join(r['unmeasured'])} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="counterfactual.py")
    parser.add_argument("--phase", choices=("debug", "decision"), required=True)
    parser.add_argument("--cell", action="append", default=[], help="debug only: one attempt suffix (repeatable)")
    parser.add_argument("--grade-root", type=Path, default=DEFAULT_GRADE_ROOT, help="receipts and grader scratch; no Python project above it")
    args = parser.parse_args(argv)
    try:
        specs = select_cells(args.phase, tuple(args.cell))
    except ValueError as exc:
        print(f"counterfactual: {exc}", file=sys.stderr)
        return 2
    out = HERE if args.phase == "decision" else HERE / "debug"
    if args.phase == "decision" and (out / "cells.json").exists():
        print("counterfactual: cells.json exists; the decision phase runs once (spec section 6)", file=sys.stderr)
        return 2
    grade_root = args.grade_root.resolve() / args.phase
    if markers := project_markers(grade_root.parent):
        print(f"counterfactual: --grade-root sits under {markers[0]}; pytest would read it while grading", file=sys.stderr)
        return 2
    header = stamp(argv)
    shutil.rmtree(WORK, ignore_errors=True)  # a scratch tree left in the checkout breaks `just gates` collection
    WORK.mkdir()
    grade_root.mkdir(parents=True, exist_ok=True)
    try:
        return _run(args.phase, specs, grade_root, header)
    finally:
        shutil.rmtree(WORK, ignore_errors=True)


def _run(phase: str, specs: tuple[CellSpec, ...], grade_root: Path, header: dict) -> int:
    out = HERE if phase == "decision" else HERE / "debug"
    if phase == "decision":
        # Spec section 2: the recorded codes are the pre-registration's; refuse before measuring if any differs.
        codes: dict[str, list[str | None]] = {}
        for spec in specs:
            attempt = json.loads((cell_dir(spec) / "attempt.json").read_text())
            if (attempt.get("code"), attempt.get("verdict")) != RECORDED[spec.attempt]:
                print(f"counterfactual: {spec.attempt} is not the spec's recorded code", file=sys.stderr)
                return 2
            codes.setdefault(spec.task, []).append(attempt.get("code"))
        if [task for task, task_codes in codes.items() if budget_shaped(task_codes)] != list(BUDGET_SHAPED):
            print("counterfactual: recorded codes do not select the spec's budget-shaped tasks", file=sys.stderr)
            return 2
    rows = []
    for spec in specs:
        row = measure(spec, grade_root)
        rows.append(row)
        print(f"{spec.task} {spec.attempt} {row['code']} trigger={row['trigger']} cf={row['counterfactual']} change={row['change']} fidelity={row['fidelity']} unmeasured={row['unmeasured']}", flush=True)
    out.mkdir(exist_ok=True)
    (out / "cells.json").write_text(json.dumps({**header, "cells": rows}, indent=1) + "\n")
    (out / "table.md").write_text(table(rows, header))
    if phase == "decision":
        tallies = {}
        for task in (*BUDGET_SHAPED, *FLOOR):
            mine = [r for r in rows if r["task"] == task]
            tallies[task] = tally(task, [r["change"] for r in mine], [bool(r["unmeasured"]) for r in mine])
        outcome, reason = decide(tallies)
        lines = [f"evals {header['evals_commit']}{' (dirty)' if header['evals_dirty'] else ''}", header["command"], ""]
        for task, t in tallies.items():
            kind = "budget-shaped" if task in BUDGET_SHAPED else "floor"
            lines.append(f"{task} ({kind}): rescues {t.rescues}, harms {t.harms}, net {t.net}, unmeasured {t.unmeasured}{', insufficient' if t.insufficient else ''}")
        lines += ["", f"decision: {outcome}", reason]
        (out / "decision.txt").write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_finishing_counterfactual.py -q`
Expected: `100 passed`.

Run: `uv run ruff check tests/test_finishing_counterfactual.py && uv run ruff check --no-force-exclude --ignore E501 evidence/2026-09-15-finishing-counterfactual/counterfactual.py`
Expected: `All checks passed!` twice. The second check is advisory: evidence is excluded from the gate, but the script is kept clean.

- [ ] **Step 5: Prove the debug refusal from the command line, before any read**

Run: `uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase debug --cell 971281; echo "exit=$?"`
Expected: `counterfactual: --phase debug refuses decision attempt ids: 971281` then `exit=2`. No `work/`, `debug/` or grade directory is created.

- [ ] **Step 6: Run the debug phase and compare with the verified expectations**

Run: `mkdir -p "$HOME/satyrn-counterfactual-grades" && uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase debug > "$HOME/satyrn-counterfactual-grades/debug-task1.log" 2>&1; echo "exit=$?"`
Expected: `exit=0`, in about 30 s. Then run `cat evidence/2026-09-15-finishing-counterfactual/debug/table.md`. Every row must match this table, which the scratch clone at `3f5a8a9` produced:

| attempt | code | trigger turn | tokens | actual | counterfactual | change | fidelity | unmeasured |
|---|---|---|---|---|---|---|---|---|
| 490384 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 549012 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 618278 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 511653 | BUDGET_EXCEEDED | 34 | 24834 | not-pass | not-pass | none | unverifiable | |
| 249635 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 305323 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 372105 | OK-pass | - | - | pass | pass | none | pass | |
| 309486 | OK-pass | - | - | pass | pass | none | pass | |
| 714610 | OK-unavailable | 15 | 7479 | not-pass | not-pass | none | pass | |
| 770940 | OK-unavailable | 18 | 7541 | not-pass | not-pass | none | fail | fidelity: harness unavailable, replay pass |
| 840545 | OK-unavailable | 12 | 5203 | not-pass | not-pass | none | fail | fidelity: harness unavailable, replay pass |
| 624725 | OK-unavailable | 14 | 7992 | not-pass | not-pass | none | fail | fidelity: harness unavailable, replay fail |
| 808698 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 296145 | BUDGET_EXCEEDED | - | - | not-pass | not-pass | none | unverifiable | |
| 859943 | BUDGET_EXCEEDED | 34 | 27954 | not-pass | pass | rescue | unverifiable | |
| 117091 | OK-pass | 5 | 1738 | pass | pass | none | pass | |
| 172304 | OK-pass | 4 | 910 | pass | pass | none | pass | |
| 140540 | OK-pass | 9 | 2254 | pass | pass | none | pass | |
| 201516 | OK-pass | 4 | 583 | pass | pass | none | pass | |

The three fidelity failures are expected. Those review-script nights ran under a task tree whose manifest did not yet ignore `PROVENANCE.md`, so the harness answered `unavailable` ("patch touches non-source path: PROVENANCE.md"). The 2026-09-14 self-hosted records' `task_tree_sha256` no longer matches the current tree; every decision record's does. Graded debug cells: 7 of 10 reproduce. If any row differs, stop and report the difference; do not tune a rule to the table.

- [ ] **Step 7: Clean up the unreviewed outputs**

Run: `rm -rf evidence/2026-09-15-finishing-counterfactual/debug && ls -a evidence/2026-09-15-finishing-counterfactual/`
Expected: `.gitignore`, `counterfactual.py`, and possibly `__pycache__` (ignored by the root `.gitignore`). No `work/`. Task 2 regenerates `debug/` at the reviewed commit.

- [ ] **Step 8: Provenance rows and gates**

Run: `uv run python tools/provenance.py new evidence/2026-09-15-finishing-counterfactual/counterfactual.py evidence/2026-09-15-finishing-counterfactual/.gitignore tests/test_finishing_counterfactual.py`
Run: `just gates; echo "gates=$?"`
Expected: `gates=0`. At `3f5a8a9` with this test file, pytest reports `2231 passed`; the count is higher if the other agent adds tests.

- [ ] **Step 9: Commit**

```bash
git add evidence/2026-09-15-finishing-counterfactual/counterfactual.py evidence/2026-09-15-finishing-counterfactual/.gitignore tests/test_finishing_counterfactual.py PROVENANCE.md
git commit -m "Finishing counterfactual: the analysis script, its pure-rule tests, and a debug phase that refuses decision cells"
```

`PROVENANCE.md` may also carry the other agent's uncommitted rows. If `git diff PROVENANCE.md` shows rows other than these three, stage only these three with `git add -p PROVENANCE.md`.

---

### Task 2: Review gate, the one decision run, and the result (attended operator steps)

These steps belong to the controller and the maintainer, in order. The planner executed none of them. No step starts before the one above it has passed.

**Files:**
- Create (generated): `evidence/2026-09-15-finishing-counterfactual/debug/cells.json`, `debug/table.md`, `cells.json`, `table.md`, `decision.txt`
- Create: `evidence/2026-09-15-finishing-counterfactual/README.md`
- Modify: `ROADMAP.md` (the R0 row), `PROVENANCE.md`

**Interfaces:**
- Consumes: Task 1's CLI and output files.
- Produces: the committed decision (`go`, `verify` or `not-the-lever`) that R0 reads.

- [ ] **Step 1: Opus reviews the trigger and counting code line by line against spec sections 3–5**

Dispatch one Opus reviewer, blocking. Give it the spec, this plan's Rulings, the script at Task 1's commit and the test file. The reviewer may run the unit tests and `--phase debug --cell <debug id>` on debug cells only, and must not name a decision id. The review answers every item below with pass or fail and a line reference:

1. `select_cells`: `debug` refuses any id in `DECISION_IDS` before `main` touches the filesystem (no `stamp`, no `work/`). `decision` returns exactly the 24 and refuses `--cell`. `DECISION` rows, `RECORDED` pairs, `BUDGET_SHAPED` and `FLOOR` match section 2's table character for character, with ids that have leading zeros kept as strings.
2. `steps_of`: turn and token counts come from `UsageCounter.feed_event` for every event up to and including each `tool_execution_end`, with no separate counter and no `message_update` counting. Args come from the matching `tool_execution_start`.
3. `is_test_file` is section 3's rule and nothing more. `is_source_file` requires `in_source_paths`. `source_edit_indices` counts `write`/`edit` only when `is_error` is false, and bash only through replay-touched digests.
4. `find_trigger` returns the first green strictly after the first source edit's index. `is_test_run`/`is_green` use `runs_pytest` for bash and require `not is_error` and `pytest_output_green`. `self_test_green` requires `ok` true, exit 0, not timed out, and no failed/error counts (Ruling 4). `within_budget` is `<= 32_000` and `<= 48`.
5. `summary_lines`/`pytest_output_green` match Ruling 5, including "an absent summary line is not green" and multiple summary lines.
6. `replay` behaves as follows:
   - It stops after the trigger turn (`step.turn > stop_after_turn`).
   - It applies `write` only when not an error.
   - It applies edits in order with first-occurrence replacement, and records an anchor miss for each missing edit.
   - It replays bash only through `plan_bash`.
   - It marks a skipped writer for a failed replay whose original was not an error, and for any remainder `could_write_source` flags.
   - It harvests with `build_cumulative_patch(..., exclude=RESIDUE_EXCLUDES)` over the whole tree, then deletes the tree.
7. `grade` reads the receipt's `verdict`, not the exit code. It runs outside any project (the `project_markers` refusal in `main`) and sets `UV_OFFLINE=1`.
8. `measure`: `actual` is `code == "OK" and verdict == "pass"`. The final tree is graded exactly when the harness verdict is `pass`/`fail`/`unavailable`. The trigger tree is graded exactly when a trigger is within budget. Any exception becomes `raised`.
9. `unmeasured_reasons` follows section 4 plus Rulings 12–14. `counterfactual_pass` keeps the actual outcome on no trigger, an over-budget trigger, or any unmeasured reason. `change` maps rescue, harm and none.
10. `tally`: `insufficient` is `unmeasured > 1` and `net` is rescues − harms. Check `decide` against section 5 line by line, including the insufficient-but-positive case, which is `verify` (spec section 7.1, Ruling 15) and that an insufficient budget-shaped task never qualifies.
11. The `_run` decision branch refuses before measuring when any recorded code differs or the codes select other budget-shaped tasks. `main` refuses when `cells.json` exists. Outputs carry the stamp, and `decision.txt` lists every task's tally.
12. The tests exercise both directions of every rule listed in the Global Constraints, and none spawns.

A failed item is fixed by a Sonnet implementer in a new commit (never an amend). Sonnet re-reviews scoped to the fix diff, and the items the fix touched are answered again. `just gates` must exit 0 after each fix commit.

- [ ] **Step 2: Confirm a clean tree at the reviewed commit**

Run: `git status --porcelain -- src evidence/2026-09-15-finishing-counterfactual tests/test_finishing_counterfactual.py; git rev-parse HEAD`
Expected: `status` prints nothing for those paths, and `rev-parse` prints the reviewed commit id. Write the id down; it is the stamp Steps 3 and 4 must show.

- [ ] **Step 3: Regenerate the debug outputs (the Engine column) at the reviewed commit**

Run: `uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase debug; echo "exit=$?"`
Expected: `exit=0`, and the first line of `debug/table.md` names the reviewed commit without `(dirty)`. Rows match Task 1 Step 6's table unless a review fix changed a rule. In that case, record each changed row and the fix that changed it in the README's notes.

- [ ] **Step 4: The decision run — once**

Run: `uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase decision > "$HOME/satyrn-counterfactual-grades/decision.log" 2>&1; echo "exit=$?"; cat evidence/2026-09-15-finishing-counterfactual/decision.txt`
Expected: `exit=0`; `cells.json`, `table.md` and `decision.txt` exist, and each stamp names the reviewed commit without `(dirty)`.

`exit=2` with "is not the spec's recorded code" or "do not select the spec's budget-shaped tasks" means the records disagree with the pre-registration. Stop and report to the maintainer; do not edit the constants.

A bug found after this step is fixed in a new commit, and the run is repeated only with the bug and both results recorded side by side (the spec's status line). To re-run, move the first outputs to `evidence/2026-09-15-finishing-counterfactual/run-1/` in the same commit that records the bug.

- [ ] **Step 5: Commit the outputs**

```bash
uv run python tools/provenance.py new evidence/2026-09-15-finishing-counterfactual/cells.json evidence/2026-09-15-finishing-counterfactual/table.md evidence/2026-09-15-finishing-counterfactual/decision.txt evidence/2026-09-15-finishing-counterfactual/debug/cells.json evidence/2026-09-15-finishing-counterfactual/debug/table.md
just gates; echo "gates=$?"
git add evidence/2026-09-15-finishing-counterfactual/cells.json evidence/2026-09-15-finishing-counterfactual/table.md evidence/2026-09-15-finishing-counterfactual/decision.txt evidence/2026-09-15-finishing-counterfactual/debug/cells.json evidence/2026-09-15-finishing-counterfactual/debug/table.md PROVENANCE.md
git commit -m "Finishing counterfactual: decision run over the 24 pre-registered cells, with the Engine and 2026-09-14 debug cells beside it"
```

Expected: `gates=0` before the commit.

- [ ] **Step 6: Write the result README (≤ 120 lines)**

Create `evidence/2026-09-15-finishing-counterfactual/README.md` with these sections, in this order. Fill it only from the committed `decision.txt`, `table.md` and `debug/table.md`; copy rows rather than recomputing by hand. The only values typed in are the reviewed commit id and the output commit id.

1. `# Finishing counterfactual — result`, then one paragraph: the question (spec section 1), the pre-registration commit `3f5a8a9`, the reviewed script commit, and the output commit.
2. `## Decision`: the `decision:` line and its reason line from `decision.txt`, verbatim, then the consequence the section 5 bullet for that outcome states, copied.
3. `## Per task`: a table `| task | kind | rescues | harms | net | unmeasured | insufficient |` with one row per task line of `decision.txt`.
4. `## Per cell`: `table.md`'s table verbatim. Its 24 rows carry trigger turn, tokens at trigger, actual, counterfactual, rescue, harm, fidelity and unmeasured reason.
5. `## Engine column (outside the decision)`: the seven Engine rows of `debug/table.md` (`808698 296145 859943 117091 172304 140540 201516`) with their rescue and harm, and one sentence saying they are not counted (spec section 2).
6. `## Notes`: fidelity on graded decision cells as "k of n reproduce"; the unmeasured cells and their reasons; every Ruling that affected a counted cell, naming the cell; and the fidelity misses on the 2026-09-14 nights, with their cause.
7. `## Recompute`: a fenced block, with `REVIEWED` replaced by the literal commit id from Step 2:

````
```bash
git clone --branch release-one /Users/pauleveritt/projects/pauleveritt/satyrn-evals "$HOME/satyrn-counterfactual-recompute"
cd "$HOME/satyrn-counterfactual-recompute" && git checkout REVIEWED && uv sync
mv evidence/2026-09-15-finishing-counterfactual/cells.json cells.committed.json
uv run --project . python evidence/2026-09-15-finishing-counterfactual/counterfactual.py --phase decision --grade-root "$HOME/satyrn-counterfactual-grades-recompute"
uv run python -c "import json; a, b = (json.load(open(p))['cells'] for p in ('cells.committed.json', 'evidence/2026-09-15-finishing-counterfactual/cells.json')); print('identical' if a == b else 'DIFFERENT')"
```
````

Then check the cap: `wc -l evidence/2026-09-15-finishing-counterfactual/README.md` must print at most 120.

- [ ] **Step 7: Record the decision in the R0 row of ROADMAP.md**

Re-read `ROADMAP.md` first, because the other agent may have changed it. In the R0 row's "Done when" cell, append one sentence: `Knowledge stage: the finishing counterfactual decided **OUTCOME** (evidence/2026-09-15-finishing-counterfactual/README.md).`, with `OUTCOME` replaced by the literal `decision:` value from `decision.txt`. Nothing else in the file changes. `wc -l ROADMAP.md` must print at most 150.

- [ ] **Step 8: Provenance, gates, commit**

```bash
uv run python tools/provenance.py new evidence/2026-09-15-finishing-counterfactual/README.md
just gates; echo "gates=$?"
git add evidence/2026-09-15-finishing-counterfactual/README.md ROADMAP.md PROVENANCE.md
git commit -m "Finishing counterfactual result: the section 5 decision, per-task net rescues, and the Engine column"
```

Expected: `gates=0`. If `ROADMAP.md` or `PROVENANCE.md` carries the other agent's uncommitted changes, stage it with `git add -p`.

---

## Verification before hand-back (plan writing, 2026-09-15)

This was done in a scratch clone of evals `release-one` at `3f5a8a9` under `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/counterfactual-plan/evals`. It read `~/satyrn-runs` read-only and kept the grade root in the same scratchpad.

- Step 2's failure: in a fresh clone, the test file alone fails collection with `FileNotFoundError` for the script path.
- Step 4: `100 passed in 0.06s`; ruff is clean on both files.
- Step 5: `--phase debug --cell 971281` printed the refusal and exited 2, and nothing was created.
- Step 6: `--phase debug` over the 19 debug cells exited 0 in 31 s and produced the table in Step 6. Fidelity on graded debug cells was 7 of 10; the three misses are review-script 2026-09-14 cells, explained by manifest drift. Triggers found:
  - 511653: turn 34, 24,834 tokens, hidden suite fail at the trigger.
  - Review-script nights 714610, 770940, 840545 and 624725: turns 15, 18, 12 and 14.
  - 859943, Engine docs-linter: turn 34, 27,954 tokens, hidden suite pass at the trigger. This is a rescue in the Engine column.
  - 117091, 172304, 140540 and 201516, Engine misleading-locus: all pass at the trigger, no harm.
  - No trigger: 490384, 549012, 618278, 249635, 305323, 372105, 309486, 808698 and 296145.
- Three defects were found and fixed during verification; Rulings 9–11 reflect them:
  - Grading under the checkout returned `unavailable` for every agentclinic cell.
  - Leftover `work/` trees broke `just gates` collection (1,908 errors).
  - Substring writer detection flagged strings inside Python code (`"pip install -p x"`) and `ruff format --check` as writers.
- Step 8: `just gates` exited 0 (`2231 passed, 333 deselected`) with the three provenance rows.
- No decision cell was replayed, graded, parsed or printed. Decision records (`records/*.json`) were read only for `task_tree_sha256`, `token_budget` and `turn_budget`.

## Self-review against the spec

- **Section 2, scope.** Covered by `DECISION`, `RECORDED`, `BUDGET_SHAPED`, `FLOOR` and `DEBUG`. The exclusions (calc-build smoke, 719334, complaint-lifecycle) hold by omission. Task 1 holds the script; Task 2 Step 4 holds the refusal checks.
- **Section 3: source edit, own-green on both routes, budget, policy.** Covered by `source_edit_indices`, `self_test_green`, `pytest_output_green`, `is_green`, `find_trigger`, `within_budget` and `replay(stop_after_turn=…)`, with tests in both directions.
- **Section 4: actual, counterfactual, rescue/harm/net, fidelity, unmeasured, insufficient.** Covered by `actual_pass`, `grade`, `change`, `tally`, `fidelity`, `unmeasured_reasons` and `TaskTally.insufficient`, with tests in both directions.
- **Section 5.** Covered by `decide`, with every outcome tested, including the section 7.1 amendment (Ruling 15).
- **Section 6.** CLI phases and refusal: Task 1. No model, network or `/Users/Shared`: Global Constraints and `UV_OFFLINE`. Git-ignored scratch trees: Ruling 9. Opus review: Task 2 Step 1. One run: Step 4. README with table, net, Engine column, decision and recompute: Step 6. ROADMAP R0: Step 7.
