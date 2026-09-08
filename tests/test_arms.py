"""The arm reader: committed arm files as executable inputs.

No model, no network, no subprocess.

**Why both directions.** A reader whose only test is "the two shipped
files load" would still pass if every validation were deleted, so each
refusal below names the field it removes from a known-good file and the
message it expects. Each refusal's sibling success is the unmodified
shipped file it was derived from — `arms/baseline.json` or
`arms/engine.json`, named in the test.
"""

import json
import tomllib
from pathlib import Path
from typing import cast

import pytest

from satyrn_evals.arms import (
    Arm,
    ArmError,
    ArmName,
    ArmPins,
    build_argv,
    load_arm,
)

ARMS_ROOT = Path(__file__).resolve().parents[1] / "arms"
BASELINE = ARMS_ROOT / "baseline.json"
ENGINE = ARMS_ROOT / "engine.json"
ENVELOPE = ARMS_ROOT / "envelope.json"


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


# --- successes: the two shipped files -------------------------------------


def test_baseline_file_loads_with_the_four_baseline_tools() -> None:
    """Fixture: arms/baseline.json."""
    arm = load_arm(BASELINE)
    assert arm.arm == "baseline"
    assert arm.tools == ("read", "bash", "edit", "write")
    assert arm.model == "omlx/gemma-4-12B-it-MLX-8bit"
    assert arm.server_model == "gemma-4-12B-it-MLX-8bit"
    assert arm.pins.pi == "0.84.4"
    assert arm.pins.engine_commit is None
    assert arm.pins.digests == {}


def test_engine_file_loads_with_read_edit_and_the_pinned_commit() -> None:
    """Fixture: arms/engine.json. Shape, not a copied digest: the pins are
    computed in the derivation doc and recomputed by preflight.sh."""
    arm = load_arm(ENGINE)
    assert arm.arm == "engine"
    assert arm.tools == ("read", "edit")
    assert arm.model == load_arm(BASELINE).model
    commit = arm.pins.engine_commit
    assert commit is not None
    # The pin moves only by a recorded decision, which is what this line is
    # for -- it failed when the pin was bumped and had to be updated on
    # purpose. 25ca0be was the repaired Engine commit V11c and V13 ran
    # against; b977941 adds the edit-schema fix that V13 found
    # (973 refused calls, five lost cells); bc0434a added E7's runner and
    # 8f1deb3 renamed it to bash, which is why the digest set covers
    # runner.ts and orchestrator.ts as well as the two original extensions.
    # fc22622 lands two repairs found by inspecting model-facing messages,
    # neither of them an experiment: the post-edit region now reserves the
    # changed span before spending budget on context, so it can no longer
    # report truncation while showing none of the edit; and a call key now
    # carries the revision of the workspace it addresses, so a read or a test
    # after a landed edit is not mistaken for a repeat. Only engine.ts's
    # digest moves -- the region fix is in mutation.py, which the digest set
    # does not cover and the commit pin does.
    assert commit.startswith("fc22622")
    assert len(commit) == 40
    assert set(arm.pins.digests) == {
        "engine.ts",
        "mutator.ts",
        "runner.ts",
        "orchestrator.ts",
    }
    assert all(len(value) == 64 for value in arm.pins.digests.values())


def test_the_two_arms_differ_only_in_argv_and_tools() -> None:
    """Fixtures: arms/baseline.json and arms/engine.json (spec §7 row 4)."""
    baseline, engine = load_arm(BASELINE), load_arm(ENGINE)
    assert baseline.model == engine.model
    assert baseline.server_model == engine.server_model
    assert baseline.pins.pi == engine.pins.pi
    assert baseline.tools != engine.tools
    assert baseline.argv != engine.argv


def test_envelope_file_loads_with_read_and_edit_only() -> None:
    """Fixture: arms/envelope.json."""
    arm = load_arm(ENVELOPE)
    assert arm.arm == "envelope"
    assert arm.tools == ("read", "edit")
    assert arm.model == "omlx/gemma-4-12B-it-MLX-8bit"
    assert arm.server_model == "gemma-4-12B-it-MLX-8bit"


def test_envelope_agrees_with_baseline_on_everything_but_arm_and_tools() -> None:
    """Envelope is byte-identical to Baseline except for the two fields
    that name it and give it Engine's tool surface (spec: bare pi run
    against Engine's own tools)."""
    baseline_data = json.loads(BASELINE.read_text(encoding="utf-8"))
    envelope_data = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    differing_keys = {
        key
        for key in baseline_data
        if baseline_data.get(key) != envelope_data.get(key)
    }
    assert differing_keys == {"arm", "tools"}
    assert envelope_data["arm"] == "envelope"
    assert envelope_data["tools"] == ["read", "edit"]

    baseline, envelope = load_arm(BASELINE), load_arm(ENVELOPE)
    assert baseline.model == envelope.model
    assert baseline.server_model == envelope.server_model
    assert baseline.pins == envelope.pins
    assert baseline.argv == envelope.argv
    assert baseline.tools != envelope.tools


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


def test_engine_commit_that_is_not_a_40_hex_sha_is_refused(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        ENGINE,
        pins={
            "pi": "0.84.4",
            "engine_commit": "75d4863",
            "digests": {"engine.ts": "0" * 64, "mutator.ts": "1" * 64},
        },
    )
    with pytest.raises(ArmError, match="engine_commit"):
        load_arm(path)


def test_engine_arm_missing_a_source_digest_is_refused(tmp_path: Path) -> None:
    pins = json.loads(ENGINE.read_text(encoding="utf-8"))["pins"]
    pins["digests"] = {"engine.ts": pins["digests"]["engine.ts"]}
    path = _write(tmp_path, ENGINE, pins=pins)
    with pytest.raises(ArmError, match="mutator.ts"):
        load_arm(path)


def test_engine_digest_that_is_not_a_64_hex_sha256_is_refused(tmp_path: Path) -> None:
    pins = json.loads(ENGINE.read_text(encoding="utf-8"))["pins"]
    pins["digests"] = {"engine.ts": "not-a-digest", "mutator.ts": "1" * 64}
    path = _write(tmp_path, ENGINE, pins=pins)
    with pytest.raises(ArmError, match="engine.ts"):
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
    """Fixture: arms/baseline.json. pi 0.84.4 rejects `--model=VALUE` in
    print mode — that is what engine 75d4863 fixed, and the trap is the
    same here (2026-09-04 V8 smoke record)."""
    argv = build_argv(load_arm(BASELINE))
    assert not any(token.startswith("--model=") for token in argv)
    index = argv.index("--model")
    assert argv[index + 1] == "omlx/gemma-4-12B-it-MLX-8bit"
    tools_index = argv.index("--tools")
    assert argv[tools_index + 1] == "read,bash,edit,write"
    assert argv[0] == "satyrn-evals-attempt-pi"


def test_baseline_argv_is_unchanged_by_the_envelope_addition() -> None:
    """Regression sibling for the envelope test below: adding a third arm
    must not perturb Baseline's own argv construction."""
    assert build_argv(load_arm(BASELINE)) == [
        "satyrn-evals-attempt-pi",
        "--model",
        "omlx/gemma-4-12B-it-MLX-8bit",
        "--tools",
        "read,bash,edit,write",
    ]


def test_envelope_argv_is_baseline_argv_with_engines_tools() -> None:
    """Fixture: arms/envelope.json. Envelope runs the same in-tree pi
    adapter as Baseline; only the `--tools` value differs."""
    assert build_argv(load_arm(ENVELOPE)) == [
        "satyrn-evals-attempt-pi",
        "--model",
        "omlx/gemma-4-12B-it-MLX-8bit",
        "--tools",
        "read,edit",
    ]


def test_engine_argv_carries_the_model_and_no_tools_flag() -> None:
    """Fixture: arms/engine.json. `satyrn-engine attempt` takes --model and
    a contract path only; its tool surface is fixed in build_pi_command."""
    argv = build_argv(load_arm(ENGINE))
    assert argv[:2] == ["satyrn-engine", "attempt"]
    assert "--tools" not in argv
    assert argv[argv.index("--model") + 1] == "omlx/gemma-4-12B-it-MLX-8bit"


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


def test_digests_that_are_not_a_name_to_digest_map_are_refused(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        ENGINE,
        pins={"pi": "0.84.4", "engine_commit": "a" * 40, "digests": {"engine.ts": 7}},
    )
    with pytest.raises(ArmError, match="digests must map"):
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


# --- scripts/preflight.sh reads these pins; it must not restate them ------


def _preflight() -> str:
    return (ARMS_ROOT.parent / "scripts" / "preflight.sh").read_text(encoding="utf-8")


def test_preflight_reads_the_pins_instead_of_restating_them() -> None:
    """A digest copied into the script is a second copy that can drift from
    the one `load_arm` reads. The script must contain neither pinned
    digest nor the pinned commit as a literal."""
    script = _preflight()
    arm = load_arm(ENGINE)
    assert arm.pins.engine_commit is not None
    for literal in (arm.pins.engine_commit, *arm.pins.digests.values()):
        assert literal not in script
    # ...and it must actually read them out of the committed arm files.
    # Checked generically since engine E7: the script iterates whatever
    # names the arm records rather than naming files, so that a source
    # added to the pin set cannot end up recorded but unchecked.
    assert 'pins digests "$name"' in script
    assert "pins engine_commit" in script


def test_preflight_checks_every_recorded_digest_not_a_fixed_pair() -> None:
    """The sibling for the pin test above. engine E7 added `runner.ts` as a
    third `--extension`; a preflight naming two files would have left it
    recorded and unchecked, which is how the temperature gap happened."""
    script = _preflight()
    arm = load_arm(ENGINE)

    assert len(arm.pins.digests) > 2
    for name in arm.pins.digests:
        assert name not in script, f"{name} is named literally in the script"


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
