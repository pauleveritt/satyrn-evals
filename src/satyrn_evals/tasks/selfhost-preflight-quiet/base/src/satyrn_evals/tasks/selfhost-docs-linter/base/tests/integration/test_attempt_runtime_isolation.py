"""The attempt runtime boundary, with a real workspace and adapter process."""

import json
import os
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode

pytestmark = pytest.mark.integration


_PI = """\
import json
import os
import pathlib
import subprocess

print(json.dumps({
    "type": "agent_start",
    "virtual_env": os.environ.get("VIRTUAL_ENV"),
    "uv_environment": os.environ["UV_PROJECT_ENVIRONMENT"],
}), flush=True)
subprocess.run(["uv", "run", "python", "-c", "import pathlib"], check=True)
path = pathlib.Path("solution.py")
path.write_text(path.read_text().replace("return n", "return n * 2"))
print(json.dumps({
    "type": "agent_settled",
    "uv_environment_exists": pathlib.Path(os.environ["UV_PROJECT_ENVIRONMENT"]).is_dir(),
    "workspace_residue": (
        pathlib.Path(".venv").exists()
        or any(pathlib.Path(".").rglob("*.pyc"))
    ),
}), flush=True)
"""


def _task(tasks_root: Path) -> None:
    base = tasks_root / "t" / "base"
    base.mkdir(parents=True)
    (base / "pyproject.toml").write_text(
        "[project]\nname = 'isolated-task'\nversion = '0.0.0'\n"
    )
    (base / "solution.py").write_text("def double(n):\n    return n\n")
    (tasks_root / "t" / "fixtures").mkdir()
    (tasks_root / "t" / "fixtures" / "known-good.patch").write_text(
        "diff --git a/solution.py b/solution.py\n"
        "--- a/solution.py\n+++ b/solution.py\n"
        "@@ -1,2 +1,2 @@\n def double(n):\n-    return n\n+    return n * 2\n"
    )
    (tasks_root / "t" / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t",
                "contract": "Fix double.",
                "oracle": ["python", "-c", "import solution; assert solution.double(2) == 4"],
                "expected_test_ids": ["test_solution.py::test_double"],
                "source_paths": ["solution.py"],
                "fixtures": {"known_good": "fixtures/known-good.patch"},
            }
        )
    )


def test_attempt_isolates_uv_and_evals_venv_without_losing_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    script = tmp_path / "pi.py"
    script.write_text(_PI)
    pi = tmp_path / "pi"
    pi.write_text(f"#!/bin/sh\nexec {sys.executable} {script} \"$@\"\n")
    pi.chmod(0o755)

    # The adapter process receives this evaluator venv; its Pi child must not.
    evaluator_venv = tmp_path / "evals-venv"
    (evaluator_venv / "bin").mkdir(parents=True)
    monkeypatch.setenv("VIRTUAL_ENV", str(evaluator_venv))
    monkeypatch.setenv("PATH", f"{evaluator_venv / 'bin'}:{os.environ['PATH']}")
    record = attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=[
            sys.executable,
            "-m",
            "satyrn_evals.attempt_pi",
            "--model",
            "fixture",
            "--pi-bin",
            str(pi),
        ],
    )

    assert record.code is AttemptCode.OK
    cell = tmp_path / "attempts" / str(record.attempt_dir)
    assert "return n * 2" in (cell / "patch.diff").read_text()
    events = [json.loads(line) for line in (cell / "transcript.txt").read_text().splitlines()]
    assert events[0]["virtual_env"] is None
    assert Path(events[0]["uv_environment"]).name.startswith("satyrn-evals-uv-")
    assert events[1] == {
        "type": "agent_settled",
        "uv_environment_exists": True,
        "workspace_residue": False,
    }
