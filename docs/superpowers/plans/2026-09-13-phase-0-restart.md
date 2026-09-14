# Phase 0 — Restart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two lean trees — `satyrn-evals` and `satyrn-engine` — on orphan branches, holding only what the release-one design imports, with every file's source recorded, the default test tiers green, and the pacing gates (launcher record check, docs caps, review script, hooks) enforced by `just gates`.

**Architecture:** Both `main`s are tagged and left untouched. Each repo gets an orphan branch `release-one` in a worktree at `.claude/worktrees/release-one`; nothing arrives by default — every imported file is `git checkout <tag> -- path` and is recorded in `PROVENANCE.md`. New code in this phase is small and pure: a provenance recorder, a rewritten docs linter, a run-record gate, a review script's pure core, and a Claude Code hook script. Sphinx does not come over; docs are Markdown checked by the linter.

**Tech Stack:** Python 3.14, uv, pytest (hermetic default tier, `integration` marker), ruff, just, git 2.45, Node 22+ (`--experimental-strip-types`) for the engine's TypeScript tests, Claude Code hooks (`.claude/settings.json`).

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` (committed on `main` as `8633149`; imported into the new tree in Task 6).

## Global Constraints

- Python `>=3.14,<3.15`; runtime dependency `pyyaml` only; dev group `pytest`, `pytest-cov`, `ruff`, `pyrefly`.
- Default test tier: **no model, no network, no subprocess**. `tests/conftest.py`'s autouse tripwire enforces it; it is imported first and never weakened. Anything spawning a process is `@pytest.mark.integration`.
- Every refusal test has a sibling success test.
- Never `grep -c`/`-o` to count events; never pipe a gate into anything — read its exit code.
- No inference, anywhere in this phase. No merge to either `main`. No push.
- Old worktrees (`overnight-phase4-context`, `sdd-prompt-delivery`, `baseline-user-stories-n4`) and the running Ornith probe worktree are **not touched**.
- Imported files are imported **unchanged** except where a task names the edit; a test that references a dropped module or task is **deleted**, never rewritten to pass. A test that enumerates the task fleet has its expected set reduced to the kept tasks — that is the only permitted assertion change.
- Commit at the end of every task, on the `release-one` branch of the tree being worked in, with the plan's commit message. Never `--amend`.
- Tag name for both repos: `pre-release-one-2026-09-13`. Evals source revision: the tag (`main` at `8633149`). Engine source revision: the tag (`main` at `1ea478c`).

---

## File structure of the new `satyrn-evals` tree

```
LICENSE  .gitignore  .gitattributes  pyproject.toml  uv.lock  conftest.py  Justfile
README.md  BRIEF.md  AGENTS.md  ROADMAP.md  PROVENANCE.md
.claude/settings.json                     # hooks (Task 10)
src/satyrn_evals/                         # core, adapters/pi_session.py, packet.py, census.py (edited), run_record.py (new)
src/satyrn_evals/tasks/{agentclinic-repair-misleading-locus,agentclinic-complaint-lifecycle,format_number}/
arms/{baseline.json,baseline-ornith15-9b.json,baseline-26b.json}
scripts/{interleave.py,preflight.sh,preflight_commands.py,preflight_inference.py,preflight_models.py,preflight_processes.py,tally.py,usage_totals.py,power.py,timing.py,token_floor.py}
tools/{lint_docs.py (rewritten),provenance.py (new),review.py (new),agentclinic_gate.sh,reconstruct_agentclinic.py,hooks/guard.py (new)}
tests/  tests/integration/  tests/data/{v10,overlay-task,real-session-phased-verify-transcript.jsonl}  tests/integration/data/{mini-session,mini-session-divergent}
docs/pathologies.md  docs/remediations.md  docs/lessons.md
docs/superpowers/specs/2026-09-13-release-one-design.md  docs/superpowers/plans/2026-09-13-phase-0-restart.md
docs/results/.gitkeep  docs/reviews/.gitkeep
```

## File structure of the new `satyrn-engine` tree

```
LICENSE  .gitignore  pyproject.toml  uv.lock  conftest.py  Justfile  README.md  BRIEF.md  AGENTS.md  PROVENANCE.md
src/satyrn_engine/*.py                    # all eleven; delivery.py edited to drop deliver_chain
packages/engine/{engine.ts,mutator.ts,orchestrator.ts,runner.ts,package.json}
tests/  tests/fixtures/                   # minus *chain*
tools/{lint_docs.py,provenance.py,replay_guards.mjs,replay_orchestrator.mjs,exercise_mutator.mjs,exercise_runner.mjs}
docs/{glossary.md,usage.md}
```

---

### Task 1: Tags, orphan worktrees, and the provenance recorder

**Files:**
- Create (evals tree): `PROVENANCE.md`, `tools/provenance.py`, `tests/test_provenance.py`, `LICENSE`, `.gitignore`, `.gitattributes`
- Create (engine tree): `PROVENANCE.md`, `tools/provenance.py`, `LICENSE`, `.gitignore`

**Interfaces:**
- Produces: `tools/provenance.py record --sha SHA PATH...` appends one table row per path to `PROVENANCE.md`; `tools/provenance.py new PATH...` records a file created in this tree; `provenance.check(root: Path) -> list[str]` returns paths under `src/`, `tests/`, `scripts/`, `tools/`, `arms/`, `docs/` and root `*.md`/`*.toml`/`Justfile` that have no provenance row.

- [ ] **Step 1: Tag both mains and verify the trees are clean**

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
git status --porcelain            # must print only the two known uncommitted lines: docs/current/index.md and the ornith brief
git rev-parse HEAD                # expect 8633149...
git tag -a pre-release-one-2026-09-13 -m "Everything before the release-one restart; evidence, not guidance" HEAD
cd /Users/pauleveritt/projects/pauleveritt/satyrn-engine
git status --porcelain            # must be empty; if not, STOP and report
git rev-parse HEAD                # expect 1ea478c...
git tag -a pre-release-one-2026-09-13 -m "Everything before the release-one restart; evidence, not guidance" HEAD
```

- [ ] **Step 2: Create the orphan worktrees**

```bash
cd /Users/pauleveritt/projects/pauleveritt/satyrn-evals
git worktree add --orphan -b release-one .claude/worktrees/release-one
cd /Users/pauleveritt/projects/pauleveritt/satyrn-engine
git worktree add --orphan -b release-one .claude/worktrees/release-one
```

Verify each: `git -C <worktree> status --porcelain` is empty and `ls -A <worktree>` shows only `.git`. `.claude/worktrees/` is already ignored in evals (`.git/info/exclude:11`); in the engine, add `.claude/worktrees/` to `.git/info/exclude` (not to the tracked `.gitignore`).

- [ ] **Step 3: Write the failing test for the recorder (evals tree)**

Work in `/Users/pauleveritt/projects/pauleveritt/satyrn-evals/.claude/worktrees/release-one` from here on unless a step says otherwise. Create `tests/test_provenance.py`:

```python
from pathlib import Path

import pytest

from tools.provenance import check, record_imported, record_new

SHA = "8633149" + "0" * 33


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "b.py").write_text("y = 2\n")
    (tmp_path / "PROVENANCE.md").write_text("# Provenance\n\n| path | source |\n|---|---|\n")
    return tmp_path


def test_recording_an_import_writes_one_row_per_path(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    text = (root / "PROVENANCE.md").read_text()
    assert f"| src/pkg/a.py | pre-release-one-2026-09-13 @ {SHA} |" in text


def test_recording_a_new_file_names_this_tree_as_the_source(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_new(root, ["tools/b.py"])
    assert "| tools/b.py | created in release-one |" in (root / "PROVENANCE.md").read_text()


def test_check_names_every_tracked_shape_of_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    assert check(root) == ["tools/b.py"]


def test_check_is_empty_when_every_file_has_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    assert check(root) == []


def test_recording_a_path_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    with pytest.raises(FileNotFoundError):
        record_imported(root, SHA, ["src/pkg/missing.py"])
```

Also create `tests/__init__.py`? No — the existing repo uses a bare `tests/` directory with `conftest.py`; `tools` is importable because the test runs from the repo root and `conftest.py` at root exists. Create root `conftest.py` now with the exact text of the tagged one:

```bash
git checkout pre-release-one-2026-09-13 -- conftest.py LICENSE .gitignore .gitattributes tests/conftest.py tests/test_tripwire.py
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run --with pytest pytest tests/test_provenance.py -q` (no `pyproject.toml` yet, so `--with pytest`)
Expected: FAIL with `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 5: Write the recorder**

Create `tools/__init__.py` (empty) and `tools/provenance.py`:

```python
"""Record where every file in this tree came from.

The release-one trees start empty. A file arrives only by an explicit
`git checkout <tag> -- path` or by being written here, and either way it
gets one row in PROVENANCE.md. `check` names any file that has neither.
No model, no network, no subprocess.
"""

import sys
from pathlib import Path

TAG = "pre-release-one-2026-09-13"
TRACKED_DIRS = ("src", "tests", "scripts", "tools", "arms", "docs")
TRACKED_ROOT_SUFFIXES = (".md", ".toml", ".py")
TRACKED_ROOT_NAMES = ("Justfile", "LICENSE", ".gitignore", ".gitattributes")
SKIP_PARTS = frozenset({"__pycache__", ".venv", "node_modules", "_build", ".pytest_cache", ".ruff_cache"})
SKIP_SUFFIXES = frozenset({".pyc"})
HEADER = "# Provenance\n\n| path | source |\n|---|---|\n"


def _rows_file(root: Path) -> Path:
    path = root / "PROVENANCE.md"
    if not path.exists():
        path.write_text(HEADER)
    return path


def _append(root: Path, paths: list[str], source: str) -> None:
    for rel in paths:
        if not (root / rel).exists():
            raise FileNotFoundError(rel)
    with _rows_file(root).open("a") as handle:
        for rel in paths:
            handle.write(f"| {rel} | {source} |\n")


def record_imported(root: Path, sha: str, paths: list[str]) -> None:
    _append(root, paths, f"{TAG} @ {sha}")


def record_new(root: Path, paths: list[str]) -> None:
    _append(root, paths, "created in release-one")


def recorded(root: Path) -> set[str]:
    rows = set()
    for line in _rows_file(root).read_text().splitlines():
        if line.startswith("| ") and not line.startswith("| path ") and not line.startswith("|---"):
            rows.add(line.split("|")[1].strip())
    return rows


def tracked(root: Path) -> list[str]:
    files: list[str] = []
    for directory in TRACKED_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(p in SKIP_PARTS for p in path.parts) or path.suffix in SKIP_SUFFIXES:
                continue
            files.append(path.relative_to(root).as_posix())
    for path in sorted(root.iterdir()):
        if path.is_file() and (path.suffix in TRACKED_ROOT_SUFFIXES or path.name in TRACKED_ROOT_NAMES):
            if path.name != "PROVENANCE.md":
                files.append(path.name)
    return files


def check(root: Path) -> list[str]:
    have = recorded(root)
    return [rel for rel in tracked(root) if rel not in have]


def main(argv: list[str]) -> int:
    root = Path.cwd()
    match argv:
        case ["record", "--sha", sha, *paths] if paths:
            record_imported(root, sha, paths)
        case ["new", *paths] if paths:
            record_new(root, paths)
        case ["check"]:
            missing = check(root)
            for rel in missing:
                print(f"no provenance: {rel}")
            return 1 if missing else 0
        case _:
            print("usage: provenance.py record --sha SHA PATH... | new PATH... | check", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_provenance.py -q`
Expected: 5 passed

- [ ] **Step 7: Record what exists so far, in both trees**

Evals tree:

```bash
SHA=$(git rev-parse pre-release-one-2026-09-13^{commit})
uv run --with pytest python tools/provenance.py record --sha "$SHA" conftest.py LICENSE .gitignore .gitattributes tests/conftest.py tests/test_tripwire.py
uv run --with pytest python tools/provenance.py new tools/__init__.py tools/provenance.py tests/test_provenance.py
uv run --with pytest python tools/provenance.py check; echo "EXIT: $?"    # expect EXIT: 0
```

Engine tree (`/Users/pauleveritt/projects/pauleveritt/satyrn-engine/.claude/worktrees/release-one`):

```bash
git checkout pre-release-one-2026-09-13 -- LICENSE .gitignore conftest.py tests/conftest.py
mkdir -p tools && cp /Users/pauleveritt/projects/pauleveritt/satyrn-evals/.claude/worktrees/release-one/tools/provenance.py tools/provenance.py && touch tools/__init__.py
SHA=$(git rev-parse pre-release-one-2026-09-13^{commit})
python3 tools/provenance.py record --sha "$SHA" LICENSE .gitignore conftest.py tests/conftest.py
python3 tools/provenance.py new tools/__init__.py tools/provenance.py
python3 tools/provenance.py check; echo "EXIT: $?"    # expect EXIT: 0
```

- [ ] **Step 8: Commit in both trees**

Evals: `git add -A && git commit -m "Phase 0: orphan tree, tripwire, and the provenance recorder"`.
Engine: `git add -A && git commit -m "Phase 0: orphan tree, tripwire, and the provenance recorder"`.
Then `git status --short` in each — empty.

---

### Task 2: Evals root scaffold — `pyproject.toml`, `Justfile`, lock

**Files:**
- Create: `pyproject.toml`, `Justfile`, `uv.lock`, `README.md`
- Modify: `PROVENANCE.md` (via the recorder)

**Interfaces:**
- Produces: `uv sync` succeeds; `just gates` runs `uv run pytest -q`, `uv run ruff check`, `just lint-docs`; console scripts `satyrn-evals`, `satyrn-evals-session-pi`, `satyrn-evals-attempt-pi`.

- [ ] **Step 1: Import `pyproject.toml` and edit it**

```bash
git checkout pre-release-one-2026-09-13 -- pyproject.toml
```

Edit `pyproject.toml`: under `[project.scripts]` delete the `satyrn-evals-implementer-pi` line and its comment; delete the entire `docs = [...]` and `integration = [...]` dependency groups and the comment block above `integration`; in `[tool.pytest.ini_options]` replace `norecursedirs` with:

```toml
norecursedirs = [".claude", "src/satyrn_evals/tasks", "tests/data", "tests/integration/data"]
```

Leave `addopts`, `markers`, `[tool.ruff*]`, `[tool.pyrefly]`, `[tool.coverage.*]` exactly as imported.

- [ ] **Step 2: Write the Justfile**

```make
# Every gate, in order, failing on the first non-zero exit. Never pipe a
# gate into anything: a check whose exit code is not read cannot fail.
gates:
    uv run pytest -q
    uv run ruff check
    just lint-docs
    uv run python tools/provenance.py check

# Document caps and whitespace (tools/lint_docs.py). No model, network, or subprocess.
lint-docs:
    uv run python tools/lint_docs.py

# The marked tier: real Git, task materialization, oracle execution. Not in CI.
integration:
    uv run pytest -m integration -q
```

- [ ] **Step 3: Write a placeholder-free `README.md`**

```markdown
# Satyrn Evals — release one

Proves, from retained evidence, whether the Satyrn engine keeps a small local
model on track better than bare Pi. Start with `BRIEF.md`, then `ROADMAP.md`,
then `docs/superpowers/specs/2026-09-13-release-one-design.md`.

    uv sync
    just gates

Everything before this tree is tagged `pre-release-one-2026-09-13` on `main`.
It is evidence, not guidance; `PROVENANCE.md` names where each file here came from.
```

- [ ] **Step 4: Sync and verify**

```bash
uv sync
uv run python -c "import satyrn_evals" ; echo "EXIT: $?"      # expect a ModuleNotFoundError message and EXIT: 1 — src is not imported yet; that is correct for this task
uv run pytest tests/test_provenance.py tests/test_tripwire.py -q   # expect all passed
```

(`test_tripwire.py` proves the planted spawn is blocked; if it errors on import, the root `conftest.py` did not come over — re-run Task 1 Step 3's checkout.)

- [ ] **Step 5: Record and commit**

```bash
uv run python tools/provenance.py record --sha "$(git rev-parse pre-release-one-2026-09-13^{commit})" pyproject.toml
uv run python tools/provenance.py new Justfile README.md uv.lock
uv run python tools/provenance.py check; echo "EXIT: $?"
git add -A && git commit -m "Phase 0: pyproject, Justfile and lock for the lean tree"
```

---

### Task 3: Evals core source and its default-tier tests

**Files:**
- Create (import): the `src/satyrn_evals/*.py` and `src/satyrn_evals/adapters/*.py` listed in Step 1; `tests/test_*.py` listed in Step 3; `tests/data/v10/`, `tests/data/overlay-task/`, `tests/data/real-session-phased-verify-transcript.jsonl`
- Modify: `src/satyrn_evals/census.py` (drop the implementer-transcript discovery)

**Interfaces:**
- Produces: `import satyrn_evals.<module>` for every kept module; `satyrn-evals --help` lists `grade capture attempt run summarize regrade session census`.

- [ ] **Step 1: Import the core**

```bash
TAG=pre-release-one-2026-09-13
git checkout $TAG -- \
  src/satyrn_evals/__init__.py src/satyrn_evals/adapter_process.py src/satyrn_evals/arms.py \
  src/satyrn_evals/attempt.py src/satyrn_evals/attempt_pi.py src/satyrn_evals/attempt_record.py \
  src/satyrn_evals/capture.py src/satyrn_evals/capture_record.py src/satyrn_evals/census.py \
  src/satyrn_evals/cli.py src/satyrn_evals/contamination.py src/satyrn_evals/deadline.py \
  src/satyrn_evals/diff_filter.py src/satyrn_evals/discriminating.py src/satyrn_evals/engine_contract.py \
  src/satyrn_evals/errors.py src/satyrn_evals/grade.py src/satyrn_evals/manifest.py \
  src/satyrn_evals/model_error.py src/satyrn_evals/oracle_hook.py src/satyrn_evals/overlay.py \
  src/satyrn_evals/packet.py src/satyrn_evals/patch.py src/satyrn_evals/pathology.py \
  src/satyrn_evals/receipt.py src/satyrn_evals/repeat_limit.py src/satyrn_evals/rescore.py \
  src/satyrn_evals/run.py src/satyrn_evals/session.py src/satyrn_evals/session_grader.py \
  src/satyrn_evals/session_manifest.py src/satyrn_evals/session_patch.py src/satyrn_evals/session_protocol.py \
  src/satyrn_evals/session_record.py src/satyrn_evals/session_repeat_limit.py src/satyrn_evals/summary.py \
  src/satyrn_evals/taskenv.py src/satyrn_evals/turn_ledger.py src/satyrn_evals/verdict.py \
  src/satyrn_evals/workspace.py src/satyrn_evals/adapters/__init__.py src/satyrn_evals/adapters/pi_session.py
```

Not imported, by design: `attribution.py`, `chain_record.py`, `claim_closeout.py`, `claim_inventory.py`, `claim_measures.py`, `engine_evidence.py`, `live_grading.py`, `phase_ledger.py`, `route.py`, `adapters/engine_delivery.py`, `adapters/pi_implementer.py`, `adapters/self_test_tool*.ts`.

- [ ] **Step 2: Remove `census.py`'s dependency on the dropped implementer adapter**

Run `grep -n "pi_implementer\|implementer" src/satyrn_evals/census.py`. Delete the `from satyrn_evals.adapters.pi_implementer import ...` line and every function or branch whose only purpose is to discover or read the packet route's `.satyrn-implementer-transcript.jsonl` (the names the grep returns). `census` must still discover `transcript.jsonl` under a run root and count the `pathology` module's measures. Then `uv run python -c "import satyrn_evals.census, satyrn_evals.cli"` — exit 0.

- [ ] **Step 3: Import the default-tier tests for kept modules and the fixtures they read**

```bash
git checkout $TAG -- \
  tests/test_adapter_process_errors.py tests/test_agentclinic_manifests.py tests/test_agentclinic_reconstruction.py \
  tests/test_arms.py tests/test_attempt.py tests/test_attempt_pi.py tests/test_attempt_record.py \
  tests/test_capture_failures.py tests/test_capture_logic.py tests/test_capture_record.py tests/test_census.py \
  tests/test_cli.py tests/test_cli_session.py tests/test_contamination.py tests/test_deadline.py \
  tests/test_declared_scope_against_enforced.py tests/test_diff_filter.py tests/test_discriminating.py \
  tests/test_engine_contract.py tests/test_grade_git_env.py tests/test_grade_shim.py tests/test_interleave.py \
  tests/test_manifest.py tests/test_manifest_source_dirs.py tests/test_model_error.py tests/test_oracle_hook.py \
  tests/test_overlay.py tests/test_packet.py tests/test_packet_build.py tests/test_packet_render.py \
  tests/test_patch.py tests/test_pathology.py tests/test_pi_session_driver.py tests/test_pi_session_mapping.py \
  tests/test_pi_session_tool_boundary.py tests/test_receipt.py tests/test_repeat_limit.py tests/test_rescore.py \
  tests/test_run.py tests/test_rung_ladder.py tests/test_session_manifest.py \
  tests/test_session_preservation_per_checkpoint.py tests/test_session_protocol.py tests/test_session_record.py \
  tests/test_session_repeat_limit.py tests/test_summary.py tests/test_tally.py tests/test_taskenv.py \
  tests/test_timing.py tests/test_token_floor.py tests/test_toolchain.py tests/test_turn_ledger.py \
  tests/test_usage_totals.py tests/test_verdict.py tests/test_workspace.py tests/test_workspace_failures.py \
  tests/test_writable_paths_declaration.py \
  tests/data/v10 tests/data/overlay-task tests/data/real-session-phased-verify-transcript.jsonl
```

Not imported: `test_attribution_*.py`, `test_chain_record.py`, `test_claim_*.py`, `test_doc_caps.py` (rewritten in Task 7), `test_engine_delivery.py`, `test_engine_evidence.py`, `test_gap_register.py`, `test_hp4_creation_witness.py`, `test_local_pings_manifest.py`, `test_packet_golden.py` (its golden was built from a dropped task; Phase 1 re-goldens the contract), `test_phase_ledger.py`, `test_pi_implementer.py`, `test_power.py`/`test_preflight_*.py` (Task 5, with their scripts), `test_publish_gate.py`, `test_reconcile_claims.py`, `test_route.py`, `test_route_observer.py`, `test_session_mechanics_fixture.py`, and the golden JSON files under `tests/data/`.

- [ ] **Step 4: Run the default tier and read the failures**

Run: `uv run pytest -q 2>&1 | tail -40` is **not** allowed as the gate; run `uv run pytest -q > /tmp/p0-t3.log 2>&1; echo "EXIT: $?"` and read the file.

Expected failures fall in exactly three classes; anything else is a stop-and-report:

1. `ModuleNotFoundError` for a dropped module inside a kept test file → delete that test function (or the whole file if every test needs it). Find them: `grep -ln "satyrn_evals.route\|satyrn_evals.attribution\|pi_implementer\|claim_\|phase_ledger\|chain_record" tests/test_*.py`.
2. Fleet enumerations: `test_agentclinic_manifests.py`, `test_agentclinic_reconstruction.py`, `test_rung_ladder.py`, `test_writable_paths_declaration.py`, `test_census.py` reference tasks not yet present. **Do not fix these here**; they pass after Task 4 imports the tasks. Mark nothing; leave them red until Task 4.
3. `tests/test_census.py` tests that exercise the deleted implementer discovery → delete those test functions only.

- [ ] **Step 5: Verify every test not in class 2 passes**

Run: `uv run pytest -q --deselect tests/test_agentclinic_manifests.py --deselect tests/test_agentclinic_reconstruction.py --deselect tests/test_rung_ladder.py --deselect tests/test_writable_paths_declaration.py > /tmp/p0-t3b.log 2>&1; echo "EXIT: $?"`
Expected: `EXIT: 0`. Also `uv run ruff check; echo "EXIT: $?"` → 0 (fix import-order fallout from the census edit with `uv run ruff check --fix` only for `I` rules).

- [ ] **Step 6: Record and commit**

```bash
SHA=$(git rev-parse pre-release-one-2026-09-13^{commit})
git status --porcelain | awk '{print $2}' | grep -v PROVENANCE.md | xargs uv run python tools/provenance.py record --sha "$SHA"
uv run python tools/provenance.py check; echo "EXIT: $?"
git add -A && git commit -m "Phase 0: import the evals core and its default-tier tests; census no longer reads the implementer route"
```

(`census.py` is recorded as imported even though edited; Step 2's edit is the recorded exception in this plan.)

---

### Task 4: The three tasks, their gate, and their integration tests

**Files:**
- Create (import): `src/satyrn_evals/tasks/agentclinic-repair-misleading-locus/`, `src/satyrn_evals/tasks/agentclinic-complaint-lifecycle/`, `src/satyrn_evals/tasks/format_number/`, `tools/agentclinic_gate.sh`, `tools/reconstruct_agentclinic.py`, the integration tests and fakes in Step 2, `tests/integration/data/`
- Modify: the fleet tests named in Task 3 Step 4 class 2 (expected set reduced to the kept tasks); `tools/agentclinic_gate.sh` (comment only)

**Interfaces:**
- Produces: `resolve_task("agentclinic-repair-misleading-locus")`, `resolve_task("agentclinic-complaint-lifecycle")`, `resolve_task("format_number")` succeed; `just integration` runs the qualification rows for both workloads.

- [ ] **Step 1: Import the tasks and task tooling**

```bash
git checkout $TAG -- \
  src/satyrn_evals/tasks/agentclinic-repair-misleading-locus \
  src/satyrn_evals/tasks/agentclinic-complaint-lifecycle \
  src/satyrn_evals/tasks/format_number \
  tools/agentclinic_gate.sh tools/reconstruct_agentclinic.py
```

`format_number` is the grader fixture (`grade` accepts its known-good and rejects its known-broken); it is not a workload.

- [ ] **Step 2: Import the integration tier for kept modules**

```bash
git checkout $TAG -- \
  tests/integration/__init__.py tests/integration/fake_attempt.py tests/integration/fake_attempt_looping.py \
  tests/integration/fake_attempt_slow.py tests/integration/fake_pi_rpc.py tests/integration/fake_pi_v4.py \
  tests/integration/fake_session_adapter.py tests/integration/workspace_probe.py \
  tests/integration/test_adapter_process.py tests/integration/test_agentclinic_fixtures_apply.py \
  tests/integration/test_agentclinic_gate.py tests/integration/test_attempt.py tests/integration/test_attempt_pi.py \
  tests/integration/test_attempt_runtime_isolation.py tests/integration/test_bundled.py tests/integration/test_capture.py \
  tests/integration/test_complaint_lifecycle_qualification.py tests/integration/test_engine_contract_check.py \
  tests/integration/test_grade.py tests/integration/test_grade_git_env.py tests/integration/test_grade_materialized_env.py \
  tests/integration/test_grade_overlay.py tests/integration/test_grade_preservation_auto_overlay.py \
  tests/integration/test_grade_shim.py tests/integration/test_model_error_attempt.py \
  tests/integration/test_pi_session_four_prompts.py tests/integration/test_repeat_limit_attempt.py \
  tests/integration/test_repeat_limit_replay.py tests/integration/test_rescore.py tests/integration/test_run.py \
  tests/integration/test_run_signal.py tests/integration/test_session_capture_delta.py tests/integration/test_session_cli.py \
  tests/integration/test_session_grading.py tests/integration/test_session_patch.py \
  tests/integration/test_session_repeat_limit_replay.py tests/integration/test_session_run.py \
  tests/integration/test_session_workspace.py tests/integration/test_workspace.py \
  tests/integration/data/mini-session tests/integration/data/mini-session-divergent
```

Not imported: `fake_first_milestone_executor.py`, `fake_implementer.py`, `test_claim_measures_retained.py`, `test_engine_delivery.py`, `test_first_milestone_route.py`, `test_hp2_route.py`, `test_hp6_chain_record.py`, `test_live_grading.py`, `test_local_pings_bundled.py`, `test_phase_ledger_retained.py`, `test_pi_implementer_ordering.py`, `test_session_mechanics_fixture.py`, `test_session_ordering_regression_*.py`, `test_session_phased_qualification.py`.

- [ ] **Step 3: Reduce the fleet enumerations to the kept tasks**

In each of `tests/test_agentclinic_manifests.py`, `tests/test_agentclinic_reconstruction.py`, `tests/test_rung_ladder.py`, `tests/test_writable_paths_declaration.py`, `tests/integration/test_agentclinic_fixtures_apply.py`, `tests/integration/test_agentclinic_gate.py`, `tests/integration/test_bundled.py`: find the literal list or parametrization of task names (`grep -n "agentclinic-repair-depth\|framing-2\|plausible-wrong-fix\|session-phased\|phase2-guardrail\|local-pings\|session-mechanics\|session-ordering" <file>`) and delete the entries for tasks not present. Where a test asserts a count (e.g. "14 shipped tasks"), set it to the count of directories under `src/satyrn_evals/tasks/` (3). No other assertion changes. Update `tools/agentclinic_gate.sh`'s comment from "all six tasks" to "the kept tasks".

- [ ] **Step 4: Default tier green**

Run: `uv run pytest -q > /tmp/p0-t4.log 2>&1; echo "EXIT: $?"` → `EXIT: 0`. `uv run ruff check; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Integration tier green for the kept tasks**

Run: `uv run pytest -m integration -q > /tmp/p0-t4i.log 2>&1; echo "EXIT: $?"`. Expected `EXIT: 0`. Known acceptable exception: if `tests/integration/test_engine_contract_check.py` needs a `satyrn-engine` executable on `PATH` and skips or fails for that reason only, record it in the commit message as "needs the engine tree on PATH; re-run after Task 11" and continue. Any other failure: stop and report.

- [ ] **Step 6: Record and commit**

```bash
SHA=$(git rev-parse pre-release-one-2026-09-13^{commit})
git status --porcelain | awk '{print $2}' | grep -v PROVENANCE.md | xargs uv run python tools/provenance.py record --sha "$SHA"
uv run python tools/provenance.py check; echo "EXIT: $?"
git add -A && git commit -m "Phase 0: the two workloads, the grader fixture, and the integration tier"
```

Note: `git status --porcelain` lists directories for untracked trees; the recorder needs files. If `xargs` receives a directory, expand with `git status --porcelain --untracked-files=all` instead.

---

### Task 5: Arms and the measurement scripts

**Files:**
- Create (import): `arms/baseline.json`, `arms/baseline-ornith15-9b.json`, `arms/baseline-26b.json`, `scripts/interleave.py`, `scripts/preflight.sh`, `scripts/preflight_commands.py`, `scripts/preflight_inference.py`, `scripts/preflight_models.py`, `scripts/preflight_processes.py`, `scripts/tally.py`, `scripts/usage_totals.py`, `scripts/power.py`, `scripts/timing.py`, `scripts/token_floor.py`, `tests/test_power.py`, `tests/test_preflight_commands.py`, `tests/test_preflight_inference.py`, `tests/test_preflight_models.py`, `tests/test_preflight_processes.py`

- [ ] **Step 1: Import**

```bash
git checkout $TAG -- arms/baseline.json arms/baseline-ornith15-9b.json arms/baseline-26b.json \
  scripts/interleave.py scripts/preflight.sh scripts/preflight_commands.py scripts/preflight_inference.py \
  scripts/preflight_models.py scripts/preflight_processes.py scripts/tally.py scripts/usage_totals.py \
  scripts/power.py scripts/timing.py scripts/token_floor.py \
  tests/test_power.py tests/test_preflight_commands.py tests/test_preflight_inference.py \
  tests/test_preflight_models.py tests/test_preflight_processes.py
```

Not imported: `arms/engine.json` and `arms/envelope.json` (pin the retired attempt-route engine; Phase 2 writes the release-one Engine arm), `scripts/build_gap_register.py`, `scripts/hp7_live_route.py`, `scripts/publish_gate.py`, `scripts/reconcile_claims.py`, `scripts/rescore_seams.py`, `scripts/run_first_milestone.py`, `recipes/`.

- [ ] **Step 2: Green**

`uv run pytest -q > /tmp/p0-t5.log 2>&1; echo "EXIT: $?"` → 0; `uv run ruff check; echo "EXIT: $?"` → 0. If `preflight.sh` references `arms/engine.json` by default, leave it — it takes `--arms`; verify with `grep -n "engine.json" scripts/preflight.sh` and report the line in the commit message if present.

- [ ] **Step 3: Record and commit**

```bash
git status --porcelain --untracked-files=all | awk '{print $2}' | grep -v PROVENANCE.md | xargs uv run python tools/provenance.py record --sha "$(git rev-parse pre-release-one-2026-09-13^{commit})"
uv run python tools/provenance.py check; echo "EXIT: $?"
git add -A && git commit -m "Phase 0: baseline arms and the preflight, interleave, tally and usage instruments"
```

---

### Task 6: The documents — BRIEF, AGENTS, ROADMAP, the record, the spec

**Files:**
- Create (import, then edit): `BRIEF.md`; (import unchanged): `docs/pathologies.md`, `docs/remediations.md`, `docs/superpowers/specs/2026-09-13-release-one-design.md`, `docs/superpowers/plans/2026-09-13-phase-0-restart.md`
- Create (import to a new path): `docs/lessons.md` from `docs/development/lessons.md`
- Create (new): `AGENTS.md`, `ROADMAP.md`, `docs/results/.gitkeep`, `docs/reviews/.gitkeep`

- [ ] **Step 1: Import**

```bash
git checkout $TAG -- BRIEF.md docs/pathologies.md docs/remediations.md \
  docs/superpowers/specs/2026-09-13-release-one-design.md docs/superpowers/plans/2026-09-13-phase-0-restart.md
git show $TAG:docs/development/lessons.md > docs/lessons.md
mkdir -p docs/results docs/reviews && touch docs/results/.gitkeep docs/reviews/.gitkeep
```

- [ ] **Step 2: Edit `BRIEF.md`**

Replace the `## North star` section's two paragraphs with:

```markdown
Keep a small model on track, so a Python developer can use local AI and stay
at the wheel. The developer's engineering is domain engineering — specs and
tests — not agent engineering. Release one ships an Engine that beats bare Pi
at three mechanical pathologies and an Eval that proves it; the design is
`docs/superpowers/specs/2026-09-13-release-one-design.md`.

Satyrn Evals captures a task, invokes an attempt command, persists the patch
and transcript, and grades the saved evidence offline. The engine seam is an
executable command, so the suite can be developed with a fake command and does
not import engine internals.
```

Keep `## Invariants`, `## Development feedback policy`, and `## Comparison policy` verbatim. Delete `## What comes next` entirely. Fix the one relative link in invariant 2 (`docs/topics/trust-boundaries.md`) to read `the trust-boundaries note on the tagged tree (` `git show pre-release-one-2026-09-13:docs/topics/trust-boundaries.md` `)`.

- [ ] **Step 3: Write `AGENTS.md`**

```markdown
# Working in this repository

Read `BRIEF.md`, `ROADMAP.md`, and the release-one design
(`docs/superpowers/specs/2026-09-13-release-one-design.md`). Then read the
plan for the current phase and nothing else. The tag
`pre-release-one-2026-09-13` on `main` holds everything before this tree; it
is evidence for a named question, never guidance.

**Unattended is for building; attended is for deciding and spending.** An
agent executing a plan implements its tasks, commits at task boundaries, and
stops at anything the plan did not foresee: an underspecified task, a task
that fails acceptance twice, a red gate whose fix is not in the plan, or any
step that wants inference. It never merges, never pushes, never runs a model
outside `satyrn-evals launch` with a frozen record, and never writes a result
or review file except through `satyrn-evals launch` and `tools/review.py`.

The default test tier uses no model, network, or subprocess; the tripwire in
`tests/conftest.py` enforces it. Every refusal test has a sibling success test.
Grade from hook-written evidence, never stdout or exit status. State
denominators and missingness. Count events from `tool_execution_start`, one
per call — never `grep -c`. Read a gate's exit code; never pipe a gate.

**The instrument is not the work.** Two consecutive instrument-only pieces stop
the loop; a token run does not restart it. If a fix is larger than the
measurement it unblocks, stop and ask. Every file here has a row in
`PROVENANCE.md`; `just gates` fails if one does not.
```

- [ ] **Step 4: Write `ROADMAP.md`** (≤ 150 lines; this is the whole file)

```markdown
# Roadmap — release one

The design is `docs/superpowers/specs/2026-09-13-release-one-design.md`. One
claim: an Engine that beats bare Pi at three mechanical pathologies
(repeat/read-lock loops, never running its own tests, writing outside the
declared scope), and an Eval that proves it, cold and warm. Nothing else is
claimed.

## Phases

| # | Phase | Mode | Done when | Status |
|---|---|---|---|---|
| 0 | Restart: tags, orphan trees, the import with provenance, gates green, launcher gate, docs caps, review script, hooks | overnight | both trees build; default tiers green; `just gates` enforces the caps; `PROVENANCE.md` names every file's source | in progress — `docs/superpowers/plans/2026-09-13-phase-0-restart.md` |
| 1 | Engine `/implement` v1: derived contract, guards on the dispatch route, carried tests, compact results, receipt | overnight, fake-first | every component has a replay or fixture test in both directions; a fake model completes `/implement` end to end with no inference | not started |
| 2 | Eval core: two workloads re-qualified, `census` for the three counts, the warm prefix as a fixture, cold/warm launcher profiles | overnight, except one attended prefix recording | the eval runs both arms and both conditions against a fake and produces the per-cell table | not started |
| 3 | Route proof: one cell per arm per condition | attended | guards fire where retained evidence says they should; receipts read; the model probe has fixed the model | not started |
| 4 | Comparison: n=12 per cell on the M1 Pro | unattended batch, frozen in daylight | one result page against the decision rule | not started |
| 5 | Decide and ship, or stop | attended | release one published, or a stated negative | not started |

The Ornith 1.5 9B pathology probe runs alongside 0–2 on the tagged tree
(`git show pre-release-one-2026-09-13:docs/current/ornith-9b-pathology-probe-brief.md`)
and fixes the model before Phase 3.

## Rules that bind every phase

- Attended cycles are ≤ 1 GPU-hour and n ≤ 8; the weekly batch is n = 12 per
  cell, record and grant frozen in daylight, run on the M1 Pro.
- A result is one file under `docs/results/`, ≤ 120 lines, with a fenced
  recompute command; at most twelve before one is folded into
  `docs/pathologies.md` or `docs/lessons.md`.
- Two consecutive instrument-only pieces stop the loop.
- Nothing pools across conditions, workloads, models, or machines.

## Deferred

Contributor-authored suites; a fifth roadmap phase; the isolation-vs-guards
ablation; the 16 GB target if the probe is negative; the orchestrator skill;
the `session-ordering-regression` hazard question; any course-derived claim.
```

- [ ] **Step 5: Record and commit**

```bash
SHA=$(git rev-parse pre-release-one-2026-09-13^{commit})
uv run python tools/provenance.py record --sha "$SHA" BRIEF.md docs/pathologies.md docs/remediations.md docs/lessons.md \
  docs/superpowers/specs/2026-09-13-release-one-design.md docs/superpowers/plans/2026-09-13-phase-0-restart.md
uv run python tools/provenance.py new AGENTS.md ROADMAP.md docs/results/.gitkeep docs/reviews/.gitkeep
uv run python tools/provenance.py check; echo "EXIT: $?"
git add -A && git commit -m "Phase 0: BRIEF trimmed to invariants and policy; AGENTS, ROADMAP, the record, and the spec"
```

(`docs/lessons.md` is recorded as imported although its path moved; the row's source SHA is what matters.)

---

### Task 7: The docs linter, rewritten to the release-one caps

**Files:**
- Create: `tools/lint_docs.py` (new, not imported), `tests/test_doc_caps.py`

**Interfaces:**
- Produces: `lint_docs.check(root: Path) -> list[str]`; `just lint-docs` exits 1 on any failure.

Rules: `ROADMAP.md` ≤ 150 lines; every `docs/results/*.md` ≤ 120 lines and contains at least one fenced code block (a line starting with three backticks or four spaces followed by a command is **not** enough — require the backtick fence); at most 12 files in `docs/results/` (`.gitkeep` excluded); `docs/superpowers/specs/*.md` and `docs/superpowers/plans/*.md` ≤ 400 lines... **no** — plans are long by nature; cap specs at 400 and leave plans uncapped; the only directories permitted under `docs/` are `superpowers`, `superpowers/specs`, `superpowers/plans`, `results`, `reviews`; trailing whitespace and a blank last line fail in every `*.md` under the root and `docs/`.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from tools.lint_docs import check


def _docs(tmp_path: Path) -> Path:
    for d in ("docs/superpowers/specs", "docs/superpowers/plans", "docs/results", "docs/reviews"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "ROADMAP.md").write_text("# Roadmap\n")
    return tmp_path


def test_a_clean_tree_has_no_failures(tmp_path: Path) -> None:
    assert check(_docs(tmp_path)) == []


def test_roadmap_over_150_lines_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "ROADMAP.md").write_text("x\n" * 151)
    assert check(root) == ["ROADMAP.md: 151 lines > 150"]


def test_result_over_120_lines_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("```\nx\n```\n" + "y\n" * 118)
    assert check(root) == ["docs/results/r.md: 121 lines > 120"]


def test_result_without_a_fenced_recompute_block_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("# r\n\nno command here\n")
    assert check(root) == ["docs/results/r.md: no fenced recompute block"]


def test_result_with_a_fence_and_under_cap_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("# r\n\n```bash\nuv run x\n```\n")
    assert check(root) == []


def test_thirteen_results_fail(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    for i in range(13):
        (root / f"docs/results/r{i}.md").write_text("```\nx\n```\n")
    assert "docs/results: 13 result files > 12" in check(root)


def test_a_spec_over_400_lines_fails_and_a_long_plan_does_not(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/superpowers/specs/s.md").write_text("x\n" * 401)
    (root / "docs/superpowers/plans/p.md").write_text("x\n" * 900)
    assert check(root) == ["docs/superpowers/specs/s.md: 401 lines > 400"]


def test_an_unlisted_directory_under_docs_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/current").mkdir()
    assert check(root) == ["docs/current: directory not permitted under docs/"]


def test_trailing_whitespace_and_blank_last_line_fail(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/lessons.md").write_text("a \nb\n\n")
    assert check(root) == ["docs/lessons.md:1: trailing whitespace", "docs/lessons.md: blank line at EOF"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_doc_caps.py -q` → FAIL, `No module named 'tools.lint_docs'`

- [ ] **Step 3: Write the linter**

```python
"""Enforce the release-one document caps. No model, network, or subprocess.

The caps are the mechanical form of a rule prose could not hold: a result is
one short page with its recompute command, the roadmap fits on a screen, and
docs/ cannot grow new rooms.
"""

import sys
from pathlib import Path

ROADMAP_CAP = 150
RESULT_CAP = 120
RESULT_COUNT_CAP = 12
SPEC_CAP = 400
PERMITTED_DIRS = frozenset({"superpowers", "superpowers/specs", "superpowers/plans", "results", "reviews"})
SKIP_PARTS = frozenset({"_build", ".venv", "node_modules", ".claude"})


def _lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


def _whitespace(root: Path) -> list[str]:
    failures: list[str] = []
    paths = sorted({*root.glob("*.md"), *root.glob("docs/**/*.md")})
    for path in paths:
        if not path.is_file() or any(p in SKIP_PARTS for p in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        lines = _lines(path)
        failures.extend(f"{rel}:{n}: trailing whitespace" for n, line in enumerate(lines, 1) if line != line.rstrip())
        if lines and lines[-1] == "":
            failures.append(f"{rel}: blank line at EOF")
    return failures


def check(root: Path) -> list[str]:
    failures: list[str] = []
    roadmap = root / "ROADMAP.md"
    if roadmap.exists() and (n := len(_lines(roadmap))) > ROADMAP_CAP:
        failures.append(f"ROADMAP.md: {n} lines > {ROADMAP_CAP}")
    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(p for p in docs.rglob("*") if p.is_dir()):
            rel = path.relative_to(docs).as_posix()
            if rel not in PERMITTED_DIRS:
                failures.append(f"docs/{rel}: directory not permitted under docs/")
        results = sorted(p for p in (docs / "results").glob("*.md")) if (docs / "results").is_dir() else []
        for path in results:
            rel = path.relative_to(root).as_posix()
            lines = _lines(path)
            if len(lines) > RESULT_CAP:
                failures.append(f"{rel}: {len(lines)} lines > {RESULT_CAP}")
            if not any(line.startswith("```") for line in lines):
                failures.append(f"{rel}: no fenced recompute block")
        if len(results) > RESULT_COUNT_CAP:
            failures.append(f"docs/results: {len(results)} result files > {RESULT_COUNT_CAP}")
        for path in sorted((docs / "superpowers" / "specs").glob("*.md")) if (docs / "superpowers" / "specs").is_dir() else []:
            if (n := len(_lines(path))) > SPEC_CAP:
                failures.append(f"{path.relative_to(root).as_posix()}: {n} lines > {SPEC_CAP}")
    failures.extend(_whitespace(root))
    return failures


def main() -> int:
    failures = check(Path.cwd())
    for line in failures:
        print(f"  {line}")
    if failures:
        print(f"\nlint-docs: {len(failures)} failures")
        return 1
    print("lint-docs: all documents within cap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests, then the real tree**

`uv run pytest tests/test_doc_caps.py -q` → 9 passed. Then `just lint-docs; echo "EXIT: $?"` → must be 0 on the actual tree. If the spec exceeds 400 lines, that is a real finding: report the count and stop (do not raise the cap).

- [ ] **Step 5: Record and commit**

```bash
uv run python tools/provenance.py new tools/lint_docs.py tests/test_doc_caps.py
git add -A && git commit -m "Phase 0: docs caps as a gate — roadmap, results, specs, permitted directories"
```

---

### Task 8: The run-record gate

**Files:**
- Create: `src/satyrn_evals/run_record.py`, `tests/test_run_record.py`
- Modify: `src/satyrn_evals/cli.py` (add `launch --check RECORD`)

**Interfaces:**
- Produces: `RunRecord` (frozen dataclass), `load_run_record(path: Path) -> RunRecord` (raises `RunRecordError`, a `UsageError` subclass from `errors.py`, naming the first missing or ill-typed field), `gate(record: RunRecord, *, previous_result_committed: bool | None) -> None` (raises `RunRecordError` on any refusal), and the CLI `satyrn-evals launch --check RECORD.json` (exit 0 on pass, usage exit code on refusal). Phase 2 adds the cell loop behind the same subcommand.

Record schema (all required):

```json
{
  "version": 1,
  "task": "agentclinic-repair-misleading-locus",
  "task_tree_sha256": "<64 hex>",
  "arm": "baseline",
  "model": "omlx/gemma-4-12B-it-MLX-8bit",
  "condition": "cold",
  "n": 4,
  "mode": "attended",
  "max_minutes": 60,
  "stop_rule": "established infrastructure failure only; ordinary failures are counted",
  "decision_rule": "presence counts per pathology; no rate",
  "previous_result": null
}
```

Gate rules: `mode` is `attended` (n ≤ 8, `max_minutes` ≤ 60) or `batch` (n ≤ 12, `max_minutes` ≤ 720); `condition` is `cold` or `warm`; `task_tree_sha256` is 64 lowercase hex; `stop_rule` and `decision_rule` are non-empty; `previous_result` is `null` or a path — when a path, `previous_result_committed` must be `True` (the CLI computes it; the pure gate is told).

- [ ] **Step 1: Failing tests**

```python
import json
from pathlib import Path

import pytest

from satyrn_evals.errors import UsageError
from satyrn_evals.run_record import RunRecord, RunRecordError, gate, load_run_record

GOOD = {
    "version": 1, "task": "agentclinic-repair-misleading-locus", "task_tree_sha256": "a" * 64,
    "arm": "baseline", "model": "omlx/gemma-4-12B-it-MLX-8bit", "condition": "cold", "n": 4,
    "mode": "attended", "max_minutes": 60,
    "stop_rule": "established infrastructure failure only", "decision_rule": "presence counts; no rate",
    "previous_result": None,
}


def _write(tmp_path: Path, **over: object) -> Path:
    path = tmp_path / "record.json"
    path.write_text(json.dumps({**GOOD, **over}))
    return path


def test_a_complete_record_loads_and_passes_the_gate(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path))
    assert isinstance(record, RunRecord) and record.n == 4
    gate(record, previous_result_committed=None)


def test_a_missing_field_is_named(tmp_path: Path) -> None:
    body = {k: v for k, v in GOOD.items() if k != "decision_rule"}
    path = tmp_path / "r.json"
    path.write_text(json.dumps(body))
    with pytest.raises(RunRecordError, match="decision_rule"):
        load_run_record(path)


def test_run_record_error_is_a_usage_error() -> None:
    assert issubclass(RunRecordError, UsageError)


@pytest.mark.parametrize("over", [{"n": 9}, {"max_minutes": 61}])
def test_attended_caps_are_enforced(tmp_path: Path, over: dict[str, object]) -> None:
    with pytest.raises(RunRecordError, match="attended"):
        gate(load_run_record(_write(tmp_path, **over)), previous_result_committed=None)


def test_batch_allows_twelve_and_twelve_hours(tmp_path: Path) -> None:
    gate(load_run_record(_write(tmp_path, mode="batch", n=12, max_minutes=720)), previous_result_committed=None)


def test_batch_refuses_thirteen(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="batch"):
        gate(load_run_record(_write(tmp_path, mode="batch", n=13, max_minutes=720)), previous_result_committed=None)


def test_a_bad_digest_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="task_tree_sha256"):
        load_run_record(_write(tmp_path, task_tree_sha256="abc"))


def test_a_previous_result_must_be_committed(tmp_path: Path) -> None:
    record = load_run_record(_write(tmp_path, previous_result="docs/results/2026-09-14-x.md"))
    with pytest.raises(RunRecordError, match="previous_result"):
        gate(record, previous_result_committed=False)
    gate(record, previous_result_committed=True)


def test_an_unknown_condition_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RunRecordError, match="condition"):
        load_run_record(_write(tmp_path, condition="lukewarm"))
```

- [ ] **Step 2: Run to verify failure**

`uv run pytest tests/test_run_record.py -q` → FAIL, `No module named 'satyrn_evals.run_record'`

- [ ] **Step 3: Implement**

First check the base class: `grep -n "^class UsageError" src/satyrn_evals/errors.py` — it exists in the imported `errors.py`; if its name differs, use the class the imported `cli.py` maps to the usage exit code and adjust the test's import to match. Then `src/satyrn_evals/run_record.py`:

```python
"""The frozen record a run must carry before the launcher will spend anything.

A record is a small JSON file written and committed in daylight. `gate`
refuses anything outside the cadence the design fixed: attended runs are
n <= 8 and an hour; the weekly batch is n <= 12 and twelve hours. The check
is pure; the CLI supplies the one fact that needs git.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from satyrn_evals.errors import UsageError

type Mode = Literal["attended", "batch"]
type Condition = Literal["cold", "warm"]

CAPS: dict[str, tuple[int, int]] = {"attended": (8, 60), "batch": (12, 720)}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class RunRecordError(UsageError):
    """The record is absent, ill-formed, or outside the cadence."""


@dataclass(frozen=True, slots=True)
class RunRecord:
    version: int
    task: str
    task_tree_sha256: str
    arm: str
    model: str
    condition: Condition
    n: int
    mode: Mode
    max_minutes: int
    stop_rule: str
    decision_rule: str
    previous_result: str | None


_REQUIRED: dict[str, type | tuple[type, ...]] = {
    "version": int, "task": str, "task_tree_sha256": str, "arm": str, "model": str,
    "condition": str, "n": int, "mode": str, "max_minutes": int,
    "stop_rule": str, "decision_rule": str, "previous_result": (str, type(None)),
}


def load_run_record(path: Path) -> RunRecord:
    try:
        body = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RunRecordError(f"run record {path}: {error}") from error
    for field, kind in _REQUIRED.items():
        if field not in body:
            raise RunRecordError(f"run record {path}: missing {field}")
        if not isinstance(body[field], kind) or isinstance(body[field], bool):
            raise RunRecordError(f"run record {path}: {field} has the wrong type")
    if body["condition"] not in ("cold", "warm"):
        raise RunRecordError(f"run record {path}: condition must be cold or warm")
    if body["mode"] not in CAPS:
        raise RunRecordError(f"run record {path}: mode must be attended or batch")
    if not _HEX64.match(body["task_tree_sha256"]):
        raise RunRecordError(f"run record {path}: task_tree_sha256 must be 64 lowercase hex")
    for field in ("stop_rule", "decision_rule"):
        if not body[field].strip():
            raise RunRecordError(f"run record {path}: {field} is empty")
    return RunRecord(**{k: body[k] for k in _REQUIRED})


def gate(record: RunRecord, *, previous_result_committed: bool | None) -> None:
    max_n, max_minutes = CAPS[record.mode]
    if record.n > max_n or record.max_minutes > max_minutes:
        raise RunRecordError(
            f"{record.mode} runs are capped at n<={max_n} and {max_minutes} minutes; "
            f"record asks n={record.n}, {record.max_minutes} minutes")
    if record.previous_result is not None and previous_result_committed is not True:
        raise RunRecordError(f"previous_result {record.previous_result} is not committed")
```

Then in `cli.py`, add a `launch` subcommand next to `census` with one flag, `--check RECORD`, that loads the record, computes `previous_result_committed` by running `git ls-files --error-unmatch <path>` via `subprocess.run` **only when `previous_result` is not null**, calls `gate`, prints `launch: record accepted` and returns 0; any `RunRecordError` follows the CLI's existing usage-error path. Without `--check`, `launch` prints `launch: cells are Phase 2; use --check` and returns the usage exit code.

- [ ] **Step 4: Tests pass; CLI check**

`uv run pytest tests/test_run_record.py tests/test_cli.py -q` → passed. Write `/tmp/rec.json` with the GOOD body and run `uv run satyrn-evals launch --check /tmp/rec.json; echo "EXIT: $?"` → `launch: record accepted`, `EXIT: 0`. Then `uv run pytest -q > /tmp/p0-t8.log 2>&1; echo "EXIT: $?"` → 0 (the tripwire proves the `--check` path spawned nothing in the default tier: `previous_result` is null in every default-tier test).

- [ ] **Step 5: Record and commit**

```bash
uv run python tools/provenance.py new src/satyrn_evals/run_record.py tests/test_run_record.py
git add -A && git commit -m "Phase 0: the run-record gate — no record, no cells"
```

---

### Task 9: The review script's pure core

**Files:**
- Create: `tools/review.py`, `tests/test_review.py`

**Interfaces:**
- Produces: `review_path(root: Path, commit_range: str, model: str) -> Path` → `docs/reviews/<start>..<end>-<model-slug>.md`; `refuse_if_exists(path: Path) -> None` (raises `FileExistsError`); `provider_and_model(spec: str) -> tuple[str, str]` (`"zai/glm-5.3"` → `("zai", "glm-5.3")`); `build_prompt(diff: str, range_label: str) -> str`; `main(argv)` runs `pi -p --no-session --no-extensions --no-skills -nc --provider P --model M --exclude-tools write,edit PROMPT` and writes its stdout to the path. The `pi` call is the only subprocess and is not exercised in the default tier.

- [ ] **Step 1: Failing tests**

```python
from pathlib import Path

import pytest

from tools.review import build_prompt, provider_and_model, refuse_if_exists, review_path


def test_review_path_encodes_range_and_model(tmp_path: Path) -> None:
    path = review_path(tmp_path, "8633149..9f1c2d3", "zai/glm-5.3")
    assert path == tmp_path / "docs" / "reviews" / "8633149..9f1c2d3-zai-glm-5.3.md"


def test_an_existing_review_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.md"
    path.write_text("x")
    with pytest.raises(FileExistsError):
        refuse_if_exists(path)


def test_an_absent_review_path_is_allowed(tmp_path: Path) -> None:
    refuse_if_exists(tmp_path / "absent.md")


def test_provider_and_model_split_on_the_first_slash() -> None:
    assert provider_and_model("zai/glm-5.3") == ("zai", "glm-5.3")
    assert provider_and_model("openrouter-curated/moonshotai/kimi-k3") == ("openrouter-curated", "moonshotai/kimi-k3")


def test_a_model_spec_without_a_provider_is_refused() -> None:
    with pytest.raises(ValueError, match="provider/model"):
        provider_and_model("glm-5.3")


def test_build_prompt_carries_the_diff_and_asks_for_one_verdict() -> None:
    prompt = build_prompt("diff --git a/x b/x\n+1\n", "8633149..9f1c2d3")
    assert "8633149..9f1c2d3" in prompt
    assert "diff --git a/x b/x" in prompt
    assert "Accept" in prompt and "itemized" in prompt
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_review.py -q` → `No module named 'tools.review'`

- [ ] **Step 3: Implement**

```python
"""One review, one model, one file. Refuses to write a second review of the
same range; delete the first if you truly need another, and that shows in git.
"""

import subprocess
import sys
from pathlib import Path

PROMPT = """Review the commit range {range_label} of this repository against the
release-one design (docs/superpowers/specs/2026-09-13-release-one-design.md),
BRIEF.md's invariants and comparison policy, and AGENTS.md. Verify claims by
reading the tree, not the commit messages. Return exactly one verdict line —
`Accept` or `Send back` — followed by an itemized list of what must change,
each item naming file:line. No second-order commentary.

{diff}
"""


def review_path(root: Path, commit_range: str, model: str) -> Path:
    slug = model.replace("/", "-")
    return root / "docs" / "reviews" / f"{commit_range}-{slug}.md"


def refuse_if_exists(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"a review already exists at {path}; delete it deliberately to review again")


def provider_and_model(spec: str) -> tuple[str, str]:
    if "/" not in spec:
        raise ValueError(f"model must be given as provider/model, got {spec!r}")
    provider, model = spec.split("/", 1)
    return provider, model


def build_prompt(diff: str, range_label: str) -> str:
    return PROMPT.format(range_label=range_label, diff=diff)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: review.py COMMIT_RANGE PROVIDER/MODEL", file=sys.stderr)
        return 2
    commit_range, spec = argv
    root = Path.cwd()
    path = review_path(root, commit_range, spec)
    refuse_if_exists(path)
    provider, model = provider_and_model(spec)
    diff = subprocess.run(["git", "diff", commit_range], check=True, capture_output=True, text=True).stdout
    prompt = build_prompt(diff, commit_range)
    result = subprocess.run(
        ["pi", "-p", "--no-session", "--no-extensions", "--no-skills", "-nc",
         "--provider", provider, "--model", model, "--exclude-tools", "write,edit", prompt],
        check=True, capture_output=True, text=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<!-- {commit_range} reviewed by {spec} -->\n\n{result.stdout}")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Pass** — `uv run pytest tests/test_review.py -q` → 6 passed; `uv run ruff check` → clean.

- [ ] **Step 5: Record and commit**

```bash
uv run python tools/provenance.py new tools/review.py tests/test_review.py
git add -A && git commit -m "Phase 0: the review script — one range, one model, one file"
```

---

### Task 10: Claude Code hooks that make the gates fire before the action

**Files:**
- Create: `tools/hooks/__init__.py`, `tools/hooks/guard.py`, `tests/test_hook_guard.py`, `.claude/settings.json`

**Interfaces:**
- Produces: `decide(tool_name: str, tool_input: dict) -> str | None` returning a refusal message or `None`. The hook process reads Claude Code's JSON from stdin, calls `decide`, and exits 2 with the message on stderr to block, 0 to allow.

Rules: a `Bash` command containing `pi -p` or `pi --print` is blocked unless it contains `tools/review.py`; a `Bash` command containing `satyrn-evals run `, `satyrn-evals session ` or `satyrn-evals attempt ` is blocked unless it contains `satyrn-evals launch`; a `Bash` command that mentions `docs/results/` or `docs/reviews/` together with `>`, `>>`, `tee `, `cp `, `mv ` or `touch ` is blocked unless it contains `satyrn-evals launch` or `tools/review.py`; a `Write`, `Edit` or `MultiEdit` whose `file_path` is under `docs/results/` or `docs/reviews/` is blocked. Everything else is allowed. This is a tripwire for agents, not a sandbox; `AGENTS.md` says so.

- [ ] **Step 1: Failing tests**

```python
import pytest

from tools.hooks.guard import decide


@pytest.mark.parametrize("command", [
    "pi -p --provider zai --model glm-5.3 'review this'",
    "cd x && pi --print 'hi'",
    "uv run satyrn-evals run agentclinic-repair-misleading-locus --n 1 -- satyrn-evals-attempt-pi",
    "uv run satyrn-evals session agentclinic-complaint-lifecycle -- satyrn-evals-session-pi",
    "echo x > docs/results/2026-09-14-probe.md",
    "tee docs/reviews/a..b-zai.md < /tmp/x",
])
def test_blocked_bash_commands(command: str) -> None:
    assert decide("Bash", {"command": command}) is not None


@pytest.mark.parametrize("command", [
    "uv run python tools/review.py 8633149..9f1c2d3 zai/glm-5.3",
    "uv run satyrn-evals launch --check /tmp/rec.json",
    "uv run pytest -q",
    "git commit -m 'x'",
    "cat docs/results/2026-09-14-probe.md",
    "pip install x",
])
def test_allowed_bash_commands(command: str) -> None:
    assert decide("Bash", {"command": command}) is None


@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit"])
def test_direct_writes_to_results_and_reviews_are_blocked(tool: str) -> None:
    assert decide(tool, {"file_path": "/repo/docs/results/x.md"}) is not None
    assert decide(tool, {"file_path": "/repo/docs/reviews/x.md"}) is not None


def test_direct_writes_elsewhere_are_allowed() -> None:
    assert decide("Write", {"file_path": "/repo/docs/lessons.md"}) is None
    assert decide("Edit", {"file_path": "/repo/src/satyrn_evals/cli.py"}) is None


def test_unknown_tools_are_allowed() -> None:
    assert decide("Read", {"file_path": "/repo/docs/results/x.md"}) is None
```

- [ ] **Step 2: Run to verify failure** — `No module named 'tools.hooks'`

- [ ] **Step 3: Implement**

`tools/hooks/__init__.py` empty. `tools/hooks/guard.py`:

```python
"""PreToolUse guard for Claude Code. Exit 2 blocks the tool call and shows
the message; exit 0 allows it. A tripwire for agents, not a sandbox.
"""

import json
import re
import sys

_PI_PRINT = re.compile(r"(^|[\s;&|(])pi\s+(-p|--print)\b")
_DIRECT_RUN = re.compile(r"satyrn-evals\s+(run|session|attempt)\s")
_RESULT_PATHS = re.compile(r"docs/(results|reviews)/")
_WRITING = re.compile(r"(>>?|\btee\s|\bcp\s|\bmv\s|\btouch\s)")


def decide(tool_name: str, tool_input: dict) -> str | None:
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if _PI_PRINT.search(command) and "tools/review.py" not in command:
            return "blocked: model reviews run only through tools/review.py (one range, one model, one file)"
        if _DIRECT_RUN.search(command) and "satyrn-evals launch" not in command:
            return "blocked: cells run only through `satyrn-evals launch` with a frozen record"
        if _RESULT_PATHS.search(command) and _WRITING.search(command) \
                and "satyrn-evals launch" not in command and "tools/review.py" not in command:
            return "blocked: docs/results and docs/reviews are written only by the launcher and the review script"
        return None
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = str(tool_input.get("file_path", ""))
        if _RESULT_PATHS.search(path):
            return "blocked: docs/results and docs/reviews are written only by the launcher and the review script"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    message = decide(str(payload.get("tool_name", "")), payload.get("tool_input") or {})
    if message is None:
        return 0
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

`.claude/settings.json` (project-level, committed):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "uv run --project \"$CLAUDE_PROJECT_DIR\" python \"$CLAUDE_PROJECT_DIR/tools/hooks/guard.py\""}]
      },
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [{"type": "command", "command": "uv run --project \"$CLAUDE_PROJECT_DIR\" python \"$CLAUDE_PROJECT_DIR/tools/hooks/guard.py\""}]
      }
    ]
  }
}
```

- [ ] **Step 4: Pass, then prove the hook end to end without Claude**

`uv run pytest tests/test_hook_guard.py -q` → 17 passed. Then:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"pi -p hello"}}' | uv run python tools/hooks/guard.py; echo "EXIT: $?"     # expect the blocked message and EXIT: 2
echo '{"tool_name":"Bash","tool_input":{"command":"uv run pytest -q"}}' | uv run python tools/hooks/guard.py; echo "EXIT: $?"  # expect EXIT: 0
```

Note in the commit message that the hook takes effect for sessions opened in this worktree after the settings file exists; the current session will not see it.

- [ ] **Step 5: Record and commit**

```bash
uv run python tools/provenance.py new tools/hooks/__init__.py tools/hooks/guard.py tests/test_hook_guard.py
git add -A && git commit -m "Phase 0: PreToolUse guard — reviews, cells, and result files go only through their tools"
```

(`.claude/settings.json` is outside the provenance-tracked shapes; it is committed but not recorded — the recorder's `tracked()` does not walk `.claude/`.)

---

### Task 11: The engine tree

Work in `/Users/pauleveritt/projects/pauleveritt/satyrn-engine/.claude/worktrees/release-one`.

**Files:**
- Create (import): `src/satyrn_engine/*.py` (all eleven), `packages/engine/*` (all five), `tests/*.py` and `tests/*.mjs` except `test_delivery_chain.py` and `test_integration_delivery_chain.py`, `tests/fixtures/`, `tools/replay_guards.mjs`, `tools/replay_orchestrator.mjs`, `tools/exercise_mutator.mjs`, `tools/exercise_runner.mjs`, `tools/lint_docs.py`, `pyproject.toml`, `Justfile`, `BRIEF.md`, `README.md`, `docs/glossary.md`, `docs/usage.md`
- Modify: `src/satyrn_engine/delivery.py` (remove `deliver_chain`), `pyproject.toml` (drop the `docs` group), `Justfile` (drop docs targets; add the Node gates), `BRIEF.md` ("Where to start"), `README.md` (one paragraph pointing at the release-one spec)
- Create: `AGENTS.md`, `uv.lock`

- [ ] **Step 1: Import**

```bash
TAG=pre-release-one-2026-09-13
git checkout $TAG -- src packages tests tools/replay_guards.mjs tools/replay_orchestrator.mjs \
  tools/exercise_mutator.mjs tools/exercise_runner.mjs tools/lint_docs.py \
  pyproject.toml Justfile BRIEF.md README.md docs/glossary.md docs/usage.md
git rm -q --cached tests/test_delivery_chain.py tests/test_integration_delivery_chain.py && rm tests/test_delivery_chain.py tests/test_integration_delivery_chain.py
```

If `git rm --cached` complains the files are not tracked yet (they were only checked out), plain `rm` is enough.

- [ ] **Step 2: Remove `deliver_chain` from `delivery.py`**

`grep -n "deliver_chain\|_chain" src/satyrn_engine/delivery.py src/satyrn_engine/cli.py` — delete the `deliver_chain` function (from its `def` at the line the grep reports through its final `return`) and any helper the grep shows is used **only** by it. `deliver(..., base=...)` and the CLI's `--base` stay: `/implement` branches from the developer's HEAD and `base` is a harmless parameter. Then `uv run --with pytest python -c "import satyrn_engine.delivery, satyrn_engine.cli"` — exit 0 after Step 3's sync.

- [ ] **Step 3: Edit `pyproject.toml`, `Justfile`, `BRIEF.md`, `README.md`; write `AGENTS.md`**

`pyproject.toml`: delete the `docs = [...]` dependency group. Leave everything else.

`Justfile` — replace the whole file:

```make
# Every gate, in order, stopping at the first non-zero exit. Read this
# recipe's own exit code; never pipe it into anything.
gates:
    uv run pytest -q
    uv run ruff check
    node --test --experimental-strip-types tests/test_loop_breaker.mjs tests/test_mutator.mjs tests/test_runner.mjs tests/test_runner_prompt.mjs tests/test_orchestrator.mjs tests/test_transport.mjs
    node --experimental-strip-types tools/replay_guards.mjs
    just lint-docs
    uv run python tools/provenance.py check

lint-docs:
    uv run python tools/lint_docs.py

# The marked tier: real subprocesses and Git. Not in CI.
integration:
    uv run pytest -m integration -q

# Launch pi with the package wired to this checkout (install once with
# `pi install /path/to/satyrn-engine/packages/engine`; see docs/usage.md).
pi-engine:
    SATYRN_ENGINE_REPO=$$PWD pi
```

`BRIEF.md`: replace the `## Where to start` section's paragraph with: "The release-one design lives in `satyrn-evals` at `docs/superpowers/specs/2026-09-13-release-one-design.md`; this tree implements its Phase 1 (`/implement` v1). Everything before this tree is tagged `pre-release-one-2026-09-13` on `main`." Leave the rest of `BRIEF.md` verbatim — its architecture section is what release one builds on.

`README.md`: keep the first two paragraphs (the mission) and the `## What it owns — and doesn't` section; replace everything after with one paragraph: "Release one ships `/implement`: a developer-invoked bounded operation that runs one piece of work in a fresh model context and its own worktree under a derived contract, with the guards loaded, and returns a candidate plus a compact receipt. Design and roadmap: the `satyrn-evals` repository, `docs/superpowers/specs/2026-09-13-release-one-design.md`."

`AGENTS.md`:

```markdown
# Working in this repository

Read `BRIEF.md`, then the release-one design in `satyrn-evals`
(`docs/superpowers/specs/2026-09-13-release-one-design.md`) and the plan for the
current phase. The tag `pre-release-one-2026-09-13` on `main` is evidence, not
guidance.

Default tests use no model, network, or subprocess (`tests/conftest.py`
enforces it); process behaviour is the `integration` tier. A refusal test has
a sibling success test. Guards are proven by replay over recorded tool-call
sequences before they run live (`tools/replay_guards.mjs`, `tests/fixtures/guards`).
Product code never imports a laboratory. One process per operation; no
sidecar. Commit at plan-task boundaries; never merge or push; never run a
model unless the plan's step names it. Every file has a row in `PROVENANCE.md`.
```

- [ ] **Step 4: Sync and run every gate**

```bash
uv sync
uv run pytest -q > /tmp/p0-e.log 2>&1; echo "EXIT: $?"
```

Expected `EXIT: 0`. If a kept test imports `deliver_chain`, delete that test function (it tested the dropped chain). Then `uv run ruff check; echo "EXIT: $?"` → 0; `node --test --experimental-strip-types tests/test_loop_breaker.mjs tests/test_mutator.mjs tests/test_runner.mjs tests/test_runner_prompt.mjs tests/test_orchestrator.mjs tests/test_transport.mjs; echo "EXIT: $?"` → 0; `node --experimental-strip-types tools/replay_guards.mjs; echo "EXIT: $?"` → 0. If Node reports a missing module for `@earendil-works/pi-coding-agent`, check whether the tagged tree carried a `node_modules` or lockfile (`git ls-tree -r $TAG --name-only | grep -i "package-lock\|node_modules" | head`); if it did not and the tests ran there via a globally installed pi, note the exact command that works in the commit message and stop if none does. Then `uv run pytest -m integration -q > /tmp/p0-ei.log 2>&1; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Record and commit**

```bash
SHA=$(git rev-parse pre-release-one-2026-09-13^{commit})
git status --porcelain --untracked-files=all | awk '{print $2}' | grep -v "PROVENANCE.md\|AGENTS.md\|uv.lock" | xargs uv run python tools/provenance.py record --sha "$SHA"
uv run python tools/provenance.py new AGENTS.md uv.lock
uv run python tools/provenance.py check; echo "EXIT: $?"
just gates; echo "EXIT: $?"     # must be 0
git add -A && git commit -m "Phase 0: the engine tree — core, guards, adapter, fixtures; the orchestration chain left behind"
```

---

### Task 12: Close the phase

**Files:**
- Modify (evals tree): `ROADMAP.md` (Phase 0 status), `.github/workflows/gates.yml` (new)
- Modify (engine tree): `.github/workflows/gates.yml` (new)

- [ ] **Step 1: CI runs the default gates in both trees**

Create `.github/workflows/gates.yml` in each tree:

```yaml
name: gates
on:
  push:
    branches: ["release-one"]
  pull_request:
jobs:
  gates:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with: {enable-cache: true}
      - uses: actions/setup-node@v4
        with: {node-version: "22"}
      - uses: extractions/setup-just@v2
      - run: uv python install
      - run: uv sync --frozen
      - run: just gates
```

(The engine's `just gates` needs Node; the evals one does not use it but the same file is fine.)

- [ ] **Step 2: Full gates, both trees, exit codes read**

Evals: `just gates; echo "EXIT: $?"` → 0. Engine: `just gates; echo "EXIT: $?"` → 0. Integration tiers: `just integration; echo "EXIT: $?"` in each → 0, or the single named exception from Task 4 Step 5.

- [ ] **Step 3: Mark Phase 0 done and write the status**

In the evals `ROADMAP.md`, change Phase 0's Status cell to `done <today's date> — <evals commit>, <engine commit>`. Then `just lint-docs` → 0.

- [ ] **Step 4: Commit both trees**

Evals: `git add -A && git commit -m "Phase 0 done: gates and CI for the lean tree"`. Engine: `git add -A && git commit -m "Phase 0 done: gates and CI for the lean tree"`.

- [ ] **Step 5: Status page for the morning** (chat message to the maintainer, not a file)

Under 200 words: both worktree paths and branch heads; default-tier and integration counts per tree; every test file deleted and why (dropped module or dropped task); every imported file that was edited (`census.py`, `delivery.py`, `pyproject.toml` ×2, `Justfile` ×2, `BRIEF.md` ×2, `README.md` ×2, the fleet tests); anything that stopped or was left red with its named cause; the exact `pi install` / Node command status from Task 11. Do **not** start Phase 1.

---

## Self-review against the spec

- **Restart mechanics** (tags, orphan worktrees, `git checkout <sha> -- path`, `PROVENANCE.md`): Task 1, every task's record step, Task 12's completeness gate. Covered.
- **Evals import list**: core modules Task 3; workloads and grader fixture Task 4; arms and instruments Task 5; BRIEF/pathologies/remediations/lessons/spec Task 6; `packet.py` imported as-is (the spec's "renamed to what it is" is Phase 1's, because Phase 1 changes its API — stated in Task 3). **Leave-behind list**: every named module, script, route and task is in a "Not imported" line. Covered.
- **Engine import list**: Task 11, with `deliver_chain` removed and `--base` kept, reason given. Covered.
- **Mechanical gates**: launcher record gate Task 8 (`--check` now, cells in Phase 2 — the spec's Phase 0 done-when says "the launcher gate", not the launcher); docs caps Task 7 (roadmap 150, results 120 and twelve, specs 400, permitted directories, whitespace); review script Task 9; hooks Task 10. Covered.
- **Sphinx**: deliberately not imported; the spec's gates are pytest, ruff, docs caps, launcher — none needs it. Stated in the architecture paragraph.
- **Placeholder scan**: no TBD/TODO; every code step has code; every command has an expected result. The three "stop and report" conditions (dirty engine tree, unexpected test failure class, Node module resolution) are explicit stops, not placeholders.
- **Type consistency**: `record_imported/record_new/check` (Task 1) used identically in Tasks 3–6, 11; `RunRecord/RunRecordError/gate/load_run_record` (Task 8) match the CLI step; `decide` (Task 10) matches `main`; `review_path/refuse_if_exists/provider_and_model/build_prompt` (Task 9) match tests.
