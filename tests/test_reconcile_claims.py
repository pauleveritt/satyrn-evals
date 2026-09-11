"""The reconciliation report: rendered from the ledger, sources checked.

Default tier: `render_report` is pure; the `--check` path is exercised
against a temporary root.
"""

import sys
from pathlib import Path

from satyrn_evals.claim_inventory import ClaimRecord
from satyrn_evals.phase_ledger import PhaseCounts, PhaseLedger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from reconcile_claims import (  # noqa: E402  # scripts/ added via sys.path above
    AttemptSpec,
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
