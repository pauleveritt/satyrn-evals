"""Pure rules of evidence/2026-10-05-rrg-delivery/decide.py, loaded by path.

Default tier: synthetic night directories under tmp_path and hand-built cells.
No subprocess, no ~/satyrn-runs. The reader applies §4 and §5 of
docs/superpowers/specs/2026-10-05-run-record-gate-delivery-comparison.md.
"""

import hashlib
import importlib.util
import json
import sys
from math import comb
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PATH = _ROOT / "evidence" / "2026-10-05-rrg-delivery" / "decide.py"
_SPEC = importlib.util.spec_from_file_location("rrg_decide", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
decide = importlib.util.module_from_spec(_SPEC)
sys.modules["rrg_decide"] = decide
_SPEC.loader.exec_module(decide)

D, N, U, INFRA = decide.DELIVERED, decide.NOT_DELIVERED, decide.UNAVAILABLE, decide.INFRASTRUCTURE


def result(code: str, verdict: str | None, *, arm: str = "baseline", slot: int = 0, phase: str | None = None) -> dict:
    return {"slot": slot, "arm": arm, "attempt_dir": f"t-{slot}", "code": code, "verdict": verdict,
            "message": "m", "deadline_phase": phase}


def write_night(root: Path, slots: list[dict], *, refusals: int = 0, reaches: int = 0,
                skip_attempt: set[int] = frozenset(), drop_key: dict[int, str] | None = None,
                confinement: dict[int, tuple[int, int]] | None = None) -> Path:
    night = root / "night"
    (night / "slots").mkdir(parents=True)
    for body in slots:
        i = body["slot"]
        (night / "slots" / f"{i:02d}.json").write_text(json.dumps(body))
        if i in skip_attempt:
            continue
        r, x = (confinement or {}).get(i, (refusals, reaches))
        cell = {"code": body["code"], "verdict": body["verdict"], "confinement": {"refusals": r, "reaches": x}}
        for key in (drop_key or {}).get(i, "").split(","):
            if key == "confinement":
                del cell["confinement"]
            elif key:
                del cell["confinement"][key]
        d = night / body["arm"] / body["attempt_dir"]
        d.mkdir(parents=True)
        (d / "attempt.json").write_text(json.dumps(cell))
    return night


def cell(arm: str, cls: str, *, refusals: int = 0, reaches: int = 0, slot: int = 0):
    return decide.Cell(slot=slot, arm=arm, attempt_dir=f"{arm}-{slot}-{cls}", cls=cls,
                       refusals=refusals, reaches=reaches)


def cells(arm: str, **spec: int) -> list:
    """cells('engine', delivered=3, **{'not delivered': 2}) -> cells with fresh slot numbers."""
    out = []
    for cls, count in spec.items():
        cls = cls.replace("_", " ")
        out += [cell(arm, cls, slot=len(out) + 100 * (arm == "engine")) for _ in range(count)]
    return out


# classify

def test_classify_pass_is_delivered():
    assert decide.classify(result("OK", "pass")) == D


def test_classify_fail_is_not_delivered():
    assert decide.classify(result("OK", "fail")) == N


def test_classify_unavailable_verdict():
    assert decide.classify(result("OK", "unavailable")) == U


def test_classify_budget_exceeded_and_no_patch_are_not_delivered():
    assert decide.classify(result("BUDGET_EXCEEDED", None)) == N
    assert decide.classify(result("NO_PATCH", None, arm="engine")) == N


def test_classify_command_phase_deadline_is_not_delivered():
    assert decide.classify(result("DEADLINE_EXCEEDED", None, phase="command")) == N


def test_classify_other_phase_deadline_is_infrastructure():
    assert decide.classify(result("DEADLINE_EXCEEDED", None, phase="grading")) == INFRA


def test_classify_setup_phase_deadline_is_infrastructure():
    assert decide.classify(result("DEADLINE_EXCEEDED", None, phase="setup")) == INFRA


def test_classify_command_timeout_is_not_delivered():
    assert decide.classify(result("COMMAND_TIMEOUT", None)) == N


def test_classify_infrastructure_code():
    assert decide.classify(result("MODEL_ERROR", None)) == INFRA


# load

def test_load_reads_a_two_arm_night_in_slot_order(tmp_path: Path):
    slots = [result("OK", "pass", slot=2, arm="baseline"), result("OK", "fail", slot=0, arm="baseline"),
             result("NO_PATCH", None, slot=1, arm="engine")]
    night = write_night(tmp_path, slots, refusals=2, reaches=1)
    got = decide.load(night)
    assert [(c.slot, c.arm, c.attempt_dir, c.cls, c.refusals, c.reaches) for c in got] == [
        (0, "baseline", "t-0", N, 2, 1), (1, "engine", "t-1", N, 2, 1), (2, "baseline", "t-2", D, 2, 1)]


def test_load_ignores_a_replaced_slot_file(tmp_path: Path):
    night = write_night(tmp_path, [result("OK", "pass", slot=0)])
    replaced = result("MODEL_ERROR", None, slot=0) | {"attempt_dir": "gone"}
    (night / "slots" / "00.replaced-1.json").write_text(json.dumps(replaced))
    assert [c.attempt_dir for c in decide.load(night)] == ["t-0"]


def test_load_is_refused_on_a_missing_attempt_json(tmp_path: Path):
    night = write_night(tmp_path, [result("OK", "pass", slot=3)], skip_attempt={3})
    with pytest.raises(decide.Refused, match=r"slot 3.*attempt\.json"):
        decide.load(night)


def test_load_is_refused_on_a_missing_confinement_key(tmp_path: Path):
    for drop in ("confinement", "reaches", "refusals"):
        night = write_night(tmp_path / drop, [result("OK", "pass", slot=1)], drop_key={1: drop})
        with pytest.raises(decide.Refused, match=r"slot 1.*confinement"):
            decide.load(night)


def test_load_is_refused_on_a_non_integer_confinement_count(tmp_path: Path):
    night = write_night(tmp_path, [result("OK", "pass", slot=1)])
    path = night / "baseline" / "t-1" / "attempt.json"
    path.write_text(json.dumps({"code": "OK", "verdict": "pass", "confinement": {"refusals": "2", "reaches": 0}}))
    with pytest.raises(decide.Refused):
        decide.load(night)
    path.write_text(json.dumps({"code": "OK", "verdict": "pass", "confinement": {"refusals": 2, "reaches": 0}}))
    assert decide.load(night)[0].refusals == 2


def test_refused_is_a_system_exit():
    assert issubclass(decide.Refused, SystemExit)


def test_load_reads_an_infrastructure_slot_without_an_attempt_json(tmp_path: Path):
    night = write_night(tmp_path, [result("WORKSPACE_FAILED", None, slot=0)], skip_attempt={0})
    (got,) = decide.load(night)
    assert (got.cls, got.refusals, got.reaches) == (INFRA, 0, 0)


def test_load_reads_an_infrastructure_slot_whose_attempt_json_has_no_confinement(tmp_path: Path):
    night = write_night(tmp_path, [result("TRANSCRIPT_MISSING", None, slot=0),
                                   result("DEADLINE_EXCEEDED", None, slot=1, arm="engine", phase="setup")],
                        drop_key={0: "confinement", 1: "confinement"})
    got = decide.load(night)
    assert [(c.cls, c.refusals, c.reaches) for c in got] == [(INFRA, 0, 0), (INFRA, 0, 0)]


def test_load_still_refuses_a_non_infrastructure_cell_without_confinement(tmp_path: Path):
    night = write_night(tmp_path, [result("NO_PATCH", None, slot=0)], drop_key={0: "confinement"})
    with pytest.raises(decide.Refused, match=r"slot 0.*confinement"):
        decide.load(night)


def test_load_is_refused_when_attempt_json_disagrees_with_the_slot(tmp_path: Path):
    night = write_night(tmp_path, [result("OK", "pass", slot=4)])
    path = night / "baseline" / "t-4" / "attempt.json"
    body = json.loads(path.read_text())
    path.write_text(json.dumps({**body, "verdict": "fail"}))
    with pytest.raises(decide.Refused, match=r"slot 4.*verdict disagrees"):
        decide.load(night)
    path.write_text(json.dumps({**body, "code": "NO_PATCH"}))
    with pytest.raises(decide.Refused, match=r"slot 4.*code disagrees"):
        decide.load(night)
    path.write_text(json.dumps(body))
    assert [c.cls for c in decide.load(night)] == [D]


def test_load_cross_checks_an_infrastructure_slot_that_has_an_attempt_json(tmp_path: Path):
    night = write_night(tmp_path, [result("MODEL_ERROR", None, slot=2)])
    path = night / "baseline" / "t-2" / "attempt.json"
    path.write_text(json.dumps({"code": "OK", "verdict": "pass"}))
    with pytest.raises(decide.Refused, match=r"slot 2"):
        decide.load(night)


# counts

def test_counts_excludes_and_lists_a_reach_cell_under_both_settings():
    cs = cells("baseline", delivered=1) + [cell("baseline", D, reaches=1, slot=9)] + cells("engine", delivered=1)
    for admitted_only in (False, True):
        got = decide.counts(cs, admitted_only=admitted_only, unavailable="baseline-favouring")
        assert got["baseline"] == {"delivered": 1, "n": 1}
        assert [e["attempt_dir"] for e in got["excluded"]] == ["baseline-9-delivered"]
        assert got["excluded"][0]["arm"] == "baseline" and "reach" in got["excluded"][0]["why"]


def test_counts_keeps_a_refusal_only_cell_unless_admitted_only():
    cs = [cell("baseline", N, refusals=2), cell("baseline", D, slot=1), cell("engine", D, slot=2)]
    kept = decide.counts(cs, admitted_only=False, unavailable="baseline-favouring")
    assert kept["baseline"] == {"delivered": 1, "n": 2} and kept["excluded"] == []
    admitted = decide.counts(cs, admitted_only=True, unavailable="baseline-favouring")
    assert admitted["baseline"] == {"delivered": 1, "n": 1}
    assert [e["attempt_dir"] for e in admitted["excluded"]] == ["baseline-0-not delivered"]
    assert "refusal" in admitted["excluded"][0]["why"]


def test_counts_baseline_favouring_flips_unavailable_by_arm():
    cs = [cell("engine", U), cell("baseline", U, slot=1), cell("engine", D, slot=2), cell("baseline", N, slot=3)]
    got = decide.counts(cs, admitted_only=False, unavailable="baseline-favouring")
    assert got["engine"] == {"delivered": 1, "n": 2}
    assert got["baseline"] == {"delivered": 1, "n": 2}
    assert got["excluded"] == []


def test_counts_names_each_reclassified_unavailable_cell():
    cs = [cell("engine", U), cell("baseline", U, slot=1), cell("engine", D, slot=2),
          cell("baseline", U, reaches=1, slot=3)]
    got = decide.counts(cs, admitted_only=False, unavailable="baseline-favouring")
    assert [(r["attempt_dir"], r["arm"]) for r in got["reclassified"]] == [
        ("engine-0-unavailable", "engine"), ("baseline-1-unavailable", "baseline")]
    assert "not delivered" in got["reclassified"][0]["why"] and "as delivered" in got["reclassified"][1]["why"]
    assert [e["attempt_dir"] for e in got["excluded"]] == ["baseline-3-unavailable"]


def test_counts_reclassifies_nothing_when_unavailable_is_excluded():
    cs = [cell("engine", U), cell("baseline", U, slot=1), cell("engine", D, slot=2)]
    assert decide.counts(cs, admitted_only=False, unavailable="excluded")["reclassified"] == []
    assert decide.counts([cell("engine", D)], admitted_only=False, unavailable="baseline-favouring")["reclassified"] == []


def test_counts_excluded_removes_unavailable_from_both_arms_and_lists_them():
    cs = [cell("engine", U), cell("baseline", U, slot=1), cell("engine", D, slot=2), cell("baseline", N, slot=3)]
    got = decide.counts(cs, admitted_only=False, unavailable="excluded")
    assert got["engine"] == {"delivered": 1, "n": 1}
    assert got["baseline"] == {"delivered": 0, "n": 1}
    assert sorted(e["attempt_dir"] for e in got["excluded"]) == ["baseline-1-unavailable", "engine-0-unavailable"]


def test_counts_excludes_and_lists_infrastructure():
    cs = [cell("engine", INFRA), cell("engine", D, slot=1), cell("baseline", N, slot=2)]
    for setting in ("baseline-favouring", "excluded"):
        got = decide.counts(cs, admitted_only=False, unavailable=setting)
        assert got["engine"] == {"delivered": 1, "n": 1}
        assert [e["attempt_dir"] for e in got["excluded"]] == ["engine-0-infrastructure"]


def test_counts_rejects_an_unknown_unavailable_setting():
    with pytest.raises(ValueError):
        decide.counts([], admitted_only=False, unavailable="engine-favouring")
    assert decide.counts([], admitted_only=False, unavailable="excluded")["excluded"] == []


# fisher_one_sided

def test_fisher_matches_the_stated_value():
    assert decide.fisher_one_sided(11, 12, 6, 12) == pytest.approx(0.034324942791762014)


def test_fisher_equal_rates_are_above_one_half():
    assert decide.fisher_one_sided(6, 12, 6, 12) > 0.5


def test_fisher_extreme_case_is_one_over_choose():
    assert decide.fisher_one_sided(12, 12, 0, 12) == pytest.approx(1 / comb(24, 12))


def test_fisher_no_difference_in_an_empty_table_is_one():
    assert decide.fisher_one_sided(0, 0, 0, 0) == 1.0


def test_fisher_is_one_sided_in_the_engine_direction():
    assert decide.fisher_one_sided(0, 12, 12, 12) > 0.99


# decide

HOLDS = cells("engine", delivered=12) + cells("baseline", **{"not_delivered": 12})
ONE_COUNT = (cells("engine", delivered=9, **{"not_delivered": 3})
             + cells("baseline", delivered=2)
             + [cell("baseline", N, refusals=1, slot=50 + i) for i in range(10)])
NEGATIVE = cells("engine", delivered=6, **{"not_delivered": 6}) + cells("baseline", delivered=6, **{"not_delivered": 6})
# Engine 7 delivered + 5 unavailable; Baseline 3 delivered + 4 not delivered + 5 unavailable.
HOLDS_, ONE_, NEG_ = "holds", "not holding: rejects on one count only", "stated negative"
BESIDE_REJECTS = (cells("engine", delivered=7, unavailable=5)
                  + cells("baseline", delivered=3, **{"not_delivered": 4}, unavailable=5))


def test_decide_holds_when_both_counts_reject():
    got = decide.decide(HOLDS)
    assert got["verdict"] == "holds"
    assert got["primary"]["p"] <= 0.05 and got["admitted"]["p"] <= 0.05
    assert got["primary"]["counts"]["engine"] == {"delivered": 12, "n": 12}


def test_decide_rejecting_on_one_count_only_is_not_holding():
    got = decide.decide(ONE_COUNT)
    assert got["primary"]["p"] <= 0.05 < got["admitted"]["p"]
    assert got["admitted"]["counts"]["baseline"] == {"delivered": 2, "n": 2}
    assert got["verdict"] == "not holding: rejects on one count only"


def test_decide_rejecting_on_the_admitted_count_alone_is_also_not_holding():
    cs = HOLDS + [cell("engine", N, refusals=1, slot=70 + i) for i in range(40)]
    got = decide.decide(cs)
    assert got["primary"]["p"] > 0.05 >= got["admitted"]["p"]
    assert got["verdict"] == "not holding: rejects on one count only"


def test_decide_states_a_negative_when_neither_rejects():
    got = decide.decide(NEGATIVE)
    assert got["verdict"] == "stated negative"
    assert got["primary"]["p"] > 0.05 and got["admitted"]["p"] > 0.05


def test_decide_beside_reading_never_changes_the_verdict():
    got = decide.decide(BESIDE_REJECTS)
    assert got["beside"]["p"] <= 0.05 < got["primary"]["p"]
    assert got["verdict"] == "stated negative"
    assert decide.decide(HOLDS)["verdict"] == "holds"


def test_decide_beside_failing_to_reject_leaves_holds(monkeypatch: pytest.MonkeyPatch):
    """No real cell set separates them (a Baseline-favouring primary rejecting implies beside rejects on
    every small table searched), so the structure is shown by forcing beside to a non-rejecting reading."""
    real = decide._reading

    def reading(cs, alpha, *, admitted_only, unavailable):
        got = real(cs, alpha, admitted_only=admitted_only, unavailable=unavailable)
        return {**got, "p": 0.9, "rejects": False} if unavailable == "excluded" else got

    monkeypatch.setattr(decide, "_reading", reading)
    got = decide.decide(HOLDS)
    assert got["beside"]["rejects"] is False
    assert got["verdict"] == "holds"


def test_decide_is_refused_when_an_arm_is_empty_in_the_primary_reading():
    cs = cells("baseline", **{"not_delivered": 3}) + [cell("engine", D, reaches=1, slot=9)]
    with pytest.raises(decide.Refused, match=r"primary.*engine"):
        decide.decide(cs)


def test_decide_is_refused_when_an_arm_is_empty_in_the_admitted_reading():
    cs = cells("baseline", **{"not_delivered": 3}) + [cell("engine", D, refusals=1, slot=9)]
    with pytest.raises(decide.Refused, match=r"admitted.*engine"):
        decide.decide(cs)


def test_decide_with_every_arm_populated_is_not_refused():
    assert decide.decide(cells("baseline", delivered=1) + cells("engine", delivered=1))["verdict"] in {
        HOLDS_, ONE_, NEG_}


def test_decide_beside_uses_excluded_unavailable_and_lists_them():
    got = decide.decide(BESIDE_REJECTS)
    assert got["beside"]["counts"]["engine"] == {"delivered": 7, "n": 7}
    assert len(got["beside"]["counts"]["excluded"]) == 10


def test_decide_alpha_is_honoured():
    assert decide.decide(HOLDS, alpha=1e-12)["verdict"] == "stated negative"


# main

HEAD = "a" * 40


def record(path: Path, n: int, arm: str = "baseline+engine") -> Path:
    path.write_text(json.dumps({"arm": arm, "n": n}))
    return path


def sitting_night(root: Path, *, missing: set[int] = frozenset(), status: str = "complete",
                  sha: str | None = None, heads: tuple[str, ...] = (HEAD,), n: int = 3,
                  record_arm: str = "baseline+engine") -> tuple[Path, Path]:
    """Three cells per arm: Baseline fails every one, the Engine passes every one."""
    slots = []
    for i in range(2 * n):
        arm = "baseline" if i % 2 == 0 else "engine"
        slots.append(result("OK", "pass" if arm == "engine" else "fail", arm=arm, slot=i))
    night = write_night(root, [s for s in slots if s["slot"] not in missing])
    rec = record(root / "rec.json", n, record_arm)
    ledger = {"status": status, "record_sha256": sha or hashlib.sha256(rec.read_bytes()).hexdigest(),
              "sittings": [{"evals_head": h} for h in heads]}
    (night / "launch.json").write_text(json.dumps(ledger))
    return night, rec


def test_main_is_refused_on_an_incomplete_night(tmp_path: Path):
    night, rec = sitting_night(tmp_path, missing={4})
    with pytest.raises(decide.Refused, match="incomplete night: baseline 2 of 3, engine 3 of 3"):
        decide.main([str(night), str(rec)])


def test_main_decides_on_a_complete_night(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    night, rec = sitting_night(tmp_path)
    assert decide.main([str(night), str(rec)]) == 0
    out = capsys.readouterr().out
    body, table = out.split("\n\n", 1)
    parsed = json.loads(body)
    assert parsed["primary"]["counts"]["engine"] == {"delivered": 3, "n": 3}
    assert parsed["primary"]["counts"]["baseline"] == {"delivered": 0, "n": 3}
    assert parsed["primary"]["p"] == pytest.approx(0.05) and parsed["primary"]["rejects"] is True
    assert parsed["verdict"] == "holds"
    assert "| reading |" in table and "verdict: holds" in table


def test_main_prints_the_night_s_evals_heads(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    other = "b" * 40
    night, rec = sitting_night(tmp_path, heads=(HEAD, other, HEAD))
    decide.main([str(night), str(rec)])
    out = capsys.readouterr().out
    assert json.loads(out.split("\n\n", 1)[0])["evals_head"] == [HEAD, other]
    assert f"evals_head: {HEAD}, {other}" in out


def test_main_is_refused_on_a_record_with_other_arms(tmp_path: Path):
    night, rec = sitting_night(tmp_path, record_arm="baseline")
    with pytest.raises(decide.Refused, match="arms"):
        decide.main([str(night), str(rec)])


def test_main_is_refused_on_a_wrong_argument_count():
    with pytest.raises(decide.Refused, match="usage"):
        decide.main([])


def test_main_is_refused_when_the_night_is_not_complete(tmp_path: Path):
    night, rec = sitting_night(tmp_path, status="capped")
    with pytest.raises(decide.Refused, match="capped"):
        decide.main([str(night), str(rec)])


def test_main_is_refused_when_the_night_belongs_to_another_record(tmp_path: Path):
    night, rec = sitting_night(tmp_path, sha="0" * 64)
    with pytest.raises(decide.Refused, match="another record"):
        decide.main([str(night), str(rec)])


def test_main_is_refused_without_a_launch_ledger(tmp_path: Path):
    night, rec = sitting_night(tmp_path)
    (night / "launch.json").unlink()
    with pytest.raises(decide.Refused, match="launch.json"):
        decide.main([str(night), str(rec)])


def test_the_frozen_infrastructure_codes_equal_the_launchers_today():
    assert {c.value for c in decide.launch.INFRASTRUCTURE_CODES} == decide.EXPECTED_INFRASTRUCTURE_CODES
    assert {"WORKSPACE_FAILED", "CLEANUP_FAILED", "GRADE_FAILED", "TRANSCRIPT_MISSING", "TRANSCRIPT_EMPTY",
            "MODEL_ERROR", "PATCH_INVALID"} == decide.EXPECTED_INFRASTRUCTURE_CODES


def test_main_is_refused_when_the_launchers_infrastructure_codes_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    night, rec = sitting_night(tmp_path)
    drifted = frozenset(decide.launch.INFRASTRUCTURE_CODES - {decide.launch.AttemptCode.MODEL_ERROR})
    monkeypatch.setattr(decide.launch, "INFRASTRUCTURE_CODES", drifted)
    with pytest.raises(decide.Refused, match="infrastructure codes"):
        decide.main([str(night), str(rec)])
