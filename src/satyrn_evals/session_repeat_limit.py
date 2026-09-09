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
from collections import deque

type ToolKey = str


def _tool_key(payload: object) -> ToolKey | None:
    """The (name, arguments) identity of a tool call, or None if unreadable.

    The arguments live on the ``toolCall`` inside a ``message_update`` payload;
    the mapped ``tool_end`` carries no arguments at all.
    """
    if not isinstance(payload, dict):
        return None
    event = payload.get("assistantMessageEvent")
    call = event.get("toolCall") if isinstance(event, dict) else None
    if not isinstance(call, dict) or not call.get("name"):
        return None
    return json.dumps(
        [call.get("name"), call.get("arguments")], sort_keys=True, default=str
    )


class SessionWindowTripwire:
    """Latching detector for a key recurring ``limit`` times in a window.

    The consecutive detector below cannot see a **rotating** loop. Session 11 of
    the 2026-09-08 batch made 194 tool calls, 188 of them `bash`, drawn from
    **22 distinct** calls: three near-identical `summarize` probes accounted for
    173, cycled A-B-C-A-B-C, so its longest identical-consecutive run is **1**.
    89% of its calls repeated something already tried. It burned the full 600 s
    step timeout and no consecutive rule reaches it.

    This counts occurrences inside a sliding window instead, the way the
    engine's own loop breaker does.

    **The separation is real and thin, which is why this is opt-in with a
    caller-chosen limit.** Over the twelve sessions, the most occurrences of one
    key inside a 20-call window:

        step timeouts       6, 9, 20, 20
        everything else     2, 4, 5, 5, 5, 5, 6, 6

    A limit of 7 catches three of the four timeouts and none of the healthy
    sessions — but the nearest healthy session sits at 6, a margin of **one
    call**. The engine's consecutive breaker was adopted against a gap of 5
    versus 280. This is not that, and a session that legitimately re-runs one
    test command seven times in twenty calls would be ended by it.
    """

    def __init__(self, limit: int, window: int = 20) -> None:
        if limit < 1:
            raise ValueError(f"repeat limit must be at least 1, got {limit}")
        if window < limit:
            raise ValueError(f"window {window} cannot be smaller than limit {limit}")
        self._limit = limit
        self._window = window
        self._recent: deque[ToolKey] = deque(maxlen=window)
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window(self) -> int:
        return self._window

    def reset(self) -> None:
        """Forget the window. Steps are separate requests."""
        self._recent.clear()

    def feed(self, payload: object) -> bool:
        key = _tool_key(payload)
        if key is None:
            return self._tripped
        self._recent.append(key)
        if sum(1 for seen in self._recent if seen == key) >= self._limit:
            self._tripped = True
        return self._tripped


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
        key = _tool_key(payload)
        if key is None:
            return self._tripped
        self._run = self._run + 1 if key == self._previous else 1
        self._previous = key
        if self._run >= self._limit:
            self._tripped = True
        return self._tripped
