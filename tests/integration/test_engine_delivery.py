"""The real composition proof: engine_command_implementer against a real
satyrn-engine deliver subprocess, real git, no mocks. Skipped, not
failed, when the sibling satyrn-engine checkout is not present -- it is
an external dependency this repository does not vendor or require
(ROADMAP.md, "State and dependencies").
"""

import subprocess
import sys
from pathlib import Path

import pytest

from satyrn_evals.adapters.engine_delivery import (
    engine_command_implementer,
    init_engine_repo,
)
from satyrn_evals.chain_record import run_and_record_engine_chain
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import build_packet
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
FAKE_IMPLEMENTER = Path(__file__).parent / "fake_implementer.py"
SIBLING_ENGINE_BIN = (
    Path.home() / "projects/pauleveritt/satyrn-engine/.venv/bin/satyrn-engine"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not SIBLING_ENGINE_BIN.is_file(),
        reason="sibling satyrn-engine checkout not found at the conventional path",
    ),
]


def _packet(step_id: str):
    return build_packet(
        TASK, load_manifest(TASK), load_session_spec(TASK), step_id,
        base_revision="3e6607e533792ab0", turn_budget=40, tool_call_budget=60,
    )


def _grade_pass(step_id: str, workspace: Path) -> tuple[str, str]:
    return "pass", f"scripted pass for {step_id}"


def test_two_phases_compose_a_real_fold_forward_chain(tmp_path: Path) -> None:
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)

    implementer, receipts = engine_command_implementer(
        repo,
        str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0,
        harness_root=tmp_path / "harness",
    )

    result_one = implementer(_packet("phase-1-home"))
    assert result_one.reported_outcome == "delivered", receipts
    result_two = implementer(_packet("phase-2-board"))
    assert result_two.reported_outcome == "delivered", receipts

    assert len(receipts) == 2
    assert receipts[0]["base_commit"] != receipts[1]["base_commit"]
    tree = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", receipts[1]["candidate_commit"]],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.split()
    changed_by_phase_one = set(receipts[0]["changed_paths"])
    changed_by_phase_two = set(receipts[1]["changed_paths"])
    assert changed_by_phase_one <= set(tree)  # phase 1's files survive into phase 2
    assert changed_by_phase_two <= set(tree)


def test_a_refused_phase_leaves_the_next_bases_on_its_predecessor(
    tmp_path: Path,
) -> None:
    """No-partial-chain's sibling for this seam: a NO_CHANGES phase must
    not silently become the next phase's base."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)

    implementer, receipts = engine_command_implementer(
        repo,
        str(SIBLING_ENGINE_BIN),
        [sys.executable, "-c", "pass"],  # touches nothing -> NO_CHANGES
        timeout=60.0,
        harness_root=tmp_path / "harness",
    )
    result = implementer(_packet("phase-1-home"))
    assert result.reported_outcome == "refused"
    assert receipts[0]["code"] == "NO_CHANGES"


def test_run_and_record_engine_chain_retains_a_real_two_phase_chain(
    tmp_path: Path,
) -> None:
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0, harness_root=tmp_path / "harness",
    )

    record = run_and_record_engine_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        implementer, receipts, repo, _grade_pass,
        tmp_path / "chain.json", turn_budget=40, tool_call_budget=60,
    )

    assert len(record.phases) >= 1
    first = record.phases[0]
    assert first.accepted is True
    assert first.implementer_mutations is not None
    assert len(first.implementer_mutations) > 0
    assert first.orchestrator_mutations == ()
    assert first.candidate_snapshot_path is not None
    import json as _json
    saved = _json.loads(Path(first.candidate_snapshot_path).read_text())
    assert saved  # real file content, not empty
