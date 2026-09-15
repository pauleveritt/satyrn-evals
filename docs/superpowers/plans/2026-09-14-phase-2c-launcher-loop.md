# Phase 2c — The launcher's cell loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-14 under the maintainer's overnight authority (he is asleep; open questions are decided below as Rulings).** Planned against Phase 2b's plan (`docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md`, committed `ec5482f`, executing on `release-one` tonight) as its six task commits replayed (tag `t6`, trees identical to that plan's blocks). Every test below was run before hand-back (see "Test verification").

**Goal:** Roadmap row 2c: `satyrn-evals launch RECORD` runs a frozen record's cells — n per arm, k at a time, arms interleaved, under the record's isolation profile, budget and backstop — stops on an infrastructure failure and never on a model outcome, stops cleanly on a signal, resumes a stopped night without re-running a finished cell, and writes a per-night ledger, per-arm summaries and a committed result; `satyrn-evals record new` writes the record. Then tonight's Baseline admission cells run through it.

**Architecture:** Three layers, one per task. `run_record` gains the fields a launch needs (k, rung, authority, interleaved arms) and `record new`. `launch.launch_cells` is a pure loop over slots that takes `spawn` and `drift` callables, so the default tier drives it with fake processes and a fake clock. `launch_record.launch_record` is the gates (frozen, committed, caps, the seams a deciding record refuses, the cell preflight, the settings provenance), the drift probe, and the real spawn: each cell is its own `python -m satyrn_evals.launch_cell SPEC` process in its own session, running `attempt` and writing `slots/NN.json` only when the attempt returns a record.

**Tech Stack:** Python 3.14, uv, pytest (default tier: audit-hook spawn tripwire; `integration` marker), ruff, just; git 2.45.1 (Homebrew); sudo; the Phase 2b cell user `satyrn-cell`; `satyrn-engine` checkout for the one Engine row.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` — "The eval" (isolation; budget and backstop; concurrency k; arms interleaved; admission rule; sample and decision rule: "a night the cap stops early completes the next night under the same record"; campaign record; denominators: "only an established infrastructure failure replaces one"), "Process" (the launcher is the only path to a model and refuses without a frozen run record, the previous result committed, n and wall clock under the cadence cap, and a clean `preflight_settings` provenance block; cadence caps; docs caps; plans tested up front). Contract: Phase 2b plan's Interfaces blocks (Tasks 1–3, 6) and its Rulings 1, 7, 8, 11, 19. House style: the 2a and 2b plans.

## Rulings

Conflicts between the spec, 2b's contract and the code at `t6`, each with the ruling, why, and the cost if wrong. The maintainer is asleep; all are this plan's.

1. **A cell is a process, not a thread.** `launch_record` starts `python -m satyrn_evals.launch_cell SPEC` per cell (`start_new_session=True`). `attempt` has no cancellation and signals reach only the main thread, so a thread pool could not stop a running cell; a process gets SIGTERM, which `run._abort_on_signals` turns into `SignalAbort` inside `attempt`, whose workspace teardown already stops the model (the cell-side kill included, 2b Ruling 7). The loop sends SIGTERM, waits `grace` (60 s), then SIGKILLs the child's group. Cost if wrong: none identified; the SIGTERM integration row shows the fake `pi` gone and no workspace left.
2. **The record gains `k`, `rung` and `authority`, optional with defaults 1, null, null.** k is the spec's frozen concurrency. `rung` is forced by this plan's verification: both AgentClinic manifests' default `contract` is their **R3** text, while the spec runs them at **R1**; without a pinned rung every AgentClinic admission cell would have run at the wrong rung. `authority` carries tonight's exception in the record itself. Optional, unlike 2b's required fields, so every earlier record and test fixture still loads; `record new` always writes all three. `record new --rung contract` pins the manifest default (tasks without a `contracts` map, e.g. `calc-build`). Cost if wrong: a hand-written record without `rung` runs the default contract; the checklist writes every record with `record new`.
3. **Interleaved arms are named in `arm`, joined by `+`** (`baseline+engine`), in the order the launcher alternates them; `record_arms(record)` splits it. `check_invocation` accepts a command of any of the record's arms; `launch --preflight` accepts an arm file of any of them. `n` stays per arm (the attended cap n ≤ 8 and the batch cap n ≤ 12 are per arm, as the spec's "24 cells across both arms" reads). Cost if wrong: one string field instead of a list; the loader refuses a repeated or ill-formed arm.
4. **Interleaving is strict alternation, not a seeded shuffle.** Slot i runs `arms[i % len(arms)]`. A night stopped at any point leaves the arms at most one cell apart, and at k = 2 every concurrent pair is one cell of each arm, so prefill contention is shared equally. `scripts/interleave.py`'s seeded order remains for one-cell-per-directory schedules. Cost if wrong: a fixed order could correlate with a time-of-night effect; at k = 2 both arms share every slot pair, which bounds it.
5. **What stops a night.** Infrastructure: the codes `WORKSPACE_FAILED`, `CLEANUP_FAILED`, `GRADE_FAILED`, `TRANSCRIPT_MISSING`, `TRANSCRIPT_EMPTY`, `MODEL_ERROR` (2a's classification of an unreachable or failing server), `PATCH_INVALID`; `DEADLINE_EXCEEDED` outside the command phase; a cell process that exits without a slot record (an adapter or harness crash); drift between cells. A model outcome never stops it: `OK`, `NO_PATCH`, `COMMAND_TIMEOUT`, `BUDGET_EXCEEDED`, `REPEAT_LIMIT`, `DEADLINE_EXCEEDED` in the command. On a stop no new cell starts and running cells finish (their outcomes are real). A finished infrastructure slot is replaced on the next launch: its record moves to `slots/NN.replaced-M.json`, its attempt directory stays on disk, and the ledger and result list it. Nothing is retried within a launch. Cost if wrong: a `PATCH_INVALID` caused by a model writing binary junk would stop a night; it has never been observed and the stop is loud.
6. **Where results go.** The night directory is `RUNS_ROOT/<record stem>/` with `RUNS_ROOT` defaulting to `~/satyrn-runs` (the maintainer's 700 home, which `launch --preflight` already proves the cell cannot read): `launch.json` (ledger: every sitting, every finished and replaced slot), `slots/`, and one `run`-shaped directory per arm whose `summary.json` is written when that arm's n cells are finished (`satyrn-evals summarize` rebuilds it). The committed result is `<record>.result.json` beside the record in `records/` — counts, cells, sittings — and a later record's `previous_result` names it. It is not a `docs/results/` page: the docs cap is twelve result files and Phase 4 alone needs nine; the human page for admission is Phase 3's reading. `records/` is outside `tools/provenance.py`'s tracked directories, so records and results need no provenance rows. Cost if wrong: one more directory at the repository root.
7. **A deciding record refuses every test seam.** Admission, route-proof and campaign records refuse `--no-settings`, `--no-hunt`, a `--timeout` other than 1,800 s, an `--attempt-timeout` other than 2,100 s, and `SATYRN_CELL_PATH_PREFIX` (2b Ruling 8). Development records may use them, which is how the integration rows run a fake `pi`. Cost if wrong: none; a deciding cell runs only under the spec's settings.
8. **The wall clock is checked before each cell, with the cell's whole deadline.** A cell starts only while `elapsed + attempt deadline ≤ max_minutes × 60`; otherwise nothing new starts, running cells finish, and the launch exits 4 (`capped`). Launching the same record again resumes it (a new sitting in the ledger). Admission records stay `mode: attended`, 60 minutes: at a 2,100 s deadline a sitting starts cells only in its first 25 minutes, so a slow task takes several consecutive sittings, each re-running the full preflight. That is the spec's cadence ("a night the cap stops early completes the next night under the same record") applied per sitting. Cost if wrong: about a minute of hunt per extra sitting.
9. **Frozen means tracked and unchanged against `HEAD`** in the git repository that holds the record (`git ls-files --error-unmatch` and `git diff --quiet HEAD --`). `gate(record_frozen=)` is a new keyword whose `None` means unchecked, so `launch --check` is unchanged. `write_new_record` reads the new file back through `gate` with `previous_result_committed=True` (found by verification: a record naming a previous result could not be written at all); the commit is the launcher's fact. Cost if wrong: none identified.
10. **Drift between cells is pins, not the cell preflight.** Before each cell: the record's and arm files' bytes, the task tree digest, and each arm's `preflight_settings` provenance JSON (re-run; `--cell` under isolation) must equal what the launch began with. The cell preflight (stale cell processes, readable paths, `pi --version`, the hunt) runs once at launch start: at k > 1 a running sibling is a cell process and would read as stale. Cost if wrong: a `pi` upgraded mid-sitting is caught only by the next launch.
11. **Warm-prefix recording and replay move to 2d** (roadmap row added), landing before Phase 4, where the warm secondary is used. Nothing in admission or route proof needs it. Cost if wrong: none; it was never on tonight's path.
12. **The first isolated Pi turn goes through the launcher** with a committed development record on `calc-build`, replacing 2b checklist item 8's direct `attempt` (which the repository hook blocks for an agent operator in any case). Cost if wrong: none; the same attempt runs.
13. **Tonight's operator decides k and nothing else from the probe.** k is `analyze`'s `k`. A context cap is not set unattended: it would change Pi's model config and the settings provenance, and the spec makes it a sitting's decision; the decode rates go into the morning status for the maintainer. Cost if wrong: admission runs at native context, as every earlier Ornith cell did.
14. **No new record launches after 06:30 EDT, 2026-09-15.** A record capped then is committed as capped and resumes next night under the same record. Cost if wrong: an idle GPU before 07:30.

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer per task; one Opus review per task before the next starts.
- **The controller blocks on every dispatch; nothing runs in the background** while building. (The overnight checklist's multi-minute commands are the one exception: see its preamble.)
- **No inference while building.** Fake `pi` only; no `launch` of a real model, no `pi -p`, no request to oMLX. The overnight checklist is the only place inference happens, after all three tasks are committed.
- **Default test tier: no subprocess, no network, no model** (the audit hook in `tests/conftest.py`). Anything that spawns is `@pytest.mark.integration`. Every integration row that needs `satyrn-cell` takes the `cell_scratch` fixture, which skips with the reason when `sudo -n -u satyrn-cell true` fails.
- **Every refusal test has a sibling success test**; every detector has a firing row and a silent row.
- **Every task ends with `just gates` exit 0** (read the exit code; never pipe a gate). New files get `PROVENANCE.md` rows (`uv run python tools/provenance.py new <paths>`); edited files keep theirs. Run `uv run ruff check --fix` before gates.
- **Integration runs name their files, never concurrently with another cell-user test run** (the launch preflight counts any running cell process as stale). After Task 3: `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q tests/integration/test_launch_record.py tests/integration/test_isolated_arms.py tests/integration/test_cell_isolation.py tests/integration/test_cell_preflight.py tests/integration/test_run_signal.py tests/integration/test_budget_attempt.py tests/integration/test_evidence_run.py tests/integration/test_engine_arm.py`.
- **Four integration rows fail on this Mac before any change**: `tests/test_workspace_failures.py::test_prepare_repository_fails_closed_on_verification[*]` (their fake environment reaches `/usr/bin/git`, which refuses until the Xcode license is accepted). Reported, never fixed here, never counted against a task.
- **Commit at the end of every task** on evals `release-one`, with the plan's message. Never `--amend`, merge or push. A task whose gates are red is not committed.
- **Evals tree only.** The engine is read, never edited. **The cell user is the maintainer's**: never create or change users, groups or `/etc/sudoers.d`; the only sudo forms are `sudo -n -u satyrn-cell` and `sudo -n -H -u satyrn-cell`; never `pkill -U satyrn-cell`; under `/Users/Shared/satyrn-cells` create only what tests and attempts create and remove.
- **Nothing is written to `/tmp` or `/private/tmp`** except under the session scratchpad `$SCR` (`/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/phase2c-exec/`). Tests use pytest's `tmp_path`; an integration `--basetemp` is under `$SCR` and removed right after the run.
- **No test copies a bundled hidden task into pytest's temp directory.** Integration rows run `calc-build` from `tests/integration/data/tasks`; default-tier rows only read bundled trees in place.
- **Starting point:** evals `release-one` with Phase 2b's six task commits and this plan's commit. If 2b's executor deviated from its plan, a diff hunk below may not apply verbatim: apply it by hand to the same effect and say so in the task report. Docs caps stand: `ROADMAP.md` ≤ 150 lines; `just lint-docs` exit 0. Old worktrees under `.claude/worktrees/` are never checked out, edited or removed.

---

## File structure

```
src/satyrn_evals/run_record.py        # k, rung, authority; record_arms; gate(record_frozen=); new_record, write_new_record  (modify, T1)
src/satyrn_evals/cli.py               # record new (T1); launch RECORD, --arm repeatable (T3)                               (modify, T1 T3)
src/satyrn_evals/launch.py            # the pure cell loop: slots, k, stops, resume, signals, ledger                         (new, T2)
src/satyrn_evals/launch_cell.py       # one cell process: attempt, then slots/NN.json; PopenCell                             (new, T3)
src/satyrn_evals/launch_record.py     # launch RECORD: gates, preflight, settings, drift, spawn, summaries, result            (new, T3)
tests/test_run_record.py, tests/test_record_new.py                                                                          (modify/new, T1)
tests/test_launch.py                                                                                                          (new, T2)
tests/test_launch_record.py, tests/integration/test_launch_record.py                                                         (new, T3)
tests/integration/fake_pi_build.py    # mode "unreachable"                                                                   (modify, T3)
ROADMAP.md                            # row 2c built; row 2d (warm prefix)                                                   (modify, T3)
```

---

### Task 1: Records the launcher can run, and `record new`

**Files:**
- Create: `tests/test_record_new.py`
- Modify: `src/satyrn_evals/run_record.py` (imports; constants; `RunRecord` optional fields; `_OPTIONAL`; loader checks; `record_arms`; `gate(record_frozen=)`; `check_invocation` membership; `new_record`; `write_new_record`), `src/satyrn_evals/cli.py` (imports; `record` dispatch; `_record_new`; the `record new` parser), `tests/test_run_record.py` (import and appended rows only)

**Interfaces:**
- Consumes (2b): `run_record.RunRecord`, `load_run_record`, `gate`, `check_invocation`, `PURPOSES`, `DECIDING_PURPOSES`; `task_tree.tree_digest`; `attempt.resolve_contract`; `manifest.load_manifest`, `resolve_task`.
- Produces: `RunRecord.k: int = 1`, `.rung: str | None = None`, `.authority: str | None = None`; `run_record.K_VALUES = (1, 2, 3)`, `ARM_SEPARATOR = "+"`, `STOP_RULE`, `ADMISSION_DECISION_RULE`; `record_arms(record) -> tuple[str, ...]`; `gate(record, *, previous_result_committed, record_frozen: bool | None = None)` (refuses "not frozen" on `False`); `check_invocation` accepts any arm of `record_arms`; `new_record(*, task, tasks_root, arm, model, n, k, rung: str | None, purpose, isolation, mode, max_minutes, token_budget, turn_budget, previous_result, authority, decision_rule, stop_rule=STOP_RULE) -> dict` (RunRecordError for a campaign or route-proof record without a decision rule; UsageError for an unknown rung); `write_new_record(path, body) -> RunRecord` (refuses an existing path; removes a file the loader or gate refuses). CLI: `satyrn-evals record new --output P --task T --arm A --rung R|contract --n N --k K --purpose P [--isolation isolated] [--model omlx/Ornith-1.5-9B-MLX-8bit] [--mode attended] [--max-minutes 60] [--token-budget 32000] [--turn-budget 48] [--previous-result P] [--authority TEXT] [--decision-rule TEXT] [--tasks-root R]` → exit 0 and one line naming the path and digest; 2 on any refusal.

- [ ] **Step 1: Failing tests.** Apply to `tests/test_run_record.py` (no existing assertion changes):

```diff
diff --git a/tests/test_run_record.py b/tests/test_run_record.py
index 57d92cd..3817b5b 100644
--- a/tests/test_run_record.py
+++ b/tests/test_run_record.py
@@ -17,6 +17,7 @@ from satyrn_evals.run_record import (
     command_model,
     gate,
     load_run_record,
+    record_arms,
 )
 from satyrn_evals.task_tree import tree_digest

@@ -235,3 +236,44 @@ def test_the_command_arm_and_model_are_read_from_either_spelling() -> None:
     assert command_arm(["cmd"]) is None
     assert command_model(["a", "--model=omlx/m"]) == "omlx/m"
     assert command_model(["a", "--model"]) is None
+
+
+# --- 2c: concurrency, rung, authority, interleaved arms, the frozen fact -------
+
+
+def test_a_record_without_the_2c_fields_runs_one_cell_at_a_time_on_the_default_contract(tmp_path: Path) -> None:
+    record = load_run_record(_write(tmp_path))
+    assert (record.k, record.rung, record.authority) == (1, None, None)
+    assert record_arms(record) == ("baseline",)
+
+
+def test_the_2c_fields_load(tmp_path: Path) -> None:
+    record = load_run_record(_write(tmp_path, k=3, rung="R1", authority="the maintainer, 2026-09-14"))
+    assert (record.k, record.rung, record.authority) == (3, "R1", "the maintainer, 2026-09-14")
+
+
+@pytest.mark.parametrize("k", [0, 4, True])
+def test_k_outside_one_to_three_is_refused(tmp_path: Path, k: object) -> None:
+    with pytest.raises(RunRecordError, match="k must be 1, 2 or 3|k has the wrong type"):
+        load_run_record(_write(tmp_path, k=k))
+
+
+@pytest.mark.parametrize("arm", ["baseline+baseline", "baseline+", "Baseline"])
+def test_an_ill_formed_arm_list_is_refused(tmp_path: Path, arm: str) -> None:
+    with pytest.raises(RunRecordError, match="arm must name distinct arms"):
+        load_run_record(_write(tmp_path, arm=arm))
+
+
+def test_an_interleaved_record_accepts_either_arms_command(tmp_path: Path) -> None:
+    record = _pinned(tmp_path, arm="baseline+engine")
+    assert record_arms(record) == ("baseline", "engine")
+    engine = ["satyrn-evals-attempt-engine", "--model", "omlx/gemma-4-12B-it-MLX-8bit"]
+    for command in (BASELINE, engine):
+        check_invocation(record, task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=command)
+
+
+def test_an_unfrozen_record_is_refused_and_a_frozen_one_passes(tmp_path: Path) -> None:
+    record = load_run_record(_write(tmp_path))
+    with pytest.raises(RunRecordError, match="not frozen"):
+        gate(record, previous_result_committed=None, record_frozen=False)
+    gate(record, previous_result_committed=None, record_frozen=True)
```

`tests/test_record_new.py`:

```python
"""``satyrn-evals record new``: a record the launcher accepts, written without hand-editing JSON."""

import json
from pathlib import Path

import pytest

from satyrn_evals.cell import Isolation
from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import (
    ADMISSION_DECISION_RULE,
    RunRecordError,
    load_run_record,
    new_record,
    record_arms,
)
from satyrn_evals.task_tree import tree_digest

TASK = "agentclinic-repair-depth-3"
AUTHORITY = "maintainer's one-time unattended-inference exception, 2026-09-14"


def _new(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "record", "new", "--output", str(tmp_path / "records" / "depth-3.json"), "--task", TASK,
        "--arm", "baseline", "--rung", "R1", "--n", "4", "--k", "2", "--purpose", "admission",
        "--authority", AUTHORITY, *extra,
    ]


def test_an_admission_record_is_written_with_the_tree_digest_and_the_spec_rule(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    record = load_run_record(tmp_path / "records" / "depth-3.json")
    assert record.task_tree_sha256 == tree_digest(DEFAULT_TASKS_ROOT / TASK)
    assert (record.n, record.k, record.rung, record.purpose) == (4, 2, "R1", "admission")
    assert record.isolation is Isolation.ISOLATED
    assert (record.token_budget, record.turn_budget, record.max_minutes) == (32000, 48, 60)
    assert record.decision_rule == ADMISSION_DECISION_RULE and record.authority == AUTHORITY
    assert record.model == "omlx/Ornith-1.5-9B-MLX-8bit" and record.previous_result is None


def test_a_written_record_is_never_overwritten(tmp_path: Path) -> None:
    assert main(_new(tmp_path)) == 0
    before = (tmp_path / "records" / "depth-3.json").read_text()
    assert main(_new(tmp_path, "--n", "3")) == 2
    assert (tmp_path / "records" / "depth-3.json").read_text() == before


def test_an_unknown_rung_writes_nothing(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--rung", "R9")) == 2
    assert not (tmp_path / "records" / "depth-3.json").exists()


def test_a_record_the_gate_refuses_is_not_left_behind(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--isolation", "local")) == 2
    assert main(_new(tmp_path, "--n", "9")) == 2
    assert not (tmp_path / "records" / "depth-3.json").exists()


@pytest.mark.parametrize("k", ["0", "4"])
def test_k_outside_one_to_three_is_a_usage_error(tmp_path: Path, k: str) -> None:
    with pytest.raises(SystemExit):
        main(_new(tmp_path, "--k", k))


def test_a_campaign_record_must_state_its_decision_rule(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="needs --decision-rule"):
        new_record(
            task=TASK, tasks_root=DEFAULT_TASKS_ROOT, arm="baseline+engine", model="omlx/m", n=12, k=2,
            rung="R1", purpose="campaign", isolation="isolated", mode="batch", max_minutes=720,
            token_budget=32000, turn_budget=48, previous_result=None, authority=None, decision_rule=None,
        )


def test_an_interleaved_development_record_names_both_arms_in_order(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    assert main([
        "record", "new", "--output", str(out), "--task", TASK, "--arm", "baseline+engine", "--rung", "R1",
        "--n", "2", "--k", "2", "--purpose", "development", "--isolation", "local",
    ]) == 0
    assert record_arms(load_run_record(out)) == ("baseline", "engine")
    assert json.loads(out.read_text())["decision_rule"] == "none: development, no task outcome"


def test_the_default_contract_is_pinned_as_a_null_rung(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    assert main([
        "record", "new", "--output", str(out), "--task", "format_number", "--arm", "baseline",
        "--rung", "contract", "--n", "1", "--k", "1", "--purpose", "development",
    ]) == 0
    assert load_run_record(out).rung is None


def test_a_record_that_follows_a_result_is_written_and_its_commit_is_left_to_launch(tmp_path: Path) -> None:
    assert main(_new(tmp_path, "--previous-result", "records/depth-3.result.json")) == 0
    assert load_run_record(tmp_path / "records" / "depth-3.json").previous_result == "records/depth-3.result.json"
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest -q tests/test_run_record.py tests/test_record_new.py` → `Interrupted: 2 errors during collection`: `ImportError: cannot import name 'record_arms' from 'satyrn_evals.run_record'` and `cannot import name 'ADMISSION_DECISION_RULE' from 'satyrn_evals.run_record'`.

- [ ] **Step 3: Implement.** Apply to `src/satyrn_evals/run_record.py`:

```diff
diff --git a/src/satyrn_evals/run_record.py b/src/satyrn_evals/run_record.py
index 842717b..16e9ea5 100644
--- a/src/satyrn_evals/run_record.py
+++ b/src/satyrn_evals/run_record.py
@@ -13,9 +13,11 @@ from dataclasses import dataclass
 from pathlib import Path
 from typing import Literal

+from satyrn_evals.attempt import resolve_contract
 from satyrn_evals.budget import AttemptBudget
 from satyrn_evals.cell import Isolation
 from satyrn_evals.errors import UsageError
+from satyrn_evals.manifest import load_manifest, resolve_task
 from satyrn_evals.task_tree import tree_digest

 type Mode = Literal["attended", "batch"]
@@ -34,6 +36,17 @@ ARM_ADAPTERS = {
 }

 CAPS: dict[str, tuple[int, int]] = {"attended": (8, 60), "batch": (12, 720)}
+#: Concurrency the spec allows ("Concurrency, both arms"): the largest of 1, 2 or 3 the probe admits.
+K_VALUES = (1, 2, 3)
+#: Arms a record interleaves are joined with this separator in its ``arm`` field (Ruling 3).
+ARM_SEPARATOR = "+"
+STOP_RULE = "established infrastructure failure only"
+#: The spec's admission rule ("Workloads"), written into every admission record by ``record new``.
+ADMISSION_DECISION_RULE = (
+    "admission: ceiling when bare Pi passes at most 1 of 4 within budget and no passing cell "
+    "read material outside its worktree; floor when it passes 4 of 4; a ceiling candidate "
+    "passing 2 of 4 or more moves to the floor set"
+)
 _HEX64 = re.compile(r"^[0-9a-f]{64}$")


@@ -61,6 +74,10 @@ class RunRecord:
     # The launcher profile and what the run is for (Ruling 1).
     isolation: Isolation
     purpose: Purpose
+    # Phase 2c (Ruling 2): optional so earlier records load; ``record new`` always writes them.
+    k: int = 1
+    rung: str | None = None
+    authority: str | None = None


 _REQUIRED: dict[str, type | tuple[type, ...]] = {
@@ -71,6 +88,12 @@ _REQUIRED: dict[str, type | tuple[type, ...]] = {
 }


+_OPTIONAL: dict[str, type | tuple[type, ...]] = {
+    "k": int, "rung": (str, type(None)), "authority": (str, type(None)),
+}
+_ARM_PART = re.compile(r"^[a-z][a-z-]*$")
+
+
 def load_run_record(path: Path) -> RunRecord:
     try:
         body = json.loads(path.read_text())
@@ -103,17 +126,39 @@ def load_run_record(path: Path) -> RunRecord:
         raise RunRecordError(
             f"run record {path}: purpose must be one of {', '.join(sorted(PURPOSES))}"
         )
-    fields = {k: body[k] for k in _REQUIRED}
+    parts = body["arm"].split(ARM_SEPARATOR)
+    if not all(_ARM_PART.match(part) for part in parts) or len(set(parts)) != len(parts):
+        raise RunRecordError(f"run record {path}: arm must name distinct arms joined by {ARM_SEPARATOR}")
+    for field, kind in _OPTIONAL.items():
+        if field in body and (not isinstance(body[field], kind) or isinstance(body[field], bool)):
+            raise RunRecordError(f"run record {path}: {field} has the wrong type")
+    if body.get("k", 1) not in K_VALUES:
+        raise RunRecordError(f"run record {path}: k must be 1, 2 or 3")
+    fields = {k: body[k] for k in _REQUIRED} | {k: body[k] for k in _OPTIONAL if k in body}
     fields["isolation"] = Isolation(body["isolation"])
     return RunRecord(**fields)


+def record_arms(record: RunRecord) -> tuple[str, ...]:
+    """The arms the record runs, in the order the launcher alternates them."""
+    return tuple(record.arm.split(ARM_SEPARATOR))
+
+
 def attempt_budget(record: RunRecord) -> AttemptBudget:
     """The budget every attempt under this record is held to."""
     return AttemptBudget(output_tokens=record.token_budget, turns=record.turn_budget)


-def gate(record: RunRecord, *, previous_result_committed: bool | None) -> None:
+def gate(
+    record: RunRecord, *, previous_result_committed: bool | None, record_frozen: bool | None = None
+) -> None:
+    """Refuse a record outside the cadence; ``None`` for a fact means the caller did not check it.
+
+    ``record_frozen`` is the launcher's: the record file is tracked and has no
+    change against ``HEAD`` (``launch RECORD`` supplies it; ``--check`` does not).
+    """
+    if record_frozen is False:
+        raise RunRecordError("the run record is not frozen: commit it, unchanged, before launch")
     max_n, max_minutes = CAPS[record.mode]
     if record.n > max_n or record.max_minutes > max_minutes:
         raise RunRecordError(
@@ -154,7 +199,68 @@ def check_invocation(record: RunRecord, *, task: str, task_dir: Path, command: S
         raise RunRecordError(
             f"task_tree_sha256 drifted: the record pins {record.task_tree_sha256}, the tree is {actual}"
         )
-    if (arm := command_arm(command)) != record.arm:
+    if (arm := command_arm(command)) not in record_arms(record):
         raise RunRecordError(f"the record is for arm {record.arm}; the command runs {arm or 'no known adapter'}")
     if (model := command_model(command)) != record.model:
         raise RunRecordError(f"the record is for model {record.model}; the command passes --model {model}")
+
+
+def new_record(
+    *,
+    task: str,
+    tasks_root: Path,
+    arm: str,
+    model: str,
+    n: int,
+    k: int,
+    rung: str | None,
+    purpose: str,
+    isolation: str,
+    mode: str,
+    max_minutes: int,
+    token_budget: int,
+    turn_budget: int,
+    previous_result: str | None,
+    authority: str | None,
+    decision_rule: str | None,
+    stop_rule: str = STOP_RULE,
+) -> dict[str, object]:
+    """A record body ``load_run_record`` and ``gate`` accept, with the tree digest and rung read from the task.
+
+    ``rung=None`` pins the manifest's default ``contract`` (a task without a
+    ``contracts`` map). The decision rule defaults only for admission (the spec's rule) and
+    development; route-proof and campaign records state their own.
+    """
+    task_dir = resolve_task(task, tasks_root=tasks_root)
+    resolve_contract(load_manifest(task_dir), rung)
+    if decision_rule is None:
+        match purpose:
+            case "admission":
+                decision_rule = ADMISSION_DECISION_RULE
+            case "development":
+                decision_rule = "none: development, no task outcome"
+            case _:
+                raise RunRecordError(f"a {purpose} record needs --decision-rule")
+    return {
+        "version": 1, "task": task, "task_tree_sha256": tree_digest(task_dir), "arm": arm, "model": model,
+        "condition": "cold", "n": n, "mode": mode, "max_minutes": max_minutes, "stop_rule": stop_rule,
+        "decision_rule": decision_rule, "previous_result": previous_result, "token_budget": token_budget,
+        "turn_budget": turn_budget, "isolation": isolation, "purpose": purpose, "k": k, "rung": rung,
+        "authority": authority,
+    }
+
+
+def write_new_record(path: Path, body: dict[str, object]) -> RunRecord:
+    """Write ``body`` to a new file and read it back through the loader and the gate; never overwrite."""
+    if path.exists():
+        raise RunRecordError(f"{path} exists: a written record is frozen, write a new one")
+    path.parent.mkdir(parents=True, exist_ok=True)
+    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
+    try:
+        record = load_run_record(path)
+        # Whether the previous result is committed is the launcher's fact, checked at launch.
+        gate(record, previous_result_committed=True)
+    except RunRecordError:
+        path.unlink()
+        raise
+    return record
```

Apply to `src/satyrn_evals/cli.py`:

```diff
diff --git a/src/satyrn_evals/cli.py b/src/satyrn_evals/cli.py
index f5d8516..bf94655 100644
--- a/src/satyrn_evals/cli.py
+++ b/src/satyrn_evals/cli.py
@@ -26,11 +26,15 @@ from satyrn_evals.qualify import qualify
 from satyrn_evals.rescore import regrade_attempt, summarize_output
 from satyrn_evals.run import run
 from satyrn_evals.run_record import (
+    K_VALUES,
+    PURPOSES,
     RunRecordError,
     attempt_budget,
     check_invocation,
     gate,
     load_run_record,
+    new_record,
+    write_new_record,
 )
 from satyrn_evals.session import run_session
 from satyrn_evals.session_grader import SessionGrader
@@ -212,6 +216,8 @@ def main(argv: list[str] | None = None) -> int:
             gate(record, previous_result_committed=previous_result_committed)
             print("launch: record accepted")
             return 0
+        if args.command == "record":
+            return _record_new(args)
         if args.command == "cell-engine":
             print(export_engine(Path(args.engine_repo), args.commit))
             return 0
@@ -282,6 +288,19 @@ def _launch_preflight(args: argparse.Namespace) -> int:
     return 1 if problems else 0


+def _record_new(args: argparse.Namespace) -> int:
+    """Write one run record from flags, read it back through the loader and gate, print its path."""
+    body = new_record(
+        task=args.task, tasks_root=Path(args.tasks_root), arm=args.arm, model=args.model, n=args.n, k=args.k,
+        rung=None if args.rung == "contract" else args.rung, purpose=args.purpose, isolation=args.isolation, mode=args.mode,
+        max_minutes=args.max_minutes, token_budget=args.token_budget, turn_budget=args.turn_budget,
+        previous_result=args.previous_result, authority=args.authority, decision_rule=args.decision_rule,
+    )
+    write_new_record(Path(args.output), body)
+    print(f"record: wrote {args.output} (task_tree_sha256 {body['task_tree_sha256']}); commit it before launch")
+    return 0
+
+
 parser = argparse.ArgumentParser(
     prog="satyrn-evals",
     description="Offline grading and task capture for development tasks.",
@@ -485,4 +504,27 @@ launch_p.add_argument(
     "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
 )

+record_p = sub.add_parser("record", help="write a run record the launcher accepts")
+record_sub = record_p.add_subparsers(dest="record_command", required=True)
+record_new_p = record_sub.add_parser("new", help="write a new run record from flags; never overwrites")
+record_new_p.add_argument("--output", required=True, help="record path to create (e.g. records/NAME.json)")
+record_new_p.add_argument("--task", required=True, help="task name")
+record_new_p.add_argument("--arm", required=True, help="arm, or arms joined by + to interleave (baseline+engine)")
+record_new_p.add_argument("--rung", required=True, help="contract rung key from the task manifest (R1, R1-plan), or contract for its default text")
+record_new_p.add_argument("--n", type=positive_int, required=True, help="cells per arm")
+record_new_p.add_argument("--k", type=int, choices=K_VALUES, required=True, help="cells at a time")
+record_new_p.add_argument("--purpose", required=True, choices=sorted(PURPOSES))
+record_new_p.add_argument("--isolation", default="isolated", choices=["isolated", "local"])
+record_new_p.add_argument("--model", default="omlx/Ornith-1.5-9B-MLX-8bit")
+record_new_p.add_argument("--mode", default="attended", choices=["attended", "batch"])
+record_new_p.add_argument("--max-minutes", type=positive_int, default=60)
+record_new_p.add_argument("--token-budget", type=positive_int, default=32000)
+record_new_p.add_argument("--turn-budget", type=positive_int, default=48)
+record_new_p.add_argument("--previous-result", default=None, help="the committed result this record follows")
+record_new_p.add_argument("--authority", default=None, help="who authorized this spend, and when")
+record_new_p.add_argument("--decision-rule", default=None, help="required unless purpose is admission or development")
+record_new_p.add_argument(
+    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
+)
+
 build_census_parser(sub)
```

- [ ] **Step 4: Pass.** `uv run pytest -q tests/test_run_record.py tests/test_record_new.py tests/test_cli.py tests/test_cell_preflight.py` → 119 passed.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new tests/test_record_new.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2c: a run record pins k, rung and authority and may interleave arms; record new writes one the gate accepts"
```

Expected: gates EXIT 0 (default tier 20 more rows than 2b's end state; 1,936 on the replay).

---

### Task 2: The cell loop

**Files:**
- Create: `src/satyrn_evals/launch.py`, `tests/test_launch.py`

**Interfaces:**
- Consumes (2a/2b): `attempt_record.AttemptCode`; `run._abort_on_signals`, `run.SignalAbort`; `errors.UsageError`.
- Produces: `launch.LEDGER_NAME = "launch.json"`, `SLOTS_DIR = "slots"`, `INFRASTRUCTURE_CODES`; `class Status(StrEnum)`: `COMPLETE`, `CAPPED`, `INFRASTRUCTURE`, `INTERRUPTED`; `@dataclass Slot(index: int, arm: str)` with `.name` (`"03"`); `class CellProcess(Protocol)`: `poll() -> int | None`, `terminate()`, `kill()`; `type Spawn = Callable[[Slot], CellProcess]`, `type Drift = Callable[[], str | None]`; `@dataclass LaunchOutcome(status, reason, finished: list[dict], replaced: list[dict])`; `plan_slots(arms, n) -> list[Slot]`; `slot_path(night, slot) -> Path` (`night/slots/NN.json`); `infrastructure_reason(result: dict) -> str | None`; `read_slots(night) -> dict[int, dict]`; `write_ledger(night, *, identity, sitting, outcome)`; `check_night(night, identity)` (UsageError when the ledger belongs to another record); `launch_cells(*, night, arms, n, k, max_seconds, cell_seconds, spawn, drift, grace=60.0, poll_interval=1.0, clock=time.monotonic, sleep=time.sleep) -> LaunchOutcome` (never raises for a signal: returns `INTERRUPTED`). A slot result dict is `{"slot", "arm", "attempt_dir", "code", "verdict", "message", "command_exit", "deadline_phase"}` (written by Task 3's cell process).

- [ ] **Step 1: Failing tests.** `tests/test_launch.py`:

```python
"""The launcher's cell loop against fake cell processes and a fake clock: nothing spawns."""

import json
import signal
from pathlib import Path

import pytest

from satyrn_evals.errors import UsageError
from satyrn_evals.launch import (
    LEDGER_NAME,
    SLOTS_DIR,
    Slot,
    Status,
    check_night,
    infrastructure_reason,
    launch_cells,
    plan_slots,
    read_slots,
    slot_path,
    write_ledger,
)
from satyrn_evals.run import SignalAbort


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeCell:
    """A cell that finishes after ``polls`` polls, writing its slot record unless ``code`` is None."""

    def __init__(self, night: Path, slot: Slot, *, code: str | None, polls: int, phase: str | None = None) -> None:
        self.night, self.slot, self.code, self.polls, self.phase = night, slot, code, polls, phase
        self.exit: int | None = None
        self.signals: list[str] = []

    def _write(self) -> None:
        if self.code is None:
            return
        slot_path(self.night, self.slot).write_text(json.dumps({
            "slot": self.slot.index, "arm": self.slot.arm, "attempt_dir": f"t-{self.slot.index}",
            "code": self.code, "verdict": "pass" if self.code == "OK" else None, "message": f"attempt {self.code}",
            "deadline_phase": self.phase,
        }))

    def poll(self) -> int | None:
        if self.exit is None:
            self.polls -= 1
            if self.polls <= 0:
                self._write()
                self.exit = 0 if self.code is not None else 1
        return self.exit

    def terminate(self) -> None:
        self.signals.append("TERM")
        self.exit = 143

    def kill(self) -> None:
        self.signals.append("KILL")
        self.exit = -9


class Spawner:
    def __init__(self, night: Path, clock: Clock, codes: dict[int, str | None] | None = None, polls: int = 3) -> None:
        self.night, self.clock, self.codes, self.polls = night, clock, codes or {}, polls
        self.started: list[tuple[float, Slot]] = []
        self.cells: dict[int, FakeCell] = {}
        self.max_running = 0

    def __call__(self, slot: Slot) -> FakeCell:
        self.started.append((self.clock.now, slot))
        cell = FakeCell(self.night, slot, code=self.codes.get(slot.index, "OK"), polls=self.polls)
        self.cells[slot.index] = cell
        running = sum(1 for c in self.cells.values() if c.exit is None)
        self.max_running = max(self.max_running, running)
        return cell


def _launch(night: Path, spawner: Spawner, clock: Clock, **over: object):
    kwargs: dict[str, object] = dict(
        night=night, arms=("baseline", "engine"), n=2, k=2, max_seconds=3600, cell_seconds=100,
        spawn=spawner, drift=lambda: None, clock=clock, sleep=clock.sleep, poll_interval=1.0, grace=5.0,
    )
    return launch_cells(**{**kwargs, **over})


def test_slots_alternate_the_arms_in_record_order() -> None:
    assert [(s.index, s.arm) for s in plan_slots(("baseline", "engine"), 2)] == [
        (0, "baseline"), (1, "engine"), (2, "baseline"), (3, "engine"),
    ]
    assert [s.arm for s in plan_slots(("baseline",), 3)] == ["baseline"] * 3


def test_a_record_completes_k_at_a_time_in_slot_order(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock)
    outcome = _launch(tmp_path, spawner, clock)
    assert (outcome.status, outcome.reason) == (Status.COMPLETE, None)
    assert [slot.index for _, slot in spawner.started] == [0, 1, 2, 3]
    assert spawner.max_running == 2
    assert sorted(read_slots(tmp_path)) == [0, 1, 2, 3]
    assert [r["slot"] for r in outcome.finished] == [0, 1, 2, 3]


def test_k_one_runs_one_cell_at_a_time(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock)
    assert _launch(tmp_path, spawner, clock, k=1).status is Status.COMPLETE
    assert spawner.max_running == 1


@pytest.mark.parametrize("code", ["NO_PATCH", "COMMAND_TIMEOUT", "BUDGET_EXCEEDED", "REPEAT_LIMIT", "OK"])
def test_a_model_outcome_never_stops_the_night(tmp_path: Path, code: str) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, codes={0: code, 1: code})
    assert _launch(tmp_path, spawner, clock).status is Status.COMPLETE
    assert len(spawner.started) == 4


@pytest.mark.parametrize("code", ["MODEL_ERROR", "WORKSPACE_FAILED", "CLEANUP_FAILED", "GRADE_FAILED", "TRANSCRIPT_EMPTY"])
def test_an_infrastructure_outcome_stops_the_night_and_lets_running_cells_finish(tmp_path: Path, code: str) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, codes={0: code})
    outcome = _launch(tmp_path, spawner, clock)
    assert outcome.status is Status.INFRASTRUCTURE
    assert outcome.reason == f"slot 00 (baseline): {code}: attempt {code}"
    assert [slot.index for _, slot in spawner.started] == [0, 1]
    assert sorted(read_slots(tmp_path)) == [0, 1]  # slot 1 was running and finished


def test_a_deadline_outside_the_command_is_infrastructure_and_inside_it_is_not() -> None:
    base = {"slot": 3, "arm": "engine", "code": "DEADLINE_EXCEEDED", "message": "m"}
    assert infrastructure_reason({**base, "deadline_phase": "command"}) is None
    assert infrastructure_reason({**base, "deadline_phase": "grading"}) == "slot 03 (engine): DEADLINE_EXCEEDED in grading: m"


def test_a_cell_process_that_exits_without_a_record_stops_the_night(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, codes={1: None})
    outcome = _launch(tmp_path, spawner, clock)
    assert outcome.status is Status.INFRASTRUCTURE
    assert outcome.reason == "slot 01 (engine): the cell process exited 1 without an attempt record"


def test_drift_before_a_cell_stops_the_night(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock)
    answers = iter([None, None, "task_tree_sha256 drifted"])
    outcome = _launch(tmp_path, spawner, clock, drift=lambda: next(answers, None))
    assert (outcome.status, outcome.reason) == (Status.INFRASTRUCTURE, "preflight drift: task_tree_sha256 drifted")
    assert len(spawner.started) == 2


def test_the_wall_clock_stops_new_cells_and_a_second_launch_resumes_without_rerunning(tmp_path: Path) -> None:
    clock = Clock()
    first = Spawner(tmp_path, clock, polls=70)
    outcome = _launch(tmp_path, first, clock, k=1, max_seconds=160, cell_seconds=100)
    assert outcome.status is Status.CAPPED and "3 slot(s) wait" in (outcome.reason or "")
    assert [slot.index for _, slot in first.started] == [0]
    before = slot_path(tmp_path, Slot(0, "baseline")).read_text()
    clock2 = Clock()
    second = Spawner(tmp_path, clock2)
    assert _launch(tmp_path, second, clock2, k=1).status is Status.COMPLETE
    assert [slot.index for _, slot in second.started] == [1, 2, 3]
    assert slot_path(tmp_path, Slot(0, "baseline")).read_text() == before


def test_a_finished_infrastructure_slot_is_replaced_on_the_next_launch(tmp_path: Path) -> None:
    clock = Clock()
    assert _launch(tmp_path, Spawner(tmp_path, clock, codes={0: "MODEL_ERROR"}), clock, k=1).status is Status.INFRASTRUCTURE
    clock2 = Clock()
    second = Spawner(tmp_path, clock2)
    outcome = _launch(tmp_path, second, clock2, k=1)
    assert outcome.status is Status.COMPLETE
    assert [slot.index for _, slot in second.started] == [0, 1, 2, 3]
    assert [r["code"] for r in outcome.replaced] == ["MODEL_ERROR"]
    assert outcome.replaced[0]["replaced_because"].startswith("slot 00 (baseline): MODEL_ERROR")
    assert (tmp_path / SLOTS_DIR / "00.replaced-1.json").is_file()
    assert read_slots(tmp_path)[0]["code"] == "OK"


@pytest.mark.parametrize("error", [SignalAbort(signal.SIGTERM), KeyboardInterrupt()])
def test_a_signal_stops_every_running_cell_and_reports_interrupted(tmp_path: Path, error: BaseException) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, polls=1000)
    calls = {"n": 0}

    def sleep(seconds: float) -> None:
        calls["n"] += 1
        if calls["n"] == 3:
            raise error
        clock.sleep(seconds)

    outcome = _launch(tmp_path, spawner, clock, sleep=sleep)
    assert outcome.status is Status.INTERRUPTED and type(error).__name__ in (outcome.reason or "")
    assert [cell.signals for cell in spawner.cells.values()] == [["TERM"], ["TERM"]]
    assert read_slots(tmp_path) == {}


def test_a_cell_that_ignores_sigterm_is_killed_after_the_grace(tmp_path: Path) -> None:
    clock = Clock()
    spawner = Spawner(tmp_path, clock, polls=1000)

    class Stubborn(FakeCell):
        def terminate(self) -> None:
            self.signals.append("TERM")

    def spawn(slot: Slot) -> FakeCell:
        cell = Stubborn(tmp_path, slot, code="OK", polls=1000)
        spawner.cells[slot.index] = cell
        return cell

    raised = []

    def sleep(seconds: float) -> None:
        if clock.now >= 2 and not raised:
            raised.append(True)
            raise KeyboardInterrupt
        clock.sleep(seconds)

    outcome = launch_cells(
        night=tmp_path, arms=("baseline",), n=1, k=1, max_seconds=3600, cell_seconds=10, spawn=spawn,
        drift=lambda: None, clock=clock, sleep=sleep, poll_interval=1.0, grace=0.3,
    )
    assert outcome.status is Status.INTERRUPTED
    assert spawner.cells[0].signals == ["TERM", "KILL"]


def test_the_ledger_keeps_every_sitting_and_refuses_another_record(tmp_path: Path) -> None:
    identity = {"record": "records/a.json", "record_sha256": "1" * 64}
    clock = Clock()
    capped = _launch(tmp_path, Spawner(tmp_path, clock, polls=70), clock, k=1, max_seconds=160)
    write_ledger(tmp_path, identity=identity, sitting={"started": "s1", "k": 1}, outcome=capped)
    clock2 = Clock()
    done = _launch(tmp_path, Spawner(tmp_path, clock2), clock2, k=1)
    check_night(tmp_path, identity)
    write_ledger(tmp_path, identity=identity, sitting={"started": "s2", "k": 1}, outcome=done)
    ledger = json.loads((tmp_path / LEDGER_NAME).read_text())
    assert [s["status"] for s in ledger["sittings"]] == ["capped", "complete"]
    assert ledger["status"] == "complete" and [s["slot"] for s in ledger["slots"]] == [0, 1, 2, 3]
    with pytest.raises(UsageError, match="belongs to another record"):
        check_night(tmp_path, {**identity, "record_sha256": "2" * 64})
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest -q tests/test_launch.py` → collection error `ModuleNotFoundError: No module named 'satyrn_evals.launch'`.

- [ ] **Step 3: Implement.** `src/satyrn_evals/launch.py`:

```python
"""The launcher's cell loop: a record's cells, k at a time, arms alternating, one ledger per night.

``satyrn-evals launch RECORD`` is the only path to a model (spec, "Process").
The gates are the CLI's; this module is what happens after them:

- **Slots.** A record asks n cells per arm. Slot i runs arm
  ``arms[i % len(arms)]``: strict alternation, so a night stopped at any point
  leaves the arms at most one cell apart and every pair of concurrent cells at
  k = 2 is one of each (Ruling 4).
- **k at a time.** A slot starts when fewer than k run, no stop is pending,
  the drift probe is silent, and the cell's whole deadline still fits the
  record's wall clock. Otherwise nothing new starts and the running cells
  finish.
- **Each cell is its own process** (``launch_cell``), writing
  ``slots/NN.json`` when its attempt returns a record. A slot with that file
  is finished and never runs again (resume).
- **Stops.** An infrastructure outcome (``INFRASTRUCTURE_CODES``; a deadline
  outside the command phase; a cell process that exits without a record) or
  a drift stops the loop and is recorded; a model outcome never does. A
  finished infrastructure slot is replaced on the next launch: its record
  moves to ``slots/NN.replaced-M.json`` and the ledger lists it (spec,
  "Denominators": only an established infrastructure failure replaces a cell).
- **Signals.** SIGTERM and SIGHUP raise ``SignalAbort`` (``run._abort_on_signals``)
  and SIGINT raises ``KeyboardInterrupt``: every running cell is sent SIGTERM,
  given ``grace`` seconds to tear its model down, then killed; the outcome says
  ``interrupted`` and the caller writes the ledger and exits (an interrupted
  slot has no record and runs again on the next launch).

Nothing here spawns: the caller passes ``spawn`` and ``drift``. The default
tier drives the loop with fakes; ``launch_cell.popen_cell`` is the real spawn.
"""

import json
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.errors import UsageError
from satyrn_evals.run import _abort_on_signals

LEDGER_NAME = "launch.json"
SLOTS_DIR = "slots"
#: Outcomes that measured nothing about the model: they stop the night (Ruling 5).
INFRASTRUCTURE_CODES = frozenset({
    AttemptCode.WORKSPACE_FAILED, AttemptCode.CLEANUP_FAILED, AttemptCode.GRADE_FAILED,
    AttemptCode.TRANSCRIPT_MISSING, AttemptCode.TRANSCRIPT_EMPTY, AttemptCode.MODEL_ERROR,
    AttemptCode.PATCH_INVALID,
})
_SLOT_FILE = re.compile(r"^(\d{2})\.json$")


class Status(StrEnum):
    COMPLETE = "complete"
    CAPPED = "capped"
    INFRASTRUCTURE = "infrastructure"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class Slot:
    index: int
    arm: str

    @property
    def name(self) -> str:
        return f"{self.index:02d}"


class CellProcess(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...


type Spawn = Callable[[Slot], CellProcess]
type Drift = Callable[[], str | None]


@dataclass(slots=True)
class LaunchOutcome:
    status: Status
    reason: str | None
    finished: list[dict] = field(default_factory=list)
    replaced: list[dict] = field(default_factory=list)


def plan_slots(arms: Sequence[str], n: int) -> list[Slot]:
    """n slots per arm, alternating in the record's order."""
    return [Slot(index, arms[index % len(arms)]) for index in range(n * len(arms))]


def slot_path(night: Path, slot: Slot) -> Path:
    return night / SLOTS_DIR / f"{slot.name}.json"


def infrastructure_reason(result: dict) -> str | None:
    """Why a finished slot measured nothing, or ``None`` for a model outcome."""
    code = AttemptCode(result["code"])
    where = f"slot {result['slot']:02d} ({result['arm']})"
    if code in INFRASTRUCTURE_CODES:
        return f"{where}: {code}: {result['message']}"
    if code is AttemptCode.DEADLINE_EXCEEDED and result.get("deadline_phase") != "command":
        return f"{where}: {code} in {result.get('deadline_phase')}: {result['message']}"
    return None


def read_slots(night: Path) -> dict[int, dict]:
    """Every finished slot's result, by index (replaced results are not finished)."""
    directory = night / SLOTS_DIR
    if not directory.is_dir():
        return {}
    found: dict[int, dict] = {}
    for path in sorted(directory.iterdir()):
        if match := _SLOT_FILE.match(path.name):
            found[int(match.group(1))] = json.loads(path.read_text(encoding="utf-8"))
    return found


def _replace_infrastructure_slots(night: Path, finished: dict[int, dict]) -> list[dict]:
    """Move each finished infrastructure slot aside so the slot runs again; return what moved."""
    replaced: list[dict] = []
    for index, result in sorted(finished.items()):
        if (reason := infrastructure_reason(result)) is None:
            continue
        source = night / SLOTS_DIR / f"{index:02d}.json"
        count = len(list(source.parent.glob(f"{index:02d}.replaced-*.json")))
        source.rename(source.with_name(f"{index:02d}.replaced-{count + 1}.json"))
        replaced.append({**result, "replaced_because": reason})
        del finished[index]
    return replaced


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def write_ledger(night: Path, *, identity: dict, sitting: dict, outcome: LaunchOutcome) -> None:
    """Append this sitting to ``launch.json`` and restate the slots every sitting has finished."""
    path = night / LEDGER_NAME
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {**identity, "sittings": [], "replaced": []}
    ledger["sittings"].append({**sitting, "ended": _now(), "status": outcome.status, "reason": outcome.reason})
    ledger["replaced"].extend(outcome.replaced)
    ledger["status"], ledger["reason"] = outcome.status, outcome.reason
    finished = read_slots(night)
    ledger["slots"] = [finished[index] for index in sorted(finished)]
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def check_night(night: Path, identity: dict) -> None:
    """Refuse a night directory that belongs to a different record (same stem, other bytes)."""
    path = night / LEDGER_NAME
    if not path.is_file():
        return
    ledger = json.loads(path.read_text(encoding="utf-8"))
    for key, value in identity.items():
        if ledger.get(key) != value:
            raise UsageError(f"{night} belongs to another record: its {key} is {ledger.get(key)!r}, not {value!r}")


def launch_cells(
    *,
    night: Path,
    arms: Sequence[str],
    n: int,
    k: int,
    max_seconds: float,
    cell_seconds: float,
    spawn: Spawn,
    drift: Drift,
    grace: float = 60.0,
    poll_interval: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> LaunchOutcome:
    """Run every unfinished slot; see the module docstring for the rules."""
    (night / SLOTS_DIR).mkdir(parents=True, exist_ok=True)
    finished = read_slots(night)
    outcome = LaunchOutcome(Status.COMPLETE, None, replaced=_replace_infrastructure_slots(night, finished))
    pending = [slot for slot in plan_slots(arms, n) if slot.index not in finished]
    running: dict[int, tuple[Slot, CellProcess]] = {}
    start = clock()
    capped = False
    try:
        with _abort_on_signals():
            while pending or running:
                for index, (slot, process) in list(running.items()):
                    if (exit_code := process.poll()) is None:
                        continue
                    del running[index]
                    reason = _finish(night, slot, exit_code, outcome)
                    if reason is not None and outcome.status is Status.COMPLETE:
                        outcome.status, outcome.reason = Status.INFRASTRUCTURE, reason
                stopping = outcome.status is not Status.COMPLETE or capped
                while not stopping and pending and len(running) < k:
                    if clock() - start + cell_seconds > max_seconds:
                        capped = stopping = True
                    elif (problem := drift()) is not None:
                        outcome.status, outcome.reason = Status.INFRASTRUCTURE, f"preflight drift: {problem}"
                        stopping = True
                    else:
                        slot = pending.pop(0)
                        running[slot.index] = (slot, spawn(slot))
                if not running and (stopping or not pending):
                    break
                sleep(poll_interval)
    except BaseException as exc:  # SignalAbort, KeyboardInterrupt, or a spawn that raised
        _stop_running(running, grace=grace, clock=clock, sleep=sleep, poll_interval=poll_interval)
        for slot, _ in running.values():
            if slot_path(night, slot).is_file():
                outcome.finished.append(json.loads(slot_path(night, slot).read_text(encoding="utf-8")))
        outcome.status, outcome.reason = Status.INTERRUPTED, f"{type(exc).__name__}: {exc}"
        return outcome
    if outcome.status is Status.COMPLETE and pending:
        outcome.status = Status.CAPPED
        outcome.reason = (
            f"the record's wall clock leaves no room for another {cell_seconds:g} s cell; "
            f"{len(pending)} slot(s) wait for the next launch of the same record"
        )
    return outcome


def _finish(night: Path, slot: Slot, exit_code: int, outcome: LaunchOutcome) -> str | None:
    """Collect one exited cell; the infrastructure reason it stops the night for, if any."""
    path = slot_path(night, slot)
    if not path.is_file():
        return f"slot {slot.name} ({slot.arm}): the cell process exited {exit_code} without an attempt record"
    result = json.loads(path.read_text(encoding="utf-8"))
    outcome.finished.append(result)
    return infrastructure_reason(result)


def _stop_running(
    running: dict[int, tuple[Slot, CellProcess]],
    *,
    grace: float,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
    poll_interval: float,
) -> None:
    """SIGTERM every running cell, wait up to ``grace`` for its teardown, then kill what is left."""
    for _, process in running.values():
        process.terminate()
    stop = clock() + grace
    while any(process.poll() is None for _, process in running.values()) and clock() < stop:
        sleep(min(poll_interval, 0.1))
    for _, process in running.values():
        if process.poll() is None:
            process.kill()
```

- [ ] **Step 4: Pass.** `uv run pytest -q tests/test_launch.py` → 22 passed.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/launch.py tests/test_launch.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2c: the launcher's cell loop runs slots k at a time with arms alternating, stops on infrastructure or a signal, and resumes without re-running a finished cell"
```

---

### Task 3: `launch RECORD` — gates, cell processes, the isolated rows, the roadmap

**Files:**
- Create: `src/satyrn_evals/launch_cell.py`, `src/satyrn_evals/launch_record.py`, `tests/test_launch_record.py`, `tests/integration/test_launch_record.py`
- Modify: `src/satyrn_evals/cli.py` (imports; `launch RECORD` dispatch and usage line; `_launch_preflight` takes the first `--arm` and any arm of the record; the `launch` parser), `tests/integration/fake_pi_build.py` (mode `unreachable`), `ROADMAP.md` (rows 2c and 2d)

**Interfaces:**
- Consumes (T1): `record_arms`, `gate(record_frozen=)`, `check_invocation`, `DECIDING_PURPOSES`, `RunRecord.k/.rung`; (T2): everything `launch` produces; (2b): `cell.Isolation`, `CELL_PATH_PREFIX_ENV`, `cell_preflight.preflight_cell`, `CellPreflight`, `arms.load_arm`, `build_argv`; (2a): `attempt.attempt`, `rescore._load_cell`, `compute_pathology`, `compute_evidence`, `pathology_context`, `summary.compute_summary`, `write_summary`; integration helpers `integration.test_isolated_arms._cell_pi`, `integration.test_attempt._engine_repo`, `integration.cell_support.cell_process_alive`, fixture `cell_scratch`.
- Produces: `launch_cell.COMMAND_BACKSTOP = 1800.0`, `ATTEMPT_DEADLINE = 2100.0`, `slot_result(*, slot, arm, record) -> dict`, `write_atomically(path, body)`, `run_cell(spec) -> int`, `main(argv)` (`python -m satyrn_evals.launch_cell SPEC`; 128 + signal on a stop), `PopenCell`, `popen_cell(spec_path, log_path) -> PopenCell`; `launch_record.DEFAULT_RUNS_ROOT = ~/satyrn-runs`, `SETTINGS_SCRIPT`, `EXIT_CODES`, `git_frozen(path) -> bool`, `git_committed(path) -> bool`, `git_head() -> str`, `settings_provenance(arm_path, cell) -> (int, str)`, `@dataclass LaunchFacts(frozen, committed, head, preflight, settings, spawn_cell)`, `write_arm_summaries(night, arms, n, task_dir) -> dict`, `launch_record(record_path, arm_paths, *, tasks_root, runs_root=DEFAULT_RUNS_ROOT, timeout=COMMAND_BACKSTOP, attempt_timeout=ATTEMPT_DEADLINE, hunt=True, settings=True, grace=60.0, poll_interval=1.0, facts=None, out=None, err=None) -> int` (0 complete, 1 preflight or settings problem, 2 refusal via RunRecordError/UsageError, 3 infrastructure or interrupted, 4 capped). CLI: `satyrn-evals launch RECORD --arm ARM.json [--arm ARM2.json] [--tasks-root R] [--runs-root D] [--no-hunt] [--no-settings] [--timeout S] [--attempt-timeout S]`; the committed result `<record>.result.json` holds `record`, `record_sha256`, `status`, `reason`, `night`, `task`, `rung`, `k`, `n`, `purpose`, `arms.<arm>.{finished, n, code_counts, passes, summary, contamination?}`, `cells[{slot, arm, attempt_dir, code, verdict}]`, `replaced`, `sittings`. Fake `pi` mode `unreachable` → the harness records `MODEL_ERROR`.

- [ ] **Step 1: Failing tests.** `tests/test_launch_record.py`:

```python
"""``launch RECORD``'s gates and wiring, with every git, sudo and spawn fact faked: nothing spawns."""

import json
from pathlib import Path

import pytest

from satyrn_evals.cell import CELL_PATH_PREFIX_ENV
from satyrn_evals.cell_preflight import CellPreflight
from satyrn_evals.cli import main
from satyrn_evals.errors import SatyrnError
from satyrn_evals.launch import SLOTS_DIR, Slot, slot_path
from satyrn_evals.launch_record import LaunchFacts, launch_record
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import new_record, write_new_record

REPO = Path(__file__).resolve().parent.parent
ARM = REPO / "arms" / "baseline-ornith15-9b.json"
TASK = "agentclinic-repair-depth-3"
SETTINGS = '{"arm_sha256": "a"}'


def _record(tmp_path: Path, **over: object) -> Path:
    body = new_record(
        task=TASK, tasks_root=DEFAULT_TASKS_ROOT, arm="baseline", model="omlx/Ornith-1.5-9B-MLX-8bit", n=2, k=1,
        rung="R1", purpose="admission", isolation="isolated", mode="attended", max_minutes=60,
        token_budget=32000, turn_budget=48, previous_result=None, authority="test", decision_rule=None,
    )
    path = tmp_path / "records" / "depth-3.json"
    write_new_record(path, {**body, **over})
    return path


class Spawned(Exception):
    """Raised by the fake spawn: the gates passed and a cell would have started."""


def _facts(**over: object) -> LaunchFacts:
    def spawn(spec: Path, log: Path) -> object:
        raise Spawned(spec.read_text())

    base = dict(
        frozen=lambda path: True, committed=lambda path: True, head=lambda: "f" * 40,
        preflight=lambda **kw: CellPreflight([], {"pi_version": "0.85.1"}), settings=lambda path, cell: (0, SETTINGS),
        spawn_cell=spawn,
    )
    return LaunchFacts(**{**base, **over})  # type: ignore[arg-type]


def _launch(tmp_path: Path, record: Path, facts: LaunchFacts, **over: object) -> int:
    kwargs: dict[str, object] = dict(tasks_root=DEFAULT_TASKS_ROOT, runs_root=tmp_path / "runs", facts=facts, poll_interval=0.0, grace=0.0)
    return launch_record(record, [ARM], **{**kwargs, **over})  # type: ignore[arg-type]


def test_a_clean_admission_record_reaches_its_first_cell_with_the_records_settings(tmp_path: Path) -> None:
    record = _record(tmp_path)
    assert _launch(tmp_path, record, _facts()) == 3  # the fake spawn raised: interrupted
    spec = json.loads((tmp_path / "runs" / "depth-3" / SLOTS_DIR / "00.spec.json").read_text())
    assert spec["command"] == ["satyrn-evals-attempt-pi", "--model", "omlx/Ornith-1.5-9B-MLX-8bit", "--tools", "read,bash,edit,write"]
    assert (spec["rung"], spec["token_budget"], spec["turn_budget"], spec["isolation"]) == ("R1", 32000, 48, "isolated")
    assert (spec["timeout"], spec["attempt_timeout"]) == (1800.0, 2100.0)
    assert spec["output"] == str(tmp_path / "runs" / "depth-3" / "baseline")
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "interrupted" and result["sittings"][0]["evals_head"] == "f" * 40
    assert result["arms"]["baseline"]["finished"] == 0 and result["cells"] == []


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"settings": False}, "--no-settings"),
        ({"hunt": False}, "--no-hunt"),
        ({"timeout": 900.0}, "--timeout 900"),
        ({"attempt_timeout": 60.0}, "--attempt-timeout 60"),
    ],
)
def test_a_deciding_record_refuses_every_test_seam(tmp_path: Path, over: dict[str, object], message: str) -> None:
    record = _record(tmp_path)
    with pytest.raises(SatyrnError, match=message):
        _launch(tmp_path, record, _facts(), **over)
    assert not (tmp_path / "runs").exists()


def test_a_deciding_record_refuses_the_cell_path_seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, "/fake/bin")
    record = _record(tmp_path)
    assert main(["launch", str(record), "--arm", str(ARM), "--runs-root", str(tmp_path / "runs")]) == 2
    assert not (tmp_path / "runs").exists()


def test_a_development_record_may_use_the_seams(tmp_path: Path) -> None:
    record = _record(tmp_path, purpose="development", decision_rule="none")
    assert _launch(tmp_path, record, _facts(), settings=False, hunt=False, timeout=60.0, attempt_timeout=90.0) == 3


def _refused(tmp_path: Path, record: Path, facts: LaunchFacts) -> str:
    with pytest.raises(SatyrnError) as refusal:
        _launch(tmp_path, record, facts)
    assert refusal.value.exit_code == 2
    return str(refusal.value)


def test_an_unfrozen_record_is_refused_before_any_cell(tmp_path: Path) -> None:
    assert "not frozen" in _refused(tmp_path, _record(tmp_path), _facts(frozen=lambda path: False))
    assert not (tmp_path / "runs").exists()


def test_a_previous_result_that_is_not_committed_is_refused(tmp_path: Path) -> None:
    record = _record(tmp_path, previous_result="records/earlier.result.json")
    assert "is not committed" in _refused(tmp_path, record, _facts(committed=lambda path: False))
    assert _launch(tmp_path, record, _facts()) == 3  # committed: the gates pass


def test_an_arm_file_the_record_does_not_run_is_refused(tmp_path: Path) -> None:
    record = _record(tmp_path, arm="baseline+engine")
    assert "the --arm files are baseline" in _refused(tmp_path, record, _facts())


@pytest.mark.parametrize(
    "facts",
    [
        _facts(preflight=lambda **kw: CellPreflight(["the cell can find /x/known-good.patch"], {})),
        _facts(settings=lambda path, cell: (1, "preflight_settings FAILED: temperature")),
    ],
    ids=["cell-preflight", "settings"],
)
def test_a_preflight_or_settings_problem_exits_1_and_runs_nothing(
    tmp_path: Path, facts: LaunchFacts, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _launch(tmp_path, _record(tmp_path), facts) == 1
    assert "launch FAILED:" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


def test_the_preflight_protects_the_runs_root_and_hunts_by_default(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def preflight(**kwargs: object) -> CellPreflight:
        seen.update(kwargs)
        return CellPreflight(["stop here"], {})

    assert _launch(tmp_path, _record(tmp_path), _facts(preflight=preflight)) == 1
    assert seen["hunt_root"] == "/" and seen["pinned_pi"] == "0.85.1"
    assert tmp_path / "runs" in seen["protected"]  # type: ignore[operator]


class Finishing:
    """A cell that has already written a NO_PATCH slot record."""

    def __init__(self, spec: Path) -> None:
        body = json.loads(spec.read_text())
        slot_path(spec.parent.parent, Slot(body["slot"], body["arm"])).write_text(json.dumps({
            "slot": body["slot"], "arm": body["arm"], "attempt_dir": "x", "code": "NO_PATCH", "verdict": None,
            "message": "attempt refused: NO_PATCH", "command_exit": 0, "deadline_phase": None,
        }))

    def poll(self) -> int:
        return 0

    def terminate(self) -> None: ...
    def kill(self) -> None: ...


def test_a_settings_change_between_cells_stops_the_night_as_drift(tmp_path: Path) -> None:
    answers = iter([(0, SETTINGS), (0, SETTINGS), (0, '{"arm_sha256": "b"}')])
    facts = _facts(settings=lambda path, cell: next(answers), spawn_cell=lambda spec, log: Finishing(spec))
    record = _record(tmp_path)
    assert _launch(tmp_path, record, facts) == 3
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "infrastructure"
    assert result["reason"] == "preflight drift: the settings provenance for baseline changed"
    assert [c["slot"] for c in result["cells"]] == [0]


def test_a_night_directory_of_another_record_is_refused(tmp_path: Path) -> None:
    first = _record(tmp_path)
    assert _launch(tmp_path, first, _facts()) == 3
    other = tmp_path / "elsewhere" / "depth-3.json"
    other.parent.mkdir()
    other.write_text(first.read_text().replace('"k": 1', '"k": 2'))
    assert "belongs to another record" in _refused(tmp_path, other, _facts())
```

Apply to `tests/integration/fake_pi_build.py`:

```diff
diff --git a/tests/integration/fake_pi_build.py b/tests/integration/fake_pi_build.py
index eca23f0..c8d29c0 100644
--- a/tests/integration/fake_pi_build.py
+++ b/tests/integration/fake_pi_build.py
@@ -19,6 +19,9 @@ stdout:
   only a tighter harness budget can trip it, never `deliver`'s live
   enforcement or the engine's own `attempt` -- record its pid in
   ``SATYRN_FAKE_PI_PIDFILE``, then sleep so only a tripwire can end it.
+- ``unreachable``: change nothing and end the one turn the way Pi does when
+  the model server cannot be reached (``stopReason: error`` with no status),
+  which the harness records as ``MODEL_ERROR`` (Phase 2c's infrastructure stop).
 """

 import json
@@ -62,6 +65,11 @@ def main() -> int:
         turn(20_000)
         time.sleep(120)
         return 0
+    if mode == "unreachable":
+        emit({"type": "turn_start"})
+        emit({"type": "turn_end", "message": {"role": "assistant", "content": [], "stopReason": "error", "errorMessage": "Connection error."}})
+        emit({"type": "agent_end"})
+        return 0
     if mode in ("commit", "write"):
         emit({"type": "turn_start"})
         for index, (path, text) in enumerate(GOOD.items()):
```

`tests/integration/test_launch_record.py`:

```python
"""Roadmap row 2c: records run through the launcher under isolation, against a fake ``pi``.

Real launcher, real cell processes, real sudo, git and harness; ``pi`` is
`fake_pi_build.py` run as the cell user. Records are written with
``record new`` and committed in a scratch repository, so the frozen gate is
the real one. Every record here is ``purpose: development`` (the only purpose
the test PATH seam and ``--no-settings`` are allowed for). No model runs.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from integration.cell_support import cell_process_alive
from integration.test_attempt import (
    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
)
from integration.test_isolated_arms import _cell_pi  # type: ignore[missing-import]
from satyrn_evals.cell import CELLS_ROOT
from satyrn_evals.cell_engine import export_engine
from satyrn_evals.cli import main
from satyrn_evals.launch import LEDGER_NAME
from satyrn_evals.summary import SUMMARY_NAME

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
ENTRY = "import sys; from satyrn_evals.cli import main; sys.exit(main())"


def _git(repo: Path, *argv: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *argv], cwd=repo, check=True, capture_output=True)


def _frozen_record(tmp_path: Path, name: str, *, arm: str, n: int, k: int, max_minutes: int = 60) -> Path:
    repo = tmp_path / "records"
    if not (repo / ".git").exists():
        repo.mkdir()
        _git(repo, "init", "-q")
    path = repo / f"{name}.json"
    assert main([
        "record", "new", "--output", str(path), "--task", "calc-build", "--tasks-root", str(TASKS), "--arm", arm,
        "--rung", "contract", "--n", str(n), "--k", str(k), "--purpose", "development",
        "--max-minutes", str(max_minutes), "--model", "omlx/fixture",
    ]) == 0
    _git(repo, "add", path.name)
    _git(repo, "commit", "-qm", name)
    return path


def _arm_file(tmp_path: Path, name: str, argv: list[str]) -> Path:
    body = {
        "arm": name, "argv": argv, "tools": ["read", "bash", "edit", "write"], "model": "omlx/fixture",
        "server_model": "fixture",
        "pins": {"pi": "0.85.1", "engine_commit": None, "digests": {}},
    }
    if name == "engine":
        body["pins"] = {
            "pi": "0.85.1", "engine_commit": "0" * 40,
            "digests": {source: "0" * 64 for source in ("engine.ts", "mutator.ts", "runner.ts", "orchestrator.ts")},
        }
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(body))
    return path


def _baseline_arm(tmp_path: Path) -> Path:
    return _arm_file(tmp_path, "baseline", [sys.executable, "-m", "satyrn_evals.attempt_pi"])


def _launch(record: Path, arms: list[Path], runs: Path, *extra: str) -> int:
    argv = ["launch", str(record), "--tasks-root", str(TASKS), "--runs-root", str(runs), "--no-hunt", "--no-settings"]
    for arm in arms:
        argv += ["--arm", str(arm)]
    return main([*argv, "--timeout", "120", "--attempt-timeout", "300", *extra])


def _attempt_dirs() -> set[str]:
    return {p.name for p in CELLS_ROOT.iterdir() if p.name.startswith("satyrn-attempt-")}


def _result(record: Path) -> dict:
    return json.loads(record.with_suffix(".result.json").read_text())


def test_a_fake_completes_a_k2_interleaved_record_under_isolation_through_the_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "write")  # the Engine arm's deliver commits; Baseline's harvest takes the files
    export = export_engine(_engine_repo(), "HEAD", root=cell_scratch)
    engine = _arm_file(
        tmp_path, "engine",
        [sys.executable, "-m", "satyrn_evals.attempt_engine", "--engine-repo", os.fspath(export), "--uv-bin", "uv"],
    )
    record = _frozen_record(tmp_path, "interleaved", arm="baseline+engine", n=2, k=2)
    before = _attempt_dirs()
    assert _launch(record, [_baseline_arm(tmp_path), engine], tmp_path / "runs") == 0
    result = _result(record)
    assert result["status"] == "complete" and result["k"] == 2
    assert [(c["slot"], c["arm"]) for c in result["cells"]] == [(0, "baseline"), (1, "engine"), (2, "baseline"), (3, "engine")]
    for arm in ("baseline", "engine"):
        assert result["arms"][arm]["passes"] == 2 and result["arms"][arm]["code_counts"] == {"OK": 2}
        summary = json.loads((tmp_path / "runs" / "interleaved" / arm / SUMMARY_NAME).read_text())
        assert summary["n"] == 2 and summary["verdict_counts"]["pass"] == 2
    assert _attempt_dirs() <= before


def test_a_night_the_wall_clock_stops_resumes_without_rerunning_a_finished_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "commit")
    record = _frozen_record(tmp_path, "resume", arm="baseline", n=2, k=1, max_minutes=1)
    arms, runs = [_baseline_arm(tmp_path)], tmp_path / "runs"
    # A 59 s deadline leaves the one-minute record room for exactly one cell.
    assert _launch(record, arms, runs, "--attempt-timeout", "59") == 4
    first = _result(record)
    assert first["status"] == "capped" and [c["slot"] for c in first["cells"]] == [0]
    assert _launch(record, arms, runs, "--attempt-timeout", "59") == 0
    second = _result(record)
    assert second["status"] == "complete" and [c["slot"] for c in second["cells"]] == [0, 1]
    assert second["cells"][0]["attempt_dir"] == first["cells"][0]["attempt_dir"]
    assert [s["status"] for s in second["sittings"]] == ["capped", "complete"]
    assert json.loads((runs / "resume" / "baseline" / SUMMARY_NAME).read_text())["n"] == 2


def test_an_unreachable_server_stops_the_night_and_the_next_launch_replaces_that_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "unreachable")
    record = _frozen_record(tmp_path, "infra", arm="baseline", n=2, k=1)
    arms, runs = [_baseline_arm(tmp_path)], tmp_path / "runs"
    assert _launch(record, arms, runs) == 3
    stopped = _result(record)
    assert stopped["status"] == "infrastructure"
    assert stopped["reason"].startswith("slot 00 (baseline): MODEL_ERROR") and "Connection error." in stopped["reason"]
    assert [c["slot"] for c in stopped["cells"]] == [0]  # slot 1 never started
    (cell_scratch / "bin" / "pi").write_text((cell_scratch / "bin" / "pi").read_text().replace("unreachable", "commit"))
    assert _launch(record, arms, runs) == 0
    resumed = _result(record)
    assert resumed["status"] == "complete" and [c["code"] for c in resumed["cells"]] == ["OK", "OK"]
    assert [r["code"] for r in resumed["replaced"]] == ["MODEL_ERROR"]
    assert resumed["replaced"][0]["attempt_dir"] != resumed["cells"][0]["attempt_dir"]


def test_the_launcher_refuses_a_record_that_is_not_committed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "commit")
    record = _frozen_record(tmp_path, "edited", arm="baseline", n=1, k=1)
    record.write_text(record.read_text().replace('"n": 1', '"n": 2'))
    assert _launch(record, [_baseline_arm(tmp_path)], tmp_path / "runs") == 2
    assert not (tmp_path / "runs" / "edited").exists()


def test_sigterm_stops_the_launcher_and_its_running_cell_leaves_no_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    pidfile = _cell_pi(cell_scratch, monkeypatch, "trickle")
    record = _frozen_record(tmp_path, "signal", arm="baseline", n=2, k=1)
    runs = tmp_path / "runs"
    before = _attempt_dirs()
    launcher = subprocess.Popen([
        sys.executable, "-c", ENTRY, "launch", str(record), "--tasks-root", str(TASKS), "--runs-root", str(runs),
        "--no-hunt", "--no-settings", "--arm", str(_baseline_arm(tmp_path)), "--timeout", "120", "--attempt-timeout", "300",
    ])
    try:
        stop = time.monotonic() + 60
        while not pidfile.exists() and time.monotonic() < stop:
            time.sleep(0.2)
        assert pidfile.exists(), "the fake pi never started"
        launcher.send_signal(signal.SIGTERM)
        assert launcher.wait(timeout=90) == 3
    finally:
        if launcher.poll() is None:
            launcher.kill()
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while cell_process_alive(pid) and time.monotonic() < stop:
        time.sleep(0.1)
    assert not cell_process_alive(pid), f"fake pi {pid} outlived the launcher"
    ledger = json.loads((runs / "signal" / LEDGER_NAME).read_text())
    assert ledger["status"] == "interrupted" and "SignalAbort: SIGTERM" in ledger["reason"]
    assert ledger["slots"] == []
    assert _attempt_dirs() <= before
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest -q tests/test_launch_record.py` → collection error `ModuleNotFoundError: No module named 'satyrn_evals.launch_record'`. `uv run pytest -m integration -q tests/integration/test_launch_record.py` → every row fails with `SystemExit: 2` (argparse does not know `launch RECORD` yet); on a machine without the cell user they skip.

- [ ] **Step 3: Implement.** `src/satyrn_evals/launch_cell.py`:

```python
"""One launcher cell in its own process: the attempt, then its slot record.

``launch_record`` writes ``slots/NN.spec.json`` and starts
``python -m satyrn_evals.launch_cell SPEC`` in its own session. The child runs
``attempt`` with the record's budget, rung and profile, and only when
``attempt`` returns a record writes ``slots/NN.json`` (atomically), the file
that makes the slot finished. SIGTERM and SIGHUP raise ``SignalAbort`` inside
the attempt, so the workspace's own teardown stops the model (the cell-side
kill included under isolation) before the process exits without a slot record.
"""

import contextlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptRecord
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell import Isolation
from satyrn_evals.errors import SatyrnError
from satyrn_evals.run import SignalAbort, _abort_on_signals

#: The spec's backstop on this machine ("Budget, both arms"): per attempt command, and the attempt deadline.
COMMAND_BACKSTOP = 1800.0
ATTEMPT_DEADLINE = 2100.0


def slot_result(*, slot: int, arm: str, record: AttemptRecord) -> dict[str, object]:
    """What the loop reads back about a finished slot."""
    return {
        "slot": slot,
        "arm": arm,
        "attempt_dir": record.attempt_dir,
        "code": record.code.value,
        "verdict": None if record.verdict is None else record.verdict.value,
        "message": record.message,
        "command_exit": record.command_exit,
        "deadline_phase": None if record.deadline is None else record.deadline.phase.value,
    }


def write_atomically(path: Path, body: dict[str, object]) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)


def run_cell(spec: dict) -> int:
    with _abort_on_signals():
        record = attempt(
            task=spec["task"],
            tasks_root=Path(spec["tasks_root"]),
            output=Path(spec["output"]),
            command=list(spec["command"]),
            timeout=spec["timeout"],
            attempt_timeout=spec["attempt_timeout"],
            rung=spec["rung"],
            budget=AttemptBudget(output_tokens=spec["token_budget"], turns=spec["turn_budget"]),
            isolation=Isolation(spec["isolation"]),
        )
    write_atomically(Path(spec["result"]), slot_result(slot=spec["slot"], arm=spec["arm"], record=record))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        return run_cell(json.loads(Path(args[0]).read_text(encoding="utf-8")))
    except SignalAbort as stop:
        print(f"launch_cell: stopped by {stop}", file=sys.stderr)
        return 128 + stop.signum
    except KeyboardInterrupt:
        print("launch_cell: stopped by SIGINT", file=sys.stderr)
        return 128 + signal.SIGINT
    except SatyrnError as error:
        print(f"launch_cell: {error}", file=sys.stderr)
        return error.exit_code


class PopenCell:
    """A running cell process: its own session, SIGTERM for teardown, SIGKILL to its group as a last resort."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process

    def poll(self) -> int | None:
        return self.process.poll()

    def terminate(self) -> None:
        with contextlib.suppress(ProcessLookupError):
            self.process.send_signal(signal.SIGTERM)

    def kill(self) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait()


def popen_cell(spec_path: Path, log_path: Path) -> PopenCell:
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "satyrn_evals.launch_cell", os.fspath(spec_path)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    return PopenCell(process)


if __name__ == "__main__":
    sys.exit(main())
```

`src/satyrn_evals/launch_record.py`:

```python
"""``satyrn-evals launch RECORD --arm ARM.json …``: the gates, then the record's cells.

The spec's launcher gates ("Process"), in order, before any cell:

1. the record loads, and every ``--arm`` file is one of the record's arms on
   the record's model, with a command ``check_invocation`` accepts (task,
   task tree, arm, model) and a rung the task declares;
2. a deciding record (admission, route-proof, campaign) runs with the spec's
   backstop (1,800 s command, 2,100 s deadline), the settings check, the full
   hunt and no test PATH seam (Ruling 7);
3. ``gate``: the record is frozen (tracked, unchanged against ``HEAD``), the
   previous result is committed, n and wall clock are under the cadence cap,
   and a deciding purpose is isolated;
4. under isolation, the cell preflight (``cell_preflight.preflight_cell``) is clean;
5. ``scripts/preflight_settings.py`` exits 0 for every arm (``--cell`` under
   isolation); its provenance block is kept for the drift check.

Between cells the drift probe re-reads the record and arm file bytes, the
task tree digest and the settings provenance; any change stops the night.

Artifacts: the night directory ``RUNS_ROOT/<record stem>/`` (under the
maintainer's home by default, which the cell cannot read) holds ``launch.json``
(the ledger), ``slots/`` and one ``run``-shaped directory per arm whose
``summary.json`` is written once that arm's n cells are finished
(``satyrn-evals summarize`` rebuilds it). The committed result is
``<record>.result.json`` beside the record (Ruling 6).

Exit codes: 0 complete; 1 preflight or settings problem (nothing ran); 2 a
refused record or invocation; 3 an infrastructure stop or a signal; 4 the
wall clock stopped the night early (launch the same record again to resume).
"""

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from satyrn_evals.arms import Arm, build_argv, load_arm
from satyrn_evals.attempt import resolve_contract
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, Isolation
from satyrn_evals.cell_preflight import CellPreflight, preflight_cell
from satyrn_evals.launch import (
    SLOTS_DIR,
    CellProcess,
    LaunchOutcome,
    Slot,
    Status,
    check_night,
    launch_cells,
    read_slots,
    slot_path,
    write_ledger,
)
from satyrn_evals.launch_cell import (
    ATTEMPT_DEADLINE,
    COMMAND_BACKSTOP,
    popen_cell,
    write_atomically,
)
from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.rescore import (
    _load_cell,
    compute_evidence,
    compute_pathology,
    pathology_context,
)
from satyrn_evals.run_record import (
    DECIDING_PURPOSES,
    RunRecord,
    RunRecordError,
    check_invocation,
    gate,
    load_run_record,
    record_arms,
)
from satyrn_evals.summary import SUMMARY_NAME, compute_summary, write_summary
from satyrn_evals.task_tree import tree_digest

DEFAULT_RUNS_ROOT = Path.home() / "satyrn-runs"
SETTINGS_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "preflight_settings.py"
EXIT_CODES = {Status.COMPLETE: 0, Status.INFRASTRUCTURE: 3, Status.INTERRUPTED: 3, Status.CAPPED: 4}


def _git(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=False)


def git_frozen(path: Path) -> bool:
    """Tracked, and no staged or unstaged change against ``HEAD``."""
    where, name = path.resolve().parent, path.name
    return (
        _git(["ls-files", "--error-unmatch", "--", name], where).returncode == 0
        and _git(["diff", "--quiet", "HEAD", "--", name], where).returncode == 0
    )


def git_committed(path: str) -> bool:
    return _git(["ls-files", "--error-unmatch", "--", path], Path.cwd()).returncode == 0


def git_head() -> str:
    return _git(["rev-parse", "HEAD"], Path.cwd()).stdout.strip()


def settings_provenance(arm_path: Path, cell: bool) -> tuple[int, str]:
    """``preflight_settings.py`` for one arm: its exit code and its provenance JSON."""
    ran = subprocess.run(
        [sys.executable, os.fspath(SETTINGS_SCRIPT), os.fspath(arm_path), *(["--cell"] if cell else [])],
        capture_output=True, text=True, check=False,
    )
    return ran.returncode, ran.stdout if ran.returncode == 0 else ran.stdout + ran.stderr


@dataclass(frozen=True, slots=True)
class LaunchFacts:
    """Everything that spawns or reads git, replaceable by the default tier."""

    frozen: Callable[[Path], bool] = git_frozen
    committed: Callable[[str], bool] = git_committed
    head: Callable[[], str] = git_head
    preflight: Callable[..., CellPreflight] = preflight_cell
    settings: Callable[[Path, bool], tuple[int, str]] = settings_provenance
    spawn_cell: Callable[[Path, Path], CellProcess] = popen_cell


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _arms(record: RunRecord, arm_paths: Sequence[Path]) -> dict[str, tuple[Path, Arm]]:
    loaded = {}
    for path in arm_paths:
        arm = load_arm(path)
        if arm.arm in loaded:
            raise RunRecordError(f"--arm names {arm.arm} twice")
        loaded[arm.arm] = (path, arm)
    if sorted(loaded) != sorted(record_arms(record)):
        raise RunRecordError(f"the record runs {record.arm}; the --arm files are {'+'.join(loaded) or 'none'}")
    for path, arm in loaded.values():
        if arm.model != record.model:
            raise RunRecordError(f"arm file {path} is on {arm.model}; the record is on {record.model}")
    if len({arm.pins.pi for _, arm in loaded.values()}) != 1:
        raise RunRecordError("the arms pin different pi versions; interleaved arms run one pi")
    return loaded


def write_arm_summaries(night: Path, arms: Sequence[str], n: int, task_dir: Path) -> dict[str, dict]:
    """``summary.json`` for every arm whose n slots are finished; the counts for every arm."""
    manifest = load_manifest(task_dir)
    overlay, visible_texts = pathology_context(task_dir, manifest)
    finished = read_slots(night)
    report: dict[str, dict] = {}
    for arm in arms:
        results = [result for _, result in sorted(finished.items()) if result["arm"] == arm]
        codes: dict[str, int] = {}
        for result in results:
            codes[result["code"]] = codes.get(result["code"], 0) + 1
        entry: dict[str, object] = {
            "finished": len(results), "n": n, "code_counts": codes,
            "passes": sum(1 for result in results if result["verdict"] == "pass"), "summary": None,
        }
        if len(results) == n:
            output = night / arm
            cells = [_load_cell(output / result["attempt_dir"]) for result in results]
            kwargs = dict(task_dir=task_dir, manifest=manifest, overlay=overlay, visible_texts=visible_texts)
            summary = compute_summary(
                cells, oracle_visibility=manifest.oracle_visibility,
                pathology=compute_pathology(output, cells, **kwargs), evidence=compute_evidence(output, cells, **kwargs),
            )
            write_summary(output / SUMMARY_NAME, summary)
            entry["summary"] = os.fspath(output / SUMMARY_NAME)
            entry["contamination"] = summary.contamination
        report[arm] = entry
    return report


def launch_record(
    record_path: Path,
    arm_paths: Sequence[Path],
    *,
    tasks_root: Path,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    timeout: float = COMMAND_BACKSTOP,
    attempt_timeout: float = ATTEMPT_DEADLINE,
    hunt: bool = True,
    settings: bool = True,
    grace: float = 60.0,
    poll_interval: float = 1.0,
    facts: LaunchFacts | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    facts = facts or LaunchFacts()
    out, err = out or sys.stdout, err or sys.stderr
    record = load_run_record(record_path)
    arms = _arms(record, arm_paths)
    task_dir = resolve_task(record.task, tasks_root=tasks_root)
    commands = {name: build_argv(arm) for name, (_, arm) in arms.items()}
    for command in commands.values():
        check_invocation(record, task=record.task, task_dir=task_dir, command=command)
    resolve_contract(load_manifest(task_dir), record.rung)
    if record.purpose in DECIDING_PURPOSES:
        seams = [
            name for name, used in (
                ("--no-settings", not settings), ("--no-hunt", not hunt),
                (f"--timeout {timeout:g}", timeout != COMMAND_BACKSTOP),
                (f"--attempt-timeout {attempt_timeout:g}", attempt_timeout != ATTEMPT_DEADLINE),
                (CELL_PATH_PREFIX_ENV, bool(os.environ.get(CELL_PATH_PREFIX_ENV))),
            ) if used
        ]
        if seams:
            raise RunRecordError(f"a {record.purpose} record runs with none of: {', '.join(seams)}")
    previous = None if record.previous_result is None else facts.committed(record.previous_result)
    gate(record, previous_result_committed=previous, record_frozen=facts.frozen(record_path))

    problems: list[str] = []
    checked: dict[str, object] = {}
    if record.isolation is Isolation.ISOLATED:
        report = facts.preflight(
            pinned_pi=next(iter(arms.values()))[1].pins.pi,
            protected=(Path.cwd(), tasks_root, Path.home(), runs_root),
            tasks_root=tasks_root, hunt_root="/" if hunt else None,
        )
        problems += report.problems
        checked["preflight"] = report.checked
    baseline_settings: dict[str, str] = {}
    if settings:
        for name, (path, _) in arms.items():
            code, text = facts.settings(path, record.isolation is Isolation.ISOLATED)
            if code != 0:
                problems.append(f"preflight_settings for {name} exited {code}: {text.strip()}")
            baseline_settings[name] = text
        checked["settings"] = {name: json.loads(text) for name, text in baseline_settings.items() if text.startswith("{")}
    if problems:
        for problem in problems:
            print(f"launch FAILED: {problem}", file=err)
        return 1

    night = runs_root / record_path.stem
    identity = {"record_sha256": _sha256(record_path)}
    check_night(night, identity)
    pinned = {record_path: identity["record_sha256"], **{path: _sha256(path) for path, _ in arms.values()}}
    tree = record.task_tree_sha256

    def drift() -> str | None:
        for path, digest in pinned.items():
            if _sha256(path) != digest:
                return f"{path} changed since the launch began"
        if tree_digest(task_dir) != tree:
            return f"the {record.task} task tree no longer matches task_tree_sha256"
        for name, (path, _) in arms.items() if settings else ():
            if facts.settings(path, record.isolation is Isolation.ISOLATED)[1] != baseline_settings[name]:
                return f"the settings provenance for {name} changed"
        return None

    def spawn(slot: Slot) -> CellProcess:
        spec = {
            "slot": slot.index, "arm": slot.arm, "task": record.task, "tasks_root": os.fspath(tasks_root),
            "output": os.fspath(night / slot.arm), "command": commands[slot.arm], "timeout": timeout,
            "attempt_timeout": attempt_timeout, "rung": record.rung, "token_budget": record.token_budget,
            "turn_budget": record.turn_budget, "isolation": record.isolation.value,
            "result": os.fspath(slot_path(night, slot)),
        }
        spec_path = night / SLOTS_DIR / f"{slot.name}.spec.json"
        write_atomically(spec_path, spec)
        return facts.spawn_cell(spec_path, night / SLOTS_DIR / f"{slot.name}.log")

    sitting = {
        "record": os.fspath(record_path), "started": datetime.now(UTC).isoformat(timespec="seconds"),
        "k": record.k, "evals_head": facts.head(), **checked,
    }
    outcome: LaunchOutcome = launch_cells(
        night=night, arms=record_arms(record), n=record.n, k=record.k, max_seconds=record.max_minutes * 60,
        cell_seconds=attempt_timeout, spawn=spawn, drift=drift, grace=grace, poll_interval=poll_interval,
    )
    write_ledger(night, identity=identity, sitting=sitting, outcome=outcome)
    ledger = json.loads((night / "launch.json").read_text(encoding="utf-8"))
    result = {
        "record": os.fspath(record_path), **identity, "status": outcome.status.value, "reason": outcome.reason, "night": os.fspath(night),
        "task": record.task, "rung": record.rung, "k": record.k, "n": record.n, "purpose": record.purpose,
        "arms": write_arm_summaries(night, record_arms(record), record.n, task_dir),
        "cells": [{key: slot[key] for key in ("slot", "arm", "attempt_dir", "code", "verdict")} for slot in ledger["slots"]],
        "replaced": ledger["replaced"], "sittings": ledger["sittings"],
    }
    write_atomically(record_path.with_suffix(".result.json"), result)
    print(json.dumps({"status": result["status"], "reason": result["reason"], "night": result["night"],
                      "result": os.fspath(record_path.with_suffix(".result.json"))}, indent=2), file=out)
    if outcome.status is not Status.COMPLETE:
        print(f"launch stopped ({outcome.status}): {outcome.reason}", file=err)
    return EXIT_CODES[outcome.status]
```

Apply to `src/satyrn_evals/cli.py`:

```diff
diff --git a/src/satyrn_evals/cli.py b/src/satyrn_evals/cli.py
index bf94655..c09c5c5 100644
--- a/src/satyrn_evals/cli.py
+++ b/src/satyrn_evals/cli.py
@@ -21,6 +21,8 @@ from satyrn_evals.census import build_arg_parser as build_census_parser
 from satyrn_evals.census import run_cli as run_census
 from satyrn_evals.errors import SatyrnError, UsageError
 from satyrn_evals.grade import grade
+from satyrn_evals.launch_cell import ATTEMPT_DEADLINE, COMMAND_BACKSTOP
+from satyrn_evals.launch_record import DEFAULT_RUNS_ROOT, launch_record
 from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
 from satyrn_evals.qualify import qualify
 from satyrn_evals.rescore import regrade_attempt, summarize_output
@@ -34,6 +36,7 @@ from satyrn_evals.run_record import (
     gate,
     load_run_record,
     new_record,
+    record_arms,
     write_new_record,
 )
 from satyrn_evals.session import run_session
@@ -200,8 +203,16 @@ def main(argv: list[str] | None = None) -> int:
         if args.command == "launch":
             if args.preflight is not None:
                 return _launch_preflight(args)
+            if args.record is not None:
+                if args.check is not None:
+                    raise UsageError("launch takes RECORD or --check RECORD, not both")
+                return launch_record(
+                    Path(args.record), [Path(path) for path in args.arm or []], tasks_root=Path(args.tasks_root),
+                    runs_root=Path(args.runs_root), timeout=args.timeout, attempt_timeout=args.attempt_timeout,
+                    hunt=not args.no_hunt, settings=not args.no_settings,
+                )
             if args.check is None:
-                print("launch: cells are Phase 2c; use --check or --preflight", file=sys.stderr)
+                print("launch: RECORD --arm ARM.json, --check RECORD, or --preflight RECORD --arm ARM.json", file=sys.stderr)
                 return UsageError.exit_code
             record = load_run_record(Path(args.check))
             previous_result_committed = None
@@ -265,10 +276,10 @@ def _launch_preflight(args: argparse.Namespace) -> int:
     record = load_run_record(Path(args.preflight))
     if record.isolation is not Isolation.ISOLATED:
         raise RunRecordError(f"launch --preflight checks the cell user; {args.preflight} is a local record")
-    if args.arm is None:
+    if not args.arm:
         raise UsageError("launch --preflight needs --arm ARM.json")
-    arm = load_arm(Path(args.arm))
-    if (arm.arm, arm.model) != (record.arm, record.model):
+    arm = load_arm(Path(args.arm[0]))
+    if arm.arm not in record_arms(record) or arm.model != record.model:
         raise RunRecordError(
             f"arm file {args.arm} is {arm.arm} on {arm.model}; the record is {record.arm} on {record.model}"
         )
@@ -282,7 +293,7 @@ def _launch_preflight(args: argparse.Namespace) -> int:
     problems = list(report.problems)
     if os.environ.get(CELL_PATH_PREFIX_ENV):
         problems.append(f"{CELL_PATH_PREFIX_ENV} is set; it is a test seam, never a sitting's PATH")
-    print(json.dumps({"record": args.preflight, "arm": args.arm, "problems": problems, **report.checked}, indent=2))
+    print(json.dumps({"record": args.preflight, "arm": args.arm[0], "problems": problems, **report.checked}, indent=2))
     for problem in problems:
         print(f"launch preflight FAILED: {problem}", file=sys.stderr)
     return 1 if problems else 0
@@ -494,12 +505,19 @@ session_p.add_argument(
 )

 launch_p = sub.add_parser(
-    "launch", help="check a run record, or preflight the cell user for an isolated one (cells are Phase 2c)"
+    "launch", help="run a frozen record's cells; or check a record, or preflight the cell user for one"
 )
+launch_p.add_argument("record", nargs="?", default=None, help="frozen run record JSON whose cells to run")
 launch_p.add_argument("--check", default=None, help="run record JSON path to check")
 launch_p.add_argument("--preflight", default=None, help="isolated run record JSON path to preflight the cell for")
-launch_p.add_argument("--arm", default=None, help="arm JSON the preflight pins pi against")
-launch_p.add_argument("--no-hunt", action="store_true", help="skip the root-anchored find (minutes)")
+launch_p.add_argument("--arm", action="append", default=None, help="arm JSON, once per arm the record runs")
+launch_p.add_argument("--no-hunt", action="store_true", help="skip the root-anchored find (development records only)")
+launch_p.add_argument("--no-settings", action="store_true", help="skip preflight_settings (development records only)")
+launch_p.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="where the night directory lives")
+launch_p.add_argument("--timeout", type=positive_finite_timeout, default=COMMAND_BACKSTOP, help="command backstop, seconds")
+launch_p.add_argument(
+    "--attempt-timeout", type=positive_finite_timeout, default=ATTEMPT_DEADLINE, help="attempt deadline, seconds"
+)
 launch_p.add_argument(
     "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
 )
```

Apply to `ROADMAP.md`:

```diff
diff --git a/ROADMAP.md b/ROADMAP.md
index 777cf9f..a8d28a1 100644
--- a/ROADMAP.md
+++ b/ROADMAP.md
@@ -14,7 +14,8 @@ more. Nothing else is claimed.
 | 1 | Engine `/implement` v1: derived contract, guards 1–4 and symbol preservation, carried tests, compact results, receipt | overnight, fake-first | every component has replay or fixture tests both directions; a fake model completes `/implement` end to end; 120/300 frozen against measured suite durations | done 2026-09-14 — evals e0f25df, engine 46d4514 |
 | 2a | Eval core: harvest, token and turn tripwire, census extensions, hygiene | overnight | harness items 1, 3, 4, 5 have fixture tests both directions; the Engine arm runs against a fake | done 2026-09-14 — docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md |
 | 2b | Isolation and tasks: two-uid isolation, generator and R1-plan, candidates qualified, context-speed and concurrency probe | overnight, plus attended isolation setup and probe | the eval runs both arms against a fake under isolation with the budget tripwire; every candidate passes offline qualification; k measured; settings provenance verified by preflight | built 2026-09-15 — docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md; k and the first isolated Pi turn are the attended checklist in its Task 6 |
-| 2c | Launcher loop and warm prefix: `launch RECORD` runs n cells at k with arms interleaved under the record's profile; the warm prefix recorded and replayed byte-identically | overnight, plus attended recording | a fake completes a k = 2 interleaved record under isolation through the launcher; a recorded prefix replays byte-identically against a fake | not started; lands before Phase 3 |
+| 2c | Launcher loop: `launch RECORD` runs n cells per arm at k with arms interleaved under the record's profile, stops on infrastructure, resumes a stopped night; `record new` | overnight | a fake completes a k = 2 interleaved record under isolation through the launcher; a resumed night and an infrastructure stop | built 2026-09-15 — docs/superpowers/plans/2026-09-14-phase-2c-launcher-loop.md |
+| 2d | Warm prefix: a developer prefix recorded and replayed byte-identically (a declared secondary outside the win rule) | overnight, plus attended recording | a recorded prefix replays byte-identically against a fake | not started; lands before Phase 4 |
 | 3 | Admission and route proof: Baseline admission cells; one Engine cell per ceiling task | attended | ceiling and floor sets fixed; guards fire where retained evidence says they should; receipts read | not started |
 | 4 | Comparison: campaign record, held-out cut, seven batch nights | unattended batch, frozen in daylight | one result page per task and one against the rule | not started |
 | 5 | Decide and ship, or stop | attended | release one published, or a stated negative | not started |
```

- [ ] **Step 4: Pass, the launch rows three times.** `uv run pytest -q tests/test_launch_record.py tests/test_cli.py tests/test_cell_preflight.py tests/test_run_record.py` → 124 passed. Then, with no other cell-user test running:

```bash
for i in 1 2 3; do rm -rf "$SCR/pt$i"; SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q tests/integration/test_launch_record.py --basetemp "$SCR/pt$i"; echo "EXIT: $?"; rm -rf "$SCR/pt$i"; done
```

Expected: `5 passed` and `EXIT: 0` three times (about 13 s each). Then the Global Constraints' named integration rows → EXIT 0 (28 passed on the replay). Confirm nothing was left: `ls /Users/Shared/satyrn-cells` shows no `satyrn-attempt-*` or `satyrn-test-*` of this run, and `ps -A -o user=,command= | grep '^satyrn-cell' | grep -v -e /usr/libexec/ -e /usr/sbin/ -e /System/` prints nothing.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/launch_cell.py src/satyrn_evals/launch_record.py tests/test_launch_record.py tests/integration/test_launch_record.py
uv run ruff check --fix; just gates; echo "EXIT: $?"; just lint-docs; echo "EXIT: $?"
git add -A && git commit -m "Phase 2c: launch RECORD runs a frozen record's cells under its profile through the gates; a fake completes a k = 2 interleaved record under isolation, a resumed night and an infrastructure stop; roadmap rows 2c and 2d"
```

- [ ] **Step 6: The overnight run checklist** (for the controller/operator, not the maintainer; executed after Step 5 is committed, in this order, and reported in the morning status).

Preamble. Run every command from `~/projects/pauleveritt/satyrn-evals` on `release-one`, after 2b's six task commits and this plan's three are in and `just gates` is 0. `W=~/satyrn-smokes/2c` is the operator's scratch under the maintainer's 700 home (`mkdir -p ~/satyrn-smokes/2c`); every command below spells it out because shell state does not persist between tool calls. The probe and every `launch`/`admit.sh` run are started with the Bash tool's `run_in_background` and waited on for their exit notification; never two at once, and nothing else uses the GPU or the cell user meanwhile. **Stop the night** — start nothing further, report verbatim — on any unexpected EXIT, a launch exit of 1, 2 or 3, or any `EACCES`, "dubious ownership" or missing-tool error. The authority string every record carries: `the maintainer's one-time unattended-inference exception, 2026-09-14`.

1. **The cell's Pi settings (2b item 2, 2b Ruling 18).** Exactly the two behaviour keys, then verify compaction against the arm on a copy:
   ```bash
   W=~/satyrn-smokes/2c; mkdir -p "$W"
   (cd / && printf '{"compaction": {"enabled": true, "reserveTokens": 16384}, "defaultThinkingLevel": "high"}\n' | sudo -n -H -u satyrn-cell -- /bin/sh -c 'cat > /Users/satyrn-cell/.pi/agent/settings.json')
   C=$(mktemp -d "$W/cellpi-XXXX")
   (cd / && sudo -n -H -u satyrn-cell -- /bin/cat /Users/satyrn-cell/.pi/agent/models.json) > "$C/models.json"
   (cd / && sudo -n -H -u satyrn-cell -- /bin/cat /Users/satyrn-cell/.pi/agent/settings.json) > "$C/settings.json"
   uv run python scripts/preflight_inference.py arms/baseline-ornith15-9b.json --pi-config-dir "$C"; echo "EXIT: $?"   # 0
   rm -rf "$C"
   ```
2. **Export the engine for the cell (2b item 3, 2b Ruling 10).** No Engine cell runs tonight; the export is ready for Phase 3: `uv run satyrn-evals cell-engine --engine-repo ~/projects/pauleveritt/satyrn-engine --commit release-one; echo "EXIT: $?"` → prints `/Users/Shared/satyrn-cells/engine-<sha>`, EXIT 0.
3. **Warm the cell's uv cache for every candidate base (2b item 4; network, no model).** Each base copy is removed at once (a self-hosted base carries other tasks' hidden suites):
   ```bash
   for t in agentclinic-repair-depth-3 agentclinic-repair-depth-2 selfhost-run-record-gate selfhost-guard-prefixes selfhost-review-script selfhost-docs-linter; do
     D=$(mktemp -d /Users/Shared/satyrn-cells/warm-XXXXXX); chmod 2770 "$D"
     chmod +a "user:$USER allow list,search,add_file,add_subdirectory,delete_child,read,write,append,readattr,writeattr,readextattr,writeextattr,readsecurity,delete,file_inherit,directory_inherit" "$D"
     cp -R src/satyrn_evals/tasks/$t/base/. "$D/"; chmod -R g+rwX "$D"
     (cd /Users/Shared && sudo -n -H -u satyrn-cell -- /usr/bin/env -i HOME=/Users/satyrn-cell PATH=/Users/satyrn-cell/.local/bin:/opt/homebrew/bin:/usr/bin:/bin /bin/sh -c "umask 007 && cd '$D' && uv sync --frozen && uv sync --frozen --offline"); echo "$t EXIT: $?"
     rm -rf "$D"
   done
   ls /Users/Shared/satyrn-cells
   ```
   Every line `EXIT: 0`; no `warm-*` left.
4. **Settings provenance as the cell (2b item 5):** `W=~/satyrn-smokes/2c; uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell --record "$W/settings-cell.json"; echo "EXIT: $?"` → 0.
5. **The isolated preflight with the full hunt (2b item 6)**, on an uncommitted scratch admission record (`--preflight` does not require a frozen record):
   ```bash
   W=~/satyrn-smokes/2c; rm -f "$W/preflight-depth-3.json"
   uv run satyrn-evals record new --output "$W/preflight-depth-3.json" --task agentclinic-repair-depth-3 --rung R1 --arm baseline --n 4 --k 1 --purpose admission --authority "the maintainer's one-time unattended-inference exception, 2026-09-14"
   uv run satyrn-evals launch --preflight "$W/preflight-depth-3.json" --arm arms/baseline-ornith15-9b.json > "$W/preflight.json"; echo "EXIT: $?"
   ```
   EXIT 0 and `"problems": []` (about a minute). A hit is material a hunting model could read: stop the night and report it (removing it is the maintainer's).
6. **Nothing of a cell is left (2b item 7):** `ps -A -o user=,command= | grep '^satyrn-cell' | grep -v -e /usr/libexec/ -e /usr/sbin/ -e /System/` prints nothing; `ls /Users/Shared/satyrn-cells` shows no `satyrn-attempt-*`, `satyrn-test-*` or `warm-*`.
7. **The first Pi turn as the cell, through the launcher (2b item 8; Ruling 12; inference, no task outcome).**
   ```bash
   mkdir -p records
   uv run satyrn-evals record new --output records/2026-09-14-first-turn.json --task calc-build --tasks-root tests/integration/data/tasks --arm baseline --rung contract --n 1 --k 1 --purpose development --decision-rule "none: an isolation smoke, no task outcome" --authority "the maintainer's one-time unattended-inference exception, 2026-09-14"
   git add records/2026-09-14-first-turn.json && git commit -m "Phase 3 night 2026-09-14: the first isolated Pi turn's record (calc-build, development)"
   uv run satyrn-evals launch records/2026-09-14-first-turn.json --arm arms/baseline-ornith15-9b.json --tasks-root tests/integration/data/tasks; echo "EXIT: $?"
   ```
   Background; then read `records/2026-09-14-first-turn.result.json` (`status`; the cell's `code` — `NO_PATCH` or a fail is a finding, not a failure of the smoke), the attempt under `~/satyrn-runs/2026-09-14-first-turn/baseline/calc-build-*/`: `transcript.txt`'s first line (`"cwd"` under `/Users/Shared/satyrn-cells/`), that it holds `turn_start` events, whether the model's `git` and `uv run` commands succeeded; then item 6 again. Commit the result: `git add records/2026-09-14-first-turn.result.json && git commit -m "Phase 3 night 2026-09-14: the first isolated Pi turn's result"`. A launch exit other than 0 stops the night.
8. **The context-speed and concurrency probe (2b item 9; inference, exclusive GPU, about 25 minutes; Ruling 13).** Background:
   ```bash
   W=~/satyrn-smokes/2c; uv run python scripts/speed_probe.py run --model Ornith-1.5-9B-MLX-8bit --plan "$W/probe-plan.json"; echo "EXIT: $?"
   ```
   Then (the server rotates its log at midnight; concatenating the newest rotated file with the live one covers either case):
   ```bash
   W=~/satyrn-smokes/2c; L=$(ls -t ~/.omlx/logs/server.log.* 2>/dev/null | head -1)
   cat ${L:+"$L"} ~/.omlx/logs/server.log > "$W/server.log"
   uv run python scripts/speed_probe.py analyze --plan "$W/probe-plan.json" --log "$W/server.log" > "$W/probe.json"; echo "EXIT: $?"
   python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["k"])' "$W/probe.json" > "$W/k"; cat "$W/k"
   ```
   EXIT 0 twice; `$W/k` holds 1, 2 or 3. No context cap is set tonight (Ruling 13); `decode_tok_s_by_prompt` and `total_tok_s_by_k` go into the morning status.
9. **Write the admission driver** `~/satyrn-smokes/2c/admit.sh` (one record: write, freeze, launch until complete or 06:30, commit the result):

```bash
cat > ~/satyrn-smokes/2c/admit.sh <<'SH'
#!/bin/sh
# admit.sh TASK RUNG PREVIOUS_RESULT -- from the evals checkout; exits with the launcher's last code (2 before any launch).
set -u
T=$1; RUNG=$2; PREV=$3; W=$HOME/satyrn-smokes/2c
K=$(cat "$W/k") || exit 2
AUTH="the maintainer's one-time unattended-inference exception, 2026-09-14"
R=records/2026-09-14-admission-$T.json; RES=records/2026-09-14-admission-$T.result.json
STOP=$(date -j -f "%Y-%m-%d %H:%M" "2026-09-15 06:30" +%s)
if [ ! -f "$R" ]; then
  uv run satyrn-evals record new --output "$R" --task "$T" --rung "$RUNG" --arm baseline --n 4 --k "$K" \
    --purpose admission --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 \
    --previous-result "$PREV" --authority "$AUTH" || exit 2
  git add "$R" && git commit -qm "Phase 3 admission record: $T (Baseline, n=4, k=$K, 32,000 tokens and 48 turns, isolated; $AUTH)" || exit 2
fi
S=4
while [ "$(date +%s)" -lt "$STOP" ]; do
  uv run satyrn-evals launch "$R" --arm arms/baseline-ornith15-9b.json; S=$?
  [ "$S" -eq 4 ] || break
done
if [ -f "$RES" ]; then
  STATUS=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$RES")
  git add "$RES" && { git diff --cached --quiet || git commit -qm "Phase 3 admission result: $T ($STATUS)"; }
fi
echo "admit $T EXIT: $S"; exit "$S"
SH
```

10. **Ceiling admission, one record at a time, in this order** (each run in the background; the next starts only after the previous exited 0 and its result is committed; exit 4 means 06:30 was reached: stop the night; 1, 2 or 3: stop the night and report the result's `reason` and the launcher's stderr verbatim):
    1. `sh ~/satyrn-smokes/2c/admit.sh agentclinic-repair-depth-3 R1 records/2026-09-14-first-turn.result.json`
    2. `sh ~/satyrn-smokes/2c/admit.sh selfhost-run-record-gate R1-plan records/2026-09-14-admission-agentclinic-repair-depth-3.result.json`
    3. `sh ~/satyrn-smokes/2c/admit.sh selfhost-guard-prefixes R1-plan records/2026-09-14-admission-selfhost-run-record-gate.result.json`
    4. `sh ~/satyrn-smokes/2c/admit.sh selfhost-review-script R1-plan records/2026-09-14-admission-selfhost-guard-prefixes.result.json`
    Between records, `git log --oneline -2` shows the result commit, and item 6's `ps` line prints nothing.
11. **Floor tasks, only while the clock allows** (the driver launches nothing after 06:30):
    1. `sh ~/satyrn-smokes/2c/admit.sh agentclinic-repair-depth-2 R1 records/2026-09-14-admission-selfhost-review-script.result.json`
    2. `sh ~/satyrn-smokes/2c/admit.sh selfhost-docs-linter R1-plan records/2026-09-14-admission-agentclinic-repair-depth-2.result.json`
12. **Morning status** (under 250 words, not a docs page): evals head and the night's commits; item 5's `problems`; item 7's findings; the probe's `k`, `total_tok_s_by_k` and `decode_tok_s_by_prompt`; for each record: `status`, `reason` if any, `sittings` count, and per arm `passes` of `finished`, `code_counts` and `contamination`; any stop verbatim. Classifying tasks into ceiling and floor is the maintainer's reading in daylight; the operator reports counts only.

---

## Self-review against the spec

- **The launcher is the only path to a model and refuses** without a frozen record (T1 `gate(record_frozen=)`, T3 `git_frozen`; integration row "not committed"), the previous result committed (T3 row), n and wall clock under the cadence cap (`gate` caps; T2 wall-clock stop per cell), and a clean `preflight_settings` provenance block (T3: exit 1 on a non-zero settings run; deciding records cannot skip it, Ruling 7). The cell preflight is 2b's, run by every isolated launch.
- **Isolation, both arms, one condition**: the record's profile reaches every cell (`spec["isolation"]`); the done-when row runs both arms isolated at k = 2.
- **Budget and backstop**: every cell gets the record's 32,000/48 (or the record's values) and 1,800/2,100 s; deciding records refuse other backstops (Ruling 7).
- **Concurrency k frozen in the record, same for both arms, arms interleaved**: T1 `k`, T2 `plan_slots` and the k bound, Ruling 4.
- **Admission rule**: written into every admission record by `record new` (`ADMISSION_DECISION_RULE`); counting is Phase 3's reading of the results (passes and contamination per arm are in the result).
- **Denominators**: every launched cell with a record stays; only an infrastructure slot is replaced, and the replacement is listed (Ruling 5).
- **"A night the cap stops early completes the next night under the same record"**: exit 4 and resume (T2 row, integration row).
- **Stop rules**: infrastructure stops, model outcomes do not (T2 parametrized rows; integration `unreachable` row); SIGINT/SIGTERM with teardown (T2 rows; integration SIGTERM row: fake `pi` gone, no workspace left).
- **Rungs**: R1 for AgentClinic and R1-plan for self-hosted tasks are pinned per record (Ruling 2); the checklist names them.
- **Docs caps**: no `docs/results` file is written (Ruling 6); `ROADMAP.md` gains one row.
- **Process**: three tasks; every test run before hand-back (below). Warm prefix: 2d (Ruling 11).

## Test verification (plan review, 2026-09-14)

Every test this plan specifies was run in a scratch clone of 2b's verified replay at tag `t6` (never the main checkout, which 2b's controller is committing to tonight), on the maintainer's Mac with `satyrn-cell` set up and the engine checkout at `satyrn-engine`. A prototype was written first and committed as the three task commits (`p1`–`p3`); the file blocks and diffs above are extracted from those commits.

- **Before each task, its new tests fail for the missing implementation only**: T1 `ImportError` for `record_arms` and `ADMISSION_DECISION_RULE`; T2 `No module named 'satyrn_evals.launch'`; T3 `No module named 'satyrn_evals.launch_record'` and, for the integration rows, `SystemExit: 2` from argparse.
- **After each task**: T1 `just gates` EXIT 0, default tier 1,936 passed; T1 files plus `test_cli.py` and `test_cell_preflight.py` 119 passed. T2 22 passed; gates EXIT 0. T3 124 passed; gates EXIT 0, default tier 1,973 passed; `tests/integration/test_launch_record.py` 5 passed three runs in a row (12.9–13.1 s); the named integration rows 28 passed in 35 s.
- **The plan text reproduces the commits**: its file blocks written and its diff blocks applied with `git apply`, in order, with each task's provenance command, on a fresh clone of `t6`, give a tree identical to `p3` (`git diff --cached p3` empty); default tier 1,973 passed there. The overnight driver script in Step 6 passes `sh -n`, and its `date -j` stop time parses on this Mac.
- **Left behind**: after every run, no `satyrn-attempt-*` or `satyrn-test-*` of these runs under the cells root and no non-system `satyrn-cell` process. (2b's controller was running its own isolated rows at the same time; its leftovers were its own and were not touched.)

Defects found in the draft by running it, and fixed in this plan: both AgentClinic manifests' default contract is R3, not the spec's R1, so the record pins its rung (Ruling 2); `write_new_record` refused any record naming a previous result, because it read the file back through `gate` with the commit fact unknown (Ruling 9); the Engine arm's fake must write without committing (`deliver` commits the candidate), so the interleaved row uses fake mode `write` for both arms; a CLI default of `sys.stderr` bound at import time hid the launcher's problem lines from pytest's capture (`out`/`err` default to `None`).

Not executed, because it spends inference or is the operator's: Task 3 Step 6.
