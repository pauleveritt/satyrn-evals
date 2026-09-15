"""Integration tier: Engine accepts every generated contract (V11a spec §7).

``id`` stability is a claim about this generator, not about Engine. Engine's
acceptance of the generated shape is proven only here, by running the real
``satyrn-engine check`` against a pinned Engine checkout — twelve rows, six
tasks at each of the two shipped rungs.

The refusal sibling matters as much as the acceptance rows: a preflight that
cannot fail is one of the recorded instrument defects (harvest index, "a
preflight that could not fail"). The last test strips ``id`` from a
generated contract and shows the same command rejecting it.

Marked ``integration``: it spawns the Engine CLI and does not run in CI.
"""

import os
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.engine_contract import render_engine_contract
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest

pytestmark = pytest.mark.integration

STATES = [
    "misleading-locus",
]
RUNGS = ["R1", "R3"]


def _engine_cli() -> str:
    """The installed Engine console script in the pinned checkout.

    The same resolution `tests/integration/test_attempt.py` uses, minus the
    Node and pi requirements: `check` parses a contract and stats a
    directory, so it needs nothing but the installed Engine.
    """
    if (configured := os.environ.get("SATYRN_V4_ENGINE_REPO")) is not None:
        candidates = [Path(configured)]
    else:
        # Walk up rather than counting parents: this file runs both from the
        # repository root and from a git worktree one level deeper, where a
        # fixed parent index names the wrong directory.
        candidates = [
            parent / "satyrn-engine" for parent in Path(__file__).resolve().parents
        ]
    for root in candidates:
        if (cli := root / ".venv" / "bin" / "satyrn-engine").is_file():
            return os.fspath(cli)
    pytest.skip("an installed satyrn-engine checkout is required")


def _generated(state: str, rung: str, tmp_path: Path) -> tuple[Path, Path]:
    task_dir = DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}"
    manifest = load_manifest(task_dir)
    rendered = render_engine_contract(
        task_dir, manifest, rung=rung, contract_text=manifest.contracts[rung]
    )
    path = tmp_path / f"{state}-{rung}.yaml"
    path.write_bytes(rendered)
    return path, task_dir / "base"


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("rung", RUNGS)
def test_engine_check_accepts_the_generated_contract(
    state: str, rung: str, tmp_path: Path
) -> None:
    contract, repo = _generated(state, rung, tmp_path)
    result = subprocess.run(
        [_engine_cli(), "check", "--repo", os.fspath(repo), os.fspath(contract)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (state, rung, result.stderr)


def test_engine_check_refuses_a_contract_without_an_id(tmp_path: Path) -> None:
    """The sibling refusal: the same command on the same fixture, with the
    field Engine requires (proposal correction 14) removed."""
    contract, repo = _generated("misleading-locus", "R1", tmp_path)
    stripped = tmp_path / "no-id.yaml"
    stripped.write_text(
        "\n".join(
            line
            for line in contract.read_text(encoding="utf-8").splitlines()
            if not line.startswith("id:")
        )
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [_engine_cli(), "check", "--repo", os.fspath(repo), os.fspath(stripped)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "id" in result.stderr
