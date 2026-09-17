"""The qualification's fake ``pi``: apply the task's known-good patch, commit part of it.

No model. It runs in the attempt worktree, applies ``SATYRN_QUALIFY_PATCH``
with ``git apply``, then commits some of the touched files and leaves the
rest uncommitted -- the shapes that scored ``NO_PATCH`` under
``git diff HEAD`` (spec, "What the evidence settled"). With two or more
files it commits the first half, sorted; with one file it commits it when
BASE already had it and leaves it untracked when it is new. It writes a
Pi-shaped ``--mode json`` stream so the harness's tail has something to read.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from satyrn_evals.patch import parse_patch_paths

PATCH_ENV = "SATYRN_QUALIFY_PATCH"


def committed_paths(paths: list[str], existing: set[str]) -> list[str]:
    """Which touched paths the fake commits; the rest stay uncommitted."""
    ordered = sorted(paths)
    if len(ordered) >= 2:
        return ordered[: len(ordered) // 2]
    return [path for path in ordered if path in existing]


def _emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def main() -> int:
    patch_text = Path(os.environ[PATCH_ENV]).read_text(encoding="utf-8")
    paths = list(parse_patch_paths(patch_text))
    existing = {path for path in paths if Path(path).exists()}
    _emit({"type": "session", "version": 3, "cwd": os.getcwd()})
    _emit({"type": "agent_start"})
    _emit({"type": "turn_start"})
    subprocess.run(["git", "apply", "-"], input=patch_text.encode("utf-8"), check=True, capture_output=True)
    if commit := committed_paths(paths, existing):
        subprocess.run(["git", "add", "--", *commit], check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=qualify", "-c", "user.email=qualify@example.invalid", "commit", "-qm", "qualify"],
            check=True, capture_output=True,
        )
    _emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": 10}}})
    _emit({"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}})
    _emit({"type": "agent_end"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
