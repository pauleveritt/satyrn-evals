"""The attempt budget: output tokens and turns, counted as the transcript is written.

Spec "Budget, both arms": 32,000 output tokens (thinking included) and 48
turns per attempt, "enforced by the harness reading the transcript as it is
written. A cell over either is ``BUDGET_EXCEEDED``, a fail." The values are
the campaign's and reach an attempt from the run record
(``run_record.attempt_budget``); this module holds no defaults.

The counted shapes are the ones the engine's receipt counts from the same
stream (satyrn-engine Phase 1 Task 2): one ``turn_start`` is one turn; an
assistant ``message_end`` adds its ``usage.output``. ``cacheRead`` and input
tokens are not budget.
"""

import json
from dataclasses import dataclass
from typing import Literal

type BudgetDimension = Literal["output_tokens", "turns"]


@dataclass(frozen=True, slots=True)
class AttemptBudget:
    """The per-attempt budget a run record froze."""

    output_tokens: int
    turns: int

    def __post_init__(self) -> None:
        for name in ("output_tokens", "turns"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"budget {name} must be a positive integer, got {value!r}")


class UsageCounter:
    """Turns and assistant output tokens over Pi ``--mode json`` lines.

    Lenient by design, like the repeat tripwire: a live transcript can carry
    a partial write, and an unparseable line counts as nothing.
    """

    def __init__(self) -> None:
        self.turns = 0
        self.output_tokens = 0

    def feed_event(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        match event.get("type"):
            case "turn_start":
                self.turns += 1
            case "message_end":
                message = event.get("message")
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    return
                usage = message.get("usage")
                output = usage.get("output") if isinstance(usage, dict) else None
                if type(output) is int and output >= 0:
                    self.output_tokens += output

    def feed(self, line: str) -> None:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            return
        self.feed_event(event)


class BudgetTripwire:
    """Latching detector: trips on the first line that puts usage over budget."""

    def __init__(self, budget: AttemptBudget) -> None:
        self.budget = budget
        self.usage = UsageCounter()
        self._over: BudgetDimension | None = None

    @property
    def over(self) -> BudgetDimension | None:
        return self._over

    def feed(self, line: str) -> bool:
        """Consume one transcript line; return whether the budget is exceeded."""
        if self._over is None:
            self.usage.feed(line)
            if self.usage.output_tokens > self.budget.output_tokens:
                self._over = "output_tokens"
            elif self.usage.turns > self.budget.turns:
                self._over = "turns"
        return self._over is not None

    def message(self) -> str:
        if self._over == "turns":
            return (
                f"attempt command started turn {self.usage.turns}, over the "
                f"budget of {self.budget.turns} turns"
            )
        return (
            f"attempt command spent {self.usage.output_tokens} output tokens, "
            f"over the budget of {self.budget.output_tokens}"
        )
