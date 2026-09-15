#!/usr/bin/env python3
"""Deterministic Pi fixture that drives the real E4 mutator once."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    mode = os.environ.get("SATYRN_FAKE_PI_MODE", "replace")
    print(
        json.dumps(
            {"type": "agent_start", "argv": sys.argv[1:], "cwd": os.getcwd()}
        ),
        flush=True,
    )
    if mode == "fail":
        print(
            json.dumps({"type": "session_shutdown", "reason": "fixture failure"}),
            flush=True,
        )
        return 17

    context_text = os.environ["SATYRN_MUTATION_CONTEXT"]
    context = json.loads(context_text)
    if set(context["revisions"]) != {"solution.py"}:
        print(json.dumps({"type": "fixture_error", "context": context}), flush=True)
        return 19
    replacement = {
        "path": "solution.py",
        "edits": [
            {
                "oldText": "    return str(n)",
                "newText": (
                    '    sign = "-" if n < 0 else ""\n'
                    '    return sign + format(abs(n), ",")'
                ),
            }
        ],
    }
    engine_repo = Path(os.environ["SATYRN_ENGINE_REPO"])
    with tempfile.TemporaryDirectory(prefix="satyrn-v4-fake-pi-") as temporary:
        root = Path(temporary)
        context_path = root / "context.json"
        input_path = root / "input.json"
        context_path.write_text(context_text, encoding="utf-8")
        input_path.write_text(json.dumps(replacement), encoding="utf-8")
        completed = subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                os.fspath(engine_repo / "tools" / "exercise_mutator.mjs"),
                os.fspath(context_path),
                os.fspath(input_path),
            ],
            cwd=engine_repo,
            capture_output=True,
            text=True,
            check=False,
        )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    print(json.dumps({"type": "session_shutdown", "reason": mode}), flush=True)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
