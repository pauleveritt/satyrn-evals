"""The census's pure classification rules. Default tier: synthetic events, no subprocess.

The eight classes of design section 7 are columns a reviewer fills, not values
this module computes (a count without a class does not admit a task, AGENTS.md).
What is computed is the *evidence* each class is argued from, and each flag has
a firing row and a silent row.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from satyrn_evals.census_classify import (
    CLASSES,
    Facts,
    TurnRow,
    flags,
    per_turn,
    whole_attempt_seconds,
    within_32k,
)


def _assistant(output: int, *, stop: str | None = None) -> dict:
    message: dict = {"role": "assistant", "usage": {"output": output}, "content": []}
    if stop is not None:
        message["stopReason"] = stop
    return {"type": "message_end", "message": message}


TURN = {"type": "turn_start"}


def test_the_eight_classes_are_the_specs_and_in_its_order() -> None:
    assert CLASSES == (
        "information", "ambiguity", "capability", "budget",
        "finishing", "runaway", "hunting", "allowlist",
    )


def test_per_turn_carries_tokens_cumulative_tokens_and_length_stops() -> None:
    rows = per_turn([TURN, _assistant(1000), TURN, _assistant(16000, stop="length"), _assistant(500)])
    assert rows == [
        TurnRow(turn=1, output_tokens=1000, cumulative_output_tokens=1000, length_stops=0),
        TurnRow(turn=2, output_tokens=16500, cumulative_output_tokens=17500, length_stops=1),
    ]


def test_per_turn_of_an_empty_stream_is_empty() -> None:
    assert per_turn([]) == []


@pytest.mark.parametrize(
    ("tokens", "turn", "expected"),
    [(32_000, 48, True), (32_001, 48, False), (32_000, 49, False), (0, 1, True)],
)
def test_within_32k_is_the_pre_registered_line(tokens: int, turn: int, expected: bool) -> None:
    assert within_32k(tokens, turn) is expected


def _facts(**overrides: Any) -> Facts:
    base: dict[str, Any] = dict(
        code="BUDGET_EXCEEDED", verdict=None, tripped_verdict=None, length_stops=0, root_searches=0,
        tool_reported_timeouts=0, first_pass_turn=None, first_pass_tokens=None, self_stop_turn=None,
        allowlist_reason=None,
    )
    return Facts(**(base | overrides))


def test_a_pass_state_inside_the_line_that_the_cell_worked_past_flags_finishing() -> None:
    assert flags(_facts(first_pass_turn=20, first_pass_tokens=18_000))["finishing"] is True


def test_a_pass_state_outside_the_line_flags_budget_not_finishing() -> None:
    row = flags(_facts(first_pass_turn=60, first_pass_tokens=41_000))
    assert (row["budget"], row["finishing"]) == (True, False)


def test_no_pass_state_at_all_flags_capability() -> None:
    row = flags(_facts())
    assert (row["capability"], row["budget"], row["finishing"]) == (True, False, False)


def test_a_cell_that_passed_flags_none_of_the_three() -> None:
    row = flags(_facts(code="OK", verdict="pass", first_pass_turn=8, first_pass_tokens=6000, self_stop_turn=9))
    assert not any(row[name] for name in ("capability", "budget", "finishing"))


def test_a_length_stop_flags_runaway_and_none_flags_it_silent() -> None:
    assert flags(_facts(length_stops=1))["runaway"] is True
    assert flags(_facts(length_stops=0))["runaway"] is False


def test_a_root_search_or_a_bounded_command_flags_hunting() -> None:
    assert flags(_facts(root_searches=1))["hunting"] is True
    assert flags(_facts(tool_reported_timeouts=1))["hunting"] is True
    assert flags(_facts())["hunting"] is False


def test_a_non_source_path_reason_flags_allowlist() -> None:
    assert flags(_facts(allowlist_reason="patch touches non-source path: pyproject.toml"))["allowlist"] is True
    assert flags(_facts(allowlist_reason="no patch"))["allowlist"] is False


def test_information_and_ambiguity_are_never_flagged_mechanically() -> None:
    """R0 §2: both are task defects argued from the reconstruction, never counted."""
    row = flags(_facts(first_pass_turn=None))
    assert row["information"] is None and row["ambiguity"] is None


def test_whole_attempt_seconds_comes_from_the_directory_stamp_and_the_record_mtime() -> None:
    """Ruling 8: no new harness clock; the two stamps already exist."""
    name = "selfhost-docs-linter-20260916-013000-500000"
    started = datetime(2026, 9, 16, 1, 30, 0, 500_000, tzinfo=UTC).timestamp()
    assert whole_attempt_seconds(name, 1_000_000.0) == 1_000_000.0 - started


def test_a_directory_name_without_a_stamp_has_no_whole_attempt_seconds() -> None:
    assert whole_attempt_seconds("not-a-stamp", 1_000_000.0) is None
