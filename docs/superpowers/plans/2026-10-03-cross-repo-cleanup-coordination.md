# Cross-repo Cleanup Coordination (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** re-planned 2026-10-06 from the maintainer's cleanup brief of that day; the 2026-10-03 draft is superseded (its text is in this file's history). Task 0 and Task 4 are approved by that brief. Task 5 is attended: it runs inside the EB re-plan's Task 3, after the maintainer merges.

**Goal:** The cleanup items that cross the repository boundary land with the EB head-tolerance fix in exactly one Engine re-pin, and every backlog entry that names them is closed by a commit it can cite.

**Architecture:** Three of the five original steps are on `main` in both repositories and are recorded here with their commits. Step 4 is open: an engine-only, test-first branch `cleanup-derive-size-fixture` in worktree `../satyrn-engine-cleanup`, cut from engine `origin/main`. Step 5 is no longer this plan's own re-pin: it is the EB re-plan's Task 3 (`docs/superpowers/plans/2026-10-06-eb-replan.md`), which pins one engine merge holding both `eb-head-tolerance` and this plan's branch. This plan wraps that task with the ordering checks, the `_engine/` re-sync and the close-out it does not carry.

**Tech Stack:** Python 3.14, uv, pytest; git worktrees; no model, no network.

**Spec:** `evidence/2026-10-02-cleanup-audit/README.md` sections 1, 2 and 11 (the findings), and `docs/superpowers/plans/2026-10-06-eb-replan.md`, Task 3 and its Global Constraints ("Cleanup coordination"). Read both repositories' `AGENTS.md` first.

## Global Constraints

- **The pin is engine `23a0ef649dc4764bf09ca51110434b1b34ac1c27`.** Engine `main` = `origin/main` = `23a0ef6`; the three Engine arm files and `_engine/manifest.json` pin it. `cell_engine.engine_checkout_problems` refuses every Engine launch when `../satyrn-engine` is anywhere else.
- **Do not touch:** engine `main` or the checkout `../satyrn-engine` (any commit there moves HEAD off the pin and blocks Engine launches); the worktrees `../satyrn-engine-eb3` and `.claude/worktrees/eb-replan`; `~/satyrn-runs`; the untracked `evidence/*/…-draft.md` files; any decided evidence or ledger entry.
- **Engine work** happens in the worktree `../satyrn-engine-cleanup`, never in `../satyrn-engine`.
- **One re-pin.** This plan's engine branch reaches engine `main` in the same maintainer merge as `eb-head-tolerance`, before the EB re-plan's Task 3 writes the pin. If it misses that merge it waits for the next runtime re-pin; it never forces a pin of its own.
- **`origin/derive-new-top-level-module` stays out.** It holds `d4abd65` ("derive: admit a new top-level module") and `92c9282`, is unmerged, and changes `derive.py`, which changes the Engine's contract. It needs the maintainer's decision and must not ride this re-pin.
- **No backend change.** The ollama switch is its own plan (see the end of this file). Do not edit `~/.pi/agent/models.json` or the oMLX settings.
- Default tests use no model, network or subprocess. A refusal test has a sibling success test.
- Never pipe a gate. Write `just gates > "$TMPDIR/gates.log" 2>&1 && git add … && git commit …`, so the commit depends on the gate itself, and print the exit separately on failure.
- An executing agent commits at task boundaries and never merges or pushes. Merging, pushing and the re-pin are the maintainer's.
- Every new file gets a `PROVENANCE.md` row in its own repository.

## Review Focus

1. **A second re-pin.** `cleanup-derive-size-fixture` lands on engine `main` after the pin is chosen, which forces another Engine condition. Task 5 Step 1 checks ancestry for both branches before the pin is written.
2. **The unmerged derive branch rides the pin.** `d4abd65` reaches `main` by a stray merge and changes the contract unnoticed. Task 5 Step 1 checks that it is not an ancestor and that the pin's diff from `23a0ef6` names only the two branches' files.
3. **`_engine/` falls out of step with the re-pinned arm.** `tests/test_engine_docs.py:13` requires `_engine/manifest.json` to name the arm's pin, and the EB re-plan's Task 3 changes the pin without running `just sync-engine`. Task 5 Step 3 runs it before the gates.
4. **The vendored fixture drifts again with no signal on CI.** The cross-check skips when the evals tree is absent. Task 4 keeps that skip and adds a test that a divergence warns and a match does not, so the check itself is proven in the default tier.
5. **A machine-specific path survives.** Task 4 Step 5 greps the engine tree for `/Users/` and expects no hit under `tests/` or `src/`.

## The five steps and where each stands

| # | Step | Repository | State on 2026-10-06 |
|---|---|---|---|
| 1 | Receipts count `self_test_red_stop`; the retired `self_test_redirected` is dropped | engine | done: `d979cba`, merged as `5b681b0`; in the pin `23a0ef6`. |
| 2 | The frozen census scripts and the launcher stop naming `--cell` | evals | done: `159a04d`, `8519271`, on `main`. |
| 3 | The self-hosted task bases carry no nested self-hosted task | evals | done: `7fc679f`, ledger entry "C1" (`c8c5904`), on `main`. |
| 4 | The engine's vendored task manifests match the re-cut tasks, with no machine path | engine | **open.** Confirmed at `23a0ef6`: `uv run pytest tests/test_derive_size.py -q -W error` fails on `selfhost-preflight-quiet` (`produces_count live=9 vendored=10`), and `LIVE_TASKS` at line 50 is a hard-coded `/Users/…` path. Task 4. |
| 5 | One re-pin of the Engine arms, `_engine/` re-sync, backlog entries closed | both | **now the EB re-plan's Task 3**, wrapped by Task 5 below. |

The 2026-10-03 draft's other prerequisite, `cleanup-audit-backlog`, is merged (`2327c79`). The clone `../satyrn-engine-pinned` (at `1869397`) is obsolete; it is not on the cleared housekeeping list, so removing it is the maintainer's call.

Verify the table before starting:

```bash
cd ~/projects/pauleveritt/satyrn-evals
for c in 159a04d 8519271 7fc679f c8c5904; do git merge-base --is-ancestor $c main && echo "in evals main: $c" || echo "MISSING: $c"; done
git -C ../satyrn-engine fetch origin
for c in d979cba 5b681b0 2327c79; do git -C ../satyrn-engine merge-base --is-ancestor $c origin/main && echo "in engine origin/main: $c" || echo "MISSING: $c"; done
git -C ../satyrn-engine rev-parse --short HEAD origin/main        # 23a0ef6 twice
grep -l 23a0ef649dc4764bf09ca51110434b1b34ac1c27 arms/*.json _engine/manifest.json   # three arms and the manifest
```

Expected: seven `in … main` lines, `23a0ef6` twice, four file names. Any other answer: stop and report; do not repair it under this plan.

---

### Task 1, Task 2, Task 3: done

No work. The table above is their record.

---

### Task 0: Housekeeping (controller, local only)

None of this touches a pin, a record or evidence. Each removal checks its target first.

- [ ] **Step 1: Remove the merged `../satyrn-engine-eb` worktree.**

```bash
cd ~/projects/pauleveritt/satyrn-engine
git -C ../satyrn-engine-eb status --short                                          # no output
git merge-base --is-ancestor eb-confinement-parity origin/main && echo merged      # merged
git worktree remove ../satyrn-engine-eb
```

The branch `eb-confinement-parity` stays.

- [ ] **Step 2: Move the eight `satyrn-engine-*` temp directories to the Trash.** They are the ones `evidence/2026-10-06-eb-replan/README.md` §1.6 item 3 names, one per Engine `BUDGET_EXCEEDED` cell; the trees that review needed are committed under `evidence/2026-10-06-eb-replan/budget-trees/`.

```bash
cd "$TMPDIR"
ls -d satyrn-engine-*        # exactly: 4b7i2uw3 541d9gkv bqt3_c5y iqkv7lz2 lpx5ovhc rl2giglz t56nnrz4 tld5e1f3
for d in 4b7i2uw3 541d9gkv bqt3_c5y iqkv7lz2 lpx5ovhc rl2giglz t56nnrz4 tld5e1f3; do mv "satyrn-engine-$d" ~/.Trash/; done
```

A name outside that list stays where it is.

- [ ] **Step 3: Remove the evals `engine-budget` worktree.**

```bash
cd ~/projects/pauleveritt/satyrn-evals
git merge-base --is-ancestor worktree-engine-budget main && echo merged          # merged
git -C .claude/worktrees/engine-budget status --short                            # no output
git worktree remove .claude/worktrees/engine-budget
```

---

### Task 4: The vendored preflight-quiet manifest matches the live task, and the path is portable (engine)

The cross-check in `tests/test_derive_size.py` reads the evals task tree from a hard-coded `/Users/pauleveritt/...` path and warns today: `selfhost-preflight-quiet: ... produces_count live=9 vendored=10`. The live `Produces:` line no longer names `Certificate.as_dict()` and spells out `main`'s four callables. The other seven fixtures agree with the live tree.

**Files:**
- Modify: `tests/test_derive_size.py` (the `LIVE_TASKS` constant at line 50; `test_vendored_matches_live_manifests` near line 209)
- Modify: `tests/fixtures/derive_size/selfhost-preflight-quiet.json`
- Modify: `BACKLOG.md` (two entries under "Added 2026-10-02", Step 7)

**Interfaces:**
- Consumes: `satyrn_engine.derive.produces_names(request: str) -> tuple[str, ...]`, already imported by the test module.
- Produces: `LIVE_TASKS_ENV = "SATYRN_EVALS_TASKS"` and `live_tasks_root(environment: Mapping[str, str] | None = None) -> Path` in `tests/test_derive_size.py`. Task 5 runs this module with warnings as errors at the pin.

- [ ] **Step 1: Make the worktree.**

```bash
cd ~/projects/pauleveritt/satyrn-engine
git rev-parse --short HEAD                      # 23a0ef6; if not, stop
git fetch origin
git rev-parse --short origin/main               # 23a0ef6; if not, stop and report
git worktree add ../satyrn-engine-cleanup -b cleanup-derive-size-fixture origin/main
cd ../satyrn-engine-cleanup && uv sync --frozen
```

Every later step in this task runs in `../satyrn-engine-cleanup`.

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

The module already imports `json`, `warnings`, `Path` and `pytest`.

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

The re-vendored task no longer sits at the cap. That breaks one existing test (the 2026-10-03 draft missed it; found by the implementer on 2026-10-06), and it makes one line of the module docstring stale. The boundary itself stays pinned synthetically by `test_ten_produced_symbols_are_admitted` and `test_eleven_produced_symbols_are_refused`. Make two more edits in `tests/test_derive_size.py`:

- Replace the whole `test_selfhost_preflight_quiet_sits_exactly_at_the_produces_cap` function with:

```python
def test_selfhost_preflight_quiet_sits_one_under_the_produces_cap():
    # The real task, re-vendored 2026-10-06 at 9 produced symbols. It sat at
    # the cap (10) until the live task dropped `Certificate.as_dict()`. The
    # boundary itself is pinned synthetically by the two tests below.
    request = request_for("selfhost-preflight-quiet")
    assert len(produces_names(request)) == MEDIUM_PRODUCES_CAP - 1
    assert size_refusal(request) is None
```

- In the module docstring, replace `(it sits\nexactly at the 10-symbol cap today) turns` with `(it sat\nexactly at the 10-symbol cap then) would turn`. The line break stays where it is.

- [ ] **Step 5: Run the module, then the gates.**

```bash
uv run pytest -q tests/test_derive_size.py -W error; echo "exit $?"     # exit 0, no warning
grep -rn "/Users/" tests src; echo "exit $?"                            # no output, exit 1
just gates; echo "exit $?"                                              # exit 0
```

The first command runs the cross-check against the sibling evals checkout. If that checkout is absent the eight cross-check rows skip and the exit is still 0.

- [ ] **Step 6: Commit.**

```bash
just gates > "$TMPDIR/gates.log" 2>&1 && git add tests/test_derive_size.py tests/fixtures/derive_size/selfhost-preflight-quiet.json && git commit -m "derive_size: re-vendor preflight-quiet at nine symbols; the live tree is found by name, not by a machine path"
git show --stat HEAD
```

- [ ] **Step 7: Close the two engine backlog entries on this branch.** The close-out rides the same merge as the fix, so no engine commit lands after the pin. In `BACKLOG.md`, under "Added 2026-10-02", replace the whole "**Receipts miss red-stop firings.**" bullet and the whole "**Vendored task manifests.**" bullet with:

```markdown
- **Receipts count red-stop firings: done.** `d979cba`, merged as `5b681b0`;
  evals has pinned it since `23a0ef6`.
- **Vendored task manifests: done** on branch `cleanup-derive-size-fixture`:
  `selfhost-preflight-quiet` re-vendored at nine symbols, and the evals tree
  found through `SATYRN_EVALS_TASKS` or the sibling checkout. It lands with
  `eb-head-tolerance` in one merge, which evals pins in its ledger entry
  "Engine re-pin for head tolerance".
```

Then:

```bash
just gates > "$TMPDIR/gates.log" 2>&1 && git add BACKLOG.md && git commit -m "Backlog: red-stop receipts and the vendored manifests are done; both reach the evals pin with head tolerance"
git show --stat HEAD
```

**An executing agent stops here.** It reports the two commits and the three exits from Step 5. It does not merge, push, or remove the worktree.

---

### Task 5: One re-pin, in order, and the backlog closes (attended; wraps the EB re-plan's Task 3)

This task wraps `docs/superpowers/plans/2026-10-06-eb-replan.md` Task 3. It does not restate that task's steps; it adds the checks around them and the one step they omit.

**Files:**
- Modify (by `just sync-engine`): `_engine/manifest.json`, `_engine/*.md`, `_engine/rendered/*.md`, `PROVENANCE.md`
- Modify: `ROADMAP.md` (the "Frozen census scripts" bullet under "Cleanup, 2026-10-02")

**Interfaces:**
- Consumes: the engine merge commit `<M>` that holds `eb-head-tolerance` and `cleanup-derive-size-fixture`; EB re-plan Task 3's commits on evals branch `eb-replan`.
- Produces: nothing a later task reads.

- [ ] **Step 1: The maintainer merges both engine branches into engine `main` in one merge and pushes. Then, before any pin is written:**

```bash
cd ~/projects/pauleveritt/satyrn-engine
git fetch origin
M=$(git rev-parse origin/main)
for b in eb-head-tolerance cleanup-derive-size-fixture; do
  git merge-base --is-ancestor "$b" "$M" && echo "in main: $b" || echo "MISSING: $b"
done
git merge-base --is-ancestor d4abd65 "$M" && echo "STOP: d4abd65 is in main" || echo "d4abd65 out"
git diff --stat 23a0ef6 "$M"
```

Expected: two `in main:` lines, `d4abd65 out`, and a diff that names only `src/satyrn_engine/delivery.py`, `BACKLOG.md`, `PROVENANCE.md` and files under `tests/` (the two branches' files). Any `MISSING:`, a `STOP:`, or another file in the diff stops the task. A missing branch forces a second re-pin, and an extra file is a change no ledger entry covers.

- [ ] **Step 2: Run EB re-plan Task 3 Steps 1–3** with `<M>`: fast-forward `../satyrn-engine` to `<M>`, set `pins.engine_commit` in the three arm files `grep -l 23a0ef6 arms/` lists, confirm the seven digests are unchanged, and write the ledger entry "Engine re-pin for head tolerance". Have that entry also say that the merge carries `cleanup-derive-size-fixture` (tests, fixture and backlog only).

- [ ] **Step 3: Re-sync `_engine/` (the step EB Task 3 omits).** `tests/test_engine_docs.py:13` requires `_engine/manifest.json` to name the arm's pin.

```bash
cd ~/projects/pauleveritt/satyrn-engine && git rev-parse HEAD     # <M>
cd ~/projects/pauleveritt/satyrn-evals/.claude/worktrees/eb-replan
SATYRN_ENGINE_REPO=~/projects/pauleveritt/satyrn-engine just sync-engine; echo "exit $?"   # exit 0
python3 -c "import json;print(json.load(open('_engine/manifest.json'))['engine_commit'])"   # <M>
cd ~/projects/pauleveritt/satyrn-engine && uv run pytest -q tests/test_derive_size.py -W error; echo "exit $?"   # exit 0
```

- [ ] **Step 4: Run EB re-plan Task 3 Step 4** (gates and commit). Include the `_engine/` and `PROVENANCE.md` changes from Step 3 in that commit.

- [ ] **Step 5: Close the evals backlog entry.** On `eb-replan`, in `ROADMAP.md` under "Cleanup, 2026-10-02", replace the whole "**Frozen census scripts call `preflight_settings.py --cell`…**" bullet with:

```markdown
- **Cross-repo cleanup: closed <date>.** `--cell` residue `159a04d`,
  `8519271`; un-nested bases `7fc679f`; red-stop receipts `d979cba` (engine
  `5b681b0`, pinned since `23a0ef6`); vendored manifests and the portable
  path in engine `<M>` (ledger entry "Engine re-pin for head tolerance").
  Issue pauleveritt/satyrn-evals#23.
```

Substitute the real date and short commit before committing. A literal `<M>` or `<date>` in the file is a failed step.

```bash
just gates > "$TMPDIR/gates.log" 2>&1 && git add ROADMAP.md && git commit -m "roadmap: the cross-repo cleanup is closed at the head-tolerance re-pin"
git show --stat HEAD
```

- [ ] **Step 6 (the maintainer):** close issue pauleveritt/satyrn-evals#23 with the two commits and `<M>`, and remove the worktree: `git -C ~/projects/pauleveritt/satyrn-engine worktree remove ../satyrn-engine-cleanup` once its branch is in `main`.

---

## Not in this plan

- **`origin/derive-new-top-level-module` (`d4abd65`, `92c9282`).** It is unmerged and changes `derive.py`, so it changes the Engine's contract. It needs the maintainer's decision, its own admission question, and its own re-pin. It must not ride Task 5.
- **The ollama switch** gets its own plan, written after EB's decision L (EB re-plan "Step 2"). Facts that plan starts from:
  - Backends never pool.
  - EB Step 2 compares new cells with retained oMLX cells.
  - Ollama serves a 32,768-token context (`docs/user-journey.md` §4–5), against the arms' `context_window` of 262,144.
  - So the switch means new arm files and fresh baselines on both arms, not an edit to a pinned arm.
  Installing ollama alongside oMLX is fine. Editing `~/.pi/agent/models.json` or the oMLX settings is not.
- **Single-repository cleanup items** stay where the backlogs put them: the unconfirmed mark, `STATE.md`, the roadmap's shape, the session route, the unused gates, the fossil files and the engine's documents. None of them touches a pin.
- **`../satyrn-engine-pinned`**, the obsolete clone at `1869397`. Removing it is the maintainer's call.
