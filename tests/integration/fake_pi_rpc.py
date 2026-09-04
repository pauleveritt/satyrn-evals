"""Deterministic stand-in for Pi speaking rpc.md's wire protocol.

Ignores the rpc flags it receives; on each prompt command emits a mapped
event stream (turn_end, tool_execution_end, compaction on prompts 2 and
3) and agent_settled, and appends the script's text for that prompt
number to PI_FAKE_FILE relative to its cwd, so checkpoints have content.

Scripted modes (environment variables):
- PI_FAKE_SCRIPT: JSON mapping "1".."N" to text ("" = edit nothing).
- PI_FAKE_TERMINAL: a stopReason declared via agent_end on prompt 2.
- PI_FAKE_RESPONSE_FAIL: every prompt gets a failed command response.
- PI_FAKE_RETRY_FAIL: auto_retry_end{success:false} before prompt 2's settle.
- PI_FAKE_DIE: exit before settling prompt 2 (pi EOF mid-prompt).
- PI_FAKE_MALFORMED: one non-JSON line per prompt.
- PI_FAKE_UNSOLICITED: one event before any prompt.
- PI_FAKE_OUTSIDE: write outside.txt (outside source_paths) on prompt 2.
"""

import json
import os
import sys
from pathlib import Path


def out(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    # session-runtime-policy check: the adapter's pi child must inherit
    # PYTHONDONTWRITEBYTECODE (the fake IS the pi child in these tests)
    marker = os.environ.get("PI_FAKE_ENV_MARKER")
    if marker and os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        Path(marker).write_text("missing")
    script = json.loads(Path(os.environ["PI_FAKE_SCRIPT"]).read_text())
    target = os.environ["PI_FAKE_FILE"]
    prompted = 0
    if os.environ.get("PI_FAKE_UNSOLICITED"):
        out({"type": "queue_update"})
    for raw in sys.stdin:
        message = json.loads(raw)
        if message.get("type") != "prompt":
            continue
        if os.environ.get("PI_FAKE_RESPONSE_FAIL"):
            out({"type": "response", "command": "prompt", "success": False,
                 "error": "declined", "id": message.get("id")})
            continue
        if os.environ.get("PI_FAKE_MALFORMED"):
            sys.stdout.write("not json at all\n")
            sys.stdout.flush()
        prompted += 1
        if os.environ.get("PI_FAKE_PYTEST"):
            import subprocess

            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q"],
                cwd=Path.cwd(), capture_output=True,
            )
            if os.environ.get("PI_FAKE_PYTEST_RAN"):
                Path(os.environ["PI_FAKE_PYTEST_RAN"]).write_text(
                    f"rc={result.returncode}"
                )
        if os.environ.get("PI_FAKE_RETRY_FAIL") and prompted == 2:
            out({"type": "auto_retry_end", "success": False, "finalError": "boom"})
        if os.environ.get("PI_FAKE_DIE") and prompted == 2:
            sys.exit(0)  # gone before settling: pi EOF mid-prompt
        if os.environ.get("PI_FAKE_OUTSIDE") and prompted == 2:
            Path.cwd().joinpath("outside.txt").write_text("forbidden\n")
        text = script.get(str(prompted), "")
        if text:
            path = Path.cwd() / target
            path.write_text(path.read_text() + text)
        out({"type": "turn_end"})
        terminal = os.environ.get("PI_FAKE_TERMINAL")
        if terminal and prompted == 2:
            out({"type": "agent_end", "messages": [{"stopReason": terminal}]})
        out({"type": "tool_execution_end", "toolCallId": f"t{prompted}"})
        if prompted in (2, 3):
            out({"type": "compaction_start"})
            out({"type": "compaction_end"})
        out({"type": "response", "command": "prompt", "success": True,
             "id": message.get("id")})
        out({"type": "agent_settled"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
