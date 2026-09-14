"""Replay the repeated-call tripwire over a real batch's transcripts.

`BRIEF.md` rule 8: a detector must fire on a known-bad and stay silent on
a known-good **from the same batch**. This replays it over the V11c
spike's 24 retained transcripts and asserts both directions at once.

Integration-tier because it reads a batch under `~/satyrn-smokes`, which
CI does not have; it spawns nothing and runs no model. It skips rather
than fails when that batch is absent, so a fresh clone is not broken by
it -- and the skip is why the same claim is *also* pinned as unit tests
in `tests/test_repeat_limit.py`, which need no batch at all.

**Re-check this per model.** The gap it relies on was measured on
gemma-4-12B; V12 introduces a second capability point, and a limit is
only as good as the separation on the model it is applied to.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.repeat_limit import RepeatTripwire

pytestmark = pytest.mark.integration

BATCH = Path.home() / "satyrn-smokes" / "2026-09-05-v11c-spike-184017"


def _cells() -> list[tuple[str, str, int]]:
    """(cell name, attempt code, longest identical run) for every cell."""
    rows = []
    for summary in sorted(BATCH.glob("cell-*/summary.json")):
        cell = summary.parent
        for record_path in cell.glob("*/attempt.json"):
            code = json.loads(record_path.read_text())["code"]
            lines = (record_path.parent / "transcript.txt").read_text().splitlines()
            # A limit of 1 never latches usefully here; run the wire with an
            # unreachable limit and read the longest run it observed.
            wire = RepeatTripwire(limit=10**9)
            longest = 0
            for line in lines:
                wire.feed(line)
                longest = max(longest, wire.run)
            rows.append((cell.name, code, longest))
    return rows


@pytest.fixture(scope="module")
def cells() -> list[tuple[str, str, int]]:
    if not BATCH.is_dir():
        pytest.skip(f"the V11c spike batch is not present at {BATCH}")
    rows = _cells()
    assert len(rows) == 24, f"expected 24 cells, found {len(rows)}"
    return rows


@pytest.mark.parametrize("limit", [10, 25, 50])
def test_the_tripwire_fires_only_on_the_locked_cells(
    cells: list[tuple[str, str, int]], limit: int
) -> None:
    """Both directions, one batch: every limit in the observed gap fires
    on exactly the seven locked cells and on no successful cell."""
    fired = {name for name, _, longest in cells if longest >= limit}
    succeeded = {name for name, code, _ in cells if code == "OK"}
    assert len(fired) == 7, sorted(fired)
    assert fired & succeeded == set(), sorted(fired & succeeded)


def test_the_gap_the_limit_sits_in_is_still_there(
    cells: list[tuple[str, str, int]],
) -> None:
    """The choice of limit rests on a gap, not on a tuned threshold. If a
    future batch closes that gap, this fails and the limit is no longer
    justified by this evidence."""
    healthy = [longest for _, code, longest in cells if code == "OK"]
    locked = [longest for _, code, longest in cells if code != "OK"]
    assert max(healthy) <= 5, healthy
    assert sorted(locked)[-7:] == [280] * 7, sorted(locked)
