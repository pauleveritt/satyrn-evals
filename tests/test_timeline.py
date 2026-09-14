"""The harness's tool-call timeline: stamped as read, read back as spans."""

import json
from pathlib import Path

from satyrn_evals.timeline import TimelineWriter, ToolSpan, read_timeline


def _clock(*values: float):
    stamps = iter(values)
    return lambda: next(stamps)


def test_the_writer_stamps_only_tool_starts_and_ends(tmp_path: Path) -> None:
    path = tmp_path / "timeline.jsonl"
    writer = TimelineWriter(path, clock=_clock(10.0, 131.5))
    for line in (
        json.dumps({"type": "turn_start"}),
        json.dumps({"type": "tool_execution_start", "toolCallId": "c1", "toolName": "bash", "args": {}}),
        "{half a line",
        json.dumps({"type": "tool_execution_update", "toolCallId": "c1", "toolName": "bash"}),
        json.dumps({"type": "tool_execution_end", "toolCallId": "c1", "toolName": "bash"}),
    ):
        writer.feed(line)
    writer.close()
    assert [json.loads(line) for line in path.read_text().splitlines()] == [
        {"at": 10.0, "event": "start", "toolCallId": "c1", "toolName": "bash"},
        {"at": 131.5, "event": "end", "toolCallId": "c1", "toolName": "bash"},
    ]


def test_spans_pair_starts_with_ends_and_keep_unfinished_calls() -> None:
    text = "\n".join(
        json.dumps(record)
        for record in (
            {"at": 1.0, "event": "start", "toolCallId": "a", "toolName": "bash"},
            {"at": 2.0, "event": "start", "toolCallId": "b", "toolName": "read"},
            {"at": 2.5, "event": "end", "toolCallId": "b", "toolName": "read"},
            {"at": 3.0, "event": "end", "toolCallId": "zzz", "toolName": "bash"},
        )
    ) + "\nnot json\n"
    spans = read_timeline(text)
    assert spans == {"a": ToolSpan("bash", 1.0, None), "b": ToolSpan("read", 2.0, 2.5)}
    assert spans["b"].seconds == 0.5 and spans["a"].seconds is None
