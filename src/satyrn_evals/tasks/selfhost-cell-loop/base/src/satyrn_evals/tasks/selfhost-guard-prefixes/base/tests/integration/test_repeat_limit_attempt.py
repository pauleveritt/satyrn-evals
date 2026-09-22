"""The repeated-call spending rule against a real process.

It stops a live cell, so it spawns one and is integration-tier; the
planted-spawn tripwire is untouched and the `integration` marker is what
opens the gate. No model runs.

Each refusal has its sibling, per `BRIEF.md` rule 6: the rule fires on a
locked loop, stays silent when the same adapter varies its calls, and
stays silent when a batch did not ask for it at all.
"""

import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration

LOOPER = Path(__file__).parent / "fake_attempt_looping.py"
TASK = "format_number"


def _cmd(*args: str) -> list[str]:
    return [sys.executable, str(LOOPER), *args]


def test_a_locked_loop_is_stopped_and_says_so(tmp_path: Path) -> None:
    """The rule fires: the cell is torn down and recorded as REPEAT_LIMIT,
    which is deliberately not NO_PATCH -- a cell we stopped is not the
    same event as one that refused on its own."""
    record = attempt(
        task=TASK,
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "attempts",
        command=_cmd("--calls", "60"),
        timeout=120,
        max_repeated_calls=10,
    )
    assert record.code is AttemptCode.REPEAT_LIMIT
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.command_exit is None  # torn down, like a timeout
    assert record.workspace_base_sha is not None
    assert "repeated one tool call" in record.message


def test_distinct_calls_are_not_stopped(tmp_path: Path) -> None:
    """The success sibling: the same adapter, the same call count, the
    same limit -- but each call differs, so the cell runs to completion.
    The rule keys on repetition, not on volume."""
    record = attempt(
        task=TASK,
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "attempts",
        command=_cmd("--calls", "60", "--distinct", "--sleep", "0"),
        timeout=120,
        max_repeated_calls=10,
    )
    assert record.code is not AttemptCode.REPEAT_LIMIT
    assert record.command_exit == 0


def test_the_rule_is_off_unless_a_batch_asks(tmp_path: Path) -> None:
    """The second sibling, and the property the default rests on: the
    same locked loop is *not* stopped when no limit is given, so a batch
    that did not opt in runs as it did before the rule existed."""
    record = attempt(
        task=TASK,
        tasks_root=DEFAULT_TASKS_ROOT,
        output=tmp_path / "attempts",
        command=_cmd("--calls", "20", "--sleep", "0"),
        timeout=120,
    )
    assert record.code is not AttemptCode.REPEAT_LIMIT
    assert record.command_exit == 0
