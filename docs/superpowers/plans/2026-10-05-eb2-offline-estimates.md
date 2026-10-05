# EB2 — offline remedy estimates on the 23a0ef6 cells — Implementation Plan

> **Executed 2026-10-05 with controller rulings that supersede parts of Tasks 3–5; see the decision ledger entry '2026-10-05 — EB2 executed'.**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For each candidate Engine-budget remedy, state an offline estimate on the retained 23a0ef6 cells of what it can save, and whether that can clear the floor-parity threshold, before any remedy is specified or built.

**Architecture:** This is one stdlib script, `evidence/2026-10-05-eb2-estimates/eb2.py`. It reuses EB1's classification unchanged (`eb1.py`, loaded by path, digest frozen) and the cell read's slot enumeration (`read_cells.py`, loaded by path, digest frozen). It adds three things EB1 lacked: a loader over the six EB nights that reads finished slots only and refuses a short count; an exact rank-sum test that stays fast at n = 12 with ties; and a threshold table. Its output and a README land under the same evidence directory. No model, network or subprocess. No Engine change, and no remedy spec.

**Tech Stack:** Python 3.14 stdlib, pytest (default tier), `just gates`.

**Spec:** `docs/superpowers/specs/2026-10-02-engine-budget-design.md`, sections 3 (the EB2 row), 4 and 7, which are on branch `worktree-engine-budget` until D1. Read it beside `evidence/2026-10-03-eb1-read/README.md` (same branch) and `evidence/2026-10-05-eb-cell-read/README.md` (on `main`).

## Rulings this plan rests on, and decisions it needs

- **Ruled 2026-10-05 (maintainer, in session: "Keep review-script in the floor set"):** the floor set at engine `23a0ef6` is {guard-prefixes, review-script}. EB1's rule, read as proportions on the new cells, would have dropped review-script (Engine 6 of 12 delivered, higher in 32 of 66 pass pairs). Task 1 records the ruling.
- **D1 (maintainer, attended): merge `worktree-engine-budget` into `main`.** The spec, `eb1.py`, `cells.py` and EB1's README live only on that branch. `git merge-tree` shows one conflict, `PROVENANCE.md`, where both sides appended rows: keep both, as in the ledger entry "Engine pin moved to the merge commit 5b681b0". Agents never merge, so **Task 1 cannot start before D1.** Recommended.
- **D2 (maintainer): review-script's role is no-harm.** At `23a0ef6`, review-script already meets section 4's median clause (Engine 10,828 ≤ 1.25 × Baseline's 10,970). Its rank-sum clause is recomputed in Task 4. Under D2, a remedy is never chosen for review-script's sake. Every remedy that touches review-script's path must be estimated not to push its median above the margin. Its delivered rate (6 of 12 against 11 of 12) is reported but is not the decider. Recommended.
- **D3 (maintainer): may EB2 estimate a scratch-path remedy?** This would add a permitted scratch path to the contract. EB1 §7 named inline probing as the largest guard-prefixes cost no listed remedy targets, and said estimating a scratch path needs a ruling first. "Yes" adds one row to Task 3's bounds, as an estimate only; it builds nothing. Recommended: yes.
- **D4 (maintainer): the margin EB2 screens at is provisional 1.25 (spec section 4).** Task 4 also reports 1.35, the margin EB1 found the guard-prefixes Baseline spread needs. EB3's pre-registration fixes the final margin; EB2 does not.

## Global Constraints

- "The default test tier uses no model, network, or subprocess; the tripwire in `tests/conftest.py` enforces it. Every refusal test has a sibling success test." (AGENTS.md)
- "Grade from hook-written evidence, never stdout or exit status. State denominators and missingness. Count events from `tool_execution_start`, one per call." (AGENTS.md)
- "Read a gate's exit code; never pipe a gate." Commit only after `just gates` itself exits 0.
- The decider is "output tokens per delivered pass, per task, never pooled" (spec, rulings 2026-10-02). EB0's `1869397` Engine cells are never pooled with `23a0ef6` cells.
- "Parity is not a remedy" (spec). Pi's three edit repairs, descriptions and guidelines are already in the pin. Hoisting or unwrapping shapes Pi refuses is a remedy (spec §7).
- A remedy that changes calls from turn 1 cannot be scored by replay. Its figure is an **upper bound** and is labelled as one (R0 §1.4; EB1 §5).
- "Every file here has a row in `PROVENANCE.md`; `just gates` fails if one does not."
- Roles: Sonnet implements each task. Opus reviews each task and the whole branch. Fable is used only if the maintainer asks.
- **Stop rule:** if no candidate, alone or in a non-overlapping sum, has an upper bound at or above guard-prefixes' required cut, EB2 ends there. The README says "no listed remedy can clear the threshold". No remedy spec is drafted, and the controller brings that result to the maintainer.

## Review Focus

1. **Rank-sum test cost at n = 12 with ties.** EB1's `mw_p` enumerates every combination: C(24,12) ≈ 2.7 M per distinct rank vector. Ties in the resample world defeat its cache, so a power run would never finish. A reasonable person expects the power table in seconds and equal to EB1's p on EB1-sized samples. Task 2 pins both.
2. **A night short of cells.** A night still running, a replaced slot or a missing result file must stop the script by name. It must never compute medians over 11 cells while calling them 12. Task 2 pins it.
3. **Combining stage-1 and stage-2 Engine nights.** Combining is valid only because both nights ran the same arm file. If the arm digests differ, the loader must refuse. Task 2 pins it.
4. **A remedy that does not apply to a task.** The light path does not apply to review-script, which creates files (EB1 §5). The table must print "n.a.", never a number. Task 3 pins it.
5. **A task already inside the margin.** Review-script's required cut is negative. The table must say "within margin (no-harm)", never print a negative "saving needed". Task 3 pins it.

---

### Task 1: Record the floor-set ruling and D2–D4 (docs only)

**Precondition:** D1 is merged, so `docs/superpowers/specs/2026-10-02-engine-budget-design.md` and `evidence/2026-10-03-eb1-read/eb1.py` exist on `main`. If either is missing, stop. D2–D4 are answered in session; copy the maintainer's words.

**Files:**
- Modify: `evidence/2026-09-15-release-one-decision-ledger.md` (append one entry at the end)
- Modify: `docs/superpowers/specs/2026-10-02-engine-budget-design.md` (append bullets to section 7; rewrite nothing above)

- [ ] **Step 1: Append the ledger entry**

```markdown
## 2026-10-05 — EB floor set kept at {guard-prefixes, review-script} at 23a0ef6; EB2 plan's rulings
- Evidence: `evidence/2026-10-05-eb-cell-read/README.md` (`5be84e8`), 12 cells per arm per task at engine `23a0ef6`, development. Guard-prefixes: Engine 28,463 against Baseline 5,510 output tokens per delivered pass (Engine higher in 66 of 72 pass pairs). Review-script: 10,828 against 10,970 (32 of 66), Engine delivering 6 of 12 against 11 of 12.
- **Ruled by the maintainer 2026-10-05 ("Keep review-script in the floor set"):** the floor set stays {guard-prefixes, review-script}, although EB1's rule read as proportions would drop review-script. EB1's floor set rested on `1869397` cells; this ruling re-derives it on the `23a0ef6` cells.
- D2 (review-script is a no-harm floor task): <maintainer's words>. D3 (scratch-path remedy estimated in EB2): <maintainer's words>. D4 (EB2 screens at 1.25, reports 1.35; EB3 fixes the margin): <maintainer's words>.
- Plan: `docs/superpowers/plans/2026-10-05-eb2-offline-estimates.md`.
```

Replace each `<maintainer's words>` with the quoted answer. If a decision was not answered, stop before committing.

- [ ] **Step 2: Append to the spec's section 7**

```markdown
- **Floor set re-derived at `23a0ef6` (2026-10-05).** Kept at {guard-prefixes, review-script} by ruling (ledger, 2026-10-05), on `evidence/2026-10-05-eb-cell-read/`. EB2's estimates are made on those cells, never on EB0's `1869397` Engine cells. Review-script is a no-harm floor task (D2): it already meets section 4's median clause at this pin.
```

- [ ] **Step 3: Run the gates and read the exit code**

Run: `just gates; echo "gates exit $?"`
Expected: `gates exit 0`. On any other value, stop and fix inside this task's two files only.

- [ ] **Step 4: Commit**

```bash
git add evidence/2026-09-15-release-one-decision-ledger.md docs/superpowers/specs/2026-10-02-engine-budget-design.md
git commit -m "ledger: EB floor set kept at {guard-prefixes, review-script} at 23a0ef6; EB2 plan rulings D2-D4"
```

---

### Task 2: `eb2.py` loader and exact rank-sum test, with frozen inputs

**Files:**
- Create: `evidence/2026-10-05-eb2-estimates/eb2.py`
- Create: `tests/test_eb2_estimates.py`
- Modify: `tests/test_frozen_instruments.py` (two `FROZEN` entries)
- Modify: `PROVENANCE.md` (one row per new file)

**Interfaces:**
- Consumes: `eb1.read_cell(cell: Path) -> dict` (it classifies the cell), `eb1.mw_p(eng, base) -> float`, `rc.load_night(night: Path) -> dict` with `{"launch": dict | None, "slots": {idx: {"result": dict, "spec": dict}}, "replaced": list}`.
- Produces: `NIGHTS: dict[tuple[str, str], tuple[str, ...]]`, `EXPECTED = 12`, `finished_cells(night: Path, arm: str) -> list[Path]`, `load(runs: Path, nights=NIGHTS, expected=EXPECTED, read=None) -> dict[tuple[str, str], list[dict]]`, `mw_p(eng: list[float], base: list[float]) -> float`, `parity(eng, base, margin: float) -> bool`, class `ShortNight(SystemExit)`.

- [ ] **Step 1: Write the failing tests**

```python
"""Pure rules of evidence/2026-10-05-eb2-estimates/eb2.py, loaded by path.

Default tier: synthetic night directories under tmp_path and number lists.
No subprocess, no ~/satyrn-runs.
"""

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PATH = _ROOT / "evidence" / "2026-10-05-eb2-estimates" / "eb2.py"
_SPEC = importlib.util.spec_from_file_location("eb2", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
eb2 = importlib.util.module_from_spec(_SPEC)
sys.modules["eb2"] = eb2
_SPEC.loader.exec_module(eb2)


def night(root: Path, name: str, arm: str, dirs: list[str], *, digest: str = "a" * 64,
          replaced: list[str] = (), unslotted: list[str] = ()) -> Path:
    n = root / name
    (n / "slots").mkdir(parents=True)
    (n / "launch.json").write_text(json.dumps({"status": "complete", "arm_sha256": {arm: digest}}))
    for i, d in enumerate(dirs):
        (n / arm / d).mkdir(parents=True)
        (n / "slots" / f"{i:02d}.json").write_text(json.dumps({"slot": i, "arm": arm, "attempt_dir": d}))
        (n / "slots" / f"{i:02d}.spec.json").write_text("{}")
    for j, d in enumerate(replaced):
        (n / arm / d).mkdir(parents=True)
        (n / "slots" / f"{j:02d}.replaced-1.json").write_text(json.dumps({"arm": arm, "attempt_dir": d}))
    for d in unslotted:
        (n / arm / d).mkdir(parents=True)
    return n


def test_finished_cells_reads_slots_not_directories(tmp_path):
    n = night(tmp_path, "N", "engine", ["c0", "c1"], replaced=["old"], unslotted=["stray"])
    assert [p.name for p in eb2.finished_cells(n, "engine")] == ["c0", "c1"]


def test_load_combines_nights_of_one_arm_file(tmp_path):
    night(tmp_path, "S1", "engine", ["a0", "a1"])
    night(tmp_path, "S2", "engine", ["b0"])
    data = eb2.load(tmp_path, nights={("t", "engine"): ("S1", "S2")}, expected=3, read=lambda p: {"name": p.name})
    assert [c["name"] for c in data["t", "engine"]] == ["a0", "a1", "b0"]


def test_load_refuses_a_short_night(tmp_path):
    night(tmp_path, "S1", "engine", ["a0", "a1"])
    with pytest.raises(eb2.ShortNight, match="t engine: 2 finished cells, expected 3"):
        eb2.load(tmp_path, nights={("t", "engine"): ("S1",)}, expected=3, read=lambda p: {})


def test_load_refuses_nights_with_different_arm_files(tmp_path):
    night(tmp_path, "S1", "engine", ["a0"], digest="a" * 64)
    night(tmp_path, "S2", "engine", ["b0"], digest="b" * 64)
    with pytest.raises(eb2.ShortNight, match="different arm files"):
        eb2.load(tmp_path, nights={("t", "engine"): ("S1", "S2")}, expected=2, read=lambda p: {})


@pytest.mark.parametrize("eng,base", [
    ([5, 7, 9, 9, 12, 15], [3, 4, 9, 6, 6, 8]),
    ([1, 1, 1, 2, 2, 2], [1, 2, 1, 2, 1, 2]),
    ([10, 20, 30, 40, 50, 60], [61, 62, 63, 64, 65, 66]),
])
def test_mw_p_equals_eb1_exact_test_with_ties(eng, base):
    assert eb2.mw_p(eng, base) == pytest.approx(eb2.eb1.mw_p(eng, base), abs=1e-12)


def test_mw_p_is_fast_at_twelve_with_ties():
    eng = [float(x % 5) for x in range(12)]
    base = [float(x % 4) for x in range(12)]
    start = time.perf_counter()
    eb2.mw_p(eng, base)
    assert time.perf_counter() - start < 1.0


def test_parity_needs_both_clauses():
    base = [90.0, 95.0, 100.0, 105.0, 110.0, 115.0]
    assert eb2.parity(base, base, 1.25) is True                                   # both clauses hold
    assert eb2.parity([x + 20 for x in base], base, 1.25) is False                # median 122.5 <= 128.1, rank-sum p 0.005 rejects
    assert eb2.parity([200.0, 30.0, 40.0, 300.0, 250.0, 260.0], base, 1.25) is False  # median clause fails
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_eb2_estimates.py -q`
Expected: a collection error, because `eb2.py` does not exist.

- [ ] **Step 3: Write `eb2.py` (loader and test only; Task 3 adds the rest)**

```python
"""EB2 - offline remedy estimates on the 23a0ef6 cells (no model, network or subprocess).

Usage, from the repo root:

    uv run python evidence/2026-10-05-eb2-estimates/eb2.py [RUNS_ROOT]

RUNS_ROOT defaults to ~/satyrn-runs. EB1's classification is reused unchanged
(evidence/2026-10-03-eb1-read/eb1.py), and so is the cell read's slot
enumeration (evidence/2026-10-05-eb-cell-read/read_cells.py). Both digests are
frozen in tests/test_frozen_instruments.py.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


eb1 = _load("eb1", "evidence/2026-10-03-eb1-read/eb1.py")
rc = _load("read_cells", "evidence/2026-10-05-eb-cell-read/read_cells.py")

NIGHTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("guard-prefixes", "engine"): ("2026-10-04-eb-s1-engine-selfhost-guard-prefixes",
                                   "2026-10-04-eb-s2-engine-selfhost-guard-prefixes"),
    ("guard-prefixes", "baseline"): ("2026-10-04-eb-s2-baseline-selfhost-guard-prefixes",),
    ("review-script", "engine"): ("2026-10-04-eb-s1-engine-selfhost-review-script",
                                  "2026-10-04-eb-s2-engine-selfhost-review-script"),
    ("review-script", "baseline"): ("2026-10-04-eb-s2-baseline-selfhost-review-script",),
}
EXPECTED = 12


class ShortNight(SystemExit):
    """A night set that cannot be read as EXPECTED finished cells of one arm file."""


def finished_cells(night: Path, arm: str) -> list[Path]:
    """Cell directories of the night's finished, unreplaced slots for ARM, in slot order."""
    out = []
    for _, slot in sorted(rc.load_night(night)["slots"].items()):
        result = slot.get("result") or {}
        if result.get("arm") == arm and result.get("attempt_dir"):
            out.append(night / arm / result["attempt_dir"])
    return out


def load(runs: Path, nights=NIGHTS, expected: int = EXPECTED, read=None) -> dict[tuple[str, str], list[dict]]:
    read = read or eb1.read_cell
    data: dict[tuple[str, str], list[dict]] = {}
    for (task, arm), names in nights.items():
        digests = {json.loads((runs / n / "launch.json").read_text())["arm_sha256"][arm] for n in names}
        if len(digests) != 1:
            raise ShortNight(f"{task} {arm}: nights {names} ran different arm files {sorted(digests)}")
        paths = [p for n in names for p in finished_cells(runs / n, arm)]
        if len(paths) != expected:
            raise ShortNight(f"{task} {arm}: {len(paths)} finished cells, expected {expected}")
        data[task, arm] = [read(p) for p in paths]
    return data


def mw_p(eng: list[float], base: list[float]) -> float:
    """Exact one-sided p of rank-sum(Engine) >= observed (H0: Engine <= Baseline), midranks for ties.

    Same statistic as eb1.mw_p. Doubled midranks are integers, so the null
    distribution is a subset-sum count by dynamic programming, not an
    enumeration of C(n, k) subsets.
    """
    values = sorted([*eng, *base])
    doubled: dict[float, int] = {}
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[j + 1] == values[i]:
            j += 1
        doubled[values[i]] = i + j + 2
        i = j + 1
    ranks = [doubled[v] for v in values]
    k = len(eng)
    observed = sum(doubled[v] for v in eng)
    ways: list[dict[int, int]] = [{0: 1}] + [{} for _ in range(k)]
    for r in ranks:
        for size in range(k, 0, -1):
            for total, count in ways[size - 1].items():
                ways[size][total + r] = ways[size].get(total + r, 0) + count
    return sum(c for s, c in ways[k].items() if s >= observed) / sum(ways[k].values())


def parity(eng, base, margin: float) -> bool:
    """Spec section 4: the median clause and the rank-sum clause."""
    return statistics.median(eng) <= margin * statistics.median(base) and mw_p(eng, base) >= 0.05
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_eb2_estimates.py -q`
Expected: 9 passed. If `test_mw_p_equals_eb1_exact_test_with_ties` fails, the doubling is wrong. Do not loosen the tolerance.

- [ ] **Step 5: Freeze the two inputs**

Compute each digest and add it to `FROZEN` in `tests/test_frozen_instruments.py`. Then change that module's docstring to say the file also pins the EB2 inputs at their committed blobs.

```bash
git show HEAD:evidence/2026-10-03-eb1-read/eb1.py | shasum -a 256
git show HEAD:evidence/2026-10-05-eb-cell-read/read_cells.py | shasum -a 256
```

```python
    "evidence/2026-10-03-eb1-read/eb1.py": "<digest from the first command>",
    "evidence/2026-10-05-eb-cell-read/read_cells.py": "<digest from the second command>",
```

- [ ] **Step 6: Provenance rows, gates, commit**

Append to `PROVENANCE.md`:

```markdown
| evidence/2026-10-05-eb2-estimates/eb2.py | written 2026-10-05 for EB2 (plan docs/superpowers/plans/2026-10-05-eb2-offline-estimates.md); offline estimates on the 23a0ef6 EB cells, reusing eb1.py and read_cells.py unchanged |
| tests/test_eb2_estimates.py | written 2026-10-05 for EB2; default-tier tests of eb2.py's loader, rank-sum test, power and threshold rules |
```

Run: `just gates; echo "gates exit $?"`. Expected: `gates exit 0`.

```bash
git add evidence/2026-10-05-eb2-estimates/eb2.py tests/test_eb2_estimates.py tests/test_frozen_instruments.py PROVENANCE.md
git commit -m "EB2: loader over the 23a0ef6 nights and an exact rank-sum test fast at n = 12; eb1.py and read_cells.py frozen"
```

---

### Task 3: Power, required cut, and remedy bounds

**Files:**
- Modify: `evidence/2026-10-05-eb2-estimates/eb2.py`
- Modify: `tests/test_eb2_estimates.py`

**Interfaces:**
- Consumes: `parity`, `eb1.passes`, `eb1.cat_tokens`, `eb1.out_total`, `eb1.m`, `eb1.ARMS`.
- Produces: `power(base_passes: list[float], n_eng: int, n_base: int, mults, reps: int, margin: float, seed: int) -> dict`, `required_cut(eng_total: list[float], base_total: list[float], margin: float) -> float`, `bounds(data, task: str, scratch: bool) -> dict[str, float | None]`, `verdict_line(task: str, cut: float, bounds: dict) -> str`, `LIGHT_PATH_TASKS = frozenset({"guard-prefixes"})`, `MARGINS = (1.25, 1.35)`, `SEED = 20261005`.

- [ ] **Step 1: Write the failing tests (append)**

```python
def test_power_is_deterministic_and_monotone():
    base = [2308.0, 2663.0, 2898.0, 5206.0, 5813.0, 16178.0, 17764.0, 19599.0]
    a = eb2.power(base, 9, 8, (1.0, 2.0), reps=200, margin=1.25, seed=1)
    b = eb2.power(base, 9, 8, (1.0, 2.0), reps=200, margin=1.25, seed=1)
    assert a == b
    assert a["log-normal", 1.0] > a["log-normal", 2.0]


def test_required_cut_positive_and_negative():
    assert eb2.required_cut([28463.0], [5510.0], 1.25) == pytest.approx(28463 - 1.25 * 5510)
    assert eb2.required_cut([10828.0], [10970.0], 1.25) < 0


def test_verdict_line_within_margin_is_no_harm():
    assert eb2.verdict_line("review-script", -2884.0, {"x": 100.0}) == \
        "review-script: within margin (no-harm); a remedy must not raise its median above the margin"


def test_verdict_line_names_bounds_that_clear():
    line = eb2.verdict_line("guard-prefixes", 21576.0, {"light path": 22000.0, "test lines": 9000.0, "light n.a.": None})
    assert line.startswith("guard-prefixes: required cut 21,576")
    assert "can clear alone: light path" in line


def test_verdict_line_stop_when_nothing_clears():
    line = eb2.verdict_line("guard-prefixes", 21576.0, {"test lines": 9000.0})
    assert line.endswith("no listed remedy can clear the threshold alone")


def test_bounds_marks_light_path_na_off_its_tasks():
    cell = lambda total: {"verdict": "pass", "turns": [{"cat": "probe", "out": total}]}
    data = {("review-script", "engine"): [cell(10)], ("review-script", "baseline"): [cell(5)]}
    assert eb2.bounds(data, "review-script", scratch=False)["light path (whole E-B median gap)"] is None
```

If `eb1.out_total` or `eb1.cat_tokens` need cell keys beyond `verdict` and `turns`, read their bodies and add exactly those keys to the `cell` lambda. Change nothing else in the test.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_eb2_estimates.py -q`
Expected: the new tests fail with `AttributeError` on `power`, `required_cut`, `verdict_line` and `bounds`.

- [ ] **Step 3: Implement (append to `eb2.py`; add `import math` and `import random` to its imports)**

```python
SEED = 20261005
MARGINS = (1.25, 1.35)
LIGHT_PATH_TASKS = frozenset({"guard-prefixes"})  # review-script creates files (EB1 section 5)


def power(base_passes, n_eng, n_base, mults, reps, margin, seed) -> dict:
    """P(parity declared) when the Engine is mult x Baseline; plus the true-parity 95% median ratio."""
    rng = random.Random(seed)
    logs = [math.log(x) for x in base_passes]
    mu, sd = statistics.mean(logs), statistics.stdev(logs)
    worlds = {"resample": lambda: rng.choice(base_passes), "log-normal": lambda: math.exp(rng.gauss(mu, sd))}
    out: dict = {}
    for world, draw in worlds.items():
        for mult in mults:
            hits = sum(parity([draw() * mult for _ in range(n_eng)], [draw() for _ in range(n_base)], margin)
                       for _ in range(reps))
            out[world, mult] = hits / reps
        ratios = sorted(statistics.median([draw() for _ in range(n_eng)]) /
                        statistics.median([draw() for _ in range(n_base)]) for _ in range(reps))
        out[world, "q95"] = ratios[int(0.95 * (reps - 1))]
    return out


def required_cut(eng_total, base_total, margin) -> float:
    """Output tokens per delivered pass the Engine median must lose to meet the median clause."""
    return statistics.median(eng_total) - margin * statistics.median(base_total)


def bounds(data, task: str, scratch: bool) -> dict[str, float | None]:
    """Upper bounds per remedy, in output tokens per delivered pass (EB1 section 5 formulas)."""
    e, b = (eb1.passes(data[task, arm]) for arm in ("engine", "baseline"))
    ce, cb = [eb1.cat_tokens(c) for c in e], [eb1.cat_tokens(c) for c in b]

    def pick(cats, keys):
        return [sum(x[k] for k in keys) for x in cats]

    gap = eb1.m([eb1.out_total(c) for c in e]) - eb1.m([eb1.out_total(c) for c in b])
    rows: dict[str, float | None] = {
        "light path (whole E-B median gap)": gap if task in LIGHT_PATH_TASKS else None,
        "contract test lines (E-B median, pre-edit + test file)":
            eb1.m(pick(ce, ["pre-edit", "test file"])) - eb1.m(pick(cb, ["pre-edit", "test file"])),
        "edit-shape hoisting (E median, schema + ANCHOR_MISSING retries)":
            eb1.m(pick(ce, ["retry:schema", "retry:ANCHOR_MISSING"])),
    }
    if scratch:
        rows["scratch path (E-B median, probe)"] = eb1.m(pick(ce, ["probe"])) - eb1.m(pick(cb, ["probe"]))
    return rows


def verdict_line(task: str, cut: float, bounds: dict) -> str:
    if cut <= 0:
        return f"{task}: within margin (no-harm); a remedy must not raise its median above the margin"
    clear = [name for name, value in bounds.items() if value is not None and value >= cut]
    head = f"{task}: required cut {cut:,.0f}; "
    if clear:
        return head + "can clear alone: " + ", ".join(clear)
    return head + "no listed remedy can clear the threshold alone"
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_eb2_estimates.py -q`
Expected: all pass.

- [ ] **Step 5: Gates and commit**

Run: `just gates; echo "gates exit $?"`. Expected: `gates exit 0`.

```bash
git add evidence/2026-10-05-eb2-estimates/eb2.py tests/test_eb2_estimates.py
git commit -m "EB2: power at the delivered counts, required cut, remedy upper bounds and the clear/no-harm verdict"
```

---

### Task 4: `main`, the offline run, and the EB0 regression

**Files:**
- Modify: `evidence/2026-10-05-eb2-estimates/eb2.py` (add `main`)
- Create: `evidence/2026-10-05-eb2-estimates/eb2.txt` (the script's output)
- Modify: `PROVENANCE.md`

- [ ] **Step 1: Add `main`**

```python
TASKS = ("guard-prefixes", "review-script")


def main(argv: list[str]) -> int:
    runs = Path(argv[1]).expanduser() if len(argv) > 1 else Path("~/satyrn-runs").expanduser()
    scratch = "--no-scratch" not in argv
    data = load(runs)
    eb1.TASKS = {task: None for task in TASKS}  # EB1's sections iterate TASKS' keys only
    print("# EB2 offline estimates, engine 23a0ef6, 12 cells per arm per task")
    eb1.section2(data, list(TASKS))
    eb1.section3(data)
    eb1.section4(data, list(TASKS))
    eb1.section5(data)
    print(f"\n## Power of section 4's rule at the delivered counts (seed {SEED}, 4000 reps)")
    for task in TASKS:
        e, b = (eb1.passes(data[task, arm]) for arm in ("engine", "baseline"))
        base = [float(eb1.out_total(c)) for c in b]
        for counts in ((len(e), len(b)), (2 * len(e), 2 * len(b))):
            for margin in MARGINS:
                p = power(base, *counts, (1.0, 1.25, 1.5, 2.0), reps=4000, margin=margin, seed=SEED)
                print(f"  {task} E n={counts[0]} B n={counts[1]} margin {margin}: "
                      + ", ".join(f"{w} {k}: {v:.3f}" for (w, k), v in p.items()))
    print("\n## Required cut and remedy upper bounds (output tokens per delivered pass)")
    for task in TASKS:
        e, b = (eb1.passes(data[task, arm]) for arm in ("engine", "baseline"))
        et, bt = [eb1.out_total(c) for c in e], [eb1.out_total(c) for c in b]
        print(f"  {task}: rank-sum p (Engine <= Baseline) {mw_p(et, bt):.4f}")
        rows = bounds(data, task, scratch)
        for name, value in rows.items():
            print(f"    {name}: {'n.a.' if value is None else f'{value:,.0f}'}")
        for margin in MARGINS:
            print("    " + verdict_line(task, required_cut(et, bt, margin), rows) + f" [margin {margin}]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

`--no-scratch` exists so the run matches a D3 "no". If D3 was "no", pass `--no-scratch` in Step 3.

- [ ] **Step 2: Confirm EB1's sections read only `TASKS`' keys**

Run: `grep -n "TASKS\[" evidence/2026-10-03-eb1-read/eb1.py; echo "grep exit $?"`
Expected: no lines, `grep exit 1`. If any line prints, a section reads a night name from `TASKS`. Stop and report: the plan's reuse assumption is wrong.

- [ ] **Step 3: Run the script on the retained cells**

Run: `uv run python evidence/2026-10-05-eb2-estimates/eb2.py > evidence/2026-10-05-eb2-estimates/eb2.txt; echo "exit $?"`
Expected: `exit 0`. Then check that `eb2.txt` names both tasks, does not name `depth-3`, and shows guard-prefixes Engine and Baseline totals of 28,463 and 5,510 in section 2's total row (the cell read's medians). A `ShortNight` or a different total stops the task; report it and do not edit the numbers.

- [ ] **Step 4: Regression against EB1 on EB0's nights (offline)**

Run:

```bash
uv run python - <<'EOF'
import importlib.util, io, sys, contextlib
from pathlib import Path
spec = importlib.util.spec_from_file_location("eb2", "evidence/2026-10-05-eb2-estimates/eb2.py")
eb2 = importlib.util.module_from_spec(spec); sys.modules["eb2"] = eb2; spec.loader.exec_module(eb2)
runs = Path("~/satyrn-runs").expanduser()
nights = {(t, a): (n,) for t, n in (("guard-prefixes", "2026-10-02-eb0-selfhost-guard-prefixes"),
                                     ("review-script", "2026-10-02-eb0-selfhost-review-script"))
          for a in ("baseline", "engine")}
mine = eb2.load(runs, nights=nights, expected=6)
theirs = eb2.eb1.load(runs)
for key in mine:
    a, b = io.StringIO(), io.StringIO()
    eb2.eb1.TASKS = {key[0]: None}
    with contextlib.redirect_stdout(a): eb2.eb1.section2(mine, [key[0]])
    with contextlib.redirect_stdout(b): eb2.eb1.section2(theirs, [key[0]])
    print(key, "identical" if a.getvalue() == b.getvalue() else "DIFFERENT")
EOF
```

Expected: four lines, each `identical`. A `DIFFERENT` means the slot loader and EB1's directory loader disagree on EB0. Stop and report which cells differ.

- [ ] **Step 5: Provenance, gates, commit**

```markdown
| evidence/2026-10-05-eb2-estimates/eb2.txt | written 2026-10-05 by evidence/2026-10-05-eb2-estimates/eb2.py over the six EB nights in ~/satyrn-runs (engine 23a0ef6), offline |
```

Run: `just gates; echo "gates exit $?"`. Expected: `gates exit 0`.

```bash
git add evidence/2026-10-05-eb2-estimates/eb2.py evidence/2026-10-05-eb2-estimates/eb2.txt PROVENANCE.md
git commit -m "EB2: offline run on the 23a0ef6 cells; slot loader reproduces EB1 section 2 on EB0"
```

---

### Task 5: The EB2 README, and the stop or the hand-off

**Files:**
- Create: `evidence/2026-10-05-eb2-estimates/README.md`
- Modify: `PROVENANCE.md`

- [ ] **Step 1: Write the README from `eb2.txt` only**

Copy numbers from `eb2.txt`; compute nothing by hand. Sections, in order:

1. **What was read.** Six nights, 12 cells per arm per task, engine `23a0ef6`, offline. The recompute command in a fenced block (`uv run python evidence/2026-10-05-eb2-estimates/eb2.py`). The EB0 regression result from Task 4 Step 4.
2. **Attribution per floor task.** EB1 §2's table, re-derived. State the residual of the medians. Name every category whose Engine median changed direction against EB1 (EB0 cells, `1869397`), without pooling or computing a difference across pins.
3. **The parity rule's power at the delivered counts and at twice them,** at margins 1.25 and 1.35. State the true-parity 95th-percentile median ratio per task.
4. **Required cut and remedy bounds.** One table per task: remedy, class targeted, replay-scorable (yes / partly / no, copying EB1 §5's column), upper bound, and clears at 1.25 / 1.35. Overlaps: the light path contains every other guard-prefixes row, and the test lines overlap the probe row. Never add overlapping rows.
5. **Review-script, no-harm.** The rank-sum p and the margin headroom. For each remedy that would change review-script's path, say whether its bound could push the median above the margin.
6. **Outcome.** Exactly one of:
   - "**No listed remedy can clear the threshold on guard-prefixes**, alone or in a non-overlapping sum. EB2 stops here. No remedy spec is drafted." (the plan's stop rule)
   - "**Remedies whose upper bound clears:** <names>. Each is an upper bound; only a build and EB3 can measure the effect. Next: the maintainer picks which to specify."

- [ ] **Step 2: Provenance, gates, commit**

```markdown
| evidence/2026-10-05-eb2-estimates/README.md | written 2026-10-05 for EB2 from eb2.txt; offline estimates, development, never deciding |
```

Run: `just gates; echo "gates exit $?"`. Expected: `gates exit 0`.

```bash
git add evidence/2026-10-05-eb2-estimates/README.md PROVENANCE.md
git commit -m "EB2: offline estimates README (outcome: <stop | remedies that clear>)"
```

- [ ] **Step 3: Hand off (attended)**

Stop. The controller brings the outcome line, the two required cuts and the bounds table to the maintainer. Remedy specs, any Engine build and EB3's pre-registration are later plans, each started by the maintainer.

---

## Self-review notes

- **Spec coverage.** The EB2 row's "offline estimate … names its class and says whether replay can score it" is Task 5 §4. Section 4's margin and power are Task 3/4 and Task 5 §3. Section 7's floor set is Task 1, and its scratch-path ruling is D3. The EB2 row's "approved spec per remedy; fixture tests both directions" is deliberately out of scope. It follows the maintainer's pick (Task 5 Step 3), because AGENTS.md puts building after the estimate.
- **Not in this plan:** the review-script contract question (a prompt defect or not) and EB1's "admission is arm-asymmetric". Both bear on EB3's cross-arm read, not on EB2's estimates. They stay listed as open in `evidence/2026-10-05-eb-cell-read/README.md`.
