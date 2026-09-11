"""The reconciliation report: rendered from the ledger, sources checked.

Default tier: `render_report` is pure; the `--check` path is exercised
against a temporary root.
"""

import json
import sys
from collections.abc import Sequence
from pathlib import Path

from satyrn_evals.claim_inventory import INVENTORY, ClaimRecord
from satyrn_evals.claim_measures import ClaimMeasure
from satyrn_evals.phase_ledger import PhaseCounts, PhaseLedger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from reconcile_claims import (  # noqa: E402  # scripts/ added via sys.path above
    AttemptSpec,
    _count_measure,
    _phase4_reaching_engine_attempts,
    measure_inventory_for_run,
    render_report,
    validate_root,
)


def _spec(label: str, arm: str) -> AttemptSpec:
    return AttemptSpec(label=label, run_dir=label, arm=arm)


def test_render_report_names_every_attempt_and_its_state() -> None:
    ledger = PhaseLedger(
        "measured",
        None,
        (PhaseCounts("phase-1-home", 6, 3, 1, "fail"),),
    )
    report = render_report(((_spec("engine-01", "engine"), ledger),))
    assert "engine-01" in report
    assert "phase-1-home" in report
    assert "6" in report


def test_render_report_carries_a_refusal_as_a_word_not_a_zero() -> None:
    ledger = PhaseLedger("undecidable", "2 session blocks against 4 declared phases", ())
    report = render_report(((_spec("engine-02", "engine"), ledger),))
    assert "undecidable" in report
    assert "2 session blocks against 4 declared phases" in report
    assert "| — | — | — |" in report


def test_the_committed_document_carries_the_current_inventory() -> None:
    from satyrn_evals.claim_inventory import render_table

    doc = (Path(__file__).resolve().parent.parent / "docs/current/phase-v-claim-inventory.md").read_text()
    assert render_table() in doc


def test_render_report_records_the_revision_and_artifact_digests() -> None:
    """V1 Currency rule: the HEAD revision and each artifact's sha256 are
    recorded before measuring."""
    ledger = PhaseLedger(
        "measured", None, (PhaseCounts("phase-1-home", 6, 3, 1, "fail"),)
    )
    report = render_report(
        ((_spec("engine-01", "engine"), ledger),),
        head="a" * 40,
        digests={"x/transcript.jsonl": "b" * 64},
        runs_root="/runs",
    )
    assert "a" * 40 in report
    assert "b" * 64 in report
    assert "x/transcript.jsonl" in report
    assert "**Runs root:** `/runs`" in report


def test_validate_root_names_a_missing_citation(tmp_path: Path) -> None:
    record = ClaimRecord(
        id="missing",
        quote="x",
        source="nope.md",
        carriers=(),
        level="unit",
        measure="turns",
        population="none",
    )
    assert "nope.md" in validate_root(tmp_path, records=(record,))


def _count(results: Sequence[str]) -> ClaimMeasure:
    return _count_measure(
        claim_id="c-test",
        measure="measure",
        population="population",
        results=results,
        published="13 of 15",
        action="action description",
        gap="gap description",
    )


def test_count_measure_all_yes_is_yes() -> None:
    measure = _count(["yes", "yes", "yes"])

    assert measure.result == "yes"
    assert measure.evidence[0] == (
        "derived 3 yes, 0 undecidable, of 3 action description "
        "(published 13 of 15)"
    )


def test_count_measure_all_no_is_no() -> None:
    measure = _count(["no", "no"])

    assert measure.result == "no"
    assert measure.evidence[0] == (
        "derived 0 yes, 0 undecidable, of 2 action description "
        "(published 13 of 15)"
    )


def test_count_measure_a_single_unreadable_member_is_undecidable() -> None:
    """An unreadable member is not folded into a decided `yes` count."""
    measure = _count(["yes", "no", "undecidable"])

    assert measure.result == "undecidable"
    assert measure.evidence[0] == (
        "derived 1 yes, 1 undecidable, of 3 action description "
        "(published 13 of 15)"
    )


def test_count_measure_an_empty_set_is_no() -> None:
    """Degenerate fold: no members measured and none unreadable.

    The wired path never reaches this branch with an empty set --
    `measure_inventory_for_run` reports an unenumerable population as
    `undecidable` before it calls `_count_measure`.
    """
    measure = _count([])

    assert measure.result == "no"
    assert measure.evidence[0] == (
        "derived 0 yes, 0 undecidable, of 0 action description "
        "(published 13 of 15)"
    )


def test_phase4_enumeration_reads_chain_records_not_run_dir_names(
    tmp_path: Path,
) -> None:
    def write_chain(run_dir: str, phase_ids: Sequence[str] | None = None) -> None:
        run = tmp_path / run_dir
        run.mkdir()
        (run / "chain.json").write_text(
            json.dumps(
                {"phases": [{"step_id": phase} for phase in phase_ids or ()]}
            ),
            encoding="utf-8",
        )

    write_chain(
        "reaches-phase-4",
        ["phase-1-home", "phase-2-board", "phase-3-add", "phase-4-resolve-reopen"],
    )
    write_chain("stops-at-phase-3", ["phase-1-home", "phase-2-board", "phase-3-add"])
    malformed = tmp_path / "malformed"
    malformed.mkdir()
    (malformed / "chain.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / "no-chain").mkdir()

    assert tuple(
        spec.run_dir for spec in _phase4_reaching_engine_attempts(tmp_path)
    ) == ("reaches-phase-4",)


def test_measure_inventory_marks_an_absent_transcript_undecidable(
    tmp_path: Path,
) -> None:
    """An absent Engine transcript is an unreadable member, never an empty
    event list folded silently into the denominator."""
    measures = measure_inventory_for_run(
        INVENTORY,
        tmp_path,
        (AttemptSpec("engine-absent", "engine-absent", "engine"),),
    )
    destructive = next(
        measure
        for measure in measures
        if measure.claim_id == "c-destroyed-13-of-15"
    )

    assert destructive.result == "undecidable"
    assert destructive.evidence[0] == (
        "derived 0 yes, 1 undecidable, of 1 phase-4-reaching Engine attempts "
        "applied a destructive edit (published 13 of 15)"
    )
