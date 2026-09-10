"""HP5.3 -- the ledger, and the difference between zero and unobserved."""

import pytest

from satyrn_evals.attribution import Mutation, attribute

A = "0" * 64
B = "1" * 64


def _b(step: str, boundary: str, snap: dict[str, str]):
    return (step, boundary, snap)


def test_a_phase_splits_its_two_windows() -> None:
    ledger = attribute(
        [
            _b("p1", "before_handoff", {}),
            _b("p1", "after_handoff", {"app.py": A}),
            _b("p1", "chain_end", {"app.py": A, "README.md": A}),
        ],
        {},
    )
    (phase,) = ledger.phases
    assert phase.implementer == (Mutation("app.py", "created"),)
    assert phase.orchestrator == (Mutation("README.md", "created"),)


def test_the_orchestrator_window_runs_to_the_next_handoff() -> None:
    ledger = attribute(
        [
            _b("p1", "before_handoff", {}),
            _b("p1", "after_handoff", {"app.py": A}),
            _b("p2", "before_handoff", {"app.py": B}),
            _b("p2", "after_handoff", {"app.py": B}),
            _b("p2", "chain_end", {"app.py": B}),
        ],
        {},
    )
    first, second = ledger.phases
    assert first.orchestrator == (Mutation("app.py", "modified"),)
    assert second.implementer == ()
    assert second.orchestrator == ()


def test_totals_recompute_from_the_phases() -> None:
    """Computed on read, never accumulated as the phases run."""
    ledger = attribute(
        [
            _b("p1", "before_handoff", {}),
            _b("p1", "after_handoff", {"a.py": A, "b.py": A}),
            _b("p2", "before_handoff", {"a.py": A, "b.py": A, "c.py": A}),
            _b("p2", "after_handoff", {"a.py": A, "b.py": A, "c.py": A}),
            _b("p2", "chain_end", {"a.py": A, "b.py": A, "c.py": A}),
        ],
        {},
    )
    assert ledger.implementer_mutations == sum(
        len(p.implementer) for p in ledger.phases
    )
    assert ledger.implementer_mutations == 2
    assert ledger.orchestrator_mutations == 1


def test_a_window_never_observed_is_unobserved_not_zero() -> None:
    """The spec's fifth acceptance. A `0` that means "we did not look" is the
    detached-worker gap in a new place."""
    ledger = attribute([_b("p1", "before_handoff", {})], {})
    (phase,) = ledger.phases
    assert phase.implementer is None
    assert phase.orchestrator is None
    assert ledger.implementer_mutations is None
    assert ledger.unobserved_phases == ("p1",)


def test_an_observed_zero_is_zero() -> None:
    """The sibling of the case above, differing only in whether the window
    was closed. Without this the check above passes on any empty ledger."""
    ledger = attribute(
        [
            _b("p1", "before_handoff", {"app.py": A}),
            _b("p1", "after_handoff", {"app.py": A}),
            _b("p1", "chain_end", {"app.py": A}),
        ],
        {},
    )
    (phase,) = ledger.phases
    assert phase.implementer == ()
    assert ledger.implementer_mutations == 0
    assert ledger.unobserved_phases == ()


def test_one_unobserved_phase_poisons_the_total() -> None:
    """A total summed across an unobserved window would understate the chain
    and read as a finding about the run."""
    ledger = attribute(
        [
            _b("p1", "before_handoff", {}),
            _b("p1", "after_handoff", {"a.py": A}),
            _b("p2", "before_handoff", {"a.py": A}),
        ],
        {},
    )
    assert ledger.phases[0].implementer == (Mutation("a.py", "created"),)
    assert ledger.phases[1].implementer is None
    assert ledger.implementer_mutations is None
    assert ledger.unobserved_phases == ("p2",)


def test_phases_keep_their_handoff_order() -> None:
    ledger = attribute(
        [
            _b("z", "before_handoff", {}),
            _b("z", "after_handoff", {}),
            _b("a", "before_handoff", {}),
            _b("a", "after_handoff", {}),
            _b("a", "chain_end", {}),
        ],
        {},
    )
    assert [p.step_id for p in ledger.phases] == ["z", "a"]


def test_an_unknown_boundary_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown boundary"):
        attribute([_b("p1", "midway", {})], {})


def test_a_known_boundary_from_the_same_shape_is_accepted() -> None:
    """The sibling of the refusal above."""
    assert attribute([_b("p1", "before_handoff", {})], {}).phases[0].step_id == "p1"


def test_a_window_opened_twice_is_refused() -> None:
    """Silently keeping the later snapshot would report a number computed
    from an arbitrary half of the evidence."""
    with pytest.raises(ValueError, match="opened twice"):
        attribute(
            [_b("p1", "before_handoff", {}), _b("p1", "before_handoff", {})], {}
        )


def test_a_window_closed_twice_is_refused() -> None:
    with pytest.raises(ValueError, match="closed twice"):
        attribute(
            [
                _b("p1", "before_handoff", {}),
                _b("p1", "after_handoff", {}),
                _b("p1", "after_handoff", {}),
            ],
            {},
        )


def test_two_different_steps_open_without_refusal() -> None:
    """The sibling of both refusals above."""
    ledger = attribute(
        [_b("p1", "before_handoff", {}), _b("p2", "before_handoff", {})], {}
    )
    assert [p.step_id for p in ledger.phases] == ["p1", "p2"]
