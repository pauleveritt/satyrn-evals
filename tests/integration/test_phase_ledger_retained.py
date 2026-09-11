"""The retained attempts, recomputed to their published per-phase values.

Integration because these artifacts live under ``~/satyrn-smokes``. No model
and no subprocess; a missing artifact is a loud skip, never a silent pass.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from reconcile_claims import (  # noqa: E402  # scripts/ added via sys.path above
    ATTEMPTS,
    AttemptSpec,
    ledger_for,
)

pytestmark = pytest.mark.integration

RUNS_ROOT = Path(os.path.expanduser("~/satyrn-smokes"))

#: label -> published per-phase turns, copied from each attempt's own result
#: document (never derived here). The round-2 rows are
#: `docs/current/te4-phase4-guardrail-reverification-round2-result.md:21-22`.
PUBLISHED: dict[str, tuple[int, ...]] = {
    "baseline-01": (7, 22, 6, 8),
    "baseline-02": (9, 8, 9, 6),
    "engine-01": (6, 8, 10, 23),
    "engine-02": (6, 7, 9, 23),
    "round2-01": (6, 8, 8, 21),
    "round2-02": (6, 8, 7, 28),
    "recurrence-01": (6, 8, 11, 19),
    "recurrence-03": (6, 8, 8, 14),
}


@pytest.mark.parametrize("spec", ATTEMPTS, ids=lambda spec: spec.label)
def test_retained_attempt_recomputes_to_its_published_per_phase_turns(spec) -> None:
    if not (RUNS_ROOT / spec.run_dir).exists():
        pytest.skip(f"retained attempt absent: {RUNS_ROOT / spec.run_dir}")
    ledger = ledger_for(spec, RUNS_ROOT)
    assert ledger.state == "measured", ledger.reason
    assert tuple(cell.turns for cell in ledger.cells) == PUBLISHED[spec.label]


def test_a_missing_attempt_is_a_named_absent_state_not_a_zero(tmp_path: Path) -> None:
    """Sibling to the success above: `ledger_for` on an absent artifact
    returns the named refusal state with no cells, never a zero. This
    exercises the production path, not a dataclass literal."""
    spec = AttemptSpec(label="missing", run_dir="does-not-exist", arm="engine")

    ledger = ledger_for(spec, tmp_path)

    assert ledger.state == "absent"
    assert ledger.reason
    assert ledger.cells == ()
