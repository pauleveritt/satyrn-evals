"""The census's pure classification rules. Default tier: synthetic events, no subprocess.

The eight classes of design section 7 are columns a reviewer fills, not values
this module computes (a count without a class does not admit a task, AGENTS.md).
What is computed is the *evidence* each class is argued from, and each flag has
a firing row and a silent row.
"""

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from satyrn_evals.census_classify import (
    CLASSES,
    TOKEN_LINE,
    TURN_LINE,
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


def test_the_night_guard_refuses_a_folder_that_holds_another_nights_cells(tmp_path: Path) -> None:
    """Ruling 11: the morning-after-night-2 classify commands must not silently
    overwrite night 1's three same-named committed folders."""
    task_dir = tmp_path / "selfhost-docs-linter"
    task_dir.mkdir()
    (task_dir / "cells.json").write_text(json.dumps({"night": "2026-09-16-census-selfhost-docs-linter"}))
    refusal = driver._overwrite_refusal(tmp_path, {"selfhost-docs-linter"}, "2026-09-17-census-selfhost-docs-linter")
    assert refusal is not None
    assert "2026-09-16-census-selfhost-docs-linter" in refusal
    assert "2026-09-17-census-selfhost-docs-linter" in refusal


def test_the_night_guard_allows_the_same_night_or_a_fresh_folder(tmp_path: Path) -> None:
    """The siblings: a deliberate re-classification of the same night, and a task
    with no existing folder, both write."""
    task_dir = tmp_path / "selfhost-docs-linter"
    task_dir.mkdir()
    (task_dir / "cells.json").write_text(json.dumps({"night": "2026-09-16-census-selfhost-docs-linter"}))
    assert driver._overwrite_refusal(
        tmp_path, {"selfhost-docs-linter"}, "2026-09-16-census-selfhost-docs-linter"
    ) is None
    assert driver._overwrite_refusal(tmp_path, {"a-fresh-task"}, "2026-09-17-census-a-fresh-task") is None


# --- Task 4 fix round 1: cell_span / decode_row / load_decode_log coverage ---

_DECODE_COMPLETION_LINE = (
    "2026-01-01 00:01:00,000 - omlx.server - INFO - [-] - Chat completion: "
    "model=Ornith-1.5-9B-MLX-8bit, 50 tokens in 10.0s (5.0 tok/s), "
    "prompt: 10, finish_reason=tool_calls, max_tokens=1000, request_max_tokens=1000"
)


def _stamped_cell(folder: Path, *, attempt_dir: str = "t-20260101-000000-000001") -> Any:
    return driver.Cell(
        task="t", night="n", arm="baseline", attempt=attempt_dir.rsplit("-", 1)[-1],
        attempt_dir=attempt_dir, folder=folder,
    )


def test_cell_span_reads_the_directory_stamp_and_the_attempt_json_mtime(tmp_path: Path) -> None:
    """Ruling 10's fourth-reason sibling: both stamps present is a clean span."""
    (tmp_path / "attempt.json").write_text("{}")
    cell = _stamped_cell(tmp_path)
    started, ended, reason = driver.cell_span(cell)
    assert reason is None
    assert started == attempt_started(cell.attempt_dir)
    assert ended == (tmp_path / "attempt.json").stat().st_mtime


def test_cell_span_refuses_a_directory_name_without_a_stamp(tmp_path: Path) -> None:
    """Ruling 10's NO_STAMP reason, exercised directly (previously untested)."""
    (tmp_path / "attempt.json").write_text("{}")
    cell = _stamped_cell(tmp_path, attempt_dir="not-a-stamp")
    assert driver.cell_span(cell) == (None, None, driver.cd.NO_STAMP)


def test_cell_span_refuses_a_missing_attempt_json(tmp_path: Path) -> None:
    """Ruling 10's NO_ATTEMPT_JSON reason, exercised directly (previously untested,
    though reachable on night 2 -- `measure` already tolerates an unreadable attempt)."""
    cell = _stamped_cell(tmp_path)  # attempt.json never written
    assert driver.cell_span(cell) == (None, None, driver.cd.NO_ATTEMPT_JSON)


def test_decode_row_reports_the_span_reason_when_the_span_is_unavailable(tmp_path: Path) -> None:
    cell = _stamped_cell(tmp_path)  # no attempt.json -> NO_ATTEMPT_JSON
    log = driver.DecodeLog(completions=[], spans=[])
    assert driver.decode_row(cell, log) == {
        "decode_tok_s": None, "decode_median_tok_s": None, "decode_completions": 0,
        "decode_overlap": None, "decode_reason": driver.cd.NO_ATTEMPT_JSON,
    }


def test_decode_row_reads_the_rate_when_the_span_is_available(tmp_path: Path) -> None:
    """The sibling of the reason case: a real span reads a real rate."""
    (tmp_path / "attempt.json").write_text("{}")
    cell = _stamped_cell(tmp_path)
    started, ended, reason = driver.cell_span(cell)
    assert reason is None
    completion = driver.cd.Completion(ended=started + 100.0, seconds=10.0, tokens=50, prompt=10, max_tokens=100)
    log = driver.DecodeLog(completions=[completion], spans=[(started, ended)])
    row = driver.decode_row(cell, log)
    assert (row["decode_tok_s"], row["decode_completions"], row["decode_overlap"], row["decode_reason"]) == (
        5.0, 1, 1, None,
    )


def test_load_decode_log_reads_every_matching_file_in_name_order(tmp_path: Path) -> None:
    (tmp_path / "server.log").write_text(_DECODE_COMPLETION_LINE + "\n")
    (tmp_path / "attempt.json").write_text("{}")
    cell = _stamped_cell(tmp_path)
    log = driver.load_decode_log(str(tmp_path / "server.log*"), [cell])
    assert len(log.completions) == 1
    assert log.completions[0].tokens == 50


def test_load_decode_log_spans_come_from_the_whole_night_not_a_filtered_selection(tmp_path: Path) -> None:
    """FINDING 2: a --cell-filtered re-run must still report the full night's
    decode_overlap. `load_decode_log` is given the night's whole cell set by
    `main`, never the `--cell`-narrowed `selected` list."""
    (tmp_path / "server.log").write_text(_DECODE_COMPLETION_LINE + "\n")
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "attempt.json").write_text("{}")
    (dir_b / "attempt.json").write_text("{}")
    cell_a = _stamped_cell(dir_a, attempt_dir="t-20260101-000000-000001")
    cell_b = _stamped_cell(dir_b, attempt_dir="t-20260101-000000-500000")
    started_a, ended_a, _ = driver.cell_span(cell_a)

    # An unfiltered run: both cells contribute a span.
    full = driver.load_decode_log(str(tmp_path / "server.log*"), [cell_a, cell_b])
    assert len(full.spans) == 2
    assert driver.cd.span_overlap(full.spans, started_a, ended_a) == 2

    # The regression this guards against: if `load_decode_log` were given only
    # a `--cell`-filtered selection (as `main` did before this fix), the same
    # cell's decode_overlap would silently undercount the sharing.
    filtered_only = driver.load_decode_log(str(tmp_path / "server.log*"), [cell_a])
    assert driver.cd.span_overlap(filtered_only.spans, started_a, ended_a) == 1
    assert driver.cd.span_overlap(filtered_only.spans, started_a, ended_a) < driver.cd.span_overlap(
        full.spans, started_a, ended_a
    )


# --- Task 5 whole-path review fix round ---


def test_missing_evidence_is_not_actual_at_the_line() -> None:
    """S5-1: `_empty_evidence()` feeds `actual_at_line` an unavailable reading, not a
    zero one. Zero tokens and zero turns both sit inside the 32k/48 line, so a
    parse failure must not silently manufacture a pass at the line."""
    assert actual_at_line(verdict="pass", output_tokens=None, turns=None) is False


def test_a_real_zero_reading_is_still_actual_at_the_line() -> None:
    """The sibling: a cell that genuinely passed at turn 0 with 0 tokens (not an
    unavailable reading) is still actual at the line -- the fix distinguishes
    "unavailable" from "zero", it does not forbid zero."""
    assert actual_at_line(verdict="pass", output_tokens=0, turns=0) is True


def test_the_empty_evidence_block_states_unavailable_not_zero() -> None:
    """S5-1: the row a parse failure produces must say the evidence was
    unavailable, not print zero as though it had been measured."""
    empty = driver._empty_evidence()
    assert (empty["output_tokens"], empty["turns"]) == (None, None)


def test_a_cell_with_unreadable_evidence_never_reads_as_actual_at_the_line(tmp_path: Path) -> None:
    """S5-1, end to end through `_no_reading`: an `_empty_audit` row -- the shape a
    swallowed audit failure produces -- must never read `actual_32k = True`."""
    cell = driver.Cell(
        task="t", night="n", arm="baseline", attempt="000001",
        attempt_dir="t-20260101-000000-000001", folder=tmp_path,
    )
    audit_row = driver._empty_audit(cell, {"code": "OK", "verdict": "pass"})
    reading = driver._no_reading(audit_row, raised="RuntimeError: boom")
    assert reading["actual"] is False


def test_the_pre_registered_line_constants_are_pinned_to_the_committed_instrument() -> None:
    """S5-3: `actual_at_line` reads `TOKEN_LINE`/`TURN_LINE`, `trigger.within_budget`
    reads `counterfactual.py`'s `TOKEN_BUDGET`/`TURN_BUDGET`. They agree today but
    nothing pins them, and `counterfactual.py` may not be touched (Ruling 18) --
    so the pin lives here, on the package side."""
    assert TOKEN_LINE == driver.cf.TOKEN_BUDGET
    assert TURN_LINE == driver.cf.TURN_BUDGET


def test_a_cell_whose_span_is_null_still_counts_toward_other_cells_overlap(tmp_path: Path) -> None:
    """S5-7: a cell that cannot contribute a span (one of Ruling 10's four reasons)
    must not simply vanish from every other cell's `decode_overlap` -- it shared
    the machine even though its own window is unknown."""
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    (good_dir / "attempt.json").write_text("{}")
    good_cell = driver.Cell(
        task="t", night="n", arm="baseline", attempt="000001",
        attempt_dir="t-20260101-000000-000001", folder=good_dir,
    )
    # No attempt.json in this one -> NO_ATTEMPT_JSON, a null span.
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad_cell = driver.Cell(
        task="t", night="n", arm="baseline", attempt="000002",
        attempt_dir="t-20260101-000000-500000", folder=bad_dir,
    )
    started, ended, reason = driver.cell_span(good_cell)
    assert reason is None
    log_without_fix_context = driver.load_decode_log(str(tmp_path / "server.log*"), [good_cell, bad_cell])
    overlap = driver.decode_row(good_cell, log_without_fix_context)["decode_overlap"]
    # Only `good_cell` contributes a real span (1), but `bad_cell` shared the
    # machine and must still be accounted for rather than silently dropped.
    assert overlap == 2


def test_a_night_with_no_unspannable_cells_is_unaffected() -> None:
    """The sibling of S5-7: when every cell has a clean span, nothing changes."""
    assert driver.cd.span_overlap([(0.0, 100.0)], 0.0, 100.0) == 1


def test_the_overwrite_refusal_runs_before_any_cell_is_measured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S6-1: an operator who forgets `--out` on the morning after must be refused
    before paying for hours of replay and grading, not after measuring every cell."""
    out = tmp_path / "out"
    task_dir = out / "t"
    task_dir.mkdir(parents=True)
    (task_dir / "cells.json").write_text(json.dumps({"night": "some-other-night"}))

    cell = driver.Cell(
        task="t", night="n", arm="baseline", attempt="000001",
        attempt_dir="t-20260101-000000-000001", folder=tmp_path,
    )
    monkeypatch.setattr(driver, "select", lambda night, record, only=(): [cell])
    monkeypatch.setattr(driver, "cells", lambda night, record: [cell])
    monkeypatch.setattr(driver, "stamp", lambda argv, night: {"night": "this-night", "evals_commit": "x",
                                                               "evals_dirty": False, "command": "x",
                                                               "tz_offset": "+0000"})
    measured: list[int] = []

    def _fake_measure(*a: object, **k: object) -> dict:
        measured.append(1)
        return {"task": "t", "attempt": "000001", "code": "OK", "own_green_turn": None,
                "pass_turn": None, "run1": {"change": "none"}, "run2": {"change": "none"}, "raised": None}

    monkeypatch.setattr(driver, "measure", _fake_measure)

    grade_root = tmp_path / "grades"
    rc = driver.main([
        "--night", str(tmp_path), "--record", str(tmp_path / "record.json"),
        "--out", str(out), "--grade-root", str(grade_root),
        "--server-log", str(tmp_path / "no-such-server.log*"),
    ])
    assert rc == 2
    assert measured == []


def test_the_overwrite_refusal_still_writes_when_the_night_is_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sibling of S6-1: a fresh --out still measures and writes."""
    out = tmp_path / "out"
    cell = driver.Cell(
        task="t", night="n", arm="baseline", attempt="000001",
        attempt_dir="t-20260101-000000-000001", folder=tmp_path,
    )
    monkeypatch.setattr(driver, "select", lambda night, record, only=(): [cell])
    monkeypatch.setattr(driver, "cells", lambda night, record: [cell])
    monkeypatch.setattr(driver, "stamp", lambda argv, night: {"night": "this-night", "evals_commit": "x",
                                                               "evals_dirty": False, "command": "x",
                                                               "tz_offset": "+0000"})
    fake_row = {"task": "t", "attempt": "000001", "code": "OK", "own_green_turn": None,
                "pass_turn": None, "run1": {"change": "none"}, "run2": {"change": "none"}, "raised": None,
                "actual_32k": False, "actual_48k": False, "unmeasured": []}
    monkeypatch.setattr(driver, "measure", lambda *a, **k: fake_row)
    monkeypatch.setattr(driver, "table", lambda rows, header: "table\n")
    monkeypatch.setattr(driver, "tally_table", lambda rows: "tally\n")
    monkeypatch.setattr(driver, "classes", lambda rows, header: "classes\n")

    grade_root = tmp_path / "grades"
    rc = driver.main([
        "--night", str(tmp_path), "--record", str(tmp_path / "record.json"),
        "--out", str(out), "--grade-root", str(grade_root),
        "--server-log", str(tmp_path / "no-such-server.log*"),
    ])
    assert rc == 0
    assert (out / "t" / "cells.json").is_file()


def test_the_night_guard_refuses_a_folder_with_outputs_but_no_cellsjson(tmp_path: Path) -> None:
    """S6-2: the refusal keyed only on `cells.json` would let a folder holding
    `table.md`/`classes.md` (no `cells.json`) be overwritten without complaint."""
    task_dir = tmp_path / "selfhost-docs-linter"
    task_dir.mkdir()
    (task_dir / "table.md").write_text("stale table\n")
    refusal = driver._overwrite_refusal(tmp_path, {"selfhost-docs-linter"}, "2026-09-17-census-selfhost-docs-linter")
    assert refusal is not None
    assert "selfhost-docs-linter" in refusal


def test_the_night_guard_still_allows_a_folder_with_neither_file(tmp_path: Path) -> None:
    """The sibling of S6-2: a folder with no prior outputs at all is still clear
    to write."""
    task_dir = tmp_path / "selfhost-docs-linter"
    task_dir.mkdir()
    assert driver._overwrite_refusal(
        tmp_path, {"selfhost-docs-linter"}, "2026-09-17-census-selfhost-docs-linter"
    ) is None
