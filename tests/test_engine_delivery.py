"""engine_command_implementer's pure argv construction -- default tier:
nothing here spawns satyrn-engine or git. The real composition proof is
tests/integration/test_engine_delivery.py.
"""

from pathlib import Path

import pytest

from satyrn_evals.adapters.engine_delivery import (
    build_deliver_argv,
    deliver_result_from_receipt,
)
from satyrn_evals.errors import RouteError


def _argv(tmp_path: Path, **kw: object) -> list[str]:
    defaults = {
        "base": None,
        "implementer_argv": ["pi_implementer", "--model", "m"],
        "turn_budget": 40,
    }
    return build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        **{**defaults, **kw},  # type: ignore[arg-type]
    )


def test_build_deliver_argv_omits_base_for_the_first_phase(tmp_path: Path) -> None:
    assert "--base" not in _argv(tmp_path)


def test_build_deliver_argv_includes_base_for_a_later_phase(tmp_path: Path) -> None:
    argv = _argv(tmp_path, base="abc1234")
    assert "--base" in argv
    assert argv[argv.index("--base") + 1] == "abc1234"


def test_build_deliver_argv_preserves_the_implementer_argv_after_separator(
    tmp_path: Path,
) -> None:
    argv = _argv(
        tmp_path,
        implementer_argv=["pi_implementer", "--model", "m", "--tools", "read"],
    )
    separator = argv.index("--")
    assert argv[separator + 1:] == [
        "pi_implementer", "--model", "m", "--tools", "read",
    ]


def test_build_deliver_argv_names_repo_timeout_and_contract(tmp_path: Path) -> None:
    contract = tmp_path / "contract.yaml"
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, contract, 42.5,
        base=None, implementer_argv=["tool"], turn_budget=40,
    )
    assert argv[0] == "satyrn-engine"
    assert argv[1] == "deliver"
    assert argv[argv.index("--repo") + 1] == str(tmp_path)
    assert argv[argv.index("--timeout") + 1] == "42.5"
    assert str(contract) in argv


def test_build_deliver_argv_passes_the_packet_turn_budget(tmp_path: Path) -> None:
    argv = _argv(tmp_path, turn_budget=20)
    assert argv[argv.index("--turn-limit") + 1] == "20"


def test_build_deliver_argv_omits_a_deadline_when_none_is_declared(
    tmp_path: Path,
) -> None:
    """A packet with no deadline produces no ``--deadline-seconds``."""
    assert "--deadline-seconds" not in _argv(tmp_path)


def test_build_deliver_argv_passes_a_declared_deadline(tmp_path: Path) -> None:
    argv = _argv(tmp_path, deadline_seconds=30.0)
    assert argv[argv.index("--deadline-seconds") + 1] == "30.0"


def test_build_deliver_argv_refuses_a_nonsensical_turn_budget(tmp_path: Path) -> None:
    with pytest.raises(RouteError, match="turn_budget"):
        _argv(tmp_path, turn_budget=0)


@pytest.mark.parametrize("bad", [0, -1, True, float("nan"), float("inf")])
def test_build_deliver_argv_refuses_a_nonsensical_deadline(
    tmp_path: Path, bad: object
) -> None:
    with pytest.raises(RouteError, match="deadline_seconds"):
        _argv(tmp_path, deadline_seconds=bad)


def _receipt(code: str, changed_paths: object) -> dict[str, object]:
    return {
        "code": code,
        "message": f"{code} message",
        "changed_paths": changed_paths,
    }


def test_an_ok_receipt_is_a_delivered_candidate() -> None:
    result = deliver_result_from_receipt(
        _receipt("OK", ["app.py", "tests/test_app.py"])
    )
    assert result.reported_outcome == "delivered"
    assert result.changed_files == ("app.py", "tests/test_app.py")


def test_a_tests_failed_receipt_is_still_a_delivered_candidate() -> None:
    """The engine's TESTS_FAILED code names a retained failing candidate,
    not a refusal: files were produced and committed, and the authoritative
    validation verdict is carried on the phase record, not here."""
    result = deliver_result_from_receipt(
        _receipt("TESTS_FAILED", ["app.py"])
    )
    assert result.reported_outcome == "delivered"
    assert result.changed_files == ("app.py",)


def test_a_budget_exhausted_receipt_is_delivered_but_partial() -> None:
    """The engine's BUDGET_EXHAUSTED code names a retained partial candidate,
    not a refusal: the phase's files were committed before the budget fired,
    and the authoritative exhaustion state is carried on the receipt's
    ``budget`` block, read back by ``run_and_record_engine_chain``."""
    result = deliver_result_from_receipt(
        _receipt("BUDGET_EXHAUSTED", ["app.py"])
    )
    assert result.reported_outcome == "delivered"
    assert result.changed_files == ("app.py",)


def test_a_refusal_receipt_names_its_reason() -> None:
    """Sibling of the delivered cases: a receipt with no candidate still
    reports refused, with the engine's message as the reason."""
    result = deliver_result_from_receipt(_receipt("NO_CHANGES", []))
    assert result.reported_outcome == "refused"
    assert result.changed_files == ()
    assert result.message == "NO_CHANGES message"


def test_an_ok_receipt_without_changed_paths_is_refused() -> None:
    """The refusal sibling in the other direction: OK with no files is not
    a delivered candidate (delivering nothing is a refusal)."""
    result = deliver_result_from_receipt(_receipt("OK", []))
    assert result.reported_outcome == "refused"
    assert result.changed_files == ()
