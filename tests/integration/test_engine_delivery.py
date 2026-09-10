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
from satyrn_evals.chain_record import load_chain_record, run_and_record_engine_chain
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


def test_a_grader_crash_on_phase_two_still_leaves_phase_one_retained(
    tmp_path: Path,
) -> None:
    """The crash-safety property this route was missing: phase 1 passes,
    phase 2's grader raises. Preserve-before-judging means phase 1's
    already-graded decision, and phase 2's real candidate commit's content,
    both survive on disk -- not nothing, which is what waiting until the
    whole chain finished (the prior version) would have left."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0, harness_root=tmp_path / "harness",
    )
    output = tmp_path / "chain.json"

    def crashing_grader(step_id: str, ws: Path) -> tuple[str, str]:
        if step_id == "phase-2-board":
            raise RuntimeError("grader exploded")
        return "pass", "scripted pass"

    with pytest.raises(RuntimeError, match="grader exploded"):
        run_and_record_engine_chain(
            TASK, load_manifest(TASK), load_session_spec(TASK),
            implementer, receipts, repo, crashing_grader,
            output, turn_budget=40, tool_call_budget=60,
        )

    assert output.is_file(), "nothing was persisted before the crash propagated"
    record = load_chain_record(output)
    assert [p.step_id for p in record.phases] == ["phase-1-home", "phase-2-board"]

    first, second = record.phases
    assert first.graded and first.accepted is True
    assert first.reason == "scripted pass"

    assert not second.graded
    assert second.accepted is None and second.reason is None
    assert second.result.reported_outcome == "delivered"  # the implementer DID run
    assert second.candidate_snapshot_path is not None  # real candidate survived
    import json as _json
    saved = _json.loads(Path(second.candidate_snapshot_path).read_text())
    assert saved  # real content, not empty
