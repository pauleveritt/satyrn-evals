"""The Baseline adapter as a real process, against real Git.

Integration tier: this spawns processes and runs Git. No model and no
network — pi is replaced by a fixture, which is the V4 substitution
pattern, so nothing here is a model-behaviour claim.

Two rows, both directions of the same seam:

* **success** — a fixture pi that edits a tracked file: the adapter
  delivers a non-empty patch and a transcript whose every line parses as
  JSON. The JSON purity is the point: the adapter sends pi's stderr to
  DEVNULL precisely so one diagnostic line cannot make V10 report the
  whole cell ``measured: false`` (`pathology.py:88-89`).
* **failure** — the bundled `fake_pi_v4.py` fixture in its ``fail`` mode:
  pi exits 17 having written no edit, and the adapter still preserves the
  transcript and writes an (empty) patch before returning that exit.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from satyrn_evals import attempt_pi

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "src" / "satyrn_evals" / "attempt_pi.py"
FAKE_PI_V4 = Path(__file__).resolve().parent / "fake_pi_v4.py"

_EDITING_PI = """\
import json, pathlib, sys
print(json.dumps({"type": "agent_start", "argv": sys.argv[1:]}), flush=True)
sys.stderr.write("a pi diagnostic that must not reach the transcript\\n")
path = pathlib.Path("solution.py")
path.write_text(path.read_text().replace("return n", "return n * 2"))
print(json.dumps({"type": "agent_settled"}), flush=True)
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A one-file repository with a committed HEAD to diff against."""
    work = tmp_path / "work"
    work.mkdir()
    (work / "solution.py").write_text("def double(n):\n    return n\n")
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "Test")
    _git(work, "add", "-A")
    _git(work, "commit", "-qm", "base")
    return work


def _shim(tmp_path: Path, body: Path | str) -> Path:
    """A `pi` executable on disk, as the session adapter's tests build one."""
    target = tmp_path / "fake_pi.py"
    if isinstance(body, Path):
        target = body
    else:
        target.write_text(body)
    shim = tmp_path / "pi"
    shim.write_text(f'#!/bin/sh\nexec {sys.executable} {target} "$@"\n')
    shim.chmod(0o755)
    return shim


def _run(
    repo: Path, tmp_path: Path, shim: Path, **extra: str
) -> tuple[int, Path, Path]:
    patch_path = tmp_path / "patch.diff"
    transcript_path = tmp_path / "transcript.txt"
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    completed = subprocess.run(
        [
            sys.executable,
            str(ADAPTER),
            "--model",
            "omlx/gemma-4-12B-it-MLX-8bit",
            "--pi-bin",
            str(shim),
        ],
        cwd=repo,
        capture_output=True,
        env={
            **os.environ,
            attempt_pi.CONTRACT_ENV: "Make double return twice its input.",
            attempt_pi.PATCH_ENV: str(patch_path),
            attempt_pi.TRANSCRIPT_ENV: str(transcript_path),
            attempt_pi.BASE_SHA_ENV: base,
            **extra,
        },
    )
    return completed.returncode, patch_path, transcript_path


def test_adapter_delivers_a_patch_and_a_json_only_transcript(
    repo: Path, tmp_path: Path
) -> None:
    code, patch_path, transcript_path = _run(
        repo, tmp_path, _shim(tmp_path, _EDITING_PI)
    )
    assert code == 0
    patch = patch_path.read_text()
    assert "diff --git a/solution.py b/solution.py" in patch
    assert "+    return n * 2" in patch
    lines = transcript_path.read_text().splitlines()
    assert [json.loads(line)["type"] for line in lines] == [
        "agent_start",
        "agent_settled",
    ]
    # the prompt reached pi as the contract text, never as a --rung
    assert "Make double return twice its input." in json.loads(lines[0])["argv"]
    assert "--rung" not in json.loads(lines[0])["argv"]


def test_adapter_preserves_the_transcript_when_pi_fails(
    repo: Path, tmp_path: Path
) -> None:
    """Fixture: tests/integration/fake_pi_v4.py in its `fail` mode. The
    sibling success is the row above."""
    code, patch_path, transcript_path = _run(
        repo,
        tmp_path,
        _shim(tmp_path, FAKE_PI_V4),
        SATYRN_FAKE_PI_MODE="fail",
    )
    assert code == 17
    assert patch_path.read_text() == ""  # no edit was made, and none is invented
    kinds = [
        json.loads(line)["type"] for line in transcript_path.read_text().splitlines()
    ]
    assert kinds == ["agent_start", "session_shutdown"]
