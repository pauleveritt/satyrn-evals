"""Stop a cell that is repeating one tool call, and record that it was.

A **spending rule**, in the same family as the attempt timeout — not a
nudge. The model is sent nothing and told nothing; the process is torn
down exactly as a timeout tears it down. A bare arm stays bare.

Why it exists: on the V11c spike (2026-09-05) seven Baseline cells each
issued 281 identical ``read app.py`` calls after locking at their fifth
tool call, and each burned about ten minutes reaching the server's
context limit. That is 70 of the batch's 102 minutes spent re-confirming
a decision the cell had already made.

Why it is believed not to change what is measured, replayed offline over
that batch's 24 retained transcripts before it ran anywhere: the longest
run of identical consecutive tool calls is **1, 3 or 5** on every cell
that succeeded and **280** on each locked cell. Nothing falls between, so
a limit inside that gap separates them exactly. Two limits on that claim:
it is inductive — 8/8 locked cells on record never recovered, which is not
proof that none could — and it is one model, so it is re-checked per model
(`tests/integration/test_repeat_limit_replay.py`).

It also forecloses observing whether compaction would rescue a locked
loop, which is why it is **off unless a batch asks for it** and why the
limit a batch used is recorded on every attempt record.
"""

import json

TOOL_START = "tool_execution_start"


class RepeatTripwire:
    """Latching detector for ``limit`` identical consecutive tool calls.

    Fed one transcript line at a time so it can run against a file that
    is still being written. Lines it cannot parse are ignored: a live
    transcript can carry a partial write or a wrapper's noise, and a
    spending rule must never end a cell over one bad line.
    """

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError(f"repeat limit must be at least 1, got {limit}")
        self._limit = limit
        self._previous: str | None = None
        self._run = 0
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def run(self) -> int:
        """Length of the current identical run, for the refusal message."""
        return self._run

    @property
    def limit(self) -> int:
        return self._limit

    def feed(self, line: str) -> bool:
        """Consume one transcript line; return whether the wire is tripped."""
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            return self._tripped
        if not isinstance(event, dict) or event.get("type") != TOOL_START:
            return self._tripped
        key = json.dumps(
            [event.get("toolName"), event.get("args")], sort_keys=True
        )
        self._run = self._run + 1 if key == self._previous else 1
        self._previous = key
        if self._run >= self._limit:
            self._tripped = True
        return self._tripped
