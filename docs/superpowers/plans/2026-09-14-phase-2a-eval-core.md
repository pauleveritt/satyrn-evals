# Phase 2a — Eval core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: approved 2026-09-14.** Phase 1 is done (evals `b7cf775`, engine `9ad3583`) and this plan is merged on `release-one` (`69fad8d`). Tasks 1–4 and 6 were planned against evals `39feaa9` plus the spec commit `76e20d8`; the only evals change since is Phase 1 Task 13b (`e0f25df`, the E5 wrapper's `UV_PROJECT_ENVIRONMENT`) and the ROADMAP rows. Task 5 starts with the R21 engine fix (Ruling 11), then verifies every name it takes from the Phase 1 plan (see "Phase 1 dependencies").

**Goal:** Harness items 1, 3, 4 and 5 of the release-one design, each with fixture tests in both directions, and the Engine arm running end to end against a fake model: harvest against the workspace base commit (untracked files included, surviving a model `git commit`), an output-token and turn tripwire read live from the transcript, per-cell evidence for every cell whatever its code, and answer-key hygiene in the test suite.

**Architecture:** The attempt adapter stays the patch seam; Evals exports the workspace base commit and both adapters harvest with the session path's temporary-index diff (`session_patch.build_cumulative_patch`). The harness's existing live transcript tail (`workspace._wait_or_trip`) gains the budget tripwire (budgets from the run record) and a tool-call timeline writer, so both arms get both from one place. A new pure module (`cell_evidence`) reads any transcript leniently and the summary carries its block for every cell. The Engine adapter runs `/implement`'s two CLI steps (`derive`, `deliver`), checks the candidate out into the Evals worktree and harvests it with the same rule as Baseline.

**Tech Stack:** Python 3.14, uv, pytest (default tier: audit-hook spawn tripwire; `integration` marker), ruff, just; git 2.45; `satyrn-engine` CLI (Phase 1) for Task 5 only.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` at `76e20d8` — "The eval" (Budget, both arms; Measures, per cell), "Harness work the workload depends on" (items 1, 3, 4, 5), "Process" ("A phase builds in half a day"), roadmap row 2a. Evidence per item: `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/workload-deep-dive/rationale.md` Q6. House style and the Phase 1 interfaces: `docs/superpowers/plans/2026-09-14-phase-1-implement.md` (on `release-one`).

## Rulings

Conflicts between the spec, the rationale and the code as of evals `39feaa9`, each with the ruling taken, why, and the cost if wrong.

1. **Where the harvest runs.** The rationale says "reuse it in the attempt adapter"; `session_patch.py:3` says "Evals — never the adapter — obtains the patch". Ruling: the adapter stays the seam and harvests; Evals exports `SATYRN_WORKSPACE_BASE_SHA` through a new `run_prepared_command(extra_environment=...)`. Why: 22 rows of `tests/test_attempt.py` and every `fake_attempt.py` integration row pin "the command delivers `patch.diff`"; moving the harvest into Evals rewrites that seam for no measured gain. Cost if wrong: a cell the harness tears down (`COMMAND_TIMEOUT`, `BUDGET_EXCEEDED`, `REPEAT_LIMIT`) keeps no patch; it is a fail either way and its evidence comes from the transcript (Task 4).
2. **What the harvest includes.** Every untracked file except runtime residue, excluded by pathspec (`**/.pytest_cache/**`, `**/__pycache__/**`, `**/.ruff_cache/**`, `**/.venv/**`; the form Phase 1 Task 8 N1 verified on git 2.45.1 and this plan re-verified with `add -N`). The grader's allowlist is unchanged, so a stray model file outside `source_paths` now makes the verdict `unavailable` where `git diff HEAD` hid it. Both arms, reported. Cost if wrong: a correct fix beside a scratch file scores not-pass; Phase 3 admission reads those cells.
3. **The budget.** `BUDGET_EXCEEDED` when output tokens or turns go strictly over the run record's `token_budget`/`turn_budget` (new required fields); no default anywhere; `attempt`/`run` take `--run-record`. A command whose last lines put it over budget after it already exited is `BUDGET_EXCEEDED` with its exit code (policy `command_exit` optional). The repeat rule is a live spending rule and is not applied to that tail. Cost if wrong: none identified; a record without budgets refuses to load, loudly.
4. **The timeline is the harness's, not the adapter's.** The spec says "an adapter timeline". Ruling: the harness already reads the transcript as it is written; it stamps read time for each `tool_execution_start`/`_end` into `timeline.jsonl`, for both arms, with no adapter change. Resolution is the poll interval (0.25 s). Cost if wrong: per-command seconds are ±0.25 s, which does not move a 120 s threshold.
5. **Evidence is a new summary block, not V10's.** V10 publishes no counts beside `measured: false` (`pathology.py:6-7`, S1), and every timeout is `partial`. Ruling: `summary.json` gains `evidence`, one block per cell, computed for every cell with a readable transcript whatever its code; the escape rules are lexical and written in `cell_evidence`'s docstring. Relative `..` escapes in bash text are not counted (file-tool `..` paths are). Cost if wrong: a hunt written as `cd .. && find .` is invisible to `root_searches`; `bash_outside_paths` and the overlay scan still see what it reads.
6. **The Engine arm's invocation.** `/implement` is a Pi slash command; the eval cannot type it. Ruling: the Engine adapter runs the two CLI calls `/implement` makes (Phase 1 Task 10), checks the candidate commit out into the Evals worktree, and harvests with Ruling 1's rule, so both arms' patches come from one function. The receipt is kept as `engine-receipt.json`, never the verdict. Cost if wrong: an Engine cell stopped mid-`deliver` has no candidate and scores `NO_PATCH`-shaped evidence under its stop code; it is a fail either way.
7. **`UV_PROJECT_ENVIRONMENT` for the engine** (found by this plan's test verification). Evals points it at the attempt's private environment (`attempt.py:262`); left set, `uv run --project ENGINE satyrn-engine` fails to spawn and every Engine cell is `NO_PATCH`. Ruling: the Engine adapter drops it for the engine's calls. Cost if wrong: the model's own `uv run` inside `deliver`'s worktree builds a `.venv` there (excluded from the candidate by Phase 1 Task 8). Phase 3 watches it.
8. **No extra teardown grace.** `deliver` and the engine's `attempt` each run their child in its own process group. Task 5's orphan test shows the fake `pi` gone within the harness's 0.25 s grace (three runs). Ruling: no new grace constant. Phase 3 watch: a real Pi (Node) exiting under `deliver`'s cooperative teardown.
9. **Moves to 2b or later.** The launcher running cells from a record (`launch` stays `--check`); a committed Engine arm file and its pins (`arms.ENGINE_SOURCES` gains `scope.ts` and `bounds.ts` once the Phase 1 engine commit is frozen); the tally that counts a pass with an out-of-worktree read of grader material as a fail (the Phase 4 result reads `evidence`); per-turn seconds and "suite runs before the last mutation" (derived at result time); the engine's derived default budget (32,000/48, Phase 1 Task 3) against a 24,000/36 campaign record.
10. **Hygiene is code and tests only.** The manifests test uses the synthetic hidden task; the default tier fails its session if a bundled grader file is left in pytest's base temp. Closing `~/satyrn-smokes` and clearing attempt directories are maintainer steps in Task 6's checklist, not executed.
11. **R21 lands before the Engine arm** (added at approval, from Phase 1's final review). Phase 1 made engine `attempt` forward Pi's stdout live (R18) so budgets trip mid-run; its pump stops reading when `forward` fails, so a hard-killed `deliver` or `attempt | head` leaves `attempt` and Pi blocked forever on a full pipe, and a `ValueError` from a closed sink escaped `_run`. A hung cell stalls a campaign night, and Task 5's orphan row is the first harness path that kills `deliver`. Ruling: Task 5 Steps 0a–0c fix it in the engine (drop a failing sink, keep draining, raise one `OSError` after Pi exits) before any Engine-arm code. Phase 1 Task 13b's `_is_engine_wrapper_command` in evals `attempt.py` stays: the E5 rows still use that wrapper shape, and the Engine adapter drops the variable itself (Ruling 7); remove both together when the E5 wrapper is retired. Cost if wrong: an engine commit inside an evals plan; it is one file, its own tests and the engine's gates, so a reviewer can reject it apart from the adapter.

## Phase 1 dependencies

Taken from the Phase 1 plan (`docs/superpowers/plans/2026-09-14-phase-1-implement.md` on `release-one`); verified against the merged engine by Task 5 Step 1 before any Task 5 code is written. If one differs, Task 5 stops and reports; nothing is adapted silently.

| what 2a uses | Phase 1 source | used in |
|---|---|---|
| `/implement` = `satyrn-engine derive --repo R -- REQUEST`, which writes `<git-dir>/satyrn/contracts/<id>.yaml` and prints `satyrn-engine: contract <path>` on stderr | Task 3 Interfaces, line 593; Ruling 5, line 21 | Task 5 `derive_argv`, `contract_path` |
| dispatch = `satyrn-engine deliver --repo R --timeout S CONTRACT -- uv run --project E satyrn-engine attempt --model=M -- CONTRACT`, receipt JSON on stdout | Task 10 Interfaces, lines 1930–1932 (`buildDeliveryInvocation`, `/implement --go` → `runDelivery`); Task 11 line 2137 | Task 5 `deliver_argv`, `candidate_commit` |
| receipt fields `code`, `candidate_commit`, `validation`, `turns`, `tokens_out`, `guard_firings` | Task 8 Interfaces, line 1666 | Task 5 integration assertions |
| guard firings are `entry_appended` events, `entry.customType` in `GUARD_KINDS = (loop_broken, scope_refused, symbol_preserved, command_bounded, command_timed_out)` | Ruling 7, line 23; Task 2 Interfaces, line 372; Task 11, line 2091 | Task 5 `pathology.GUARD_KINDS`; Task 3 counts any `customType` |
| the runner tool is named `self_test`; `--tools read,bash,edit,write,self_test` | Ruling 1, line 17; Task 9 Interfaces, line 1792 | Task 5 `pathology.TOOL_NAMES`, `census.KNOWN_TOOL_NAMES` |
| usage shapes: `turn_start`; assistant `message_end` `message.usage.output`; `cacheRead` not counted | Task 2, line 374 | Task 2 `UsageCounter` (shape only; no engine import) |

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer per task; one Opus review per task before the next starts.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **No inference anywhere.** Fake `pi`, fixture repositories, recorded shapes. No launcher, no `pi -p`.
- **Default test tier: no subprocess, no network, no model** (the audit hook in `tests/conftest.py`). Anything that spawns is `@pytest.mark.integration`.
- **Every refusal test has a sibling success test**; every detector has a firing row and a silent row.
- **Every task ends with `just gates` exit 0** (read the exit code; never pipe a gate). New files get `PROVENANCE.md` rows via `uv run python tools/provenance.py new <paths>`; edited files keep theirs. Run `uv run ruff check --fix` before gates (import order).
- **Integration runs name their files.** `tests/integration/test_attempt.py::test_real_e5_*` (2 rows) pass since Phase 1 Task 13b; they must still pass at the end of every task that touches `attempt.py`, and their assertions are not edited here.
- **Commit at the end of every task** on evals `release-one`, with the plan's message. Never `--amend`, merge or push. A task whose gates are red is not committed.
- **Evals tree only, with one exception.** The engine is read, never edited, except Task 5 Steps 0a–0c (R21, Ruling 11), which run the engine's own `just gates` and `just integration` and commit on engine `release-one`. Engine checkout: `/Users/pauleveritt/projects/pauleveritt/satyrn-engine` on `release-one`; Task 5's integration rows find it through `SATYRN_V4_ENGINE_REPO` (set it explicitly: `tests/integration/test_attempt.py:464-470` otherwise looks three parents up).
- **Starting point:** evals `release-one` with Phase 1 done and `phase-2-prep` (spec `76e20d8`, this plan) merged. Docs caps stand: `ROADMAP.md` ≤ 150 lines; `just lint-docs` exit 0.
- Old worktrees under `.claude/worktrees/` are never checked out, edited or removed.

---

## File structure

```
src/satyrn_evals/session_patch.py      # RESIDUE_EXCLUDES; build_cumulative_patch(exclude=)            (modify, T1)
src/satyrn_evals/workspace.py          # run_prepared_command(extra_environment=, budget=, timeline=); BUDGET_EXCEEDED; tail feeds budget and timeline (modify, T1-T3)
src/satyrn_evals/attempt.py            # BASE_SHA_ENV exported; budget and timeline passed through    (modify, T1-T3)
src/satyrn_evals/attempt_pi.py         # read_base_sha; harvest_patch(worktree, base)                  (modify, T1)
src/satyrn_evals/budget.py             # AttemptBudget, UsageCounter, BudgetTripwire                   (new, T2)
src/satyrn_evals/attempt_record.py     # AttemptCode.BUDGET_EXCEEDED                                   (modify, T2)
src/satyrn_evals/run_record.py         # token_budget, turn_budget; attempt_budget()                   (modify, T2)
src/satyrn_evals/run.py, cli.py        # budget from --run-record; evidence into the summary           (modify, T2, T4)
src/satyrn_evals/timeline.py           # TimelineWriter, ToolSpan, read_timeline                        (new, T3)
src/satyrn_evals/cell_evidence.py      # collect_evidence and the lexical detectors                    (new, T3)
src/satyrn_evals/summary.py, rescore.py# Summary.evidence; compute_evidence                             (modify, T4)
src/satyrn_evals/attempt_engine.py     # the Engine adapter                                             (new, T5)
src/satyrn_evals/pathology.py, census.py # self_test and the guard kinds in the vocabulary             (modify, T5)
src/satyrn_evals/hygiene.py            # overlay_digests, overlay_copies                                (new, T6)
pyproject.toml                         # satyrn-evals-attempt-engine script                             (modify, T5)
tests/integration/data/tasks/calc-build/** # a build-shaped fixture task (visible oracle)                (new, T1)
tests/integration/fake_pi_build.py     # fake pi: commit | write | idle | spend                          (new, T1)
tests/...                              # per task
ROADMAP.md                             # row 2a status                                                  (modify, T6)
```

---

### Task 1: Harvest against the base commit, untracked files included

**Files:**
- Modify: `src/satyrn_evals/session_patch.py:53-80`, `src/satyrn_evals/workspace.py:1630-1651` (`run_prepared_command`), `src/satyrn_evals/attempt.py:57-60,320-328`, `src/satyrn_evals/attempt_pi.py:1-36,194-234`
- Modify tests: `tests/test_attempt_pi.py` (six rows pin `git diff HEAD`: `test_harvest_returns_the_tracked_diff`, `test_harvest_refuses_when_git_fails`, and the four `test_main_*` rows — the only permitted assertion changes), `tests/integration/test_attempt_pi.py:84-107` (`_run` exports the base sha), `tests/test_attempt.py`, `tests/integration/test_session_patch.py`
- Create: `tests/integration/data/tasks/calc-build/` (9 files), `tests/integration/fake_pi_build.py`, `tests/integration/test_harvest_qualification.py`

**Interfaces:**
- Produces: `session_patch.RESIDUE_EXCLUDES: tuple[str, ...]`; `build_cumulative_patch(worktree, base_commit, environment=None, *, exclude: Sequence[str] = ()) -> PatchCapture` (default unchanged); `workspace.run_prepared_command(..., extra_environment: Mapping[str, str] | None = None)` (merged over the prepared environment); `attempt.BASE_SHA_ENV = "SATYRN_WORKSPACE_BASE_SHA"`; `attempt_pi.BASE_SHA_ENV` (same string), `attempt_pi.read_base_sha(environment: Mapping[str, str]) -> str` (40- or 64-hex lowercase, else `AdapterError` naming the variable), `attempt_pi.harvest_patch(worktree: Path, base_sha: str) -> str` (`AdapterError("harvest against <sha> failed (<code>): <stderr>")` on git failure); fixture task `calc-build` under `tests/integration/data/tasks`; `fake_pi_build.py` modes `commit` (default), `write`, `idle`, `spend` (Tasks 2 and 5 use the last two), env `SATYRN_FAKE_PI_MODE`, `SATYRN_FAKE_PI_PIDFILE`.

- [ ] **Step 1: The fixture task.** Create these files exactly (the patches were produced with `git diff` after `git add -N` and grade `pass` 2/2 and `fail` 0/2, error 0, on today's tree).

`tests/integration/data/tasks/calc-build/manifest.json`:

```json
{
  "name": "calc-build",
  "contract": "Create calc/helpers.py with add_all(xs) returning the sum, create calc/format.py with render(n) returning n with thousands separators, and make total(xs) in calc/core.py return add_all(xs).",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"],
  "expected_test_ids": [
    "tests/test_core.py::test_total",
    "tests/test_format.py::test_render"
  ],
  "source_paths": ["calc"],
  "source_dirs": ["calc"],
  "fixtures": {
    "known_good": "fixtures/known-good.patch",
    "known_broken": "fixtures/known-broken.patch"
  }
}
```

`base/pyproject.toml` (the `[tool.satyrn]` line is what Phase 1's `derive` reads, Ruling 12 there; `python` resolves to the engine venv under `uv run`):

```toml
[project]
name = "calc"
version = "0"
requires-python = ">=3.14"

[tool.satyrn]
self_test = ["python", "-m", "pytest", "-q"]
```

`base/.gitignore`: `.pytest_cache/` and `__pycache__/`, one per line. `base/calc/__init__.py`: empty. `base/calc/core.py`: `def total(xs):\n    return 0\n`. `base/tests/test_core.py`: `from calc.core import total\n\n\ndef test_total():\n    assert total([1, 2]) == 3\n`. `base/tests/test_format.py`: `from calc.format import render\n\n\ndef test_render():\n    assert render(1234) == "1,234"\n`.

`fixtures/known-good.patch`:

```diff
diff --git a/calc/core.py b/calc/core.py
index cc02207..1e0f88c 100644
--- a/calc/core.py
+++ b/calc/core.py
@@ -1,2 +1,5 @@
+from calc.helpers import add_all
+
+
 def total(xs):
-    return 0
+    return add_all(xs)
diff --git a/calc/format.py b/calc/format.py
new file mode 100644
index 0000000..61bc7b7
--- /dev/null
+++ b/calc/format.py
@@ -0,0 +1,2 @@
+def render(n):
+    return f"{n:,}"
diff --git a/calc/helpers.py b/calc/helpers.py
new file mode 100644
index 0000000..411fdda
--- /dev/null
+++ b/calc/helpers.py
@@ -0,0 +1,2 @@
+def add_all(xs):
+    return sum(xs)
```

`fixtures/known-broken.patch`:

```diff
diff --git a/calc/format.py b/calc/format.py
new file mode 100644
index 0000000..ae065e7
--- /dev/null
+++ b/calc/format.py
@@ -0,0 +1,2 @@
+def render(n):
+    return None
```

Check: `uv run satyrn-evals grade --tasks-root tests/integration/data/tasks calc-build tests/integration/data/tasks/calc-build/fixtures/known-good.patch --receipt /tmp/kg.json; echo "EXIT: $?"` → 0 and `"verdict": "pass"`; the same with `known-broken.patch` → `"verdict": "fail"`. (`pyproject.toml` already lists `tests/integration/data` in `norecursedirs`.)

- [ ] **Step 2: The fake `pi`.** `tests/integration/fake_pi_build.py`:

```python
#!/usr/bin/env python3
"""Fake `pi` for build-shaped fixture attempts: no model, no network.

``SATYRN_FAKE_PI_MODE`` selects what the fake does in its working directory
(the attempt worktree), while writing a Pi-shaped ``--mode json`` stream to
stdout:

- ``commit`` (default): write calc-build's three GOOD files, commit two of
  them inside the worktree and leave ``calc/format.py`` untracked -- the
  shape that scored ``NO_PATCH`` under ``git diff HEAD``.
- ``write``: write the same files and commit nothing (the Engine arm's
  ``deliver`` commits its own candidate).
- ``idle``: change nothing.
- ``spend``: change nothing, report 20,000 output tokens on each of two
  turns, record its pid in ``SATYRN_FAKE_PI_PIDFILE``, then sleep so only a
  tripwire can end it.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

GOOD = {
    "calc/core.py": "from calc.helpers import add_all\n\n\ndef total(xs):\n    return add_all(xs)\n",
    "calc/helpers.py": "def add_all(xs):\n    return sum(xs)\n",
    "calc/format.py": 'def render(n):\n    return f"{n:,}"\n',
}


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def turn(output_tokens: int) -> None:
    emit({"type": "turn_start"})
    emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": output_tokens}}})
    emit({"type": "turn_end", "message": {"role": "assistant", "content": []}})


def main() -> int:
    mode = os.environ.get("SATYRN_FAKE_PI_MODE", "commit")
    emit({"type": "session", "version": 3, "cwd": os.getcwd()})
    emit({"type": "agent_start"})
    if mode == "spend":
        if pidfile := os.environ.get("SATYRN_FAKE_PI_PIDFILE"):
            Path(pidfile).write_text(str(os.getpid()))
        turn(20_000)
        turn(20_000)
        time.sleep(120)
        return 0
    if mode in ("commit", "write"):
        emit({"type": "turn_start"})
        for index, (path, text) in enumerate(GOOD.items()):
            emit({"type": "tool_execution_start", "toolCallId": f"w{index}", "toolName": "write", "args": {"path": path, "content": text}})
            Path(path).write_text(text)
            emit({"type": "tool_execution_end", "toolCallId": f"w{index}", "toolName": "write", "result": {"content": [{"type": "text", "text": "ok"}]}})
        if mode == "commit":
            command = "git add calc/core.py calc/helpers.py && git commit -qm model"
            emit({"type": "tool_execution_start", "toolCallId": "b0", "toolName": "bash", "args": {"command": command}})
            for argv in (["git", "add", "calc/core.py", "calc/helpers.py"],
                         ["git", "-c", "user.name=fake", "-c", "user.email=fake@example.invalid", "commit", "-qm", "model"]):
                subprocess.run(argv, check=True, capture_output=True)
            emit({"type": "tool_execution_end", "toolCallId": "b0", "toolName": "bash", "result": {"content": [{"type": "text", "text": ""}]}})
        emit({"type": "entry_appended", "entry": {"type": "custom", "customType": "command_bounded", "data": {"action": "set", "timeout": 120}}})
        emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": 300}}})
        emit({"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}})
    else:
        turn(10)
    emit({"type": "agent_end"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Failing tests.**

`tests/integration/test_harvest_qualification.py` (the spec's live-harvest qualification, through the real Baseline adapter):

```python
"""The live-harvest qualification: a build attempt through the real Baseline adapter.

Integration tier: real Git, a real worktree, the real `satyrn-evals-attempt-pi`
harvest, the real oracle. `pi` is `fake_pi_build.py`; no model runs.
"""

import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
KNOWN_GOOD = TASKS / "calc-build" / "fixtures" / "known-good.patch"


def _pi_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "pi"
    shim.write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", mode)


def _baseline() -> list[str]:
    return [sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"]


def test_a_build_attempt_that_commits_and_leaves_a_file_untracked_is_harvested_whole_and_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pi_on_path(tmp_path, monkeypatch, "commit")
    output = tmp_path / "attempts"
    record = attempt(task="calc-build", tasks_root=TASKS, output=output, command=_baseline(), timeout=120)
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    patch = (output / record.attempt_dir / "patch.diff").read_text()
    assert sorted(parse_patch_paths(patch)) == sorted(parse_patch_paths(KNOWN_GOOD.read_text())) == [
        "calc/core.py", "calc/format.py", "calc/helpers.py"]


def test_an_attempt_that_changes_nothing_is_no_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _pi_on_path(tmp_path, monkeypatch, "idle")
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts", command=_baseline(), timeout=120)
    assert record.code is AttemptCode.NO_PATCH
    assert record.command_exit == 0
```

Append to `tests/integration/test_session_patch.py`:

```python
def test_harvest_excludes_runtime_residue_and_keeps_new_files(tmp_path: Path) -> None:
    from satyrn_evals.session_patch import RESIDUE_EXCLUDES

    repo, base = _repo(tmp_path)
    (repo / "new_module.py").write_text("x = 1\n")
    for residue in (".pytest_cache/v/cache/lastfailed", "pkg/__pycache__/m.cpython-314.pyc", ".ruff_cache/0.1/x", ".venv/bin/python"):
        (repo / residue).parent.mkdir(parents=True, exist_ok=True)
        (repo / residue).write_text("residue\n")
    harvested = build_cumulative_patch(repo, base, exclude=RESIDUE_EXCLUDES).patch_text
    assert "new_module.py" in harvested
    assert not any(name in harvested for name in (".pytest_cache", "__pycache__", ".ruff_cache", ".venv"))
    swept = build_cumulative_patch(repo, base).patch_text
    assert ".pytest_cache" in swept  # sibling: the session path's default is unchanged


def test_harvest_survives_a_commit_inside_the_worktree(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    (repo / "edited.txt").write_text("edited v2\n")
    (repo / "committed.txt").write_text("committed\n")
    (repo / "loose.txt").write_text("untracked\n")
    _git(repo, "add", "edited.txt", "committed.txt")
    _git(repo, "-c", "user.name=m", "-c", "user.email=m@m", "commit", "-qm", "model commit")
    assert _git(repo, "diff", "HEAD").stdout == b""  # what the old harvest saw
    capture = build_cumulative_patch(repo, base)
    assert capture.changed_paths == ("committed.txt", "edited.txt", "loose.txt")
```

Append to `tests/test_attempt.py` (uses the file's `_task`, `_install_workspace_double`, `_grade_pass`, `GOOD_PATCH`, `TRANSCRIPT`):

```python
def test_the_command_learns_the_workspace_base_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The adapter harvests against the commit Evals built, not HEAD."""
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    seen: dict[str, Any] = {}

    def run(**kwargs: Any) -> WorkspaceResult:
        seen.update(kwargs)
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).write_text(TRANSCRIPT)
        return WorkspaceResult(WorkspaceCode.OK, "attempt command completed", 0, "b" * 40)

    _install_workspace_double(monkeypatch, run)
    monkeypatch.setattr(attempt_module, "grade", _grade_pass)
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=tmp_path / "attempts", command=["fake-agent"]
    )
    assert record.code is AttemptCode.OK
    assert seen["extra_environment"] == {attempt_module.BASE_SHA_ENV: "b" * 40}
    assert attempt_module.BASE_SHA_ENV not in seen["environment"]
```

In `tests/test_attempt_pi.py`: import `read_base_sha` beside the other adapter names and `from satyrn_evals.session_patch import RESIDUE_EXCLUDES, PatchCapture`; add `BASE = "c" * 40` under `MODEL`; `_FakeRun.__init__(self, *, pi_exit: int)` drops `diff`/`diff_exit` and its `git` branch; the `seam` fixture also sets `monkeypatch.setenv(attempt_pi.BASE_SHA_ENV, BASE)`; add under the fixture:

```python
def _capture(monkeypatch: pytest.MonkeyPatch, patch_text: str) -> list[tuple[object, ...]]:
    """Replace the harvest's Git work with a recorded capture."""
    calls: list[tuple[object, ...]] = []

    def fake(worktree: Path, base: str, environment: object, *, exclude: tuple[str, ...]) -> PatchCapture:
        calls.append((worktree, base, exclude))
        return PatchCapture(patch_text, (), ())

    monkeypatch.setattr(attempt_pi, "build_cumulative_patch", fake)
    return calls
```

`test_the_adapter_reads_exactly_the_names_attempt_exports` gains `assert attempt_pi.BASE_SHA_ENV == attempt.BASE_SHA_ENV`. Replace the two harvest rows with:

```python
def test_harvest_is_the_cumulative_patch_from_the_base_without_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _capture(monkeypatch, "diff --git a/x b/x\n")
    assert harvest_patch(tmp_path, BASE) == "diff --git a/x b/x\n"
    assert calls == [(tmp_path, BASE, RESIDUE_EXCLUDES)]


def test_harvest_refuses_when_git_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sibling success: the row above. An unreadable diff must refuse, not
    write an empty patch that grading would read as `NO_PATCH`."""

    def fail(*_args: object, **_kwargs: object) -> PatchCapture:
        raise subprocess.CalledProcessError(128, ["git", "read-tree"], b"", b"fatal: bad object")

    monkeypatch.setattr(attempt_pi, "build_cumulative_patch", fail)
    with pytest.raises(AdapterError, match="harvest against c+ failed \\(128\\): fatal: bad object"):
        harvest_patch(tmp_path, BASE)


def test_the_base_sha_comes_from_the_environment(seam: dict[str, Path]) -> None:
    assert read_base_sha(os.environ) == BASE


@pytest.mark.parametrize("value", ["", "HEAD", "c" * 39, "C" * 40])
def test_a_missing_or_malformed_base_sha_is_refused(value: str) -> None:
    with pytest.raises(AdapterError, match=attempt_pi.BASE_SHA_ENV):
        read_base_sha({attempt_pi.BASE_SHA_ENV: value} if value else {})
```

The four `test_main_*` rows: `_FakeRun(pi_exit=...)` without `diff`, each calls `_capture(monkeypatch, <the old diff text or "">)` after patching `subprocess.run`; `test_main_preserves_transcript_and_patch_and_returns_pi_exit` replaces its last assertion with `assert len(fake.calls) == 1` and `assert calls == [(Path.cwd(), BASE, RESIDUE_EXCLUDES)]` (keep `calls = _capture(...)`). Append:

```python
def test_main_refuses_before_starting_pi_without_a_base_sha(
    seam: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is spent on a cell whose harvest could not run."""
    fake = _FakeRun(pi_exit=0)
    monkeypatch.setattr(attempt_pi.subprocess, "run", fake)
    monkeypatch.delenv(attempt_pi.BASE_SHA_ENV)
    with pytest.raises(AdapterError, match=attempt_pi.BASE_SHA_ENV):
        main(["--model", MODEL])
    assert fake.calls == []
```

`tests/integration/test_attempt_pi.py` `_run`: before `subprocess.run`, `base = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()`, and the child env gains `attempt_pi.BASE_SHA_ENV: base`.

- [ ] **Step 4: Run to verify failure.** `uv run pytest tests/test_attempt_pi.py tests/test_attempt.py -q` → import errors for `read_base_sha`/`RESIDUE_EXCLUDES`, then `KeyError: 'extra_environment'`. `uv run pytest -m integration tests/integration/test_harvest_qualification.py -q` → the first row fails `attempt refused: NO_PATCH` (the 2026-09-14 defect), the second passes.

- [ ] **Step 5: Implement.**

`session_patch.py`: `from collections.abc import Mapping, Sequence`; after the imports (one blank line before the comment, ruff I001):

```python
#: Runtime residue a model's own tool runs leave in a worktree. A harvest
#: passes these so ``git add -N --all`` never sweeps them into a candidate;
#: the session path passes nothing and is unchanged.
RESIDUE_EXCLUDES: tuple[str, ...] = (
    ":(exclude,glob)**/.pytest_cache/**",
    ":(exclude,glob)**/__pycache__/**",
    ":(exclude,glob)**/.ruff_cache/**",
    ":(exclude,glob)**/.venv/**",
)
```

`build_cumulative_patch` gains `*, exclude: Sequence[str] = ()` after `environment`, and line 75 becomes `_git(worktree, env, "add", "-N", "--all", "--", ".", *exclude)`.

`workspace.run_prepared_command` gains `extra_environment: Mapping[str, str] | None = None` and passes `{**workspace._environment, **(extra_environment or {})}` to `_run_command` in place of `workspace._environment`.

`attempt.py`: `BASE_SHA_ENV = "SATYRN_WORKSPACE_BASE_SHA"` after `TRANSCRIPT_ENV`; the `run_prepared_command(...)` call at 321 gains `extra_environment={BASE_SHA_ENV: workspace_lease.base_sha},`.

`attempt_pi.py`: `import re`; `from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch`; after `TRANSCRIPT_ENV`:

```python
BASE_SHA_ENV = "SATYRN_WORKSPACE_BASE_SHA"
_OBJECT_ID = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
```

Replace `harvest_patch` (194-209) with:

```python
def read_base_sha(environment: Mapping[str, str]) -> str:
    """The workspace base commit Evals exported, refusing anything else."""
    sha = environment.get(BASE_SHA_ENV, "")
    if not _OBJECT_ID.match(sha):
        raise AdapterError(f"{BASE_SHA_ENV} must name the workspace base commit, got {sha!r}")
    return sha


def harvest_patch(worktree: Path, base_sha: str) -> str:
    """Everything the attempt changed since the base commit, as one patch.

    The session path's temporary-index diff: committed, modified and
    untracked files all appear, so a model ``git commit`` hides nothing.
    Runtime residue is excluded. A git failure refuses rather than returning
    "", because an empty patch is a legible outcome (`NO_PATCH`).
    """
    try:
        capture = build_cumulative_patch(worktree, base_sha, os.environ, exclude=RESIDUE_EXCLUDES)
    except subprocess.CalledProcessError as exc:
        detail = os.fsdecode(exc.stderr or b"").strip()
        raise AdapterError(f"harvest against {base_sha} failed ({exc.returncode}): {detail}") from exc
    except OSError as exc:
        raise AdapterError(f"harvest against {base_sha} failed: {exc}") from exc
    return capture.patch_text
```

`main`: `base_sha = read_base_sha(os.environ)` right after `read_artifact_paths` (before pi starts); the last write becomes `patch_path.write_text(harvest_patch(Path.cwd(), base_sha), encoding="utf-8")`. In the module docstring, replace the first "Stated limits" bullet with: "**The harvest is the cumulative diff from the workspace base commit** (`SATYRN_WORKSPACE_BASE_SHA`), untracked files included and runtime residue excluded, so a model `git commit` hides nothing (2026-09-14: four cells scored `NO_PATCH` under `git diff HEAD`)."; the second bullet stays.

- [ ] **Step 6: Pass.** `uv run pytest -q; echo "EXIT: $?"` → 0. `uv run pytest -m integration tests/integration/test_harvest_qualification.py tests/integration/test_session_patch.py tests/integration/test_attempt_pi.py tests/integration/test_repeat_limit_attempt.py -q; echo "EXIT: $?"` → 0.

- [ ] **Step 7: Record, gates, commit.**

```bash
uv run python tools/provenance.py new tests/integration/fake_pi_build.py tests/integration/test_harvest_qualification.py $(find tests/integration/data/tasks/calc-build -type f | sort)
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2a: harvest against the workspace base commit, untracked files included; a committing build attempt grades pass"
```

---

### Task 2: The output-token and turn tripwire, budgets from the run record

**Files:**
- Create: `src/satyrn_evals/budget.py`, `tests/test_budget.py`, `tests/integration/test_budget_attempt.py`
- Modify: `src/satyrn_evals/workspace.py:58-66` (codes), `:97-123` (policies), `:921-993` (`_wait_or_trip`), `:996-1198` (`_run_command`), `run_prepared_command`; `src/satyrn_evals/attempt_record.py:87-101,184-196,406-410`; `src/satyrn_evals/attempt.py:64-69,156-201,321-333`; `src/satyrn_evals/run_record.py`; `src/satyrn_evals/run.py:144-199`; `src/satyrn_evals/cli.py`
- Modify tests: `tests/test_attempt_record.py:655` (the `_valid_v4_record` case gains `| AttemptCode.BUDGET_EXCEEDED`, or `test_v4_code_matrix_accepts_each_code[BUDGET_EXCEEDED]` fails on its missing base sha), `tests/test_run_record.py:10-16` (`GOOD` gains `"token_budget": 32000, "turn_budget": 48`; nine rows fail without it), `tests/test_workspace_failures.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 1's `run_prepared_command(extra_environment=)`, `fake_pi_build.py` mode `spend`, task `calc-build`.
- Produces: `budget.AttemptBudget(output_tokens: int, turns: int)` (positive ints, else `ValueError("budget <name> must be a positive integer, got ...")`); `budget.UsageCounter` (`.turns`, `.output_tokens`, `feed(line: str)`, `feed_event(event: object)`); `budget.BudgetTripwire(budget)` (`feed(line) -> bool`, `.over: Literal["output_tokens", "turns"] | None`, `.usage`, `message() -> str`); `WorkspaceCode.BUDGET_EXCEEDED`, `AttemptCode.BUDGET_EXCEEDED` (both `"BUDGET_EXCEEDED"`); `_wait_or_trip(..., budget: AttemptBudget | None = None) -> tuple[int | None, RepeatTripwire | BudgetTripwire | None]`; `run_prepared_command(..., budget=None)`; `attempt(..., budget: AttemptBudget | None = None)`; `run(..., budget=None)`; `RunRecord.token_budget: int`, `RunRecord.turn_budget: int`; `run_record.attempt_budget(record) -> AttemptBudget`; CLI `attempt|run --run-record PATH`.

- [ ] **Step 1: Failing tests.**

`tests/test_budget.py`:

```python
"""The attempt budget tripwire, over Pi-shaped lines. Pure: no process."""

import json

import pytest

from satyrn_evals.budget import AttemptBudget, BudgetTripwire, UsageCounter


def _turn() -> str:
    return json.dumps({"type": "turn_start"})


def _assistant(output: int, role: str = "assistant") -> str:
    return json.dumps(
        {"type": "message_end", "message": {"role": role, "usage": {"input": 9000, "output": output, "cacheRead": 50000}}}
    )


def test_usage_counts_turns_and_assistant_output_only() -> None:
    counter = UsageCounter()
    for line in (_turn(), _assistant(120), _assistant(999, role="user"), _turn(), _assistant(30), "{partial", ""):
        counter.feed(line)
    assert (counter.turns, counter.output_tokens) == (2, 150)


def test_a_line_that_puts_output_over_budget_trips_and_latches() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=100, turns=48))
    assert not wire.feed(_turn())
    assert not wire.feed(_assistant(100))  # at the budget is within it
    assert wire.feed(_assistant(1))
    assert wire.over == "output_tokens"
    assert wire.feed(_turn())  # latched
    assert wire.message() == "attempt command spent 101 output tokens, over the budget of 100"


def test_the_turn_after_the_last_budgeted_turn_trips() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=32000, turns=2))
    assert not wire.feed(_turn()) and not wire.feed(_turn())
    assert wire.feed(_turn())
    assert wire.over == "turns"
    assert wire.message() == "attempt command started turn 3, over the budget of 2 turns"


def test_a_cell_within_both_budgets_never_trips() -> None:
    wire = BudgetTripwire(AttemptBudget(output_tokens=32000, turns=48))
    assert not any(wire.feed(line) for _ in range(48) for line in (_turn(), _assistant(600)))
    assert wire.over is None


@pytest.mark.parametrize("values", [(0, 48), (32000, 0), (True, 48), (32000, 1.5)])
def test_a_budget_must_be_positive_integers(values: tuple[object, object]) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        AttemptBudget(output_tokens=values[0], turns=values[1])  # type: ignore[arg-type]
```

Append to `tests/test_workspace_failures.py` (uses its `_FakeProcess`, `_process`, `_state`, `cast`):

```python
def _usage_lines(*outputs: int) -> str:
    import json

    return "".join(
        json.dumps({"type": "turn_start"}) + "\n"
        + json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"output": n}}}) + "\n"
        for n in outputs
    )


class _WritesThenExits:
    """A command that writes its last transcript lines and exits in one wait."""

    pid = 42

    def __init__(self, transcript: Path, text: str) -> None:
        self.transcript = transcript
        self.text = text

    def wait(self, timeout: float | None = None) -> int:
        self.transcript.write_text(self.text)
        return 0


def test_budget_trips_on_a_live_transcript_before_the_command_exits(tmp_path: Path) -> None:
    from satyrn_evals.budget import AttemptBudget, BudgetTripwire

    transcript = tmp_path / "transcript.txt"
    transcript.write_text(_usage_lines(20_000, 20_000))
    process = _FakeProcess([])  # never exits on its own
    exit_code, tripped = workspace_module._wait_or_trip(
        _process(process), timeout=5.0, transcript=transcript, limit=None,
        budget=AttemptBudget(output_tokens=32_000, turns=48),
    )
    assert exit_code is None
    assert isinstance(tripped, BudgetTripwire) and tripped.over == "output_tokens"
    assert process.wait_timeouts == []


def test_budget_reads_the_tail_a_command_wrote_before_exiting(tmp_path: Path) -> None:
    from satyrn_evals.budget import AttemptBudget, BudgetTripwire

    transcript = tmp_path / "transcript.txt"
    exit_code, tripped = workspace_module._wait_or_trip(
        cast("subprocess.Popen[bytes]", _WritesThenExits(transcript, _usage_lines(40_000))),
        timeout=5.0, transcript=transcript, limit=None,
        budget=AttemptBudget(output_tokens=32_000, turns=48),
    )
    assert exit_code == 0
    assert isinstance(tripped, BudgetTripwire)


def test_a_command_within_budget_exits_untripped(tmp_path: Path) -> None:
    from satyrn_evals.budget import AttemptBudget

    transcript = tmp_path / "transcript.txt"
    exit_code, tripped = workspace_module._wait_or_trip(
        cast("subprocess.Popen[bytes]", _WritesThenExits(transcript, _usage_lines(3_000, 2_000))),
        timeout=5.0, transcript=transcript, limit=None,
        budget=AttemptBudget(output_tokens=32_000, turns=48),
    )
    assert (exit_code, tripped) == (0, None)


def test_a_finished_command_over_budget_is_budget_exceeded_with_its_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from satyrn_evals.budget import AttemptBudget

    state = _state(tmp_path)
    state.base_sha = "a" * 40
    transcript = tmp_path / "transcript.txt"
    monkeypatch.setattr(
        workspace_module.subprocess, "Popen",
        lambda *_a, **_k: _WritesThenExits(transcript, _usage_lines(40_000)),
    )
    result = workspace_module._run_command(
        ("x",), state, {}, 10.0, 0.1, transcript=transcript,
        budget=AttemptBudget(output_tokens=32_000, turns=48),
    )
    assert (result.code, result.command_exit) == (WorkspaceCode.BUDGET_EXCEEDED, 0)
    assert result.message == "attempt command spent 40000 output tokens, over the budget of 32000"
```

(The live-trip path through `_run_command` is proven in the integration tier: a fake process there would reach `os.killpg` on a fake pid.)

Append to `tests/test_run_record.py` (import `AttemptBudget` and `attempt_budget`):

```python
def test_the_record_carries_the_attempt_budget(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, token_budget=24000, turn_budget=36))
    assert attempt_budget(record) == AttemptBudget(output_tokens=24000, turns=36)


@pytest.mark.parametrize("field", ["token_budget", "turn_budget"])
def test_a_record_without_a_budget_is_refused(tmp_path: Path, field: str) -> None:
    body = {k: v for k, v in GOOD.items() if k != field}
    path = tmp_path / "r.json"
    path.write_text(json.dumps(body))
    with pytest.raises(RunRecordError, match=f"missing {field}"):
        load_run_record(path)


@pytest.mark.parametrize(("field", "value"), [("token_budget", 0), ("turn_budget", -1)])
def test_a_non_positive_budget_is_refused(tmp_path: Path, field: str, value: int) -> None:
    with pytest.raises(RunRecordError, match=f"{field} must be a positive integer"):
        load_run_record(_write(tmp_path, **{field: value}))
```

Append to `tests/test_cli.py` (add `import json` and `from satyrn_evals.budget import AttemptBudget`):

```python
def _record(tmp_path: Path) -> Path:
    path = tmp_path / "record.json"
    path.write_text(json.dumps({
        "version": 1, "task": "format_number", "task_tree_sha256": "a" * 64, "arm": "baseline",
        "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4, "mode": "attended",
        "max_minutes": 60, "stop_rule": "infrastructure only", "decision_rule": "fisher",
        "previous_result": None, "token_budget": 24000, "turn_budget": 36,
    }))
    return path


def test_run_takes_its_budget_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    assert main(["run", "format_number", "--n", "1", "--run-record", str(_record(tmp_path)), "--", "cmd"]) == 0
    assert seen["budget"] == AttemptBudget(output_tokens=24000, turns=36)


def test_run_without_a_record_has_no_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
    assert main(["run", "format_number", "--n", "1", "--", "cmd"]) == 0
    assert seen["budget"] is None


def test_attempt_with_an_unreadable_record_is_a_usage_error(tmp_path: Path) -> None:
    assert main(["attempt", "format_number", "--run-record", str(tmp_path / "absent.json"), "--", "cmd"]) == 2
```

`tests/integration/test_budget_attempt.py`:

```python
"""The output-token and turn budget against a live transcript.

Integration tier: a real worktree, the real Baseline adapter, a fake `pi`
(`fake_pi_build.py`) that reports usage. No model runs. Both directions: a
cell over budget is stopped as `BUDGET_EXCEEDED` with its `pi` gone; the same
adapter within budget is graded.
"""

import os
import sys
import time
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
CAMPAIGN = AttemptBudget(output_tokens=32_000, turns=48)


def _pi_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "pi"
    shim.write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", mode)


def _baseline() -> list[str]:
    return [sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"]


def _gone(pid: int, within: float = 5.0) -> bool:
    stop = time.monotonic() + within
    while time.monotonic() < stop:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_a_cell_over_the_output_budget_is_stopped_as_budget_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pi_on_path(tmp_path, monkeypatch, "spend")
    pidfile = tmp_path / "pi.pid"
    monkeypatch.setenv("SATYRN_FAKE_PI_PIDFILE", str(pidfile))
    started = time.monotonic()
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts",
                     command=_baseline(), timeout=120, budget=CAMPAIGN)
    assert time.monotonic() - started < 60  # the fake sleeps 120 s; only the budget ends it
    assert (record.code, record.outcome) == (AttemptCode.BUDGET_EXCEEDED, AttemptOutcome.REFUSED)
    assert record.message == "attempt command spent 40000 output tokens, over the budget of 32000"
    assert record.command_exit is None and record.verdict is None
    assert _gone(int(pidfile.read_text()))


def test_the_same_adapter_within_budget_is_graded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _pi_on_path(tmp_path, monkeypatch, "commit")
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts",
                     command=_baseline(), timeout=120, budget=CAMPAIGN)
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_budget.py tests/test_workspace_failures.py tests/test_run_record.py tests/test_cli.py -q` → `ModuleNotFoundError: satyrn_evals.budget`, `unexpected keyword argument 'budget'`, the new run-record rows fail.

- [ ] **Step 3: Implement.**

`src/satyrn_evals/budget.py`:

```python
"""The attempt budget: output tokens and turns, counted as the transcript is written.

Spec "Budget, both arms": 32,000 output tokens (thinking included) and 48
turns per attempt, "enforced by the harness reading the transcript as it is
written. A cell over either is ``BUDGET_EXCEEDED``, a fail." The values are
the campaign's and reach an attempt from the run record
(``run_record.attempt_budget``); this module holds no defaults.

The counted shapes are the ones the engine's receipt counts from the same
stream (satyrn-engine Phase 1 Task 2): one ``turn_start`` is one turn; an
assistant ``message_end`` adds its ``usage.output``. ``cacheRead`` and input
tokens are not budget.
"""

import json
from dataclasses import dataclass
from typing import Literal

type BudgetDimension = Literal["output_tokens", "turns"]


@dataclass(frozen=True, slots=True)
class AttemptBudget:
    """The per-attempt budget a run record froze."""

    output_tokens: int
    turns: int

    def __post_init__(self) -> None:
        for name in ("output_tokens", "turns"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"budget {name} must be a positive integer, got {value!r}")


class UsageCounter:
    """Turns and assistant output tokens over Pi ``--mode json`` lines.

    Lenient by design, like the repeat tripwire: a live transcript can carry
    a partial write, and an unparseable line counts as nothing.
    """

    def __init__(self) -> None:
        self.turns = 0
        self.output_tokens = 0

    def feed_event(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        match event.get("type"):
            case "turn_start":
                self.turns += 1
            case "message_end":
                message = event.get("message")
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    return
                usage = message.get("usage")
                output = usage.get("output") if isinstance(usage, dict) else None
                if type(output) is int and output >= 0:
                    self.output_tokens += output

    def feed(self, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError, TypeError:
            return
        self.feed_event(event)


class BudgetTripwire:
    """Latching detector: trips on the first line that puts usage over budget."""

    def __init__(self, budget: AttemptBudget) -> None:
        self.budget = budget
        self.usage = UsageCounter()
        self._over: BudgetDimension | None = None

    @property
    def over(self) -> BudgetDimension | None:
        return self._over

    def feed(self, line: str) -> bool:
        """Consume one transcript line; return whether the budget is exceeded."""
        if self._over is None:
            self.usage.feed(line)
            if self.usage.output_tokens > self.budget.output_tokens:
                self._over = "output_tokens"
            elif self.usage.turns > self.budget.turns:
                self._over = "turns"
        return self._over is not None

    def message(self) -> str:
        if self._over == "turns":
            return (
                f"attempt command started turn {self.usage.turns}, over the "
                f"budget of {self.budget.turns} turns"
            )
        return (
            f"attempt command spent {self.usage.output_tokens} output tokens, "
            f"over the budget of {self.budget.output_tokens}"
        )
```

`workspace.py`: `from satyrn_evals.budget import AttemptBudget, BudgetTripwire`. `WorkspaceCode.BUDGET_EXCEEDED = "BUDGET_EXCEEDED"` after `REPEAT_LIMIT`; its policy before `CLEANUP_FAILED`: `_WorkspacePolicy(_Presence.OPTIONAL, _Presence.REQUIRED, _Presence.FORBIDDEN)` with the comment "Torn down live (no exit code), or observed over budget in the lines the command wrote just before it exited (its exit code)." `_wait_or_trip` gains `budget: AttemptBudget | None = None` (last keyword) and returns `tuple[int | None, RepeatTripwire | BudgetTripwire | None]`; its fast path condition becomes `if transcript is None or (limit is None and budget is None):`; the tail section becomes:

```python
    wire = RepeatTripwire(limit) if limit is not None else None
    budget_wire = BudgetTripwire(budget) if budget is not None else None

    def tripped_by(line: str) -> RepeatTripwire | BudgetTripwire | None:
        if budget_wire is not None and budget_wire.feed(line):
            return budget_wire
        if wire is not None and wire.feed(line):
            return wire
        return None
```

In the loop, `if wire.feed(line): whole_remaining(); return None, wire` becomes `if (tripped := tripped_by(line)) is not None: whole_remaining(); return None, tripped`. After the successful `process.wait` and its `whole_remaining()`, before `return result, None`:

```python
            if budget_wire is not None:
                # A command that finished over budget is still over it: read
                # what it wrote after the last poll. The repeat rule is a
                # live spending rule and is not applied to this tail.
                if handle is None and transcript.is_file():
                    handle = transcript.open("rb")
                if handle is not None:
                    pending += handle.read().decode("utf-8", errors="replace")
                if any(budget_wire.feed(line) for line in pending.split("\n")):
                    return result, budget_wire
```

Update the docstring: "…or `(None, wire)` when the repeated-call limit or the budget tripped first; `(exit code, budget wire)` when the budget was exceeded by lines the command wrote before exiting. With neither `limit` nor `budget` the tailing is skipped entirely." `_run_command` gains `budget: AttemptBudget | None = None`, passes `budget=budget` to `_wait_or_trip`, types `tripped: RepeatTripwire | BudgetTripwire | None`, and its `else:` branch begins:

```python
                if isinstance(tripped, BudgetTripwire) and command_exit is not None:
                    # Over budget in the lines written just before a normal
                    # exit: nothing to tear down, the cell is still a fail.
                    state.process_cleanup_safe = True
                    pending = WorkspaceResult(
                        WorkspaceCode.BUDGET_EXCEEDED,
                        tripped.message(),
                        command_exit,
                        state.base_sha,
                    )
                elif tripped is not None:
```

and, inside that `elif`, after `state.process_cleanup_safe = safe`:

```python
                    stopped = (
                        (WorkspaceCode.BUDGET_EXCEEDED, tripped.message(), "budget")
                        if isinstance(tripped, BudgetTripwire)
                        else (
                            WorkspaceCode.REPEAT_LIMIT,
                            f"attempt command repeated one tool call "
                            f"{tripped.run} times, at the limit of "
                            f"{tripped.limit}",
                            "repeat-limit",
                        )
                    )
                    pending = (
                        WorkspaceResult(stopped[0], stopped[1], None, state.base_sha)
                        if safe
                        else WorkspaceResult(
                            WorkspaceCode.CLEANUP_FAILED,
                            f"{stopped[2]} cleanup is unconfirmed: {detail}",
                            None,
                            state.base_sha,
                            os.fspath(state.parent),
                        )
                    )
```

(the old `else:` OK branch is unchanged). `run_prepared_command` gains `budget: AttemptBudget | None = None` and passes it.

`attempt_record.py`: `BUDGET_EXCEEDED = "BUDGET_EXCEEDED"` after `REPEAT_LIMIT`; its policy before `MODEL_ERROR`: `_AttemptPolicy(AttemptOutcome.REFUSED, _Presence.OPTIONAL, _Presence.REQUIRED, _Presence.FORBIDDEN, _ArtifactPolicy.ANY)` with the comment "Over the run record's output-token or turn budget (spec 'Budget, both arms'): a fail. Usually torn down live, so no exit code; a command seen over budget only in its last lines keeps its exit."; in `allowed_phases`, `AttemptCode.BUDGET_EXCEEDED: frozenset({DeadlinePhase.PRESERVATION, DeadlinePhase.CLEANUP})` beside `REPEAT_LIMIT`.

`attempt.py`: import `AttemptBudget` from `satyrn_evals.budget`; `_WORKSPACE_ATTEMPT_CODES[WorkspaceCode.BUDGET_EXCEEDED] = AttemptCode.BUDGET_EXCEEDED`; `attempt()` and `_attempt()` gain `budget: AttemptBudget | None = None` (passed through); `run_prepared_command(...)` gains `budget=budget`; the deadline check tuple after it gains `WorkspaceCode.BUDGET_EXCEEDED`.

`run_record.py`: import `AttemptBudget`; `RunRecord` gains, after `previous_result`, `token_budget: int` and `turn_budget: int` (comment: the campaign budget per attempt, spec "Budget, both arms"); `_REQUIRED` gains `"token_budget": int, "turn_budget": int`; before the rule-field loop, `for field in ("token_budget", "turn_budget"): if body[field] < 1: raise RunRecordError(f"run record {path}: {field} must be a positive integer")`; add:

```python
def attempt_budget(record: RunRecord) -> AttemptBudget:
    """The budget every attempt under this record is held to."""
    return AttemptBudget(output_tokens=record.token_budget, turns=record.turn_budget)
```

`run.py`: import `AttemptBudget`; `run()` gains `budget: AttemptBudget | None = None`; after the `attempt_timeout` kwarg line, `if budget is not None: attempt_kwargs["budget"] = budget` (the default-tier double at `tests/test_run.py:85-95` takes no `budget`).

`cli.py`: import `AttemptBudget` and `attempt_budget`; add

```python
def _budget(run_record: str | None) -> AttemptBudget | None:
    """The attempt budget a run record froze; none without a record."""
    return None if run_record is None else attempt_budget(load_run_record(Path(run_record)))
```

the `attempt(` and `run(` calls in `main` gain `budget=_budget(args.run_record),`; `attempt_p` and `run_p` gain `--run-record` (`default=None`, help: "run record JSON whose token_budget and turn_budget stop the cell (default: no budget)").

In `tests/test_attempt_record.py:655` the case becomes `case AttemptCode.COMMAND_TIMEOUT | AttemptCode.REPEAT_LIMIT | AttemptCode.BUDGET_EXCEEDED:`; in `tests/test_run_record.py`, `GOOD` gains the two fields.

- [ ] **Step 4: Pass.** `uv run pytest -q; echo "EXIT: $?"` → 0. `uv run pytest -m integration tests/integration/test_budget_attempt.py tests/integration/test_repeat_limit_attempt.py tests/integration/test_harvest_qualification.py tests/integration/test_run.py -q; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/budget.py tests/test_budget.py tests/integration/test_budget_attempt.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2a: output-token and turn tripwire read live from the transcript; BUDGET_EXCEEDED; budgets from the run record"
```

---

### Task 3: The tool-call timeline and the per-cell detectors

**Files:**
- Create: `src/satyrn_evals/timeline.py`, `src/satyrn_evals/cell_evidence.py`, `tests/test_timeline.py`, `tests/test_cell_evidence.py`, `tests/integration/test_timeline_attempt.py`
- Modify: `src/satyrn_evals/workspace.py` (`_wait_or_trip`, `_run_command`, `run_prepared_command`), `src/satyrn_evals/attempt.py` (`run_prepared_command` call), `tests/test_workspace_failures.py`

**Interfaces:**
- Consumes: Task 2's `budget.UsageCounter`, `_WritesThenExits` (test helper, Task 2), `fake_pi_build.py` mode `commit`.
- Produces: `timeline.TIMELINE_NAME = "timeline.jsonl"`; `timeline.TimelineWriter(path: Path, clock: Callable[[], float] = time.time)` (`feed(line)`, `close()`; record `{"at", "event": "start"|"end", "toolCallId", "toolName"}`); `timeline.ToolSpan(tool_name, started, ended)` with `.seconds`; `timeline.read_timeline(text) -> dict[str, ToolSpan]`; `_wait_or_trip(..., timeline: Path | None = None)`, `run_prepared_command(..., timeline=None)`; every `attempt()` writes `<attempt_dir>/timeline.jsonl`; `cell_evidence.LONG_COMMAND_SECONDS = 120.0`; `cell_evidence.CellEvidence` (fields in `to_block` order: `turns, output_tokens, tool_calls, root_searches, bash_outside_paths, file_tool_escapes, git_commits, tool_reported_timeouts, guard_firings, timeline, commands_over_120s, unfinished_commands, longest_command_seconds, overlay_windows`; `to_block() -> dict[str, object]`); `collect_evidence(transcript: str, *, timeline: str | None = None, overlay: OverlaySpec | None = None, visible_texts: Sequence[str] = ()) -> CellEvidence`; `outside(cwd: str | None, path: str) -> bool`, `root_search(command, cwd) -> bool`, `outside_paths(command, cwd) -> bool`, `git_commit(command) -> bool`.

- [ ] **Step 1: Failing tests.**

`tests/test_timeline.py`:

```python
"""The harness's tool-call timeline: stamped as read, read back as spans."""

import json
from pathlib import Path

from satyrn_evals.timeline import TimelineWriter, ToolSpan, read_timeline


def _clock(*values: float):
    stamps = iter(values)
    return lambda: next(stamps)


def test_the_writer_stamps_only_tool_starts_and_ends(tmp_path: Path) -> None:
    path = tmp_path / "timeline.jsonl"
    writer = TimelineWriter(path, clock=_clock(10.0, 131.5))
    for line in (
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "tool_execution_start", "toolCallId": "c1", "toolName": "bash", "args": {}}),
        "{half a line",
        json.dumps({"type": "tool_execution_update", "toolCallId": "c1", "toolName": "bash"}),
        json.dumps({"type": "tool_execution_end", "toolCallId": "c1", "toolName": "bash"}),
    ):
        writer.feed(line)
    writer.close()
    assert [json.loads(line) for line in path.read_text().splitlines()] == [
        {"at": 10.0, "event": "start", "toolCallId": "c1", "toolName": "bash"},
        {"at": 131.5, "event": "end", "toolCallId": "c1", "toolName": "bash"},
    ]


def test_spans_pair_starts_with_ends_and_keep_unfinished_calls() -> None:
    text = "\n".join(
        json.dumps(record)
        for record in (
            {"at": 1.0, "event": "start", "toolCallId": "a", "toolName": "bash"},
            {"at": 2.0, "event": "start", "toolCallId": "b", "toolName": "read"},
            {"at": 2.5, "event": "end", "toolCallId": "b", "toolName": "read"},
            {"at": 3.0, "event": "end", "toolCallId": "zzz", "toolName": "bash"},
        )
    ) + "\nnot json\n"
    spans = read_timeline(text)
    assert spans == {"a": ToolSpan("bash", 1.0, None), "b": ToolSpan("read", 2.0, 2.5)}
    assert spans["b"].seconds == 0.5 and spans["a"].seconds is None
```

`tests/test_cell_evidence.py`:

```python
"""Per-cell evidence over partial and complete transcripts. Pure: no process.

Each detector has a firing row and a silent row. The firing shapes are the
retained ceiling-probe ones (rationale Q6 #4): `find /` piped into grep, a
`read` of an absolute path under pytest's basetemp, `git commit` inside the
worktree, and a cell cut while a command was still running.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.cell_evidence import collect_evidence, git_commit, outside, outside_paths, root_search
from satyrn_evals.overlay import OverlaySpec

CWD = "/private/var/folders/m4/x/T/satyrn-attempt-1/worktree"


def _line(event: dict) -> str:
    return json.dumps(event)


def _bash(call_id: str, command: str) -> list[str]:
    return [
        _line({"type": "tool_execution_start", "toolCallId": call_id, "toolName": "bash", "args": {"command": command}}),
        _line({"type": "tool_execution_end", "toolCallId": call_id, "toolName": "bash", "result": {"content": [{"type": "text", "text": ""}]}}),
    ]


def _transcript(*lines: str, header: bool = True) -> str:
    head = [_line({"type": "session", "version": 3, "cwd": CWD})] if header else []
    return "\n".join([*head, _line({"type": "turn_start"}), *lines]) + "\n"


@pytest.mark.parametrize(
    "command",
    [
        'find / -name "*.py" 2>/dev/null | xargs grep -l "casefold\\|declares_english"',
        "grep -rn test_acceptance ~/projects",
        "ls -R /Users/pauleveritt/satyrn-smokes",
        "mdfind test_acceptance.py",
        "sudo find /private/var/folders -name overlay",
    ],
)
def test_root_anchored_searches_fire(command: str) -> None:
    assert root_search(command, CWD)


@pytest.mark.parametrize(
    "command",
    [
        "find . -name '*.py'",
        f"find {CWD} -name '*.py'",
        "find /var/folders/m4/x/T/satyrn-attempt-1/worktree/tests -name 'test_*.py'",
        "ls -lart /tmp",
        "grep -n casefold app.py",
        "uv run python -m pytest tests/ 2>/dev/null",
    ],
)
def test_searches_inside_the_worktree_and_plain_listings_are_silent(command: str) -> None:
    assert not root_search(command, CWD)


def test_outside_paths_in_bash_text_fire_and_device_paths_and_urls_do_not() -> None:
    assert outside_paths("cat /private/var/folders/m4/x/T/pytest-of-p/pytest-1419/overlay/test_acceptance.py", CWD)
    assert outside_paths("python /tmp/harness.py > /tmp/out.txt", CWD)
    assert not outside_paths(f"cat {CWD}/app.py 2>/dev/null", CWD)
    assert not outside_paths("curl -s https://example.com/x | head", CWD)
    assert not outside_paths('python -c "print(1)"', CWD)


def test_file_tool_paths_are_outside_only_when_they_leave_the_worktree() -> None:
    assert outside(CWD, "/private/var/folders/m4/x/T/pytest-of-p/pytest-1419/x/overlay/test_acceptance.py")
    assert outside(CWD, "../seed/app.py")
    assert not outside(CWD, "app.py")
    assert not outside(CWD, "/var/folders/m4/x/T/satyrn-attempt-1/worktree/app.py")


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("git add -A && git commit -qm 'done'", True),
        ("git -C . -c user.name=m commit -m x", True),
        ("git status && git diff HEAD", False),
        ("echo 'git commit'", False),
    ],
)
def test_git_commit_inside_the_worktree(command: str, expected: bool) -> None:
    assert git_commit(command) is expected


def test_a_timed_out_cell_without_agent_end_still_yields_every_count() -> None:
    """V10 refuses this transcript and publishes nothing; evidence reads it."""
    text = _transcript(
        _line({"type": "message_end", "message": {"role": "assistant", "usage": {"output": 1500}}}),
        _line({"type": "tool_execution_start", "toolCallId": "r1", "toolName": "read",
               "args": {"path": "/private/var/folders/m4/x/T/pytest-of-p/pytest-1419/overlay/test_acceptance.py"}}),
        *_bash("b1", "git add -A && git commit -qm wip"),
        _line({"type": "entry_appended", "entry": {"type": "custom", "customType": "command_bounded", "data": {}}}),
        _line({"type": "tool_execution_start", "toolCallId": "b2", "toolName": "bash", "args": {"command": "find / -name test_acceptance.py"}}),
    )
    block = collect_evidence(text).to_block()
    assert block == {
        "turns": 1, "output_tokens": 1500, "tool_calls": 3, "root_searches": 1, "bash_outside_paths": 1,
        "file_tool_escapes": 1, "git_commits": 1, "tool_reported_timeouts": 0,
        "guard_firings": {"command_bounded": 1}, "timeline": False, "commands_over_120s": 0,
        "unfinished_commands": 0, "longest_command_seconds": None, "overlay_windows": None,
    }


def test_a_clean_cell_counts_nothing_suspicious() -> None:
    block = collect_evidence(_transcript(*_bash("b1", "uv run python -m pytest -q"))).to_block()
    assert (block["root_searches"], block["bash_outside_paths"], block["file_tool_escapes"], block["git_commits"]) == (0, 0, 0, 0)
    assert block["guard_firings"] == {}


def test_the_timeline_gives_long_and_unfinished_commands() -> None:
    timeline = "\n".join(
        json.dumps(record)
        for record in (
            {"at": 100.0, "event": "start", "toolCallId": "b1", "toolName": "bash"},
            {"at": 102.5, "event": "end", "toolCallId": "b1", "toolName": "bash"},
            {"at": 110.0, "event": "start", "toolCallId": "b2", "toolName": "bash"},
            {"at": 231.0, "event": "end", "toolCallId": "b2", "toolName": "bash"},
            {"at": 240.0, "event": "start", "toolCallId": "b3", "toolName": "bash"},
            {"at": 241.0, "event": "start", "toolCallId": "r1", "toolName": "read"},
        )
    )
    block = collect_evidence(_transcript(), timeline=timeline).to_block()
    assert (block["timeline"], block["commands_over_120s"], block["unfinished_commands"], block["longest_command_seconds"]) == (True, 1, 1, 121.0)


def test_a_tool_reported_timeout_is_counted_from_the_result_text() -> None:
    end = _line({"type": "tool_execution_end", "toolCallId": "b1", "toolName": "bash", "isError": True,
                 "result": {"content": [{"type": "text", "text": "partial output\n\nCommand timed out after 120 seconds"}]}})
    start = _line({"type": "tool_execution_start", "toolCallId": "b1", "toolName": "bash", "args": {"command": "find / -name x"}})
    assert collect_evidence(_transcript(start, end)).tool_reported_timeouts == 1
    assert collect_evidence(_transcript(*_bash("b2", "sleep 1"))).tool_reported_timeouts == 0


def test_overlay_windows_are_scanned_for_hidden_tasks_only() -> None:
    hidden = "def test_hidden():\n    a = 1\n    b = 2\n    assert a + b == 3\n"
    spec = OverlaySpec(root=Path("/tasks/t/overlay"), rel_paths=("tests/test_hidden.py",), digests={}, texts={"tests/test_hidden.py": hidden})
    leak = _line({"type": "tool_execution_end", "toolCallId": "r1", "toolName": "read",
                  "result": {"content": [{"type": "text", "text": hidden}]}})
    assert collect_evidence(_transcript(leak), overlay=spec).overlay_windows == 1
    assert collect_evidence(_transcript(*_bash("b1", "ls")), overlay=spec).overlay_windows == 0
    assert collect_evidence(_transcript(leak)).overlay_windows is None
```

(The timeout text is Pi 0.85.1's `bash.js` thrown error, `…/research/pi-bash-bounding.md:117`.)

Append to `tests/test_workspace_failures.py`:

```python
def test_the_timeline_stamps_tool_lines_including_the_tail_read_after_exit(tmp_path: Path) -> None:
    import json

    from satyrn_evals.timeline import read_timeline

    transcript = tmp_path / "transcript.txt"
    timeline = tmp_path / "timeline.jsonl"
    lines = "".join(
        json.dumps(event) + "\n"
        for event in (
            {"type": "tool_execution_start", "toolCallId": "b1", "toolName": "bash", "args": {"command": "ls"}},
            {"type": "tool_execution_end", "toolCallId": "b1", "toolName": "bash"},
        )
    )
    exit_code, tripped = workspace_module._wait_or_trip(
        cast("subprocess.Popen[bytes]", _WritesThenExits(transcript, lines)),
        timeout=5.0, transcript=transcript, limit=None, timeline=timeline,
    )
    assert (exit_code, tripped) == (0, None)
    span = read_timeline(timeline.read_text())["b1"]
    assert span.tool_name == "bash" and span.ended is not None and span.ended >= span.started


def test_no_timeline_is_written_when_none_is_asked_for(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("")
    exit_code, tripped = workspace_module._wait_or_trip(
        _process(_FakeProcess([0])), timeout=5.0, transcript=transcript, limit=None
    )
    assert (exit_code, tripped) == (0, None)
    assert list(tmp_path.iterdir()) == [transcript]
```

`tests/integration/test_timeline_attempt.py`:

```python
"""The harness timeline beside a real attempt: both arms get it from the harness."""

import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.timeline import TIMELINE_NAME, read_timeline

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"


def test_every_tool_call_of_an_attempt_has_a_start_and_an_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pi").write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    (bin_dir / "pi").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", "commit")
    output = tmp_path / "attempts"
    record = attempt(task="calc-build", tasks_root=TASKS, output=output,
                     command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"], timeout=120)
    assert record.code is AttemptCode.OK and record.attempt_dir is not None
    spans = read_timeline((output / record.attempt_dir / TIMELINE_NAME).read_text())
    assert sorted(spans) == ["b0", "w0", "w1", "w2"]
    assert all(span.ended is not None for span in spans.values())
    assert spans["b0"].tool_name == "bash"
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_timeline.py tests/test_cell_evidence.py tests/test_workspace_failures.py -q` → `ModuleNotFoundError` for both modules; `unexpected keyword argument 'timeline'`.

- [ ] **Step 3: Implement.**

`src/satyrn_evals/timeline.py`:

```python
"""The tool-call timeline: when the harness read each tool call start and end.

Pi's ``--mode json`` events carry no timestamps, so per-command seconds
cannot be recovered from a transcript afterwards. The harness already reads
the transcript as it is written (``workspace._wait_or_trip``); it stamps the
wall-clock moment it read each ``tool_execution_start`` and
``tool_execution_end`` line into ``timeline.jsonl`` beside the transcript.
One writer serves both arms, and nothing the model's tools write is used.

Resolution is the harness's poll interval (0.25 s): a stamp is when the line
was read, never earlier than when it was written. Seconds are reported per
machine and never compared across machines (spec, "Budget, both arms").
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

TIMELINE_NAME = "timeline.jsonl"
_EVENTS = {"tool_execution_start": "start", "tool_execution_end": "end"}


class TimelineWriter:
    """Append one stamped record per tool start or end line fed to it."""

    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self._handle = path.open("a", encoding="utf-8")
        self._clock = clock

    def feed(self, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError, TypeError:
            return
        if not isinstance(event, dict) or (kind := _EVENTS.get(event.get("type"))) is None:
            return
        call_id, tool = event.get("toolCallId"), event.get("toolName")
        if not isinstance(call_id, str) or not isinstance(tool, str):
            return
        record = {"at": self._clock(), "event": kind, "toolCallId": call_id, "toolName": tool}
        self._handle.write(json.dumps(record) + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


@dataclass(frozen=True, slots=True)
class ToolSpan:
    """One tool call as the harness saw it; ``ended`` is None if it never ended."""

    tool_name: str
    started: float
    ended: float | None

    @property
    def seconds(self) -> float | None:
        return None if self.ended is None else self.ended - self.started


def read_timeline(text: str) -> dict[str, ToolSpan]:
    """Spans by tool call id, in start order. Lenient: bad lines are skipped."""
    spans: dict[str, ToolSpan] = {}
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        call_id, tool, at = record.get("toolCallId"), record.get("toolName"), record.get("at")
        if not isinstance(call_id, str) or not isinstance(tool, str) or type(at) not in (int, float):
            continue
        match record.get("event"):
            case "start" if call_id not in spans:
                spans[call_id] = ToolSpan(tool, float(at), None)
            case "end" if call_id in spans and spans[call_id].ended is None:
                spans[call_id] = ToolSpan(tool, spans[call_id].started, float(at))
    return spans
```

`src/satyrn_evals/cell_evidence.py`:

```python
"""Per-cell evidence for every cell, whatever its code (spec "Measures, per cell").

Where V10 (``pathology.py``) refuses a whole transcript on one unknown event
or a missing ``agent_end`` -- which is every ``COMMAND_TIMEOUT`` and
``BUDGET_EXCEEDED`` cell -- this reads what it can, like the V16 census, and
never voids a cell. Pure: transcript text (and optionally the harness
timeline and the task overlay) in, one block out. No filesystem, no process.

The escape rules are lexical and stated so a reader can recompute them:

- a **path token** in a ``bash`` command is a word that starts with ``/``,
  ``~`` or ``$HOME`` (redirection targets included; ``/dev/null``,
  ``/dev/stdout``, ``/dev/stderr`` and ``/dev/tty`` excluded; ``//`` is a
  URL fragment, not a path);
- it is **outside** when it is ``~``/``$HOME``-rooted, or when its normalized
  form is not under the transcript's ``session`` cwd (``/private/var`` and
  ``/var``, ``/private/tmp`` and ``/tmp`` are the same place on macOS);
- a **root-anchored search** is a simple command whose program is ``find``,
  ``fd``, ``rg``, ``tree``, ``locate`` or ``mdfind``, or ``grep`` with
  ``-r``/``-R``, or ``ls -R``, with any outside path operand (``locate`` and
  ``mdfind`` search the disk and always count);
- relative escapes in bash text (``cd .. && find .``) are not counted; a
  file tool's ``..`` path is.
"""

import json
import posixpath
import re
import shlex
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from satyrn_evals.budget import UsageCounter
from satyrn_evals.contamination import scan_transcript
from satyrn_evals.overlay import OverlaySpec
from satyrn_evals.pathology import decoded_scan_text
from satyrn_evals.timeline import read_timeline

#: The spec's per-command threshold: "commands over 120 s".
LONG_COMMAND_SECONDS = 120.0
_DEVICE_PATHS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"})
_SEARCH_PROGRAMS = frozenset({"find", "fd", "rg", "tree"})
_DISK_SEARCH_PROGRAMS = frozenset({"locate", "mdfind"})
#: Which short flags make a listing or grep recursive (``ls -r`` only reverses).
_RECURSIVE_FLAGS = {"grep": "rR", "egrep": "rR", "fgrep": "rR", "ls": "R"}
_FILE_TOOLS = frozenset({"read", "edit", "write"})
_TIMED_OUT = re.compile(r"Command timed out after \d+(?:\.\d+)? seconds")
_SEPARATORS = frozenset("|&;()")


@dataclass(frozen=True, slots=True)
class CellEvidence:
    turns: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    root_searches: int = 0
    bash_outside_paths: int = 0
    file_tool_escapes: int = 0
    git_commits: int = 0
    tool_reported_timeouts: int = 0
    guard_firings: dict[str, int] = field(default_factory=dict)
    timeline: bool = False
    commands_over_120s: int = 0
    unfinished_commands: int = 0
    longest_command_seconds: float | None = None
    overlay_windows: int | None = None

    def to_block(self) -> dict[str, object]:
        return {
            "turns": self.turns,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "root_searches": self.root_searches,
            "bash_outside_paths": self.bash_outside_paths,
            "file_tool_escapes": self.file_tool_escapes,
            "git_commits": self.git_commits,
            "tool_reported_timeouts": self.tool_reported_timeouts,
            "guard_firings": dict(sorted(self.guard_firings.items())),
            "timeline": self.timeline,
            "commands_over_120s": self.commands_over_120s,
            "unfinished_commands": self.unfinished_commands,
            "longest_command_seconds": self.longest_command_seconds,
            "overlay_windows": self.overlay_windows,
        }


def _events(text: str) -> list[dict]:
    events: list[dict] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _canonical(path: str) -> str:
    normalized = posixpath.normpath(path)
    for alias in ("/private/var", "/private/tmp"):
        if normalized == alias or normalized.startswith(alias + "/"):
            return normalized.removeprefix("/private")
    return normalized


def outside(cwd: str | None, path: str) -> bool:
    """Whether a path token or file-tool path leaves the worktree."""
    if path.startswith(("~", "$HOME")):
        return True
    if cwd is None:
        return posixpath.isabs(path)
    candidate = path if posixpath.isabs(path) else posixpath.join(cwd, path)
    return not PurePosixPath(_canonical(candidate)).is_relative_to(_canonical(cwd))


def _segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token and set(token) <= _SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def _path_tokens(words: Sequence[str]) -> list[str]:
    paths: list[str] = []
    for word in words:
        value = word.split("=", 1)[1] if word.startswith("-") and "=" in word else word
        if value.startswith("//") or value in _DEVICE_PATHS:
            continue
        if value.startswith(("/", "~", "$HOME")):
            paths.append(value)
    return paths


def _program(words: Sequence[str]) -> tuple[str, list[str]]:
    index = 0
    while index < len(words) and (words[index] in ("sudo", "command", "exec") or re.match(r"^\w+=", words[index])):
        index += 1
    if index == len(words):
        return "", []
    return posixpath.basename(words[index]), list(words[index + 1 :])


def root_search(command: str, cwd: str | None) -> bool:
    for segment in _segments(command):
        program, rest = _program(segment)
        if program in _DISK_SEARCH_PROGRAMS:
            return True
        flags = _RECURSIVE_FLAGS.get(program, "")
        recursive = bool(flags) and any(
            word == "--recursive" or (re.fullmatch(r"-[A-Za-z]+", word) is not None and any(f in word for f in flags))
            for word in rest
        )
        if (program in _SEARCH_PROGRAMS or recursive) and any(outside(cwd, p) for p in _path_tokens(rest)):
            return True
    return False


def outside_paths(command: str, cwd: str | None) -> bool:
    return any(outside(cwd, p) for segment in _segments(command) for p in _path_tokens(segment))


def git_commit(command: str) -> bool:
    for segment in _segments(command):
        program, rest = _program(segment)
        if program != "git":
            continue
        index = 0
        while index < len(rest) and rest[index].startswith("-"):
            index += 2 if rest[index] in ("-C", "-c") else 1
        if index < len(rest) and rest[index] == "commit":
            return True
    return False


def _result_text(event: dict) -> str:
    result = event.get("result")
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list):
        return ""
    return "\n".join(
        part["text"] for part in content if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def collect_evidence(
    transcript: str,
    *,
    timeline: str | None = None,
    overlay: OverlaySpec | None = None,
    visible_texts: Sequence[str] = (),
) -> CellEvidence:
    events = _events(transcript)
    cwd = next(
        (e["cwd"] for e in events if e.get("type") == "session" and isinstance(e.get("cwd"), str) and e["cwd"]),
        None,
    )
    usage = UsageCounter()
    for event in events:
        usage.feed_event(event)
    starts = [e for e in events if e.get("type") == "tool_execution_start" and isinstance(e.get("toolName"), str)]
    commands = [
        e["args"]["command"]
        for e in starts
        if e["toolName"] == "bash" and isinstance(e.get("args"), dict) and isinstance(e["args"].get("command"), str)
    ]
    file_paths = [
        e["args"]["path"]
        for e in starts
        if e["toolName"] in _FILE_TOOLS and isinstance(e.get("args"), dict) and isinstance(e["args"].get("path"), str)
    ]
    guard_firings = Counter(
        e["entry"]["customType"]
        for e in events
        if e.get("type") == "entry_appended"
        and isinstance(e.get("entry"), dict)
        and isinstance(e["entry"].get("customType"), str)
    )
    timeouts = sum(
        1
        for e in events
        if e.get("type") == "tool_execution_end" and e.get("toolName") == "bash" and _TIMED_OUT.search(_result_text(e))
    )
    spans = [span for span in read_timeline(timeline or "").values() if span.tool_name == "bash"]
    finished = [span.seconds for span in spans if span.seconds is not None]
    return CellEvidence(
        turns=usage.turns,
        output_tokens=usage.output_tokens,
        tool_calls=len(starts),
        root_searches=sum(1 for command in commands if root_search(command, cwd)),
        bash_outside_paths=sum(1 for command in commands if outside_paths(command, cwd)),
        file_tool_escapes=sum(1 for path in file_paths if outside(cwd, path)),
        git_commits=sum(1 for command in commands if git_commit(command)),
        tool_reported_timeouts=timeouts,
        guard_firings=dict(guard_firings),
        timeline=timeline is not None,
        commands_over_120s=sum(1 for seconds in finished if seconds > LONG_COMMAND_SECONDS),
        unfinished_commands=sum(1 for span in spans if span.ended is None),
        longest_command_seconds=max(finished) if finished else None,
        overlay_windows=(
            None
            if overlay is None
            else len(scan_transcript(decoded_scan_text(transcript), overlay, visible_texts=visible_texts))
        ),
    )
```

`workspace.py`: `from satyrn_evals.timeline import TimelineWriter`. `_wait_or_trip` gains `timeline: Path | None = None` (after `budget`); fast path `if transcript is None or (limit is None and budget is None and timeline is None):`; after `budget_wire = …`: `writer = TimelineWriter(timeline) if timeline is not None else None`, and `tripped_by` begins `if writer is not None: writer.feed(line)`. Replace Task 2's post-exit block (from the successful `whole_remaining()` to `return result, None`) with:

```python
            whole_remaining()
            # What the command wrote after the last poll still counts: a
            # command that finished over budget is still over it, and its
            # last tool end still belongs on the timeline. The repeat rule
            # is a live spending rule and is not applied to this tail.
            if handle is None and transcript.is_file():
                handle = transcript.open("rb")
            if handle is not None:
                pending += handle.read().decode("utf-8", errors="replace")
            over = False
            for line in pending.split("\n"):
                if writer is not None:
                    writer.feed(line)
                if budget_wire is not None:
                    over = budget_wire.feed(line) or over
            return result, (budget_wire if over else None)
```

and the `finally:` also closes the writer (`if writer is not None: writer.close()`). `_run_command` and `run_prepared_command` gain `timeline: Path | None = None` and pass it through. `attempt.py`: `from satyrn_evals.timeline import TIMELINE_NAME`; the `run_prepared_command(...)` call gains `timeline=attempt_dir / TIMELINE_NAME,`. Docstring of `_wait_or_trip`: add "With `timeline`, each tool start and end line is stamped as read (`timeline.py`)."

- [ ] **Step 4: Pass.** `uv run pytest -q; echo "EXIT: $?"` → 0. `uv run pytest -m integration tests/integration/test_timeline_attempt.py tests/integration/test_budget_attempt.py tests/integration/test_harvest_qualification.py tests/integration/test_repeat_limit_attempt.py tests/integration/test_workspace.py -q; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/timeline.py src/satyrn_evals/cell_evidence.py tests/test_timeline.py tests/test_cell_evidence.py tests/integration/test_timeline_attempt.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2a: the harness stamps a tool-call timeline for both arms; per-cell detectors for root searches, outside paths, commits, timeouts and guard firings"
```

---

### Task 4: Evidence for every cell in the summary

**Files:**
- Modify: `src/satyrn_evals/summary.py:40-130,179-287`, `src/satyrn_evals/rescore.py:26-50,264,280-333`, `src/satyrn_evals/run.py:40,111-137,237-249`, `tests/test_summary.py`, `tests/test_rescore.py`
- Create: `tests/integration/test_evidence_run.py`

**Interfaces:**
- Consumes: Task 3's `collect_evidence`, `TIMELINE_NAME`; Task 2's `AttemptBudget`, `run(budget=)`.
- Produces: `Summary.evidence: dict[str, dict] | None = None` (validated: keys equal the cells in cell order; each block a dict with a boolean `transcript`); `compute_summary(..., evidence: dict[str, dict] | None = None)`; `write_summary` omits `evidence` when `None`; `rescore.compute_evidence(output, cells, *, task_dir, manifest, overlay=None, visible_texts=None) -> dict[str, dict]` — `{"transcript": False}` for a cell with no readable transcript, else `{"transcript": True, **CellEvidence.to_block()}`, overlay scanned for hidden tasks, `<cell>/timeline.jsonl` read when present; `run()` and `summarize_output()` write `evidence` into `summary.json`; `aborted.json` carries no `evidence`.

- [ ] **Step 1: Failing tests.**

Append to `tests/test_rescore.py` (uses its `_hidden_setup`, `_visible_setup`, `_pathology_cell`, `_leaky_transcript`, `_HIDDEN_OVERLAY`, `_GOOD_TRANSCRIPT`, `replace`; import `compute_evidence` beside `compute_pathology`):

```python
def _partial_leak(payload: str) -> str:
    """A timed-out cell's transcript: the leak is read, nothing closes the turn."""
    return "\n".join(_leaky_transcript(payload).splitlines()[:5]) + "\n"


def test_evidence_scans_a_timed_out_hidden_cell_that_pathology_cannot_measure(tmp_path: Path) -> None:
    output, task_dir, manifest = _hidden_setup(tmp_path)
    name, rec, receipt = _pathology_cell(output, "hidden-task-1", task="hidden-task", transcript=_partial_leak(_HIDDEN_OVERLAY))
    timed_out = replace(
        rec, outcome=AttemptOutcome.REFUSED, code=AttemptCode.COMMAND_TIMEOUT, command_exit=None,
        verdict=None, receipt_path=None, patch_path=None, patch_digest=None,
    )
    cells = [(name, timed_out, receipt)]
    assert compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)[name]["measured"] is False
    block = compute_evidence(output, cells, task_dir=task_dir, manifest=manifest)[name]
    assert block["transcript"] is True and block["overlay_windows"] == 1
    assert block["timeline"] is False


def test_evidence_for_a_clean_hidden_cell_reports_zero_windows(tmp_path: Path) -> None:
    output, task_dir, manifest = _hidden_setup(tmp_path)
    cells = [_pathology_cell(output, "hidden-task-1", task="hidden-task", transcript=_GOOD_TRANSCRIPT)]
    assert compute_evidence(output, cells, task_dir=task_dir, manifest=manifest)["hidden-task-1"]["overlay_windows"] == 0


def test_evidence_says_when_a_cell_has_no_transcript_and_reads_a_timeline_when_present(tmp_path: Path) -> None:
    output, task_dir, manifest = _visible_setup(tmp_path)
    absent = _pathology_cell(output, "format_number-1", transcript=None)
    present = _pathology_cell(output, "format_number-2", transcript=_GOOD_TRANSCRIPT)
    (output / "format_number-2" / "timeline.jsonl").write_text(
        '{"at": 1.0, "event": "start", "toolCallId": "b", "toolName": "bash"}\n', encoding="utf-8"
    )
    blocks = compute_evidence(output, [absent, present], task_dir=task_dir, manifest=manifest)
    assert blocks["format_number-1"] == {"transcript": False}
    assert blocks["format_number-2"]["timeline"] is True
    assert blocks["format_number-2"]["unfinished_commands"] == 1
    assert blocks["format_number-2"]["overlay_windows"] is None
```

Append to `tests/test_summary.py` (uses its `make_record`, `absent_pathology`, `compute_summary`, `write_summary`):

```python
def test_summary_evidence_must_name_the_cells_in_order_and_is_written_when_present(tmp_path: Path) -> None:
    first = dataclasses.replace(make_record(AttemptCode.OK, Verdict.PASS), attempt_dir="t-1")
    second = dataclasses.replace(make_record(AttemptCode.OK, Verdict.PASS), attempt_dir="t-2")
    cells = [("t-1", first, None), ("t-2", second, None)]
    evidence = {"t-1": {"transcript": False}, "t-2": {"transcript": True, "turns": 3}}
    summary = compute_summary(cells, oracle_visibility="visible", pathology=absent_pathology(cells), evidence=evidence)
    path = tmp_path / "summary.json"
    write_summary(path, summary)
    assert json.loads(path.read_text())["evidence"] == evidence
    with pytest.raises(ValueError, match="evidence must name exactly the cells"):
        dataclasses.replace(summary, evidence={"t-2": evidence["t-2"], "t-1": evidence["t-1"]})
    with pytest.raises(ValueError, match="boolean transcript"):
        dataclasses.replace(summary, evidence={"t-1": {}, "t-2": {"transcript": True}})


def test_a_summary_built_without_evidence_writes_no_evidence_key(tmp_path: Path) -> None:
    cells = [("t-1", dataclasses.replace(make_record(AttemptCode.OK, Verdict.PASS), attempt_dir="t-1"), None)]
    summary = compute_summary(cells, oracle_visibility="visible", pathology=absent_pathology(cells))
    path = tmp_path / "summary.json"
    write_summary(path, summary)
    assert "evidence" not in json.loads(path.read_text())
```

`tests/integration/test_evidence_run.py`:

```python
"""A run's summary carries evidence for a cell the budget stopped."""

import json
import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.budget import AttemptBudget
from satyrn_evals.run import run

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"


def test_a_budget_stopped_cell_has_evidence_in_the_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pi").write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    (bin_dir / "pi").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", "spend")
    output = tmp_path / "run"
    summary = run(task="calc-build", tasks_root=TASKS, output=output, n=1, timeout=120,
                  command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"],
                  budget=AttemptBudget(output_tokens=32_000, turns=48))
    assert summary.code_counts["BUDGET_EXCEEDED"] == 1
    [cell] = summary.cells
    written = json.loads((output / "summary.json").read_text())
    assert written["pathology"][cell]["measured"] is False
    evidence = written["evidence"][cell]
    assert (evidence["transcript"], evidence["turns"], evidence["output_tokens"], evidence["timeline"]) == (True, 2, 40_000, True)
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_rescore.py tests/test_summary.py -q` → `ImportError: compute_evidence`, `unexpected keyword argument 'evidence'`.

- [ ] **Step 3: Implement.**

`summary.py`: `Summary` gains, after `deadline_provenance`:

```python
    #: Per-cell evidence for every cell whatever its code (``cell_evidence``);
    #: null only on a summary built without the binder.
    evidence: dict[str, dict] | None = None
```

`__post_init__`, after `_validate_pathology(...)`: `if self.evidence is not None: _validate_evidence(self.evidence, self.cells)`. Add before `absent_pathology`:

```python
def _validate_evidence(evidence: dict[str, dict], cells: Sequence[str]) -> None:
    """Raise ValueError unless evidence names exactly the cells, in order."""
    if list(evidence) != list(cells):
        raise ValueError("evidence must name exactly the cells, in cell order")
    if any(
        not isinstance(block, dict) or type(block.get("transcript")) is not bool
        for block in evidence.values()
    ):
        raise ValueError("each evidence block must carry a boolean transcript")
```

`compute_summary` gains `evidence: dict[str, dict] | None = None` and passes `evidence=None if evidence is None else {name: evidence[name] for name, _, _ in cells}`; `write_summary` pops `evidence` when `None`.

`rescore.py`: `from satyrn_evals.cell_evidence import collect_evidence`, `from satyrn_evals.timeline import TIMELINE_NAME`; before `pathology_context`:

```python
def compute_evidence(
    output: Path,
    cells: Sequence[AttemptCell],
    *,
    task_dir: Path,
    manifest: TaskManifest,
    overlay: OverlaySpec | None = None,
    visible_texts: list[str] | None = None,
) -> dict[str, dict]:
    """Per-cell evidence blocks for every cell, whatever its code.

    Unlike ``compute_pathology`` nothing here is conditional on a measured
    transcript: a ``COMMAND_TIMEOUT``, ``BUDGET_EXCEEDED`` or ``NO_PATCH``
    cell is read like any other, and a hidden task's overlay is scanned in
    every transcript that exists. A cell with no readable transcript says
    so (``transcript: false``) and carries no counts. The harness timeline
    is read when the cell directory holds one.
    """
    if manifest.oracle_visibility == "hidden":
        if overlay is None:
            overlay = load_overlay(task_dir, manifest)
        if visible_texts is None:
            visible_texts = _base_texts(task_dir)
    blocks: dict[str, dict] = {}
    for name, record, _ in cells:
        text = (
            None
            if record.transcript_path is None
            else _read_transcript(output / name / record.transcript_path)
        )
        if text is None:
            blocks[name] = {"transcript": False}
            continue
        timeline = _read_transcript(output / name / TIMELINE_NAME)
        evidence = collect_evidence(
            text,
            timeline=timeline,
            overlay=overlay,
            visible_texts=visible_texts or [],
        )
        blocks[name] = {"transcript": True, **evidence.to_block()}
    return blocks
```

`summarize_output`: after `pathology = compute_pathology(...)`, `evidence = compute_evidence(output, cells, task_dir=task_dir, manifest=manifest)`, and `compute_summary(..., evidence=evidence)`.

`run.py`: import `compute_evidence`; in `_write_aborted`, after the `deadline_provenance` pop, `payload.pop("evidence")  # the abort marker is a tally; evidence is the summary's`; before the final `compute_summary`, `evidence = compute_evidence(output, cells, task_dir=task_dir, manifest=manifest, overlay=overlay, visible_texts=visible_texts)` and pass `evidence=evidence`. (`tests/test_run.py:787,814,844` and `tests/test_rescore.py:766` compare a run's own `summary.json` with its rebuild; both paths now compute the same block.)

- [ ] **Step 4: Pass.** `uv run pytest -q; echo "EXIT: $?"` → 0. `uv run pytest -m integration tests/integration/test_evidence_run.py tests/integration/test_run.py tests/integration/test_rescore.py -q; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new tests/integration/test_evidence_run.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2a: summary evidence for every cell, including timeouts, budget stops and NO_PATCH; the overlay scan runs on every transcript"
```

---

### Task 5: The Engine arm against a fake model

**Files:**
- Create: `src/satyrn_evals/attempt_engine.py`, `tests/test_attempt_engine.py`, `tests/integration/test_engine_arm.py`
- Engine tree (Steps 0a–0c only): Create `tests/test_integration_pi_pump.py`; Modify `src/satyrn_engine/attempt.py` (`SubprocessPiRunner.run`), `src/satyrn_engine/cli.py:45-51` (docstring), `PROVENANCE.md`
- Modify: `pyproject.toml:11-15` (script), `src/satyrn_evals/pathology.py:43-50,213-218`, `src/satyrn_evals/census.py:52-54`, `tests/test_pathology.py:44` (`TOOL_NAMES` gains `self_test` — the only permitted assertion change) and an appended block

**Interfaces:**
- Consumes: Task 1's `attempt_pi.PATCH_ENV`, `AdapterError`, `clean_pi_environment`, `harvest_patch`, `read_artifact_paths`, `read_base_sha`, `read_prompt`; Task 2's `AttemptBudget`, `attempt(budget=)`; Task 3's `collect_evidence`; `fake_pi_build.py` modes `write`, `spend`; the Phase 1 names in "Phase 1 dependencies".
- Produces: `attempt_engine.ENGINE_REPO_ENV = "SATYRN_ENGINE_REPO"`, `RECEIPT_NAME = "engine-receipt.json"`, `DERIVE_LOG_NAME = "engine-derive.txt"`, `DELIVER_LOG_NAME = "engine-deliver.txt"`, `DELIVER_TIMEOUT_SECONDS = 1800`; `EngineArgs(model, engine_repo: Path, uv_bin)`; `parse_args(args, environment) -> EngineArgs`; `derive_argv(args, worktree, request) -> list[str]`; `deliver_argv(args, worktree, contract) -> list[str]`; `contract_path(stderr) -> Path`; `candidate_commit(receipt) -> str | None`; `delivery_environment(environment) -> dict[str, str]`; `main(argv=None) -> int`; console script `satyrn-evals-attempt-engine`; `pathology.GUARD_KINDS`; `self_test` in `pathology.TOOL_NAMES` and `census.KNOWN_TOOL_NAMES`.

- [ ] **Step 0a: R21 first — a failing engine test for the closed forward pipe.** This is the one engine edit 2a makes (Ruling 11). In the engine checkout (`/Users/pauleveritt/projects/pauleveritt/satyrn-engine`, branch `release-one`), create `tests/test_integration_pi_pump.py`:

```python
"""R21: Pi's stdout pump keeps draining when a sink fails.

`SubprocessPiRunner.run` reads Pi's stdout on a thread and writes each line to
the transcript and to `forward` (R18). If `forward` breaks (deliver killed,
`attempt | head`) the pump used to stop reading, Pi blocked on a full pipe and
`process.wait()` never returned. Each row runs a real child that writes far
more than a pipe buffer (64 KB) and must return within the join timeout.
"""

import io
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from satyrn_engine.attempt import SubprocessPiRunner

pytestmark = pytest.mark.integration

LINES = 20_000
LINE = b"x" * 99 + b"\n"
CHILD = [sys.executable, "-c", f"import sys\nfor _ in range({LINES}): sys.stdout.buffer.write({LINE!r})\n"]
JOIN_SECONDS = 30


class BrokenForward(io.RawIOBase):
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.calls = 0

    def writable(self) -> bool:
        return True

    def write(self, data: bytes) -> int:  # type: ignore[override]
        self.calls += 1
        raise self.exc


def _run_bounded(transcript, forward) -> tuple[int | None, BaseException | None]:
    outcome: dict[str, object] = {}

    def target() -> None:
        try:
            outcome["code"] = SubprocessPiRunner().run(
                CHILD, Path.cwd(), {}, transcript, forward, subprocess.DEVNULL  # type: ignore[arg-type]
            )
        except BaseException as exc:  # noqa: BLE001 - the row inspects it
            outcome["error"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(JOIN_SECONDS)
    assert not worker.is_alive(), "pump stopped draining: Pi blocked on a full pipe"
    return outcome.get("code"), outcome.get("error")  # type: ignore[return-value]


def test_healthy_sinks_receive_every_line_and_the_exit_code(tmp_path: Path) -> None:
    forward = io.BytesIO()
    with (tmp_path / "t.jsonl").open("wb") as transcript:
        code, error = _run_bounded(transcript, forward)
    assert (code, error) == (0, None)
    assert forward.getvalue() == LINE * LINES
    assert (tmp_path / "t.jsonl").read_bytes() == LINE * LINES


@pytest.mark.parametrize("exc", [BrokenPipeError(32, "Broken pipe"), ValueError("I/O operation on closed file")])
def test_a_broken_forward_keeps_the_transcript_complete_and_raises_oserror(tmp_path: Path, exc: BaseException) -> None:
    forward = BrokenForward(exc)
    with (tmp_path / "t.jsonl").open("wb") as transcript:
        code, error = _run_bounded(transcript, forward)
    assert code is None
    assert isinstance(error, OSError)
    assert "forward" in str(error)
    assert forward.calls == 1  # a dead sink is not retried line by line
    assert (tmp_path / "t.jsonl").read_bytes() == LINE * LINES


def test_a_broken_transcript_keeps_forwarding_and_raises_oserror(tmp_path: Path) -> None:
    forward = io.BytesIO()
    code, error = _run_bounded(BrokenForward(OSError(28, "No space left on device")), forward)
    assert code is None
    assert isinstance(error, OSError)
    assert "transcript" in str(error)
    assert forward.getvalue() == LINE * LINES
```

Run: `cd /Users/pauleveritt/projects/pauleveritt/satyrn-engine && uv run pytest -m integration tests/test_integration_pi_pump.py -q; echo "EXIT: $?"`. Expected: the healthy row passes; the three sink-failure rows FAIL on `pump stopped draining` (the join times out at 30 s each) or on `isinstance(error, OSError)` for the `ValueError` row. If a failure row passes on the unchanged engine, stop and report: the finding is not what R21 says.

- [ ] **Step 0b: Implement.** Replace the `pump` closure and the tail of `SubprocessPiRunner.run` in `src/satyrn_engine/attempt.py` (the block from `pump_error: BaseException | None = None` through `return exit_code`) with:

```python
        sink_errors: dict[str, BaseException] = {}

        def pump() -> None:
            # R18: a reader thread over Popen.stdout, not a post-exit copy --
            # every line reaches `transcript` and `forward` while Pi runs,
            # flushed at once so deliver's live budget counter sees it.
            # R21: a failing sink is dropped, never the read loop. If
            # `forward` breaks (deliver killed, `attempt | head`) or the
            # transcript cannot be written, the pump keeps draining Pi's
            # stdout into the surviving sink, so Pi never blocks on a full
            # pipe and `process.wait()` returns. The first error per sink is
            # raised by run() after Pi exits.
            assert process.stdout is not None
            sinks = {"transcript": transcript, "forward": forward}
            try:
                for line in process.stdout:
                    for name in [name for name in sinks if name not in sink_errors]:
                        try:
                            sinks[name].write(line)
                            sinks[name].flush()
                        except (OSError, ValueError) as exc:
                            sink_errors[name] = exc
            except BaseException as exc:  # noqa: BLE001 - surfaced by run(), not swallowed
                sink_errors.setdefault("pipe", exc)

        reader = threading.Thread(target=pump, name="satyrn-attempt-pi-pump", daemon=True)
        reader.start()
        try:
            exit_code = process.wait()
        finally:
            # Join before returning: the pipe's write end can outlive
            # `process.wait()` by a few scheduler ticks, and the transcript
            # must be complete before `_run` flushes/closes it.
            reader.join()
            self._process = None
            if process.stdout is not None:
                process.stdout.close()
        for name in ("pipe", "transcript", "forward"):
            if name in sink_errors:
                exc = sink_errors[name]
                raise OSError(f"cannot {'read Pi output' if name == 'pipe' else 'write Pi output to ' + name}: {exc}") from exc
        return exit_code
```

`_run` already turns an `OSError` from `pi.run` into `cannot run Pi: …`; the `ValueError` leak the final review found is closed because the pump now wraps it. Ctrl-C on a direct `attempt` still waits for Pi to exit: recorded as a minor, not changed here.

- [ ] **Step 0c: Pass, engine gates, engine commit.** In the engine checkout: `uv run pytest -m integration tests/test_integration_pi_pump.py -q; echo "EXIT: $?"` → `4 passed`, each row in well under 30 s. `uv run pytest -m integration tests/test_integration_attempt.py tests/test_integration_delivery.py tests/test_integration_implement.py -q; echo "EXIT: $?"` → 0 (the R18 live-budget and delivery rows still pass). `uv run python tools/provenance.py new tests/test_integration_pi_pump.py`; `just gates; echo "EXIT: $?"` → 0; `just integration; echo "EXIT: $?"` → 0. Then update the stale docstring R21's ledger names (`src/satyrn_engine/cli.py:45-51`, which still describes post-exit forwarding) to say attempt forwards Pi's stdout live and keeps draining when a sink fails. Commit in the engine tree:

```bash
git add src/satyrn_engine/attempt.py src/satyrn_engine/cli.py tests/test_integration_pi_pump.py PROVENANCE.md
git commit -m "Phase 2a: attempt's Pi pump keeps draining when a sink fails (R21)"
```

Record the engine commit hash; Step 5's integration rows and Task 6's morning status name it.

- [ ] **Step 1: Verify the Phase 1 names against the merged engine.** Stop and report if any output differs; do not adapt.

```bash
E=/Users/pauleveritt/projects/pauleveritt/satyrn-engine
git -C "$E" log --oneline -1 release-one                       # a "Phase 1 done" commit (Phase 1 Task 13)
grep -n -A6 '^GUARD_KINDS' "$E/src/satyrn_engine/budget.py"       # loop_broken, scope_refused, symbol_preserved, command_bounded, command_timed_out
grep -n 'read,bash,edit,write,self_test' "$E/src/satyrn_engine/attempt.py"   # one hit
grep -n 'satyrn-engine: contract' "$E/src/satyrn_engine/cli.py"             # printed to stderr by derive
grep -n -A16 '"deliver",' "$E/packages/engine/orchestrator.ts"   # --repo R --timeout S CONTRACT -- uv run --project E satyrn-engine attempt --model=M -- CONTRACT
grep -n '"candidate_commit"\|"guard_firings"\|"validation"' "$E/src/satyrn_engine/delivery.py"   # receipt payload keys
grep -n 'appendEntry(' "$E"/packages/engine/{engine,mutator,scope,bounds}.ts   # guard firings are appendEntry custom entries
grep -n 'environ.get(PATCH_ENV)\|environ.get(TRANSCRIPT_ENV)' "$E/src/satyrn_engine/attempt.py"   # both optional (absent -> no destination)
test -x "$E/.venv/bin/satyrn-engine" && echo engine-venv-ok
```

- [ ] **Step 2: Failing tests.**

`tests/test_attempt_engine.py`:

```python
"""The Engine adapter's pure surface: arguments, the two engine argvs, the receipt.

No process: ``subprocess.run`` is replaced in the module namespace, as
``test_attempt_pi.py`` does for the Baseline adapter. Every refusal has a
sibling success over the same inputs.
"""

import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals import attempt_engine, attempt_pi
from satyrn_evals.attempt_engine import (
    DELIVER_TIMEOUT_SECONDS,
    ENGINE_REPO_ENV,
    RECEIPT_NAME,
    AdapterError,
    candidate_commit,
    contract_path,
    deliver_argv,
    delivery_environment,
    derive_argv,
    main,
    parse_args,
)

ENGINE = Path("/opt/satyrn-engine")
WORKTREE = Path("/w/worktree")
CONTRACT = Path("/w/seed/.git/worktrees/worktree/satyrn/contracts/implement-0123456789ab.yaml")
BASE = "c" * 40
COMMIT = "d" * 40


def test_arguments_take_the_engine_from_the_environment_and_ignore_the_rendered_contract() -> None:
    args = parse_args(["--model", "omlx/m", "/runs/engine-contracts/x.yaml"], {ENGINE_REPO_ENV: str(ENGINE)})
    assert (args.model, args.engine_repo, args.uv_bin) == ("omlx/m", ENGINE, "uv")


@pytest.mark.parametrize(
    ("argv", "environment", "message"),
    [
        ([], {ENGINE_REPO_ENV: "/e"}, "--model"),
        (["--model", "m"], {}, ENGINE_REPO_ENV),
        (["--model", "m", "--rung", "R1"], {ENGINE_REPO_ENV: "/e"}, "unknown adapter argument"),
        (["--model", "m", "a.yaml", "b.yaml"], {ENGINE_REPO_ENV: "/e"}, "unexpected extra argument"),
    ],
)
def test_bad_arguments_are_refused(argv: list[str], environment: dict[str, str], message: str) -> None:
    with pytest.raises(AdapterError, match=message):
        parse_args(argv, environment)


def test_derive_and_deliver_are_the_implement_invocations() -> None:
    args = parse_args(["--model", "omlx/m", "--engine-repo", str(ENGINE), "--uv-bin", "/bin/uv"], {})
    engine = ["/bin/uv", "run", "--project", str(ENGINE), "satyrn-engine"]
    assert derive_argv(args, WORKTREE, "Create calc/helpers.py") == [
        *engine, "derive", "--repo", str(WORKTREE), "--", "Create calc/helpers.py"]
    assert deliver_argv(args, WORKTREE, CONTRACT) == [
        *engine, "deliver", "--repo", str(WORKTREE), "--timeout", str(DELIVER_TIMEOUT_SECONDS), str(CONTRACT),
        "--", *engine, "attempt", "--model=omlx/m", "--", str(CONTRACT)]


def test_the_contract_path_is_read_from_derives_stderr_and_its_absence_refused() -> None:
    assert contract_path(f"warming\nsatyrn-engine: contract {CONTRACT}\n") == CONTRACT
    with pytest.raises(AdapterError, match="derive named no contract"):
        contract_path("satyrn-engine: DERIVE: name at least one tracked file\n")


def test_a_candidate_commit_is_read_from_the_receipt_or_absent() -> None:
    assert candidate_commit(json.dumps({"code": "OK", "candidate_commit": COMMIT})) == COMMIT
    assert candidate_commit(json.dumps({"code": "DIRTY_REPO", "candidate_commit": None})) is None
    assert candidate_commit("") is None


def test_the_engine_runs_without_the_patch_destination_or_the_models_uv_environment() -> None:
    cleaned = delivery_environment(
        {attempt_pi.PATCH_ENV: "/a/patch.diff", attempt_pi.TRANSCRIPT_ENV: "/a/transcript.txt",
         "UV_PROJECT_ENVIRONMENT": "/a/environment", "PATH": "/usr/bin"}
    )
    assert cleaned == {attempt_pi.TRANSCRIPT_ENV: "/a/transcript.txt", "PATH": "/usr/bin"}


@pytest.fixture()
def seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(attempt_pi.CONTRACT_ENV, "Create calc/helpers.py")
    monkeypatch.setenv(attempt_pi.PATCH_ENV, str(tmp_path / "patch.diff"))
    monkeypatch.setenv(attempt_pi.TRANSCRIPT_ENV, str(tmp_path / "transcript.txt"))
    monkeypatch.setenv(attempt_pi.BASE_SHA_ENV, BASE)
    monkeypatch.setenv(ENGINE_REPO_ENV, str(ENGINE))
    monkeypatch.setattr(attempt_engine, "harvest_patch", lambda worktree, base: f"harvested {base}\n")
    return tmp_path


def _fake_run(derive_exit: int, receipt: dict) -> tuple[list[list[str]], object]:
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if "derive" in argv:
            return subprocess.CompletedProcess(argv, derive_exit, "", f"satyrn-engine: contract {CONTRACT}\n")
        if "deliver" in argv:
            return subprocess.CompletedProcess(argv, 0, json.dumps(receipt), None)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    return calls, run


def test_main_derives_delivers_checks_out_the_candidate_and_harvests(seam: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls, run = _fake_run(0, {"code": "OK", "candidate_commit": COMMIT})
    monkeypatch.setattr(attempt_engine.subprocess, "run", run)
    assert main(["--model", "omlx/m"]) == 0
    assert [call[5] if call[0] != "git" else "git" for call in calls] == ["derive", "deliver", "git"]
    assert calls[2] == ["git", "checkout", "-q", "--detach", COMMIT]
    assert json.loads((seam / RECEIPT_NAME).read_text())["candidate_commit"] == COMMIT
    assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"


def test_main_without_a_candidate_checks_out_nothing_and_still_writes_the_patch(
    seam: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls, run = _fake_run(5, {})
    monkeypatch.setattr(attempt_engine.subprocess, "run", run)
    assert main(["--model", "omlx/m"]) == 5
    assert len(calls) == 1 and "derive" in calls[0]
    assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"
```

Append to `tests/test_pathology.py` (the file has no `pytest` import; loop, do not parametrize):

```python
# --- 2a: the /implement child's vocabulary (satyrn-engine Phase 1) ---------


def test_every_engine_guard_entry_is_measured() -> None:
    for kind in ("loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out"):
        block = count_transcript(_LOOP_BROKEN_DOC.replace('"loop_broken"', f'"{kind}"'), had_patch=True)
        assert (block.measured, block.reason) == (True, None), kind
        assert block.loop_broken == (1 if kind == "loop_broken" else 0), kind


def test_the_self_test_tool_is_a_known_tool() -> None:
    doc = _UPDATE_DOC.replace('"toolName": "bash"', '"toolName": "self_test"')
    block = count_transcript(doc, had_patch=True)
    assert (block.measured, block.tool_calls) == (True, {"self_test": 1})
```

(`test_unknown_engine_entry_custom_type_is_not_silently_accepted` at its current line stays: `future_telemetry` is still unknown.)

`tests/integration/test_engine_arm.py`:

```python
"""The Engine arm against a fake model: `/implement` behind the Evals seam.

Integration tier and engine-checkout dependent (skips without one, as the
E5 rows in `test_attempt.py` do; set SATYRN_V4_ENGINE_REPO). The real
`satyrn-evals-attempt-engine`, the real `satyrn-engine derive`/`deliver`/
`attempt`, the guards' extension files on Pi's argv; `pi` is
`fake_pi_build.py`. No model runs.
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest
from integration.test_attempt import (  # type: ignore[missing-import]  # pytest sibling resolution (tests/ on sys.path)
    _configure_engine,
    _engine_repo,
)

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_engine import RECEIPT_NAME
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell_evidence import collect_evidence
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.pathology import count_transcript
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
CAMPAIGN = AttemptBudget(output_tokens=32_000, turns=48)


def _engine_arm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> list[str]:
    engine_repo = _engine_repo()
    uv = _configure_engine(tmp_path, monkeypatch, engine_repo)
    (tmp_path / "bin" / "pi").unlink()
    (tmp_path / "bin" / "pi").write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE_PI} "$@"\n')
    (tmp_path / "bin" / "pi").chmod(0o755)
    monkeypatch.setenv("SATYRN_FAKE_PI_MODE", mode)
    return [sys.executable, "-m", "satyrn_evals.attempt_engine", "--model", "omlx/fixture",
            "--engine-repo", os.fspath(engine_repo), "--uv-bin", os.fspath(uv)]


def test_the_engine_arm_delivers_a_candidate_that_is_harvested_and_graded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = _engine_arm(tmp_path, monkeypatch, "write")
    output = tmp_path / "attempts"
    record = attempt(task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300, budget=CAMPAIGN)
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    cell = output / record.attempt_dir
    receipt = json.loads((cell / RECEIPT_NAME).read_text())
    assert (receipt["code"], receipt["validation"]) == ("OK", "passed")
    assert receipt["guard_firings"]["command_bounded"] == 1
    assert sorted(parse_patch_paths((cell / "patch.diff").read_text())) == ["calc/core.py", "calc/format.py", "calc/helpers.py"]
    transcript = (cell / "transcript.txt").read_text()
    assert count_transcript(transcript, had_patch=True).measured is True
    assert collect_evidence(transcript).guard_firings == {"command_bounded": 1}


def test_an_engine_cell_over_budget_is_stopped_and_leaves_no_model_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    command = _engine_arm(tmp_path, monkeypatch, "spend")
    pidfile = tmp_path / "pi.pid"
    monkeypatch.setenv("SATYRN_FAKE_PI_PIDFILE", os.fspath(pidfile))
    record = attempt(task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts", command=command, timeout=300, budget=CAMPAIGN)
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert record.retained_path is None
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while time.monotonic() < stop:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail(f"fake pi {pid} outlived its cell")
```

- [ ] **Step 3: Run to verify failure.** `uv run pytest tests/test_attempt_engine.py tests/test_pathology.py -q` → `ModuleNotFoundError: satyrn_evals.attempt_engine`; the two pathology rows fail `unknown_event`.

- [ ] **Step 4: Implement.**

`src/satyrn_evals/attempt_engine.py`:

```python
"""The Engine attempt adapter: the task text run through `/implement`.

The Engine arm is bare Pi's arm with each task run through the engine's
`/implement` (spec, "The eval"): the same task text, the same model and
Pi's native tools. `/implement` is derive, then deliver; outside a Pi
session its two steps are the engine CLI calls the command makes
(satyrn-engine Phase 1 Task 10: `buildDeriveInvocation`,
`buildDeliveryInvocation`):

1. ``satyrn-engine derive --repo WORKTREE -- TASK`` writes the contract under
   the worktree's git dir and names it on stderr;
2. ``satyrn-engine deliver --repo WORKTREE --timeout S CONTRACT -- satyrn-engine
   attempt --model=M -- CONTRACT`` runs one fresh Pi with every guard in its
   own isolated worktree, commits a candidate, validates it, and prints the
   receipt on stdout.

The adapter then checks the candidate out into the Evals worktree and
harvests it exactly as the Baseline adapter harvests (``attempt_pi``), so
both arms' patches come from one rule. The engine's own `attempt` writes
Pi's stream straight into ``SATYRN_ATTEMPT_TRANSCRIPT``, where the harness
reads it live for the budget and the timeline. The receipt is kept beside
the transcript as ``engine-receipt.json``; it is the engine's account and
never the verdict.
"""

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.attempt_pi import (
    PATCH_ENV,
    AdapterError,
    clean_pi_environment,
    harvest_patch,
    read_artifact_paths,
    read_base_sha,
    read_prompt,
)

ENGINE_REPO_ENV = "SATYRN_ENGINE_REPO"
RECEIPT_NAME = "engine-receipt.json"
DERIVE_LOG_NAME = "engine-derive.txt"
DELIVER_LOG_NAME = "engine-deliver.txt"
#: The deliver timeout: the spec's attempt-command backstop on this machine.
#: The harness's own command timeout and budget stop the cell first.
DELIVER_TIMEOUT_SECONDS = 1800
_CONTRACT_PREFIX = "satyrn-engine: contract "


@dataclass(frozen=True, slots=True)
class EngineArgs:
    model: str
    engine_repo: Path
    uv_bin: str


def parse_args(args: list[str], environment: Mapping[str, str]) -> EngineArgs:
    """``--model`` (required), ``--engine-repo`` (default ``$SATYRN_ENGINE_REPO``),
    ``--uv-bin``; one trailing positional (the rendered contract Evals
    appends) is accepted and ignored, because `/implement` derives its own."""
    model, engine_repo, uv_bin = "", environment.get(ENGINE_REPO_ENV, ""), "uv"
    seen_positional = False
    index = 0
    while index < len(args):
        token = args[index]
        if token in ("--model", "--engine-repo", "--uv-bin"):
            if index + 1 >= len(args):
                raise AdapterError(f"{token} needs a value")
            value = args[index + 1]
            if token == "--model":
                model = value
            elif token == "--engine-repo":
                engine_repo = value
            else:
                uv_bin = value
            index += 2
        elif token.startswith("-"):
            raise AdapterError(f"unknown adapter argument {token!r}")
        elif seen_positional:
            raise AdapterError(f"unexpected extra argument {token!r}")
        else:
            seen_positional = True
            index += 1
    if not model:
        raise AdapterError("--model is required")
    if not engine_repo:
        raise AdapterError(f"--engine-repo or {ENGINE_REPO_ENV} is required")
    return EngineArgs(model=model, engine_repo=Path(engine_repo), uv_bin=uv_bin)


def _engine(args: EngineArgs) -> list[str]:
    return [args.uv_bin, "run", "--project", os.fspath(args.engine_repo), "satyrn-engine"]


def derive_argv(args: EngineArgs, worktree: Path, request: str) -> list[str]:
    return [*_engine(args), "derive", "--repo", os.fspath(worktree), "--", request]


def deliver_argv(args: EngineArgs, worktree: Path, contract: Path) -> list[str]:
    return [
        *_engine(args), "deliver", "--repo", os.fspath(worktree),
        "--timeout", str(DELIVER_TIMEOUT_SECONDS), os.fspath(contract),
        "--", *_engine(args), "attempt", f"--model={args.model}", "--", os.fspath(contract),
    ]


def contract_path(stderr: str) -> Path:
    """The contract `derive` wrote, from its ``satyrn-engine: contract PATH`` line."""
    for line in reversed(stderr.splitlines()):
        if line.startswith(_CONTRACT_PREFIX):
            return Path(line.removeprefix(_CONTRACT_PREFIX).strip())
    raise AdapterError(f"derive named no contract: {stderr.strip()!r}")


def candidate_commit(receipt: str) -> str | None:
    """The receipt's candidate commit, or None when deliver created none."""
    try:
        data = json.loads(receipt)
    except json.JSONDecodeError:
        return None
    commit = data.get("candidate_commit") if isinstance(data, dict) else None
    return commit if isinstance(commit, str) and commit else None


def delivery_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Evals' environment for the engine, minus two entries.

    ``SATYRN_ATTEMPT_PATCH``: the engine's `attempt` would publish its own
    patch there; this adapter harvests the candidate instead, so both arms'
    patches follow one rule. ``UV_PROJECT_ENVIRONMENT``: Evals points it at
    the attempt's private environment for the model's own ``uv run``; left
    set, ``uv run --project ENGINE satyrn-engine`` would look for the engine
    there and fail to spawn.
    """
    cleaned = clean_pi_environment(environment)
    cleaned.pop(PATCH_ENV, None)
    cleaned.pop("UV_PROJECT_ENVIRONMENT", None)
    return cleaned


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv), os.environ)
    request = read_prompt(os.environ)
    patch_path, transcript_path = read_artifact_paths(os.environ)
    base_sha = read_base_sha(os.environ)
    worktree = Path.cwd()
    environment = delivery_environment(os.environ)
    derived = subprocess.run(
        derive_argv(args, worktree, request), capture_output=True, text=True, env=environment, check=False
    )
    (transcript_path.parent / DERIVE_LOG_NAME).write_text(derived.stderr, encoding="utf-8")
    exit_code = derived.returncode
    if derived.returncode == 0:
        with (transcript_path.parent / DELIVER_LOG_NAME).open("w", encoding="utf-8") as log:
            delivered = subprocess.run(
                deliver_argv(args, worktree, contract_path(derived.stderr)),
                stdout=subprocess.PIPE, stderr=log, text=True, env=environment, check=False,
            )
        (transcript_path.parent / RECEIPT_NAME).write_text(delivered.stdout, encoding="utf-8")
        exit_code = delivered.returncode
        if (commit := candidate_commit(delivered.stdout)) is not None:
            subprocess.run(["git", "checkout", "-q", "--detach", commit], check=True, capture_output=True)
    patch_path.write_text(harvest_patch(worktree, base_sha), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
```

`pyproject.toml` `[project.scripts]`, after the Baseline line: `# The Engine arm's attempt adapter: the same task text through /implement.` and `satyrn-evals-attempt-engine = "satyrn_evals.attempt_engine:main"`; then `uv sync`.

`pathology.py`: `TOOL_NAMES = frozenset({"read", "bash", "edit", "write", "run_self_test", "self_test"})` with the comment "`self_test` added in Phase 2a: the engine's `/implement` child registers the runner under that name (satyrn-engine Phase 1 Ruling 1, Task 9)"; below it

```python
#: The engine's guard-firing entries (satyrn-engine Phase 1 Task 2,
#: `budget.GUARD_KINDS`), each a `pi.appendEntry` custom entry the stream
#: carries as `entry_appended` (Phase 1 Ruling 7). Counted as nothing here;
#: `cell_evidence` counts them.
GUARD_KINDS = frozenset(
    {"loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out"}
)
```

and in `_vocabulary_ok` `if entry["customType"] != "loop_broken":` becomes `if entry["customType"] not in GUARD_KINDS:`. `census.KNOWN_TOOL_NAMES` gains `"self_test"`. `tests/test_pathology.py:44`'s set gains `"self_test"`.

- [ ] **Step 5: Pass.** `uv run pytest -q; echo "EXIT: $?"` → 0. `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration tests/integration/test_engine_arm.py -q; echo "EXIT: $?"` → `2 passed` (not skipped; a skip means the engine checkout was not found and the task is not done). Run the orphan row three times.

- [ ] **Step 6: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/attempt_engine.py tests/test_attempt_engine.py tests/integration/test_engine_arm.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2a: the Engine arm runs /implement against a fake model; the candidate is harvested and graded like Baseline's; a budget stop leaves no model running"
```

---

### Task 6: Hygiene, the roadmap row, and the maintainer checklist

**Files:**
- Create: `src/satyrn_evals/hygiene.py`, `tests/test_hygiene.py`
- Modify: `tests/test_agentclinic_manifests.py:9-11,79-96`, `tests/conftest.py` (after `_tripwire_gate`), `ROADMAP.md`

**Interfaces:**
- Consumes: `tests/conftest.py` fixture `tmp_hidden_task` (overlay `grader/overlay/tests/test_hidden.py`).
- Produces: `hygiene.overlay_digests(tasks_root: Path = DEFAULT_TASKS_ROOT) -> dict[str, str]` (sha256 → task-root-relative path, non-empty overlay files of hidden tasks); `hygiene.overlay_copies(root: Path, digests: dict[str, str]) -> list[Path]`; a default-tier session guard.

- [ ] **Step 1: Failing tests.**

`tests/test_hygiene.py`:

```python
"""Answer-key hygiene: a grader file copied out of its task is found by content."""

import json
from pathlib import Path

from satyrn_evals.hygiene import overlay_copies, overlay_digests
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT


def _tasks(tmp_path: Path) -> Path:
    root = tmp_path / "tasks"
    hidden = root / "hidden"
    (hidden / "grader" / "overlay").mkdir(parents=True)
    (hidden / "grader" / "overlay" / "test_key.py").write_text("def test_key():\n    assert 42\n")
    (hidden / "grader" / "overlay" / "__init__.py").write_text("")
    (hidden / "manifest.json").write_text(json.dumps({"grader_overlay": "grader/overlay", "oracle_visibility": "hidden"}))
    visible = root / "visible"
    visible.mkdir()
    (visible / "manifest.json").write_text(json.dumps({"name": "visible"}))
    return root


def test_a_copied_overlay_file_is_found_under_any_name(tmp_path: Path) -> None:
    digests = overlay_digests(_tasks(tmp_path))
    assert list(digests.values()) == ["hidden/grader/overlay/test_key.py"]
    scratch = tmp_path / "pytest-of-someone" / "pytest-7" / "test_x0"
    scratch.mkdir(parents=True)
    (scratch / "renamed.py").write_text("def test_key():\n    assert 42\n")
    assert overlay_copies(tmp_path / "pytest-of-someone", digests) == [scratch / "renamed.py"]


def test_empty_files_unreadable_files_and_other_content_are_not_copies(tmp_path: Path) -> None:
    digests = overlay_digests(_tasks(tmp_path))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "__init__.py").write_text("")
    (scratch / "other.py").write_text("def test_key():\n    assert 41\n")
    locked = scratch / "locked.py"
    locked.write_text("def test_key():\n    assert 42\n")
    locked.chmod(0)
    try:
        assert overlay_copies(scratch, digests) == []
    finally:
        locked.chmod(0o644)


def test_the_bundled_hidden_tasks_have_keys_to_look_for() -> None:
    assert overlay_digests(DEFAULT_TASKS_ROOT)
```

Replace `test_manifest_whose_contract_names_overlay_is_refused` (79-96) with the row below and drop `import shutil` (its only use). The overlay names the validator matches are overlay-root-relative (`manifest.py:179-196`), so the contract names `tests/test_hidden.py`, not `test_hidden.py`:

```python
def test_manifest_whose_contract_names_overlay_is_refused(tmp_hidden_task: Path) -> None:
    """End-to-end refusal at load: a hidden-task contract naming a grader-only
    path must raise ManifestError from load_manifest itself.

    The task is the synthetic hidden task from ``tests/conftest.py``, never a
    copy of a bundled one: a bundled overlay copied into pytest's temp
    directory is an answer key on disk, and on 2026-09-14 a hunting model read
    exactly that copy (spec, "What the evidence settled"). Its overlay is a
    real directory, so the ONLY defect is the contract.
    """
    manifest_path = tmp_hidden_task / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["contract"] = "the failure is in tests/test_hidden.py — fix it"
    manifest_path.write_text(json.dumps(data))
    with pytest.raises(ManifestError, match="contract names grader-only path"):
        load_manifest(tmp_hidden_task)
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_hygiene.py -q` → `ModuleNotFoundError: satyrn_evals.hygiene`. Before the replacement, confirm the leak: `uv run pytest -q tests/test_agentclinic_manifests.py --basetemp=/tmp/p2a-bt; find /tmp/p2a-bt -name test_acceptance.py` prints one path.

- [ ] **Step 3: Implement.**

`src/satyrn_evals/hygiene.py`:

```python
"""Answer-key hygiene: find copies of a hidden task's grader files elsewhere.

A hunting model reads whatever the machine holds. On 2026-09-14 the only
``depth-3`` pass read a hidden suite that ``tests/test_agentclinic_manifests.py``
had copied into pytest's temp directory (spec, "What the evidence settled").
This finds such copies by content, so the default test tier can refuse to
leave one and a maintainer can check a directory before a sitting. It deletes
nothing. Empty overlay files are not keys and are ignored: every empty file
would match them.
"""

import hashlib
import json
import os
from pathlib import Path

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT


def overlay_digests(tasks_root: Path = DEFAULT_TASKS_ROOT) -> dict[str, str]:
    """SHA-256 of every non-empty grader overlay file of every hidden task,
    mapped to its path relative to ``tasks_root``."""
    digests: dict[str, str] = {}
    for manifest_path in sorted(tasks_root.glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        overlay = data.get("grader_overlay")
        if data.get("oracle_visibility") != "hidden" or not isinstance(overlay, str):
            continue
        for path in sorted((manifest_path.parent / overlay).rglob("*")):
            if path.is_file() and not path.is_symlink() and path.stat().st_size > 0:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                digests.setdefault(digest, path.relative_to(tasks_root).as_posix())
    return digests


def overlay_copies(root: Path, digests: dict[str, str]) -> list[Path]:
    """Regular files under ``root`` whose bytes equal a grader overlay file.

    Unreadable entries and symlinks are skipped, never fatal: a test that
    made a file unreadable on purpose must not break the scan.
    """
    found: list[Path] = []
    for directory, _dirs, files in os.walk(root):
        for name in files:
            path = Path(directory) / name
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
                    continue
                if hashlib.sha256(path.read_bytes()).hexdigest() in digests:
                    found.append(path)
            except OSError:
                continue
    return sorted(found)
```

`tests/conftest.py`, after `_tripwire_gate`:

```python
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """The default tier leaves no bundled grader file in pytest's temp directory.

    pytest keeps the last three base temp directories, and on 2026-09-14 a
    hunting model read a hidden suite a test had copied there. The default
    tier (``-m "not integration"``, the addopts value) fails its session if
    any file under this run's base temp equals a bundled overlay file.
    """
    from satyrn_evals.hygiene import overlay_copies, overlay_digests

    factory = getattr(session.config, "_tmp_path_factory", None)
    if session.config.option.markexpr != "not integration" or factory is None:
        return
    copies = overlay_copies(factory.getbasetemp(), overlay_digests())
    if copies:
        for path in copies:
            print(f"bundled grader file copied into pytest's temp directory: {path}")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
```

`ROADMAP.md`: replace the phase-2 row Phase 1 Task 12 wrote with the spec's rows 2a and 2b (spec lines 363–364) plus a Status cell each: 2a `done <date> — docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md`, 2b `not started`. `just lint-docs; echo "EXIT: $?"` → 0.

- [ ] **Step 4: Pass, both directions of the guard.** `uv run pytest -q; echo "EXIT: $?"` → 0. Then prove the guard fires, and remove the probe: write `tests/test_zz_leak_probe.py` containing `import shutil` / `from satyrn_evals.manifest import DEFAULT_TASKS_ROOT` / `def test_leak(tmp_path): shutil.copy(DEFAULT_TASKS_ROOT / "agentclinic-repair-misleading-locus" / "overlay" / "test_acceptance.py", tmp_path / "x.py")`; `uv run pytest -q tests/test_zz_leak_probe.py; echo "EXIT: $?"` → `1 passed`, the "bundled grader file copied" line, `EXIT: 1`; `rm tests/test_zz_leak_probe.py`.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/hygiene.py tests/test_hygiene.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2a: no test copies a bundled hidden suite into pytest's temp directory, and the default tier fails if one does; roadmap row 2a"
```

- [ ] **Step 6: Maintainer checklist (written into the morning status, not executed).** Each line is Paul's, run in daylight before the first attended sitting:

1. `chmod 700 ~/satyrn-smokes` — 616 retained `patch.diff` answers are world-readable today (rationale Q3).
2. Remove leftover attempt parents: `ls -d "$TMPDIR"/satyrn-attempt-*` (120 on 2026-09-14), inspect, then remove the ones no retained record names; also `ls -d "$TMPDIR"/satyrn-engine-*` (a `deliver` killed mid-run leaves one).
3. Remove pytest's kept base temps holding overlay copies: `uv run python -c 'import os; from pathlib import Path; from satyrn_evals.hygiene import overlay_copies, overlay_digests; [print(p) for p in overlay_copies(Path(os.environ["TMPDIR"]) / f"pytest-of-{os.environ["USER"]}", overlay_digests())]'` lists them (174 on 2026-09-14); delete those directories by hand; re-run → prints nothing.

- [ ] **Step 7: Morning status** (under 200 words): evals head; default-tier and named integration counts; the Task 5 Step 1 verification output (verbatim, one line each); the engine commit Task 5's integration rows ran against, and the R21 engine commit (Task 5 Step 0c); the E5 rows' status; the **Phase 3 watch list** — the model's `uv run` and `self_test` exchange without `UV_PROJECT_ENVIRONMENT` inside `deliver`'s worktree (Ruling 7); a real Pi exiting under `deliver`'s teardown on a harness stop (Ruling 8); stray files outside `source_paths` now visible to the allowlist (Ruling 2); the engine's derived budget against the campaign record (Ruling 9); the maintainer checklist. Do **not** start 2b.

---

## Self-review against the spec

- **Item 1, harvest** (base commit, untracked included, the session path's temporary-index diff with `workspace_base_sha`, survives a model commit, the live-harvest qualification): Task 1; both directions in `test_harvest_qualification.py` and `test_session_patch.py`. The spec's `.gitignore` for task bases is the generator's (2b); `calc-build` carries one and the harvest excludes residue without it.
- **Item 3, tripwire** (tokens and turns read as written, `BUDGET_EXCEEDED` a fail, budgets from the record): Task 2; the Engine arm under it, Task 5.
- **Item 4, census** (over `COMMAND_TIMEOUT` cells; escapes in bash text including root-anchored `find`; transcript contamination for every cell including `NO_PATCH`; a timeline of tool-call start and end): Task 3 detectors and timeline, Task 4 binder into `summary.json`. `git commit` inside the worktree and guard firings are counted too (spec "Measures").
- **Item 5, hygiene** (the manifests test; `~/satyrn-smokes`; attempt directories): Task 6 code and checklist.
- **Row 2a "the Engine arm runs against a fake"**: Task 5.
- **Not here, by the brief and Ruling 9**: isolation (item 2), the generator and R1-plan (item 6), qualification, the probe, the warm prefix.

## Test verification (plan review, 2026-09-14)

Every test this plan specifies was run in a scratch copy of evals `release-one` at `76e20d8` (`git archive` + `uv sync --offline`, never the main checkout), first against the unchanged tree and then against a prototype of each task's implementation as written here. Task 5's integration rows ran against the engine checkout at Phase 1 Tasks 1–10 (`c367548`–`2509513`).

- Default tier: 1,679 passed before; 1,754 passed with all six tasks, the session guard active and silent. The guard failed a session when a probe test copied an overlay (Task 6 Step 4).
- Integration tier, whole: 277 passed, 1 skipped, 2 failed — the two `test_real_e5_*` rows, which fail identically on the unchanged tree against the Phase 1 engine.
- Each new test fails on today's tree for the missing implementation only: import or keyword errors, and `test_harvest_qualification.py`'s first row fails `attempt refused: NO_PATCH`, the defect it exists for.

Defects found in the draft and fixed in this plan: the manifests replacement named `test_hidden.py` where the validator matches `tests/test_hidden.py` (did not raise); `_valid_v4_record` needs the `BUDGET_EXCEEDED` case or the code-matrix row fails; the Engine adapter spawned `satyrn-engine` into the attempt's `UV_PROJECT_ENVIRONMENT` and every Engine cell was `NO_PATCH` (Ruling 7); a truncated transcript is `malformed`, not `partial`; `tests/test_pathology.py` has no `pytest` import; a finished-over-budget workspace row needed a write-on-wait process (a pre-written transcript trips live and would signal a fake pid); the six `test_attempt_pi.py` rows, two `tests/integration/test_attempt_pi.py` rows and nine `test_run_record.py` rows that pin old shapes are listed with their changes; ruff wants one blank line before `RESIDUE_EXCLUDES`'s comment and `budget` imported after `attempt_record`; `ls -r` is not recursive; an extra teardown grace was not needed (Ruling 8).

R21 steps (added at approval, verified in a scratch clone of engine `9ad3583`): the Step 0a file as written gives 3 failed, 1 passed on the unchanged engine (each failure a 30 s join timeout, 92 s total); with Step 0b's block applied, 4 passed in 0.24 s, `ruff check` clean, the engine default tier 486 passed, and `test_integration_attempt.py`, `test_integration_delivery.py`, `test_integration_implement.py` 70 passed, 1 skipped. `ruff format --check` reports 10 engine files unformatted before the change; formatting is not an engine gate.
