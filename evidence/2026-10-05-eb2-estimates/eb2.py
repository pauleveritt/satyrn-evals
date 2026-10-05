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
import math
import random
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
        cells = []
        for p in paths:
            cell = read(p)
            if cell.get("verdict") is None:  # EB1's sections format the verdict; label it with its attempt code
                cell["verdict"] = cell.get("code") or "none"
            cells.append(cell)
        data[task, arm] = cells
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


LIGHT_PATH_KEY = "light path (whole E-B median gap; not an estimate)"
COMBINED_KEY = "all estimable remedies combined"
TESTS_KEY = "contract test lines (pre-edit + test file)"
HOIST_KEY = "edit-shape hoisting (all schema + ANCHOR_MISSING retries)"
# The scratch row is new in EB2 under D3; it is not an EB1 section 5 formula.
SCRATCH_KEY = "scratch path (probe; new in EB2 under D3, not an EB1 §5 formula)"
REFERENCES = ("zero", "baseline-median")


def _removals(data, task: str, scratch: bool, reference: str) -> dict[str, list[float]]:
    """Per-cell token removals of each remedy row, in Engine pass order (combined row last).

    reference "zero" is an upper bound: a remedy removes at most every token of its category.
    reference "baseline-median" is a central estimate, not an upper bound: a remedy removes
    the excess over the Baseline median of the category, clamped at 0. Hoisting removes all
    schema and ANCHOR_MISSING retries under both.
    """
    if reference not in REFERENCES:
        raise ValueError(f"reference must be one of {REFERENCES}, got {reference!r}")
    e, b = (eb1.passes(data[task, arm]) for arm in ("engine", "baseline"))
    ce, cb = [eb1.cat_tokens(c) for c in e], [eb1.cat_tokens(c) for c in b]
    if reference == "zero":
        tests = [x["pre-edit"] + x["test file"] for x in ce]
        probes = [x["probe"] for x in ce]
    else:
        test_median = eb1.m([x["pre-edit"] + x["test file"] for x in cb])
        probe_median = eb1.m([x["probe"] for x in cb])
        tests = [max(0, x["pre-edit"] + x["test file"] - test_median) for x in ce]
        probes = [max(0, x["probe"] - probe_median) for x in ce]
    removals = {TESTS_KEY: tests, HOIST_KEY: [x["retry:schema"] + x["retry:ANCHOR_MISSING"] for x in ce]}
    if scratch:
        removals[SCRATCH_KEY] = probes
    removals[COMBINED_KEY] = [sum(parts) for parts in zip(*removals.values(), strict=True)]
    return removals


def counterfactual_totals(data, task: str, scratch: bool, reference: str = "zero") -> list[float]:
    """The Engine passes' totals after the combined per-cell removal, in pass order."""
    removals = _removals(data, task, scratch, reference)[COMBINED_KEY]
    totals = [eb1.out_total(c) for c in eb1.passes(data[task, "engine"])]
    return [t - r for t, r in zip(totals, removals, strict=True)]


def bounds(data, task: str, scratch: bool, reference: str = "zero") -> dict[str, float | None]:
    """Reductions of the median per-pass total, per-cell counterfactual, under REFERENCE.

    reference "zero" gives upper bounds (the stop rule reads only these); "baseline-median"
    gives central estimates, which are not upper bounds because the Baseline category
    distributions are bimodal. Each remedy row removes an amount from every Engine pass
    (never below zero), and the figure is median(totals) - median(totals - removed).
    Categories are disjoint per turn, so the combined row applies the rows' per-cell
    removals together. The EB1 section 5 figures stay printed by eb1.section5 for comparison.
    """
    removals = _removals(data, task, scratch, reference)
    e, b = (eb1.passes(data[task, arm]) for arm in ("engine", "baseline"))
    totals = [eb1.out_total(c) for c in e]
    engine_median = eb1.m(totals)
    rows: dict[str, float | None] = {
        name: engine_median - eb1.m([t - r for t, r in zip(totals, cut, strict=True)])
        for name, cut in removals.items() if name != COMBINED_KEY
    }
    rows[COMBINED_KEY] = engine_median - eb1.m(counterfactual_totals(data, task, scratch, reference))
    gap = engine_median - eb1.m([eb1.out_total(c) for c in b])
    return {LIGHT_PATH_KEY: gap if task in LIGHT_PATH_TASKS else None, **rows}


def verdict_line(task: str, cut: float, bounds: dict) -> str:
    """Read only upper-bound rows (reference "zero"). The light path is reported, never counted."""
    if cut <= 0:
        return f"{task}: within margin (no-harm); a remedy must not raise its median above the margin"
    head = f"{task}: required cut {cut:,.0f}; "
    alone = [name for name, value in bounds.items()
             if name not in (LIGHT_PATH_KEY, COMBINED_KEY) and value is not None and value >= cut]
    if alone:
        return head + "can clear alone: " + ", ".join(alone)
    combined = bounds.get(COMBINED_KEY)
    if combined is not None and combined >= cut:
        return head + "no remedy clears alone; the estimable remedies combined can clear (upper bound)"
    return (head + "no estimable remedy can clear the threshold, alone or combined; "
            "the light path is not estimable offline (its figure is the whole gap by definition)")


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
    print("\n## Required cut and remedy bounds (output tokens per delivered pass)")
    for task in TASKS:
        e, b = (eb1.passes(data[task, arm]) for arm in ("engine", "baseline"))
        et, bt = [eb1.out_total(c) for c in e], [eb1.out_total(c) for c in b]
        print(f"  {task}:")
        print(f"    Baseline delivered-pass totals: {sorted(bt)}")
        print(f"    Engine delivered-pass totals: {sorted(et)}")
        print(f"    rank-sum p (Engine <= Baseline) {mw_p(et, bt):.4f}")
        upper = bounds(data, task, scratch, "zero")
        print("    Upper bounds (reference: zero — a remedy removes at most every token of its category)")
        for name, value in upper.items():
            print(f"      {name}: {'n.a.' if value is None else f'{value:,.0f}'}")
        for margin in MARGINS:
            print("      " + verdict_line(task, required_cut(et, bt, margin), upper) + f" [margin {margin}]")
        p = mw_p(counterfactual_totals(data, task, scratch, "zero"), bt)
        print(f"      rank-sum p of the combined upper-bound counterfactual against Baseline: {p:.4f}")
        central = bounds(data, task, scratch, "baseline-median")
        print("    Central estimates (reference: Baseline median of the category — not an upper bound)")
        for name, value in central.items():
            print(f"      {name}: {'n.a.' if value is None else f'{value:,.0f}'}")
        for margin in MARGINS:
            print(f"      central combined {central[COMBINED_KEY]:,.0f} against required cut "
                  f"{required_cut(et, bt, margin):,.0f} [margin {margin}]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
