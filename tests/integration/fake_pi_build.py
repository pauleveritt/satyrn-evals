#!/usr/bin/env python3
"""Fake `pi` for build-shaped fixture attempts: no model, no network.

``SATYRN_FAKE_PI_MODE`` selects what the fake does in its working directory
(the attempt worktree), while writing a Pi-shaped ``--mode json`` stream to
stdout:

- ``commit`` (default): write calc-build's three GOOD files, commit two of
  them inside the worktree and leave ``calc/format.py`` untracked -- the
  shape that scored ``NO_PATCH`` under ``git diff HEAD``.
- ``write``: write the same files and commit nothing (the Engine arm's
  ``deliver`` commits its own candidate).
- ``idle``: change nothing.
- ``spend``: change nothing, report 20,000 output tokens on each of two
  turns, record its pid in ``SATYRN_FAKE_PI_PIDFILE``, then sleep so only a
  tripwire can end it.
- ``trickle``: change nothing, report 20,000 output tokens on a single
  turn -- under the engine's own default budget (32,000, `derive.py`) so
  only a tighter harness budget can trip it, never `deliver`'s live
  enforcement or the engine's own `attempt` -- record its pid in
  ``SATYRN_FAKE_PI_PIDFILE``, then sleep so only a tripwire can end it.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

GOOD = {
    "calc/core.py": "from calc.helpers import add_all\n\n\ndef total(xs):\n    return add_all(xs)\n",
    "calc/helpers.py": "def add_all(xs):\n    return sum(xs)\n",
    "calc/format.py": 'def render(n):\n    return f"{n:,}"\n',
}


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def turn(output_tokens: int) -> None:
    emit({"type": "turn_start"})
    emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": output_tokens}}})
    emit({"type": "turn_end", "message": {"role": "assistant", "content": []}})


def main() -> int:
    mode = os.environ.get("SATYRN_FAKE_PI_MODE", "commit")
    emit({"type": "session", "version": 3, "cwd": os.getcwd()})
    emit({"type": "agent_start"})
    if mode == "spend":
        if pidfile := os.environ.get("SATYRN_FAKE_PI_PIDFILE"):
            Path(pidfile).write_text(str(os.getpid()))
        turn(20_000)
        turn(20_000)
        time.sleep(120)
        return 0
    if mode == "trickle":
        if pidfile := os.environ.get("SATYRN_FAKE_PI_PIDFILE"):
            Path(pidfile).write_text(str(os.getpid()))
        turn(20_000)
        time.sleep(120)
        return 0
    if mode in ("commit", "write"):
        emit({"type": "turn_start"})
        for index, (path, text) in enumerate(GOOD.items()):
            emit({"type": "tool_execution_start", "toolCallId": f"w{index}", "toolName": "write", "args": {"path": path, "content": text}})
            Path(path).write_text(text)
            emit({"type": "tool_execution_end", "toolCallId": f"w{index}", "toolName": "write", "result": {"content": [{"type": "text", "text": "ok"}]}})
        if mode == "commit":
            command = "git add calc/core.py calc/helpers.py && git commit -qm model"
            emit({"type": "tool_execution_start", "toolCallId": "b0", "toolName": "bash", "args": {"command": command}})
            for argv in (["git", "add", "calc/core.py", "calc/helpers.py"],
                         ["git", "-c", "user.name=fake", "-c", "user.email=fake@example.invalid", "commit", "-qm", "model"]):
                subprocess.run(argv, check=True, capture_output=True)
            emit({"type": "tool_execution_end", "toolCallId": "b0", "toolName": "bash", "result": {"content": [{"type": "text", "text": ""}]}})
        emit({"type": "entry_appended", "entry": {"type": "custom", "customType": "command_bounded", "data": {"action": "set", "timeout": 120}}})
        emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": 300}}})
        emit({"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}})
    else:
        turn(10)
    emit({"type": "agent_end"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
