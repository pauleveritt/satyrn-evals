"""The V3 Track B gate: rendered from the close-out rows.

Default tier: ``render_gate`` is pure over the frozen inventory.
"""

import sys
from pathlib import Path

import pytest

from satyrn_evals.claim_closeout import CloseoutRow, closeout_rows

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from publish_gate import (  # noqa: E402  # scripts/ added via sys.path above
    MARKER,
    _write_gate,
    main,
    render_carrier_lag,
    render_gate,
)

FINAL = {"confirmed", "corrected", "not_derivable", "claim_measure_mismatch"}


def test_render_gate_names_every_claim_id_and_its_status() -> None:
    report = render_gate(closeout_rows())
    for row in closeout_rows():
        assert row.claim_id in report
        assert row.status in report


def test_a_not_derivable_row_renders_its_missing_artifact() -> None:
    report = render_gate(closeout_rows())
    for row in closeout_rows():
        if row.status == "not_derivable":
            assert row.missing is not None
            assert row.missing in report


def test_render_gate_summary_tallies_every_status() -> None:
    rows = closeout_rows()
    report = render_gate(rows)
    for status in FINAL:
        assert status in report
    assert f"of {len(rows)} records" in report


def test_a_row_with_no_missing_artifact_renders_an_em_dash() -> None:
    row = CloseoutRow(
        claim_id="c-test",
        level="claim",
        status="confirmed",
        source="x.md",
        carriers=(),
        missing=None,
    )
    report = render_gate((row,))

    assert "| c-test | claim | confirmed | — |" in report


def test_carrier_lag_names_the_none_state_not_silence() -> None:
    assert render_carrier_lag(()) == "\n**Carrier lag:** none.\n"


def test_carrier_lag_lists_each_lagging_carrier() -> None:
    report = render_carrier_lag(("a.md:1", "b.md:2"))

    assert "hard failure" in report
    assert "- a.md:1" in report
    assert "- b.md:2" in report


def test_write_gate_preserves_the_handwritten_suffix(tmp_path: Path) -> None:
    output = tmp_path / "gate.md"
    handwritten = f"{MARKER}\n\n## Reopen decisions\n\nkept by hand.\n"
    output.write_text("old generated\n\n" + handwritten)

    _write_gate(output, "new generated\n", force=False)

    assert output.read_text(encoding="utf-8") == "new generated\n\n" + handwritten


def test_write_gate_refuses_to_clobber_unmarked_handwritten(tmp_path: Path) -> None:
    output = tmp_path / "gate.md"
    output.write_text("old generated\n\n## Reopen decisions\n\nkept by hand.\n")

    with pytest.raises(RuntimeError):
        _write_gate(output, "new generated\n", force=False)


def test_check_returns_nonzero_when_a_carrier_lags(monkeypatch) -> None:
    monkeypatch.setattr("publish_gate.carrier_lag", lambda: ("a.md:1",))

    assert main(["--check"]) == 1


def test_check_returns_zero_when_no_carrier_lags(monkeypatch) -> None:
    monkeypatch.setattr("publish_gate.carrier_lag", lambda: ())

    assert main(["--check"]) == 0
