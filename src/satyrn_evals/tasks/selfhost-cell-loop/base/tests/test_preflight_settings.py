"""Preflight refuses an arm whose inference block is not enforced anywhere.

`arms/baseline-ornith15-9b.json` declared a full `inference` block for
`Ornith-1.5-9B-MLX-8bit`. That id was absent from the oMLX server's
`model_settings.json` -- the config that actually governs sampling --
while pi's `models.json` did carry a matching entry. One of two configs
agreeing is not the setting being enforced, and nothing compared the
claim to either file. This is the check that would have caught it. Each
refusal below has its sibling success, per `BRIEF.md` rule 6.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight_settings import (  # noqa: E402, I001
    _agrees,
    compare,
    main,
    omlx_entry,
    pi_entry,
    provenance,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ARMS_ROOT = _REPO_ROOT / "arms"

# --- fixtures --------------------------------------------------------------

_ARM_INFERENCE = {
    "context_window": 262144,
    "max_tokens": 32000,
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 0.0,
    "repetition_penalty": 1.0,
    "declares_reasoning": True,
}

_OMLX_SETTINGS = {
    "models": {
        "Ornith-1.5-9B-MLX-8bit": {
            "max_context_window": 262144,
            "max_tokens": 32000,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "enable_thinking": True,
        }
    }
}

_PI_MODELS = {
    "providers": {
        "omlx": {
            "models": [
                {
                    "id": "Ornith-1.5-9B-MLX-8bit",
                    "contextWindow": 262144,
                    "maxTokens": 32000,
                    "reasoning": True,
                    "samplingParams": {
                        "temperature": 0.6,
                        "top_p": 0.95,
                        "top_k": 20,
                        "min_p": 0.0,
                        "presence_penalty": 0.0,
                        "repetition_penalty": 1.0,
                    },
                }
            ]
        }
    }
}


def _omlx_model() -> dict:
    return dict(_OMLX_SETTINGS["models"]["Ornith-1.5-9B-MLX-8bit"])


def _pi_model() -> dict:
    return json.loads(json.dumps(_PI_MODELS["providers"]["omlx"]["models"][0]))


# --- omlx_entry / pi_entry ---------------------------------------------------


def test_omlx_entry_found() -> None:
    assert omlx_entry(_OMLX_SETTINGS, "Ornith-1.5-9B-MLX-8bit") == _omlx_model()


def test_omlx_entry_not_found() -> None:
    assert omlx_entry(_OMLX_SETTINGS, "no-such-model") is None


def test_omlx_entry_not_found_empty_settings() -> None:
    assert omlx_entry({}, "Ornith-1.5-9B-MLX-8bit") is None


def test_pi_entry_found() -> None:
    assert pi_entry(_PI_MODELS, "omlx", "Ornith-1.5-9B-MLX-8bit") == _pi_model()


def test_pi_entry_not_found_wrong_id() -> None:
    assert pi_entry(_PI_MODELS, "omlx", "no-such-model") is None


def test_pi_entry_not_found_wrong_provider() -> None:
    assert pi_entry(_PI_MODELS, "openrouter-curated", "Ornith-1.5-9B-MLX-8bit") is None


def test_pi_entry_not_found_empty_models() -> None:
    assert pi_entry({}, "omlx", "Ornith-1.5-9B-MLX-8bit") is None


# --- compare: clean and missing-entry cases ---------------------------------


def test_compare_clean_when_all_agree() -> None:
    assert compare(_ARM_INFERENCE, _omlx_model(), _pi_model()) == []


def test_compare_missing_omlx_entry_names_omlx() -> None:
    lines = compare(_ARM_INFERENCE, None, _pi_model())
    assert len(lines) == 1
    assert lines[0].startswith("omlx:")
    assert "model_settings.json" in lines[0]


def test_compare_missing_pi_entry_names_pi() -> None:
    lines = compare(_ARM_INFERENCE, _omlx_model(), None)
    assert len(lines) == 1
    assert lines[0].startswith("pi:")
    assert "models.json" in lines[0]


def test_compare_missing_both_entries_names_both() -> None:
    lines = compare(_ARM_INFERENCE, None, None)
    assert len(lines) == 2
    assert {line.split(":")[0] for line in lines} == {"omlx", "pi"}


def test_compare_undeclared_field_is_not_checked() -> None:
    """An arm that pins nothing makes no claim this check can contradict."""
    assert compare({}, {}, {}) == []


# --- compare: one mismatch per mapped field ---------------------------------

_OMLX_MISMATCH_FIELDS = [
    ("temperature", "temperature", 0.9),
    ("top_p", "top_p", 0.5),
    ("top_k", "top_k", 40),
    ("min_p", "min_p", 0.1),
    ("context_window", "max_context_window", 8000),
    ("max_tokens", "max_tokens", 999),
    ("declares_reasoning", "enable_thinking", False),
]


@pytest.mark.parametrize("arm_field,omlx_field,bad_value", _OMLX_MISMATCH_FIELDS)
def test_compare_one_omlx_field_mismatch(
    arm_field: str, omlx_field: str, bad_value: object
) -> None:
    omlx = _omlx_model()
    omlx[omlx_field] = bad_value
    lines = compare(_ARM_INFERENCE, omlx, _pi_model())
    assert len(lines) == 1
    assert lines[0].startswith("omlx:")
    assert arm_field in lines[0]


@pytest.mark.parametrize("arm_field,omlx_field", [(f, o) for f, o, _ in _OMLX_MISMATCH_FIELDS])
def test_compare_one_omlx_field_absent_from_entry(arm_field: str, omlx_field: str) -> None:
    omlx = _omlx_model()
    del omlx[omlx_field]
    lines = compare(_ARM_INFERENCE, omlx, _pi_model())
    assert len(lines) == 1
    assert lines[0].startswith("omlx:")
    assert arm_field in lines[0]


_PI_DIRECT_MISMATCH_FIELDS = [
    ("context_window", "contextWindow", 8000),
    ("max_tokens", "maxTokens", 999),
    ("declares_reasoning", "reasoning", False),
]


@pytest.mark.parametrize("arm_field,pi_field,bad_value", _PI_DIRECT_MISMATCH_FIELDS)
def test_compare_one_pi_direct_field_mismatch(
    arm_field: str, pi_field: str, bad_value: object
) -> None:
    pi = _pi_model()
    pi[pi_field] = bad_value
    lines = compare(_ARM_INFERENCE, _omlx_model(), pi)
    assert len(lines) == 1
    assert lines[0].startswith("pi:")
    assert arm_field in lines[0]


_PI_SAMPLING_MISMATCH_FIELDS = [
    ("temperature", "temperature", 0.9),
    ("top_p", "top_p", 0.5),
    ("top_k", "top_k", 40),
    ("min_p", "min_p", 0.1),
    ("presence_penalty", "presence_penalty", 0.2),
    ("repetition_penalty", "repetition_penalty", 1.2),
]


@pytest.mark.parametrize("arm_field,pi_field,bad_value", _PI_SAMPLING_MISMATCH_FIELDS)
def test_compare_one_pi_sampling_field_mismatch(
    arm_field: str, pi_field: str, bad_value: object
) -> None:
    pi = _pi_model()
    pi["samplingParams"][pi_field] = bad_value
    lines = compare(_ARM_INFERENCE, _omlx_model(), pi)
    assert len(lines) == 1
    assert lines[0].startswith("pi:")
    assert arm_field in lines[0]


def test_compare_one_pi_sampling_field_absent() -> None:
    pi = _pi_model()
    del pi["samplingParams"]["temperature"]
    lines = compare(_ARM_INFERENCE, _omlx_model(), pi)
    assert len(lines) == 1
    assert lines[0].startswith("pi:")
    assert "temperature" in lines[0]


def test_compare_pi_missing_sampling_params_block_is_one_line() -> None:
    """An entry with no `samplingParams` at all names the absent block once,
    not once per declared field -- the documented shape of the Ornith gap."""
    pi = _pi_model()
    del pi["samplingParams"]
    lines = [
        line for line in compare(_ARM_INFERENCE, _omlx_model(), pi) if line.startswith("pi:")
    ]
    assert len(lines) == 1
    assert "samplingParams" in lines[0]


# --- compare / _agrees: bool is not a number, int/float of equal value is --


def test_agrees_bool_vs_int_is_mismatch() -> None:
    assert _agrees(True, 1) is False
    assert _agrees(False, 0.0) is False


def test_agrees_matching_bools_agree() -> None:
    assert _agrees(True, True) is True
    assert _agrees(False, False) is True


def test_agrees_int_float_of_equal_value_agrees() -> None:
    assert _agrees(20, 20.0) is True


def test_compare_bool_vs_int_is_a_mismatch_at_omlx() -> None:
    """`enable_thinking: 1` must not silently satisfy `declares_reasoning: true`."""
    omlx = _omlx_model()
    omlx["enable_thinking"] = 1
    lines = compare(_ARM_INFERENCE, omlx, _pi_model())
    assert len(lines) == 1
    assert lines[0].startswith("omlx:")
    assert "declares_reasoning" in lines[0]


def test_compare_bool_vs_int_sibling_success_when_both_bool() -> None:
    """The sibling of the mismatch above: matching bools still agree."""
    omlx = _omlx_model()
    omlx["enable_thinking"] = True
    assert compare(_ARM_INFERENCE, omlx, _pi_model()) == []


def test_compare_bool_vs_int_is_a_mismatch_at_pi() -> None:
    pi = _pi_model()
    pi["reasoning"] = 1
    lines = compare(_ARM_INFERENCE, _omlx_model(), pi)
    assert len(lines) == 1
    assert lines[0].startswith("pi:")
    assert "declares_reasoning" in lines[0]


def test_compare_int_vs_float_of_equal_value_is_not_a_mismatch() -> None:
    """`top_k: 20` and `top_k: 20.0` are the same config value."""
    omlx = _omlx_model()
    omlx["top_k"] = 20.0
    assert compare(_ARM_INFERENCE, omlx, _pi_model()) == []


# --- provenance: digests -----------------------------------------------------


def test_provenance_digest_stable_under_key_reorder() -> None:
    arm_text_a = json.dumps({"a": 1, "b": 2})
    arm_text_b = json.dumps({"b": 2, "a": 1})
    assert provenance(arm_text_a, None, None)["arm_sha256"] == (
        provenance(arm_text_b, None, None)["arm_sha256"]
    )


def test_provenance_entry_digest_stable_under_key_reorder() -> None:
    omlx_a = {"temperature": 0.6, "max_tokens": 100}
    omlx_b = {"max_tokens": 100, "temperature": 0.6}
    record_a = provenance("{}", omlx_a, None)
    record_b = provenance("{}", omlx_b, None)
    assert record_a["omlx_entry_sha256"] == record_b["omlx_entry_sha256"]


def test_provenance_missing_entries_have_none_digests() -> None:
    record = provenance("{}", None, None)
    assert record["omlx_entry_sha256"] is None
    assert record["pi_entry_sha256"] is None
    assert record["omlx_entry"] is None
    assert record["pi_entry"] is None


def test_provenance_carries_the_entries_verbatim() -> None:
    omlx = _omlx_model()
    pi = _pi_model()
    record = provenance("{}", omlx, pi)
    assert record["omlx_entry"] == omlx
    assert record["pi_entry"] == pi


# --- CLI via main(argv) ------------------------------------------------------


def _write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _base_arm_data() -> dict:
    """A minimal, otherwise-valid arm -- loadable by `satyrn_evals.arms.load_arm`,
    which the CLI now uses. `model`/`server_model`/`inference` are what this
    script itself reads; `argv`/`tools`/`pins` are here only so `load_arm`
    accepts the file."""
    return {
        "arm": "baseline",
        "argv": ["satyrn-evals-attempt-pi"],
        "tools": ["read"],
        "model": "omlx/Ornith-1.5-9B-MLX-8bit",
        "server_model": "Ornith-1.5-9B-MLX-8bit",
        "pins": {"pi": "0.85.1", "engine_commit": None, "digests": {}},
        "inference": _ARM_INFERENCE,
    }


def _arm_file(tmp_path: Path, data: dict | None = None) -> Path:
    return _write(tmp_path / "arm.json", data if data is not None else _base_arm_data())


def test_cli_exit_0_when_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    record = json.loads(out)
    assert record["omlx_entry_sha256"] is not None
    assert record["pi_entry_sha256"] is not None


def test_cli_exit_1_on_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    arm = _arm_file(tmp_path)
    bad_settings = {"models": {"Ornith-1.5-9B-MLX-8bit": {}}}
    omlx_path = _write(tmp_path / "model_settings.json", bad_settings)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "preflight_settings FAILED" in err


def test_cli_exit_1_on_missing_entry(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", {"models": {}})
    pi_path = _write(tmp_path / "models.json", {"providers": {"omlx": {"models": []}}})

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "omlx:" in err
    assert "pi:" in err


def test_cli_exit_2_on_unreadable_arm(tmp_path: Path) -> None:
    missing_arm = tmp_path / "nope.json"
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(missing_arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 2


def test_cli_exit_2_on_unreadable_omlx_settings(tmp_path: Path) -> None:
    arm = _arm_file(tmp_path)
    bad_omlx = tmp_path / "model_settings.json"
    bad_omlx.write_text("not json", encoding="utf-8")
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(bad_omlx),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 2


def test_cli_writes_record_file(tmp_path: Path) -> None:
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)
    record_path = tmp_path / "record.json"

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
            "--record",
            str(record_path),
        ]
    )
    assert code == 0
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["omlx_entry_sha256"] is not None


# --- CLI: the arm is loaded through satyrn_evals.arms.load_arm -------------
# A malformed arm file used to traceback (exit 1 via an uncaught KeyError),
# which `preflight.sh` then reported as "settings are not verified" -- a
# false diagnosis of an authoring error. `load_arm` is the house reader
# (`preflight_models.py` uses it too); its `ArmError` is a `UsageError`,
# already exit-2-shaped.


def test_cli_exit_2_on_arm_missing_model_key(tmp_path: Path) -> None:
    data = _base_arm_data()
    del data["model"]
    arm = _arm_file(tmp_path, data)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 2


def test_cli_exit_2_on_arm_missing_model_key_sibling_success(tmp_path: Path) -> None:
    """The sibling of the refusal above: the same arm, with `model` present."""
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 0


def test_cli_exit_2_on_arm_model_not_addressing_server_model(tmp_path: Path) -> None:
    """`load_arm` refuses a `model` that does not end with `/{server_model}` --
    checked against a pi id and an oMLX id that would not otherwise
    correspond."""
    data = _base_arm_data()
    data["server_model"] = "some-other-id"
    arm = _arm_file(tmp_path, data)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 2


def test_cli_exit_2_on_arm_model_not_addressing_server_model_sibling_success(
    tmp_path: Path,
) -> None:
    """The sibling of the refusal above: `model` addresses `server_model`."""
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
        ]
    )
    assert code == 0


# --- CLI: a failing --record write is exit 2, not a traceback --------------


def test_cli_exit_2_on_record_write_failure(tmp_path: Path) -> None:
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)
    unwritable_record = tmp_path / "no-such-dir" / "record.json"

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
            "--record",
            str(unwritable_record),
        ]
    )
    assert code == 2


def test_cli_exit_2_on_record_write_failure_sibling_success(tmp_path: Path) -> None:
    """The sibling of the refusal above: the same call with a writable path."""
    arm = _arm_file(tmp_path)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    pi_path = _write(tmp_path / "models.json", _PI_MODELS)
    record_path = tmp_path / "record.json"

    code = main(
        [
            str(arm),
            "--omlx-settings",
            str(omlx_path),
            "--pi-models",
            str(pi_path),
            "--record",
            str(record_path),
        ]
    )
    assert code == 0
    assert record_path.is_file()


# --- drift guard: settings_verified_by names a script that still exists ----


@pytest.mark.parametrize(
    "arm_path", sorted(_ARMS_ROOT.glob("*.json")), ids=lambda p: p.name
)
def test_every_arm_names_a_settings_checker_that_exists(arm_path: Path) -> None:
    """A marker nothing reads can name a deleted script and nothing fails --
    the exact failure mode this branch exists to close, one level up."""
    arm = json.loads(arm_path.read_text(encoding="utf-8"))
    named = arm["settings_verified_by"]
    assert named == "scripts/preflight_settings.py"
    assert (_REPO_ROOT / named).is_file()


# --- 2b: the cell user's models.json -----------------------------------------

import subprocess  # noqa: E402

import preflight_settings as preflight_settings_module  # noqa: E402
from preflight_settings import CELL_PI_MODELS, read_cell_pi_models  # noqa: E402


def test_the_cell_models_are_read_as_the_cell_user() -> None:
    seen: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(_PI_MODELS), "")

    assert read_cell_pi_models(run) == _PI_MODELS
    assert seen == [["sudo", "-n", "-H", "-u", "satyrn-cell", "--", "/bin/cat", str(CELL_PI_MODELS)]]


def test_unreadable_cell_models_are_an_os_error() -> None:
    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, "", "sudo: a password is required")

    with pytest.raises(OSError, match="a password is required"):
        read_cell_pi_models(run)


def test_cli_cell_compares_against_the_cell_users_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(preflight_settings_module, "read_cell_pi_models", lambda: _PI_MODELS)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    assert main([str(_arm_file(tmp_path)), "--omlx-settings", str(omlx_path), "--cell"]) == 0
    assert json.loads(capsys.readouterr().out)["pi_models"] == f"satyrn-cell:{CELL_PI_MODELS}"


def test_cli_cell_exits_2_when_the_cell_models_cannot_be_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def unreadable() -> dict:
        raise OSError("cannot read as satyrn-cell")

    monkeypatch.setattr(preflight_settings_module, "read_cell_pi_models", unreadable)
    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
    assert main([str(_arm_file(tmp_path)), "--omlx-settings", str(omlx_path), "--cell"]) == 2
