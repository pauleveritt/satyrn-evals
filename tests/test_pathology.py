"""V10 pathology parser: well-formedness and the eight count axes."""

import json
from pathlib import Path

from satyrn_evals.pathology import (
    EVENT_TYPES,
    SESSION_VERSION,
    TOOL_NAMES,
    CellPathology,
    PathologyReason,
    count_transcript,
    decoded_scan_text,
)

GOOD = "\n".join([  # faithful-good document in the §1 vocabulary (event shape
    # of the §12 anchor; the row-reproducing fixture is Task 4's)
    '{"type": "session", "version": 3, "cwd": "/w"}',
    '{"type": "agent_start"}',
    '{"type": "turn_start"}',
    '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {"path": "app.py"}}',
    '{"type": "tool_execution_end", "toolCallId": "1", "toolName": "read", "result": {}}',
    '{"type": "tool_execution_start", "toolCallId": "2", "toolName": "read", "args": {"path": "tests/test_app.py"}}',
    '{"type": "tool_execution_end", "toolCallId": "2", "toolName": "read", "result": {}}',
    '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
    '{"type": "turn_start"}',
    '{"type": "tool_execution_start", "toolCallId": "3", "toolName": "edit", "args": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}}',
    '{"type": "tool_execution_end", "toolCallId": "3", "toolName": "edit", "result": {}}',
    '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
    '{"type": "turn_start"}',
    '{"type": "tool_execution_start", "toolCallId": "4", "toolName": "edit", "args": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}}',
    '{"type": "tool_execution_end", "toolCallId": "4", "toolName": "edit", "result": {}}',
    '{"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}}',
    '{"type": "agent_end"}',
    '{"type": "agent_settled"}',
])


def test_documented_constants() -> None:
    assert SESSION_VERSION == 3
    assert {"read", "bash", "edit", "write"} == TOOL_NAMES
    assert {
        "session", "agent_start", "turn_start", "turn_end", "message_start",
        "message_update", "message_end", "tool_execution_start",
        "tool_execution_end", "agent_end", "agent_settled",
    } <= EVENT_TYPES


def test_unmeasured_cell_serializes_without_count_keys() -> None:
    block = CellPathology(measured=False, reason="partial").to_block()
    assert block == {"measured": False, "reason": "partial"}


def _unmeasured(text: str) -> CellPathology:
    return count_transcript(text, had_patch=False)


def test_empty_text_is_unmeasured() -> None:
    block = _unmeasured("")
    assert (block.measured, block.reason) == (False, "empty")


def test_non_json_line_is_unparseable() -> None:
    text = '{"type": "session", "version": 3, "cwd": "/w"}\nnot json\n'
    assert _unmeasured(text).reason == "unparseable"


def test_unknown_event_type_is_unknown() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "agent_start"}\n{"type": "nova_event"}\n'
    )
    assert _unmeasured(text).reason == "unknown_event"


def test_unknown_tool_name_is_unknown() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "turn_start"}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "shell", "args": {}}\n'
    )
    assert _unmeasured(text).reason == "unknown_event"


def test_wrong_version_is_unsupported() -> None:
    text = '{"type": "session", "version": 2, "cwd": "/w"}\n'
    assert _unmeasured(text).reason == "unsupported_version"


def test_session_without_version_is_unsupported() -> None:
    # "Any other version than 3" covers an absent version key (pinned).
    text = '{"type": "session", "cwd": "/w"}\n'
    assert _unmeasured(text).reason == "unsupported_version"


def test_missing_session_header_is_malformed() -> None:
    text = '{"type": "agent_start"}\n'
    assert _unmeasured(text).reason == "malformed"


def test_unbalanced_turns_are_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "turn_start"}\n{"type": "turn_end", "message": {}}\n'
        '{"type": "turn_start"}\n'
    )
    assert _unmeasured(text).reason == "malformed"


def test_duplicate_start_id_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {"path": "a"}}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {"path": "a"}}\n'
        '{"type": "turn_end", "message": {}}\n'  # turns balanced: R5, not R4, fires
    )
    assert _unmeasured(text).reason == "malformed"


def test_unmatched_start_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {"path": "a"}}\n'
        '{"type": "turn_end", "message": {}}\n'  # turns balanced: R5, not R4, fires
    )
    assert _unmeasured(text).reason == "malformed"


def test_end_with_non_string_id_is_malformed() -> None:
    # R5: an execution id is a string; an end whose toolCallId is not a
    # string can never close a recorded start and is malformed -- never a
    # clean count. (Success sibling: GOOD's ids are all strings.)
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_end", "toolCallId": 123, "toolName": "read", "result": {}}\n'
        '{"type": "turn_end", "message": {}}\n'
    )
    assert _unmeasured(text).reason == "malformed"
    assert count_transcript(GOOD, had_patch=True).measured is True


def _two_turn_document(first_id: str, second_id: str) -> str:
    """Two balanced turns, one paired execution each, full terminal."""
    start = (
        '{"type": "tool_execution_start", "toolCallId": "@ID@", '
        '"toolName": "read", "args": {"path": "@PATH@"}}'
    )
    end = (
        '{"type": "tool_execution_end", "toolCallId": "@ID@", '
        '"toolName": "read", "result": {}}'
    )

    def _turn(call_id: str, path: str) -> str:
        return (
            '{"type": "turn_start"}\n'
            + start.replace("@ID@", call_id).replace("@PATH@", path)
            + "\n"
            + end.replace("@ID@", call_id)
            + "\n"
            + '{"type": "turn_end", "message": {}}\n'
        )

    return (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "agent_start"}\n'
        + _turn(first_id, "a")
        + _turn(second_id, "b")
        + '{"type": "agent_end"}\n{"type": "agent_settled"}\n'
    )


def test_reusing_a_completed_start_id_is_malformed() -> None:
    # Id reuse across a completed pair is document-scoped malformed (R5).
    assert _unmeasured(_two_turn_document("1", "1")).reason == "malformed"


def test_two_turn_document_with_distinct_ids_is_measured() -> None:
    # Success sibling: identical structure, distinct ids, stays measured.
    assert count_transcript(
        _two_turn_document("1", "2"), had_patch=False
    ).measured is True


def test_missing_terminal_is_partial() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "agent_start"}\n'
        '{"type": "turn_start"}\n{"type": "turn_end", "message": {}}\n'
    )
    assert _unmeasured(text).reason == "partial"


def _terminal_document(*terminal: str) -> str:
    """A minimal valid document (session, agent_start, one empty turn)."""
    head = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "agent_start"}\n'
        '{"type": "turn_start"}\n'
        '{"type": "turn_end", "message": {}}\n'
    )
    return head + "\n".join(terminal) + "\n"


def test_duplicate_agent_settled_is_malformed() -> None:
    # After the single agent_end the allowed remainder is nothing or exactly
    # one agent_settled; a second agent_settled is anomalous data (R6).
    text = _terminal_document(
        '{"type": "agent_end"}',
        '{"type": "agent_settled"}',
        '{"type": "agent_settled"}',
    )
    assert _unmeasured(text).reason == "malformed"


def test_ending_on_agent_end_is_measured() -> None:
    text = _terminal_document('{"type": "agent_end"}')
    assert count_transcript(text, had_patch=False).measured is True


def test_ending_on_single_agent_settled_is_measured() -> None:
    text = _terminal_document(
        '{"type": "agent_end"}', '{"type": "agent_settled"}'
    )
    assert count_transcript(text, had_patch=False).measured is True


def test_good_document_is_measured() -> None:
    assert count_transcript(GOOD, had_patch=True).measured is True


# --- Task 3 fixtures: one pathology each, all R1-R6 well-formed ---

def _start(call_id: str, tool: str, args: str) -> str:
    return (
        f'{{"type": "tool_execution_start", "toolCallId": "{call_id}", '
        f'"toolName": "{tool}", "args": {args}}}\n'
    )


def _end(call_id: str, tool: str) -> str:
    return (
        f'{{"type": "tool_execution_end", "toolCallId": "{call_id}", '
        f'"toolName": "{tool}", "result": {{}}}}\n'
    )


def _turn(*events: str, final_text: str | None = None) -> str:
    content = (
        f'{{"type": "text", "text": "{final_text}"}}'
        if final_text is not None
        else ""
    )
    return (
        '{"type": "turn_start"}\n'
        + "".join(events)
        + f'{{"type": "turn_end", "message": {{"role": "assistant", "content": [{content}]}}}}\n'
    )


def _doc(*turns: str) -> str:
    return (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "agent_start"}\n'
        + "".join(turns)
        + '{"type": "agent_end"}\n{"type": "agent_settled"}\n'
    )


# Two identical reads of one file: the second is a repeat, not churn.
REPEAT_TEXT = _doc(
    _turn(
        _start("1", "read", '{"path": "app.py"}'),
        _end("1", "read"),
        _start("2", "read", '{"path": "app.py"}'),
        _end("2", "read"),
    )
)

# An edit whose block is byte-identical: a no-op edit.
NOOP_TEXT = _doc(
    _turn(
        _start("1", "edit", '{"path": "app.py", "edits": [{"oldText": "x", "newText": "x"}]}'),
        _end("1", "edit"),
    )
)

# Two differing payloads on one path: the second is churn.
CHURN_TEXT = _doc(
    _turn(
        _start("1", "edit", '{"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}'),
        _end("1", "edit"),
        _start("2", "edit", '{"path": "app.py", "edits": [{"oldText": "a", "newText": "c"}]}'),
        _end("2", "edit"),
    )
)

# A bash execution invoking the runner: command-text evidence.
RUNNER_TEXT = _doc(
    _turn(
        _start("1", "bash", '{"command": "uv run pytest tests/"}'),
        _end("1", "bash"),
    )
)

# A read escaping the workspace root, lexically.
ESCAPE_TEXT = _doc(
    _turn(
        _start("1", "read", '{"path": "../etc/passwd"}'),
        _end("1", "read"),
    )
)

# An absolute path outside the workspace root: a lexical escape (the
# posixpath.isabs arm of spec §3.7).
ABSOLUTE_ESCAPE_TEXT = _doc(
    _turn(
        _start("1", "read", '{"path": "/etc/passwd"}'),
        _end("1", "read"),
    )
)

# An absolute path at or under the workspace root: same-root silence.
ABSOLUTE_IN_ROOT_TEXT = _doc(
    _turn(
        _start("1", "read", '{"path": "/w/app.py"}'),
        _end("1", "read"),
    )
)

# A relative path whose ".." normalizes back inside the root: not an
# escape (normpath runs before the is_relative_to comparison).
IN_ROOT_DOTDOT_TEXT = _doc(
    _turn(
        _start("1", "read", '{"path": "sub/../app.py"}'),
        _end("1", "read"),
    )
)

# A floored model: one text-only turn, no tool execution, no patch.
FLOOR_TEXT = _doc(_turn(final_text="I will fix the redirect now."))

# A completing model: an edit turn, then a text-only final turn; had_patch.
SUCCESS_TEXT = _doc(
    _turn(
        _start("1", "edit", '{"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}'),
        _end("1", "edit"),
    ),
    _turn(final_text="Fixed it."),
)

# An edit that names a path but no edits key: contributes nothing to churn
# (spec §3.3), so the later real edit is the first observable rewrite.
PAYLOADLESS_EDIT_FIRST_TEXT = _doc(
    _turn(_start("1", "edit", '{"path": "app.py"}'), _end("1", "edit")),
    _turn(
        _start("2", "edit", '{"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]}'),
        _end("2", "edit"),
    ),
)

# Two reads of two different files: distinct executions, never repeats.
TWO_DISTINCT_READS_TEXT = _doc(
    _turn(
        _start("1", "read", '{"path": "a.py"}'),
        _end("1", "read"),
        _start("2", "read", '{"path": "b.py"}'),
        _end("2", "read"),
    )
)

# A write then an edit on the same path with differing payloads: the
# cross-tool churn case (spec §3.3 -- payload shapes differ by
# construction, so the later edit is churn).
WRITE_THEN_EDIT_TEXT = _doc(
    _turn(
        _start("1", "write", '{"path": "app.py", "content": "v1"}'),
        _end("1", "write"),
        _start("2", "edit", '{"path": "app.py", "edits": [{"oldText": "v1", "newText": "v2"}]}'),
        _end("2", "edit"),
    )
)

# A measured-shaped document whose turn markers run turn_end-first: R4's
# running balance goes negative at the first marker.
REVERSED_TURNS_TEXT = (
    '{"type": "session", "version": 3, "cwd": "/w"}\n'
    '{"type": "agent_start"}\n'
    '{"type": "turn_end", "message": {}}\n'
    '{"type": "turn_start"}\n'
    '{"type": "agent_end"}\n{"type": "agent_settled"}\n'
)

# Amended R4 (close-out 2026-09-05): a second turn_start while a turn is
# open is malformed even though the counts balance (1 start/end pair would
# leave 2 and 2 -- here 2 starts and 2 ends balance) and the old running
# balance never went negative.
NESTED_TURNS_TEXT = (
    '{"type": "session", "version": 3, "cwd": "/w"}\n'
    '{"type": "agent_start"}\n'
    '{"type": "turn_start"}\n'
    '{"type": "turn_start"}\n'
    '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {"path": "a"}}\n'
    '{"type": "tool_execution_end", "toolCallId": "1", "toolName": "read", "result": {}}\n'
    '{"type": "turn_end", "message": {}}\n'
    '{"type": "turn_end", "message": {}}\n'
    '{"type": "agent_end"}\n{"type": "agent_settled"}\n'
)

# Amended R5 (close-out 2026-09-05): an end event's toolName must match
# its start's -- a read closed by a write of the same id is corrupted.
MISMATCHED_PAIR_TEXT = _doc(
    _turn(_start("1", "read", '{"path": "app.py"}'), _end("1", "write"))
)


def test_tool_calls_counted_by_name_first_seen() -> None:
    block = count_transcript(GOOD, had_patch=True)
    assert list(block.tool_calls) == ["read", "edit"]  # first-seen order
    assert block.tool_calls == {"read": 2, "edit": 2}


def test_repeats_count_identical_executions_beyond_the_first() -> None:
    assert count_transcript(REPEAT_TEXT, had_patch=True).repeats == 1


def test_repeats_ignore_distinct_executions() -> None:
    # Success sibling: two reads of different files are not repeats.
    block = count_transcript(TWO_DISTINCT_READS_TEXT, had_patch=True)
    assert block.repeats == 0
    assert block.tool_calls == {"read": 2}


def test_churn_counts_cross_tool_write_then_edit() -> None:
    # An edit following a write on the same path with a differing payload
    # is churn (spec §3.3); the write itself is never a no-op edit and
    # counts in tool_calls under its own name.
    block = count_transcript(WRITE_THEN_EDIT_TEXT, had_patch=True)
    assert block.churn == 1
    assert block.noop_edits == 0
    assert block.tool_calls == {"write": 1, "edit": 1}


def test_reversed_turn_markers_are_malformed() -> None:
    # Amended R4: markers alternate strictly, so a balanced-count document
    # whose first turn marker is turn_end is malformed -- the running
    # balance goes negative. (Success sibling: GOOD stays measured.)
    assert _unmeasured(REVERSED_TURNS_TEXT).reason == "malformed"
    assert count_transcript(GOOD, had_patch=True).measured is True


def test_nested_turn_markers_are_malformed() -> None:
    # Amended R4 (close-out 2026-09-05): markers strictly alternate, so a
    # second turn_start while a turn is open is malformed even with
    # balanced counts and a never-negative balance. (Success sibling: GOOD
    # alternates strictly and stays measured.)
    assert _unmeasured(NESTED_TURNS_TEXT).reason == "malformed"
    assert count_transcript(GOOD, had_patch=True).measured is True


def test_execution_pair_tool_name_mismatch_is_malformed() -> None:
    # Amended R5 (close-out 2026-09-05): the paired end must carry the
    # same toolName as its start; a read closed by a write is a corrupted
    # stream, never a clean count. (Success sibling: GOOD's pairs all
    # match and stay measured.)
    assert _unmeasured(MISMATCHED_PAIR_TEXT).reason == "malformed"
    assert count_transcript(GOOD, had_patch=True).measured is True


def test_noop_edit_fires_on_byte_identical_block() -> None:
    assert count_transcript(NOOP_TEXT, had_patch=True).noop_edits == 1


def test_churn_counts_differing_payload_on_same_path() -> None:
    block = count_transcript(CHURN_TEXT, had_patch=True)
    assert block.churn == 1
    assert block.noop_edits == 0  # the differing blocks are not no-ops


def test_churn_ignores_payloadless_edits() -> None:
    # An edit naming a path but no edits key contributes nothing (spec
    # §3.3): it neither counts as churn nor establishes a baseline, so the
    # later real edit is the first observable rewrite on the path.
    assert count_transcript(PAYLOADLESS_EDIT_FIRST_TEXT, had_patch=True).churn == 0


def test_test_runner_matches_pytest_token() -> None:
    assert count_transcript(RUNNER_TEXT, had_patch=True).test_runner_commands == 1


def test_test_runner_ignores_aliases_and_wrappers() -> None:
    # Spec §3.5: aliases, wrappers, and indirect invocations are not
    # matched. Only ``pt`` was pinned; ``make test`` and ``./run_tests.sh``
    # are the wrapper forms the done-when names.
    for command in ("pt", "make test", "./run_tests.sh"):
        text = RUNNER_TEXT.replace("uv run pytest tests/", command)
        assert count_transcript(text, had_patch=True).test_runner_commands == 0


def test_workspace_escape_is_lexical() -> None:
    assert count_transcript(ESCAPE_TEXT, had_patch=True).workspace_escapes == 1
    assert count_transcript(GOOD, had_patch=True).workspace_escapes == 0


def test_workspace_escape_fires_on_absolute_outside() -> None:
    # Spec §3.7/§9.3: an absolute path outside cwd is a lexical escape.
    # Deleting the posixpath.isabs arm would flip this to 0.
    assert count_transcript(ABSOLUTE_ESCAPE_TEXT, had_patch=True).workspace_escapes == 1


def test_workspace_escape_stays_silent_at_or_under_the_root() -> None:
    # Same-root-absolute silence: reading the cwd itself or an absolute
    # path under it stays inside the root (no escape).
    assert count_transcript(ABSOLUTE_IN_ROOT_TEXT, had_patch=True).workspace_escapes == 0
    cwd_read = ABSOLUTE_IN_ROOT_TEXT.replace('"/w/app.py"', '"/w"')
    assert count_transcript(cwd_read, had_patch=True).workspace_escapes == 0


def test_workspace_escape_stays_silent_for_in_root_dotdot() -> None:
    # A relative path whose ".." normalizes back inside the root is not an
    # escape (normpath precedes the is_relative_to comparison).
    assert count_transcript(IN_ROOT_DOTDOT_TEXT, had_patch=True).workspace_escapes == 0


def test_tool_free_terminal_turn_counts_only_without_patch() -> None:
    assert count_transcript(FLOOR_TEXT, had_patch=False).tool_free_terminal_turns == 1
    assert count_transcript(SUCCESS_TEXT, had_patch=True).tool_free_terminal_turns == 0


def test_terminal_turn_with_an_execution_is_not_counted() -> None:
    # Refusal sibling for the no-execution clause: GOOD's terminal turn
    # contains the second edit execution AND a text part, so even without a
    # retained patch it is not a tool-free terminal turn. Deleting the
    # execution scan would flip this assertion to 1.
    assert count_transcript(GOOD, had_patch=False).tool_free_terminal_turns == 0


def test_measured_cell_to_block_wire_shape() -> None:
    # The measured wire carries the full count set and never a reason key.
    wire = count_transcript(GOOD, had_patch=True).to_block()
    assert wire == {
        "measured": True,
        "tool_calls": {"read": 2, "edit": 2},
        "repeats": 1,  # the two identical edit executions on app.py
        "churn": 0,
        "noop_edits": 0,
        "test_runner_commands": 0,
        "tool_free_terminal_turns": 0,
        "workspace_escapes": 0,
        "loop_broken": 0,
    }


# A terminal turn whose content list carries no text part.
NO_TEXT_TERMINAL_TEXT = _doc(_turn())

# A terminal turn_end that carries no message at all.
NO_MESSAGE_TERMINAL_TEXT = (
    '{"type": "session", "version": 3, "cwd": "/w"}\n'
    '{"type": "agent_start"}\n'
    '{"type": "turn_start"}\n'
    '{"type": "turn_end"}\n'
    '{"type": "agent_end"}\n{"type": "agent_settled"}\n'
)


def test_terminal_turn_without_text_counts_zero() -> None:
    assert count_transcript(NO_TEXT_TERMINAL_TEXT, had_patch=False).measured is True
    assert (
        count_transcript(NO_TEXT_TERMINAL_TEXT, had_patch=False).tool_free_terminal_turns
        == 0
    )


def test_terminal_turn_without_message_counts_zero() -> None:
    block = count_transcript(NO_MESSAGE_TERMINAL_TEXT, had_patch=False)
    assert block.measured is True
    assert block.tool_free_terminal_turns == 0


# --- R1-R6 refusal sub-branches (100% branch gate coverage) ---

def test_line_that_is_json_but_not_an_object_is_unparseable() -> None:
    text = '{"type": "session", "version": 3, "cwd": "/w"}\n[1, 2]\n'
    assert _unmeasured(text).reason == "unparseable"


def test_session_without_cwd_is_malformed() -> None:
    text = '{"type": "session", "version": 3}\n'
    assert _unmeasured(text).reason == "malformed"


def test_execution_without_tool_name_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "args": {}}\n'
        '{"type": "turn_end", "message": {}}\n'
    )
    assert _unmeasured(text).reason == "malformed"


def test_execution_after_the_last_turn_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "agent_start"}\n'
        '{"type": "turn_start"}\n{"type": "turn_end", "message": {}}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", '
        '"args": {"path": "a"}}\n'
    )
    assert _unmeasured(text).reason == "malformed"


def test_execution_with_non_object_args_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", '
        '"args": "nope"}\n'
        '{"type": "turn_end", "message": {}}\n'
    )
    assert _unmeasured(text).reason == "malformed"


def test_file_tool_without_a_path_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "read", "args": {}}\n'
        '{"type": "turn_end", "message": {}}\n'
    )
    assert _unmeasured(text).reason == "malformed"


def test_execution_end_without_a_start_is_malformed() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n{"type": "turn_start"}\n'
        '{"type": "tool_execution_end", "toolCallId": "1", "toolName": "read", '
        '"result": {}}\n'
        '{"type": "turn_end", "message": {}}\n'
    )
    assert _unmeasured(text).reason == "malformed"


def test_duplicate_agent_end_is_malformed() -> None:
    text = _terminal_document(
        '{"type": "agent_end"}', '{"type": "agent_end"}'
    )
    assert _unmeasured(text).reason == "malformed"


# --- Task 4: the validation-row fixture and the S1 discipline test ---

def test_validation_row_reproduces_the_spec_table() -> None:
    text = Path("tests/data/v10/good-repair.jsonl").read_text(encoding="utf-8")
    block = count_transcript(text, had_patch=True)
    assert block.to_block() == {
        "measured": True,
        "tool_calls": {"read": 6, "edit": 2},
        "repeats": 4,
        "churn": 0,
        "noop_edits": 0,
        "test_runner_commands": 0,
        "tool_free_terminal_turns": 0,
        "workspace_escapes": 0,
        "loop_broken": 0,
    }


def test_measured_false_never_carries_counts() -> None:
    reasons: list[PathologyReason] = [
        "absent", "empty", "unparseable", "unsupported_version",
        "unknown_event", "malformed", "partial",
    ]
    for reason in reasons:
        wire = CellPathology(measured=False, reason=reason).to_block()
        assert set(wire) == {"measured", "reason"}



# --- decoded_scan_text: the overlay scan body (spec §3.8 amendment) ---

def test_decoded_scan_text_joins_result_and_message_text() -> None:
    doc = "\n".join(
        [
            json.dumps(
                {
                    "type": "tool_execution_end", "toolCallId": "1",
                    "toolName": "read",
                    "result": {
                        "content": [
                            {"type": "text",
                             "text": "def test_x():\n    assert True"}
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "turn_end",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "all fixed"}],
                    },
                }
            ),
        ]
    )
    assert decoded_scan_text(doc) == "def test_x():\n    assert True\nall fixed"


def test_decoded_scan_text_keeps_text_parts_only() -> None:
    """usage/args/metadata strings and non-text parts never appear."""
    doc = json.dumps(
        {
            "type": "message_update",
            "usage": {"input": 5, "output": 3},
            "assistantMessageEvent": {
                "type": "toolcall_start", "toolName": "read", "arguments": "{}"
            },
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "secret plan"},
                    {"type": "text", "text": "kept"},
                    {"type": "toolCall", "name": "read"},
                ],
            },
        }
    )
    assert decoded_scan_text(doc) == "kept"


def test_decoded_scan_text_skips_unparseable_and_non_object_lines() -> None:
    doc = (
        "not json\n\n[1, 2]\n"
        + json.dumps(
            {
                "type": "tool_execution_end", "toolCallId": "1",
                "toolName": "read",
                "result": {"content": [{"type": "text", "text": "ok"}]},
            }
        )
    )
    assert decoded_scan_text(doc) == "ok"


def test_decoded_scan_text_ignores_malformed_payload_shapes() -> None:
    """Non-dict results, non-list content, and non-text parts contribute
    nothing -- a defensive decode never raises on malformed payloads."""
    doc = "\n".join(
        [
            json.dumps(
                {"type": "tool_execution_end", "toolCallId": "1",
                 "toolName": "read", "result": "plain"}
            ),
            json.dumps(
                {"type": "tool_execution_end", "toolCallId": "2",
                 "toolName": "read",
                 "result": {"content": "not-a-list"}}
            ),
            json.dumps(
                {
                    "type": "turn_end",
                    "message": {
                        "role": "assistant",
                        "content": [
                            "stray",
                            {"type": "text", "text": 7},
                            {"type": "text", "text": "ok"},
                        ],
                    },
                }
            ),
            json.dumps({"type": "message_start", "message": {"content": None}}),
        ]
    )
    assert decoded_scan_text(doc) == "ok"


# --- V10 amendment 2026-09-05: tool_execution_update ----------------------
#
# Forced by the Baseline V5d smoke, which is a known-bad drawn from the
# batch this amendment serves: agentclinic-repair-depth-2 at R1 emitted 23
# tool_execution_start, 23 tool_execution_end and 49 tool_execution_update,
# so the whole cell read `unmeasured: unknown_event` and V11c precondition 2
# failed. Recompute the shape:
#
#   python3 -c "import json,collections;c=collections.Counter(
#     json.loads(l)['type'] for l in open(T) if l.strip());print(c)"
#
# An update is a streaming partial of an execution its start/end pair already
# brackets, so it must be RECOGNISED and counted as NOTHING.

_UPDATE_DOC = "\n".join([
    '{"type": "session", "version": 3, "cwd": "/w"}',
    '{"type": "agent_start"}',
    '{"type": "turn_start"}',
    '{"type": "tool_execution_start", "toolCallId": "1", "toolName": "bash", "args": {"command": "uv run pytest tests/"}}',
    '{"type": "tool_execution_update", "toolCallId": "1", "toolName": "bash", "args": {"command": "uv run pytest tests/"}, "partialResult": {"content": []}}',
    '{"type": "tool_execution_update", "toolCallId": "1", "toolName": "bash", "args": {"command": "uv run pytest tests/"}, "partialResult": {"content": [{"type": "text", "text": "collecting"}]}}',
    '{"type": "tool_execution_end", "toolCallId": "1", "toolName": "bash", "result": {}}',
    '{"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}}',
    '{"type": "agent_end"}',
    '{"type": "agent_settled"}',
])


def test_tool_execution_update_is_measured_not_unknown() -> None:
    """Success direction: the shape the real smoke emitted now measures."""
    block = count_transcript(_UPDATE_DOC, had_patch=True)
    assert (block.measured, block.reason) == (True, None)


def test_tool_execution_update_does_not_inflate_tool_calls() -> None:
    """The semantic claim: two updates on one call are still one bash call.

    Counting updates would have roughly doubled every cell's tool_calls --
    the smoke carried 49 updates against 23 real executions.
    """
    block = count_transcript(_UPDATE_DOC, had_patch=True)
    assert block.tool_calls == {"bash": 1}
    assert block.test_runner_commands == 1


def test_an_update_with_an_unknown_tool_name_is_still_unknown() -> None:
    """Refusal direction, same fixture: recognising the type did not stop
    the vocabulary check from firing on its payload."""
    bad = _UPDATE_DOC.replace('"toolName": "bash", "args": {"command": "uv run pytest tests/"}, "partialResult"',
                              '"toolName": "telepathy", "args": {}, "partialResult"')
    block = count_transcript(bad, had_patch=True)
    assert (block.measured, block.reason) == (False, "unknown_event")


def test_a_genuinely_unknown_event_type_is_still_unknown() -> None:
    """Refusal direction: the amendment widened the vocabulary by exactly one
    type, and a detector that now accepts anything would prove nothing."""
    bad = _UPDATE_DOC.replace('"type": "tool_execution_update"', '"type": "tool_execution_sideways"', 1)
    block = count_transcript(bad, had_patch=True)
    assert (block.measured, block.reason) == (False, "unknown_event")


# --- V11 correction: Engine loop-break telemetry --------------------------

_LOOP_BROKEN_DOC = _UPDATE_DOC.replace(
    '{"type": "tool_execution_update", "toolCallId": "1", "toolName": "bash", "args": {"command": "uv run pytest tests/"}, "partialResult": {"content": []}}',
    '{"type": "entry_appended", "entry": {"customType": "loop_broken"}}',
    1,
)


def test_engine_loop_break_entry_is_measured_and_counted() -> None:
    """Engine's refusal telemetry is a count, not an unknown transcript."""
    block = count_transcript(_LOOP_BROKEN_DOC, had_patch=True)
    assert (block.measured, block.reason, block.loop_broken) == (True, None, 1)
    assert block.tool_calls == {"bash": 1}


def test_unknown_engine_entry_custom_type_is_not_silently_accepted() -> None:
    """The vocabulary extension is specific to Engine's observed telemetry."""
    bad = _LOOP_BROKEN_DOC.replace('"loop_broken"', '"future_telemetry"')
    block = count_transcript(bad, had_patch=True)
    assert (block.measured, block.reason) == (False, "unknown_event")


# --- V11c follow-up: an invalid `edit` call is not an alternate shape ---

def _doc(*tool_events: str) -> str:
    """A minimal well-formed document wrapping one turn of tool events."""
    return "\n".join([
        '{"type": "session", "version": 3, "cwd": "/w"}',
        '{"type": "agent_start"}',
        '{"type": "turn_start"}',
        *tool_events,
        '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
        '{"type": "agent_end"}',
        '{"type": "agent_settled"}',
    ])


def test_an_edit_without_a_top_level_path_is_malformed() -> None:
    """Regression pin, and a correction (2026-09-05).

    Two Engine cells of the V11c spike read ``measured: false`` on an
    ``edit`` whose args were ``{"edits": [{"path": …, oldText, newText}]}``
    with no top-level ``path``. That was first diagnosed here as a second
    legitimate argument shape V10 failed to model. It is not. The paired
    ``tool_execution_end`` records pi refusing the call --
    ``Validation failed for tool "edit": - path: must have required
    properties path`` -- so the edit never executed. Teaching V10 to read a
    path out of it would manufacture ``tool_calls``, ``churn`` and
    ``noop_edits`` from a call that did nothing.

    Evidence: ``~/satyrn-smokes/2026-09-05-v11c-spike-184017/
    cell-005-engine`` events 163 and 197, ``cell-011-engine`` event 220.

    What remains owed is a way to *count* an invalid tool call rather than
    void the cell over it -- a new axis, and a proposal. See `BACKLOG.md`.
    """
    block = count_transcript(
        _doc(
            '{"type": "tool_execution_start", "toolCallId": "1", "toolName":'
            ' "edit", "args": {"edits": [{"path": "app.py", "oldText": "a",'
            ' "newText": "b"}]}}',
            '{"type": "tool_execution_end", "toolCallId": "1", "toolName":'
            ' "edit", "result": {}}',
        ),
        had_patch=True,
    )
    assert (block.measured, block.reason) == (False, "malformed")


def test_a_well_formed_edit_is_still_measured() -> None:
    """The success sibling: the shape pi actually accepts still counts."""
    block = count_transcript(
        _doc(
            '{"type": "tool_execution_start", "toolCallId": "1", "toolName":'
            ' "edit", "args": {"path": "app.py", "edits": [{"oldText": "a",'
            ' "newText": "b"}]}}',
            '{"type": "tool_execution_end", "toolCallId": "1", "toolName":'
            ' "edit", "result": {}}',
        ),
        had_patch=True,
    )
    assert block.measured is True
    assert block.tool_calls["edit"] == 1
