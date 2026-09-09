"""Stop a session step that is repeating one tool call, and record that it was.

The session sibling of `repeat_limit.py`, and deliberately a separate class
rather than a reuse of it: the attempt tripwire keys on `tool_execution_start`
(`repeat_limit.py:29`), an event the session adapter does not map
(`adapters/pi_session.py`).

**Where the key comes from, corrected against the stream itself.** A review
proposed keying on the mapped `tool_end` payload. That payload carries
`toolName`, `toolCallId`, `result` and `isError` and **no arguments**, so a key
built from it could only be the tool's name -- and ten consecutive `bash` calls
running ten different commands is ordinary work, not a loop. The arguments live
on the `toolCall` object inside a `message_update` payload, which the adapter
spools with kind `other`. That is what this keys on.

**Why, measured rather than assumed.** Over twelve Baseline sessions on
2026-09-08, four hit the 600 s step timeout. Two of them were locked loops:
sessions 02 and 05 reached longest identical-consecutive runs of **127** and
**129** calls. Successful sessions in the same batch reached **at most 5**.
Nothing falls between, so a limit inside that gap separates them exactly, and
the batch's own transcripts are the replay evidence
(`tests/integration/test_session_repeat_limit_replay.py`).

**What it does not reach, stated so the limit is not oversold.** The other two
timeouts are a different pathology. Session 03 ran 49 calls with a longest run
of 4; session 11 ran **194 calls with no two consecutive calls alike**. That is
thrashing, not looping, and no consecutive-repeat limit touches it. This fix
addresses two of the four timeouts in that batch, not four.

Off unless a caller asks for it, exactly as the attempt tripwire is: a limit
changes what a session can be observed doing, so it is a declared condition.
"""

import json

type ToolKey = str


class SessionRepeatTripwire:
    """Latching detector for ``limit`` identical consecutive tool calls.

    Fed one parsed event at a time. An event it cannot key -- a payload
    without a recognisable ``toolCall`` -- is ignored rather than treated as a
    repeat: a spending rule must never end a step over one unreadable event.
    """

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError(f"repeat limit must be at least 1, got {limit}")
        self._limit = limit
        self._previous: ToolKey | None = None
        self._run = 0
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def run(self) -> int:
        return self._run

    @property
    def limit(self) -> int:
        return self._limit

    def reset(self) -> None:
        """Forget the run. Called between steps: a session's steps are
        separate requests, so a call repeated across a step boundary is not
        the loop this detects."""
        self._previous = None
        self._run = 0

    def feed(self, payload: object) -> bool:
        """Consume one event payload; return whether the wire is tripped.

        Any payload carrying an ``assistantMessageEvent.toolCall`` counts;
        everything else is ignored.
        """
        if not isinstance(payload, dict):
            return self._tripped
        event = payload.get("assistantMessageEvent")
        call = event.get("toolCall") if isinstance(event, dict) else None
        if not isinstance(call, dict) or not call.get("name"):
            return self._tripped
        key = json.dumps(
            [call.get("name"), call.get("arguments")], sort_keys=True, default=str
        )
        self._run = self._run + 1 if key == self._previous else 1
        self._previous = key
        if self._run >= self._limit:
            self._tripped = True
        return self._tripped
