"""Offline pathology counts over a preserved Pi stream-JSON transcript.

Pure text-in/result-out: no I/O, no subprocess. A cell is measured only
when its transcript satisfies every documented well-formedness rule
(2026-09-04 V10 spec §2 R1-R6); one violation makes the whole cell
measured:false with a single reason, and the wire block never publishes
count keys beside measured:false (S1). The counted unit is the top-level
tool_execution_start event (S2); end events pair starts only where a
metric needs completion semantics.
"""

import json
import posixpath
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Literal

SESSION_VERSION = 3
EVENT_TYPES = frozenset(
    {
        "session", "agent_start", "turn_start", "turn_end", "message_start",
        "message_update", "message_end", "tool_execution_start",
        "tool_execution_update", "tool_execution_end", "agent_end",
        "agent_settled", "entry_appended",
        "compaction_start", "compaction_end",
    }
)
# `compaction_start`/`compaction_end` added 2026-09-08. Without them the parser
# returned `unknown_event` for every transcript whose context window filled --
# it was blind to exactly the cells where accumulation happened, which is the
# regime a session evaluation needs to see. Two v13c Engine cells read
# `unmeasured: unknown_event` for this reason. Like `tool_execution_update`
# they are recognised and counted as NOTHING: compaction is a measurement,
# never a fault and never a tool call.
# `tool_execution_update` added by the V10 amendment of 2026-09-05, forced by
# the Baseline V5d smoke: that transcript carried 23 starts, 23 ends and 49
# updates, so the whole cell read `unmeasured: unknown_event` and V11c's
# precondition 2 failed. An update is a STREAMING PARTIAL of an execution
# already bracketed by its start/end pair, so it is recognised and counted as
# NOTHING -- counting it would inflate tool_calls by roughly 2x per call.

# `run_self_test` added 2026-09-11 (V2b cause 1). The packet route's
# implementer adapter registers that tool (``pi_implementer.py``'s
# ``RUN_SELF_TEST_TOOL_NAME``), and the HP7 live proof shows Pi calling it
# in every phase, so every packet-route transcript read `unmeasured:
# unknown_event` at the first call -- the vocabulary was blind to the tool
# the route exists to exercise. Like `tool_execution_update` it is
# recognised and counted as an ordinary execution.
# `self_test` added in Phase 2a: the engine's `/implement` child registers
# the runner under that name (satyrn-engine Phase 1 Ruling 1, Task 9).
TOOL_NAMES = frozenset({"read", "bash", "edit", "write", "run_self_test", "self_test"})
FILE_TOOLS = frozenset({"read", "edit", "write"})
WRITE_TOOLS = frozenset({"edit", "write"})
SHELL_TOOLS = frozenset({"bash"})
RUNNER_NAMES = frozenset({"pytest"})

#: The engine's guard-firing entries (satyrn-engine Phase 1 Task 2,
#: `budget.GUARD_KINDS`), each a `pi.appendEntry` custom entry the stream
#: carries as `entry_appended` (Phase 1 Ruling 7). Counted as nothing here;
#: `cell_evidence` counts them. `self_test_enforced` added in Phase 3b (the
#: Engine's own run when the model stops untested); `self_test_detected` added
#: 2026-09-18 (the Engine detects pytest's summary line in a bash result and
#: runs its own self-test once). `self_test_redirected` is the retired Phase 3b
#: redirect, kept so already-committed route-proof transcripts still classify.
#: Without any of them every cell where it fires would read `unknown_event`.
GUARD_KINDS = frozenset(
    {
        "loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out",
        "self_test_redirected", "self_test_detected", "self_test_enforced",
        # Release two: the finish-on-green steer (design §2) and the runaway
        # resume (design §3). Without them every cell where either fires
        # reads `unknown_event` and the record is void.
        "finish_nudged", "runaway_resumed",
    }
)

_ENVELOPE_OPENING = re.compile(r'\{\s*"name"\s*:')
_ENVELOPE_ARGUMENTS = re.compile(r'"arguments"\s*:')

type PathologyReason = Literal[
    "absent", "empty", "unparseable", "unsupported_version",
    "unknown_event", "malformed", "multi_session", "partial",
]


@dataclass(frozen=True, slots=True)
class CellPathology:
    """One cell's block: measured counts, or measured:false + one reason."""

    measured: bool
    reason: PathologyReason | None = None
    truncated: bool = False
    invalid_tool_calls: int = 0
    tool_calls: dict[str, int] = field(default_factory=dict)
    repeats: int = 0
    churn: int = 0
    noop_edits: int = 0
    test_runner_commands: int = 0
    tool_free_terminal_turns: int = 0
    workspace_escapes: int = 0
    loop_broken: int = 0
    tool_call_text_messages: int = 0

    def to_block(self) -> dict[str, object]:
        if not self.measured:
            return {"measured": False, "reason": self.reason}
        return {
            "measured": True,
            "truncated": self.truncated,
            "invalid_tool_calls": self.invalid_tool_calls,
            "tool_calls": dict(self.tool_calls),
            "repeats": self.repeats,
            "churn": self.churn,
            "noop_edits": self.noop_edits,
            "test_runner_commands": self.test_runner_commands,
            "tool_free_terminal_turns": self.tool_free_terminal_turns,
            "workspace_escapes": self.workspace_escapes,
            "loop_broken": self.loop_broken,
            "tool_call_text_messages": self.tool_call_text_messages,
        }


def _unmeasured(reason: PathologyReason) -> CellPathology:
    return CellPathology(measured=False, reason=reason)


def count_transcript(text: str, *, had_patch: bool) -> CellPathology:
    """Count pathology over one well-formed transcript (spec §2, §3).

    ``had_patch`` is whether the cell preserved a patch *with content in
    it* (spec §3.6, as corrected by V11d F2 -- see ``rescore._had_patch``,
    which is where the binder decides it); every other count is
    transcript-local. The empty string is ``empty``; a
    transcript the call site could not read at all is ``absent`` and is
    decided by the caller, not here.
    """
    if not text.strip():
        return _unmeasured("empty")
    try:
        events = [
            json.loads(line)
            for line in text.splitlines()
            if line.strip()
        ]
    except json.JSONDecodeError:
        return _unmeasured("unparseable")
    if not all(isinstance(event, dict) for event in events):
        return _unmeasured("unparseable")
    # The packet route's adapter interleaves its own bookkeeping lines with
    # the stream -- `{"adapter_marker": "turn_start", "index": 0}`, carrying
    # no `type` key at all. They are not events and are dropped here, before
    # the header rule can read one as a missing session header.
    events = [event for event in events if "type" in event]
    if not events:
        return _unmeasured("empty")
    if (reason := _header_ok(events)) is not None:
        return _unmeasured(reason)
    # The packet route appends a fresh session to the same retained file for
    # each phase, so one file holds several concatenated sessions. That is
    # the harness's own append, not corruption: it is named before the
    # vocabulary and structure rules run, because a second header otherwise
    # surfaces as their symptom (`malformed`, from the duplicate agent_end)
    # rather than as its cause.
    if sum(1 for event in events if event.get("type") == "session") > 1:
        return _unmeasured("multi_session")
    if (reason := _vocabulary_ok(events)) is not None:
        return _unmeasured(reason)
    structure, truncated = _structure_ok(events)
    if structure is not None:
        return _unmeasured(structure)
    return _count(events, had_patch=had_patch, truncated=truncated)


def decoded_scan_text(text: str) -> str:
    """The decoded payload text of a transcript (V10 spec §3.8).

    The scanned body for ``overlay_windows``: the ``text`` parts of every
    ``tool_execution_end`` result ``content`` and of every event
    ``message`` content, newline-joined. The overlay scan matches raw
    lines, and a well-formed transcript stores such content JSON-escaped
    on single lines, so the body must be decoded first (amendment
    2026-09-05). Pure: no I/O. Callers pass measured documents (R1-R6
    hold), so every line parses; a defensive unparseable line, a
    non-object line, and any non-text or non-string payload contribute
    nothing.
    """
    lines: list[str] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "tool_execution_end":
            result = event.get("result")
            if isinstance(result, dict):
                _append_text_parts(lines, result.get("content"))
        message = event.get("message")
        if isinstance(message, dict):
            _append_text_parts(lines, message.get("content"))
    return "\n".join(lines)


def _append_text_parts(lines: list[str], content: object) -> None:
    """Append every text part's string in ``content`` to ``lines``."""
    if not isinstance(content, list):
        return
    for part in content:
        if (
            isinstance(part, dict)
            and part.get("type") == "text"
            and isinstance(part.get("text"), str)
        ):
            lines.append(part["text"])


def _header_ok(events: list[dict]) -> PathologyReason | None:
    first = events[0]
    if first.get("type") != "session":
        return "malformed"
    if first.get("version") != SESSION_VERSION:
        return "unsupported_version"
    if not isinstance(first.get("cwd"), str) or not first["cwd"]:
        return "malformed"
    return None


def _vocabulary_ok(events: list[dict]) -> PathologyReason | None:
    for event in events:
        if event.get("type") not in EVENT_TYPES:
            return "unknown_event"
        if event.get("type") in (
            "tool_execution_start",
            "tool_execution_update",
            "tool_execution_end",
        ):
            if not isinstance(event.get("toolName"), str) or not event["toolName"]:
                return "malformed"
            if event["toolName"] not in TOOL_NAMES:
                return "unknown_event"
        if event.get("type") == "entry_appended":
            entry = event.get("entry")
            if not isinstance(entry, dict) or not isinstance(entry.get("customType"), str):
                return "malformed"
            if entry["customType"] not in GUARD_KINDS:
                return "unknown_event"
    return None


def _structure_ok(events: list[dict]) -> tuple[PathologyReason | None, bool]:
    """(reason, truncated): ``None`` means well-formed; ``truncated`` marks a cut final turn.

    A budget- or backstop-stopped cell is killed mid-turn, so its transcript
    ends with one open ``turn_start``, no ``agent_end``, and at most the one
    tool call that was in flight. That is **measured**, with the truncation
    recorded on the block -- not malformed. Every other imbalance (a second
    open turn, an end with no start, an unpaired start outside the final
    turn, an ``agent_end`` in a truncated document) is still malformed.
    """
    types = [e.get("type") for e in events]
    turns = types.count("turn_start")
    ends = types.count("turn_end")
    if turns < 1 or ends not in (turns, turns - 1):
        return "malformed", False
    truncated = ends == turns - 1
    # R4 (amended 2026-09-05): the turn markers strictly alternate,
    # turn_start/turn_end/turn_start/turn_end -- no nesting and no
    # reversal. An explicit open/closed state rejects a turn_start while a
    # turn is open and a turn_end while none is open; with the count above,
    # the document ends closed, or open by exactly the truncated final turn.
    open_turn = False
    for event in events:
        match event.get("type"):
            case "turn_start":
                if open_turn:
                    return "malformed", truncated  # nested start: not alternating
                open_turn = True
            case "turn_end":
                if not open_turn:
                    return "malformed", truncated  # no open turn: reversal/double end
                open_turn = False
    if open_turn != truncated:
        return "malformed", truncated
    first_turn = types.index("turn_start")
    last_turn_end = max((i for i, t in enumerate(types) if t == "turn_end"), default=-1)
    last_boundary = len(types) - 1 if truncated else last_turn_end
    for i, event in enumerate(events):
        if event.get("type") in (
            "tool_execution_start",
            "tool_execution_end",
        ) and (i < first_turn or i > last_boundary):
            return "malformed", truncated
    starts: dict[str, tuple[int, dict]] = {}
    seen: set[str] = set()
    for index, event in enumerate(events):
        match event.get("type"):
            case "tool_execution_start":
                call_id = event.get("toolCallId")
                # Uniqueness is document-scoped (spec §2 R5, §0 S2): a
                # call id reused after its pair completed is malformed.
                if not isinstance(call_id, str) or call_id in seen:
                    return "malformed", truncated
                args = event.get("args")
                if not isinstance(args, dict):
                    return "malformed", truncated
                # A file-tool start whose args are a mapping but carry no
                # string ``path`` is a call pi REFUSED (it never executed);
                # it is counted as invalid, not treated as corruption. See
                # `_invalid_file_call`.
                starts[call_id] = (index, event)
                seen.add(call_id)
            case "tool_execution_end":
                call_id = event.get("toolCallId")
                if not isinstance(call_id, str):
                    return "malformed", truncated
                start = starts.get(call_id)
                if start is None:
                    return "malformed", truncated
                # R5 (amended 2026-09-05): the paired end carries the same
                # toolName as its start; a mismatch is a corrupted stream
                # (S1), never a clean count.
                if event.get("toolName") != start[1].get("toolName"):
                    return "malformed", truncated
                starts.pop(call_id)
    if starts:
        # Only the tool call in flight when the process was killed may be
        # unpaired, and only in the truncated final turn.
        if not truncated or len(starts) != 1:
            return "malformed", truncated
        if next(iter(starts.values()))[0] < last_turn_end:
            return "malformed", truncated
    ends_idx = [i for i, e in enumerate(events) if e.get("type") == "agent_end"]
    if truncated:
        if ends_idx:
            return "malformed", truncated
        return None, True
    if not ends_idx:
        return "partial", False
    if len(ends_idx) > 1:
        return "malformed", False
    remainder = events[ends_idx[0] + 1 :]
    if len(remainder) > 1 or any(
        event.get("type") != "agent_settled" for event in remainder
    ):
        return "malformed", False
    return None, False


def _invalid_file_call(event: dict) -> bool:
    """A file-tool start whose args lack a string ``path``.

    pi refused the call (its paired end carries a validation error), so it
    never executed. It is counted as ``invalid_tool_calls`` and contributes to
    none of ``tool_calls``, ``repeats``, ``churn``, ``noop_edits`` or
    ``workspace_escapes`` -- counting it would manufacture an execution from a
    call that did nothing (2026-09-08 ruling). ``_structure_ok`` guarantees
    ``args`` is a mapping, so only the ``path`` is checked here.
    """
    return event["toolName"] in FILE_TOOLS and not isinstance(
        (event.get("args") or {}).get("path"), str
    )


def _count(events: list[dict], *, had_patch: bool, truncated: bool = False) -> CellPathology:
    """Eight count axes over a well-formed document (spec §3.1-3.8).

    Called only on documents that passed R1-R6, so structural guarantees
    hold here: starts pair uniquely with ends (or one is the truncated
    in-flight call), and every file-tool execution carries a string
    ``args.path`` unless it is an invalid call, counted separately.
    ``tool_call_text_messages`` (2026-09-24) is outside the spec's axes: it
    reads assistant messages, not executions, and changes none of the others.
    A block written before it lacks the key: unknown, not zero.
    """
    starts = [e for e in events if e.get("type") == "tool_execution_start"]
    invalid = [e for e in starts if _invalid_file_call(e)]
    valid = [e for e in starts if not _invalid_file_call(e)]
    tool_calls: dict[str, int] = {}
    for event in valid:
        name = event["toolName"]
        tool_calls[name] = tool_calls.get(name, 0) + 1
    identity = Counter(
        (event["toolName"], json.dumps(event.get("args"), sort_keys=True))
        for event in valid
    )
    repeats = sum(count - 1 for count in identity.values())
    last_payload: dict[str, str] = {}
    churn = 0
    for event in valid:
        if event["toolName"] not in WRITE_TOOLS:
            continue
        args = event.get("args") or {}
        payload_key = "edits" if event["toolName"] == "edit" else "content"
        if payload_key not in args:
            # spec §3.3: an execution lacking its payload key contributes
            # nothing - it neither counts as churn nor establishes the
            # path's comparison baseline.
            continue
        payload = json.dumps(args[payload_key], sort_keys=True)
        path = args["path"]  # a valid file tool carries a string path
        if path in last_payload and payload != last_payload[path]:
            churn += 1
        last_payload[path] = payload
    noop_edits = 0
    for event in valid:
        if event["toolName"] != "edit":
            continue
        edits = (event.get("args") or {}).get("edits")
        if isinstance(edits, list) and any(
            isinstance(block, dict)
            and block.get("oldText") is not None
            and block.get("oldText") == block.get("newText")
            for block in edits
        ):
            noop_edits += 1
    test_runner_commands = 0
    for event in starts:
        if event["toolName"] not in SHELL_TOOLS:
            continue
        command = (event.get("args") or {}).get("command")
        if isinstance(command, str) and RUNNER_NAMES & set(command.split()):
            test_runner_commands += 1
    terminal = _terminal_turn(events)
    tool_free = (
        1
        if terminal is not None and not had_patch and _turn_tool_free(events, terminal)
        else 0
    )
    escapes = sum(
        1
        for event in valid
        if event["toolName"] in FILE_TOOLS
        and _escapes(events[0]["cwd"], (event.get("args") or {})["path"])
    )
    loop_broken = tool_call_text_messages = 0
    for event in events:
        match event.get("type"):
            case "message_end" if _tool_call_text(event.get("message")):
                tool_call_text_messages += 1
            case "entry_appended" if event["entry"]["customType"] == "loop_broken":
                loop_broken += 1
    return CellPathology(
        measured=True,
        truncated=truncated,
        invalid_tool_calls=len(invalid),
        tool_calls=tool_calls,
        repeats=repeats,
        churn=churn,
        noop_edits=noop_edits,
        test_runner_commands=test_runner_commands,
        tool_free_terminal_turns=tool_free,
        workspace_escapes=escapes,
        loop_broken=loop_broken,
        tool_call_text_messages=tool_call_text_messages,
    )


def _tool_call_text(message: object) -> bool:
    """An assistant message whose visible text holds a call envelope.

    Both Mellum cells of 2026-09-22 wrote malformed tool-call JSON into text
    and read ``tool_calls: {}`` (`evidence/2026-09-22-mellum-tool-surface/`).
    The envelope is the one the served chat template asks for,
    ``{"name": <function-name>, "arguments": <args-json-object>}``, and the
    ``text`` parts must carry both a ``{"name":`` opening and an
    ``"arguments":`` key: a task manifest's ``{"name": "t", "contract": "c"}``
    opens the same way, and a Pi ``toolCall`` part quoted in prose carries
    ``"arguments":`` with ``name`` not first. The unit is the assistant
    ``message_end`` -- the event the budget counter and the length-stop count
    read; ``turn_end`` repeats the turn's final message and is not counted.
    One message counts once however many envelopes it holds. Whether the message also
    carries a parsed ``toolCall`` part does not matter: a server that
    salvages one call from a broken reply still leaves the rest in text.
    ``thinking`` parts are not read (a model drafts calls in its reasoning),
    and neither are tool results, the prompt, or guard messages, whose text
    is file content or harness text, never the model's attempt at a call.
    """
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return False
    parts: list[str] = []
    _append_text_parts(parts, message.get("content"))
    if '"arguments"' not in (text := "\n".join(parts)):
        return False
    return (
        _ENVELOPE_ARGUMENTS.search(text) is not None
        and _ENVELOPE_OPENING.search(text) is not None
    )


def _terminal_turn(events: list[dict]) -> tuple[int, int] | None:
    """(turn_start index, turn_end index) of the final turn; ``None`` when no turn closed.

    A truncated transcript whose only turn was cut has no ``turn_end``; the
    terminal-turn counts are then zero rather than a crash.
    """
    end_idx = max(
        (i for i, e in enumerate(events) if e.get("type") == "turn_end"), default=None
    )
    if end_idx is None:
        return None
    start_idx = max(
        (i for i, e in enumerate(events[:end_idx]) if e.get("type") == "turn_start"),
        default=None,
    )
    if start_idx is None:
        return None
    return start_idx, end_idx


def _turn_tool_free(events: list[dict], turn: tuple[int, int]) -> bool:
    """The turn holds assistant text but no tool execution inside it."""
    start_idx, end_idx = turn
    parts = events[end_idx].get("message", {}).get("content")
    if not isinstance(parts, list):
        return False
    has_text = any(
        isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
        and part["text"].strip()
        for part in parts
    )
    if not has_text:
        return False
    return not any(
        events[i].get("type") == "tool_execution_start"
        for i in range(start_idx + 1, end_idx)
    )


def _escapes(cwd: str, path: str) -> bool:
    """Lexical escape: the file-tool path resolves outside the transcript cwd.

    Callers pass a file-tool path that R5 already guaranteed is a string
    (measured documents only), so no path-type guard is needed here.
    """
    candidate = path if posixpath.isabs(path) else posixpath.join(cwd, path)
    normalized = PurePosixPath(posixpath.normpath(candidate))
    return not normalized.is_relative_to(PurePosixPath(cwd))
