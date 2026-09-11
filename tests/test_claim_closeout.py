"""The V3 close-out audit: one status per record, no lagging carrier.

Default tier: pure over the frozen inventory and repository paths.
"""

from pathlib import Path

from satyrn_evals.claim_closeout import carrier_lag, closeout_rows, quote_drift
from satyrn_evals.claim_inventory import ClaimRecord

ROOT = Path(__file__).resolve().parent.parent
FINAL = {"confirmed", "corrected", "not_derivable", "claim_measure_mismatch"}


def test_every_record_carries_exactly_one_final_status() -> None:
    rows = closeout_rows()
    assert len(rows) == 20
    assert all(row.status in FINAL for row in rows)


def test_every_not_derivable_row_names_the_missing_artifact() -> None:
    rows = closeout_rows()
    for row in rows:
        if row.status == "not_derivable":
            assert row.missing, f"{row.claim_id} is not_derivable with no missing artifact"


def test_every_carrier_path_exists() -> None:
    assert carrier_lag(root=ROOT) == ()


def test_a_missing_carrier_path_is_reported(tmp_path) -> None:
    record = ClaimRecord(
        id="x",
        quote="6 of 18",
        source="claim_inventory.py",
        carriers=("carrier.md",),
        level="claim",
        measure="completion_rate",
        population="18 Engine attempts",
    )

    assert "carrier.md" in carrier_lag(records=(record,), root=tmp_path)


def test_quote_drift_lists_a_carrier_that_dropped_the_figure(tmp_path) -> None:
    record = ClaimRecord(
        id="x",
        quote="6 of 18",
        source="claim_inventory.py",
        carriers=("carrier.md",),
        level="claim",
        measure="completion_rate",
        population="18 Engine attempts",
    )
    (tmp_path / "carrier.md").write_text("this carrier paraphrased and dropped it")

    assert "carrier.md" in quote_drift(records=(record,), root=tmp_path)
