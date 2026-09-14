"""The seeded schedule: reproducible from its recorded seed, or refused.

No model, no network, no subprocess.

**Why both directions.** A schedule builder that ignored its seed would
still produce a balanced order, and every assertion about balance would
still pass — so the reproducibility rows below assert the order element by
element across two calls, and assert that two different seeds do not agree.
The refusal rows each name what they took away.

The last row is the cross-check that matters most: the schedule this
script writes is read back by `scripts/tally.py`. Two files that agree
only in a document drift; these two are proven to agree.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import interleave as interleave_module  # noqa: E402, I001
from interleave import (  # noqa: E402  # type: ignore[missing-import]  # scripts/ added via sys.path above
    ScheduleError,
    build_order,
    build_schedule,
    main,
    materialize,
)
from tally import TallyRefused, tally  # noqa: E402  # type: ignore[missing-import]
from satyrn_evals.arms import Arm, ArmPins  # noqa: E402
from satyrn_evals.arms import load_arm as real_load_arm  # noqa: E402

ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms"
BASELINE = ARMS_ROOT / "baseline.json"
DIGEST = "c" * 64
TASK = "agentclinic-repair-plausible-wrong-fix"
BALANCED = {"baseline": 12, "engine": 12}


# --- the dropped Engine arm, held in memory ---------------------------------
#
# `arms/engine.json` pins the retired attempt-route Engine and is
# deliberately not imported into this tree (Phase 2 writes the
# release-one Engine arm). The tests below still need a second, real
# arm to exercise two-arm scheduling, `materialize`, `main` and the
# `tally.py` cross-check, so this is the pinned tag's own
# `arms/engine.json` content -- `git show
# pre-release-one-2026-09-13:arms/engine.json` -- carried in memory
# instead of read from a committed file. `ENGINE` is a bare filename,
# not a real path: `_use_synthetic_engine_arm` below recognizes it by
# name and never touches disk for it.

ENGINE = Path("engine.json")

ENGINE_ARM_JSON = {
    "arm": "engine",
    "argv": ["satyrn-engine", "attempt"],
    "tools": ["read", "edit"],
    "model": "omlx/gemma-4-12B-it-MLX-8bit",
    "server_model": "gemma-4-12B-it-MLX-8bit",
    "pins": {
        "pi": "0.85.1",
        "engine_commit": "fc22622ac39f71ff9d0ad42718da4e1bd3500ac3",
        "digests": {
            "engine.ts": "c3ec10eb8a3efe457f1fff455bf72fa24d0d3168c1c88167eac28507e749fa46",
            "mutator.ts": "fd64391cfb7d63ba99fe4643d9c7031a286433a5df992a156ba5f7abe388489d",
            "runner.ts": "07b7cb49e8658cd80df89a209ac6b0c44211d17ce60fd8a951822f4034c6962c",
            "orchestrator.ts": "e2c8bfc078e6aaa5a63c67b9d37264f6d3d696b7d438f19fbc062d83951075aa",
        },
    },
}

ENGINE_ARM = Arm(
    arm="engine",
    argv=tuple(ENGINE_ARM_JSON["argv"]),
    tools=tuple(ENGINE_ARM_JSON["tools"]),
    model=ENGINE_ARM_JSON["model"],
    server_model=ENGINE_ARM_JSON["server_model"],
    pins=ArmPins(
        pi=ENGINE_ARM_JSON["pins"]["pi"],
        engine_commit=ENGINE_ARM_JSON["pins"]["engine_commit"],
        digests=dict(ENGINE_ARM_JSON["pins"]["digests"]),
    ),
)


def _use_synthetic_engine_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route a `load_arm` call named `engine.json` to the in-memory
    `ENGINE_ARM` above; every other path -- notably `arms/baseline.json`
    -- still reads its real committed file, unchanged."""
    monkeypatch.setattr(
        interleave_module,
        "load_arm",
        lambda path: (
            ENGINE_ARM if Path(path).name == "engine.json" else real_load_arm(path)
        ),
    )


# --- reproducibility -------------------------------------------------------


def test_the_same_seed_yields_the_same_order_element_by_element() -> None:
    first = build_order(seed=20260905, per_arm=BALANCED)
    second = build_order(seed=20260905, per_arm=BALANCED)
    assert first == second
    for index, (left, right) in enumerate(zip(first, second, strict=True)):
        assert left == right, f"position {index}"


def test_the_order_holds_exactly_twelve_of_each_arm() -> None:
    assert Counter(build_order(seed=20260905, per_arm=BALANCED)) == Counter(BALANCED)


def test_two_different_seeds_do_not_produce_the_same_order() -> None:
    """Without this the builder could ignore its seed and every balance
    assertion above would still pass."""
    assert build_order(seed=1, per_arm=BALANCED) != build_order(
        seed=2, per_arm=BALANCED
    )


# --- refusals --------------------------------------------------------------


def test_a_missing_seed_is_refused() -> None:
    with pytest.raises(ScheduleError, match="seed"):
        build_order(seed=None, per_arm=BALANCED)


def test_an_unbalanced_request_is_refused() -> None:
    with pytest.raises(ScheduleError, match="unbalanced"):
        build_order(seed=1, per_arm={"baseline": 12, "engine": 11})


def test_a_zero_length_arm_is_refused() -> None:
    with pytest.raises(ScheduleError, match="at least one"):
        build_order(seed=1, per_arm={"baseline": 0, "engine": 0})


def test_no_arms_at_all_is_refused() -> None:
    with pytest.raises(ScheduleError, match="arm"):
        build_order(seed=1, per_arm={})


def test_arms_that_do_not_agree_on_the_model_are_refused(tmp_path: Path) -> None:
    """A schedule whose arms address different models cannot support any
    comparison; the sibling success is every other row in this file, which
    uses the two shipped arm files."""
    other = tmp_path / "engine.json"
    data = dict(ENGINE_ARM_JSON)
    data["model"] = "omlx/other-model"
    data["server_model"] = "other-model"
    other.write_text(json.dumps(data))
    with pytest.raises(ScheduleError, match="model"):
        build_schedule(
            seed=1,
            arm_paths=[BASELINE, other],
            per_arm={"baseline": 2, "engine": 2},
            task=TASK,
            rung="R1",
            contract_digest=DIGEST,
        )


def test_arms_with_disagreeing_server_models_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The schedule records server identity separately from requested argv.

    Both server names are valid suffixes of the same provider-qualified
    requested model; only their agreement is under test here.
    """
    model = "provider/model-a/model-b"
    baseline = Arm(
        arm="baseline",
        argv=("pi",),
        tools=("read",),
        model=model,
        server_model="model-b",
        pins=ArmPins(pi="0.84.4", engine_commit=None, digests={}),
    )
    engine = Arm(
        arm="engine",
        argv=("satyrn-engine", "attempt"),
        tools=("read",),
        model=model,
        server_model="model-a/model-b",
        pins=ArmPins(pi="0.84.4", engine_commit=None, digests={}),
    )
    monkeypatch.setattr(
        interleave_module,
        "load_arm",
        lambda path: baseline if Path(path).name == "baseline.json" else engine,
    )
    with pytest.raises(ScheduleError, match="server model"):
        build_schedule(
            seed=1,
            arm_paths=[Path("baseline.json"), Path("engine.json")],
            per_arm={"baseline": 2, "engine": 2},
            task=TASK,
            rung="R1",
            contract_digest=DIGEST,
        )


def test_materialize_refuses_a_directory_that_already_holds_a_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run` overwrites `summary.json` in place, so reusing a root would
    silently destroy a recorded cell."""
    _use_synthetic_engine_arm(monkeypatch)
    schedule = build_schedule(
        seed=1,
        arm_paths=[BASELINE, ENGINE],
        per_arm={"baseline": 2, "engine": 2},
        task=TASK,
        rung="R1",
        contract_digest=DIGEST,
    )
    runs = tmp_path / "runs"
    materialize(schedule, runs)
    with pytest.raises(ScheduleError, match="exists"):
        materialize(schedule, runs)


# --- the schedule and its directories --------------------------------------


def test_the_schedule_names_one_directory_per_cell_with_that_arms_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_synthetic_engine_arm(monkeypatch)
    schedule = build_schedule(
        seed=20260905,
        arm_paths=[BASELINE, ENGINE],
        per_arm=BALANCED,
        task=TASK,
        rung="R1",
        contract_digest=DIGEST,
    )
    assert schedule["version"] == 2
    assert schedule["model"] == "omlx/gemma-4-12B-it-MLX-8bit"
    assert schedule["server_model"] == "gemma-4-12B-it-MLX-8bit"
    assert schedule["seed"] == 20260905
    assert len(schedule["cells"]) == 24
    assert len({cell["dir"] for cell in schedule["cells"]}) == 24
    baseline_cells = [c for c in schedule["cells"] if c["arm"] == "baseline"]
    assert len(baseline_cells) == 12
    assert baseline_cells[0]["command"][0] == "satyrn-evals-attempt-pi"
    engine_cells = [c for c in schedule["cells"] if c["arm"] == "engine"]
    assert engine_cells[0]["command"][:2] == ["satyrn-engine", "attempt"]
    assert all("--model" in cell["command"] for cell in schedule["cells"])

    runs = tmp_path / "runs"
    written = materialize(schedule, runs)
    assert len(written) == 24
    assert sorted(p.name for p in runs.iterdir() if p.is_dir()) == sorted(
        cell["dir"] for cell in schedule["cells"]
    )


def test_the_realized_order_is_written_before_any_cell_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_synthetic_engine_arm(monkeypatch)
    runs = tmp_path / "runs"
    assert (
        main(
            [
                "--seed",
                "20260905",
                "--n",
                "12",
                "--task",
                TASK,
                "--rung",
                "R1",
                "--contract-digest",
                DIGEST,
                "--output",
                str(runs),
                str(BASELINE),
                str(ENGINE),
            ]
        )
        == 0
    )
    written = json.loads((runs / "schedule.json").read_text())
    assert [cell["arm"] for cell in written["cells"]] == build_order(
        seed=20260905, per_arm=BALANCED
    )
    # every directory exists and every one of them is empty: nothing has run
    for cell in written["cells"]:
        directory = runs / cell["dir"]
        assert directory.is_dir()
        assert list(directory.iterdir()) == []


def test_the_schedule_is_the_one_tally_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cross-check: `tally.py` reads this schedule and refuses exactly
    24 missing cells — proving the two scripts agree on the format rather
    than agreeing only in a document."""
    _use_synthetic_engine_arm(monkeypatch)
    runs = tmp_path / "runs"
    main(
        [
            "--seed",
            "7",
            "--n",
            "12",
            "--task",
            TASK,
            "--rung",
            "R1",
            "--contract-digest",
            DIGEST,
            "--output",
            str(runs),
            str(BASELINE),
            str(ENGINE),
        ]
    )
    with pytest.raises(TallyRefused) as caught:
        tally(runs / "schedule.json", runs)
    kinds = [refusal.kind for refusal in caught.value.refusals]
    assert kinds == ["missing"] * 24


def test_main_refuses_an_unbalanced_or_seedless_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling success: the two rows above. `--n 0` is the reachable
    CLI-level refusal; argparse itself rejects a missing `--seed`."""
    _use_synthetic_engine_arm(monkeypatch)
    runs = tmp_path / "runs"
    assert (
        main(
            [
                "--seed",
                "1",
                "--n",
                "0",
                "--task",
                TASK,
                "--rung",
                "R1",
                "--contract-digest",
                DIGEST,
                "--output",
                str(runs),
                str(BASELINE),
                str(ENGINE),
            ]
        )
        == 1
    )
    assert not runs.exists()
    with pytest.raises(SystemExit):
        main(
            [
                "--n",
                "12",
                "--task",
                TASK,
                "--rung",
                "R1",
                "--contract-digest",
                DIGEST,
                "--output",
                str(runs),
                str(BASELINE),
                str(ENGINE),
            ]
        )


def test_an_arm_the_schedule_needs_but_has_no_file_for_is_refused() -> None:
    """Sibling success: every schedule row above passes both arm files."""
    with pytest.raises(ScheduleError, match="no arm file for engine"):
        build_schedule(
            seed=1,
            arm_paths=[BASELINE],
            per_arm={"baseline": 2, "engine": 2},
            task=TASK,
            rung="R1",
            contract_digest=DIGEST,
        )
