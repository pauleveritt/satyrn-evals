"""Per-cell evidence for every cell, whatever its code (spec "Measures, per cell").

Where V10 (``pathology.py``) refuses a whole transcript on one unknown event
or a missing ``agent_end`` -- which is every ``COMMAND_TIMEOUT`` and
``BUDGET_EXCEEDED`` cell -- this reads what it can, like the V16 census, and
never voids a cell. Pure: transcript text (and optionally the harness
timeline and the task overlay) in, one block out. No filesystem, no process.

The escape rules are lexical and stated so a reader can recompute them:

- a **path token** in a ``bash`` command is a word that starts with ``/``,
  ``~`` or ``$HOME`` (redirection targets included; ``/dev/null``,
  ``/dev/stdout``, ``/dev/stderr`` and ``/dev/tty`` excluded; ``//`` is a
  URL fragment, not a path);
- it is **outside** when it is ``~``/``$HOME``-rooted, or when its normalized
  form is not under the transcript's ``session`` cwd (``/private/var`` and
  ``/var``, ``/private/tmp`` and ``/tmp`` are the same place on macOS);
- a **root-anchored search** is a simple command whose program is ``find``,
  ``fd``, ``rg``, ``tree``, ``locate`` or ``mdfind``, or ``grep`` with
  ``-r``/``-R``, or ``ls -R``, with any outside path operand (``locate`` and
  ``mdfind`` search the disk and always count);
- relative escapes in bash text (``cd .. && find .``) are not counted; a
  file tool's ``..`` path is.
"""

import json
import posixpath
import re
import shlex
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from satyrn_evals.budget import UsageCounter
from satyrn_evals.contamination import scan_transcript
from satyrn_evals.overlay import OverlaySpec
from satyrn_evals.pathology import decoded_scan_text
from satyrn_evals.timeline import read_timeline

#: The spec's per-command threshold: "commands over 120 s".
LONG_COMMAND_SECONDS = 120.0
_DEVICE_PATHS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"})
_SEARCH_PROGRAMS = frozenset({"find", "fd", "rg", "tree"})
_DISK_SEARCH_PROGRAMS = frozenset({"locate", "mdfind"})
#: Which short flags make a listing or grep recursive (``ls -r`` only reverses).
_RECURSIVE_FLAGS = {"grep": "rR", "egrep": "rR", "fgrep": "rR", "ls": "R"}
_FILE_TOOLS = frozenset({"read", "edit", "write"})
_TIMED_OUT = re.compile(r"Command timed out after \d+(?:\.\d+)? seconds")
_SEPARATORS = frozenset("|&;()")


@dataclass(frozen=True, slots=True)
class CellEvidence:
    turns: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    root_searches: int = 0
    bash_outside_paths: int = 0
    file_tool_escapes: int = 0
    git_commits: int = 0
    tool_reported_timeouts: int = 0
    guard_firings: dict[str, int] = field(default_factory=dict)
    timeline: bool = False
    commands_over_120s: int = 0
    unfinished_commands: int = 0
    longest_command_seconds: float | None = None
    overlay_windows: int | None = None

    def to_block(self) -> dict[str, object]:
        return {
            "turns": self.turns,
            "output_tokens": self.output_tokens,
            "tool_calls": self.tool_calls,
            "root_searches": self.root_searches,
            "bash_outside_paths": self.bash_outside_paths,
            "file_tool_escapes": self.file_tool_escapes,
            "git_commits": self.git_commits,
            "tool_reported_timeouts": self.tool_reported_timeouts,
            "guard_firings": dict(sorted(self.guard_firings.items())),
            "timeline": self.timeline,
            "commands_over_120s": self.commands_over_120s,
            "unfinished_commands": self.unfinished_commands,
            "longest_command_seconds": self.longest_command_seconds,
            "overlay_windows": self.overlay_windows,
        }


def _events(text: str) -> list[dict]:
    events: list[dict] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _canonical(path: str) -> str:
    normalized = posixpath.normpath(path)
    for alias in ("/private/var", "/private/tmp"):
        if normalized == alias or normalized.startswith(alias + "/"):
            return normalized.removeprefix("/private")
    return normalized


def outside(cwd: str | None, path: str) -> bool:
    """Whether a path token or file-tool path leaves the worktree."""
    if path.startswith(("~", "$HOME")):
        return True
    if cwd is None:
        return posixpath.isabs(path)
    candidate = path if posixpath.isabs(path) else posixpath.join(cwd, path)
    return not PurePosixPath(_canonical(candidate)).is_relative_to(_canonical(cwd))


def _segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token and set(token) <= _SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def _path_tokens(words: Sequence[str]) -> list[str]:
    paths: list[str] = []
    for word in words:
        value = word.split("=", 1)[1] if word.startswith("-") and "=" in word else word
        if value.startswith("//") or value in _DEVICE_PATHS:
            continue
        if value.startswith(("/", "~", "$HOME")):
            paths.append(value)
    return paths


def _program(words: Sequence[str]) -> tuple[str, list[str]]:
    index = 0
    while index < len(words) and (words[index] in ("sudo", "command", "exec") or re.match(r"^\w+=", words[index])):
        index += 1
    if index == len(words):
        return "", []
    return posixpath.basename(words[index]), list(words[index + 1 :])


def root_search(command: str, cwd: str | None) -> bool:
    for segment in _segments(command):
        program, rest = _program(segment)
        if program in _DISK_SEARCH_PROGRAMS:
            return True
        flags = _RECURSIVE_FLAGS.get(program, "")
        recursive = bool(flags) and any(
            word == "--recursive" or (re.fullmatch(r"-[A-Za-z]+", word) is not None and any(f in word for f in flags))
            for word in rest
        )
        if (program in _SEARCH_PROGRAMS or recursive) and any(outside(cwd, p) for p in _path_tokens(rest)):
            return True
    return False


def outside_paths(command: str, cwd: str | None) -> bool:
    return any(outside(cwd, p) for segment in _segments(command) for p in _path_tokens(segment))


def git_commit(command: str) -> bool:
    for segment in _segments(command):
        program, rest = _program(segment)
        if program != "git":
            continue
        index = 0
        while index < len(rest) and rest[index].startswith("-"):
            index += 2 if rest[index] in ("-C", "-c") else 1
        if index < len(rest) and rest[index] == "commit":
            return True
    return False


def _result_text(event: dict) -> str:
    result = event.get("result")
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list):
        return ""
    return "\n".join(
        part["text"] for part in content if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def collect_evidence(
    transcript: str,
    *,
    timeline: str | None = None,
    overlay: OverlaySpec | None = None,
    visible_texts: Sequence[str] = (),
) -> CellEvidence:
    events = _events(transcript)
    cwd = next(
        (e["cwd"] for e in events if e.get("type") == "session" and isinstance(e.get("cwd"), str) and e["cwd"]),
        None,
    )
    usage = UsageCounter()
    for event in events:
        usage.feed_event(event)
    starts = [e for e in events if e.get("type") == "tool_execution_start" and isinstance(e.get("toolName"), str)]
    commands = [
        e["args"]["command"]
        for e in starts
        if e["toolName"] == "bash" and isinstance(e.get("args"), dict) and isinstance(e["args"].get("command"), str)
    ]
    file_paths = [
        e["args"]["path"]
        for e in starts
        if e["toolName"] in _FILE_TOOLS and isinstance(e.get("args"), dict) and isinstance(e["args"].get("path"), str)
    ]
    guard_firings = Counter(
        e["entry"]["customType"]
        for e in events
        if e.get("type") == "entry_appended"
        and isinstance(e.get("entry"), dict)
        and isinstance(e["entry"].get("customType"), str)
    )
    timeouts = sum(
        1
        for e in events
        if e.get("type") == "tool_execution_end" and e.get("toolName") == "bash" and _TIMED_OUT.search(_result_text(e))
    )
    spans = [span for span in read_timeline(timeline or "").values() if span.tool_name == "bash"]
    finished = [span.seconds for span in spans if span.seconds is not None]
    return CellEvidence(
        turns=usage.turns,
        output_tokens=usage.output_tokens,
        tool_calls=len(starts),
        root_searches=sum(1 for command in commands if root_search(command, cwd)),
        bash_outside_paths=sum(1 for command in commands if outside_paths(command, cwd)),
        file_tool_escapes=sum(1 for path in file_paths if outside(cwd, path)),
        git_commits=sum(1 for command in commands if git_commit(command)),
        tool_reported_timeouts=timeouts,
        guard_firings=dict(guard_firings),
        timeline=timeline is not None,
        commands_over_120s=sum(1 for seconds in finished if seconds > LONG_COMMAND_SECONDS),
        unfinished_commands=sum(1 for span in spans if span.ended is None),
        longest_command_seconds=max(finished) if finished else None,
        overlay_windows=(
            None
            if overlay is None
            else len(scan_transcript(decoded_scan_text(transcript), overlay, visible_texts=visible_texts))
        ),
    )
