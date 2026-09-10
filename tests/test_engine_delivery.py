"""engine_command_implementer's pure argv construction -- default tier:
nothing here spawns satyrn-engine or git. The real composition proof is
tests/integration/test_engine_delivery.py.
"""

from pathlib import Path

from satyrn_evals.adapters.engine_delivery import build_deliver_argv


def test_build_deliver_argv_omits_base_for_the_first_phase(tmp_path: Path) -> None:
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        base=None, implementer_argv=["pi_implementer", "--model", "m"],
    )
    assert "--base" not in argv


def test_build_deliver_argv_includes_base_for_a_later_phase(tmp_path: Path) -> None:
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        base="abc1234", implementer_argv=["pi_implementer", "--model", "m"],
    )
    assert "--base" in argv
    assert argv[argv.index("--base") + 1] == "abc1234"


def test_build_deliver_argv_preserves_the_implementer_argv_after_separator(
    tmp_path: Path,
) -> None:
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        base=None,
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
        base=None, implementer_argv=["tool"],
    )
    assert argv[0] == "satyrn-engine"
    assert argv[1] == "deliver"
    assert argv[argv.index("--repo") + 1] == str(tmp_path)
    assert argv[argv.index("--timeout") + 1] == "42.5"
    assert str(contract) in argv
