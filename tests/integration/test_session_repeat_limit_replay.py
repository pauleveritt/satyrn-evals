"""Replay the session repeat tripwire over retained transcripts.

The claim the limit rests on, checked against evidence rather than argued: on
the twelve-session batch of 2026-09-08, the longest run of identical
consecutive tool calls is **at most 5** in every session that completed, and
**127 and 129** in the two locked sessions. A limit of 10 sits inside that gap,
so it separates them exactly and cannot end a session that was working.

It also pins what the limit does NOT reach: two of the four timeouts in that
batch are not loops. Session 03's longest run is 4 and session 11's is 1 across
194 calls. A row that only showed the wire firing would let a future reader
believe the timeout problem was solved.

Marked integration because it reads batch artifacts outside the repository. It
runs no model and spawns nothing; it is skipped when the batch is absent.
"""

import json
import os
import pathlib

import pytest

from satyrn_evals.session_repeat_limit import SessionRepeatTripwire

pytestmark = pytest.mark.integration

BATCH = pathlib.Path(
    os.path.expanduser("~/satyrn-smokes/2026-09-08-session-hazard-rate-232112")
)
LOCKED = (2, 5)
NOT_LOOPS = (3, 11)
COMPLETED = (4, 7, 10)


def _longest_run(session: int) -> int:
    transcript = next((BATCH / f"session-{session:02d}").rglob("transcript.jsonl"), None)
    if transcript is None:
        pytest.skip(f"retained batch missing session-{session:02d}")
    best = 0
    wire = SessionRepeatTripwire(10**9)  # never trips; used as the run counter
    for raw in transcript.read_text().splitlines():
        if not raw.strip():
            continue
        event = json.loads(raw)
        wire.feed(event.get("payload"))
        best = max(best, wire.run)
    return best


@pytest.mark.parametrize("session", COMPLETED)
def test_a_limit_of_ten_never_fires_on_a_completed_session(session: int) -> None:
    """The direction that matters most: the limit must not cost a good run."""
    assert _longest_run(session) < 10


@pytest.mark.parametrize("session", LOCKED)
def test_a_limit_of_ten_fires_on_a_locked_session(session: int) -> None:
    assert _longest_run(session) >= 10


@pytest.mark.parametrize("session", NOT_LOOPS)
def test_the_limit_does_not_reach_the_other_two_timeouts(session: int) -> None:
    """Pinned so the fix is not read as solving the timeout problem.

    These two also hit the 600 s step timeout and are not loops: no
    consecutive-repeat limit touches them.
    """
    assert _longest_run(session) < 10


# --- The window tripwire, replayed over the same twelve sessions ---
#
# The consecutive wire reaches 2 of the 4 step timeouts. The window wire reaches
# 3, including session 11's rotating loop, and fires on none of the 8 sessions
# that did not time out. The margin is thin and the rows below say so: the
# nearest non-timeout sits at 6 against a limit of 7.

from satyrn_evals.session_repeat_limit import SessionWindowTripwire  # noqa: E402

WINDOW_CAUGHT = (2, 5, 11)
WINDOW_MISSED = (3,)
NON_TIMEOUT = (1, 4, 6, 7, 8, 9, 10, 12)


def _window_wire_trips(session: int, limit: int = 7, window: int = 20) -> bool:
    transcript = next((BATCH / f"session-{session:02d}").rglob("transcript.jsonl"), None)
    if transcript is None:
        pytest.skip(f"retained batch missing session-{session:02d}")
    wire = SessionWindowTripwire(limit, window=window)
    for raw in transcript.read_text().splitlines():
        if raw.strip():
            wire.feed(json.loads(raw).get("payload"))
    return wire.tripped


@pytest.mark.parametrize("session", WINDOW_CAUGHT)
def test_the_window_wire_catches_the_rotating_timeouts(session: int) -> None:
    assert _window_wire_trips(session) is True


@pytest.mark.parametrize("session", NON_TIMEOUT)
def test_the_window_wire_spares_every_session_that_did_not_time_out(
    session: int,
) -> None:
    """The direction that matters: it must not end a working session."""
    assert _window_wire_trips(session) is False


@pytest.mark.parametrize("session", WINDOW_MISSED)
def test_one_timeout_is_still_out_of_reach(session: int) -> None:
    """Pinned so the wire is not read as solving the timeout problem.

    Session 03 peaks at 6 occurrences in a 20-call window -- the same value two
    healthy sessions reach -- so no limit separates it from them.
    """
    assert _window_wire_trips(session) is False
