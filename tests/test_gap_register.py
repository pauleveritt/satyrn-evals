"""The V3 engine gap register: exploratory candidates, no published figures.

Default tier: ``GAP_REGISTER`` and ``render_gap_register`` are pure; the
classifier-backed observations are exercised over synthetic events.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_gap_register import (  # noqa: E402  # scripts/ added via sys.path above
    GAP_REGISTER,
    observations_for_attempts,
    render_gap_register,
)

COMMITTED_MEASURES = {
    "destructive_edit",
    "restoration",
    "self_test_outcome",
    "verification_claim",
    "turn_cost",
}


def _start(call_id: str, tool: str, args: Mapping[str, object]) -> dict:
    return {
        "type": "tool_execution_start",
        "toolCallId": call_id,
        "toolName": tool,
        "args": dict(args),
    }


def _end(call_id: str, tool: str, text: str) -> dict:
    return {
        "type": "tool_execution_end",
        "toolCallId": call_id,
        "toolName": tool,
        "isError": False,
        "result": {"content": [{"type": "text", "text": text}]},
    }


def _edit(call_id: str, old: str, new: str) -> tuple[dict, dict]:
    args = {"path": "app.py", "edits": [{"oldText": old, "newText": new}]}
    return _start(call_id, "edit", args), _end(call_id, "edit", "applied")


def test_the_register_has_at_least_one_candidate() -> None:
    assert len(GAP_REGISTER) >= 1


def test_every_candidate_measure_is_a_committed_classifier_or_turn_cost() -> None:
    for row in GAP_REGISTER:
        assert row.measure in COMMITTED_MEASURES, row.id


def test_every_row_renders_exploratory_with_population_and_proposed_change() -> None:
    report = render_gap_register({})

    assert "exploratory" in report
    for row in GAP_REGISTER:
        assert row.candidate in report
        assert row.population in report
        assert row.proposed_change in report
        assert row.population, row.id
        assert row.proposed_change, row.id


def test_no_rendered_row_contains_the_word_confirmed() -> None:
    report = render_gap_register({})

    assert "confirmed" not in report


def test_a_missing_observation_renders_not_measured_never_guessed() -> None:
    report = render_gap_register({})

    assert "not measured" in report


def test_a_supplied_observation_replaces_the_fallback() -> None:
    report = render_gap_register(
        {
            "g-verification-honesty": (
                "1 of 8 attempts show a false verification claim (exploratory)"
            )
        }
    )

    assert "1 of 8 attempts show a false verification claim" in report


def test_observations_for_attempts_counts_over_the_supplied_population() -> None:
    """A destructive replacement followed by a restoration of the same block,
    plus a passing self-test."""
    remove_start, remove_end = _edit("c1", "route\n", "")
    restore_start, restore_end = _edit("c2", "", "route\n")
    self_test_start = _start("c3", "run_self_test", {})
    self_test_end = _end("c3", "run_self_test", "exit code 0\n1 passed")
    events: Sequence[Mapping[str, object]] = [
        remove_start,
        remove_end,
        restore_start,
        restore_end,
        self_test_start,
        self_test_end,
    ]

    observed = observations_for_attempts((events,))

    assert (
        observed["g-restoration-churn"]
        == "1 content-changing, 1 re-adding removed content, 0/0 undecidable "
        "of 1 (exploratory)"
    )
    assert (
        observed["g-self-test-friction"]
        == "0 last model-invoked self-test failed, 1 passed, 0 undecidable "
        "of 1 (exploratory; not the independent final-candidate check)"
    )
    assert "exploratory" in observed["g-verification-honesty"]


def test_the_committed_register_document_exists_and_is_exploratory() -> None:
    doc = (
        Path(__file__).resolve().parent.parent
        / "docs/current/phase-v-engine-gap-register.md"
    )
    text = doc.read_text(encoding="utf-8")

    assert "exploratory" in text
    assert "confirmed" not in text
    for row in GAP_REGISTER:
        assert row.candidate in text
        assert row.population in text
        assert row.proposed_change in text
