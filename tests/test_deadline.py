"""Default-tier tests for the whole-attempt monotonic budget."""

import pickle

import pytest

from satyrn_evals.attempt_record import DeadlinePhase
from satyrn_evals.deadline import (
    AttemptDeadline,
    AttemptDeadlineExceeded,
    validate_attempt_timeout,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_deadline_returns_remaining_time_from_injected_monotonic_clock() -> None:
    clock = FakeClock()
    deadline = AttemptDeadline(10.0, clock=clock)
    clock.now = 103.25
    assert deadline.remaining(DeadlinePhase.SETUP) == 6.75


def test_deadline_rejects_an_unknown_phase_within_budget() -> None:
    with pytest.raises(ValueError):
        AttemptDeadline(10.0, clock=FakeClock()).remaining("unknown")  # type: ignore[arg-type]


def test_deadline_records_the_first_phase_that_observes_expiry() -> None:
    clock = FakeClock()
    deadline = AttemptDeadline(10.0, clock=clock)
    clock.now = 110.5
    with pytest.raises(AttemptDeadlineExceeded) as caught:
        deadline.remaining(DeadlinePhase.PRESERVATION)
    assert caught.value.phase is DeadlinePhase.PRESERVATION
    assert caught.value.elapsed == 10.5


def test_deadline_expiry_is_a_conventionally_reconstructible_exception() -> None:
    error = AttemptDeadlineExceeded(DeadlinePhase.SETUP, 10.5)
    assert error.args == (DeadlinePhase.SETUP, 10.5)
    assert pickle.loads(pickle.dumps(error)) == error


def test_deadline_prevents_a_new_productive_phase_after_expiry() -> None:
    clock = FakeClock()
    deadline = AttemptDeadline(10.0, clock=clock)
    clock.now = 110.0
    with pytest.raises(AttemptDeadlineExceeded) as first:
        deadline.remaining(DeadlinePhase.COMMAND)
    clock.now = 111.0
    with pytest.raises(AttemptDeadlineExceeded) as later:
        deadline.remaining(DeadlinePhase.GRADING)
    assert later.value is first.value
    assert later.value.phase is DeadlinePhase.COMMAND
    assert later.value.elapsed == 10.0


@pytest.mark.parametrize("timeout", [0, -1.0, float("nan"), float("inf"), True, "1"])
def test_deadline_rejects_invalid_timeout(timeout: object) -> None:
    with pytest.raises(ValueError, match="finite number greater than zero"):
        AttemptDeadline(timeout)  # type: ignore[arg-type]


def test_timeout_validation_normalizes_an_integer() -> None:
    assert validate_attempt_timeout(10) == 10.0
