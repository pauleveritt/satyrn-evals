"""The arm reader: committed arm files as executable inputs.

No model, no network, no subprocess.

**Why both directions.** A reader whose only test is "the shipped file
loads" would still pass if every validation were deleted, so each
refusal below names the field it removes from a known-good file and the
message it expects. Each refusal's sibling success is the unmodified
shipped file it was derived from — `arms/baseline.json`, named in the
test.
"""

import json
import tomllib
from pathlib import Path
from typing import cast

import pytest

from satyrn_evals.arms import (
    ENGINE_SOURCES,
    ENGINE_TOOLS,
    Arm,
    ArmError,
    ArmName,
    ArmPins,
    build_argv,
    load_arm,
)

ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms"
BASELINE = ARMS_ROOT / "baseline.json"


def _write(tmp_path: Path, source: Path, **changes: object) -> Path:
    """A copy of a shipped arm file with fields replaced or removed.

    A value of ``None`` removes the key, so a refusal test can name
    exactly the pin it took away.
    """
    data = json.loads(source.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    path = tmp_path / source.name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --- success: the shipped baseline file ------------------------------------


def test_baseline_file_loads_with_the_four_baseline_tools() -> None:
    """Fixture: arms/baseline.json."""
    arm = load_arm(BASELINE)
    assert arm.arm == "baseline"
    assert arm.tools == ("read", "bash", "edit", "write")
    assert arm.model == "omlx/gemma-4-12B-it-MLX-8bit"
    assert arm.server_model == "gemma-4-12B-it-MLX-8bit"
    assert arm.pins.pi == "0.85.1"
    assert arm.pins.engine_commit is None
    assert arm.pins.digests == {}


# --- refusals, each against a copy of a shipped file -----------------------


def test_missing_pins_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, pins=None)
    with pytest.raises(ArmError, match="pins"):
        load_arm(path)


def test_missing_pi_pin_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, pins={"engine_commit": None, "digests": {}})
    with pytest.raises(ArmError, match="pi"):
        load_arm(path)


def test_missing_model_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, model=None)
    with pytest.raises(ArmError, match="model"):
        load_arm(path)


def test_unknown_tool_name_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, tools=["read", "telepathy"])
    with pytest.raises(ArmError, match="telepathy"):
        load_arm(path)


def test_empty_tools_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, tools=[])
    with pytest.raises(ArmError, match="tools"):
        load_arm(path)


def test_empty_argv_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, argv=[])
    with pytest.raises(ArmError, match="argv"):
        load_arm(path)


def test_unknown_arm_name_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, arm="telepathy")
    with pytest.raises(ArmError, match="telepathy"):
        load_arm(path)


def test_baseline_carrying_an_engine_commit_is_refused(tmp_path: Path) -> None:
    """A pin that cannot apply to this arm is an authoring error, not a
    harmless extra: preflight would verify an engine checkout the Baseline
    arm never launches."""
    path = _write(
        tmp_path,
        BASELINE,
        pins={"pi": "0.84.4", "engine_commit": "a" * 40, "digests": {}},
    )
    with pytest.raises(ArmError, match="engine_commit"):
        load_arm(path)


def test_model_that_does_not_carry_the_server_model_is_refused(
    tmp_path: Path,
) -> None:
    """Spec §3: both naming surfaces are recorded, and they must agree."""
    path = _write(tmp_path, BASELINE, server_model="gemma-4-26B-A4B-it-OptiQ-4bit")
    with pytest.raises(ArmError, match="server_model"):
        load_arm(path)


def test_missing_server_model_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, server_model=None)
    with pytest.raises(ArmError, match="server_model"):
        load_arm(path)


def test_a_file_that_is_not_a_json_object_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ArmError, match="object"):
        load_arm(path)


# --- argv construction -----------------------------------------------------


def test_baseline_argv_uses_space_form_model_and_comma_joined_tools() -> None:
    """Fixture: arms/baseline.json. pi rejects `--model=VALUE` in print
    mode (confirmed through 0.85.1) — that is what engine 75d4863 fixed,
    and the trap is the same here (2026-09-04 V8 smoke record)."""
    argv = build_argv(load_arm(BASELINE))
    assert not any(token.startswith("--model=") for token in argv)
    index = argv.index("--model")
    assert argv[index + 1] == "omlx/gemma-4-12B-it-MLX-8bit"
    tools_index = argv.index("--tools")
    assert argv[tools_index + 1] == "read,bash,edit,write"
    assert argv[0] == "satyrn-evals-attempt-pi"


def test_baseline_argv_is_unchanged_by_the_envelope_addition() -> None:
    """Regression: a later arm sharing Baseline's pi adapter must not
    perturb Baseline's own argv construction."""
    assert build_argv(load_arm(BASELINE)) == [
        "satyrn-evals-attempt-pi",
        "--model",
        "omlx/gemma-4-12B-it-MLX-8bit",
        "--tools",
        "read,bash,edit,write",
    ]


def test_argv_construction_without_a_model_is_refused() -> None:
    """Spec §7 row 3. The sibling success is the row above."""
    arm = Arm(
        arm="baseline",
        argv=("satyrn-evals-attempt-pi",),
        tools=("read",),
        model="",
        server_model="",
        pins=ArmPins(pi="0.84.4", engine_commit=None, digests={}),
    )
    with pytest.raises(ArmError, match="model"):
        build_argv(arm)


def test_argv_holding_a_non_string_token_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, argv=["satyrn-evals-attempt-pi", 7])
    with pytest.raises(ArmError, match="non-empty strings"):
        load_arm(path)


def test_pins_that_are_not_an_object_are_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, BASELINE, pins=["0.84.4"])
    with pytest.raises(ArmError, match="pins must be an object"):
        load_arm(path)


def test_baseline_carrying_source_digests_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        BASELINE,
        pins={
            "pi": "0.84.4",
            "engine_commit": None,
            "digests": {"engine.ts": "0" * 64},
        },
    )
    with pytest.raises(ArmError, match="pins no sources"):
        load_arm(path)


def test_build_argv_refuses_an_arm_name_it_does_not_know() -> None:
    """A hand-built `Arm` must never yield an argv that silently drops the
    tool surface. The sibling successes are the two rows above."""
    arm = Arm(
        arm=cast(ArmName, "telepathy"),
        argv=("something",),
        tools=("read",),
        model="omlx/m",
        server_model="m",
        pins=ArmPins(pi="0.84.4", engine_commit=None, digests={}),
    )
    with pytest.raises(ArmError, match="unknown arm"):
        build_argv(arm)


def test_the_baseline_argv_names_an_installed_console_script() -> None:
    """Drift guard: `arms/baseline.json` names an executable, and the only
    thing that makes that name exist is pyproject's console-script table."""
    pyproject = tomllib.loads(
        (ARMS_ROOT.parent / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert load_arm(BASELINE).argv[0] in pyproject["project"]["scripts"]


# --- scripts/preflight.sh: the model proof, evals sha and token floor -----


def _preflight() -> str:
    return (ARMS_ROOT.parent / "scripts" / "preflight.sh").read_text(encoding="utf-8")


def test_preflight_proves_the_model_with_a_completion_not_a_listing() -> None:
    """The 2026-09-05 phantom `gemma-4-26B-A4B-it-OptiQ-4bit` was advertised
    on :8001 with no weights on the machine, so a listing is not evidence.
    Both directions: the completion endpoint is called, and no request in
    the script targets a model listing."""
    script = _preflight()
    assert "$BASE_URL/chat/completions" in script
    requests = [line for line in script.splitlines() if "curl" in line]
    assert requests, "the preflight makes no request at all"
    assert not any("models" in line for line in requests)


def test_preflight_records_the_evals_sha_and_demands_a_clean_tree() -> None:
    script = _preflight()
    assert 'EVALS_SHA="$(git -C "$EVALS_ROOT" rev-parse HEAD)"' in script
    assert 'git -C "$EVALS_ROOT" status --porcelain' in script


def test_preflight_demands_a_measured_token_floor() -> None:
    """The confirmed 2026-09-05 amendment's measurement duty, pinned.

    Preflight cannot *measure* the floor -- it runs before any workspace
    exists -- so it must instead refuse to proceed without one that a smoke
    already measured. Without this guard the requirement could be dropped and
    every other preflight assertion would still pass.
    """
    script = _preflight()
    assert "--token-floor-record" in script
    assert "require --token-floor-record" in script
    # it must reject a non-positive floor, not merely a missing file:
    # an absent measurement reported as 0 is the recorded silent-zero class.
    assert "input_token_floor" in script
    assert "token_floor.py" in script, "the refusal must name the tool that fixes it"


def test_baseline_compaction_is_its_own_arm(tmp_path: Path) -> None:
    """`baseline-compaction` loads as a distinct arm, so its cells can
    never be pooled with the `baseline` cells that ran while pi's
    compaction was unreachable. A shared name is exactly how that pooling
    would happen without anyone deciding it."""
    path = tmp_path / "arm.json"
    path.write_text(json.dumps({
        "arm": "baseline-compaction",
        "argv": ["satyrn-evals-attempt-pi"],
        "tools": ["read", "bash", "edit", "write"],
        "model": "omlx/m",
        "server_model": "m",
        "pins": {"pi": "0.84.4", "engine_commit": None, "digests": {}},
    }), encoding="utf-8")
    assert load_arm(path).arm == "baseline-compaction"


def test_an_unknown_arm_name_is_still_refused(tmp_path: Path) -> None:
    """The refusal sibling: widening the vocabulary by one name must not
    open it to any name."""
    path = tmp_path / "arm.json"
    path.write_text(json.dumps({
        "arm": "baseline-experimental",
        "argv": ["x"], "tools": ["read"], "model": "omlx/m",
        "server_model": "m",
        "pins": {"pi": "0.84.4", "engine_commit": None, "digests": {}},
    }), encoding="utf-8")
    with pytest.raises(ArmError, match="unknown arm"):
        load_arm(path)


def test_baseline_compaction_builds_the_baseline_argv(tmp_path: Path) -> None:
    """The two arms differ only in pi's own configuration, so their argv
    is identical -- which is exactly why that difference has to be pinned
    in the arm record and checked by preflight, where it is visible."""
    path = tmp_path / "arm.json"
    path.write_text(json.dumps({
        "arm": "baseline-compaction",
        "argv": ["satyrn-evals-attempt-pi"],
        "tools": ["read", "edit"],
        "model": "omlx/m", "server_model": "m",
        "pins": {"pi": "0.84.4", "engine_commit": None, "digests": {}},
    }), encoding="utf-8")
    assert build_argv(load_arm(path)) == [
        "satyrn-evals-attempt-pi", "--model", "omlx/m", "--tools", "read,edit"
    ]


# --- the committed Engine arm ----------------------------------------------

ENGINE = ARMS_ROOT / "engine-ornith15-9b.json"
ORNITH_BASELINE = ARMS_ROOT / "baseline-ornith15-9b.json"


def test_the_engine_arm_file_loads_with_the_engines_derived_contract_tool_surface() -> None:
    """Fixture: arms/engine-ornith15-9b.json. `satyrn-engine`
    `build_pi_command` hands pi `read,bash,edit,write,self_test` whenever the
    contract declares `test_command`, and `derive` always declares one."""
    arm = load_arm(ENGINE)
    assert arm.arm == "engine"
    assert arm.tools == ENGINE_TOOLS == ("read", "bash", "edit", "write", "self_test")
    assert arm.pins.engine_commit == "0a6e5df05f921a1e7a0c2b5e1697e86a96a3ecce"
    assert sorted(arm.pins.digests) == sorted(ENGINE_SOURCES)


def test_the_engine_arm_pins_all_seven_engine_package_sources() -> None:
    """The four always-loaded extensions, `runner.ts` (with `test_command`),
    and the two modules they import (`orchestrator.ts`, `paths.ts`)."""
    assert sorted(ENGINE_SOURCES) == [
        "bounds.ts", "engine.ts", "mutator.ts", "orchestrator.ts", "paths.ts", "runner.ts", "scope.ts",
    ]


def test_the_engine_arm_runs_the_export_of_its_pinned_commit_on_the_baselines_model_and_settings() -> None:
    engine = json.loads(ENGINE.read_text(encoding="utf-8"))
    baseline = json.loads(ORNITH_BASELINE.read_text(encoding="utf-8"))
    commit = engine["pins"]["engine_commit"]
    assert engine["argv"] == ["satyrn-evals-attempt-engine", "--engine-repo", f"/Users/Shared/satyrn-cells/engine-{commit}"]
    for key in ("model", "server_model", "inference", "settings_verified_by"):
        assert engine[key] == baseline[key], key
    assert engine["pins"]["pi"] == baseline["pins"]["pi"]
    assert build_argv(load_arm(ENGINE)) == [*engine["argv"], "--model", "omlx/Ornith-1.5-9B-MLX-8bit"]


def test_the_engine_arms_export_path_and_pinned_commit_cannot_drift_apart() -> None:
    """A re-pin edits `argv[2]`'s export path and `pins.engine_commit`
    together. Nothing else enforces that they name the same commit -- a
    re-pin that edits one and forgets the other is exactly the failure
    this test exists to catch, pinning the invariant rather than only
    today's literal shas."""
    arm = load_arm(ENGINE)
    assert Path(arm.argv[2]).name == f"engine-{arm.pins.engine_commit}"


def test_an_engine_arm_missing_a_source_digest_is_refused(tmp_path: Path) -> None:
    engine = json.loads(ENGINE.read_text(encoding="utf-8"))
    del engine["pins"]["digests"]["paths.ts"]
    path = _write(tmp_path, ENGINE, pins=engine["pins"])
    with pytest.raises(ArmError, match="missing paths.ts"):
        load_arm(path)


@pytest.mark.parametrize(
    "tools",
    [["read", "bash", "edit", "write"], ["read", "edit"], ["read", "bash", "edit", "write", "self_test", "grep"]],
    ids=["no-self-test", "old-read-edit", "extra"],
)
def test_an_engine_arm_whose_tools_are_not_the_engines_surface_is_refused(tmp_path: Path, tools: list[str]) -> None:
    path = _write(tmp_path, ENGINE, tools=tools)
    with pytest.raises(ArmError, match="read,bash,edit,write,self_test"):
        load_arm(path)


def test_a_baseline_arm_naming_self_test_is_refused(tmp_path: Path) -> None:
    """`self_test` exists only where the engine loads `runner.ts`; bare pi has no such tool."""
    path = _write(tmp_path, ORNITH_BASELINE, tools=["read", "bash", "edit", "write", "self_test"])
    with pytest.raises(ArmError, match="unknown tool name"):
        load_arm(path)
