"""The tool-call timeline: when the harness read each tool call start and end.

Pi's ``--mode json`` events carry no timestamps, so per-command seconds
cannot be recovered from a transcript afterwards. The harness already reads
the transcript as it is written (``workspace._wait_or_trip``); it stamps the
wall-clock moment it read each ``tool_execution_start`` and
``tool_execution_end`` line into ``timeline.jsonl`` beside the transcript.
One writer serves both arms, and nothing the model's tools write is used.

Resolution is the harness's poll interval (0.25 s): a stamp is when the line
was read, never earlier than when it was written. Seconds are reported per
machine and never compared across machines (spec, "Budget, both arms").
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

TIMELINE_NAME = "timeline.jsonl"
_EVENTS = {"tool_execution_start": "start", "tool_execution_end": "end"}


class TimelineWriter:
    """Append one stamped record per tool start or end line fed to it."""

    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self._handle = path.open("a", encoding="utf-8")
        self._clock = clock

    def feed(self, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError, TypeError:
            return
        if not isinstance(event, dict) or (kind := _EVENTS.get(event.get("type"))) is None:
            return
        call_id, tool = event.get("toolCallId"), event.get("toolName")
        if not isinstance(call_id, str) or not isinstance(tool, str):
            return
        record = {"at": self._clock(), "event": kind, "toolCallId": call_id, "toolName": tool}
        self._handle.write(json.dumps(record) + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


@dataclass(frozen=True, slots=True)
class ToolSpan:
    """One tool call as the harness saw it; ``ended`` is None if it never ended."""

    tool_name: str
    started: float
    ended: float | None

    @property
    def seconds(self) -> float | None:
        return None if self.ended is None else self.ended - self.started


def read_timeline(text: str) -> dict[str, ToolSpan]:
    """Spans by tool call id, in start order. Lenient: bad lines are skipped."""
    spans: dict[str, ToolSpan] = {}
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        call_id, tool, at = record.get("toolCallId"), record.get("toolName"), record.get("at")
        if not isinstance(call_id, str) or not isinstance(tool, str) or type(at) not in (int, float):
            continue
        match record.get("event"):
            case "start" if call_id not in spans:
                spans[call_id] = ToolSpan(tool, float(at), None)
            case "end" if call_id in spans and spans[call_id].ended is None:
                spans[call_id] = ToolSpan(tool, spans[call_id].started, float(at))
    return spans
