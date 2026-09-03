"""Deterministic fake session adapter: scripted scenarios, no model.

Usage: fake_session_adapter.py SCENARIO [--marker PATH]
Scenarios: clean | scope | wrong-id | output-limit | hang
The adapter edits the worktree like a competent executor would: feature
steps append the matching feature to solution.py, review edits nothing.
"""

import json
import sys
import time
from pathlib import Path

CID = "fake-conv"
FEATURES = {
    "add-a": 'def feature_a() -> str:\n    return "a"\n',
    "add-b": 'def feature_b() -> str:\n    return "b"\n',
}


def out(obj: dict) -> None:
    print(json.dumps(obj), flush=True)


def emit(step_id: str, kind: str) -> None:
    out(
        {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "kind": kind,
            "payload": {"tool": "fake"},
        }
    )


def main() -> int:
    scenario = sys.argv[1]
    marker = None
    if "--marker" in sys.argv:
        marker = sys.argv[sys.argv.index("--marker") + 1]

    out({"version": 1, "type": "session_started", "conversation_id": CID})
    for line in sys.stdin:
        msg = json.loads(line)
        if msg.get("type") == "close":
            break  # graceful close: stop stdout, exit zero
        if msg.get("type") != "prompt":
            continue
        step = msg["step_id"]
        if marker is not None and step == "review":
            Path(marker).write_text("prompted")
        if step in FEATURES and scenario in ("clean", "scope", "output-limit"):
            path = Path("solution.py")
            path.write_text(path.read_text() + FEATURES[step])
        if scenario == "scope" and step == "add-b":
            Path("outside.txt").write_text("forbidden\n")
        emit(step, "turn_end")
        emit(step, "tool_end")
        use_cid = CID
        if scenario == "wrong-id" and step != "add-a":
            use_cid = "fake-conv-2"
        outcome = "settled"
        if scenario == "output-limit" and step == "add-b":
            outcome = "output-limit"
        out(
            {
                "version": 1,
                "type": "step_finished",
                "step_id": step,
                "conversation_id": use_cid,
                "outcome": outcome,
                "message": None,
            }
        )
        if outcome != "settled":
            return 0
        if scenario == "hang" and step == "add-a":
            time.sleep(60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
