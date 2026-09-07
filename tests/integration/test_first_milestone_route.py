"""The narrow synthetic route uses retained evidence across both boundaries."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import run_first_milestone as route  # noqa: E402, I001  # type: ignore[missing-import]

pytestmark = pytest.mark.integration

PUBLIC_IDS = [
    "tests/test_app.py::test_complaints_returns_200_and_seed_complaint",
    "tests/test_app.py::test_home_returns_200_and_tagline",
    "tests/test_app.py::test_post_complaint_redirects_to_complaints",
    "tests/test_app.py::test_posted_complaint_appears_on_the_board",
]


def test_fixture_route_completes_two_predeclared_cells_and_regrades(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fixture-route"

    route.execute(output)

    schedule = json.loads((output / "schedule.json").read_text())
    state = json.loads((output / "state.json").read_text())
    result = json.loads((output / "result.json").read_text())
    assert len(schedule["cells"]) == 2
    assert schedule["model"] == "fixture/agentclinic-executor-v1"
    assert schedule["configuration_digest"]
    assert schedule["limits"] == {
        "command_timeout_seconds": 30,
        "attempt_timeout_seconds": None,
    }
    assert state["status"] == "complete"
    assert result["cells"] == 2
    assert result["per_arm"]["fixture"]["verdict_counts"]["pass"] == 2

    receipts = [
        output
        / cell["dir"]
        / json.loads((output / cell["dir"] / "summary.json").read_text())["cells"][0]
        / "receipt.json"
        for cell in schedule["cells"]
    ]
    before = [receipt.read_bytes() for receipt in receipts]
    route.regrade(output)
    assert [receipt.read_bytes() for receipt in receipts] == before
    for cell in schedule["cells"]:
        attempt = json.loads((output / cell["dir"] / "summary.json").read_text())[
            "cells"
        ][0]
        transcript = json.loads(
            (output / cell["dir"] / attempt / "transcript.txt").read_text()
        )
        assert transcript["message"]["model"] == schedule["model"]
        assert transcript["public_suite_exit"] == 0
        assert transcript["public_hook"]["executed_test_ids"] == PUBLIC_IDS
        assert transcript["public_hook"]["collect_errors"] == []
        assert transcript["public_hook"]["outcomes"] == {
            test_id: "passed" for test_id in PUBLIC_IDS
        }


def test_resume_skips_a_completed_first_cell_after_between_cell_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "fixture-route"
    original_write = route._write_state

    def interrupt_after_first_completion(path: Path, *, status, events) -> None:
        if events[-1:] == [{"event": "completed", "cell": "cell-000-fixture"}]:
            raise KeyboardInterrupt("between cells")
        original_write(path, status=status, events=events)

    monkeypatch.setattr(route, "_write_state", interrupt_after_first_completion)
    with pytest.raises(KeyboardInterrupt, match="between cells"):
        route.execute(output)
    monkeypatch.setattr(route, "_write_state", original_write)

    first_summary = output / "cell-000-fixture" / "summary.json"
    assert first_summary.exists()
    route.execute(output, resume=True)

    state = json.loads((output / "state.json").read_text())
    assert {"event": "skipped-complete", "cell": "cell-000-fixture"} in state["events"]
    assert (output / "cell-001-fixture" / "summary.json").exists()


def test_mid_cell_interrupt_preserves_paths_and_blocks_automatic_resume(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fixture-route"
    env = dict(os.environ)
    env["SATYRN_FIXTURE_PAUSE"] = "30"
    process = subprocess.Popen(
        [
            sys.executable,
            str(route.ROOT / "scripts/run_first_milestone.py"),
            "--output",
            str(output),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 20
        while not list((output / "cell-000-fixture").glob("*/patch.diff")):
            assert time.monotonic() < deadline, (
                "fixture never preserved an in-flight patch"
            )
            time.sleep(0.1)
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=20)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=20)

    state = json.loads((output / "state.json").read_text())
    assert state["status"] == "recovery-needed"
    retained = next((output / "cell-000-fixture").glob("*/patch.diff")).parent
    assert (retained / "patch.diff").exists()
    assert (retained / "transcript.txt").exists()
    with pytest.raises(route.RouteError, match="needs review"):
        route.execute(output, resume=True)
