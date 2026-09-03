"""Deterministic stand-in for Pi speaking rpc.md's wire protocol.

Ignores the rpc flags it receives; on each prompt command emits a mapped
event stream (turn_end, tool_execution_end, compaction on prompts 2 and
3) and agent_settled, and appends the script's text for that prompt
number to PI_FAKE_FILE relative to its cwd, so checkpoints have content.
PI_FAKE_SCRIPT: JSON mapping "1".."N" to text ("" = edit nothing).
"""

import json
import os
import sys
from pathlib import Path


def out(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    script = json.loads(Path(os.environ["PI_FAKE_SCRIPT"]).read_text())
    target = os.environ["PI_FAKE_FILE"]
    prompted = 0
    for raw in sys.stdin:
        message = json.loads(raw)
        if message.get("type") != "prompt":
            continue
        prompted += 1
        if os.environ.get("PI_FAKE_OUTSIDE") and prompted == 2:
            Path.cwd().joinpath("outside.txt").write_text("forbidden\n")
        text = script.get(str(prompted), "")
        if text:
            path = Path.cwd() / target
            path.write_text(path.read_text() + text)
        out({"type": "turn_end"})
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
