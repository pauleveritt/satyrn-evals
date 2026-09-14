"""PreToolUse guard for Claude Code. Exit 2 blocks the tool call and shows
the message; exit 0 allows it. A tripwire for agents, not a sandbox.
"""

import json
import re
import sys

# A command segment boundary: ; & | or a newline. Splitting on these (rather
# than only searching the whole command) keeps "pi" on one line from pulling
# in a "-p" flag that belongs to an unrelated command on the next line.
_SEGMENT_SPLIT = re.compile(r"[;&|\n]")
# "pi" must LEAD its segment (only whitespace / "(" may precede it) — not
# merely appear as a bare word anywhere in it — so "ls pi -p" (pi as an
# argument to ls) and "grep -rn pi docs" do not count as a "pi" invocation.
# A single known wrapper token may sit between the lead and "pi" itself:
# "uv run", "env" (with optional K=V assignments), "time", "timeout <arg>",
# "sudo", "nohup", or an opening "$(" / backtick — this repository's and
# the shell's habitual ways of wrapping a command without changing what it
# invokes.
_PI_LEAD = re.compile(
    r"^[\s(]*"
    r"(?:\$\(\s*|`\s*)?"
    r"(?:(?:uv\s+run|env(?:\s+\w+=\S+)*|time|timeout\s+\S+|sudo|nohup)\s+)?"
    r"pi\b"
)
# The print flag as its own token, anywhere later in the same segment (other
# flags/args may sit between "pi" and it).
_PRINT_FLAG = re.compile(r"(?:^|\s)(?:-p|--print)\b")

# A pacing-tool invocation, anchored so it starts a command (start of
# string, or after whitespace / ; & | ( ) rather than matching a quoted
# occurrence inside e.g. a commit message.
_DIRECT_RUN = re.compile(r"(?:^|[\s;&|(])satyrn-evals\s+(?:run|session|attempt)\s")

_RESULT_PATHS = re.compile(r"docs/(?:results|reviews)/")

# cp/mv/tee/touch put their target in varying argument positions (last for
# cp/mv, first for tee/touch) — a shell parser would be needed to find the
# exact destination, which is out of scope for a tripwire. So: block
# whenever one of these tokens and a protected path both appear anywhere in
# the command. This deliberately over-blocks a read like
# "cp docs/results/a.md /tmp/" — accepted, since missing a write is worse.
_WRITE_TOKEN = re.compile(r"\b(?:tee|cp|mv|touch)\b")

# A redirect operator (>, >>, or >|) followed by its target token. The
# target is checked for a protected path anywhere within it (after
# stripping surrounding quotes), so "./docs/results/…", "/repo/docs/…",
# "$PWD/docs/…" and quoted forms are all caught, not just the bare path.
# This deliberately over-blocks a redirect to an unrelated path that merely
# contains "docs/results/" as a substring (e.g. "/tmp/docs/results/a.md") —
# accepted, for the same reason.
_REDIRECT_TARGET = re.compile(r"(?:>>|>\|?)\s*(\S+)")


def _blocks_pi_print(command: str) -> bool:
    for segment in _SEGMENT_SPLIT.split(command):
        if _PI_LEAD.match(segment) and _PRINT_FLAG.search(segment):
            return True
    return False


def _writes_into_protected_path(command: str) -> bool:
    if _WRITE_TOKEN.search(command) and _RESULT_PATHS.search(command):
        return True
    for match in _REDIRECT_TARGET.finditer(command):
        target = match.group(1).strip("'\"")
        if _RESULT_PATHS.search(target):
            return True
    return False


def decide(tool_name: str, tool_input: dict) -> str | None:
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if _blocks_pi_print(command) and "tools/review.py" not in command:
            return "blocked: model reviews run only through tools/review.py (one range, one model, one file)"
        if _DIRECT_RUN.search(command) and "satyrn-evals launch" not in command:
            return "blocked: cells run only through `satyrn-evals launch` with a frozen record"
        if _writes_into_protected_path(command) \
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
