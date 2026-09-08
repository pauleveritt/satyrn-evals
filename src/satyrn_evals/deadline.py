"""One monotonic whole-attempt budget with durable first-expiry context."""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from satyrn_evals.attempt_record import DeadlinePhase

type MonotonicClock = Callable[[], float]


def validate_attempt_timeout(timeout: float) -> float:
    """Normalize the optional API's positive finite timeout value."""
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(
            "attempt deadline timeout must be a finite number greater than zero"
        )
    return float(timeout)


@dataclass(init=False)
class AttemptDeadlineExceeded(TimeoutError):
    """The first lifecycle phase that observed an exhausted attempt budget."""

    phase: DeadlinePhase
    elapsed: float

    def __init__(self, phase: DeadlinePhase, elapsed: float) -> None:
        phase = DeadlinePhase(phase)
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "elapsed", elapsed)
        TimeoutError.__init__(self, phase, elapsed)

    def __str__(self) -> str:
        return (
            f"whole-attempt deadline exceeded during {self.phase} at {self.elapsed:g}s"
        )


class AttemptDeadline:
    """Return remaining seconds or retain the first observed expiry forever.

    The attempt layer owns this value. Injecting ``clock`` keeps all default-tier
    boundary tests deterministic and prevents wall-clock changes from altering a
    recorded elapsed duration.
    """

    def __init__(
        self, timeout: float, *, clock: MonotonicClock = time.monotonic
    ) -> None:
        self.timeout = validate_attempt_timeout(timeout)
        self._clock = clock
        self._started = clock()
        self._expired: AttemptDeadlineExceeded | None = None

    def remaining(self, phase: DeadlinePhase) -> float:
        """Return the budget left for ``phase`` or raise its first expiry."""
        if self._expired is not None:
            raise self._expired
        phase = DeadlinePhase(phase)
        elapsed = self._clock() - self._started
        if elapsed >= self.timeout:
            self.expire(phase, elapsed=elapsed)
        return self.timeout - elapsed

    @property
    def expired(self) -> bool:
        """Whether a lifecycle boundary has already observed expiry."""
        return self._expired is not None

    def expire(self, phase: DeadlinePhase, *, elapsed: float | None = None) -> None:
        """Latch expiry observed by a subprocess bounded with remaining time."""
        if self._expired is None:
            phase = DeadlinePhase(phase)
            observed = self._clock() - self._started if elapsed is None else elapsed
            self._expired = AttemptDeadlineExceeded(phase, max(observed, self.timeout))
        raise self._expired
