"""The V16 pathology census: detectors, aggregation, and the no-void rule.

`archive/2026-09-07-pre-reset/docs/superpowers/specs/2026-09-07-v16-pathology-census-design.md`
is the confirmed design. Default tier: no model, no network, no subprocess --
every fixture here is a synthetic transcript built in-process.
"""

import json
from pathlib import Path

from satyrn_evals.census import (
    KNOWN_TOOL_NAMES,
    CellCensus,
    GroupKey,
    aggregate,
    census_root,
    detect_anchor_refusal,
    detect_noop_edit,
    detect_read_lock,
    detect_rejected_edit,
    detect_schema_refusal,
    detect_stall,
    detect_tool_not_found,
    detect_unknown_tool,
    detect_v10_unmeasured,
)


def _events(*lines: str) -> list[dict]:
    return [json.loads(line) for line in lines]


def _start(call_id: str, tool: str, args: dict) -> str:
    return json.dumps(
        {
            "type": "tool_execution_start",
            "toolCallId": call_id,
            "toolName": tool,
            "args": args,
        }
    )


def _end(call_id: str, tool: str, *, result: dict, is_error: bool = False) -> str:
    payload = {
        "type": "tool_execution_end",
        "toolCallId": call_id,
        "toolName": tool,
        "result": result,
    }
    if is_error:
        payload["isError"] = True
    return json.dumps(payload)


def _ok_result(text: str = "done") -> dict:
    return {"content": [{"type": "text", "text": text}]}


# --- schema_refusal -------------------------------------------------------

def test_schema_refusal_fires_on_validation_failed_marker() -> None:
    events = _events(
        _end(
            "1",
            "edit",
            result=_ok_result('Validation failed for tool "edit":\n  - path: required'),
            is_error=True,
        )
    )
    assert detect_schema_refusal(events) == 1


def test_schema_refusal_silent_on_a_clean_edit_result() -> None:
    events = _events(_end("1", "edit", result=_ok_result("applied cleanly")))
    assert detect_schema_refusal(events) == 0


# --- tool_not_found ---------------------------------------------------------

def test_tool_not_found_fires_on_the_exact_wire_shape() -> None:
    events = _events(
        _end("1", "uv", result=_ok_result("Tool uv not found"), is_error=True)
    )
    assert detect_tool_not_found(events) == 1


def test_tool_not_found_silent_when_the_tool_resolves() -> None:
    events = _events(_end("1", "bash", result=_ok_result("ran fine")))
    assert detect_tool_not_found(events) == 0


# --- unknown_tool -----------------------------------------------------------

def test_unknown_tool_fires_on_a_name_outside_the_vocabulary() -> None:
    events = _events(_start("1", "uv_run", {}))
    assert detect_unknown_tool(events) == 1


def test_unknown_tool_silent_for_every_known_name() -> None:
    events = _events(*[_start(str(i), name, {}) for i, name in enumerate(KNOWN_TOOL_NAMES)])
    assert detect_unknown_tool(events) == 0


# --- anchor_refusal ----------------------------------------------------------

def test_anchor_refusal_fires_on_the_mutator_refusal_shape() -> None:
    events = _events(
        json.dumps(
            {
                "type": "tool_execution_end",
                "toolCallId": "1",
                "toolName": "edit",
                "result": {
                    "content": [{"type": "text", "text": "ANCHOR_MISSING: old_text not found"}],
                    "details": {"satyrn": True, "ok": False, "code": "ANCHOR_MISSING"},
                },
                "isError": True,
            }
        )
    )
    assert detect_anchor_refusal(events) == 1


def test_anchor_refusal_silent_on_a_successful_mutation() -> None:
    events = _events(
        json.dumps(
            {
                "type": "tool_execution_end",
                "toolCallId": "1",
                "toolName": "edit",
                "result": {
                    "content": [{"type": "text", "text": "applied"}],
                    "details": {"satyrn": True, "ok": True, "code": "OK"},
                },
            }
        )
    )
    assert detect_anchor_refusal(events) == 0


# --- noop_edit ----------------------------------------------------------------

def test_noop_edit_fires_on_a_no_change_result() -> None:
    events = _events(_end("1", "edit", result=_ok_result("no change made")))
    assert detect_noop_edit(events) == 1


def test_noop_edit_silent_on_an_applied_edit() -> None:
    events = _events(_end("1", "edit", result=_ok_result("edit applied")))
    assert detect_noop_edit(events) == 0


# --- read_lock (frozen by the V13d protocol) ----------------------------------

def test_read_lock_counts_the_longest_identical_run_before_the_first_edit() -> None:
    events = _events(
        _start("1", "read", {"path": "app.py"}),
        _end("1", "read", result=_ok_result()),
        _start("2", "read", {"path": "app.py"}),
        _end("2", "read", result=_ok_result()),
        _start("3", "read", {"path": "app.py"}),
        _end("3", "read", result=_ok_result()),
        _start("4", "edit", {"path": "app.py", "edits": []}),
        _end("4", "edit", result=_ok_result()),
    )
    assert detect_read_lock(events) == 3


def test_read_lock_silent_when_the_first_call_is_already_an_edit() -> None:
    events = _events(
        _start("1", "edit", {"path": "app.py", "edits": []}),
        _end("1", "edit", result=_ok_result()),
        _start("2", "read", {"path": "app.py"}),
        _end("2", "read", result=_ok_result()),
        _start("3", "read", {"path": "app.py"}),
        _end("3", "read", result=_ok_result()),
    )
    assert detect_read_lock(events) == 0


def test_read_lock_does_not_merge_distinct_calls() -> None:
    events = _events(
        _start("1", "read", {"path": "a.py"}),
        _end("1", "read", result=_ok_result()),
        _start("2", "read", {"path": "b.py"}),
        _end("2", "read", result=_ok_result()),
    )
    assert detect_read_lock(events) == 1


# --- stall ----------------------------------------------------------------------

def test_stall_counts_calls_since_the_last_applied_edit() -> None:
    events = _events(
        _end("1", "read", result=_ok_result()),
        _end("2", "edit", result=_ok_result("edit applied")),
        _end("3", "read", result=_ok_result()),
        _end("4", "read", result=_ok_result()),
        _end("5", "read", result=_ok_result()),
    )
    assert detect_stall(events) == 3


def test_stall_is_not_reset_by_a_refused_or_noop_edit() -> None:
    events = _events(
        _end("1", "read", result=_ok_result()),
        _end("2", "edit", result=_ok_result("no change made")),
        _end("3", "edit", result=_ok_result("Validation failed for tool"), is_error=True),
        _end("4", "read", result=_ok_result()),
    )
    # noop + refused edits never reset the run: read, noop-edit, refused-edit, read = 4
    assert detect_stall(events) == 4


def test_stall_resets_only_on_an_applied_edit() -> None:
    events = _events(
        _end("1", "read", result=_ok_result()),
        _end("2", "edit", result=_ok_result("edit applied")),
    )
    # the one read before the applied edit is the longest run; nothing
    # follows the edit, so the trailing run is empty
    assert detect_stall(events) == 1


# --- v10_unmeasured -------------------------------------------------------------

def test_v10_unmeasured_true_with_reason_on_an_unrecognised_event() -> None:
    text = (
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
        '{"type": "agent_start"}\n{"type": "nova_event"}\n'
    )
    refused, reason = detect_v10_unmeasured(text)
    assert (refused, reason) == (True, "unknown_event")


def test_v10_unmeasured_false_on_a_well_formed_document() -> None:
    text = "\n".join(
        [
            '{"type": "session", "version": 3, "cwd": "/w"}',
            '{"type": "agent_start"}',
            '{"type": "turn_start"}',
            '{"type": "turn_end", "message": {"role": "assistant", "content": []}}',
            '{"type": "agent_end"}',
            '{"type": "agent_settled"}',
        ]
    )
    refused, reason = detect_v10_unmeasured(text)
    assert (refused, reason) == (False, None)


# --- the no-void rule (spec §3): every other detector still fires -------------

def test_a_transcript_v10_refuses_still_yields_every_other_detector() -> None:
    """The point of spec §3: one unrecognised event blinds V10 wholesale,
    but the census still counts schema_refusal, tool_not_found, and the
    rest on the very same text."""
    text = "\n".join(
        [
            '{"type": "session", "version": 3, "cwd": "/w"}',
            '{"type": "agent_start"}',
            '{"type": "nova_event"}',  # unrecognised: V10 refuses on this alone
            _end("1", "edit", result=_ok_result('Validation failed for tool "edit"')),
            _end("2", "bash", result=_ok_result("Tool uv not found")),
        ]
    )
    refused, reason = detect_v10_unmeasured(text)
    assert (refused, reason) == (True, "unknown_event")
    from satyrn_evals.census import _parse_events

    events = _parse_events(text)
    assert detect_schema_refusal(events) == 1
    assert detect_tool_not_found(events) == 1


def test_an_unparseable_line_does_not_void_the_other_lines() -> None:
    from satyrn_evals.census import _parse_events

    text = "not json at all\n" + _end(
        "1", "bash", result=_ok_result("Tool uv not found")
    )
    events = _parse_events(text)
    assert len(events) == 1  # the bad line is skipped, not fatal
    assert detect_tool_not_found(events) == 1


def test_an_empty_transcript_is_reported_not_counted_as_zero() -> None:
    """An empty transcript still yields a CellCensus -- with events_scanned
    at 0 and v10_unmeasured true (`empty`) -- rather than being silently
    treated as a clean cell with no pathology."""
    refused, reason = detect_v10_unmeasured("")
    assert (refused, reason) == (True, "empty")
    from satyrn_evals.census import _parse_events

    assert _parse_events("") == []


# --- aggregation: grouped by all four keys, never pooled ----------------------

def _cell(
    *,
    path: str = "p",
    batch: str | None = "b",
    task: str | None = "t",
    arm: str | None = "engine",
    engine_commit: str | None = "c1",
    schema_refusal: int = 0,
    read_lock: int = 0,
    stall: int = 0,
    v10_unmeasured: bool = False,
) -> CellCensus:
    return CellCensus(
        path=Path(path),
        batch=batch,
        task=task,
        arm=arm,
        engine_commit=engine_commit,
        events_scanned=0,
        schema_refusal=schema_refusal,
        tool_not_found=0,
        unknown_tool=0,
        read_lock=read_lock,
        anchor_refusal=0,
        rejected_edit=0,
        noop_edit=0,
        stall=stall,
        v10_unmeasured=v10_unmeasured,
        v10_reason="empty" if v10_unmeasured else None,
    )


def test_aggregate_groups_by_batch_task_arm_and_engine_commit() -> None:
    cells = [
        _cell(path="1", arm="engine", schema_refusal=3),
        _cell(path="2", arm="engine", schema_refusal=4),
        _cell(path="3", arm="baseline", schema_refusal=100),
    ]
    groups = aggregate(cells)
    by_key = {g.key: g for g in groups}
    engine_key = GroupKey(batch="b", task="t", arm="engine", engine_commit="c1")
    baseline_key = GroupKey(batch="b", task="t", arm="baseline", engine_commit="c1")
    assert by_key[engine_key].totals["schema_refusal"] == 7
    assert by_key[baseline_key].totals["schema_refusal"] == 100
    # never pooled: the baseline row's 100 never leaks into engine's total
    assert by_key[engine_key].cell_count == 2


def test_aggregate_separates_different_engine_commits_in_the_same_batch_task_arm() -> None:
    cells = [
        _cell(path="1", engine_commit="pre", schema_refusal=973),
        _cell(path="2", engine_commit="post", schema_refusal=0),
    ]
    groups = aggregate(cells)
    assert len(groups) == 2
    totals_by_commit = {g.key.engine_commit: g.totals["schema_refusal"] for g in groups}
    assert totals_by_commit == {"pre": 973, "post": 0}


def test_aggregate_counts_locked_cells_for_read_lock_not_a_sum() -> None:
    # is_present's naming floor is 2; three cells at 1, 3, 10 -> two "locked".
    cells = [
        _cell(path="1", read_lock=1),
        _cell(path="2", read_lock=3),
        _cell(path="3", read_lock=10),
    ]
    groups = aggregate(cells)
    assert groups[0].totals["read_lock"] == 2


def test_aggregate_counts_v10_unmeasured_cells() -> None:
    cells = [
        _cell(path="1", v10_unmeasured=True),
        _cell(path="2", v10_unmeasured=False),
        _cell(path="3", v10_unmeasured=True),
    ]
    groups = aggregate(cells)
    assert groups[0].totals["v10_unmeasured"] == 2


# --- census_root: schedule.json / preflight.json grouping, on disk ------------

def _write_batch(
    root: Path,
    *,
    task: str,
    cells: list[tuple[str, str]],  # (dir, arm)
    engine_commit: str | None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    schedule = {
        "task": task,
        "cells": [
            {"index": i, "arm": arm, "dir": cell_dir}
            for i, (cell_dir, arm) in enumerate(cells)
        ],
    }
    (root / "schedule.json").write_text(json.dumps(schedule))
    if engine_commit is not None:
        (root / "preflight.json").write_text(
            json.dumps({"engine_commit": engine_commit})
        )
    for cell_dir, _arm in cells:
        attempt_dir = root / cell_dir / "attempt-0001"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "transcript.txt").write_text(
            _end("1", "bash", result=_ok_result("Tool uv not found")) + "\n"
        )


def test_census_root_attributes_cells_from_schedule_and_preflight(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    _write_batch(
        root,
        task="agentclinic-repair-depth-2",
        cells=[("cell-000-engine", "engine"), ("cell-001-baseline", "baseline")],
        engine_commit="deadbeef",
    )
    cells = census_root(root)
    assert len(cells) == 2
    by_arm = {c.arm: c for c in cells}
    assert by_arm["engine"].task == "agentclinic-repair-depth-2"
    assert by_arm["engine"].batch == "runs"
    assert by_arm["engine"].engine_commit == "deadbeef"
    assert by_arm["baseline"].engine_commit == "deadbeef"
    # the detector still runs regardless of attribution
    assert by_arm["engine"].tool_not_found == 1


def test_census_root_degrades_to_none_without_a_schedule(tmp_path: Path) -> None:
    """No schedule.json anywhere: attribution fields are None, never
    guessed, but the cell is still censused (spec §3 -- never void)."""
    root = tmp_path / "runs"
    cell_dir = root / "cell-000-mystery"
    attempt_dir = cell_dir / "attempt-0001"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "transcript.txt").write_text(
        _end("1", "bash", result=_ok_result("Tool uv not found")) + "\n"
    )
    cells = census_root(root)
    assert len(cells) == 1
    cell = cells[0]
    assert cell.task is None
    assert cell.engine_commit is None
    # arm is still guessed from the cell-NNN-ARM directory name
    assert cell.arm == "mystery"
    assert cell.tool_not_found == 1


def test_census_root_handles_nested_per_task_batches(tmp_path: Path) -> None:
    """Mirrors the real V13b/V13c layout: one schedule.json per task
    subdirectory under a shared root."""
    root = tmp_path / "runs"
    _write_batch(
        root / "task-a",
        task="task-a",
        cells=[("cell-000-engine", "engine")],
        engine_commit="c1",
    )
    _write_batch(
        root / "task-b",
        task="task-b",
        cells=[("cell-000-baseline", "baseline")],
        engine_commit="c1",
    )
    cells = census_root(root)
    assert {c.task for c in cells} == {"task-a", "task-b"}
    assert {c.batch for c in cells} == {"runs/task-a", "runs/task-b"}


# --- rejected_edit vs noop_edit (V2b cause 3) ---------------------------------


def _edit_start(call_id: str) -> dict:
    return {
        "type": "tool_execution_start",
        "toolCallId": call_id,
        "toolName": "edit",
        "args": {"path": "app.py", "edits": [{"oldText": "a", "newText": "b"}]},
    }


def _edit_end(call_id: str, text: str, *, is_error: bool = False) -> dict:
    event = {
        "type": "tool_execution_end",
        "toolCallId": call_id,
        "toolName": "edit",
        "result": {"content": [{"type": "text", "text": text}]},
    }
    if is_error:
        event["isError"] = True
    return event


def test_a_rejected_edit_is_counted_separately_from_a_true_no_op() -> None:
    events = [
        _edit_start("c1"),
        _edit_end("c1", "Could not find the exact text in app.py.", is_error=True),
        _edit_start("c2"),
        _edit_end("c2", "No changes made to app.py; identical content.", is_error=True),
    ]

    assert detect_rejected_edit(events) == 1
    assert detect_noop_edit(events) == 1


def test_a_run_self_test_call_is_not_an_unknown_tool() -> None:
    events = [
        {"type": "tool_execution_start", "toolCallId": "c1", "toolName": "run_self_test", "args": {}},
    ]

    assert detect_unknown_tool(events) == 0


# --- packet-route discovery (V2b cause 2) -------------------------------------


def test_census_root_discovers_the_packet_route_transcript(tmp_path: Path) -> None:
    harness = tmp_path / "run" / "harness"
    harness.mkdir(parents=True)
    (harness / ".satyrn-implementer-transcript.jsonl").write_text(
        json.dumps({"type": "session", "version": 3, "cwd": "/x"}) + "\n"
        + json.dumps(
            {
                "type": "tool_execution_start",
                "toolCallId": "c1",
                "toolName": "run_self_test",
                "args": {},
            }
        )
        + "\n"
    )

    cells = census_root(tmp_path)

    assert len(cells) == 1
    assert cells[0].unknown_tool == 0


def test_a_rejected_edit_does_not_reset_the_stall_run() -> None:
    events = [
        _edit_start("c1"),
        _edit_end("c1", "Could not find the exact text in app.py.", is_error=True),
        *_events(
            _start("c2", "read", {"path": "app.py"}),
            _end("c2", "read", result=_ok_result("contents")),
        ),
    ]
    assert detect_stall(events) >= 2
