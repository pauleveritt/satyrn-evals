"""Deterministic fake session adapter: scripted scenarios, no model.

Usage: fake_session_adapter.py SCENARIO [--marker PATH]
Scenarios: clean | scope | wrong-id | wrong-id-event | output-limit |
hang | die-after-one | die-mid-read | garbage | event-wrong-step |
wrong-step-terminal | chaos-close-line | close-fail
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


def emit(step_id: str, kind: str, conversation_id: str = CID) -> None:
    out(
        {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "conversation_id": conversation_id,
            "kind": kind,
            "payload": {"tool": "fake"},
        }
    )


def main() -> int:
    scenario = sys.argv[1]
    marker = None
    if "--marker" in sys.argv:
        marker = sys.argv[sys.argv.index("--marker") + 1]

    if scenario == "garbage-banner":
        print("{not json", flush=True)  # unparseable first line
    if scenario == "no-banner":
        return 0  # exit before session_started
    if scenario == "bad-banner":
        emit("add-a", "turn_end")  # first message is not session_started
    else:
        out({"version": 1, "type": "session_started", "conversation_id": CID})
    for line in sys.stdin:
        msg = json.loads(line)
        if msg.get("type") == "close":
            if scenario == "close-hang":
                time.sleep(60)  # never exits: close deadline fires
            if scenario == "close-extra":
                out({"version": 1, "type": "event", "step_id": "late",
                     "conversation_id": CID, "kind": "turn_end",
                     "payload": {}})
            if scenario == "close-garbage":
                print("{not json", flush=True)
            if scenario == "close-fail":
                sys.exit(3)  # nonzero exit on graceful close
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
        event_cid = CID
        terminal_cid = CID
        if step == "add-b":
            if scenario == "wrong-id-event":
                event_cid = "fake-conv-2"  # events drift; terminal stays true
            elif scenario == "wrong-id":
                terminal_cid = "fake-conv-2"  # events true; terminal drifts
        if scenario == "output-limit" and step == "add-b":
            out(
                {
                    "version": 1,
                    "type": "step_finished",
                    "step_id": step,
                    "conversation_id": terminal_cid,
                    "outcome": "output-limit",
                    "message": None,
                }
            )
            return 0
        if scenario == "die-mid-read" and step == "add-a":
            emit(step, "turn_end")
            sys.exit(0)  # events then EOF, no terminal for the step
        if scenario == "garbage" and step == "add-b":
            print("{not json", flush=True)
        if scenario == "event-wrong-step" and step == "add-b":
            emit("nope", "turn_end")
        if scenario == "wrong-step-terminal" and step == "add-b":
            emit(step, "turn_end", CID)
            out({"version": 1, "type": "step_finished", "step_id": "nope",
                 "conversation_id": CID, "outcome": "settled", "message": None})
            time.sleep(60)  # the executor must stop before this matters
        if scenario == "garbage-bytes" and step == "add-b":
            sys.stdout.buffer.write(b"\xff\xfe not json\n")
            sys.stdout.buffer.flush()
        if scenario == "context-reset" and step == "add-b":
            emit(step, "context_reset")  # design:230: a protocol failure
        if scenario == "chatty" and step == "add-a":
            # events keep arriving faster than the deadline: a per-line
            # timeout would never fire; the per-prompt budget must.
            while True:
                emit(step, "turn_end")
                time.sleep(0.005)  # under the executor's read floor, so
                # reads keep returning and the deadline pre-check fires
        if scenario == "edit-public-test" and step == "add-a":
            # a self-verifying model that edits the protected public test
            path = Path("test_solution.py")
            path.write_text(path.read_text() + "# edited by the model\n")
        if scenario == "chaos-close-line" and step == "add-b":
            out({"version": 1, "type": "close"})  # an adapter must not send this
        emit(step, "turn_end", event_cid)
        emit(step, "tool_end", event_cid)
        out(
            {
                "version": 1,
                "type": "step_finished",
                "step_id": step,
                "conversation_id": terminal_cid,
                "outcome": "settled",
                "message": None,
            }
        )
        if scenario == "die-after-one" and step == "add-a":
            sys.exit(0)  # settled, then gone before the next prompt
        if scenario == "hang" and step == "add-a":
            time.sleep(60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
