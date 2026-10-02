"""The confinement extension's replay: the shipped `.ts`, driven by Node.

Integration tier only: it starts a Node process. The default tier stays
subprocess-free, and the extension's pure path logic is exercised through the
replay's fixtures, whose expected numbers are the assertions.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / "tools" / "replay_confinement.mjs"


def _node_typescript_argv(tmp_path: Path) -> list[str] | None:
    """The node invocation that can execute the shipped ``.ts``, or None.

    Node strips types by default from 22.18 (plain ``node``); older builds need
    ``--experimental-strip-types``; a build compiled without TypeScript support
    -- Ubuntu's ``node`` package, for one -- cannot run the replay at all. Probe
    with a real ``.ts`` file rather than assume, so a contributor's node skips
    instead of failing.
    """
    node = shutil.which("node")
    if node is None:
        return None
    probe = tmp_path / "probe.ts"
    probe.write_text("const x: number = 1;\n", encoding="utf-8")
    for argv in ([node, "--experimental-strip-types"], [node]):
        completed = subprocess.run([*argv, str(probe)], capture_output=True, check=False)
        if completed.returncode == 0:
            return argv
    return None


def test_the_confinement_extension_replays_every_fixture(tmp_path: Path) -> None:
    argv = _node_typescript_argv(tmp_path)
    if argv is None:
        pytest.skip("a Node with TypeScript support is required to replay the confinement extension")
    completed = subprocess.run(
        [*argv, str(REPLAY)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_the_replay_refuses_a_fixture_whose_expected_numbers_are_wrong(tmp_path: Path) -> None:
    """The sibling: a fixture that expects the wrong block count must fail the
    replay, or the check above would pass for any extension."""
    argv = _node_typescript_argv(tmp_path)
    if argv is None:
        pytest.skip("a Node with TypeScript support is required to replay the confinement extension")
    fixture = tmp_path / "wrong.json"
    fixture.write_text(
        '{"name": "wrong", "root": "work", "roots": ["corpus"],'
        ' "calls": [{"toolName": "read", "input": {"path": "solution.py"}}],'
        ' "expected": {"blocked": 1, "entries": 1, "firstBlock": 1}}',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [*argv, str(REPLAY), str(fixture)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "blocked" in completed.stderr
