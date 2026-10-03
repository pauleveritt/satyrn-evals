# C1 Re-cut and Re-qualify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-cut the seven self-hosted task bases without nested `selfhost-*` task trees, then issue the six Baseline census records under `confinement` and pass `launch --preflight` on them on this machine.

**Architecture:** One exclusion rule in `tools/cut_task.py` and a deterministic re-cut from the committed specs. Each re-cut is verified against the old tree, so the only change is the removed paths plus any recorded `base_edits`. The frozen census records stay pinned to the trees they ran on through a recorded revision chain. The new records are pinned by a default-tier guard test. The preflight sitting is attended: the maintainer runs it.

**Tech Stack:** Python 3.14, uv, pytest, `tools/cut_task.py`, the `satyrn-evals` CLI.

**Spec:** `docs/superpowers/specs/2026-10-02-c1-requalify-design.md`. The parent spec is `docs/superpowers/specs/2026-09-27-unisolated-harness-design.md`. Read `AGENTS.md` before Task 1.

## Global Constraints

- The default test tier uses no model, network, or subprocess; the tripwire in `tests/conftest.py` enforces it. Commands that spawn processes (`cut_task.py`, `qualify`, task self-tests, `-m integration`) are run as plan steps, never added to the default tier.
- Every refusal test has a sibling success test.
- Read every gate's exit code (`just gates; echo "exit $?"`). Never pipe a gate.
- Every new tracked file gets a row in `PROVENANCE.md` (`just gates` runs `tools/provenance.py check`).
- Never push, never merge, never run a model. Task 5 is the maintainer's attended sitting; an executing agent stops before it.
- Exclusion scope (ruling R3): drop `src/satyrn_evals/tasks/selfhost-*/` from every base. Keep the five external tasks (`agentclinic-*` ×4, `format_number`), `KNOWN_DEFECTS.md`, and other tasks' specs.
- Record parameters (spec §5): Baseline arm, purpose `admission`, `confinement`, mode `batch`, n = 6, k = 3, 48,000 tokens / 72 turns, backstop 4,800 s, `max_minutes` 240, rung R2 for `agentclinic-repair-depth-3` and R1-plan for the other five.
- The machine is declared, never assumed comparable: the records say Apple M5 Max (128 GiB); the census evidence names no machine (ruling R4).
- Stop and ask on anything this plan did not foresee: a re-cut that differs beyond the removed paths, a public test that breaks for a reason other than naming a removed selfhost task, a step that fails acceptance twice.

## Review Focus

1. **A re-cut whose manifest differs beyond `digests.task_tree`.** For example, `expected_test_ids` re-collected differently by this interpreter's pytest would silently change what grades. Task 2 Step 8 compares old and new manifests key by key and stops on any other difference.
2. **The R0 §1.2 `validity` block is lost.** `cut()` does not write it, and five of the seven manifests carry one. Task 2 Step 7 carries it over, and Task 2 Step 1 adds a default-tier test that every census selfhost manifest still has it.
3. **A `base_edits` entry that hides more than the broken test.** Task 2 Step 10 allows a skip only on a test that fails because it names a removed selfhost task, and it compares the public suite's pass, skip and fail counts before and after.
4. **A C1 record that pins a tree a later commit moved.** Task 4's guard test checks each record against `tree_digest` of the current tree, so any later base change fails in the default tier.
5. **Old task trees left on disk.** The moved-aside copies in the scratch directory hold overlays and fixtures, which are grader material outside the repository. Task 2 Step 15 deletes them, and Task 5 Step 1 checks they are gone before the sitting.

---

### Task 1: The frozen-record check becomes a recorded revision chain

The census records pin the tree before the 2026-09-25 revision. The current check allows exactly one recorded revision, and C1 adds a second. This task changes the shape only: the chains hold today's two digests, and the default tier stays green.

**Files:**
- Modify: `tests/test_census_records_frozen.py:48-121`, the comment block, `REVISED_TASK_TREES`, `test_a_frozen_census_record_pins_the_current_task_tree` and `test_the_revision_map_is_real_and_traceable`.

**Interfaces:**
- Produces: `TASK_TREE_REVISIONS: dict[str, tuple[str, ...]]`, oldest first. `chain[0]` is the digest the frozen census records pin; `chain[-1]` is the committed tree. Task 2 appends one digest per census selfhost task.
- Produces: `revision_problem(task: str, pinned: str, current: str, chain: tuple[str, ...] | None) -> str | None`.

- [ ] **Step 1: Write the synthetic tests for the new check, both directions**

Append to `tests/test_census_records_frozen.py`:

```python
A, B, C = "a" * 64, "b" * 64, "c" * 64


def test_an_unrevised_task_that_matches_its_record_has_no_problem() -> None:
    assert revision_problem("t", A, A, None) is None


def test_an_unrevised_task_that_drifted_is_named() -> None:
    assert revision_problem("t", A, B, None) == (
        f"t: the record pins {A}, the tree is {B}; re-issue the record with `record new` before a night"
    )


def test_a_tree_at_its_last_recorded_revision_has_no_problem() -> None:
    assert revision_problem("t", A, C, (A, B, C)) is None


def test_a_tree_that_moved_past_its_last_recorded_revision_is_named() -> None:
    assert revision_problem("t", A, B, (A, B, C)) == (
        f"t is {B}, not its last recorded revision {C}; record the revision in TASK_TREE_REVISIONS"
    )


def test_a_record_that_does_not_pin_the_chains_first_digest_is_named() -> None:
    assert revision_problem("t", B, C, (A, B, C)) == (
        f"t: the record pins {B}, not {A}, the digest its revisions are recorded against"
    )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest -q tests/test_census_records_frozen.py -k "revision or unrevised or chains"`
Expected: FAIL with `NameError: name 'revision_problem' is not defined`.

- [ ] **Step 3: Replace the map, its comment, and the two tests that read it**

Replace everything from the line `#: 2026-09-25: the five self-hosted bases gained ...` through the closing `}` of `REVISED_TASK_TREES` with the block below. The five chains carry the same two digests the old map held, in the same order:

```python
#: Every recorded revision of a census task's tree since its census record was
#: frozen, oldest first: ``chain[0]`` is the digest the frozen census records
#: pin, each later entry is a recorded revision, and the last is the tree as
#: committed now. A frozen record is never re-issued to follow its task; the
#: revision is recorded here, with its reason, instead.
#:
#: 2026-09-25: the five self-hosted bases gained the two host-independence
#: fixes their public suites needed on Linux (`src/satyrn_evals/tasks/`
#: KNOWN_DEFECTS.md).
#:
#: 2026-09-27: `a194500` changed the bases but left every committed
#: `manifest.digests.task_tree` stale, so `cut_task check` could not pass. The
#: manifests were regenerated with the recorded `base_edits` that reproduce the
#: bases byte for byte; the manifest is inside `tree_digest(task_dir)`, so the
#: recorded revised digest moved even though no model-facing byte changed. The
#: census records still pin the pre-2026-09-25 digest, unchanged.
TASK_TREE_REVISIONS: dict[str, tuple[str, ...]] = {
    "selfhost-cell-loop": (
        "406487a854b78b38b615d23de3c20f18eed39b04610ce3e905ff997e542f3173",
        "65ea33d4b34f2b27e6271e6af9bc78a8da5af7348ede832171f40453f2e0b74b",
    ),
    "selfhost-docs-linter": (
        "a8c1aaf0e2d5136be35ed6e5d2bf49cb88e06e15c7217ed0b481edfbd090b1c6",
        "3e3f7adf7cd962ba04a0948e4bf60f1f9056fc8fb96b9b45a11e780e2da7333e",
    ),
    "selfhost-run-record-gate": (
        "a7c74e5449d5a82e155f9e0161b793697ac9c973323818fe335297faf114ebcc",
        "068f216e08ef0abee4d3f2b1042ed38d68aaac5a638004c06a1052e03f52be05",
    ),
    "selfhost-speed-probe": (
        "dbb752affe8df090fa8594e8f046383c3ac57e6657fbb7c6181f31331270df28",
        "be6946cd336d318a1e5d3d2e04a6be6ab0fdbfa4be9f145841fdc52145cc26cd",
    ),
    "selfhost-preflight-quiet": (
        "1edcf796591ec22e9c19187744d43706f840e4fdc05dbe790f925c06cac86aa0",
        "0567373a69595a8c642b8332df407f83feedb06c4aefc706c2269bba122a5e25",
    ),
}


def revision_problem(task: str, pinned: str, current: str, chain: tuple[str, ...] | None) -> str | None:
    """Why a frozen census record no longer matches its task's tree, or None.

    With no recorded revisions the record must pin the tree as it is. With a
    chain, the tree must be the chain's last entry and the record must pin its
    first, so an unrecorded drift fails and so does a record that was quietly
    re-issued.
    """
    if chain is None:
        if pinned == current:
            return None
        return f"{task}: the record pins {pinned}, the tree is {current}; re-issue the record with `record new` before a night"
    if current != chain[-1]:
        return f"{task} is {current}, not its last recorded revision {chain[-1]}; record the revision in TASK_TREE_REVISIONS"
    if pinned != chain[0]:
        return f"{task}: the record pins {pinned}, not {chain[0]}, the digest its revisions are recorded against"
    return None
```

Replace the body of `test_a_frozen_census_record_pins_the_current_task_tree` (keep its decorator and signature):

```python
    record = json.loads(record_path.read_text())
    task = record["task"]
    current = tree_digest(DEFAULT_TASKS_ROOT / task)
    assert revision_problem(task, record["task_tree_sha256"], current, TASK_TREE_REVISIONS.get(task)) is None
```

Replace `test_the_revision_map_is_real_and_traceable` with:

```python
def test_the_revision_map_is_real_and_traceable() -> None:
    """Each chain records at least one revision, never repeats a digest, and
    starts at exactly what a frozen census record pins -- so the relaxation
    cannot hide a drift it was not recorded against."""
    census = {json.loads(p.read_text())["task"]: json.loads(p.read_text())["task_tree_sha256"] for p in NIGHT1 + NIGHT2 + NIGHT3}
    for task, chain in TASK_TREE_REVISIONS.items():
        assert len(chain) >= 2, task
        assert len(set(chain)) == len(chain), task
        assert census[task] == chain[0], task
```

- [ ] **Step 4: Run the file to verify everything passes**

Run: `uv run pytest -q tests/test_census_records_frozen.py`
Expected: PASS. `grep -n REVISED_TASK_TREES tests/` prints nothing.

- [ ] **Step 5: Gates and commit**

Run: `just gates; echo "exit $?"`. Expected: `exit 0`.

```bash
git add tests/test_census_records_frozen.py
git commit -m "census records: a recorded revision chain per task, not one revision

Shape only: the chains hold the two digests the old map held. C1 appends
the re-cut digest (docs/superpowers/specs/2026-10-02-c1-requalify-design.md §3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Exclude nested selfhost tasks from every base, and re-cut the seven

**Files:**
- Modify: `tools/cut_task.py`, the module docstring's `base/` bullet, a new `SELFHOST_TASKS_PREFIX` constant beside `EXCLUDED_PREFIXES`, and `excluded()` with its docstring.
- Modify: `tests/test_cut_task.py`, two new tests after `test_another_tasks_cut_tree_stays_in_the_base`.
- Modify: `tests/test_task_base_residue.py`, a nested-root predicate, the guard, and two sibling tests.
- Modify: `tests/test_census_records_frozen.py`, one digest appended to each chain, and a C1 paragraph in the comment.
- Modify: `tools/task_specs/selfhost-*.json`, only if Step 10 records a `base_edits` entry.
- Replace: `src/satyrn_evals/tasks/selfhost-{cell-loop,docs-linter,guard-prefixes,preflight-quiet,review-script,run-record-gate,speed-probe}/`, re-cut.
- Modify: `PROVENANCE.md`, rows for removed paths dropped.

**Interfaces:**
- Consumes: `TASK_TREE_REVISIONS` (Task 1).
- Produces: `SELFHOST_TASKS_PREFIX = "src/satyrn_evals/tasks/selfhost-"` in `tools/cut_task.py`, and `nested_selfhost_roots(base: Path) -> list[Path]` in `tests/test_task_base_residue.py`. It also produces the re-cut trees whose `tree_digest` Task 4's records pin.

Every command below uses `S="${TMPDIR:-/tmp}/satyrn-c1-recut"` as the scratch directory. Set it in each shell you open.

- [ ] **Step 1: Write the failing tests**

In `tests/test_cut_task.py`, after `test_another_tasks_cut_tree_stays_in_the_base`:

```python
def test_every_self_hosted_tasks_cut_tree_stays_out_of_every_base() -> None:
    """C1 (2026-10-02-c1-requalify-design.md, ruling R3): a self-hosted task's
    base is this repository, so archiving another self-hosted task into it
    nests the repository inside itself, four levels deep on preflight-quiet."""
    assert excluded("src/satyrn_evals/tasks/selfhost-other/manifest.json", [], "t")
    assert excluded("src/satyrn_evals/tasks/selfhost-other/base/src/satyrn_evals/cli.py", [], "t")


def test_an_external_tasks_cut_tree_and_a_self_hosted_spec_stay_in_the_base() -> None:
    """The success sibling: the public suites use the external tasks as fixtures."""
    assert not excluded("src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json", [], "t")
    assert not excluded("src/satyrn_evals/tasks/format_number/base/x.py", [], "t")
    assert not excluded("src/satyrn_evals/tasks/KNOWN_DEFECTS.md", [], "t")
    assert not excluded("tools/task_specs/selfhost-other.json", [], "t")
```

In `tests/test_task_base_residue.py`, after `residue_paths`:

```python
def nested_selfhost_roots(base: Path) -> list[Path]:
    """Self-hosted task directories inside a base, relative to it (C1, ruling R3)."""
    tasks = base / "src" / "satyrn_evals" / "tasks"
    if not tasks.is_dir():
        return []
    return sorted(path.relative_to(base) for path in tasks.glob("selfhost-*") if path.is_dir())


def test_no_persisted_task_base_nests_a_self_hosted_task() -> None:
    nested = {
        str(base.relative_to(TASKS_ROOT)): found
        for base in sorted(TASKS_ROOT.glob("*/base"))
        if (found := nested_selfhost_roots(base))
    }
    assert nested == {}


def test_the_nesting_predicate_finds_nothing_beside_external_tasks(tmp_path: Path) -> None:
    """The success sibling: external fixture tasks stay and are not nesting."""
    (tmp_path / "src" / "satyrn_evals" / "tasks" / "format_number" / "base").mkdir(parents=True)
    assert nested_selfhost_roots(tmp_path) == []


def test_the_nesting_predicate_names_a_nested_self_hosted_task(tmp_path: Path) -> None:
    (tmp_path / "src" / "satyrn_evals" / "tasks" / "selfhost-x" / "base").mkdir(parents=True)
    assert nested_selfhost_roots(tmp_path) == [Path("src/satyrn_evals/tasks/selfhost-x")]
```

In `tests/test_census_records_frozen.py`, after `test_a_cut_census_task_carries_no_authored_disclosure`. This pins Review Focus line 2:

```python
@pytest.mark.parametrize("task", sorted(t for t in CENSUS_TASKS if t.startswith("selfhost-")))
def test_every_census_selfhost_task_keeps_its_validity_block(task: str) -> None:
    """A re-cut does not write the R0 §1.2 `validity` block (`cut_task.py`
    POST_CUT_MANIFEST_KEYS); C1 carries it over by hand, and this catches a
    re-cut that dropped it."""
    validity = json.loads((DEFAULT_TASKS_ROOT / task / "manifest.json").read_text()).get("validity")
    assert validity is not None and validity["passed"] is True, task
```

- [ ] **Step 2: Run them to verify the right ones fail**

Run: `uv run pytest -q tests/test_cut_task.py tests/test_task_base_residue.py tests/test_census_records_frozen.py`
Expected: `test_every_self_hosted_tasks_cut_tree_stays_out_of_every_base` FAILS, and `test_no_persisted_task_base_nests_a_self_hosted_task` FAILS, naming all seven selfhost bases. Everything else, including the validity test, PASSES.

- [ ] **Step 3: Implement the exclusion**

In `tools/cut_task.py`, add the constant after `EXCLUDED_FILES`:

```python
#: Every self-hosted task's cut tree, not only the task's own: a self-hosted
#: base is this repository, so archiving another self-hosted task into it nests
#: the repository inside itself (C1, 2026-10-02-c1-requalify-design.md, R3).
#: External tasks stay; the public suites use them as fixtures.
SELFHOST_TASKS_PREFIX = "src/satyrn_evals/tasks/selfhost-"
```

In `excluded()`, change the first condition so that it reads:

```python
    if path in EXCLUDED_FILES or path in set(hidden) or path.startswith((*EXCLUDED_PREFIXES, SELFHOST_TASKS_PREFIX)):
        return True
```

Append this sentence to `excluded()`'s docstring paragraph: "Every self-hosted task's cut tree stays out of every base, because a self-hosted base is this repository; the external tasks stay as the public suites' fixtures." In the module docstring's first bullet, change "minus plans, specs, ``.claude``, ``.github``, ``PROVENANCE.md`` and the HIDDEN files" to "minus plans, specs, ``.claude``, ``.github``, ``PROVENANCE.md``, every self-hosted task's cut tree and the HIDDEN files".

- [ ] **Step 4: Run the unit tests**

Run: `uv run pytest -q tests/test_cut_task.py`
Expected: PASS. The residue guard still fails, because the bases are not re-cut yet.

- [ ] **Step 5: Record the before-state, on the old trees**

Extract the committed old trees from `HEAD`, so no ignored or untracked file comes along, then record their self-test facts:

```bash
S="${TMPDIR:-/tmp}/satyrn-c1-recut"; rm -rf "$S"; mkdir -p "$S/old"
for t in src/satyrn_evals/tasks/selfhost-*/; do
  git archive HEAD -- "${t%/}" | tar -x -C "$S/old" --strip-components 3
done
ls "$S/old"
```

Expected: the seven selfhost directories.

```bash
S="${TMPDIR:-/tmp}/satyrn-c1-recut"
uv run python - "$S/old" "$S/selftest-before.json" <<'EOF'
import json, sys
from pathlib import Path
from satyrn_evals.manifest import load_manifest
from satyrn_evals.task_selftest import task_self_test
root, out = Path(sys.argv[1]), Path(sys.argv[2])
facts = {}
for task_dir in sorted(root.glob("selfhost-*")):
    result = task_self_test(task_dir, load_manifest(task_dir))
    facts[task_dir.name] = {"problems": result.problems, "checked": result.checked}
    print(task_dir.name, "problems:", result.problems)
out.write_text(json.dumps(facts, indent=2, default=str))
EOF
echo "exit $?"
```

Expected: seven lines and `exit 0`. If any old tree already has self-test problems, write them down. They are pre-existing, and Step 10 compares against them; do not fix them.

- [ ] **Step 6: Re-cut the seven tasks**

`cut()` refuses to overwrite a task, so remove each task directory and cut it again from its spec:

```bash
for s in tools/task_specs/selfhost-*.json; do
  t=$(basename "$s" .json)
  rm -rf "src/satyrn_evals/tasks/$t"
  uv run python tools/cut_task.py cut "$s" || { echo "cut failed: $t"; break; }
done
echo "exit $?"
```

Expected: seven task paths printed, no `cut failed`, `exit 0`.

- [ ] **Step 7: Carry each `validity` block over**

```bash
S="${TMPDIR:-/tmp}/satyrn-c1-recut"
uv run python - "$S/old" <<'EOF'
import json, sys
from pathlib import Path
old_root = Path(sys.argv[1])
for old in sorted(old_root.glob("selfhost-*/manifest.json")):
    validity = json.loads(old.read_text()).get("validity")
    if validity is None:
        continue
    new = Path("src/satyrn_evals/tasks") / old.parent.name / "manifest.json"
    body = json.loads(new.read_text())
    body["validity"] = validity
    new.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    print("validity carried:", old.parent.name)
EOF
```

Expected: five lines: cell-loop, docs-linter, preflight-quiet, run-record-gate and speed-probe. The `validity` key is last in each old manifest, so appending it keeps the key order.

- [ ] **Step 8: Verify the re-cut changed only what the design allows**

```bash
S="${TMPDIR:-/tmp}/satyrn-c1-recut"
uv run python - "$S/old" <<'EOF'
import json, sys
from pathlib import Path
old_root, new_root = Path(sys.argv[1]), Path("src/satyrn_evals/tasks")
nested = "base/src/satyrn_evals/tasks/selfhost-"
bad = []
for old in sorted(old_root.glob("selfhost-*")):
    new = new_root / old.name
    files = lambda root: {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    o, n = files(old), files(new)
    removed, added = o - n, n - o
    bad += [f"{old.name}: removed {p}" for p in removed if not p.startswith(nested)]
    bad += [f"{old.name}: added {p}" for p in added]
    for p in sorted(o & n):
        if p != "manifest.json" and (old / p).read_bytes() != (new / p).read_bytes():
            bad.append(f"{old.name}: changed {p}")
    om, nm = json.loads((old / "manifest.json").read_text()), json.loads((new / "manifest.json").read_text())
    om["digests"].pop("task_tree"); nm["digests"].pop("task_tree")
    if om != nm:
        keys = sorted(k for k in set(om) | set(nm) if om.get(k) != nm.get(k))
        bad.append(f"{old.name}: manifest differs beyond digests.task_tree in {keys}")
    print(f"{old.name}: {len(removed)} nested paths removed, {len(n)} files now")
print("\n".join(bad) or "only nested selfhost paths and digests.task_tree changed")
sys.exit(1 if bad else 0)
EOF
echo "exit $?"
```

Expected: preflight-quiet removes about 3,821 paths, cell-loop and speed-probe about 1,092 each, the other four about 44 each. The last line is `only nested selfhost paths and digests.task_tree changed`, then `exit 0`. **Any other line is a stop:** report it to the maintainer and do not continue.

- [ ] **Step 9: Self-test the new bases**

```bash
S="${TMPDIR:-/tmp}/satyrn-c1-recut"
uv run python - "$S/selftest-before.json" <<'EOF'
import json, sys
from pathlib import Path
from satyrn_evals.manifest import load_manifest
from satyrn_evals.task_selftest import task_self_test
before = json.loads(Path(sys.argv[1]).read_text())
moved = []
for name in sorted(before):
    task_dir = Path("src/satyrn_evals/tasks") / name
    result = task_self_test(task_dir, load_manifest(task_dir))
    was = before[name]
    keys = ("base_exit", "known_good_exit", "repair_base")
    now, then = {k: result.checked.get(k) for k in keys}, {k: was["checked"].get(k) for k in keys}
    print(name, "problems:", result.problems, "now:", now, "before:", then)
    if now != then or bool(result.problems) != bool(was["problems"]):
        moved.append(name)
print("moved:", moved)
sys.exit(1 if moved else 0)
EOF
echo "exit $?"
```

Expected: `moved: []` and `exit 0`; then skip Step 10. If a task moved, go to Step 10 for that task only.

- [ ] **Step 10: Only if Step 9 moved a task: find the failing public tests and record the edit**

For each moved task `T`, run its public suite at known-good in a copy and list the failures:

```bash
S="${TMPDIR:-/tmp}/satyrn-c1-recut"; T=selfhost-preflight-quiet   # the moved task
rm -rf "$S/probe" && cp -R "src/satyrn_evals/tasks/$T/base" "$S/probe" && cd "$S/probe" \
  && git init -q && git apply "$OLDPWD/src/satyrn_evals/tasks/$T/fixtures/known-good.patch" \
  && uv run pytest -q -rfE 2>&1 | tail -40; cd "$OLDPWD"
```

Do the same in a copy of `$S/old/$T/base` and compare the pass/skip/fail counts.

A failure qualifies for a recorded edit **only** if it fails because the test names or reads a `selfhost-*` task that the re-cut removed (for example `tests/test_census_records_frozen.py` resolving `DEFAULT_TASKS_ROOT / "selfhost-cell-loop"`). For each qualifying test, add a `base_edits` entry to `tools/task_specs/$T.json` in this shape:

- `path`: the test file.
- `old`: the test's own `def test_...(` line, exactly once in the file.
- `new`: `@pytest.mark.skip(reason="C1: names a self-hosted task the C1 cut excludes from this base")\n` followed by that same line.
- `reason`: one sentence naming the removed task the test reads and citing `docs/superpowers/specs/2026-10-02-c1-requalify-design.md` §2.3.

If the failure happens at collection (a module-level read), use instead `old` = the module's first `import` line, and `new` = `import pytest\n\npytest.skip("C1: names a self-hosted task the C1 cut excludes from this base", allow_module_level=True)\n` followed by that line. Because the skip sits above every import, nothing in the module can fail at collection before it.

Then re-cut `T` alone (`rm -rf src/satyrn_evals/tasks/$T && uv run python tools/cut_task.py cut tools/task_specs/$T.json`), repeat Step 7 for it, and re-run Step 9. The skip count may rise only by the tests you marked. **Stop and report if:**
- a failure doesn't name a removed selfhost task;
- the same task needs a second round;
- the base exit code changed.

- [ ] **Step 11: Offline qualification and the fresh-cut check**

```bash
uv run satyrn-evals qualify agentclinic-repair-depth-3 selfhost-cell-loop selfhost-docs-linter selfhost-guard-prefixes selfhost-preflight-quiet selfhost-review-script selfhost-run-record-gate selfhost-speed-probe; echo "exit $?"
uv run pytest -m integration -q tests/integration/test_cut_task.py; echo "exit $?"
```

Expected: every check `ok` and `exit 0`, then the integration file passes and `exit 0`. `qualify` drives the real Baseline adapter, which now loads the confinement extension, so this is the re-qualification on this harness. It uses no model.

- [ ] **Step 12: Append the C1 digest to each census chain**

```bash
uv run python -c "
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.task_tree import tree_digest
for t in ['selfhost-cell-loop','selfhost-docs-linter','selfhost-run-record-gate','selfhost-speed-probe','selfhost-preflight-quiet']:
    print(t, tree_digest(DEFAULT_TASKS_ROOT / t))
"
```

In `tests/test_census_records_frozen.py`, append each printed digest as the third entry of that task's chain in `TASK_TREE_REVISIONS`. Add this paragraph to the comment, after the 2026-09-27 paragraph:

```python
#:
#: C1 (2026-10-02-c1-requalify-design.md): every self-hosted base was re-cut
#: without the other self-hosted task trees nested in it (the cleanup audit's
#: P0, evidence/2026-10-02-cleanup-audit/README.md §1); the prompt is
#: byte-identical, and the census records still pin the pre-2026-09-25 digest.
```

- [ ] **Step 13: Drop the provenance rows of removed paths**

```bash
uv run python - <<'EOF'
from pathlib import Path
path = Path("PROVENANCE.md")
kept, dropped = [], 0
for line in path.read_text().splitlines(keepends=True):
    cell = line.split("|")[1].strip() if line.startswith("| ") else ""
    if cell.startswith("src/satyrn_evals/tasks/") and not Path(cell).exists():
        dropped += 1
        continue
    kept.append(line)
path.write_text("".join(kept))
print("dropped", dropped)
EOF
```

Expected: about 6,000 dropped. Then run `uv run python tools/provenance.py check; echo "exit $?"` and expect `exit 0`. If it names a file, that file is new in a re-cut: give it a row in the existing selfhost-base style, copying the source text of a sibling row from the same task, then re-run the check.

- [ ] **Step 14: Full gates**

Run: `just gates; echo "exit $?"`
Expected: `exit 0`, with the nesting guard, the validity test and the frozen-record chain all passing.

- [ ] **Step 15: Remove the scratch copies and commit**

```bash
rm -rf "${TMPDIR:-/tmp}/satyrn-c1-recut"
git add -A tools/cut_task.py tools/task_specs tests/test_cut_task.py tests/test_task_base_residue.py tests/test_census_records_frozen.py src/satyrn_evals/tasks PROVENANCE.md
git status --short | grep -v '^D ' | head -20
```

Expected: the deletions plus the modified files above; nothing unexpected. Commit, listing each task's new digest from Step 12 (and guard-prefixes and review-script from `tree_digest` too) in the body:

```bash
git commit -m "C1: re-cut the seven self-hosted bases without nested self-hosted tasks

cut_task excludes src/satyrn_evals/tasks/selfhost-*/ from every base
(2026-10-02-c1-requalify-design.md, R3). Prompts byte-identical; validity
blocks carried over; offline qualify passes on this harness.

<one line per task: name old-digest -> new-digest>

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Retire the dead `--cell` path and head the frozen census scripts

**Files:**
- Modify: `src/satyrn_evals/launch_record.py`, the module docstring items 3, 4 and 6, `settings_provenance`, the `settings` field of the facts dataclass (line 184), and its two call sites (lines 364 and 393).
- Modify: `tests/test_launch_record.py`, the three `settings=lambda path, cell: ...` fakes (lines 46, 160 and 428).
- Modify: `src/satyrn_evals/cli.py`, the `--preflight` help (line 717) and `_launch_preflight`'s docstring.
- Modify: `scripts/preflight_settings.py`, the docstring's `--cell` paragraph (lines 45-48) and the usage line (line 54).
- Modify: `scripts/census_night.sh`, `scripts/census_night_2.sh` and `scripts/census_night_3.sh`, a header after line 1.
- Create: `tests/test_retired_cell_flag.py`.

**Interfaces:**
- Produces: `settings_provenance(arm_path: Path) -> tuple[int, str]`; the facts field becomes `settings: Callable[[Path], tuple[int, str]]`.
- Produces: `HISTORICAL_MARK = "# HISTORICAL: frozen evidence for the isolated census nights"` and `retired_flag_callers(paths: Iterable[Path]) -> list[str]` in the new test file.

- [ ] **Step 1: Write the failing guard test, both directions**

Create `tests/test_retired_cell_flag.py`:

```python
"""No live code passes ``--cell``, the flag ``preflight_settings.py`` lost with
the two-uid harness (2026-09-27); only files headed as historical may still
name it (2026-10-02-c1-requalify-design.md §4). No model, network, or subprocess.
"""

import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORICAL_MARK = "# HISTORICAL: frozen evidence for the isolated census nights"
RETIRED = re.compile(r"--cell(?![\w-])")


def retired_flag_callers(paths: Iterable[Path]) -> list[str]:
    """Files that name ``--cell`` and are not headed as historical."""
    return sorted(
        path.name
        for path in paths
        if RETIRED.search(text := path.read_text()) and HISTORICAL_MARK not in text
    )


def _live() -> list[Path]:
    return sorted([*(ROOT / "src" / "satyrn_evals").glob("*.py"), *(ROOT / "scripts").glob("*")])


def test_no_live_file_names_the_retired_cell_flag() -> None:
    assert retired_flag_callers(p for p in _live() if p.is_file()) == []


def test_a_historical_file_and_a_cell_dir_flag_are_not_callers(tmp_path: Path) -> None:
    (tmp_path / "old.sh").write_text(f"#!/bin/sh\n{HISTORICAL_MARK}\nx.py --cell\n")
    (tmp_path / "timing.py").write_text('p.add_argument("--cell-dir")\n')
    assert retired_flag_callers(sorted(tmp_path.iterdir())) == []


def test_an_unheaded_caller_is_named(tmp_path: Path) -> None:
    (tmp_path / "live.sh").write_text("#!/bin/sh\nx.py --cell\n")
    assert retired_flag_callers([tmp_path / "live.sh"]) == ["live.sh"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest -q tests/test_retired_cell_flag.py`
Expected: `test_no_live_file_names_the_retired_cell_flag` FAILS, naming `census_night.sh`, `census_night_2.sh`, `census_night_3.sh`, `launch_record.py` and `preflight_settings.py`. The other two tests PASS.

- [ ] **Step 3: Head the three census scripts**

Insert these four lines after line 1 (`#!/bin/sh`) of each of `scripts/census_night.sh`, `scripts/census_night_2.sh` and `scripts/census_night_3.sh`, and change nothing else in them:

```sh
# HISTORICAL: frozen evidence for the isolated census nights (two-uid harness,
# retired 2026-09-27, 35c298d). Not runnable under confinement: it calls
# `preflight_settings.py --cell`, a flag that no longer exists. C3 runs from its
# own driver (docs/superpowers/specs/2026-10-02-c1-requalify-design.md §4).
```

- [ ] **Step 4: Remove the dead branch**

In `src/satyrn_evals/launch_record.py`:

```python
def settings_provenance(arm_path: Path) -> tuple[int, str]:
    """``preflight_settings.py`` for one arm: its exit code and its provenance JSON."""
    ran = subprocess.run(
        [sys.executable, os.fspath(SETTINGS_SCRIPT), os.fspath(arm_path)],
        capture_output=True, text=True, check=False,
    )
    return ran.returncode, ran.stdout if ran.returncode == 0 else ran.stdout + ran.stderr
```

Change the facts field to `settings: Callable[[Path], tuple[int, str]] = settings_provenance`, and the two call sites from `facts.settings(path, False)` to `facts.settings(path)`. In the module docstring:
- Item 3: change "and a deciding purpose is isolated" to "and the record names the current `confinement`".
- Item 4: replace it with "4. the confinement preflight (``cell_preflight.preflight_confinement``) is clean, and an Engine arm's checkout is the commit and bytes it pins (``cell_engine.engine_checkout_problems``);".
- Item 6: replace it with "6. ``scripts/preflight_settings.py`` exits 0 for every arm; its provenance block is kept for the drift check."

In `tests/test_launch_record.py`, change the three fakes from `lambda path, cell:` to `lambda path:`.

In `src/satyrn_evals/cli.py`:
- Change the `--preflight` help to `"run record JSON path to preflight under confinement"`.
- Change `_launch_preflight`'s docstring first line to `"""The confinement preflight, for every arm the record runs; the JSON report goes to stdout, each problem to stderr."""`.

In `scripts/preflight_settings.py`:
- Delete the docstring paragraph that begins "File reads, with one exception: ``--cell`` reads the cell user's" and ends "names the cell's file as its Pi source." together with its trailing blank line.
- Change the usage line `[--pi-models ~/.pi/agent/models.json | --cell] \\` to `[--pi-models ~/.pi/agent/models.json] \\`.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q tests/test_retired_cell_flag.py tests/test_launch_record.py`
Expected: PASS.

- [ ] **Step 6: Provenance, gates, commit**

Append to `PROVENANCE.md`:

```
| tests/test_retired_cell_flag.py | created <today's date> on phase-c1; guard that no live file passes the retired --cell flag (C1 design §4) |
```

Run: `just gates; echo "exit $?"`. Expected: `exit 0`.

```bash
git add src/satyrn_evals/launch_record.py src/satyrn_evals/cli.py scripts/preflight_settings.py scripts/census_night.sh scripts/census_night_2.sh scripts/census_night_3.sh tests/test_launch_record.py tests/test_retired_cell_flag.py PROVENANCE.md
git commit -m "launcher: drop the dead --cell branch; head the frozen census scripts as historical

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The six C1 records and their guard

**Files:**
- Create: `tests/test_c1_records.py`.
- Create: `records/<date>-c1-<task>.json` ×6, where `<date>` is the day they are issued (`date +%F`).
- Modify: `PROVENANCE.md`.

**Interfaces:**
- Consumes: the re-cut trees (Task 2); `CENSUS_TASKS` (`satyrn_evals.qualify`); `CONFINEMENT` (`satyrn_evals.run_record`, value `"extension"`).
- Produces: six frozen records whose paths match `records/*-c1-*.json`, which Task 5 preflights.

- [ ] **Step 1: Write the guard test**

Create `tests/test_c1_records.py`:

```python
"""The six C1 records carry the design's parameters and pin the current task
trees (docs/superpowers/specs/2026-10-02-c1-requalify-design.md §5). A base
that moves after they were issued fails here, before any sitting.
No model, network, or subprocess.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.qualify import CENSUS_TASKS
from satyrn_evals.run_record import CONFINEMENT
from satyrn_evals.task_tree import tree_digest

ROOT = Path(__file__).resolve().parent.parent
DESIGN = "docs/superpowers/specs/2026-10-02-c1-requalify-design.md"
MACHINE = "Apple M5 Max"
C1 = sorted(p for p in (ROOT / "records").glob("*-c1-*.json") if not p.name.endswith(".result.json"))
EXPECTED = {
    "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit", "backend": "omlx",
    "purpose": "admission", "confinement": CONFINEMENT, "mode": "batch", "n": 6, "k": 3,
    "token_budget": 48_000, "turn_budget": 72, "command_backstop_s": 4_800, "max_minutes": 240,
    "previous_result": None,
}


def c1_problems(record: dict, current_tree: str) -> list[str]:
    """Every way a record departs from the design's §5 table, or ``[]``."""
    problems = [
        f"{key} is {record.get(key)!r}, want {want!r}"
        for key, want in EXPECTED.items()
        if record.get(key) != want
    ]
    if record.get("rung") != CENSUS_TASKS.get(record.get("task", "")):
        problems.append(f"rung is {record.get('rung')!r}, want {CENSUS_TASKS.get(record.get('task', ''))!r}")
    if record.get("task_tree_sha256") != current_tree:
        problems.append("task_tree_sha256 is not the current tree")
    authority = record.get("authority") or ""
    if DESIGN not in authority or MACHINE not in authority:
        problems.append("authority does not name the C1 design and the machine")
    return problems


def test_the_c1_records_are_exactly_the_census_set() -> None:
    tasks = [json.loads(p.read_text())["task"] for p in C1]
    assert sorted(tasks) == sorted(CENSUS_TASKS)


@pytest.mark.parametrize("path", C1, ids=lambda p: p.stem)
def test_a_c1_record_carries_the_design_and_pins_the_current_tree(path: Path) -> None:
    record = json.loads(path.read_text())
    assert c1_problems(record, tree_digest(DEFAULT_TASKS_ROOT / record["task"])) == []


def test_the_check_names_a_changed_budget_and_a_drifted_tree() -> None:
    """The refusal sibling, on a real record with one field changed at a time."""
    record = json.loads(C1[0].read_text())
    current = tree_digest(DEFAULT_TASKS_ROOT / record["task"])
    assert c1_problems({**record, "token_budget": 32_000}, current) == ["token_budget is 32000, want 48000"]
    assert c1_problems(record, "0" * 64) == ["task_tree_sha256 is not the current tree"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest -q tests/test_c1_records.py`
Expected: `test_the_c1_records_are_exactly_the_census_set` FAILS (`[] != [...]`), and `test_the_check_names_a_changed_budget_and_a_drifted_tree` ERRORS with an `IndexError`, because no record exists yet.

- [ ] **Step 3: Issue the six records**

```bash
D=$(date +%F)
RECUT=$(git log -1 --format=%h --grep "^C1: re-cut the seven")
echo "re-cut commit: $RECUT"
AUTH="maintainer-approved C1 design docs/superpowers/specs/2026-10-02-c1-requalify-design.md, approved 2026-10-02: Baseline re-qualification of the census under confinement, on the self-hosted bases re-cut at $RECUT; runs on an Apple M5 Max (128 GiB); the census it re-derives (records/2026-09-1[678]-census*) ran on an earlier machine its evidence does not name, and is never pooled with these"
RULE="none for outcomes: the classified table at C3 decides (docs/superpowers/specs/2026-10-02-c1-requalify-design.md section 5), not a pass count"
for T in agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe selfhost-preflight-quiet; do
  case $T in agentclinic-repair-depth-3) RUNG=R2;; *) RUNG=R1-plan;; esac
  uv run satyrn-evals record new --output "records/$D-c1-$T.json" --task "$T" --arm baseline --rung "$RUNG" \
    --n 6 --k 3 --purpose admission --mode batch --max-minutes 240 --command-backstop 4800 \
    --token-budget 48000 --turn-budget 72 --authority "$AUTH" --decision-rule "$RULE" \
    || { echo "record new failed: $T"; break; }
done
ls records/*-c1-*.json
```

Expected: `re-cut commit:` prints a hash (if it is empty, stop), no `record new failed`, and six files listed.

- [ ] **Step 4: Run the guard**

Run: `uv run pytest -q tests/test_c1_records.py`
Expected: PASS (8 tests).

- [ ] **Step 5: Provenance, gates, commit**

Append one `PROVENANCE.md` row per new file, using the real issued date:

```
| tests/test_c1_records.py | created <date> on phase-c1; guard that the C1 records carry the design's parameters and pin the current trees |
| records/<date>-c1-<task>.json | created <date> on phase-c1 by `satyrn-evals record new`; C1 Baseline census record under confinement (C1 design §5) |
```

The record row appears six times, once per task.

Run: `just gates; echo "exit $?"`. Expected: `exit 0`.

```bash
git add tests/test_c1_records.py records/*-c1-*.json PROVENANCE.md
git commit -m "C1: six Baseline census records under confinement

Census parameters with nights 2-3's 4,800 s backstop; the machine declared
(2026-10-02-c1-requalify-design.md §5, R4). Not launched: C3 decides that.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**An executing agent stops here.** Report the four commits and hand Task 5 to the maintainer.

---

### Task 5: The preflight sitting (attended, the maintainer)

This uses no inference. It needs oMLX serving `Ornith-1.5-9B-MLX-8bit` with the 16,000 per-turn cap, because `launch --preflight` asks the server `GET /v1/models` and `preflight_settings.py` reads the served settings. The maintainer runs these commands, or approves each one in the sitting.

**Files:**
- Create: `evidence/<date>-c1-preflight/README.md` and one `<task>.json` per record.
- Modify: `PROVENANCE.md`.

- [ ] **Step 1: Check the machine and that no old trees are left**

```bash
sysctl -n machdep.cpu.brand_string hw.memsize
ls "${TMPDIR:-/tmp}/satyrn-c1-recut" 2>/dev/null && echo "STOP: old trees still on disk" || echo "scratch clean"
git status --short
```

Expected: `Apple M5 Max`, `137438953472`, `scratch clean`, and a clean tree.

- [ ] **Step 2: Settings provenance for the Baseline arm**

```bash
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json; echo "exit $?"
```

Expected: `exit 0`. Anything else means the oMLX entry or `~/.pi/agent/models.json` is not at 16,000 (`max_tokens`) or the arm's sampling. Fix it on the host and re-run; that is a host fix, not a harness change.

- [ ] **Step 3: Preflight each record**

```bash
D=<the issued date>; mkdir -p "evidence/$D-c1-preflight"
for R in records/$D-c1-*.json; do
  T=$(basename "$R" .json); T=${T#$D-c1-}
  uv run satyrn-evals launch --preflight "$R" --arm arms/baseline-ornith15-9b.json > "evidence/$D-c1-preflight/$T.json"
  echo "$T exit $?"
done
```

Expected: six lines ending `exit 0`. A non-zero exit lists its problems on stderr and in the JSON `problems` array. Do not re-issue a record to make it pass; bring the problem back as a finding.

- [ ] **Step 4: The evidence README and commit**

Write `evidence/<date>-c1-preflight/README.md`, ≤ 40 lines. It states:
- the machine (Step 1 output);
- Step 2's exit code;
- each record's preflight exit code and its `task_self_test` facts from the JSON;
- the commit the records were issued at;
- the recompute command, which is Step 3's loop.

Add PROVENANCE rows for the README and the six JSON files, run `just gates; echo "exit $?"` (expect `exit 0`), and commit with the message `C1: preflight passes on the six records (this machine)`.

---

### Task 6: Close out C1

**Files:**
- Modify: `evidence/2026-09-15-release-one-decision-ledger.md` (append), `ROADMAP.md` (the C1 row and one cleanup bullet).

- [ ] **Step 1: The ledger entry**

Append to `evidence/2026-09-15-release-one-decision-ledger.md`:

```markdown
## <date> — C1: the census re-qualified under confinement (re-cut <re-cut short sha>)

- Design: docs/superpowers/specs/2026-10-02-c1-requalify-design.md (approved 2026-10-02; rulings R1-R4).
- Re-cut: every self-hosted base without the other self-hosted task trees; prompts byte-identical; R0 §1.2 validity blocks carried over (measured on the nested bases; the prompt they certify is unchanged). Task trees, old -> new: <one line per task from the Task 2 commit body>.
- Records: records/<date>-c1-*.json (six, Baseline, admission, confinement); preflight exit 0 on each, evidence/<date>-c1-preflight/README.md.
- Machine: Apple M5 Max, 128 GiB; the census evidence names no machine, so nothing here pools with it.
- Clears nothing: every C0 mark stands until C3's table and C4's counterfactual name their re-derivations. Next piece is C2 (measurement), not another instrument fix.
```

- [ ] **Step 2: The roadmap**

In `ROADMAP.md`:
- Append to the C1 row's "Done when" cell: ` done <date>: ledger entry "C1", re-cut <sha>, records records/<date>-c1-*`.
- In "Cleanup, 2026-10-02", delete the "**Un-nest the task bases.**" bullet.
- In the same section, change the census-scripts bullet's first sentence to end with "— headed as historical and the launcher's dead branch removed at C1; the engine's red-stop receipt fix remains."

- [ ] **Step 3: Gates and commit**

Run: `just gates; echo "exit $?"`. Expected: `exit 0`.

```bash
git add evidence/2026-09-15-release-one-decision-ledger.md ROADMAP.md
git commit -m "C1 done: ledger entry and roadmap row

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
