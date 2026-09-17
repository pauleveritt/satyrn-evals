"""The census's pure classification rules. Default tier: synthetic events, no subprocess.

The eight classes of design section 7 are columns a reviewer fills, not values
this module computes (a count without a class does not admit a task, AGENTS.md).
What is computed is the *evidence* each class is argued from, and each flag has
a firing row and a silent row.
"""

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from satyrn_evals.census_classify import (
    CLASSES,
    Facts,
    TurnRow,
    actual_at_line,
    attempt_started,
    flags,
    per_turn,
    whole_attempt_seconds,
    within_32k,
)

# The night driver lives in a dated evidence directory (not an importable
# package), so its allowlist decision is loaded by path as the finishing
# counterfactual's tests load theirs. Loading it spawns nothing; the grade is
# faked per test.
_DRIVER_PATH = Path(__file__).resolve().parents[1] / "evidence" / "2026-09-16-census" / "classify.py"
_DRIVER_SPEC = importlib.util.spec_from_file_location("census_classify_driver", _DRIVER_PATH)
assert _DRIVER_SPEC is not None and _DRIVER_SPEC.loader is not None
driver = importlib.util.module_from_spec(_DRIVER_SPEC)
sys.modules["census_classify_driver"] = driver
_DRIVER_SPEC.loader.exec_module(driver)


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
        code="BUDGET_EXCEEDED", verdict=None, passed_at_line=False, tripped_verdict=None, raised=None,
        length_stops=0, root_searches=0, tool_reported_timeouts=0, first_pass_turn=None,
        first_pass_tokens=None, self_stop_turn=None, allowlist_reason=None,
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


def test_a_tripped_worktree_that_graded_pass_is_not_capability() -> None:
    """Ruling R-5: a pass state the tear-down hid is a finishing/budget case,
    not evidence the cell lacked the capability."""
    row = flags(_facts(tripped_verdict="pass"))
    assert (row["capability"], row["budget"], row["finishing"]) == (False, False, False)


def test_a_tripped_worktree_that_did_not_pass_still_flags_capability() -> None:
    """The sibling: a tripped grade that is not a pass leaves capability on."""
    assert flags(_facts(tripped_verdict="fail"))["capability"] is True
    assert flags(_facts(tripped_verdict="unavailable"))["capability"] is True


def test_a_swallowed_measurement_failure_is_not_capability() -> None:
    """Ruling R-5: a cell that raised measured nothing, so it is not
    capability evidence (the reviewer's class, not a count)."""
    row = flags(_facts(raised="ValueError: no transcript"))
    assert (row["capability"], row["budget"], row["finishing"]) == (False, False, False)


def test_a_cell_without_a_raise_still_flags_capability() -> None:
    """The sibling: no swallowed failure leaves the capability count intact."""
    assert flags(_facts(raised=None))["capability"] is True


def test_a_cell_that_passed_flags_none_of_the_three() -> None:
    row = flags(_facts(
        code="OK", verdict="pass", passed_at_line=True,
        first_pass_turn=8, first_pass_tokens=6000, self_stop_turn=9,
    ))
    assert not any(row[name] for name in ("capability", "budget", "finishing"))


def test_a_length_stop_flags_runaway_and_none_flags_it_silent() -> None:
    assert flags(_facts(length_stops=1))["runaway"] is True
    assert flags(_facts(length_stops=0))["runaway"] is False


def test_a_root_search_or_a_bounded_command_flags_hunting() -> None:
    assert flags(_facts(root_searches=1))["hunting"] is True
    assert flags(_facts(tool_reported_timeouts=1))["hunting"] is True
    assert flags(_facts())["hunting"] is False


def test_a_non_source_path_reason_flags_allowlist() -> None:
    """Ruling R-4: the driver sets this reason only from a filtered grade that
    passed, so the classifier's expression stays a plain substring test."""
    assert flags(_facts(allowlist_reason="filtered pass after removing non-source path(s): pyproject.toml"))["allowlist"] is True
    assert flags(_facts(allowlist_reason="no patch"))["allowlist"] is False
    # No filtered pass means no reason at all: the four unfiltered false
    # positives must read False.
    assert flags(_facts(allowlist_reason=None))["allowlist"] is False


def _diff(path: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        "-x\n"
        "+y\n"
    )


def _driver_cell(tmp_path: Path) -> Any:
    return driver.Cell(
        task="t", night="n", arm="baseline", attempt="000001",
        attempt_dir="t-20260101-000000-000001", folder=tmp_path,
    )


def test_the_filtered_allowlist_grade_honours_ignored_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ruling R-4, plan ruling 3: the filter is the one `ignored_paths` uses.
    A patch whose only non-source file is ignored is not an allowlist case; a
    genuinely voiding non-source path is, when the filtered remainder passes."""
    cell = _driver_cell(tmp_path)
    source = _diff("tools/lint_docs.py")

    def verdict(value: str):
        def fake(task: str, patch: str, root: Path, name: str) -> dict:
            return {"verdict": value, "reason": ""}

        return fake

    monkeypatch.setattr(driver, "_grade", verdict("pass"))
    # `PROVENANCE.md` is in ignored_paths: the grader drops it before its
    # allowlist check, so even though the filtered remainder passes there is
    # no voiding path and no allowlist.
    assert driver._filtered_allowlist_reason(
        cell, source + _diff("PROVENANCE.md"), ("tools/lint_docs.py",), ("PROVENANCE.md",), tmp_path
    ) is None
    # `pyproject.toml` is outside ignored_paths: it voids, and the filtered
    # pass is the evidence.
    reason = driver._filtered_allowlist_reason(
        cell, source + _diff("pyproject.toml"), ("tools/lint_docs.py",), ("PROVENANCE.md",), tmp_path
    )
    assert reason is not None and "non-source path" in reason
    # The other direction on the grade: a voiding path whose filtered patch
    # does not pass is not allowlist evidence.
    monkeypatch.setattr(driver, "_grade", verdict("fail"))
    assert driver._filtered_allowlist_reason(
        cell, source + _diff("pyproject.toml"), ("tools/lint_docs.py",), ("PROVENANCE.md",), tmp_path
    ) is None


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


def test_a_pass_inside_the_line_is_actual_at_the_line() -> None:
    assert actual_at_line(verdict="pass", output_tokens=19_556, turns=40) is True


def test_a_pass_whose_turns_left_the_line_is_not_actual_at_the_line() -> None:
    """Night 1's run-record-gate 275888: OK/pass at turn 55 with 30,444 tokens."""
    assert actual_at_line(verdict="pass", output_tokens=30_444, turns=55) is False


def test_a_pass_whose_tokens_left_the_line_is_not_actual_at_the_line() -> None:
    """Night 1's docs-linter 845472: OK/pass at turn 54 with 38,999 tokens."""
    assert actual_at_line(verdict="pass", output_tokens=38_999, turns=54) is False


def test_a_fail_inside_the_line_is_not_actual_at_the_line() -> None:
    assert actual_at_line(verdict="fail", output_tokens=1_000, turns=3) is False


def test_a_tripped_cell_is_not_actual_at_the_line_whatever_the_tripped_grade() -> None:
    """Ruling 3: the tripped verdict describes the 48k teardown, never a delivery at the line."""
    assert actual_at_line(verdict=None, output_tokens=20_000, turns=30) is False


def test_the_boundary_is_inclusive_on_both_axes() -> None:
    assert actual_at_line(verdict="pass", output_tokens=32_000, turns=48) is True
    assert actual_at_line(verdict="pass", output_tokens=32_001, turns=48) is False
    assert actual_at_line(verdict="pass", output_tokens=32_000, turns=49) is False


def test_the_class_flags_read_the_line_not_the_budget() -> None:
    """Ruling 5: a cell that passed outside the line, holding a pass state inside it,
    is a finishing row -- the same reading the tally uses."""
    row = flags(_facts(verdict="pass", code="OK", passed_at_line=False,
                       first_pass_turn=16, first_pass_tokens=13_809))
    assert (row["finishing"], row["capability"], row["budget"]) == (True, False, False)


def test_a_cell_that_passed_inside_the_line_flags_none_of_the_three() -> None:
    row = flags(_facts(verdict="pass", code="OK", passed_at_line=True,
                       first_pass_turn=16, first_pass_tokens=9_081))
    assert not any(row[name] for name in ("capability", "budget", "finishing"))


def test_attempt_started_is_the_directorys_utc_stamp() -> None:
    from datetime import UTC, datetime

    expected = datetime(2026, 9, 16, 18, 29, 41, 312540, tzinfo=UTC).timestamp()
    assert attempt_started("selfhost-docs-linter-20260916-182941-312540") == expected


def test_a_directory_name_without_a_stamp_has_no_start() -> None:
    assert attempt_started("not-a-stamp") is None
