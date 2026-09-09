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
