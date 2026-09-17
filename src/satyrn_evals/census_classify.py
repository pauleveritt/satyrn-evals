"""The census's classification arithmetic: what each of the eight classes is argued from.

Design section 7. The classes themselves are columns a reviewer fills, by turn,
from the reconstruction -- "a count without a class does not admit a task"
(AGENTS.md), and information and ambiguity are task defects under R0 §2 that no
counter can decide. What this module computes is the evidence: per-turn tokens,
the pre-registered 32,000-token / 48-turn line, and one boolean per mechanically
decidable class. `information` and `ambiguity` are always None: the reviewer
fills them or nothing does.

Pure: dicts and numbers in, dicts and numbers out. No filesystem, no process.
The replay and own-green rules are not here -- they are the pre-registered,
Opus-reviewed ones in
`evidence/2026-09-15-finishing-counterfactual/counterfactual.py`, which the
night driver loads by path so the census reads the same instrument run 1 and
run 2 read (Ruling 7).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from satyrn_evals.budget import UsageCounter

#: Design section 7's table, in its order.
CLASSES: tuple[str, ...] = (
    "information", "ambiguity", "capability", "budget",
    "finishing", "runaway", "hunting", "allowlist",
)
#: The two a reviewer argues and a counter never decides (R0 §2).
REVIEWER_ONLY: tuple[str, ...] = ("information", "ambiguity")
#: The pre-registered comparison line, from
#: `2026-09-15-release-two-finishing-counterfactual.md` section 3.
TOKEN_LINE = 32_000
TURN_LINE = 48
#: `attempt.attempt_dir_name`: ``<task>-YYYYmmdd-HHMMSS-ffffff``.
_STAMP = re.compile(r"-(\d{8}-\d{6}-\d{6})\Z")


@dataclass(frozen=True, slots=True)
class TurnRow:
    turn: int
    output_tokens: int
    cumulative_output_tokens: int
    length_stops: int


def per_turn(events: list[dict]) -> list[TurnRow]:
    """One row per turn, counted exactly as the budget counts (`UsageCounter`).

    Tokens an assistant message carries before the first `turn_start` belong to
    turn 0 and are dropped from the rows but not from the cumulative totals, so
    a row's cumulative figure always matches the tripwire's at that point.
    """
    usage = UsageCounter()
    rows: dict[int, list[int]] = {}
    for event in events:
        before = usage.output_tokens
        usage.feed_event(event)
        if usage.turns >= 1:
            row = rows.setdefault(usage.turns, [0, 0, 0])
            row[0] += usage.output_tokens - before
            row[1] = usage.output_tokens
            row[2] += 1 if _is_length_stop(event) else 0
    return [
        TurnRow(turn=turn, output_tokens=row[0], cumulative_output_tokens=row[1], length_stops=row[2])
        for turn, row in sorted(rows.items())
    ]


def _is_length_stop(event: dict) -> bool:
    message = event.get("message")
    return (
        event.get("type") == "message_end"
        and isinstance(message, dict)
        and message.get("role") == "assistant"
        and message.get("stopReason") == "length"
    )


def within_32k(output_tokens: int, turn: int) -> bool:
    """The pre-registered line: cumulative output tokens <= 32,000 and turn <= 48."""
    return output_tokens <= TOKEN_LINE and turn <= TURN_LINE


def actual_at_line(*, verdict: str | None, output_tokens: int, turns: int) -> bool:
    """The harness verdict read at the pre-registered line, not at the record's budget.

    Night 1 compared own-green triggers at 32,000 tokens / 48 turns against the
    verdict at the record's 48,000-token budget, so a cell that only reached its
    pass *between* the two lines counted as no rescue (night-2 design section
    3.2). A pass is a pass at the line only if the cell's own spend stayed
    inside it.

    ``verdict`` is the delivered patch's. A torn-down cell's verdict is ``None``
    by the census's own rule, so its ``tripped_verdict`` -- a 48k teardown state
    -- can never make it actual at the line (Ruling 3), and ``code`` adds
    nothing because only an ``OK`` cell carries a graded verdict (Ruling 4).
    """
    return verdict == "pass" and within_32k(output_tokens, turns)


@dataclass(frozen=True, slots=True)
class Facts:
    """What one cell offers the classifier, all of it already recorded.

    `first_pass_*` come from the driver's turn-by-turn grading, not from the
    cell's own test runs: a pass state is the hidden suite's, an own-green is
    the model's, and section 7 distinguishes them. `tripped_verdict` is the
    offline grade of the torn-down worktree; `raised` is a swallowed
    measurement failure (an unreadable cell, a failed replay or grade), and
    either one withholds the capability flag (Ruling R-5).
    """

    code: str | None
    verdict: str | None
    #: Ruling 5: the line reading -- whether this cell's own outcome passed at
    #: the pre-registered 32k/48 line, distinct from `verdict`/`code`'s 48k
    #: reading. The classes read this, not the budget.
    passed_at_line: bool
    tripped_verdict: str | None
    raised: str | None
    length_stops: int
    root_searches: int
    tool_reported_timeouts: int
    first_pass_turn: int | None
    first_pass_tokens: int | None
    self_stop_turn: int | None
    allowlist_reason: str | None


def flags(facts: Facts) -> dict[str, bool | None]:
    """One entry per class: True/False where a record decides it, None where only a reviewer can."""
    # Ruling 5: the classes read the same line the tally reads. `verdict` and
    # `code` stay on Facts as the 48k reading, printed in their own columns.
    passed = facts.passed_at_line
    reached = facts.first_pass_turn is not None and facts.first_pass_tokens is not None
    inside = reached and within_32k(facts.first_pass_tokens or 0, facts.first_pass_turn or 0)
    # Ruling R-5 (extended): a swallowed measurement failure (``raised``) or a
    # tripped worktree that graded pass is not capability evidence -- the cell
    # either measured nothing or reached a pass the tear-down hid.
    return {
        "information": None,
        "ambiguity": None,
        "capability": not passed and not reached and not facts.raised and facts.tripped_verdict != "pass",
        "budget": not passed and reached and not inside,
        "finishing": not passed and bool(inside),
        "runaway": facts.length_stops > 0,
        "hunting": facts.root_searches > 0 or facts.tool_reported_timeouts > 0,
        "allowlist": bool(facts.allowlist_reason and "non-source path" in facts.allowlist_reason),
    }


def attempt_started(attempt_dir: str) -> float | None:
    """The attempt directory's microsecond UTC stamp, as epoch seconds."""
    match = _STAMP.search(attempt_dir)
    if match is None:
        return None
    started = datetime.strptime(match.group(1), "%Y%m%d-%H%M%S-%f").replace(tzinfo=UTC)
    return started.timestamp()


def whole_attempt_seconds(attempt_dir: str, record_mtime: float) -> float | None:
    """Ruling 8: the directory's stamp to `attempt.json`'s mtime.

    No new harness clock. `timeline.jsonl` is monotonic and holds only tool
    events, so it gives the tool span and never the whole attempt; these two
    stamps already exist and bracket setup, command, preservation and grading.
    """
    started = attempt_started(attempt_dir)
    return None if started is None else record_mtime - started
