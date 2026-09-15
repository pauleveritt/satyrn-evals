"""Preflight refuses a batch whose arms do not all name the same model.

With two arms, a first-vs-last comparison happens to check everything.
With three, it silently skips the middle arm -- exactly the "pass on an
arm nobody checked" defect `scripts/preflight.sh` already warns about for
its own PATH check. Each refusal below has its sibling success, per
`BRIEF.md` rule 6.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight_models import disagreeing, load_arms  # noqa: E402, I001

_PINS = {"pi": "0.84.4", "engine_commit": None, "digests": {}}


def _arm(
    tmp_path: Path,
    name: str,
    *,
    model: str = "omlx/gemma-4-12B-it-MLX-8bit",
    server_model: str | None = None,
) -> Path:
    """A minimal, otherwise-valid arm file named ``name``.

    ``name`` doubles as the arm's own ``arm`` field (a name the loader
    recognizes) and as the file's stem, so a test can tell which
    position -- first, middle, or last -- a reported mismatch came from.
    ``server_model`` defaults to the suffix ``model`` addresses, which is
    what `load_arm` itself requires.
    """
    if server_model is None:
        server_model = model.removeprefix("omlx/")
    path = tmp_path / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "arm": name,
                "argv": ["satyrn-evals-attempt-pi"],
                "tools": ["read"],
                "model": model,
                "server_model": server_model,
                "pins": dict(_PINS),
            }
        ),
        encoding="utf-8",
    )
    return path


def test_a_middle_arm_naming_a_different_model_is_caught(tmp_path: Path) -> None:
    """The point of the change: a first-vs-last comparison would miss
    this, because the first and last arms here agree with each other."""
    first = _arm(tmp_path, "baseline")
    middle = _arm(tmp_path, "envelope", model="omlx/other-model")
    last = _arm(tmp_path, "baseline-compaction")
    mismatches = disagreeing(load_arms([first, middle, last]))
    assert [name for name, _, _ in mismatches] == ["envelope"]
    assert mismatches[0][1] == "omlx/other-model"


def test_agreeing_server_model_but_disagreeing_model_is_caught(
    tmp_path: Path,
) -> None:
    first = _arm(tmp_path, "baseline")
    middle = _arm(tmp_path, "envelope", model="omlx/other-model")
    mismatches = disagreeing(load_arms([first, middle]))
    assert mismatches == [("envelope", "omlx/other-model", "other-model")]


def test_agreeing_model_but_disagreeing_server_model_is_caught(
    tmp_path: Path,
) -> None:
    """A model string with more than one path segment can validly address
    two different `server_model` suffixes (`load_arm` only requires that
    `model` end with `/{server_model}`), so this scenario is reachable
    even though it can't happen with `arms/baseline.json`'s single-slash
    model string."""
    shared_model = "omlx/sub/gemma-4-12B-it-MLX-8bit"
    first = _arm(tmp_path, "baseline", model=shared_model, server_model="sub/gemma-4-12B-it-MLX-8bit")
    middle = _arm(tmp_path, "envelope", model=shared_model, server_model="gemma-4-12B-it-MLX-8bit")
    last = _arm(tmp_path, "baseline-compaction", model=shared_model, server_model="sub/gemma-4-12B-it-MLX-8bit")
    mismatches = disagreeing(load_arms([first, middle, last]))
    assert [(name, server_model) for name, _, server_model in mismatches] == [
        ("envelope", "gemma-4-12B-it-MLX-8bit")
    ]


def test_three_agreeing_arms_are_accepted(tmp_path: Path) -> None:
    arms = [
        _arm(tmp_path, "baseline"),
        _arm(tmp_path, "envelope"),
        _arm(tmp_path, "baseline-compaction"),
    ]
    assert disagreeing(load_arms(arms)) == []


def test_a_single_arm_is_accepted_on_its_own(tmp_path: Path) -> None:
    assert disagreeing(load_arms([_arm(tmp_path, "baseline")])) == []
