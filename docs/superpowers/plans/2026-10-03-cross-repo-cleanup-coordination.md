# Cross-repo Cleanup Coordination (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** draft for the maintainer's approval, written 2026-10-03. Not approved; do not execute Task 4 or Task 5 until it is.

**Goal:** The five cleanup items that cross the repository boundary land in an order that costs exactly one Engine re-pin, and every backlog entry that names them is closed by a commit it can cite.

**Architecture:** Three of the five steps are already done and are recorded here with the commit that did each. One step is open and is an engine-only, test-first task on its own branch. The last step is the re-pin, which the approved engine-budget plan already owns; this plan adds only the ordering checks and the backlog close-out that plan does not carry.

**Tech Stack:** Python 3.14, uv, pytest; git worktrees; no model, no network.

**Spec:** `evidence/2026-10-02-cleanup-audit/README.md` sections 1, 2 and 11 (the findings), and `docs/superpowers/plans/2026-10-03-engine-confinement-and-edit-parity.md` on branch `worktree-engine-budget` (the approved re-pin plan, called "the EB plan" below). Read both repositories' `AGENTS.md` first.

## Global Constraints

- The sibling checkout `../satyrn-engine` stays detached at `1869397`. `cell_engine.engine_checkout_problems` refuses every Engine launch when its HEAD is anything else. No task here checks out a branch in that directory.
- Engine work happens in a git worktree created from `origin/main`, never in the sibling checkout.
- One re-pin. Every engine commit this plan or the EB plan produces is on engine `main` before the EB plan's Task 5 chooses its commit `<E>`.
- Default tests use no model, network or subprocess. A refusal test has a sibling success test.
- Never pipe a gate. Read `just gates; echo "exit $?"`.
- An executing agent commits at task boundaries and never merges or pushes. Merging, pushing and the re-pin are the maintainer's.
- Every new file gets a `PROVENANCE.md` row in its own repository.

## Review Focus

1. **A second re-pin.** An engine commit that lands on `main` after `<E>` is chosen forces another Engine condition. Task 5 Step 1 checks ancestry before the pin is written.
2. **The vendored fixture drifts again with no signal on CI.** The cross-check skips when the evals tree is absent. Task 4 keeps that skip, and adds a test that a divergence warns and a match does not, so the check itself is proven in the default tier.
3. **A machine-specific path survives.** Task 4 Step 5 greps the engine tree for `/Users/` and expects no hit under `tests/` or `src/`.
4. **A backlog entry closed without evidence.** Task 5 Step 3 gives the exact replacement text, each citing a commit.
5. **The sibling checkout moved.** Task 4 Step 1 and Task 5 Step 1 both print its HEAD and expect `1869397`.

## The five steps and where each stands

| # | Step | Repository | State on 2026-10-03 |
|---|---|---|---|
| 1 | Receipts count `self_test_red_stop`; the retired `self_test_redirected` is dropped | engine | built: `d979cba` on branch `eb-confinement-parity` (worktree `../satyrn-engine-eb`), EB plan Task 2. Not merged, not pushed. |
| 2 | The frozen census scripts and the launcher stop naming `--cell` | evals | done: `159a04d` (dead branch removed, scripts headed historical) and `8519271` (the guard scans every live module), branch `phase-c1`. |
| 3 | The self-hosted task bases carry no nested self-hosted task | evals | done: `7fc679f` (re-cut of the seven bases), ledger entry "C1" (`c8c5904`), branch `phase-c1`. |
| 4 | The engine's vendored task manifests match the re-cut tasks, with no machine path | engine | **open.** Task 4 below. |
| 5 | The three Engine arms re-pin once; `_engine/` re-syncs; the backlog entries close | both | planned: EB plan Task 5 (attended, after C4's verdict). Task 5 below adds the ordering checks and the close-out. |

Verify the table before starting:

```bash
cd ~/projects/pauleveritt/satyrn-evals
git log --oneline -1 159a04d; git log --oneline -1 8519271; git log --oneline -1 7fc679f
git -C ../satyrn-engine log --oneline -1 d979cba
git -C ../satyrn-engine rev-parse --short HEAD        # 1869397
for t in src/satyrn_evals/tasks/selfhost-*/; do echo "$(git ls-files "$t" | grep -c '/base/src/satyrn_evals/tasks/selfhost-') $t"; done   # 0 on every line
grep -c -- '--cell' src/satyrn_evals/launch_record.py  # 0
```

---

### Task 1, Task 2, Task 3: done

No work. The table above is their record. If any verification line disagrees with the table, stop and report; do not repair it under this plan.

---

### Task 4: The vendored preflight-quiet manifest matches the live task, and the path is portable (engine)

The cross-check in `tests/test_derive_size.py` reads the evals task tree from a hard-coded `/Users/pauleveritt/...` path and warns today: `selfhost-preflight-quiet: ... produces_count live=9 vendored=10`. The live `Produces:` line no longer names `Certificate.as_dict()` and spells out `main`'s four callables. The other seven fixtures agree with the live tree.

**Files:**
- Modify: `tests/test_derive_size.py` (the `LIVE_TASKS` constant at line 50; `test_vendored_matches_live_manifests` near line 216)
- Modify: `tests/fixtures/derive_size/selfhost-preflight-quiet.json`

**Interfaces:**
- Consumes: `satyrn_engine.derive.produces_names(request: str) -> tuple[str, ...]`, already imported by the test module.
- Produces: `LIVE_TASKS_ENV = "SATYRN_EVALS_TASKS"` and `live_tasks_root(environment: Mapping[str, str] | None = None) -> Path` in `tests/test_derive_size.py`. Task 5 runs this module with warnings as errors.

- [ ] **Step 1: Make the worktree.**

```bash
cd ~/projects/pauleveritt/satyrn-engine
git rev-parse --short HEAD                      # 1869397; if not, stop
git fetch origin
git worktree add ../satyrn-engine-cleanup -b cleanup-derive-size-fixture origin/main
cd ../satyrn-engine-cleanup && uv sync --frozen
```

- [ ] **Step 2: Write the failing tests.** Append to `tests/test_derive_size.py`:

```python
def test_the_live_tasks_root_is_the_directory_the_environment_names(tmp_path):
    assert live_tasks_root({LIVE_TASKS_ENV: str(tmp_path)}) == tmp_path


def test_the_live_tasks_root_defaults_to_the_sibling_evals_checkout():
    root = live_tasks_root({})
    assert root.parts[-4:] == ("satyrn-evals", "src", "satyrn_evals", "tasks")
    assert root.parents[3] == Path(__file__).resolve().parents[2]


def _live_task(root: Path, name: str, contract: str) -> None:
    (root / name).mkdir()
    (root / name / "manifest.json").write_text(json.dumps({"contract": contract}), encoding="utf-8")


def test_a_live_manifest_that_matches_the_vendored_fixture_raises_no_warning(tmp_path, monkeypatch):
    name = "selfhost-preflight-quiet"
    _live_task(tmp_path, name, _fixture(name)["request"])
    monkeypatch.setenv(LIVE_TASKS_ENV, str(tmp_path))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        test_vendored_matches_live_manifests(name)


def test_a_live_manifest_that_diverges_from_the_vendored_fixture_warns(tmp_path, monkeypatch):
    name = "selfhost-preflight-quiet"
    diverged = (
        "Files:\n- Create: `scripts/preflight_quiet.py`\n- Test: `tests/`\n\n"
        "Interfaces:\n- Produces: `only_one() -> int`.\n"
    )
    _live_task(tmp_path, name, diverged)
    monkeypatch.setenv(LIVE_TASKS_ENV, str(tmp_path))
    with pytest.warns(UserWarning, match="produces_count live=1 vendored=9"):
        test_vendored_matches_live_manifests(name)


def test_the_vendored_preflight_quiet_fixture_declares_nine_symbols():
    fixture = _fixture("selfhost-preflight-quiet")
    assert fixture["produces_count"] == 9
    assert len(produces_names(fixture["request"])) == 9
    assert "Certificate.as_dict" not in produces_names(fixture["request"])
```

- [ ] **Step 3: Run them and watch them fail.**

Run: `uv run pytest -q tests/test_derive_size.py; echo "exit $?"`
Expected: exit 1. The first four fail with `NameError: name 'live_tasks_root' is not defined` (or `LIVE_TASKS_ENV`); the last fails with `assert 10 == 9`.

- [ ] **Step 4: Implement.** In `tests/test_derive_size.py`, add `import os` and `from collections.abc import Mapping` to the imports, and replace the line

```python
LIVE_TASKS = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/src/satyrn_evals/tasks")
```

with

```python
LIVE_TASKS_ENV = "SATYRN_EVALS_TASKS"


def live_tasks_root(environment: Mapping[str, str] | None = None) -> Path:
    """The evals task tree the cross-check reads: the directory
    ``SATYRN_EVALS_TASKS`` names, else the sibling ``satyrn-evals`` checkout
    beside this repository. Never a machine-specific path."""
    environment = os.environ if environment is None else environment
    if named := environment.get(LIVE_TASKS_ENV):
        return Path(named)
    return Path(__file__).resolve().parents[2] / "satyrn-evals" / "src" / "satyrn_evals" / "tasks"
```

In `test_vendored_matches_live_manifests`, replace `manifest = LIVE_TASKS / name / "manifest.json"` with `manifest = live_tasks_root() / name / "manifest.json"`.

In `tests/fixtures/derive_size/selfhost-preflight-quiet.json`, set `"produces_count": 9` and, inside `"request"`, make two edits to the `Produces:` line so it reads as the live manifest does:

- replace `` `main(argv: Sequence[str] | None = None, *, loadavg, cores, read_ps, read_log) -> int` `` with `` `main(argv: Sequence[str] | None = None, *, loadavg: Callable[[], tuple[float, float, float]], cores: Callable[[], int], read_ps: Callable[[], str], read_log: Callable[[], Iterable[str]]) -> int` ``
- replace `` `Certificate(problems: tuple[str, ...], record: dict[str, object])` with `Certificate.as_dict()`; `` with `` `Certificate(problems: tuple[str, ...], record: dict[str, object])`; ``

Leave `"verdict": "admitted"` and `"non_test_path_count": 1` as they are.

- [ ] **Step 5: Run the module, then the gates.**

```bash
uv run pytest -q tests/test_derive_size.py -W error; echo "exit $?"     # exit 0, no warning
grep -rn "/Users/" tests src; echo "exit $?"                            # no output, exit 1
just gates; echo "exit $?"                                              # exit 0
```

The first command runs the cross-check against the sibling evals checkout. If that checkout is absent the eight cross-check rows skip and the exit is still 0.

- [ ] **Step 6: Commit.**

```bash
git add tests/test_derive_size.py tests/fixtures/derive_size/selfhost-preflight-quiet.json
git commit -m "derive_size: re-vendor preflight-quiet at nine symbols; the live tree is found by name, not by a machine path"
```

**An executing agent stops here** and reports the commit and the three exits. It does not merge, push, or remove the worktree.

---

### Task 5: One re-pin, in order, and the backlog closes (attended, the maintainer)

This task wraps the EB plan's Task 5. It does not restate that task's steps.

**Files:**
- Modify: `ROADMAP.md` (the "Cleanup, 2026-10-02" list under "Deferred")
- Modify: satyrn-engine `BACKLOG.md` (the "Added 2026-10-02" entries)

**Interfaces:**
- Consumes: engine commit `<E>`, the commit the EB plan's Task 5 pins; branches `eb-confinement-parity`, `cleanup-derive-size-fixture` and `cleanup-audit-backlog` in satyrn-engine.
- Produces: nothing a later task reads.

- [ ] **Step 1: Land the engine branches, then check ancestry before any pin is written.** Merge `cleanup-audit-backlog`, `cleanup-derive-size-fixture` and `eb-confinement-parity` into engine `main` (pull requests or fast-forwards, the maintainer's choice) and push `main`. Then, with `<E>` the resulting `main` head:

```bash
cd ~/projects/pauleveritt/satyrn-engine
git fetch origin
for b in cleanup-audit-backlog cleanup-derive-size-fixture eb-confinement-parity; do
  git merge-base --is-ancestor "$b" origin/main && echo "in main: $b" || echo "MISSING: $b"
done
git rev-parse --short HEAD        # still 1869397 until the EB plan moves it
```

Expected: three `in main:` lines. Any `MISSING:` line stops the task: pinning now would force a second re-pin.

- [ ] **Step 2: Run the EB plan's Task 5** (`docs/superpowers/plans/2026-10-03-engine-confinement-and-edit-parity.md`, branch `worktree-engine-budget`) with that `<E>`. It re-pins the three arms, updates the evals guard vocabulary, runs `just sync-engine`, writes the ledger entry and runs the smoke cell. After it, check the two things it does not:

```bash
cd ~/projects/pauleveritt/satyrn-engine          # now at <E>
uv run pytest -q tests/test_derive_size.py -W error; echo "exit $?"   # exit 0
cd ../satyrn-evals
python3 -c "import json;print(json.load(open('_engine/manifest.json'))['engine_commit'])"   # <E>
```

- [ ] **Step 3: Close the backlog entries.** In `ROADMAP.md`, replace the "Cross-repo cluster" bullet under "Cleanup, 2026-10-02" with:

```markdown
- **Cross-repo cluster: closed <date>.** `--cell` residue `159a04d`; un-nested
  bases `7fc679f`; red-stop receipts, vendored manifests and the re-pin at
  engine `<E>` (ledger entry "Engine re-pin").
```

In satyrn-engine `BACKLOG.md`, replace the "Receipts miss red-stop firings" entry and the `test_derive_size.py` clause of the "Fossils" entry with:

```markdown
- **Receipts count red-stop firings: done** (`d979cba`, pinned by evals at
  `<E>`). **Vendored task manifests re-vendored, path portable: done**
  (branch `cleanup-derive-size-fixture`, in `<E>`).
```

Substitute the real date and commit before committing; a literal `<E>` or `<date>` in either file is a failed step.

- [ ] **Step 4: Gates and commits.**

```bash
cd ~/projects/pauleveritt/satyrn-evals && just gates; echo "exit $?"     # exit 0
git add ROADMAP.md && git commit -m "roadmap: the cross-repo cleanup cluster is closed at the Engine re-pin"
```

The engine `BACKLOG.md` edit is a commit on engine `main` after `<E>`. It changes no pinned file and no behaviour, and the arms keep pinning `<E>`; say so in its message so nobody re-pins for it.

- [ ] **Step 5: Remove the worktree.** `git -C ~/projects/pauleveritt/satyrn-engine worktree remove ../satyrn-engine-cleanup` once its branch is in `main`.

## What this plan does not cover

The single-repository cleanup items stay where the backlog puts them: the unconfirmed mark, `STATE.md`, the roadmap's shape, the session route, the unused gates, the fossil files and the engine's documents. None of them touches a pin.
