"""The preflight process guard distinguishes batch work from IDE Pi."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from preflight_processes import measurement_processes  # noqa: E402, I001


MODEL = "omlx/gemma-4-12B-it-MLX-8bit"


def test_ide_pi_session_is_not_a_measurement_process() -> None:
    snapshot = f"101 1 /Applications/IDE/pi --mode rpc --model {MODEL}\n"
    assert measurement_processes(snapshot, MODEL) == []


def test_print_json_pi_with_pinned_model_is_refused() -> None:
    snapshot = f"101 1 /usr/local/bin/pi --print --mode json --model {MODEL}\n"
    assert len(measurement_processes(snapshot, MODEL)) == 1


def test_engine_attempt_and_its_pi_descendant_are_refused() -> None:
    snapshot = "\n".join(
        [
            "200 1 /usr/local/bin/satyrn-engine attempt --model " + MODEL,
            "201 200 /usr/local/bin/pi --mode rpc --model " + MODEL,
        ]
    )
    found = measurement_processes(snapshot, MODEL)
    assert len(found) == 2
    assert all("pid=" + pid in " ".join(found) for pid in ("200", "201"))


def test_unrelated_pi_and_engine_like_processes_are_ignored() -> None:
    snapshot = "\n".join(
        [
            "301 1 /Applications/IDE/pi --print --mode json --model another",
            "302 1 /usr/local/bin/other-engine --attempt --model " + MODEL,
        ]
    )
    assert measurement_processes(snapshot, MODEL) == []
