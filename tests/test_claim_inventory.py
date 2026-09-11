"""The claim inventory: frozen records, valid sources, one table.

Default tier: pure, no filesystem read beyond the repository's own paths.
"""

from pathlib import Path

from satyrn_evals.claim_inventory import (
    INVENTORY,
    ClaimRecord,
    render_table,
    validate_sources,
)

ROOT = Path(__file__).resolve().parent.parent


def test_every_cited_source_path_exists() -> None:
    assert validate_sources(ROOT) == ()


def test_ids_are_unique() -> None:
    ids = [record.id for record in INVENTORY]
    assert len(ids) == len(set(ids))


def test_a_record_defaults_to_unreconciled() -> None:
    """The default is the pre-reconciliation state; V1/V2 then settle records
    in place, so the test pins the default rather than the whole tuple."""
    record = ClaimRecord(
        id="example",
        quote="x",
        source="ROADMAP.md",
        carriers=(),
        level="unit",
        measure="turns",
        population="none",
    )
    assert record.status == "unreconciled"


def test_both_levels_are_present() -> None:
    levels = {record.level for record in INVENTORY}
    assert levels == {"unit", "claim"}


def test_the_inventory_holds_twenty_records_seven_unit_thirteen_claim() -> None:
    assert len(INVENTORY) == 20
    assert sum(1 for record in INVENTORY if record.level == "unit") == 7
    assert sum(1 for record in INVENTORY if record.level == "claim") == 13


def test_the_table_names_every_record_and_its_population() -> None:
    table = render_table(
        (
            ClaimRecord(
                id="example",
                quote="6 of 18",
                source="docs/current/te6-explain-and-decide.md",
                carriers=(),
                level="claim",
                measure="completion_rate",
                population="18 Engine attempts",
            ),
        )
    )
    assert "example" in table
    assert "6 of 18" in table
    assert "18 Engine attempts" in table


def test_validate_sources_names_a_missing_path(tmp_path: Path) -> None:
    record = ClaimRecord(
        id="missing",
        quote="x",
        source="does/not/exist.md",
        carriers=("also/missing.md",),
        level="unit",
        measure="turns",
        population="none",
    )
    missing = validate_sources(tmp_path, records=(record,))
    assert "does/not/exist.md" in missing
    assert "also/missing.md" in missing
