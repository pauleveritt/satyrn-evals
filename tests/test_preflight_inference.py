"""Preflight refuses a batch whose inference settings drifted under it.

The refusal is the point, so each one has its sibling success per
`BRIEF.md` rule 6. F6 -- pi declaring a 262,144 context window against a
server enforcing 80,000 -- was recorded before the V11c spike and cost 70
of its 102 minutes; what was missing was any machine check that the
settings a batch depends on are the settings that are live.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight_inference import (  # noqa: E402, I001
    drifted,
    live_settings,
)

_LIVE = {
    "context_window": 262144,
    "max_tokens": 8192,
    "compaction_enabled": True,
    "compaction_reserve_tokens": 16384,
    "temperature": None,
}


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A pi config directory shaped like the real one, models nested."""
    d = tmp_path / "pi"
    d.mkdir()
    (d / "models.json").write_text(json.dumps({
        "providers": {
            "omlx": {"models": [
                {"id": "other-model", "contextWindow": 32000, "maxTokens": 32000},
                {"id": "gemma-4-12B-it-MLX-8bit",
                 "contextWindow": 262144, "maxTokens": 8192},
            ]}
        }
    }), encoding="utf-8")
    (d / "settings.json").write_text(json.dumps({
        "compaction": {"enabled": True, "reserveTokens": 16384}
    }), encoding="utf-8")
    return d


def _arm(tmp_path: Path, name: str, **overrides: object) -> Path:
    inference = dict(_LIVE) | overrides
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps({
        "arm": name,
        "server_model": "gemma-4-12B-it-MLX-8bit",
        "inference": inference,
    }), encoding="utf-8")
    return p


def test_an_arm_matching_pis_config_does_not_drift(
    tmp_path: Path, config_dir: Path
) -> None:
    """The success sibling: recorded settings equal to pi's pass silently."""
    assert drifted([_arm(tmp_path, "baseline")], config_dir=config_dir) == []


def test_a_changed_context_window_is_refused(
    tmp_path: Path, config_dir: Path
) -> None:
    """F6's own shape: the setting a batch depends on moved under it."""
    arm = _arm(tmp_path, "baseline", context_window=80000)
    assert drifted([arm], config_dir=config_dir) == [
        ("baseline", "context_window", 80000, 262144)
    ]


def test_a_changed_compaction_reserve_is_refused(
    tmp_path: Path, config_dir: Path
) -> None:
    """Compaction decides when a long cell is cut short, so it is pinned
    like the window: a silent change alters what is measured."""
    arm = _arm(tmp_path, "baseline", compaction_reserve_tokens=4096)
    assert drifted([arm], config_dir=config_dir) == [
        ("baseline", "compaction_reserve_tokens", 4096, 16384)
    ]


def test_an_arm_recording_no_inference_block_is_refused(
    tmp_path: Path, config_dir: Path
) -> None:
    """An unrecorded setting is the condition this check exists to
    prevent, so it refuses rather than passing on an empty comparison --
    the "a preflight that could not fail" defect."""
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps({
        "arm": "legacy", "server_model": "gemma-4-12B-it-MLX-8bit"
    }), encoding="utf-8")
    assert drifted([p], config_dir=config_dir) == [
        ("legacy", "inference", "recorded", "absent")
    ]


def test_every_drifted_setting_is_reported_not_just_the_first(
    tmp_path: Path, config_dir: Path
) -> None:
    """A preflight that stops at the first disagreement makes the operator
    re-run it once per setting."""
    arm = _arm(tmp_path, "baseline", context_window=1, max_tokens=2)
    assert len(drifted([arm], config_dir=config_dir)) == 2


def test_a_model_pi_does_not_list_is_an_error(
    tmp_path: Path, config_dir: Path
) -> None:
    """Silently comparing against nothing is how a check that cannot fail
    is born; an unknown model raises instead."""
    p = tmp_path / "ghost.json"
    p.write_text(json.dumps({
        "arm": "ghost", "server_model": "no-such-model", "inference": dict(_LIVE)
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="does not declare"):
        drifted([p], config_dir=config_dir)


def test_live_settings_finds_a_model_however_pi_nests_it(
    config_dir: Path
) -> None:
    """The search is by id, so pi reorganizing its providers does not
    silently stop finding the model."""
    assert live_settings(config_dir, "gemma-4-12B-it-MLX-8bit") == _LIVE
