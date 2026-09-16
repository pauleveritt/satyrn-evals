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
- a **bash test run** is a ``bash`` command with any simple command whose
  program, after leading ``NAME=value`` words, ``env`` and a ``timeout
  DURATION`` wrapper, and after ``uv run`` and its options, is ``pytest`` or
  ``py.test``, or ``python``/``python3[.N]`` followed by ``-m pytest``; the
  Engine's redirect (a narrower rule: nothing else in the command) is read
  from ``guard_firings``;
- the **first passing self-test** is the first of: a ``self_test`` result
  whose text starts ``Test command exited 0``; a ``bash`` result whose text
  starts with the Engine's redirect sentence and holds that line; a
  ``self_test_enforced`` entry with ``exit_code`` 0. It records the turns and
  output tokens counted up to that event, and which route it took;
- a **length stop** is one assistant ``message_end`` whose ``stopReason`` is
  ``"length"``: the per-turn output cap cut that message. It is counted on the
  same events the budget counter sums ``usage.output`` from, so the two can
  never disagree about which messages were the model's; ``turn_end`` carries
  the same field and is not counted.
- an unquoted newline ends a simple command exactly like ``;``; a newline
  inside a quoted argument stays part of that argument's text.
- a heredoc body (``<<WORD`` / ``<<-WORD``, ``WORD`` optionally quoted; not
  ``<<<``, and not ``<<`` that never resolves to a matching terminator line)
  is never a command -- its lines, up to and including the line matching
  the delimiter (leading tabs stripped for ``<<-``), are dropped before
  commands are split; an **unterminated** heredoc (no later line equals the
  delimiter -- including a false ``<<`` from arithmetic left-shift, whose
  "delimiter" is text like ``2))``) is treated as no heredoc at all: the
  text is kept and the newline that started it still ends the command like
  ``;``, so a real command after it is never dropped.
- a **source mutation** is a ``write`` or ``edit`` whose ``tool_execution_end``
  is not an error and whose worktree-relative path is inside the manifest's
  ``source_paths`` and is not a test file (basename ``test_*.py`` or
  ``*_test.py``, or any parent component ``tests``). This is the finishing
  counterfactual's own rule, so the two instruments agree;
- **exploration turns** are the ``turn_start`` events strictly before the turn
  holding the first source mutation, and ``null`` when there is none;
- the **biggest turn** is the turn with the most assistant output tokens, with
  its share of the cell's total;
- a **self stop** is an ``agent_end`` event on a cell the harness did not cut:
  the loop ended on its own rather than being torn down. A cell whose outcome
  code is a harness cut (``HARNESS_CUT_CODES``: ``BUDGET_EXCEEDED``,
  ``COMMAND_TIMEOUT``, ``REPEAT_LIMIT``, ``DEADLINE_EXCEEDED``) is never a
  self-stop even when an ``agent_end`` is present, because the tear-down can
  leave one behind (Ruling R-3). Its turn and token counts are those at that
  event.
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
#: The outcome codes that mean the harness stopped the cell, so an ``agent_end``
#: in the transcript is tear-down residue, not a self-stop (Ruling R-3).
HARNESS_CUT_CODES = frozenset(
    {"BUDGET_EXCEEDED", "COMMAND_TIMEOUT", "REPEAT_LIMIT", "DEADLINE_EXCEEDED"}
)
_DEVICE_PATHS = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"})
_SEARCH_PROGRAMS = frozenset({"find", "fd", "rg", "tree"})
_DISK_SEARCH_PROGRAMS = frozenset({"locate", "mdfind"})
#: Which short flags make a listing or grep recursive (``ls -r`` only reverses).
_RECURSIVE_FLAGS = {"grep": "rR", "egrep": "rR", "fgrep": "rR", "ls": "R"}
_FILE_TOOLS = frozenset({"read", "edit", "write"})
_TIMED_OUT = re.compile(r"Command timed out after \d+(?:\.\d+)? seconds")
_PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?")
#: satyrn-engine runner.ts: `successResult`'s first line and `redirectSentence`'s opening.
_SELF_TEST_PASSED = "Test command exited 0"
_REDIRECTED = "The Engine ran self_test in place of this command"
_UV_RUN_VALUE_FLAGS = frozenset(
    {"--with", "--with-requirements", "--project", "--directory", "--python", "-p", "--group",
     "--extra", "--package", "--env-file", "--index"}
)
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
    self_test_calls: int = 0
    bash_test_runs: int = 0
    length_stops: int = 0
    first_passing_self_test: dict[str, object] | None = None
    timeline: bool = False
    commands_over_120s: int = 0
    unfinished_commands: int = 0
    longest_command_seconds: float | None = None
    overlay_windows: int | None = None
    tool_span_seconds: float | None = None
    exploration_turns: int | None = None
    biggest_turn: dict[str, object] | None = None
    self_stop: dict[str, int] | None = None

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
            "self_test_calls": self.self_test_calls,
            "bash_test_runs": self.bash_test_runs,
            "length_stops": self.length_stops,
            "first_passing_self_test": self.first_passing_self_test,
            "timeline": self.timeline,
            "commands_over_120s": self.commands_over_120s,
            "unfinished_commands": self.unfinished_commands,
            "longest_command_seconds": self.longest_command_seconds,
            "overlay_windows": self.overlay_windows,
            "tool_span_seconds": self.tool_span_seconds,
            "exploration_turns": self.exploration_turns,
            "biggest_turn": self.biggest_turn,
            "self_stop": self.self_stop,
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


def _worktree_relative(path: str, cwd: str | None) -> str | None:
    """A file tool's path as a worktree-relative POSIX path, or None if it leaves."""
    if outside(cwd, path):
        return None
    if not posixpath.isabs(path):
        return posixpath.normpath(path)
    if cwd is None:
        return None
    return posixpath.relpath(_canonical(path), _canonical(cwd))


def _in_source_paths(path: str, source_paths: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    return any(
        candidate == PurePosixPath(entry) or candidate.is_relative_to(PurePosixPath(entry))
        for entry in source_paths
    )


def _is_test_path(path: str) -> bool:
    """The finishing counterfactual's rule exactly (module docstring, Ruling 14)."""
    parts = PurePosixPath(path).parts
    if "tests" in parts[:-1]:
        return True
    name = parts[-1] if parts else ""
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py")


def _heredoc_word(command: str, index: int) -> tuple[str | None, int]:
    """The delimiter word starting at ``index`` (quotes stripped), and the
    index just past it; ``None`` if there is no word before the newline."""
    n = len(command)
    while index < n and command[index] in " \t":
        index += 1
    if index >= n or command[index] == "\n":
        return None, index
    quote: str | None = None
    word: list[str] = []
    while index < n:
        char = command[index]
        if quote is not None:
            if char == quote:
                quote = None
            else:
                word.append(char)
            index += 1
            continue
        if char in "'\"":
            quote = char
            index += 1
            continue
        if char in " \t\n":
            break
        word.append(char)
        index += 1
    return ("".join(word) or None), index


def _skip_heredoc_body(command: str, index: int, delimiter: str, strip_tabs: bool) -> int | None:
    """Index just past the line matching ``delimiter``, dropping every line
    from ``index`` up to and including it; ``None`` if no such line exists
    (an unterminated heredoc -- per R6, treated as no heredoc at all, so the
    caller keeps the text instead of swallowing it)."""
    n = len(command)
    while index <= n:
        newline = command.find("\n", index)
        end = newline if newline != -1 else n
        line = command[index:end]
        candidate = line.lstrip("\t") if strip_tabs else line
        if candidate == delimiter:
            return end + 1 if newline != -1 else n
        if newline == -1:
            return None
        index = newline + 1
    return None


def _mask_unquoted_newlines(command: str) -> str:
    """Turn an unquoted newline into ``;`` so ``_segments`` treats it as the
    separator it is in a shell; a newline inside a quoted argument (or right
    after a backslash) is left alone -- it is text, not a separator. A
    heredoc body is dropped outright: its lines are literal stdin text, not
    commands, even though they sit at column zero unquoted."""
    pieces: list[str] = []
    quote: str | None = None
    escaped = False
    pending_heredocs: list[tuple[str, bool]] = []
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if escaped:
            pieces.append(char)
            escaped = False
            index += 1
        elif quote == "'":
            pieces.append(char)
            if char == "'":
                quote = None
            index += 1
        elif char == "\\" and quote != "'":
            pieces.append(char)
            escaped = True
            index += 1
        elif quote == '"':
            pieces.append(char)
            if char == '"':
                quote = None
            index += 1
        elif char in "'\"":
            pieces.append(char)
            quote = char
            index += 1
        elif quote is None and command.startswith("<<<", index):
            # Here-string: never a heredoc. Consume all three `<` at once so
            # the third one can't be re-matched as the start of `<<`.
            pieces.append(command[index : index + 3])
            index += 3
        elif quote is None and char == "<" and command.startswith("<<", index):
            operator_end = index + 2
            strip_tabs = command.startswith("-", operator_end)
            if strip_tabs:
                operator_end += 1
            delimiter, after = _heredoc_word(command, operator_end)
            if delimiter is None:
                pieces.append(char)
                index += 1
            else:
                pieces.append(command[index:after])
                pending_heredocs.append((delimiter, strip_tabs))
                index = after
        elif char == "\n":
            pieces.append(";")
            index += 1
            for delimiter, strip_tabs in pending_heredocs:
                # R6: an unterminated heredoc (no line matches the
                # delimiter) is not a heredoc at all -- keep the text and
                # let the newline's `;` still separate commands, rather
                # than swallowing everything after it.
                skipped = _skip_heredoc_body(command, index, delimiter, strip_tabs)
                if skipped is not None:
                    index = skipped
            pending_heredocs = []
        else:
            pieces.append(char)
            index += 1
    return "".join(pieces)


def _segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(_mask_unquoted_newlines(command), posix=True, punctuation_chars=True)
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


def _unwrap(words: Sequence[str]) -> list[str]:
    rest = list(words)
    while rest and (rest[0] == "env" or re.match(r"^[A-Za-z_]\w*=", rest[0])):
        rest = rest[1:]
    if rest[:1] == ["timeout"]:
        rest = rest[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[1:]
        rest = rest[1:]
    return rest


def runs_pytest(command: str) -> bool:
    """Whether any simple command in a bash command runs pytest (module docstring)."""
    for segment in _segments(command):
        words = _unwrap(segment)
        if len(words) >= 2 and posixpath.basename(words[0]) == "uv" and words[1] == "run":
            words = words[2:]
            while words and words[0].startswith("-"):
                words = words[2:] if words[0] in _UV_RUN_VALUE_FLAGS else words[1:]
            words = _unwrap(words)
        if not words:
            continue
        program = posixpath.basename(words[0])
        if program in ("pytest", "py.test") or (_PYTHON.fullmatch(program) and words[1:3] == ["-m", "pytest"]):
            return True
    return False


def _passing_route(event: dict) -> str | None:
    match event.get("type"):
        case "tool_execution_end":
            text = _result_text(event)
            if event.get("toolName") == "self_test" and text.split("\n", 1)[0] == _SELF_TEST_PASSED:
                return "tool"
            if event.get("toolName") == "bash" and text.startswith(_REDIRECTED) and _SELF_TEST_PASSED in text.split("\n")[1:2]:
                return "redirected"
        case "entry_appended":
            entry = event.get("entry")
            if (
                isinstance(entry, dict)
                and entry.get("customType") == "self_test_enforced"
                and isinstance(entry.get("data"), dict)
                and entry["data"].get("exit_code") == 0
            ):
                return "enforced"
    return None


def _length_stop(event: dict) -> bool:
    """One assistant ``message_end`` cut at the per-turn output cap (module docstring)."""
    if event.get("type") != "message_end":
        return False
    message = event.get("message")
    return (
        isinstance(message, dict)
        and message.get("role") == "assistant"
        and message.get("stopReason") == "length"
    )


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


def _track_mutation(
    event: dict, turn: int, cwd: str | None, source_paths: Sequence[str], pending: dict[str, int]
) -> int | None:
    """The turn of the first landed source mutation, once its end event arrives.

    Pi runs one tool call at a time, so a call's start and end bracket nothing
    else; when they do not, this answers with the first mutation that *landed*,
    which is what "mutation" means.
    """
    call_id = event.get("toolCallId")
    if not isinstance(call_id, str):
        return None
    match event.get("type"):
        case "tool_execution_start" if event.get("toolName") in ("write", "edit"):
            args = event.get("args")
            path = args.get("path") if isinstance(args, dict) else None
            if isinstance(path, str):
                relative = _worktree_relative(path, cwd)
                if relative is not None and _in_source_paths(relative, source_paths) and not _is_test_path(relative):
                    pending[call_id] = turn
        case "tool_execution_end" if call_id in pending:
            start_turn = pending.pop(call_id)
            if not event.get("isError"):
                return start_turn
    return None


def collect_evidence(
    transcript: str,
    *,
    timeline: str | None = None,
    overlay: OverlaySpec | None = None,
    visible_texts: Sequence[str] = (),
    source_paths: Sequence[str] = (),
    cut: bool = False,
) -> CellEvidence:
    """Every per-cell count this module can read from the transcript.

    ``source_paths`` is the manifest's, so a mutation can be told from a
    detour; empty means no path is a source path. ``cut`` says the cell's
    outcome code is a harness cut, so an ``agent_end`` is tear-down residue
    and ``self_stop`` stays null (Ruling R-3).
    """
    events = _events(transcript)
    cwd = next(
        (e["cwd"] for e in events if e.get("type") == "session" and isinstance(e.get("cwd"), str) and e["cwd"]),
        None,
    )
    usage = UsageCounter()
    first_pass: dict[str, object] | None = None
    per_turn: dict[int, int] = {}
    self_stop: dict[str, int] | None = None
    mutation_turn: int | None = None
    pending_mutations: dict[str, int] = {}
    for event in events:
        before = usage.output_tokens
        usage.feed_event(event)
        if usage.output_tokens != before:
            per_turn[usage.turns] = per_turn.get(usage.turns, 0) + (usage.output_tokens - before)
        if first_pass is None and (route := _passing_route(event)) is not None:
            first_pass = {"turn": usage.turns, "output_tokens": usage.output_tokens, "route": route}
        if self_stop is None and not cut and event.get("type") == "agent_end":
            self_stop = {"turn": usage.turns, "output_tokens": usage.output_tokens}
        if mutation_turn is None:
            mutation_turn = _track_mutation(event, usage.turns, cwd, source_paths, pending_mutations)
    total = usage.output_tokens
    biggest_turn: dict[str, object] | None = None
    if per_turn and total:
        turn, tokens = max(per_turn.items(), key=lambda item: (item[1], -item[0]))
        biggest_turn = {"turn": turn, "output_tokens": tokens, "share": round(tokens / total, 3)}
    all_spans = read_timeline(timeline or "")
    tool_span_seconds = None
    if all_spans:
        starts = [span.started for span in all_spans.values()]
        ends = [span.ended if span.ended is not None else span.started for span in all_spans.values()]
        tool_span_seconds = max(ends) - min(starts)
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
    spans = [span for span in all_spans.values() if span.tool_name == "bash"]
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
        self_test_calls=sum(1 for e in starts if e["toolName"] == "self_test"),
        bash_test_runs=sum(1 for command in commands if runs_pytest(command)),
        length_stops=sum(1 for event in events if _length_stop(event)),
        first_passing_self_test=first_pass,
        timeline=timeline is not None,
        commands_over_120s=sum(1 for seconds in finished if seconds > LONG_COMMAND_SECONDS),
        unfinished_commands=sum(1 for span in spans if span.ended is None),
        longest_command_seconds=max(finished) if finished else None,
        overlay_windows=(
            None
            if overlay is None
            else len(scan_transcript(decoded_scan_text(transcript), overlay, visible_texts=visible_texts))
        ),
        tool_span_seconds=tool_span_seconds,
        exploration_turns=None if mutation_turn is None else mutation_turn - 1,
        biggest_turn=biggest_turn,
        self_stop=self_stop,
    )
