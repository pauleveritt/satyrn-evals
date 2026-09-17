"""Fake attempt command that writes a locked read-loop transcript.

Reproduces the V11c spike's Baseline pathology in miniature: it emits
identical `read app.py` tool calls to the transcript, flushing each, and
then blocks. A real cell reaches the context limit; this one waits to be
stopped, so the test observes the spending rule and nothing else.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--calls", type=int, default=200)
    p.add_argument("--distinct", action="store_true",
                   help="vary each call, so the tripwire must NOT fire")
    p.add_argument("--sleep", type=float, default=60.0)
    p.add_argument("contract", nargs="?")
    p.parse_args(namespace=(args := argparse.Namespace()))

    transcript = Path(os.environ["SATYRN_ATTEMPT_TRANSCRIPT"])
    with transcript.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(
            {"type": "session", "version": 3, "cwd": "/w"}) + "\n")
        for i in range(args.calls):
            stream.write(json.dumps({
                "type": "tool_execution_start",
                "toolCallId": f"c{i}",
                "toolName": "read",
                "args": {"path": f"file{i}.py" if args.distinct else "app.py"},
            }) + "\n")
            stream.flush()
            time.sleep(0.01)
    time.sleep(args.sleep)
    sys.exit(0)


if __name__ == "__main__":
    main()
