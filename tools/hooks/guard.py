"""PreToolUse guard for Claude Code. Exit 2 blocks the tool call and shows
the message; exit 0 allows it. A tripwire for agents, not a sandbox.
"""

import json
import re
import sys

# A "pi" command, anchored so it starts a command (start of string, or after
# whitespace / ; & | ( ) rather than matching inside "pip", "pipx", "mypi",
# "api", etc.
_PI_START = re.compile(r"(?:^|[\s;&|(])pi\b")
# The print flag as its own token, anywhere later in the same command
# segment (other flags/args may sit between "pi" and it).
_PRINT_FLAG = re.compile(r"(?:^|\s)(?:-p|--print)\b")

# A pacing-tool invocation, anchored the same way, so a quoted occurrence
# inside e.g. a commit message does not match.
_DIRECT_RUN = re.compile(r"(?:^|[\s;&|(])satyrn-evals\s+(?:run|session|attempt)\s")

_RESULT_PATHS = re.compile(r"docs/(?:results|reviews)/")
# A writing token that actually targets a docs/results or docs/reviews path
# (immediately, allowing only whitespace in between) — not merely present
# somewhere else in the same command.
_WRITE_TARGET = re.compile(r"(?:>>?\s*|\btee\s+|\bcp\s+|\bmv\s+|\btouch\s+)docs/(?:results|reviews)/")


def _blocks_pi_print(command: str) -> bool:
    for match in _PI_START.finditer(command):
        start = match.end()
        segment_end = len(command)
        for sep in (";", "&", "|"):
            idx = command.find(sep, start)
            if idx != -1:
                segment_end = min(segment_end, idx)
        segment = command[start:segment_end]
        if _PRINT_FLAG.search(segment):
            return True
    return False


def decide(tool_name: str, tool_input: dict) -> str | None:
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if _blocks_pi_print(command) and "tools/review.py" not in command:
            return "blocked: model reviews run only through tools/review.py (one range, one model, one file)"
        if _DIRECT_RUN.search(command) and "satyrn-evals launch" not in command:
            return "blocked: cells run only through `satyrn-evals launch` with a frozen record"
        if _WRITE_TARGET.search(command) \
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
