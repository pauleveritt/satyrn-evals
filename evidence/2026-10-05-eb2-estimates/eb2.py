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
