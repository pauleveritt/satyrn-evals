"""The diagnostic Summary: counts-only tally over attempt cells.

A cell is (attempt directory name, record, parsed receipt dict or None).
Visible-task summaries carry cells + oracle_visibility but no contamination
section; hidden-task summaries additionally tally contamination outcomes
beside the verdict counts, with graded = flagged + clean + unmeasured.
"""

import dataclasses
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.summary import (
    AttemptCell,
    Summary,
    absent_pathology,
    compute_summary,
    write_summary,
)
from satyrn_evals.verdict import Verdict

_CODES = frozenset(code.value for code in AttemptCode)
_VERDICTS = frozenset(v.value for v in Verdict)


def make_record(
    code: AttemptCode,
    verdict: Verdict | None,
    *,
    command_exit: int | None = 0,
    timeout: float = 123.0,
) -> AttemptRecord:
    outcome = AttemptOutcome.ATTEMPTED if verdict is not None else AttemptOutcome.REFUSED
    attempted = verdict is not None
    return AttemptRecord(
        version=1,
        outcome=outcome,
        code=code,
        message="test",
        task="format_number",
        command=("fake",),
        command_exit=command_exit,
        patch_path="patch.diff" if attempted else None,
        transcript_path="transcript.txt" if attempted else None,
        patch_digest="a" * 64 if attempted else None,
        transcript_digest="b" * 64 if attempted else None,
        verdict=verdict,
        receipt_path="receipt.json" if attempted else None,
        timeout=timeout,
        workspace_base_sha="c" * 40,
    )


def _cell(
    name: str,
    code: AttemptCode = AttemptCode.OK,
    verdict: Verdict | None = Verdict.PASS,
    receipt: dict | None = None,
) -> tuple[str, AttemptRecord, dict | None]:
    record = make_record(code=code, verdict=verdict)
    return (name, record, receipt)


def _compute(
    cells: Sequence[AttemptCell],
    *,
    oracle_visibility: str = "visible",
    pathology: dict[str, dict] | None = None,
) -> Summary:
    """compute_summary over pure-tally cells with honest absent blocks.

    These tests never place transcripts on disk, so every cell's honest
    pathology block is `absent`. Tests that exercise the pathology
    contract itself call compute_summary directly with explicit blocks.
    """
    if pathology is None:
        pathology = absent_pathology(cells)
    return compute_summary(
        cells, oracle_visibility=oracle_visibility, pathology=pathology
    )


def _receipt_dict(
    checks: tuple[tuple[str, str], ...] = (("grader_content_in_patch", "clean"),),
) -> dict:
    return {
        "contamination": {
            "visibility": "hidden",
            "checks": [
                {"check": c, "outcome": o, "evidence": []} for c, o in checks
            ],
        }
    }


def test_summary_round_trip_and_tally(tmp_path: Path) -> None:
    summary = _compute(
        [("task-1", make_record(AttemptCode.OK, Verdict.PASS), None)],
        oracle_visibility="visible",
    )
    path = tmp_path / "summary.json"
    write_summary(path, summary)
    data = json.loads(path.read_text())
    assert data["n"] == 1 and data["attempted"] == 1 and data["refused"] == 0
    assert data["code_counts"][AttemptCode.OK.value] == 1
    assert data["verdict_counts"][Verdict.PASS.value] == 1
    assert data["timeouts"] == 0
    assert data["cells"] == ["task-1"]
    assert data["oracle_visibility"] == "visible"
    assert "contamination" not in data


def test_compute_summary_all_refused_is_the_sibling() -> None:
    summary = _compute(
        [
            ("task-1", make_record(AttemptCode.NO_PATCH, None), None),
            (
                "task-2",
                make_record(AttemptCode.COMMAND_TIMEOUT, None, command_exit=None),
                None,
            ),
        ],
        oracle_visibility="visible",
    )
    assert summary.n == 2 and summary.attempted == 0 and summary.refused == 2
    assert summary.code_counts[AttemptCode.NO_PATCH.value] == 1
    assert summary.timeouts == 1


def test_compute_summary_tallies_verdicts_over_attempted_only() -> None:
    summary = _compute(
        [
            ("task-1", make_record(AttemptCode.OK, Verdict.PASS), None),
            ("task-2", make_record(AttemptCode.OK, Verdict.FAIL), None),
            ("task-3", make_record(AttemptCode.NO_PATCH, None), None),
        ],
        oracle_visibility="visible",
    )
    assert summary.attempted == 2 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 1
    assert summary.verdict_counts[Verdict.FAIL.value] == 1
    assert summary.verdict_counts[Verdict.UNAVAILABLE.value] == 0


def test_summary_names_cells_and_visibility() -> None:
    summary = _compute(
        [_cell("task-1"), _cell("task-2")], oracle_visibility="visible"
    )
    assert summary.cells == ["task-1", "task-2"]
    assert summary.oracle_visibility == "visible"
    assert summary.contamination is None


def test_hidden_summary_counts_and_invariant() -> None:
    cells = [
        _cell("task-1", receipt=_receipt_dict()),
        _cell(
            "task-2",
            verdict=Verdict.FAIL,
            receipt=_receipt_dict((("grader_content_in_patch", "flagged"),)),
        ),
        _cell("task-3", receipt={}),  # pre-V7 receipt: no key
        _cell("task-4", code=AttemptCode.NO_PATCH, verdict=None, receipt=None),  # refused
    ]
    summary = _compute(cells, oracle_visibility="hidden")
    assert summary.contamination == {
        "graded": 3,
        "flagged": 1,
        "clean": 1,
        "unmeasured": 1,
    }
    assert summary.n == 4 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 2  # denominators untouched


def test_denominators_unchanged_by_contamination_outcomes() -> None:
    verdicts = [Verdict.PASS, Verdict.FAIL, Verdict.UNAVAILABLE]
    clean = [_cell(f"t-{i}", verdict=v) for i, v in enumerate(verdicts)]
    flagged = [
        _cell(
            f"t-{i}",
            verdict=v,
            receipt=_receipt_dict((("grader_content_in_patch", "flagged"),)),
        )
        for i, v in enumerate(verdicts)
    ]
    a = _compute(clean, oracle_visibility="visible")
    b = _compute(flagged, oracle_visibility="hidden")
    assert (
        a.n,
        a.attempted,
        a.refused,
        a.code_counts,
        a.verdict_counts,
        a.timeouts,
    ) == (
        b.n,
        b.attempted,
        b.refused,
        b.code_counts,
        b.verdict_counts,
        b.timeouts,
    )


def test_summary_invariant_refuses_bad_tally() -> None:
    with pytest.raises(ValueError, match="flagged \\+ clean \\+ unmeasured"):
        Summary(
            n=1,
            attempted=1,
            refused=0,
            code_counts={c.value: 0 for c in AttemptCode},
            verdict_counts={v.value: 0 for v in Verdict},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="hidden",
            cells=["t-1"],
            pathology={"t-1": {"measured": False, "reason": "absent"}},
            contamination={"graded": 2, "flagged": 1, "clean": 1, "unmeasured": 1},
        )


def test_summary_invariant_refuses_bad_key_set() -> None:
    with pytest.raises(ValueError, match="exactly graded/flagged/clean/unmeasured"):
        Summary(
            n=1,
            attempted=1,
            refused=0,
            code_counts={c.value: 0 for c in AttemptCode},
            verdict_counts={v.value: 0 for v in Verdict},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="hidden",
            cells=["t-1"],
            pathology={"t-1": {"measured": False, "reason": "absent"}},
            contamination={"graded": 1, "flagged": 1, "clean": 0, "bogus": 0},
        )


def test_write_summary_omits_contamination_when_visible(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    write_summary(path, _compute([_cell("task-1")], oracle_visibility="visible"))
    data = json.loads(path.read_text())
    assert "contamination" not in data
    assert data["task"] == "format_number"
    assert data["command"] == ["fake"]
    assert data["timeout"] == 123.0
    # pathology is always on the wire (V10 spec §4), even for visible runs
    assert data["pathology"] == {
        "task-1": {"measured": False, "reason": "absent"}
    }


def test_write_summary_includes_contamination_when_hidden(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    summary = _compute(
        [_cell("task-1", receipt=_receipt_dict())], oracle_visibility="hidden"
    )
    write_summary(path, summary)
    data = json.loads(path.read_text())
    assert data["contamination"] == {
        "graded": 1,
        "flagged": 0,
        "clean": 1,
        "unmeasured": 0,
    }


def test_summary_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Summary(
            n=-1,
            attempted=0,
            refused=0,
            code_counts={c: 0 for c in _CODES},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            pathology={},
            contamination=None,
        )
    with pytest.raises(ValueError, match="attempted \\+ refused"):
        Summary(
            n=2,
            attempted=0,
            refused=0,
            code_counts={c: 0 for c in _CODES},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            pathology={},
            contamination=None,
        )
    with pytest.raises(ValueError, match="one key per"):
        Summary(
            n=0,
            attempted=0,
            refused=0,
            code_counts={"NOPE": 0},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=0,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            pathology={},
            contamination=None,
        )
    with pytest.raises(ValueError, match="timeouts must equal"):
        Summary(
            n=0,
            attempted=0,
            refused=0,
            code_counts={c: 0 for c in _CODES},
            verdict_counts={v: 0 for v in _VERDICTS},
            timeouts=1,
            task="format_number",
            command=["fake"],
            timeout=123.0,
            oracle_visibility="visible",
            cells=[],
            pathology={},
            contamination=None,
        )


def test_summary_names_its_arm_from_the_records() -> None:
    cells = [
        ("t-1", make_record(AttemptCode.OK, Verdict.PASS), None),
        ("t-2", make_record(AttemptCode.OK, Verdict.FAIL), None),
    ]
    summary = _compute(cells, oracle_visibility="visible")
    assert summary.task == "format_number"
    assert summary.command == ["fake"]
    assert summary.timeout == 123.0


def test_compute_summary_refuses_cells_without_a_timeout() -> None:
    record = dataclasses.replace(make_record(AttemptCode.OK, Verdict.PASS), timeout=None)
    with pytest.raises(ValueError, match="timeout"):
        _compute([("t-1", record, None)], oracle_visibility="visible")


def test_compute_summary_refuses_empty_cells() -> None:
    with pytest.raises(ValueError, match="at least one cell"):
        _compute([], oracle_visibility="visible")


def test_compute_summary_refuses_mixed_identity() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, command=("other",))
    with pytest.raises(ValueError, match="command"):
        _compute([("t-1", a, None), ("t-2", b, None)], oracle_visibility="visible")


def test_compute_summary_refuses_mixed_task_on_a_later_cell() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, task="other-task")
    with pytest.raises(ValueError, match="mixed tasks"):
        _compute([("t-1", a, None), ("t-2", b, None)],
                        oracle_visibility="visible")


def test_compute_summary_refuses_a_later_cell_without_a_timeout() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, timeout=None)
    with pytest.raises(ValueError, match="has no recorded timeout"):
        _compute([("t-1", a, None), ("t-2", b, None)],
                        oracle_visibility="visible")


def test_compute_summary_refuses_mixed_timeouts() -> None:
    a = make_record(AttemptCode.OK, Verdict.PASS)
    b = dataclasses.replace(a, timeout=456.0)
    with pytest.raises(ValueError, match="mixed timeouts"):
        _compute([("t-1", a, None), ("t-2", b, None)],
                        oracle_visibility="visible")


def test_summary_pathology_requires_every_cell_key() -> None:
    cells = [_cell("t-1"), _cell("t-2")]
    with pytest.raises(ValueError, match="pathology"):
        compute_summary(
            cells,
            oracle_visibility="visible",
            pathology={"t-1": {"measured": False, "reason": "absent"}},
        )


def test_summary_pathology_refuses_blocks_without_measured() -> None:
    cells = [_cell("t-1")]
    with pytest.raises(ValueError, match="boolean measured"):
        compute_summary(
            cells,
            oracle_visibility="visible",
            pathology={"t-1": {"reason": "absent"}},
        )


def test_summary_pathology_writes_through() -> None:
    cells = [_cell("t-1")]
    pathology = {"t-1": {"measured": False, "reason": "absent"}}
    summary = compute_summary(cells, oracle_visibility="visible", pathology=pathology)
    assert summary.pathology == pathology


def test_summary_pathology_refuses_non_dict_block() -> None:
    """The short-circuit's non-dict branch: a block that is not a dict."""
    cells = [_cell("t-1")]
    with pytest.raises(ValueError, match="boolean measured"):
        compute_summary(
            cells,
            oracle_visibility="visible",
            # deliberately ill-typed: the validation must refuse it
            pathology={"t-1": "junk"},  # type: ignore[assignment]
        )


def test_summary_pathology_follows_cell_order_not_input_order() -> None:
    """compute_summary reorders the block to the summary's cell order.

    In-order callers (all of them today) cannot distinguish a reorder from
    a passthrough; an out-of-order input pins the reorder (spec §4: keys
    follow the summary's cell order) and that the values followed their
    keys.
    """
    cells = [_cell("t-1"), _cell("t-2")]
    blocks = {
        "t-2": {"measured": False, "reason": "absent"},
        "t-1": {"measured": True, "tool_calls": {"read": 1}},
    }
    summary = compute_summary(cells, oracle_visibility="visible", pathology=blocks)
    assert list(summary.pathology) == summary.cells
    assert summary.pathology["t-1"] == blocks["t-1"]
    assert summary.pathology["t-2"] == blocks["t-2"]


# --- V11a Task 5: the summary names the rung and the digest ---
#
# Two runs at R1 and R3 with the same command otherwise differ only by the
# prompt echoed in the transcript (spec §5). The summary refuses a mixed
# batch exactly as it refuses mixed tasks, commands and timeouts.

_R1_DIGEST = "1" * 64
_R3_DIGEST = "3" * 64


def _rung_cell(
    name: str, *, rung: str | None, digest: str | None
) -> AttemptCell:
    record = dataclasses.replace(
        make_record(AttemptCode.OK, Verdict.PASS),
        rung=rung,
        contract_digest=digest,
    )
    return (name, record, None)


def test_summary_carries_the_rung_and_digest_of_its_cells() -> None:
    summary = _compute(
        [
            _rung_cell("t-1", rung="R1", digest=_R1_DIGEST),
            _rung_cell("t-2", rung="R1", digest=_R1_DIGEST),
        ]
    )
    assert summary.rung == "R1"
    assert summary.contract_digest == _R1_DIGEST


def test_summary_over_legacy_cells_carries_explicit_unknowns() -> None:
    """Sibling success: a pre-V11a batch summarizes with both fields null."""
    summary = _compute(
        [
            _rung_cell("t-1", rung=None, digest=None),
            _rung_cell("t-2", rung=None, digest=None),
        ]
    )
    assert summary.rung is None
    assert summary.contract_digest is None


def test_compute_summary_refuses_mixed_rungs() -> None:
    with pytest.raises(ValueError, match="mixed rungs"):
        _compute(
            [
                _rung_cell("t-1", rung="R1", digest=_R1_DIGEST),
                _rung_cell("t-2", rung="R3", digest=_R3_DIGEST),
            ]
        )


def test_compute_summary_refuses_mixed_digests_at_the_same_rung() -> None:
    """The rung label is an authoring claim; the digest is the text itself.
    Equal labels over different bytes is exactly the confusion to refuse."""
    with pytest.raises(ValueError, match="mixed contract digests"):
        _compute(
            [
                _rung_cell("t-1", rung="R1", digest=_R1_DIGEST),
                _rung_cell("t-2", rung="R1", digest=_R3_DIGEST),
            ]
        )


def test_summary_json_carries_both_new_fields() -> None:
    summary = _compute([_rung_cell("t-1", rung="R1", digest=_R1_DIGEST)])
    data = dataclasses.asdict(summary)
    assert data["rung"] == "R1"
    assert data["contract_digest"] == _R1_DIGEST
