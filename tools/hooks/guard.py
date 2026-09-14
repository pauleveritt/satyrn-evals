"""PreToolUse guard for Claude Code. Exit 2 blocks the tool call and shows
the message; exit 0 allows it. A tripwire for agents, not a sandbox.
"""

import json
import re
import sys

_PI_PRINT = re.compile(r"(^|[\s;&|(])pi\s+(-p|--print)\b")
_DIRECT_RUN = re.compile(r"satyrn-evals\s+(run|session|attempt)\s")
_RESULT_PATHS = re.compile(r"docs/(results|reviews)/")
_WRITING = re.compile(r"(>>?|\btee\s|\bcp\s|\bmv\s|\btouch\s)")


def decide(tool_name: str, tool_input: dict) -> str | None:
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if _PI_PRINT.search(command) and "tools/review.py" not in command:
            return "blocked: model reviews run only through tools/review.py (one range, one model, one file)"
        if _DIRECT_RUN.search(command) and "satyrn-evals launch" not in command:
            return "blocked: cells run only through `satyrn-evals launch` with a frozen record"
        if _RESULT_PATHS.search(command) and _WRITING.search(command) \
                and "satyrn-evals launch" not in command and "tools/review.py" not in command:
            return "blocked: docs/results and docs/reviews are written only by the launcher and the review script"
        return None
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = str(tool_input.get("file_path", ""))
        if _RESULT_PATHS.search(path):
            return "blocked: docs/results and docs/reviews are written only by the launcher and the review script"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    message = decide(str(payload.get("tool_name", "")), payload.get("tool_input") or {})
    if message is None:
        return 0
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
