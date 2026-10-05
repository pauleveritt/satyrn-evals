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


def _verdict_after_load(tmp_path, cell: dict):
    night(tmp_path, "S1", "engine", ["a0"])
    data = eb2.load(tmp_path, nights={("t", "engine"): ("S1",)}, expected=1, read=lambda p: dict(cell))
    return data["t", "engine"][0]["verdict"]


def test_load_labels_a_missing_verdict_with_its_code(tmp_path):
    assert _verdict_after_load(tmp_path, {"verdict": None, "code": "NO_PATCH"}) == "NO_PATCH"


def test_load_keeps_a_present_verdict(tmp_path):
    assert _verdict_after_load(tmp_path, {"verdict": "pass", "code": "OK"}) == "pass"


def test_load_labels_none_when_code_missing_too(tmp_path):
    assert _verdict_after_load(tmp_path, {"verdict": None}) == "none"


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
    line = eb2.verdict_line("guard-prefixes", 21576.0,
                            {eb2.LIGHT_PATH_KEY: 30000.0, "test lines": 22000.0, "hoisting": 100.0,
                             eb2.COMBINED_KEY: 22100.0})
    assert line.startswith("guard-prefixes: required cut 21,576")
    assert "can clear alone: test lines" in line
    assert eb2.LIGHT_PATH_KEY not in line


def test_verdict_line_stop_when_nothing_clears():
    line = eb2.verdict_line("guard-prefixes", 21576.0,
                            {eb2.LIGHT_PATH_KEY: 30000.0, "test lines": 9000.0, eb2.COMBINED_KEY: 12000.0})
    assert line.endswith("no listed remedy can clear the threshold, alone or combined; "
                         "the light path's figure is the whole gap by definition, not an estimate")


def test_verdict_line_combined_clears():
    line = eb2.verdict_line("guard-prefixes", 21576.0,
                            {eb2.LIGHT_PATH_KEY: 30000.0, "a": 12000.0, "b": 11000.0, eb2.COMBINED_KEY: 23000.0})
    assert line.endswith("no remedy clears alone; the estimable remedies combined can clear (upper bound)")


def test_verdict_line_zero_cut_is_no_harm():
    assert eb2.verdict_line("review-script", 0.0, {"x": 100.0}) == \
        "review-script: within margin (no-harm); a remedy must not raise its median above the margin"


def test_bounds_marks_light_path_na_off_its_tasks():
    def cell(total):
        return {"verdict": "pass", "turns": [{"cat": "probe", "out": total}]}

    data = {("review-script", "engine"): [cell(10)], ("review-script", "baseline"): [cell(5)]}
    assert eb2.bounds(data, "review-script", scratch=False)[eb2.LIGHT_PATH_KEY] is None


def _cell(*turns):
    return {"verdict": "pass", "turns": [{"cat": cat, "out": out} for cat, out in turns]}


def test_bounds_gives_light_path_number_on_guard_prefixes():
    data = {("guard-prefixes", "engine"): [_cell(("probe", 10))], ("guard-prefixes", "baseline"): [_cell(("probe", 4))]}
    assert eb2.bounds(data, "guard-prefixes", scratch=False)[eb2.LIGHT_PATH_KEY] == 6


def _counterfactual_data():
    # Engine totals 20, 110, 100 (median 100); Baseline totals 25, 55, 60 (median 55).
    # Baseline pre-edit + test file: 10, 20, 30 (median 20); Baseline probe: 5, 15, 25 (median 15).
    engine = [
        _cell(("pre-edit", 10), ("retry:schema", 5), ("final", 5)),
        _cell(("pre-edit", 30), ("test file", 10), ("retry:ANCHOR_MISSING", 20), ("probe", 40), ("final", 10)),
        _cell(("pre-edit", 20), ("probe", 10), ("final", 70)),
    ]
    baseline = [
        _cell(("pre-edit", 10), ("probe", 5), ("final", 10)),
        _cell(("pre-edit", 20), ("probe", 15), ("final", 20)),
        _cell(("pre-edit", 30), ("probe", 25), ("final", 5)),
    ]
    return {("guard-prefixes", "engine"): engine, ("guard-prefixes", "baseline"): baseline}


def test_bounds_are_counterfactual_medians():
    got = eb2.bounds(_counterfactual_data(), "guard-prefixes", scratch=True)
    tests_key = "contract test lines (pre-edit + test file, excess over Baseline median)"
    hoist_key = "edit-shape hoisting (all schema + ANCHOR_MISSING retries)"
    probe_key = "scratch path (probe, excess over Baseline median; new in EB2 under D3, not an EB1 §5 formula)"
    # test-lines removals 0, 20, 0 (cell 1 at 10 is below the median 20: clamped): 20,90,100 -> 100 - 90
    assert got[tests_key] == 10
    # hoisting removals 5, 20, 0: 15,90,100 -> 100 - 90
    assert got[hoist_key] == 10
    # probe removals 0, 25, 0: 20,85,100 -> 100 - 85
    assert got[probe_key] == 15
    # combined removals 5, 65, 0: 15,45,100 -> 100 - 45 = 55, not the sum of rows (35)
    assert got[eb2.COMBINED_KEY] == 55
    assert got[eb2.LIGHT_PATH_KEY] == 45  # 100 - 55, reported, not an estimate
    without = eb2.bounds(_counterfactual_data(), "guard-prefixes", scratch=False)
    assert probe_key not in without
    # combined without scratch: removals 5, 40, 0: 15,70,100 -> 100 - 70
    assert without[eb2.COMBINED_KEY] == 30


def test_bounds_never_negative_when_engine_is_below_baseline():
    data = {("guard-prefixes", "engine"): [_cell(("pre-edit", 1), ("probe", 1), ("final", 3))] * 3,
            ("guard-prefixes", "baseline"): [_cell(("pre-edit", 50), ("probe", 50), ("final", 3))] * 3}
    got = eb2.bounds(data, "guard-prefixes", scratch=True)
    assert got["contract test lines (pre-edit + test file, excess over Baseline median)"] == 0
    assert got[eb2.COMBINED_KEY] == 0
