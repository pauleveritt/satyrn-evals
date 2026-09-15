"""``launch RECORD``'s gates and wiring, with every git, sudo and spawn fact faked: nothing spawns."""

import json
import os
from pathlib import Path

import pytest

from satyrn_evals.arms import Arm
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, CELLS_ROOT
from satyrn_evals.cell_preflight import CellPreflight
from satyrn_evals.cli import main
from satyrn_evals.errors import SatyrnError
from satyrn_evals.launch import SLOTS_DIR, Slot, slot_path
from satyrn_evals.launch_record import LaunchFacts, launch_record
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.run_record import new_record, write_new_record

REPO = Path(__file__).resolve().parent.parent
ARM = REPO / "arms" / "baseline-ornith15-9b.json"
TASK = "agentclinic-repair-depth-3"
SETTINGS = '{"arm_sha256": "a"}'


def _record(tmp_path: Path, **over: object) -> Path:
    body = new_record(
        task=TASK, tasks_root=DEFAULT_TASKS_ROOT, arm="baseline", model="omlx/Ornith-1.5-9B-MLX-8bit", n=2, k=1,
        rung="R1", purpose="admission", isolation="isolated", mode="attended", max_minutes=60,
        token_budget=32000, turn_budget=48, previous_result=None, authority="test", decision_rule=None,
    )
    path = tmp_path / "records" / "depth-3.json"
    write_new_record(path, {**body, **over})
    return path


class Spawned(Exception):
    """Raised by the fake spawn: the gates passed and a cell would have started."""


def _facts(**over: object) -> LaunchFacts:
    def spawn(spec: Path, log: Path) -> object:
        raise Spawned(spec.read_text())

    base = dict(
        frozen=lambda path: True, committed=lambda path: True, head=lambda: "f" * 40,
        preflight=lambda **kw: CellPreflight([], {"pi_version": "0.85.1"}), settings=lambda path, cell: (0, SETTINGS),
        spawn_cell=spawn,
    )
    return LaunchFacts(**{**base, **over})  # type: ignore[arg-type]


def _launch(tmp_path: Path, record: Path, facts: LaunchFacts, **over: object) -> int:
    kwargs: dict[str, object] = dict(tasks_root=DEFAULT_TASKS_ROOT, runs_root=tmp_path / "runs", facts=facts, poll_interval=0.0, grace=0.0)
    return launch_record(record, [ARM], **{**kwargs, **over})  # type: ignore[arg-type]


def test_a_clean_admission_record_reaches_its_first_cell_with_the_records_settings(tmp_path: Path) -> None:
    record = _record(tmp_path)
    assert _launch(tmp_path, record, _facts()) == 3  # the fake spawn raised: interrupted
    spec = json.loads((tmp_path / "runs" / "depth-3" / SLOTS_DIR / "00.spec.json").read_text())
    assert spec["command"] == ["satyrn-evals-attempt-pi", "--model", "omlx/Ornith-1.5-9B-MLX-8bit", "--tools", "read,bash,edit,write"]
    assert (spec["rung"], spec["token_budget"], spec["turn_budget"], spec["isolation"]) == ("R1", 32000, 48, "isolated")
    assert (spec["timeout"], spec["attempt_timeout"]) == (1800.0, 2100.0)
    assert spec["output"] == str(tmp_path / "runs" / "depth-3" / "baseline")
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "interrupted" and result["sittings"][0]["evals_head"] == "f" * 40
    assert result["arms"]["baseline"]["finished"] == 0 and result["cells"] == []


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"settings": False}, "--no-settings"),
        ({"hunt": False}, "--no-hunt"),
        ({"timeout": 900.0}, "--timeout 900"),
        ({"attempt_timeout": 60.0}, "--attempt-timeout 60"),
    ],
)
def test_a_deciding_record_refuses_every_test_seam(tmp_path: Path, over: dict[str, object], message: str) -> None:
    record = _record(tmp_path)
    with pytest.raises(SatyrnError, match=message):
        _launch(tmp_path, record, _facts(), **over)
    assert not (tmp_path / "runs").exists()


def test_a_deciding_record_refuses_the_cell_path_seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, "/fake/bin")
    record = _record(tmp_path)
    assert main(["launch", str(record), "--arm", str(ARM), "--runs-root", str(tmp_path / "runs")]) == 2
    assert not (tmp_path / "runs").exists()


def test_a_development_record_may_use_the_seams(tmp_path: Path) -> None:
    record = _record(tmp_path, purpose="development", decision_rule="none")
    assert _launch(tmp_path, record, _facts(), settings=False, hunt=False, timeout=60.0, attempt_timeout=90.0) == 3


def _refused(tmp_path: Path, record: Path, facts: LaunchFacts) -> str:
    with pytest.raises(SatyrnError) as refusal:
        _launch(tmp_path, record, facts)
    assert refusal.value.exit_code == 2
    return str(refusal.value)


def test_an_unfrozen_record_is_refused_before_any_cell(tmp_path: Path) -> None:
    assert "not frozen" in _refused(tmp_path, _record(tmp_path), _facts(frozen=lambda path: False))
    assert not (tmp_path / "runs").exists()


def test_a_previous_result_that_is_not_committed_is_refused(tmp_path: Path) -> None:
    record = _record(tmp_path, previous_result="records/earlier.result.json")
    assert "is not committed" in _refused(tmp_path, record, _facts(committed=lambda path: False))
    assert _launch(tmp_path, record, _facts()) == 3  # committed: the gates pass


def test_an_arm_file_the_record_does_not_run_is_refused(tmp_path: Path) -> None:
    record = _record(tmp_path, arm="baseline+engine")
    assert "the --arm files are baseline" in _refused(tmp_path, record, _facts())


@pytest.mark.parametrize(
    "facts",
    [
        _facts(preflight=lambda **kw: CellPreflight(["the cell can find /x/known-good.patch"], {})),
        _facts(settings=lambda path, cell: (1, "preflight_settings FAILED: temperature")),
    ],
    ids=["cell-preflight", "settings"],
)
def test_a_preflight_or_settings_problem_exits_1_and_runs_nothing(
    tmp_path: Path, facts: LaunchFacts, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _launch(tmp_path, _record(tmp_path), facts) == 1
    assert "launch FAILED:" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()


def test_the_preflight_protects_the_runs_root_and_hunts_by_default(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def preflight(**kwargs: object) -> CellPreflight:
        seen.update(kwargs)
        return CellPreflight(["stop here"], {})

    assert _launch(tmp_path, _record(tmp_path), _facts(preflight=preflight)) == 1
    assert seen["hunt_root"] == "/" and seen["pinned_pi"] == "0.85.1"
    assert tmp_path / "runs" in seen["protected"]  # type: ignore[operator]


def test_the_preflight_tolerates_only_the_cell_path_prefixs_own_entry_under_the_cells_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5: without the test PATH seam, nothing is tolerated; with it set under
    the real cells root, only its direct child there is passed through."""
    seen: dict[str, object] = {}

    def preflight(**kwargs: object) -> CellPreflight:
        seen.update(kwargs)
        return CellPreflight([], {"pi_version": "0.85.1"})

    record = _record(tmp_path, purpose="development", decision_rule="none")
    assert _launch(tmp_path, record, _facts(preflight=preflight)) == 3
    assert seen["tolerated"] == ()

    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, os.fspath(CELLS_ROOT / "satyrn-test-abc123" / "bin"))
    seen.clear()
    assert _launch(tmp_path, record, _facts(preflight=preflight)) == 3
    assert seen["tolerated"] == (CELLS_ROOT / "satyrn-test-abc123",)


class Finishing:
    """A cell that has already written a NO_PATCH slot record."""

    def __init__(self, spec: Path) -> None:
        body = json.loads(spec.read_text())
        slot_path(spec.parent.parent, Slot(body["slot"], body["arm"])).write_text(json.dumps({
            "slot": body["slot"], "arm": body["arm"], "attempt_dir": "x", "code": "NO_PATCH", "verdict": None,
            "message": "attempt refused: NO_PATCH", "command_exit": 0, "deadline_phase": None,
        }))

    def poll(self) -> int:
        return 0

    def terminate(self) -> None: ...
    def kill(self) -> None: ...


class Recording:
    """A cell that finishes on its first poll, writing a slot record with a chosen code/verdict."""

    def __init__(self, spec: Path, *, code: str, verdict: str | None) -> None:
        body = json.loads(spec.read_text())
        slot_path(spec.parent.parent, Slot(body["slot"], body["arm"])).write_text(json.dumps({
            "slot": body["slot"], "arm": body["arm"], "attempt_dir": f"t-{body['slot']}", "code": code,
            "verdict": verdict, "message": f"attempt {code}", "command_exit": 0, "deadline_phase": None,
        }))

    def poll(self) -> int:
        return 0

    def terminate(self) -> None: ...
    def kill(self) -> None: ...


def test_an_infrastructure_slot_is_excluded_from_the_arms_counts_and_summary(tmp_path: Path) -> None:
    """The night stops on slot 1's MODEL_ERROR; slot 0's model outcome still counts, slot 1 does not."""
    codes, verdicts = iter(["OK", "MODEL_ERROR"]), iter(["pass", None])
    facts = _facts(spawn_cell=lambda spec, log: Recording(spec, code=next(codes), verdict=next(verdicts)))
    record = _record(tmp_path)
    assert _launch(tmp_path, record, facts) == 3
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "infrastructure"
    arm = result["arms"]["baseline"]
    assert (arm["finished"], arm["passes"], arm["code_counts"]) == (1, 1, {"OK": 1})
    assert arm["summary"] is None and "contamination" not in arm
    assert arm["infrastructure"] == [{"slot": 1, "code": "MODEL_ERROR", "attempt_dir": "t-1"}]
    assert [cell["infrastructure"] for cell in result["cells"]] == [False, True]


def test_an_all_model_outcome_arm_is_unaffected_by_the_infrastructure_exclusion(tmp_path: Path) -> None:
    """Sibling of the row above: no infrastructure outcome finishes, so nothing is excluded.

    Slot 1 never spawns (the fake raises, as ``_facts()``'s default spawn does for every test
    above that expects ``interrupted``) so this stays in the default tier without a real
    attempt directory for a completed arm to summarize.
    """
    calls = {"n": 0}

    def spawn_cell(spec: Path, log: Path) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            return Recording(spec, code="NO_PATCH", verdict=None)
        raise Spawned(spec.read_text())

    facts = _facts(spawn_cell=spawn_cell)
    record = _record(tmp_path)
    assert _launch(tmp_path, record, facts) == 3
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "interrupted"
    arm = result["arms"]["baseline"]
    assert (arm["finished"], arm["code_counts"]) == (1, {"NO_PATCH": 1})
    assert arm["infrastructure"] == [] and arm["summary"] is None
    assert [cell["infrastructure"] for cell in result["cells"]] == [False]


def test_a_summary_error_still_writes_a_result_with_best_effort_counts_and_exits_3(tmp_path: Path) -> None:
    """``write_arm_summaries`` raises once both slots are finished (no real attempt dirs on disk);
    the committed result must land anyway, with a ``summary_error`` and the counts still computed."""
    facts = _facts(spawn_cell=lambda spec, log: Recording(spec, code="OK", verdict="pass"))
    record = _record(tmp_path)
    assert _launch(tmp_path, record, facts) == 3
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "complete"  # the outcome itself completed; only the summary step failed
    assert "summary_error" in result and result["summary_error"]
    arm = result["arms"]["baseline"]
    assert (arm["finished"], arm["passes"], arm["code_counts"]) == (2, 2, {"OK": 2})
    assert arm["summary"] is None and arm["infrastructure"] == []


def test_a_settings_change_between_cells_stops_the_night_as_drift(tmp_path: Path) -> None:
    answers = iter([(0, SETTINGS), (0, SETTINGS), (0, '{"arm_sha256": "b"}')])
    facts = _facts(settings=lambda path, cell: next(answers), spawn_cell=lambda spec, log: Finishing(spec))
    record = _record(tmp_path)
    assert _launch(tmp_path, record, facts) == 3
    result = json.loads(record.with_suffix(".result.json").read_text())
    assert result["status"] == "infrastructure"
    assert result["reason"] == "preflight drift: the settings provenance for baseline changed"
    assert [c["slot"] for c in result["cells"]] == [0]


def test_a_night_directory_of_another_record_is_refused(tmp_path: Path) -> None:
    first = _record(tmp_path)
    assert _launch(tmp_path, first, _facts()) == 3
    other = tmp_path / "elsewhere" / "depth-3.json"
    other.parent.mkdir()
    other.write_text(first.read_text().replace('"k": 1', '"k": 2'))
    assert "belongs to another record" in _refused(tmp_path, other, _facts())


# --- the Engine arm: route proof --------------------------------------------

ENGINE_ARM = REPO / "arms" / "engine-ornith15-9b.json"
ROUTE_PROOF_RULE = "route proof: guards fire where retained Baseline evidence says they should; receipt read"


def _route_proof(tmp_path: Path) -> Path:
    body = new_record(
        task=TASK, tasks_root=DEFAULT_TASKS_ROOT, arm="engine", model="omlx/Ornith-1.5-9B-MLX-8bit", n=1, k=1,
        rung="R1", purpose="route-proof", isolation="isolated", mode="attended", max_minutes=60,
        token_budget=32000, turn_budget=48, previous_result="records/x.result.json", authority="test",
        decision_rule=ROUTE_PROOF_RULE,
    )
    path = tmp_path / "records" / "route-proof.json"
    write_new_record(path, body)
    return path


def test_a_route_proof_record_runs_the_committed_engine_arm_on_its_export(tmp_path: Path) -> None:
    seen: list[str] = []

    def export(arm: Arm) -> list[str]:
        seen.append(arm.arm)
        return []

    record = _route_proof(tmp_path)
    assert launch_record(
        record, [ENGINE_ARM], tasks_root=DEFAULT_TASKS_ROOT, runs_root=tmp_path / "runs",
        facts=_facts(engine_export=export), poll_interval=0.0, grace=0.0,
    ) == 3  # the fake spawn raised: interrupted
    assert seen == ["engine"]
    spec = json.loads((tmp_path / "runs" / "route-proof" / SLOTS_DIR / "00.spec.json").read_text())
    commit = "341d4c450317f63e6af8958d45606cb737a131af"
    assert spec["command"] == [
        "satyrn-evals-attempt-engine", "--engine-repo", f"/Users/Shared/satyrn-cells/engine-{commit}",
        "--model", "omlx/Ornith-1.5-9B-MLX-8bit",
    ]
    assert (spec["arm"], spec["rung"], spec["isolation"]) == ("engine", "R1", "isolated")


def test_an_engine_export_problem_exits_1_and_runs_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    facts = _facts(engine_export=lambda arm: ["the engine export /x is not under /Users/Shared/satyrn-cells"])
    assert launch_record(
        _route_proof(tmp_path), [ENGINE_ARM], tasks_root=DEFAULT_TASKS_ROOT, runs_root=tmp_path / "runs",
        facts=facts, poll_interval=0.0, grace=0.0,
    ) == 1
    assert "launch FAILED: engine: the engine export /x is not under" in capsys.readouterr().err
    assert not (tmp_path / "runs").exists()
