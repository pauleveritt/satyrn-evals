# Phase 3 prep — The Engine arm ready for the route proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-15 on the maintainer's "proceed"; the open questions are decided below as Rulings.** Planned against evals `release-one` at `f966016` (admission done; the spec's ceiling set is depth-3, run-record-gate and docs-linter) and engine `release-one` at `341d4c4` (read only). Every test below was run before hand-back (see "Test verification"). Three tasks, about an hour.

**Goal:** Phase 3's route proof can run: one isolated Engine cell per ceiling task, through `launch`, on a committed Engine arm whose export holds no answer key and is checked against the arm's pins before any cell.

**Architecture:** Task 1 is the arm: `arms.ENGINE_SOURCES` becomes the seven `packages/engine/*.ts` files the engine loads and imports, the loader holds an Engine arm to the engine's real tool surface (`read,bash,edit,write,self_test`), and `arms/engine-ornith15-9b.json` is committed with its export path in the argv. Task 2 is the export: `cell_engine.export_engine` archives an allowlist (`EXPORT_PATHS`) instead of the whole tree, and `export_leaks` refuses any file named like, or holding the bytes of, a bundled hidden grader file, both when the export is made and in `verify_export`. Task 3 is the launcher: `cell_engine.arm_export_problems` checks the export an Engine arm names against its commit and digests, and `launch` and `launch --preflight` refuse on any problem; an integration row runs the committed arm (export path aside) through the launcher under isolation against the fake `pi`.

**Tech Stack:** Python 3.14, uv, pytest (default tier: audit-hook spawn tripwire; `integration` marker), ruff, just, git; sudo and the `satyrn-cell` user for the isolated rows; the `satyrn-engine` checkout (`SATYRN_V4_ENGINE_REPO`) for the export rows.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` — "The eval" (isolation, both arms; the Engine arm; budget and backstop), "Process" (the launcher is the only path to a model; deciding records refuse test seams; plans tested up front; docs caps), the phase table's row 3 ("one Engine cell per ceiling task … guards fire where retained evidence says they should; receipts read"). Contract and launcher facts: Phase 2a plan (Engine adapter, `attempt_engine`), Phase 2b plan and ledger `.superpowers/sdd/2026-09-14-phase-2b-isolation-and-tasks/progress.md` (R6 read-only export; R11 foreign entries and the sticky root; R14 parked "export hunt_names guard"), Phase 2c plan and ledger `.superpowers/sdd/2026-09-14-phase-2c-launcher-loop/progress.md` (R5 tolerated scratch; R7 parked the export guard again). Evidence: the launch preflight's hunt refused on 2026-09-15 01:10 on `/Users/Shared/satyrn-cells/engine-<sha>/tests/test_doc_caps.py`, the basename of selfhost-docs-linter's hidden suite. House style: the 2c and generator-fix plans.

## Rulings

1. **The export is an allowlist: `src`, `packages`, `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`** (`cell_engine.EXPORT_PATHS`, passed to `git archive` as pathspecs). Never `tests`, `docs`, `tools`, `BACKLOG.md`, `conftest.py` or anything else. `README.md` is required: without it `uv sync --frozen --offline` fails in hatchling ("Readme file does not exist: README.md"). `LICENSE` is not required (a sync without it exits 0); it travels with a copy of Apache-2.0 code. The `uv sync` flags are unchanged and **the dev group stays in the export's environment**: a draft with `--no-dev` made the isolated Engine row fail its receipt with `validation_output` "`<export>/.venv/bin/python: No module named pytest`". On the `calc-build` fixture the engine's validation (`uv run python -m pytest -q`) resolved Python from the export's `.venv`. Cost if wrong: an engine file needed at runtime outside the allowlist; the isolated Engine rows (derive, deliver, attempt, validation) pass on it.
2. **An export holding grader material is refused, by name or by bytes, whenever it is made or verified.** `export_leaks(dest, digests)` walks the whole export, `.venv` included. It names every file whose basename is that of any hidden overlay file, and every file whose SHA-256 equals one (`hygiene.overlay_digests`, `hygiene.overlay_copies`). `export_engine` checks before writing the marker, and `verify_export` checks too. So every reuse, every isolated Engine cell (`attempt_engine.isolated`) and every launch (Ruling 6) refuses a leaking export. A name match counts even with other bytes, because the hunt and a hunting model both look by name. All overlay names count, helpers included (`_seed.py`, `_contract.py`): the preflight hunt skips helpers as noise on a whole disk, but no engine or dependency file carries them (verified on a synced export). This closes the "export hunt guard" that 2b R14 and 2c R7 parked. An old whole-tree export is refused on reuse, so the operator removes it deliberately; the cells root was empty at planning time. Cost if wrong: a future dependency ships a file named like a hidden suite and the export refuses loudly; rename the task's hidden file, never widen the check.
3. **`ENGINE_SOURCES` is all seven `packages/engine/*.ts` files at the pinned commit**: `engine.ts`, `mutator.ts`, `scope.ts`, `bounds.ts` (always `--extension`), `runner.ts` (`--extension` with `test_command`), `orchestrator.ts` and `paths.ts` (imported). `satyrn-engine/src/satyrn_engine/attempt.py` refuses to start without the first four, plus `runner.ts` when the contract declares `test_command`. An integration row checks each digest against `git show <commit>:packages/engine/<name>`, and that the `.ts` files at the commit are exactly this set. Cost if wrong: none identified; a new module at a later commit fails that row.
4. **The Engine arm's tools are exactly `read,bash,edit,write,self_test`** (`arms.ENGINE_TOOLS`). `build_pi_command` passes that `--tools` whenever the contract declares `test_command`, and `derive` always declares one (`self_test_command` defaults to `uv run python -m pytest -q`). The adapter's argv never carries tools (`build_argv`), so the loader holds the arm file's record to the engine's surface. It refuses `read,edit` (the stale 75d4863 description in `arms.py`'s docstring, corrected), a missing `self_test`, or an extra name. Baseline, envelope and baseline-compaction keep `KNOWN_TOOLS`, so a Baseline arm naming `self_test` is refused. Cost if wrong: a contract without `test_command` would run `read,bash,edit,write`; `derive` cannot produce one.
5. **`arms/engine-ornith15-9b.json` names its export in its argv**: `["satyrn-evals-attempt-engine", "--engine-repo", "/Users/Shared/satyrn-cells/engine-341d4c450317f63e6af8958d45606cb737a131af"]`. It does not name the export through `SATYRN_ENGINE_REPO`, which the record, the arm and the drift probe cannot see. `engine_commit` is the full sha of `341d4c4`, with the seven digests. `model`, `server_model`, `settings_verified_by`, `pins.pi` and the whole `inference` block equal `arms/baseline-ornith15-9b.json`'s, so `preflight_settings.py arms/engine-ornith15-9b.json --cell` checks the same server and Pi entries; it exited 0 at planning time. Cost if wrong: none; a later engine commit is a new arm file, never an edit of this one.
6. **Before any cell, `launch` and `launch --preflight` check an Engine arm's export against its pins** (`cell_engine.arm_export_problems(arm, cells_root=CELLS_ROOT)`). The argv must carry `--engine-repo`, named `engine-<engine_commit>` and under the cells root. It must pass `verify_export` (Ruling 2), its marker must hold `engine_commit`, and every pinned `packages/engine/<name>` must match its digest byte for byte. Other arms return no problems. `launch_record` runs it under isolation, after the cell preflight, through a new `LaunchFacts.engine_export` seam; each problem is `launch FAILED: engine: …` and exit 1. It is not in the between-cells drift probe: the export is read-only to the cell and owned by the maintainer, and the arm file's bytes are already pinned. Until now nothing on the launch path compared the export with the arm; the pins were claims. Cost if wrong: an export edited by the maintainer mid-sitting is caught by the next launch.
7. **The route-proof integration row is a `development` record on `calc-build`.** The fake `pi` is a test seam a deciding record refuses (2c R7), and `calc-build` is the fixture the fake completes. Its arm is the committed file with only `--engine-repo` changed, to a scratch export of the same pinned commit under `cell_scratch`. It runs the record's own Ornith model string, and the export check, isolation and receipt are real. The 2c k = 2 interleaved row now takes the same derived arm (its model set to the fixture's, to match the fixture Baseline). No test writes to `/Users/Shared/satyrn-cells` outside `cell_scratch`'s `satyrn-test-*` directory. Cost if wrong: none; the deciding records differ from this row only in the seams 2c already proves refused.
8. **The operator exports by full sha, not `release-one`.** The arm pins `341d4c4`; `cell-engine --commit release-one` would export whatever the branch holds that day, and Ruling 6 would then refuse the launch. Cost if wrong: none.
9. **No engine edit, no spec or roadmap edit.** Row 3's status changes when the route-proof results are read, not when the arm is ready. One observation goes to the route-proof reading, not to this plan: the fixture's validation ran on the export's Python (Ruling 1). The receipts' `validation` and `validation_output` on the three real tasks are part of "receipts read".

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer per task; one Opus review per task before the next starts.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **No inference.** No `launch` of a real model, no `pi -p`, no request to oMLX. The operator commands at the end are the operator's, not the controller's.
- **Default test tier: no subprocess, no network, no model** (the audit hook in `tests/conftest.py`). Anything that spawns is `@pytest.mark.integration`.
- **Every refusal test has a sibling success test**; every detector has a firing row and a silent row.
- **Every task ends with `just gates` exit 0** (read the exit code; never pipe a gate). New files get `PROVENANCE.md` rows (`uv run python tools/provenance.py new <paths>`); edited files keep theirs. Run `uv run ruff check --fix` before gates.
- **Isolated integration rows run serially, never beside another cell-user run**, and skip with the reason when `sudo -n -u satyrn-cell true` fails (`cell_scratch`). After a run, macOS may leave a `(mdworker_shared)` process under the cell user for a minute; the launch preflight names it as stale, so wait and rerun.
- **Four integration rows fail on this Mac before any change**: `tests/test_workspace_failures.py::test_prepare_repository_fails_closed_on_verification[*]` (the Xcode license). Reported, never fixed here, never counted against a task.
- **Commit at the end of every task** on evals `release-one`, with the plan's message. Never `--amend`, merge or push. A task whose gates are red is not committed.
- **Evals tree only.** The engine is read, never edited. **The cell user is the maintainer's**: never create or change users, groups or `/etc/sudoers.d`; the only sudo forms are `sudo -n -u satyrn-cell` and `sudo -n -H -u satyrn-cell`. Under `/Users/Shared/satyrn-cells` create only what `cell_scratch` and attempts create and remove. **The cells root stays empty**: no task makes the real export; the operator's first command does.
- **Nothing is written to `/tmp` or `/private/tmp`** except under the session scratchpad `$SCR` (`/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/engine-arm-exec/`). Integration runs pass `--basetemp "$SCR/bt"` and remove it right after.
- **No test copies a bundled hidden task, or an engine file named like one, onto disk.** The whole-tree firing row lists `git archive` members in memory.
- **Docs caps stand:** spec ≤ 400 lines, `ROADMAP.md` ≤ 150; `just lint-docs` exit 0.
- **Starting point:** evals `release-one` at `f966016` plus this plan's commit (with its `PROVENANCE.md` row). Engine checkout at `/Users/pauleveritt/projects/pauleveritt/satyrn-engine` holding `341d4c450317f63e6af8958d45606cb737a131af`. The diff blocks below apply with `git apply` from the repository root; if one does not apply, apply it by hand to the same effect and say so in the task report.

---

## File structure

```
src/satyrn_evals/arms.py                   # ENGINE_TOOLS; ENGINE_SOURCES (seven); the engine arm's tool check    (modify, T1)
arms/engine-ornith15-9b.json               # the committed Engine arm                                             (new, T1)
tests/test_arms.py, tests/test_interleave.py, tests/integration/test_launch_record.py                            (modify, T1)
tests/integration/test_engine_arm_pins.py  # digests and the source set against the engine checkout             (new T1, modify T2)
src/satyrn_evals/cell_engine.py            # EXPORT_PATHS; export_leaks; verify_export(digests); arm_export_problems (modify, T2 T3)
tests/test_cell_engine.py, tests/integration/test_isolated_arms.py                                                (modify, T2 T3)
src/satyrn_evals/launch_record.py          # LaunchFacts.engine_export; the check after the cell preflight        (modify, T3)
src/satyrn_evals/cli.py                    # launch --preflight adds the export problems                          (modify, T3)
tests/test_launch_record.py, tests/test_cell_preflight.py, tests/integration/test_cell_preflight.py,
tests/integration/test_launch_record.py                                                                           (modify, T3)
```

---

### Task 1: The Engine arm file pins what the engine loads, on the engine's tool surface

**Files:**
- Create: `arms/engine-ornith15-9b.json`, `tests/integration/test_engine_arm_pins.py`
- Modify: `src/satyrn_evals/arms.py` (module docstring; `ENGINE_TOOLS`; `ENGINE_SOURCES`; `_load_pins` docstring; `load_arm` tool check)
- Test: `tests/test_arms.py` (import; appended rows), `tests/test_interleave.py` (one row reads the committed Engine arm), `tests/integration/test_launch_record.py` (its synthetic Engine arm uses the new surface and sources until Task 3 replaces it)

**Interfaces:**
- Consumes: `arms.load_arm`, `arms.build_argv`, `arms.KNOWN_TOOLS`, `arms.ArmError`; `integration.test_attempt._engine_repo`.
- Produces: `arms.ENGINE_TOOLS: tuple[str, ...] = ("read", "bash", "edit", "write", "self_test")`; `arms.ENGINE_SOURCES: tuple[str, ...] = ("engine.ts", "mutator.ts", "scope.ts", "bounds.ts", "runner.ts", "orchestrator.ts", "paths.ts")`; `load_arm` raises `ArmError` ("the engine arm's tools must be read,bash,edit,write,self_test …") for an Engine arm with any other tool list, and "unknown tool name(s) self_test" for any other arm naming it. File `arms/engine-ornith15-9b.json`: `arm` `engine`; `argv` `["satyrn-evals-attempt-engine", "--engine-repo", "/Users/Shared/satyrn-cells/engine-341d4c450317f63e6af8958d45606cb737a131af"]`; `pins.engine_commit` `341d4c450317f63e6af8958d45606cb737a131af`; seven digests; model and `inference` as `arms/baseline-ornith15-9b.json`.

- [ ] **Step 1: Write the failing tests.** Save this block as `$SCR/t1-tests.diff` and run `git apply "$SCR/t1-tests.diff"`:

```diff
diff --git a/tests/integration/test_engine_arm_pins.py b/tests/integration/test_engine_arm_pins.py
new file mode 100644
index 0000000..73a23fb
--- /dev/null
+++ b/tests/integration/test_engine_arm_pins.py
@@ -0,0 +1,40 @@
+"""The committed Engine arm's pins against the engine checkout (SATYRN_V4_ENGINE_REPO): git reads only, no model."""
+
+import hashlib
+import json
+import subprocess
+from pathlib import Path
+
+import pytest
+
+from integration.test_attempt import (
+    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
+)
+from satyrn_evals.arms import ENGINE_SOURCES, load_arm
+
+pytestmark = pytest.mark.integration
+
+ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"
+
+
+def _git(*argv: str) -> subprocess.CompletedProcess[bytes]:
+    return subprocess.run(["git", "-C", str(_engine_repo()), *argv], capture_output=True, check=True)
+
+
+def test_every_pinned_digest_is_the_bytes_of_that_source_at_the_pinned_commit() -> None:
+    arm = load_arm(ENGINE_ARM)
+    for name in ENGINE_SOURCES:
+        blob = _git("show", f"{arm.pins.engine_commit}:packages/engine/{name}").stdout
+        assert hashlib.sha256(blob).hexdigest() == arm.pins.digests[name], name
+
+
+def test_the_pinned_sources_are_every_typescript_file_of_the_engine_package_at_the_pinned_commit() -> None:
+    """A new module the extensions import would otherwise run unpinned."""
+    arm = load_arm(ENGINE_ARM)
+    listed = _git("ls-tree", "--name-only", arm.pins.engine_commit, "packages/engine/").stdout.decode().split()
+    assert sorted(Path(path).name for path in listed if path.endswith(".ts")) == sorted(ENGINE_SOURCES)
+
+
+def test_the_pinned_engine_commit_is_a_full_sha_the_checkout_holds() -> None:
+    commit = json.loads(ENGINE_ARM.read_text(encoding="utf-8"))["pins"]["engine_commit"]
+    assert _git("rev-parse", "--verify", f"{commit}^{{commit}}").stdout.decode().strip() == commit
diff --git a/tests/integration/test_launch_record.py b/tests/integration/test_launch_record.py
index f4ad922..ffd2f82 100644
--- a/tests/integration/test_launch_record.py
+++ b/tests/integration/test_launch_record.py
@@ -22,6 +22,7 @@ from integration.test_attempt import (
     _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
 )
 from integration.test_isolated_arms import _cell_pi  # type: ignore[missing-import]
+from satyrn_evals.arms import ENGINE_SOURCES, ENGINE_TOOLS
 from satyrn_evals.cell import CELLS_ROOT
 from satyrn_evals.cell_engine import export_engine
 from satyrn_evals.cli import main
@@ -61,9 +62,10 @@ def _arm_file(tmp_path: Path, name: str, argv: list[str]) -> Path:
         "pins": {"pi": "0.85.1", "engine_commit": None, "digests": {}},
     }
     if name == "engine":
+        body["tools"] = list(ENGINE_TOOLS)
         body["pins"] = {
             "pi": "0.85.1", "engine_commit": "0" * 40,
-            "digests": {source: "0" * 64 for source in ("engine.ts", "mutator.ts", "runner.ts", "orchestrator.ts")},
+            "digests": {source: "0" * 64 for source in ENGINE_SOURCES},
         }
     path = tmp_path / f"{name}.json"
     path.write_text(json.dumps(body))
diff --git a/tests/test_arms.py b/tests/test_arms.py
index 1cac027..24605da 100644
--- a/tests/test_arms.py
+++ b/tests/test_arms.py
@@ -18,6 +18,8 @@ from typing import cast
 import pytest

 from satyrn_evals.arms import (
+    ENGINE_SOURCES,
+    ENGINE_TOOLS,
     Arm,
     ArmError,
     ArmName,
@@ -322,3 +324,65 @@ def test_baseline_compaction_builds_the_baseline_argv(tmp_path: Path) -> None:
     assert build_argv(load_arm(path)) == [
         "satyrn-evals-attempt-pi", "--model", "omlx/m", "--tools", "read,edit"
     ]
+
+
+# --- the committed Engine arm ----------------------------------------------
+
+ENGINE = ARMS_ROOT / "engine-ornith15-9b.json"
+ORNITH_BASELINE = ARMS_ROOT / "baseline-ornith15-9b.json"
+
+
+def test_the_engine_arm_file_loads_with_the_engines_derived_contract_tool_surface() -> None:
+    """Fixture: arms/engine-ornith15-9b.json. `satyrn-engine`
+    `build_pi_command` hands pi `read,bash,edit,write,self_test` whenever the
+    contract declares `test_command`, and `derive` always declares one."""
+    arm = load_arm(ENGINE)
+    assert arm.arm == "engine"
+    assert arm.tools == ENGINE_TOOLS == ("read", "bash", "edit", "write", "self_test")
+    assert arm.pins.engine_commit == "341d4c450317f63e6af8958d45606cb737a131af"
+    assert sorted(arm.pins.digests) == sorted(ENGINE_SOURCES)
+
+
+def test_the_engine_arm_pins_all_seven_engine_package_sources() -> None:
+    """The four always-loaded extensions, `runner.ts` (with `test_command`),
+    and the two modules they import (`orchestrator.ts`, `paths.ts`)."""
+    assert sorted(ENGINE_SOURCES) == [
+        "bounds.ts", "engine.ts", "mutator.ts", "orchestrator.ts", "paths.ts", "runner.ts", "scope.ts",
+    ]
+
+
+def test_the_engine_arm_runs_the_export_of_its_pinned_commit_on_the_baselines_model_and_settings() -> None:
+    engine = json.loads(ENGINE.read_text(encoding="utf-8"))
+    baseline = json.loads(ORNITH_BASELINE.read_text(encoding="utf-8"))
+    commit = engine["pins"]["engine_commit"]
+    assert engine["argv"] == ["satyrn-evals-attempt-engine", "--engine-repo", f"/Users/Shared/satyrn-cells/engine-{commit}"]
+    for key in ("model", "server_model", "inference", "settings_verified_by"):
+        assert engine[key] == baseline[key], key
+    assert engine["pins"]["pi"] == baseline["pins"]["pi"]
+    assert build_argv(load_arm(ENGINE)) == [*engine["argv"], "--model", "omlx/Ornith-1.5-9B-MLX-8bit"]
+
+
+def test_an_engine_arm_missing_a_source_digest_is_refused(tmp_path: Path) -> None:
+    engine = json.loads(ENGINE.read_text(encoding="utf-8"))
+    del engine["pins"]["digests"]["paths.ts"]
+    path = _write(tmp_path, ENGINE, pins=engine["pins"])
+    with pytest.raises(ArmError, match="missing paths.ts"):
+        load_arm(path)
+
+
+@pytest.mark.parametrize(
+    "tools",
+    [["read", "bash", "edit", "write"], ["read", "edit"], ["read", "bash", "edit", "write", "self_test", "grep"]],
+    ids=["no-self-test", "old-read-edit", "extra"],
+)
+def test_an_engine_arm_whose_tools_are_not_the_engines_surface_is_refused(tmp_path: Path, tools: list[str]) -> None:
+    path = _write(tmp_path, ENGINE, tools=tools)
+    with pytest.raises(ArmError, match="read,bash,edit,write,self_test"):
+        load_arm(path)
+
+
+def test_a_baseline_arm_naming_self_test_is_refused(tmp_path: Path) -> None:
+    """`self_test` exists only where the engine loads `runner.ts`; bare pi has no such tool."""
+    path = _write(tmp_path, ORNITH_BASELINE, tools=["read", "bash", "edit", "write", "self_test"])
+    with pytest.raises(ArmError, match="unknown tool name"):
+        load_arm(path)
diff --git a/tests/test_interleave.py b/tests/test_interleave.py
index 1d65570..6468eb8 100644
--- a/tests/test_interleave.py
+++ b/tests/test_interleave.py
@@ -152,7 +152,7 @@ def test_arms_that_do_not_agree_on_the_model_are_refused(tmp_path: Path) -> None
     comparison; the sibling success is every other row in this file, which
     uses the two shipped arm files."""
     other = tmp_path / "engine.json"
-    data = dict(ENGINE_ARM_JSON)
+    data = json.loads((BASELINE.parent / "engine-ornith15-9b.json").read_text())
     data["model"] = "omlx/other-model"
     data["server_model"] = "other-model"
     other.write_text(json.dumps(data))
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `uv run pytest -q tests/test_arms.py tests/test_interleave.py`
Expected: collection error, `ImportError: cannot import name 'ENGINE_TOOLS' from 'satyrn_evals.arms'`.

- [ ] **Step 3: Write the implementation and the arm file.** Save this block as `$SCR/t1-impl.diff`, run `git apply "$SCR/t1-impl.diff"`, then `uv run python tools/provenance.py new arms/engine-ornith15-9b.json tests/integration/test_engine_arm_pins.py`:

```diff
diff --git a/arms/engine-ornith15-9b.json b/arms/engine-ornith15-9b.json
new file mode 100644
index 0000000..44eb7dd
--- /dev/null
+++ b/arms/engine-ornith15-9b.json
@@ -0,0 +1,44 @@
+{
+  "arm": "engine",
+  "settings_verified_by": "scripts/preflight_settings.py",
+  "argv": [
+    "satyrn-evals-attempt-engine",
+    "--engine-repo",
+    "/Users/Shared/satyrn-cells/engine-341d4c450317f63e6af8958d45606cb737a131af"
+  ],
+  "tools": [
+    "read",
+    "bash",
+    "edit",
+    "write",
+    "self_test"
+  ],
+  "model": "omlx/Ornith-1.5-9B-MLX-8bit",
+  "server_model": "Ornith-1.5-9B-MLX-8bit",
+  "pins": {
+    "pi": "0.85.1",
+    "engine_commit": "341d4c450317f63e6af8958d45606cb737a131af",
+    "digests": {
+      "engine.ts": "0f581ffeed8931fb0f656f6df7d547ad14893eb2c3edd1d8e203b819d4b2f9d1",
+      "mutator.ts": "d34ed2d44342db67739bf0b9458d6773b2b2d3a21aacde36ad4635ec82e88a52",
+      "scope.ts": "2eab1e01e01a34fdf42ec3e0555adadc7863f170fe6e71bc5ab2a42a3711049a",
+      "bounds.ts": "9fe674f671f328c1ba7bbe20b4cbb40016a92596a49166478d937d7c8cd67eb6",
+      "runner.ts": "c0142503bc13d626d37d6490072b9e3492c411a97c8835af9a187b220c4df5e0",
+      "orchestrator.ts": "83171788dd6084e73dc0fb54405e9a0487f0a35e3c899eeee8f01f2d7f92ded7",
+      "paths.ts": "9c5822fd01789cd44a648925285b85423b34cf6d1bdbef5e8d9d661fc9cc40bc"
+    }
+  },
+  "inference": {
+    "context_window": 262144,
+    "max_tokens": 32000,
+    "compaction_enabled": true,
+    "compaction_reserve_tokens": 16384,
+    "temperature": 0.6,
+    "top_p": 0.95,
+    "top_k": 20,
+    "min_p": 0.0,
+    "presence_penalty": 0.0,
+    "repetition_penalty": 1.0,
+    "declares_reasoning": true
+  }
+}
diff --git a/src/satyrn_evals/arms.py b/src/satyrn_evals/arms.py
index b9d950b..3ba82be 100644
--- a/src/satyrn_evals/arms.py
+++ b/src/satyrn_evals/arms.py
@@ -11,9 +11,10 @@ before three concrete implementations need the same shape. There is no
 registry, no discovery, and no plugin point; a caller names a path.

 **The tool surface is a predeclared confound.** Baseline holds
-`read,bash,edit,write`; Engine holds `read,edit` and wraps its prompt with
-its own handoff builder (`satyrn-engine` `build_pi_command`, pinned at
-commit `75d4863`). Any comparison between the two is meaningful only as
+`read,bash,edit,write`; Engine holds `read,bash,edit,write,self_test` and
+wraps its prompt with its own handoff builder (`satyrn-engine`
+`build_pi_command`, pinned by the arm's `engine_commit`). Any comparison
+between the two is meaningful only as
 "the shipped Engine versus bare Pi as shipped" — a product-level
 comparison that supports no sentence about a mechanism.
 """
@@ -43,20 +44,32 @@ type ArmName = Literal["baseline", "baseline-compaction", "envelope", "engine"]
 #: capability.
 KNOWN_TOOLS: frozenset[str] = frozenset({"read", "bash", "edit", "write"})

-#: The Engine sources whose bytes the Engine arm pins.
+#: The Engine's tool surface for the contracts it runs. `satyrn-engine`
+#: `build_pi_command` passes pi `--tools read,bash,edit,write,self_test`
+#: whenever the contract declares `test_command` (engine Ruling 1:
+#: `runner.ts` registers `self_test`), and `derive` always declares one. The
+#: Engine argv never carries it (`build_argv`), so the arm file records it,
+#: and the loader holds that record to exactly this surface.
+ENGINE_TOOLS: tuple[str, ...] = ("read", "bash", "edit", "write", "self_test")
+
+#: The Engine sources whose bytes the Engine arm pins: every TypeScript file
+#: of `packages/engine` at the pinned commit.
 #:
-#: `engine.ts` and `mutator.ts` are the `--extension` files
-#: `satyrn-engine`'s `build_pi_command` has always handed pi. `runner.ts`
-#: joined them with engine E7, which hands it over as a third extension
-#: whenever the contract declares `test_command` -- a set that stopped at
-#: two would have left the model's new tool surface unpinned.
-#: `orchestrator.ts` is not an extension but is imported by both, so a
-#: digest set omitting it would pin the entry points and not the behaviour.
+#: `engine.ts`, `mutator.ts`, `scope.ts` and `bounds.ts` are the
+#: `--extension` files `build_pi_command` always hands pi, and `runner.ts`
+#: joins them whenever the contract declares `test_command`
+#: (`satyrn-engine` `attempt.py`, which also refuses to start without the
+#: first four). `orchestrator.ts` and `paths.ts` are not extensions but are
+#: imported by them, so a digest set omitting either would pin the entry
+#: points and not the behaviour.
 ENGINE_SOURCES: tuple[str, ...] = (
     "engine.ts",
     "mutator.ts",
+    "scope.ts",
+    "bounds.ts",
     "runner.ts",
     "orchestrator.ts",
+    "paths.ts",
 )

 _COMMIT_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
@@ -120,7 +133,7 @@ def _load_pins(raw: object, arm: ArmName, source: Path) -> ArmPins:
     """The pin block, validated against what this arm can actually pin.

     Baseline pins pi alone; Engine additionally pins the commit and the
-    bytes of the two extension sources. A pin that cannot apply to the
+    bytes of every `ENGINE_SOURCES` file. A pin that cannot apply to the
     arm is refused rather than ignored: preflight would otherwise verify
     an engine checkout the Baseline arm never launches.
     """
@@ -173,7 +186,13 @@ def load_arm(path: Path) -> Arm:
         raise ArmError(f"{source}: an arm file must be a JSON object")
     arm_name = _arm_name(_require_str(data, "arm", source), source)
     tools = _require_list(data, "tools", source)
-    if unknown := sorted(set(tools) - KNOWN_TOOLS):
+    if arm_name == "engine":
+        if tuple(tools) != ENGINE_TOOLS:
+            raise ArmError(
+                f"{source}: the engine arm's tools must be {','.join(ENGINE_TOOLS)} "
+                f"(satyrn-engine build_pi_command for a derived contract), got {','.join(tools)}"
+            )
+    elif unknown := sorted(set(tools) - KNOWN_TOOLS):
         raise ArmError(f"{source}: unknown tool name(s) {', '.join(unknown)}")
     model = _require_str(data, "model", source)
     server_model = _require_str(data, "server_model", source)
```

The digests are `git -C /Users/pauleveritt/projects/pauleveritt/satyrn-engine show 341d4c4:packages/engine/<name> | shasum -a 256`; Step 4's integration row recomputes them.

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `uv run pytest -q tests/test_arms.py tests/test_interleave.py` → `49 passed`.
Run: `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_engine_arm_pins.py; echo "EXIT: $?"; rm -rf "$SCR/bt"` → `EXIT: 0` (3 passed).
Run: `uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell > /dev/null; echo "EXIT: $?"` → stderr `preflight_settings ok: 'engine' settings verified against oMLX and pi config`, `EXIT: 0` (a read of the cell's `models.json` through `sudo -n -H -u satyrn-cell cat`; no inference).
Run: `uv run ruff check --fix && just gates; echo "EXIT: $?"` → `EXIT: 0` (default tier 2,055 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/satyrn_evals/arms.py arms/engine-ornith15-9b.json PROVENANCE.md tests/test_arms.py tests/test_interleave.py tests/integration/test_launch_record.py tests/integration/test_engine_arm_pins.py
git commit -m "Phase 3 prep: the Engine arm file pins all seven engine sources at 341d4c4 on the engine's read,bash,edit,write,self_test surface"
```

---

### Task 2: The engine export holds only what the cell runs, and never an answer key

**Files:**
- Modify: `src/satyrn_evals/cell_engine.py` (module docstring; imports; `EXPORT_PATHS`; `export_leaks`; `verify_export(dest, digests=None)`; `export_engine` archives the allowlist and checks before the marker)
- Test: `tests/test_cell_engine.py` (imports; appended rows), `tests/integration/test_isolated_arms.py` (imports; the export row asserts the allowlist; one new row), `tests/integration/test_engine_arm_pins.py` (one firing/silent row over the archive, in memory)

**Interfaces:**
- Consumes: Task 1's `arms/engine-ornith15-9b.json` and `load_arm`; `hygiene.overlay_digests(tasks_root=DEFAULT_TASKS_ROOT) -> dict[str, str]` (digest to path under the tasks root), `hygiene.overlay_copies(root, digests) -> list[Path]`; `cell_engine.export_engine`, `verify_export`, `MARKER`.
- Produces: `cell_engine.EXPORT_PATHS: tuple[str, ...] = ("src", "packages", "pyproject.toml", "uv.lock", "README.md", "LICENSE")`; `cell_engine.export_leaks(dest: Path, digests: Mapping[str, str]) -> list[str]` (sorted; lines `"<path> is named like the hidden <task path>"` and `"<path> holds the bytes of the hidden <task path>"`); `cell_engine.verify_export(dest: Path, digests: Mapping[str, str] | None = None) -> str` (`None` means the bundled tasks' digests; raises `EngineExportError("export <dest> holds grader material: …")` after the ownership, mode and marker checks); `export_engine` raises `EngineExportError("<dest> holds grader material; no marker written: …")`.

- [ ] **Step 1: Write the failing tests.** Save this block as `$SCR/t2-tests.diff` and run `git apply "$SCR/t2-tests.diff"`:

```diff
diff --git a/tests/integration/test_engine_arm_pins.py b/tests/integration/test_engine_arm_pins.py
index 73a23fb..0b7be14 100644
--- a/tests/integration/test_engine_arm_pins.py
+++ b/tests/integration/test_engine_arm_pins.py
@@ -1,8 +1,10 @@
 """The committed Engine arm's pins against the engine checkout (SATYRN_V4_ENGINE_REPO): git reads only, no model."""

 import hashlib
+import io
 import json
 import subprocess
+import tarfile
 from pathlib import Path

 import pytest
@@ -11,6 +13,8 @@ from integration.test_attempt import (
     _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
 )
 from satyrn_evals.arms import ENGINE_SOURCES, load_arm
+from satyrn_evals.cell_engine import EXPORT_PATHS
+from satyrn_evals.hygiene import overlay_digests

 pytestmark = pytest.mark.integration

@@ -38,3 +42,19 @@ def test_the_pinned_sources_are_every_typescript_file_of_the_engine_package_at_t
 def test_the_pinned_engine_commit_is_a_full_sha_the_checkout_holds() -> None:
     commit = json.loads(ENGINE_ARM.read_text(encoding="utf-8"))["pins"]["engine_commit"]
     assert _git("rev-parse", "--verify", f"{commit}^{{commit}}").stdout.decode().strip() == commit
+
+
+def _archived_names(commit: str, *paths: str) -> set[str]:
+    """Basenames of every file ``git archive`` would write, read in memory: nothing lands on disk."""
+    archive = _git("archive", "--format=tar", commit, *(["--", *paths] if paths else [])).stdout
+    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
+        return {Path(member.name).name for member in tar.getmembers() if member.isfile()}
+
+
+def test_the_whole_tree_of_the_pinned_commit_names_a_hidden_suite_and_the_allowlist_does_not() -> None:
+    """The firing row is the 2026-09-15 hunt's find; the silent row is what `export_engine` now archives."""
+    commit = load_arm(ENGINE_ARM).pins.engine_commit
+    assert commit is not None
+    hidden = {Path(path).name for path in overlay_digests().values()}
+    assert "test_doc_caps.py" in _archived_names(commit) & hidden
+    assert _archived_names(commit, *EXPORT_PATHS) & hidden == set()
diff --git a/tests/integration/test_isolated_arms.py b/tests/integration/test_isolated_arms.py
index 1a2659e..22f2bb0 100644
--- a/tests/integration/test_isolated_arms.py
+++ b/tests/integration/test_isolated_arms.py
@@ -21,6 +21,7 @@ from integration.cell_support import cell_process_alive
 from integration.test_attempt import (
     _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
 )
+from satyrn_evals.arms import load_arm
 from satyrn_evals.attempt import attempt
 from satyrn_evals.attempt_engine import RECEIPT_NAME
 from satyrn_evals.attempt_record import AttemptCode
@@ -31,7 +32,14 @@ from satyrn_evals.cell import (
     Isolation,
     share_with_cell,
 )
-from satyrn_evals.cell_engine import export_engine
+from satyrn_evals.cell_engine import (
+    EXPORT_PATHS,
+    MARKER,
+    export_engine,
+    export_leaks,
+    verify_export,
+)
+from satyrn_evals.hygiene import overlay_digests
 from satyrn_evals.patch import parse_patch_paths
 from satyrn_evals.verdict import Verdict

@@ -160,6 +168,7 @@ def test_the_engine_export_is_made_once_and_runs_as_the_cell_user(cell_scratch:

     first = export_engine(_engine_repo(), "HEAD", root=cell_scratch)
     assert export_engine(_engine_repo(), "HEAD", root=cell_scratch) == first
+    assert sorted(path.name for path in first.iterdir()) == sorted([*EXPORT_PATHS, ".venv", MARKER])
     environment = cell_environment(parent=cell_scratch)
     environment.pop("UV_PROJECT_ENVIRONMENT")  # as `attempt_engine.as_cell` does
     ran = run_as_cell(
@@ -171,3 +180,18 @@ def test_the_engine_export_is_made_once_and_runs_as_the_cell_user(cell_scratch:
     touched = run_as_cell(["/usr/bin/touch", os.fspath(probe)], cwd=first, environment=environment)
     assert touched.returncode != 0 and not probe.exists(), touched.stderr
     assert main(["cell-engine", "--engine-repo", os.fspath(_engine_repo()), "--commit", "not-a-commit"]) == 2
+
+
+ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"
+
+
+def test_the_export_of_the_arms_pinned_commit_holds_no_grader_material(cell_scratch: Path) -> None:
+    """341d4c4's whole tree holds ``tests/test_doc_caps.py``, the name of selfhost-docs-linter's hidden suite;
+    its export holds only ``EXPORT_PATHS`` and the environment, and verifies."""
+    commit = load_arm(ENGINE_ARM).pins.engine_commit
+    assert commit is not None
+    export = export_engine(_engine_repo(), commit, root=cell_scratch)
+    assert export.name == f"engine-{commit}"
+    assert not (export / "tests").exists() and not (export / "docs").exists()
+    assert export_leaks(export, overlay_digests()) == []
+    assert verify_export(export) == commit
diff --git a/tests/test_cell_engine.py b/tests/test_cell_engine.py
index 8b6c285..eb62f64 100644
--- a/tests/test_cell_engine.py
+++ b/tests/test_cell_engine.py
@@ -3,12 +3,18 @@
 Every refusal has a success sibling over the same shape.
 """

-
+import json
 from pathlib import Path

 import pytest

-from satyrn_evals.cell_engine import EngineExportError, verify_export
+from satyrn_evals.cell_engine import (
+    EXPORT_PATHS,
+    EngineExportError,
+    export_leaks,
+    verify_export,
+)
+from satyrn_evals.hygiene import overlay_digests

 SHA = "d" * 40

@@ -54,3 +60,54 @@ def test_an_export_with_an_empty_marker_is_refused(tmp_path: Path) -> None:
 def test_a_missing_export_directory_is_refused(tmp_path: Path) -> None:
     with pytest.raises(EngineExportError, match="cannot stat"):
         verify_export(tmp_path / "does-not-exist")
+
+
+# --- the export holds no answer key (the 2026-09-15 01:10 hunt) -------------
+
+KEY = "def test_caps():\n    assert 42\n"
+
+
+def _digests(tmp_path: Path) -> dict[str, str]:
+    """A hidden task whose overlay holds ``tests/test_doc_caps.py``, as selfhost-docs-linter's does."""
+    task = tmp_path / "tasks" / "hidden"
+    (task / "overlay" / "tests").mkdir(parents=True)
+    (task / "overlay" / "tests" / "test_doc_caps.py").write_text(KEY)
+    (task / "manifest.json").write_text(json.dumps({"grader_overlay": "overlay", "oracle_visibility": "hidden"}))
+    return overlay_digests(tmp_path / "tasks")
+
+
+def _export_with(tmp_path: Path, relative: str, text: str) -> Path:
+    export = _export(tmp_path)
+    (export / relative).parent.mkdir(parents=True, exist_ok=True)
+    (export / relative).write_text(text)
+    return export
+
+
+def test_an_export_of_only_engine_sources_is_verified_against_the_answer_keys(tmp_path: Path) -> None:
+    export, digests = _export_with(tmp_path, "src/satyrn_engine/cli.py", "def main():\n    return 0\n"), _digests(tmp_path)
+    assert export_leaks(export, digests) == []
+    assert verify_export(export, digests) == SHA
+
+
+def test_an_export_holding_a_file_named_like_a_hidden_test_is_refused(tmp_path: Path) -> None:
+    """The engine's own ``tests/test_doc_caps.py`` is not the hidden suite, but a hunting model finds it by name."""
+    export, digests = _export_with(tmp_path, "tests/test_doc_caps.py", "def test_engine_caps():\n    pass\n"), _digests(tmp_path)
+    assert export_leaks(export, digests) == [
+        f"{export / 'tests' / 'test_doc_caps.py'} is named like the hidden hidden/overlay/tests/test_doc_caps.py"
+    ]
+    with pytest.raises(EngineExportError, match="holds grader material"):
+        verify_export(export, digests)
+
+
+def test_an_export_holding_a_hidden_files_bytes_under_another_name_is_refused(tmp_path: Path) -> None:
+    export, digests = _export_with(tmp_path, "docs/notes.py", KEY), _digests(tmp_path)
+    assert export_leaks(export, digests) == [
+        f"{export / 'docs' / 'notes.py'} holds the bytes of the hidden hidden/overlay/tests/test_doc_caps.py"
+    ]
+    with pytest.raises(EngineExportError, match="holds grader material"):
+        verify_export(export, digests)
+
+
+def test_the_export_allowlist_is_what_the_cell_runs_and_never_tests_or_docs() -> None:
+    assert EXPORT_PATHS == ("src", "packages", "pyproject.toml", "uv.lock", "README.md", "LICENSE")
+    assert not {"tests", "docs", "tools", "BACKLOG.md", "conftest.py"} & set(EXPORT_PATHS)
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `uv run pytest -q tests/test_cell_engine.py`
Expected: collection error, `ImportError: cannot import name 'EXPORT_PATHS' from 'satyrn_evals.cell_engine'`.

- [ ] **Step 3: Write the implementation.** Save this block as `$SCR/t2-impl.diff` and run `git apply "$SCR/t2-impl.diff"`:

```diff
diff --git a/src/satyrn_evals/cell_engine.py b/src/satyrn_evals/cell_engine.py
index 6905b3a..eafe7e8 100644
--- a/src/satyrn_evals/cell_engine.py
+++ b/src/satyrn_evals/cell_engine.py
@@ -2,27 +2,45 @@

 The Engine arm's ``derive`` and ``deliver`` run as the cell user, and the
 cell cannot read the maintainer's engine checkout (his home is 700). So the
-maintainer exports the pinned commit -- ``git archive``, no history -- into
-``CELLS_ROOT/engine-<commit>``, syncs its environment offline from his own
-uv cache against a Python the cell can execute (Homebrew's, world-readable;
+maintainer exports the pinned commit -- ``git archive`` of ``EXPORT_PATHS``
+only, no history -- into ``CELLS_ROOT/engine-<commit>``, syncs its
+environment offline from his own uv cache against a Python the cell can
+execute (Homebrew's, world-readable;
 uv's managed Pythons live under his home), and shares it with the group
 read-only (Ruling 10: the pinned engine stays enforceable only if the cell
 cannot write into its export -- source or ``.venv``). The marker file is
 written last, so a half-made export is never reused.
+
+The cell can read the export, and a hunting model reads whatever it can
+reach: on 2026-09-15 the launch preflight's hunt found the engine's own
+``tests/test_doc_caps.py`` in a whole-tree export, the basename of
+selfhost-docs-linter's hidden suite. So the export holds only what
+``uv sync`` builds and the cell runs, and an export holding any file named
+like, or with the bytes of, a bundled hidden grader file is refused when it
+is made and every time it is verified.
 """

+import hashlib
 import io
 import os
 import stat
 import subprocess
 import tarfile
+from collections.abc import Mapping
 from pathlib import Path

 from satyrn_evals.cell import CELLS_ROOT, grant_maintainer, share_with_cell
 from satyrn_evals.errors import UsageError
+from satyrn_evals.hygiene import overlay_copies, overlay_digests

 MARKER = ".satyrn-engine-export"
 CELL_PYTHON = Path("/opt/homebrew/bin/python3.14")
+#: What an export holds: the package sources ``uv sync`` builds (``src``,
+#: ``pyproject.toml``, ``uv.lock``, and ``README.md``, which hatchling's
+#: ``readme`` field refuses to build without), the extensions pi loads
+#: (``packages``), and the licence that travels with a copy. Never ``tests``,
+#: ``docs``, ``tools`` or anything else of the engine repository.
+EXPORT_PATHS: tuple[str, ...] = ("src", "packages", "pyproject.toml", "uv.lock", "README.md", "LICENSE")


 class EngineExportError(UsageError):
@@ -33,14 +51,36 @@ def export_path(commit: str, root: Path = CELLS_ROOT) -> Path:
     return root / f"engine-{commit}"


-def verify_export(dest: Path) -> str:
+def export_leaks(dest: Path, digests: Mapping[str, str]) -> list[str]:
+    """Every file under ``dest`` named like, or holding the bytes of, a hidden grader file.
+
+    ``digests`` is ``hygiene.overlay_digests``: grader-file SHA-256 to its
+    path under the tasks root. A name match is a leak even with other bytes,
+    because the preflight hunt (``cell_preflight.hunt_names``) and a hunting
+    model both look by name.
+    """
+    names = {Path(relative).name: relative for relative in digests.values()}
+    leaks = [
+        f"{Path(directory) / name} is named like the hidden {names[name]}"
+        for directory, _dirs, files in os.walk(dest)
+        for name in files
+        if name in names
+    ]
+    for path in overlay_copies(dest, dict(digests)):
+        leaks.append(f"{path} holds the bytes of the hidden {digests[hashlib.sha256(path.read_bytes()).hexdigest()]}")
+    return sorted(leaks)
+
+
+def verify_export(dest: Path, digests: Mapping[str, str] | None = None) -> str:
     """The commit this export holds, once it is confirmed safe to reuse or run (F2/R11).

     A cell able to rename or remove entries under a non-sticky cells root
     could plant its own directory with a matching marker; this refuses
     anything the maintainer does not still exclusively control: owned by
     the current uid, no group-write and no other-write bit, and a complete
-    marker. Raises ``EngineExportError`` naming which check failed.
+    marker. It also refuses an export holding grader material
+    (``export_leaks`` against ``digests``, default the bundled tasks').
+    Raises ``EngineExportError`` naming which check failed.
     """
     try:
         info = dest.stat()
@@ -57,6 +97,8 @@ def verify_export(dest: Path) -> str:
         raise EngineExportError(f"export {dest} has no complete marker: {exc}") from exc
     if not sha:
         raise EngineExportError(f"export {dest} has an empty marker")
+    if leaks := export_leaks(dest, overlay_digests() if digests is None else digests):
+        raise EngineExportError(f"export {dest} holds grader material: {'; '.join(leaks)}")
     return sha


@@ -80,7 +122,10 @@ def export_engine(engine_repo: Path, commit: str, *, root: Path = CELLS_ROOT, py
         if existing_sha != sha:
             raise EngineExportError(f"{dest} exists without a complete export marker; remove it deliberately")
         return dest
-    archive = subprocess.run(["git", "-C", os.fspath(engine_repo), "archive", "--format=tar", sha], capture_output=True, check=False)
+    archive = subprocess.run(
+        ["git", "-C", os.fspath(engine_repo), "archive", "--format=tar", sha, "--", *EXPORT_PATHS],
+        capture_output=True, check=False,
+    )
     if archive.returncode != 0:
         raise EngineExportError(f"git archive {sha} failed: {os.fsdecode(archive.stderr).strip()}")
     dest.mkdir()
@@ -95,6 +140,8 @@ def export_engine(engine_repo: Path, commit: str, *, root: Path = CELLS_ROOT, py
     )
     if synced.returncode != 0:
         raise EngineExportError(f"uv sync in {dest} failed: {synced.stderr.strip()}")
+    if leaks := export_leaks(dest, overlay_digests()):
+        raise EngineExportError(f"{dest} holds grader material; no marker written: {'; '.join(leaks)}")
     share_with_cell(dest, writable=False)
     (dest / MARKER).write_text(sha + "\n")
     share_with_cell(dest, writable=False)
```

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `uv run pytest -q tests/test_cell_engine.py` → `10 passed`.
Run: `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_engine_arm_pins.py tests/integration/test_isolated_arms.py; echo "EXIT: $?"; rm -rf "$SCR/bt"; ls -A /Users/Shared/satyrn-cells` → `EXIT: 0` (10 passed; the isolated rows skip with the reason if the cell user is unavailable) and an empty listing.
Run: `uv run ruff check --fix && just gates; echo "EXIT: $?"` → `EXIT: 0` (default tier 2,059 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/satyrn_evals/cell_engine.py tests/test_cell_engine.py tests/integration/test_isolated_arms.py tests/integration/test_engine_arm_pins.py
git commit -m "Phase 3 prep: the engine export archives src, packages and the build files only, and refuses any file named like or equal to a hidden grader file"
```

---

### Task 3: `launch` checks an Engine arm's export against its pins, and the committed arm runs through the launcher

**Files:**
- Modify: `src/satyrn_evals/cell_engine.py` (import `Arm`; `arm_export_problems`), `src/satyrn_evals/launch_record.py` (docstring gate 4; import; `LaunchFacts.engine_export`; the check after the cell preflight), `src/satyrn_evals/cli.py` (import; `_launch_preflight` adds the problems)
- Test: `tests/test_cell_engine.py`, `tests/test_launch_record.py`, `tests/test_cell_preflight.py` (appended rows), `tests/integration/test_launch_record.py` (the Engine arm is the committed file; one route-proof-shaped row), `tests/integration/test_cell_preflight.py` (one row: the hunt as the cell over a real export)

**Interfaces:**
- Consumes: Task 1's `arms/engine-ornith15-9b.json`, `ENGINE_SOURCES`; Task 2's `verify_export`, `EngineExportError`, `export_engine`; `cell_engine.export_path(commit, root=CELLS_ROOT)`; `launch_record.LaunchFacts`, `launch_record.launch_record`; `cli._launch_preflight`; `cell_preflight.preflight_cell`; `integration.cell_support.run_as_cell`; `cell.cell_environment`.
- Produces: `cell_engine.arm_export_problems(arm: Arm, cells_root: Path = CELLS_ROOT) -> list[str]` (empty for a non-Engine arm; exact lines: `"the engine arm's argv names no --engine-repo export (satyrn-evals cell-engine)"`, `"the engine export <p> is not engine-<commit>, the arm's pinned commit"`, `"the engine export <p> is not under <cells_root>"`, `verify_export`'s message, `"the engine export <p> holds <sha>, not the arm's pinned <commit>"`, `"the engine export <p> has no packages/engine/<name>"`, `"the engine export <p> has packages/engine/<name> other than the pinned bytes"`); `LaunchFacts.engine_export: Callable[[Arm], list[str]] = arm_export_problems`. Behaviour: under isolation, `launch_record` prints `launch FAILED: <arm>: <problem>` and exits 1 before any cell; `launch --preflight` lists the problems in its report's `problems` and exits 1.

- [ ] **Step 1: Write the failing tests.** Save this block as `$SCR/t3-tests.diff` and run `git apply "$SCR/t3-tests.diff"`:

```diff
diff --git a/tests/integration/test_cell_preflight.py b/tests/integration/test_cell_preflight.py
index 69688fc..e294273 100644
--- a/tests/integration/test_cell_preflight.py
+++ b/tests/integration/test_cell_preflight.py
@@ -6,13 +6,21 @@ planted file proves the refusal and its removal proves the silence.
 """

 import json
+import os
 import stat
 import sys
+from dataclasses import replace
 from pathlib import Path

 import pytest

+from integration.cell_support import (
+    run_as_cell,  # type: ignore[missing-import]  # pytest sibling resolution
+)
+from integration.test_attempt import _engine_repo  # type: ignore[missing-import]
 from satyrn_evals.arms import load_arm
+from satyrn_evals.cell import cell_environment
+from satyrn_evals.cell_engine import arm_export_problems, export_engine
 from satyrn_evals.cell_preflight import preflight_cell
 from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

@@ -81,3 +89,22 @@ def test_the_hunt_finds_a_planted_answer_key_and_nothing_once_it_is_gone(
 def test_the_cell_users_pi_models_are_read_as_the_cell(cell_scratch: Path) -> None:
     models = read_cell_pi_models()
     assert "omlx" in models["providers"], json.dumps(models)[:200]
+
+
+def test_the_hunt_run_as_the_cell_over_the_pinned_engine_export_finds_nothing(
+    cell_scratch: Path, hermetic_cells_root: Path
+) -> None:
+    """The 2026-09-15 hunt refused on the whole-tree export; the allowlisted export of the same commit is silent,
+    though the cell reads it, and it is the engine the committed arm pins."""
+    committed = load_arm(REPO / "arms" / "engine-ornith15-9b.json")
+    assert committed.pins.engine_commit is not None
+    export = export_engine(_engine_repo(), committed.pins.engine_commit, root=cell_scratch)
+    found = run_as_cell(
+        ["/usr/bin/find", os.fspath(export / "packages"), "-name", "engine.ts"], cwd=export,
+        environment=cell_environment(parent=cell_scratch),
+    )
+    assert found.stdout.strip() == os.fspath(export / "packages" / "engine" / "engine.ts"), found.stderr
+    report = preflight_cell(pinned_pi=PINNED, protected=(), hunt_root=str(export), cells_root=hermetic_cells_root)
+    assert report.problems == [] and report.checked["hunt_hits"] == []
+    pointed = replace(committed, argv=("satyrn-evals-attempt-engine", "--engine-repo", os.fspath(export)))
+    assert arm_export_problems(pointed) == []
diff --git a/tests/integration/test_launch_record.py b/tests/integration/test_launch_record.py
index ffd2f82..4c465ee 100644
--- a/tests/integration/test_launch_record.py
+++ b/tests/integration/test_launch_record.py
@@ -22,7 +22,8 @@ from integration.test_attempt import (
     _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
 )
 from integration.test_isolated_arms import _cell_pi  # type: ignore[missing-import]
-from satyrn_evals.arms import ENGINE_SOURCES, ENGINE_TOOLS
+from satyrn_evals.arms import load_arm
+from satyrn_evals.attempt_engine import RECEIPT_NAME
 from satyrn_evals.cell import CELLS_ROOT
 from satyrn_evals.cell_engine import export_engine
 from satyrn_evals.cli import main
@@ -32,6 +33,7 @@ from satyrn_evals.summary import SUMMARY_NAME
 pytestmark = pytest.mark.integration

 TASKS = Path(__file__).parent / "data" / "tasks"
+ENGINE_ARM = Path(__file__).resolve().parents[2] / "arms" / "engine-ornith15-9b.json"
 ENTRY = "import sys; from satyrn_evals.cli import main; sys.exit(main())"


@@ -39,7 +41,9 @@ def _git(repo: Path, *argv: str) -> None:
     subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *argv], cwd=repo, check=True, capture_output=True)


-def _frozen_record(tmp_path: Path, name: str, *, arm: str, n: int, k: int, max_minutes: int = 60) -> Path:
+def _frozen_record(
+    tmp_path: Path, name: str, *, arm: str, n: int, k: int, max_minutes: int = 60, model: str = "omlx/fixture"
+) -> Path:
     repo = tmp_path / "records"
     if not (repo / ".git").exists():
         repo.mkdir()
@@ -48,7 +52,7 @@ def _frozen_record(tmp_path: Path, name: str, *, arm: str, n: int, k: int, max_m
     assert main([
         "record", "new", "--output", str(path), "--task", "calc-build", "--tasks-root", str(TASKS), "--arm", arm,
         "--rung", "contract", "--n", str(n), "--k", str(k), "--purpose", "development",
-        "--max-minutes", str(max_minutes), "--model", "omlx/fixture",
+        "--max-minutes", str(max_minutes), "--model", model,
     ]) == 0
     _git(repo, "add", path.name)
     _git(repo, "commit", "-qm", name)
@@ -61,17 +65,30 @@ def _arm_file(tmp_path: Path, name: str, argv: list[str]) -> Path:
         "server_model": "fixture",
         "pins": {"pi": "0.85.1", "engine_commit": None, "digests": {}},
     }
-    if name == "engine":
-        body["tools"] = list(ENGINE_TOOLS)
-        body["pins"] = {
-            "pi": "0.85.1", "engine_commit": "0" * 40,
-            "digests": {source: "0" * 64 for source in ENGINE_SOURCES},
-        }
     path = tmp_path / f"{name}.json"
     path.write_text(json.dumps(body))
     return path


+def _engine_arm(tmp_path: Path, export: Path, *, model: str | None = None) -> Path:
+    """The committed Engine arm, byte for byte but for its export path (a scratch export of the same commit)
+    and, for a record interleaved with the fixture Baseline, its model."""
+    body = json.loads(ENGINE_ARM.read_text())
+    repo = body["argv"].index("--engine-repo") + 1
+    body["argv"][repo] = os.fspath(export)
+    if model is not None:
+        body["model"], body["server_model"] = model, model.split("/", 1)[1]
+    path = tmp_path / "engine.json"
+    path.write_text(json.dumps(body))
+    return path
+
+
+def _pinned_export(cell_scratch: Path) -> Path:
+    commit = load_arm(ENGINE_ARM).pins.engine_commit
+    assert commit is not None
+    return export_engine(_engine_repo(), commit, root=cell_scratch)
+
+
 def _baseline_arm(tmp_path: Path) -> Path:
     return _arm_file(tmp_path, "baseline", [sys.executable, "-m", "satyrn_evals.attempt_pi"])

@@ -95,11 +112,7 @@ def test_a_fake_completes_a_k2_interleaved_record_under_isolation_through_the_la
     tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
 ) -> None:
     _cell_pi(cell_scratch, monkeypatch, "write")  # the Engine arm's deliver commits; Baseline's harvest takes the files
-    export = export_engine(_engine_repo(), "HEAD", root=cell_scratch)
-    engine = _arm_file(
-        tmp_path, "engine",
-        [sys.executable, "-m", "satyrn_evals.attempt_engine", "--engine-repo", os.fspath(export), "--uv-bin", "uv"],
-    )
+    engine = _engine_arm(tmp_path, _pinned_export(cell_scratch), model="omlx/fixture")
     record = _frozen_record(tmp_path, "interleaved", arm="baseline+engine", n=2, k=2)
     before = _attempt_dirs()
     assert _launch(record, [_baseline_arm(tmp_path), engine], tmp_path / "runs") == 0
@@ -113,6 +126,28 @@ def test_a_fake_completes_a_k2_interleaved_record_under_isolation_through_the_la
     assert _attempt_dirs() <= before


+def test_the_committed_engine_arm_completes_a_route_proof_shaped_record_under_isolation_through_the_launcher(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
+) -> None:
+    """Phase 3's route-proof cell against a fake: one Engine cell, k = 1, the committed arm on the record's model,
+    its export checked against its pins, the receipt kept. ``development`` only because the fake ``pi`` is a seam."""
+    _cell_pi(cell_scratch, monkeypatch, "write")
+    engine = _engine_arm(tmp_path, _pinned_export(cell_scratch))
+    record = _frozen_record(tmp_path, "route-proof", arm="engine", n=1, k=1, model="omlx/Ornith-1.5-9B-MLX-8bit")
+    before = _attempt_dirs()
+    assert _launch(record, [engine], tmp_path / "runs") == 0
+    result = _result(record)
+    assert result["status"] == "complete" and [(c["arm"], c["code"], c["verdict"]) for c in result["cells"]] == [
+        ("engine", "OK", "pass")
+    ]
+    receipt = json.loads((tmp_path / "runs" / "route-proof" / "engine" / result["cells"][0]["attempt_dir"] / RECEIPT_NAME).read_text())
+    assert (receipt["code"], receipt["validation"]) == ("OK", "passed")
+    assert set(receipt["guard_firings"]) >= {"scope_refused", "symbol_preserved", "command_bounded"}
+    ledger = json.loads((tmp_path / "runs" / "route-proof" / LEDGER_NAME).read_text())
+    assert ledger["sittings"][0]["preflight"]["tolerated"] == [os.fspath(cell_scratch)]
+    assert _attempt_dirs() <= before
+
+
 def test_a_night_the_wall_clock_stops_resumes_without_rerunning_a_finished_cell(
     tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
 ) -> None:
diff --git a/tests/test_cell_engine.py b/tests/test_cell_engine.py
index eb62f64..1fedb27 100644
--- a/tests/test_cell_engine.py
+++ b/tests/test_cell_engine.py
@@ -1,17 +1,22 @@
-"""``verify_export``'s pure safety checks (F2/R11): no subprocess, no cell.
+"""``verify_export``'s pure safety checks (F2/R11) and an Engine arm's export against its pins: no subprocess, no cell.

 Every refusal has a success sibling over the same shape.
 """

+import hashlib
 import json
+from dataclasses import replace
 from pathlib import Path

 import pytest

+from satyrn_evals.arms import ENGINE_SOURCES, Arm, load_arm
 from satyrn_evals.cell_engine import (
     EXPORT_PATHS,
     EngineExportError,
+    arm_export_problems,
     export_leaks,
+    export_path,
     verify_export,
 )
 from satyrn_evals.hygiene import overlay_digests
@@ -111,3 +116,91 @@ def test_an_export_holding_a_hidden_files_bytes_under_another_name_is_refused(tm
 def test_the_export_allowlist_is_what_the_cell_runs_and_never_tests_or_docs() -> None:
     assert EXPORT_PATHS == ("src", "packages", "pyproject.toml", "uv.lock", "README.md", "LICENSE")
     assert not {"tests", "docs", "tools", "BACKLOG.md", "conftest.py"} & set(EXPORT_PATHS)
+
+
+# --- an Engine arm's export against its pins (launch and launch --preflight) ---
+
+ENGINE_ARM = Path(__file__).resolve().parents[1] / "arms" / "engine-ornith15-9b.json"
+
+
+def _pinned_export(tmp_path: Path) -> tuple[Arm, Path]:
+    """The committed Engine arm, its ``--engine-repo`` pointed at a stand-in export holding the pinned bytes."""
+    committed = load_arm(ENGINE_ARM)
+    commit = committed.pins.engine_commit
+    assert commit is not None
+    export = tmp_path / "cells" / f"engine-{commit}"
+    (export / "packages" / "engine").mkdir(parents=True)
+    for name in ENGINE_SOURCES:
+        (export / "packages" / "engine" / name).write_text(f"// {name}\n")
+    (export / ".satyrn-engine-export").write_text(f"{commit}\n")
+    digests = {name: hashlib.sha256(f"// {name}\n".encode()).hexdigest() for name in ENGINE_SOURCES}
+    arm = replace(
+        committed,
+        argv=("satyrn-evals-attempt-engine", "--engine-repo", str(export)),
+        pins=replace(committed.pins, digests=digests),
+    )
+    return arm, export
+
+
+def test_an_engine_arm_whose_export_is_its_pinned_commit_and_bytes_has_no_problems(tmp_path: Path) -> None:
+    arm, _ = _pinned_export(tmp_path)
+    assert arm_export_problems(arm, cells_root=tmp_path / "cells") == []
+
+
+def test_the_committed_engine_arm_names_the_export_of_its_pinned_commit_under_the_cells_root() -> None:
+    arm = load_arm(ENGINE_ARM)
+    assert arm.pins.engine_commit is not None
+    assert arm.argv[arm.argv.index("--engine-repo") + 1] == str(export_path(arm.pins.engine_commit))
+
+
+def test_a_baseline_arm_has_no_export_to_check(tmp_path: Path) -> None:
+    baseline = load_arm(ENGINE_ARM.parent / "baseline-ornith15-9b.json")
+    assert arm_export_problems(baseline, cells_root=tmp_path / "missing") == []
+
+
+def test_an_engine_arm_naming_no_export_is_a_problem(tmp_path: Path) -> None:
+    arm, _ = _pinned_export(tmp_path)
+    assert arm_export_problems(replace(arm, argv=("satyrn-evals-attempt-engine",)), cells_root=tmp_path / "cells") == [
+        "the engine arm's argv names no --engine-repo export (satyrn-evals cell-engine)"
+    ]
+
+
+def test_an_export_named_for_another_commit_is_a_problem(tmp_path: Path) -> None:
+    arm, export = _pinned_export(tmp_path)
+    other = export.rename(export.with_name("engine-" + "e" * 40))
+    moved = replace(arm, argv=("satyrn-evals-attempt-engine", "--engine-repo", str(other)))
+    assert arm_export_problems(moved, cells_root=tmp_path / "cells") == [
+        f"the engine export {other} is not engine-{arm.pins.engine_commit}, the arm's pinned commit"
+    ]
+
+
+def test_an_export_outside_the_cells_root_is_a_problem(tmp_path: Path) -> None:
+    arm, export = _pinned_export(tmp_path)
+    elsewhere = tmp_path / "elsewhere"
+    assert arm_export_problems(arm, cells_root=elsewhere) == [f"the engine export {export} is not under {elsewhere}"]
+
+
+def test_an_export_whose_marker_names_another_commit_is_a_problem(tmp_path: Path) -> None:
+    arm, export = _pinned_export(tmp_path)
+    (export / ".satyrn-engine-export").write_text("e" * 40 + "\n")
+    assert arm_export_problems(arm, cells_root=tmp_path / "cells") == [
+        f"the engine export {export} holds {'e' * 40}, not the arm's pinned {arm.pins.engine_commit}"
+    ]
+
+
+def test_an_export_whose_source_bytes_differ_from_the_pins_is_a_problem(tmp_path: Path) -> None:
+    arm, export = _pinned_export(tmp_path)
+    (export / "packages" / "engine" / "scope.ts").write_text("// edited\n")
+    (export / "packages" / "engine" / "paths.ts").unlink()
+    assert arm_export_problems(arm, cells_root=tmp_path / "cells") == [
+        f"the engine export {export} has no packages/engine/paths.ts",
+        f"the engine export {export} has packages/engine/scope.ts other than the pinned bytes",
+    ]
+
+
+def test_an_unsafe_export_is_a_problem(tmp_path: Path) -> None:
+    arm, export = _pinned_export(tmp_path)
+    (export / "tests").mkdir()
+    (export / "tests" / "test_doc_caps.py").write_text("x = 1\n")
+    [problem] = arm_export_problems(arm, cells_root=tmp_path / "cells")
+    assert problem.startswith(f"export {export} holds grader material")
diff --git a/tests/test_cell_preflight.py b/tests/test_cell_preflight.py
index 8afba40..8c7cdef 100644
--- a/tests/test_cell_preflight.py
+++ b/tests/test_cell_preflight.py
@@ -279,3 +279,18 @@ def test_preflight_fails_on_a_cell_problem_or_the_test_path_seam(

 def test_the_preflight_module_names_its_runner_default() -> None:
     assert cell_preflight.preflight_cell.__kwdefaults__["run"] is subprocess.run
+
+
+ENGINE_ARM = REPO / "arms" / "engine-ornith15-9b.json"
+
+
+def test_preflight_for_the_engine_arm_checks_its_export(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight([], {"pi_version": "0.85.1"}))
+    record = _record(tmp_path, arm="engine", purpose="route-proof")
+    monkeypatch.setattr(cli_module, "arm_export_problems", lambda arm: [])
+    assert main(["launch", "--preflight", record, "--arm", str(ENGINE_ARM), "--no-hunt"]) == 0
+    monkeypatch.setattr(cli_module, "arm_export_problems", lambda arm: [f"export for {arm.arm} is missing"])
+    assert main(["launch", "--preflight", record, "--arm", str(ENGINE_ARM), "--no-hunt"]) == 1
+    assert "launch preflight FAILED: export for engine is missing" in capsys.readouterr().err
diff --git a/tests/test_launch_record.py b/tests/test_launch_record.py
index 406d495..31efa7e 100644
--- a/tests/test_launch_record.py
+++ b/tests/test_launch_record.py
@@ -6,6 +6,7 @@ from pathlib import Path

 import pytest

+from satyrn_evals.arms import Arm
 from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, CELLS_ROOT
 from satyrn_evals.cell_preflight import CellPreflight
 from satyrn_evals.cli import main
@@ -273,3 +274,53 @@ def test_a_night_directory_of_another_record_is_refused(tmp_path: Path) -> None:
     other.parent.mkdir()
     other.write_text(first.read_text().replace('"k": 1', '"k": 2'))
     assert "belongs to another record" in _refused(tmp_path, other, _facts())
+
+
+# --- the Engine arm: route proof --------------------------------------------
+
+ENGINE_ARM = REPO / "arms" / "engine-ornith15-9b.json"
+ROUTE_PROOF_RULE = "route proof: guards fire where retained Baseline evidence says they should; receipt read"
+
+
+def _route_proof(tmp_path: Path) -> Path:
+    body = new_record(
+        task=TASK, tasks_root=DEFAULT_TASKS_ROOT, arm="engine", model="omlx/Ornith-1.5-9B-MLX-8bit", n=1, k=1,
+        rung="R1", purpose="route-proof", isolation="isolated", mode="attended", max_minutes=60,
+        token_budget=32000, turn_budget=48, previous_result="records/x.result.json", authority="test",
+        decision_rule=ROUTE_PROOF_RULE,
+    )
+    path = tmp_path / "records" / "route-proof.json"
+    write_new_record(path, body)
+    return path
+
+
+def test_a_route_proof_record_runs_the_committed_engine_arm_on_its_export(tmp_path: Path) -> None:
+    seen: list[str] = []
+
+    def export(arm: Arm) -> list[str]:
+        seen.append(arm.arm)
+        return []
+
+    record = _route_proof(tmp_path)
+    assert launch_record(
+        record, [ENGINE_ARM], tasks_root=DEFAULT_TASKS_ROOT, runs_root=tmp_path / "runs",
+        facts=_facts(engine_export=export), poll_interval=0.0, grace=0.0,
+    ) == 3  # the fake spawn raised: interrupted
+    assert seen == ["engine"]
+    spec = json.loads((tmp_path / "runs" / "route-proof" / SLOTS_DIR / "00.spec.json").read_text())
+    commit = "341d4c450317f63e6af8958d45606cb737a131af"
+    assert spec["command"] == [
+        "satyrn-evals-attempt-engine", "--engine-repo", f"/Users/Shared/satyrn-cells/engine-{commit}",
+        "--model", "omlx/Ornith-1.5-9B-MLX-8bit",
+    ]
+    assert (spec["arm"], spec["rung"], spec["isolation"]) == ("engine", "R1", "isolated")
+
+
+def test_an_engine_export_problem_exits_1_and_runs_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
+    facts = _facts(engine_export=lambda arm: ["the engine export /x is not under /Users/Shared/satyrn-cells"])
+    assert launch_record(
+        _route_proof(tmp_path), [ENGINE_ARM], tasks_root=DEFAULT_TASKS_ROOT, runs_root=tmp_path / "runs",
+        facts=facts, poll_interval=0.0, grace=0.0,
+    ) == 1
+    assert "launch FAILED: engine: the engine export /x is not under" in capsys.readouterr().err
+    assert not (tmp_path / "runs").exists()
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `uv run pytest -q tests/test_cell_engine.py tests/test_launch_record.py tests/test_cell_preflight.py`
Expected: collection error, `ImportError: cannot import name 'arm_export_problems' from 'satyrn_evals.cell_engine'`. (With only `tests/test_launch_record.py tests/test_cell_preflight.py`: 3 failed — two `TypeError: LaunchFacts.__init__() got an unexpected keyword argument 'engine_export'`, one `AttributeError` for `cli.arm_export_problems`.)

- [ ] **Step 3: Write the implementation.** Save this block as `$SCR/t3-impl.diff` and run `git apply "$SCR/t3-impl.diff"`:

```diff
diff --git a/src/satyrn_evals/cell_engine.py b/src/satyrn_evals/cell_engine.py
index eafe7e8..fb5c454 100644
--- a/src/satyrn_evals/cell_engine.py
+++ b/src/satyrn_evals/cell_engine.py
@@ -29,6 +29,7 @@ import tarfile
 from collections.abc import Mapping
 from pathlib import Path

+from satyrn_evals.arms import Arm
 from satyrn_evals.cell import CELLS_ROOT, grant_maintainer, share_with_cell
 from satyrn_evals.errors import UsageError
 from satyrn_evals.hygiene import overlay_copies, overlay_digests
@@ -102,6 +103,46 @@ def verify_export(dest: Path, digests: Mapping[str, str] | None = None) -> str:
     return sha


+def arm_export_problems(arm: Arm, cells_root: Path = CELLS_ROOT) -> list[str]:
+    """Why the export an Engine arm's argv names is not the engine the arm pins; empty when it is.
+
+    ``launch`` and ``launch --preflight`` run this before any cell: the arm
+    file names its export (``--engine-repo``), and the pins are claims until
+    the export is checked against them. The export must be
+    ``engine-<engine_commit>`` under ``cells_root``, pass ``verify_export``
+    (maintainer-owned, read-only, a complete marker, no grader material),
+    hold the pinned commit in its marker, and hold every pinned
+    ``packages/engine`` source byte for byte. Other arms have no export.
+    """
+    if arm.arm != "engine":
+        return []
+    argv = list(arm.argv)
+    if "--engine-repo" not in argv[:-1]:
+        return ["the engine arm's argv names no --engine-repo export (satyrn-evals cell-engine)"]
+    export = Path(argv[argv.index("--engine-repo") + 1])
+    if export.name != f"engine-{arm.pins.engine_commit}":
+        return [f"the engine export {export} is not engine-{arm.pins.engine_commit}, the arm's pinned commit"]
+    if not export.resolve().is_relative_to(cells_root.resolve()):
+        return [f"the engine export {export} is not under {cells_root}"]
+    try:
+        sha = verify_export(export)
+    except EngineExportError as exc:
+        return [str(exc)]
+    if sha != arm.pins.engine_commit:
+        return [f"the engine export {export} holds {sha}, not the arm's pinned {arm.pins.engine_commit}"]
+    problems: list[str] = []
+    for name, digest in sorted(arm.pins.digests.items()):
+        source = export / "packages" / "engine" / name
+        try:
+            actual = hashlib.sha256(source.read_bytes()).hexdigest()
+        except OSError:
+            problems.append(f"the engine export {export} has no packages/engine/{name}")
+            continue
+        if actual != digest:
+            problems.append(f"the engine export {export} has packages/engine/{name} other than the pinned bytes")
+    return problems
+
+
 def export_engine(engine_repo: Path, commit: str, *, root: Path = CELLS_ROOT, python: Path = CELL_PYTHON) -> Path:
     """The export directory for ``commit``, made once; an existing safe, complete export is reused."""
     resolved = subprocess.run(
diff --git a/src/satyrn_evals/cli.py b/src/satyrn_evals/cli.py
index 99e610f..19a5429 100644
--- a/src/satyrn_evals/cli.py
+++ b/src/satyrn_evals/cli.py
@@ -15,7 +15,7 @@ from satyrn_evals.budget import AttemptBudget
 from satyrn_evals.capture import capture
 from satyrn_evals.capture_record import CaptureOutcome
 from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, Isolation
-from satyrn_evals.cell_engine import export_engine
+from satyrn_evals.cell_engine import arm_export_problems, export_engine
 from satyrn_evals.cell_preflight import preflight_cell
 from satyrn_evals.census import build_arg_parser as build_census_parser
 from satyrn_evals.census import run_cli as run_census
@@ -300,7 +300,7 @@ def _launch_preflight(args: argparse.Namespace) -> int:
         tasks_root=tasks_root,
         hunt_root=None if args.no_hunt else "/",
     )
-    problems = list(report.problems)
+    problems = [*report.problems, *arm_export_problems(arm)]
     if os.environ.get(CELL_PATH_PREFIX_ENV):
         problems.append(f"{CELL_PATH_PREFIX_ENV} is set; it is a test seam, never a sitting's PATH")
     print(json.dumps({"record": args.preflight, "arm": args.arm[0], "problems": problems, **report.checked}, indent=2))
diff --git a/src/satyrn_evals/launch_record.py b/src/satyrn_evals/launch_record.py
index c434eaf..bd11171 100644
--- a/src/satyrn_evals/launch_record.py
+++ b/src/satyrn_evals/launch_record.py
@@ -11,7 +11,9 @@ The spec's launcher gates ("Process"), in order, before any cell:
 3. ``gate``: the record is frozen (tracked, unchanged against ``HEAD``), the
    previous result is committed, n and wall clock are under the cadence cap,
    and a deciding purpose is isolated;
-4. under isolation, the cell preflight (``cell_preflight.preflight_cell``) is clean;
+4. under isolation, the cell preflight (``cell_preflight.preflight_cell``) is clean,
+   and an Engine arm's export is the commit and bytes it pins
+   (``cell_engine.arm_export_problems``);
 5. ``scripts/preflight_settings.py`` exits 0 for every arm (``--cell`` under
    isolation); its provenance block is kept for the drift check.

@@ -44,6 +46,7 @@ from typing import TextIO
 from satyrn_evals.arms import Arm, build_argv, load_arm
 from satyrn_evals.attempt import resolve_contract
 from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, CELLS_ROOT, Isolation
+from satyrn_evals.cell_engine import arm_export_problems
 from satyrn_evals.cell_preflight import CellPreflight, preflight_cell
 from satyrn_evals.errors import SatyrnError
 from satyrn_evals.launch import (
@@ -129,6 +132,7 @@ class LaunchFacts:
     preflight: Callable[..., CellPreflight] = preflight_cell
     settings: Callable[[Path, bool], tuple[int, str]] = settings_provenance
     spawn_cell: Callable[[Path, Path], CellProcess] = popen_cell
+    engine_export: Callable[[Arm], list[str]] = arm_export_problems


 def _sha256(path: Path) -> str:
@@ -287,6 +291,8 @@ def launch_record(
         )
         problems += report.problems
         checked["preflight"] = report.checked
+        for name, (_, arm) in arms.items():
+            problems += [f"{name}: {problem}" for problem in facts.engine_export(arm)]
     baseline_settings: dict[str, str] = {}
     if settings:
         for name, (path, _) in arms.items():
```

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `uv run pytest -q tests/test_cell_engine.py tests/test_launch_record.py tests/test_cell_preflight.py` → `61 passed`.
Run, serially and with nothing else using the cell user: `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q --basetemp "$SCR/bt" tests/integration/test_launch_record.py tests/integration/test_isolated_arms.py tests/integration/test_cell_isolation.py tests/integration/test_cell_preflight.py tests/integration/test_run_signal.py tests/integration/test_budget_attempt.py tests/integration/test_evidence_run.py tests/integration/test_engine_arm.py tests/integration/test_engine_arm_pins.py; echo "EXIT: $?"; rm -rf "$SCR/bt"; ls -A /Users/Shared/satyrn-cells` → `EXIT: 0` (35 passed, about 50 s) and an empty listing.
Run: `uv run ruff check --fix && just gates; echo "EXIT: $?"` → `EXIT: 0` (default tier 2,071 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/satyrn_evals/cell_engine.py src/satyrn_evals/launch_record.py src/satyrn_evals/cli.py tests/test_cell_engine.py tests/test_launch_record.py tests/test_cell_preflight.py tests/integration/test_launch_record.py tests/integration/test_cell_preflight.py
git commit -m "Phase 3 prep: launch and launch --preflight check an Engine arm's export against its commit and digests; the committed arm completes a route-proof-shaped record under isolation"
```

---

## Operator: the export and the three route-proof cells

Not executed by the controller: the export is the only write to the real cells root, and the launches spend inference. Run from the evals checkout after the three task commits, one record at a time, each launch in the background. A launch exit of 4 means the sitting's 60 minutes capped it: run the same `launch` again until it exits 0. Exit 1, 2 or 3 stops the route proof; report the result's `reason` and the launcher's stderr verbatim. If a preflight names a stale `(mdworker_shared)` cell process, wait a minute and rerun it.

```bash
# 1. The export of the pinned commit (Ruling 8), into the real cells root; the preflight on the first record.
ls -A /Users/Shared/satyrn-cells   # expect nothing, or only engine-341d4c45…; remove any other engine-* export deliberately first
uv run satyrn-evals cell-engine --engine-repo ~/projects/pauleveritt/satyrn-engine --commit 341d4c450317f63e6af8958d45606cb737a131af
# prints /Users/Shared/satyrn-cells/engine-341d4c450317f63e6af8958d45606cb737a131af

# 2. The Engine arm's settings, as the cell.
uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell; echo "EXIT: $?"   # EXIT: 0

AUTH="maintainer: proceed to Phase 3 route proof, 2026-09-15"
RULE="route proof: guards fire where retained Baseline evidence says they should; receipt read"
ARM=arms/engine-ornith15-9b.json

# 3a. agentclinic-repair-depth-3 (R1)
uv run satyrn-evals record new --output records/2026-09-15-route-proof-agentclinic-repair-depth-3.json --task agentclinic-repair-depth-3 --rung R1 --arm engine --n 1 --k 1 --purpose route-proof --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --decision-rule "$RULE" --authority "$AUTH" --previous-result records/2026-09-15-admission-selfhost-docs-linter.result.json
uv run satyrn-evals launch --preflight records/2026-09-15-route-proof-agentclinic-repair-depth-3.json --arm $ARM; echo "EXIT: $?"   # EXIT: 0 and "problems": [] (full hunt, about a minute)
git add records/2026-09-15-route-proof-agentclinic-repair-depth-3.json && git commit -m "Phase 3 route-proof record: agentclinic-repair-depth-3 (Engine at 341d4c4, R1, n=1, k=1, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-route-proof-agentclinic-repair-depth-3.json --arm $ARM; echo "EXIT: $?"
git add records/2026-09-15-route-proof-agentclinic-repair-depth-3.result.json && git commit -m "Phase 3 route-proof result: agentclinic-repair-depth-3 ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-route-proof-agentclinic-repair-depth-3.result.json"))["status"])'))"

# 3b. selfhost-run-record-gate (R1-plan)
uv run satyrn-evals record new --output records/2026-09-15-route-proof-selfhost-run-record-gate.json --task selfhost-run-record-gate --rung R1-plan --arm engine --n 1 --k 1 --purpose route-proof --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --decision-rule "$RULE" --authority "$AUTH" --previous-result records/2026-09-15-route-proof-agentclinic-repair-depth-3.result.json
git add records/2026-09-15-route-proof-selfhost-run-record-gate.json && git commit -m "Phase 3 route-proof record: selfhost-run-record-gate (Engine at 341d4c4, R1-plan, n=1, k=1, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-route-proof-selfhost-run-record-gate.json --arm $ARM; echo "EXIT: $?"
git add records/2026-09-15-route-proof-selfhost-run-record-gate.result.json && git commit -m "Phase 3 route-proof result: selfhost-run-record-gate ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-route-proof-selfhost-run-record-gate.result.json"))["status"])'))"

# 3c. selfhost-docs-linter (R1-plan)
uv run satyrn-evals record new --output records/2026-09-15-route-proof-selfhost-docs-linter.json --task selfhost-docs-linter --rung R1-plan --arm engine --n 1 --k 1 --purpose route-proof --isolation isolated --token-budget 32000 --turn-budget 48 --max-minutes 60 --decision-rule "$RULE" --authority "$AUTH" --previous-result records/2026-09-15-route-proof-selfhost-run-record-gate.result.json
git add records/2026-09-15-route-proof-selfhost-docs-linter.json && git commit -m "Phase 3 route-proof record: selfhost-docs-linter (Engine at 341d4c4, R1-plan, n=1, k=1, 32,000 tokens and 48 turns, isolated; $AUTH)"
uv run satyrn-evals launch records/2026-09-15-route-proof-selfhost-docs-linter.json --arm $ARM; echo "EXIT: $?"
git add records/2026-09-15-route-proof-selfhost-docs-linter.result.json && git commit -m "Phase 3 route-proof result: selfhost-docs-linter ($(python3 -c 'import json; print(json.load(open("records/2026-09-15-route-proof-selfhost-docs-linter.result.json"))["status"])'))"
```

Every launch repeats the cell preflight with the full hunt and the export check (Ruling 6), so records 3b and 3c need no separate `--preflight`. For the reading, each cell's `~/satyrn-runs/2026-09-15-route-proof-<task>/engine/*/` holds `engine-receipt.json` (`code`, `validation`, `validation_output`, `guard_firings`, `carried`), `engine-derive.txt`, `engine-deliver.txt`, `transcript.txt` and the Evals `receipt.json`. The guard firings are read against the retained Baseline admission cells of the same task; validation is read with Ruling 9's observation in mind.

---

## Self-review against the spec and the brief

- **Export leak** (brief 1): allowlist in T2 (`EXPORT_PATHS`; Ruling 1 with the README/LICENSE/dev-group verification). The export check reuses `hygiene.overlay_digests` by basename and digest, both when the export is made and in `verify_export` (T2, Ruling 2). The launch and preflight check is T3 (Ruling 6). The 2b/2c parked guard is closed.
- **Engine arm file** (brief 2): `ENGINE_SOURCES` is seven (T1, Ruling 3, checked against the engine checkout). The tool naming agrees between adapter and loader (`ENGINE_TOOLS`, Ruling 4). `arms/engine-ornith15-9b.json` holds the full sha, seven digests, argv `satyrn-evals-attempt-engine` with its export, and Baseline Ornith's `inference` (Ruling 5). `preflight_settings --cell` gave exit 0.
- **Route-proof records through `launch`** (brief 3): `record new --purpose route-proof --arm engine --n 1 --k 1 --decision-rule …` writes all three records (verified in scratch). A default-tier row takes a route-proof record with the committed arm to its first cell with the right command. An integration row runs the committed arm, export path aside, through `launch` under isolation to `complete`, receipt `OK`/`passed`, with a real export of `341d4c4` present under the cells root (T3, Ruling 7). The hunt as the cell over that export is silent, and `arm_export_problems` passes it.
- **Last step**: the operator section runs the three brief items in order, by full sha (Ruling 8).
- **Placeholders**: none. Names are consistent across tasks: `ENGINE_TOOLS`, `ENGINE_SOURCES`, `EXPORT_PATHS`, `export_leaks`, `verify_export(dest, digests)`, `arm_export_problems(arm, cells_root)`, `LaunchFacts.engine_export`.

## Test verification (plan review, 2026-09-15)

Every test this plan specifies was run in a scratch clone of evals `release-one` at `f966016` (`.../scratchpad/engine-arm-plan/clone`, never the main checkout), with no inference. A prototype was committed there as `p1`, `p2` and `p3`; every diff block above was extracted from those commits, trailing whitespace stripped for the docs lint.

- **Before each task, its new tests fail for the missing implementation only**: T1 `ImportError` for `ENGINE_TOOLS`; T2 `ImportError` for `EXPORT_PATHS`; T3 `ImportError` for `arm_export_problems` (and, without `test_cell_engine.py`, 3 failed on `LaunchFacts(engine_export=)` and `cli.arm_export_problems`).
- **After each task**: T1 `tests/test_arms.py tests/test_interleave.py` 49 passed; `test_engine_arm_pins.py` 3 passed; `preflight_settings.py arms/engine-ornith15-9b.json --cell` EXIT 0 (the Baseline Ornith arm also 0); `just gates` EXIT 0, default tier 2,055 passed. T2 `test_cell_engine.py` 10 passed; `test_engine_arm_pins.py` and `test_isolated_arms.py` 10 passed; `just gates` EXIT 0, 2,059 passed. T3 61 passed across the three default-tier files; the nine integration files 35 passed in 46 s; `just gates` EXIT 0, 2,071 passed. `/Users/Shared/satyrn-cells` was empty after every run.
- **The operator's record commands**: the three `record new` commands, with the chained `--previous-result`, each exited 0 into scratch, and those files were then deleted. `launch --preflight` on the depth-3 record with the committed arm and no export exits 1, naming `cannot stat export /Users/Shared/satyrn-cells/engine-341d4c45…`, which is Ruling 6 firing before the operator's export.
- **The plan text reproduces the commits**: the six diff blocks, extracted from this file and applied with `git apply` in order on a fresh clone at `f966016` with Task 1's `provenance.py new`, give a tree identical to `p3`.

Found by running the draft, and fixed here. The 341d4c4 export without `README.md` fails `uv sync` (Ruling 1). `--no-dev` made the isolated Engine row's receipt `TESTS_FAILED` (`No module named pytest` from the export's `.venv`), so the dev group stays (Rulings 1, 9). `tests/test_interleave.py::test_arms_that_do_not_agree_on_the_model_are_refused` built its refused file from a four-digest `read,edit` Engine arm, which the new loader refuses for the tools before the schedule can refuse the model; it now starts from the committed arm, so the refusal is the model's again. 2c's integration Engine arm carried `"0" * 40` pins, which Task 3's export check refuses; it is now the committed arm with its export path changed.
