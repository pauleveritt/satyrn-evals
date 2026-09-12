"""The real composition proof: engine_command_implementer against a real
satyrn-engine deliver subprocess, real git, no mocks. Skipped, not
failed, when the sibling satyrn-engine checkout is not present -- it is
an external dependency this repository does not vendor or require
(ROADMAP.md, "State and dependencies").
"""

import dataclasses
import subprocess
import sys
from pathlib import Path

import pytest

from satyrn_evals.adapters.engine_delivery import (
    engine_command_implementer,
    init_engine_repo,
)
from satyrn_evals.chain_record import (
    AppliedState,
    load_chain_record,
    run_and_record_engine_chain,
)
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import build_packet
from satyrn_evals.route import BudgetState, ValidationOutcome
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


def test_a_failed_engine_validation_stops_the_composed_chain(
    tmp_path: Path,
) -> None:
    """The composed route stops on the engine's ``FAILED`` validation, matching
    ``deliver_chain``'s ``TESTS_FAILED`` stop: the phase rejects (even though
    the grader would have passed) rather than folding a failing candidate into
    the next phase."""
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

    assert [p.step_id for p in record.phases] == ["phase-1-home"]
    first = record.phases[0]
    assert first.accepted is False
    assert first.reason == "engine validation: failed"
    assert first.implementer_mutations is not None
    assert len(first.implementer_mutations) > 0
    assert first.orchestrator_mutations == ()
    assert first.candidate_snapshot_path is not None
    import json as _json
    saved = _json.loads(Path(first.candidate_snapshot_path).read_text())
    assert saved  # real file content, not empty
    # This task's own session.json declares a real self_test_command, so a
    # full run through this route already exercises the harness-run self-test
    # wired into `engine_command_implementer`, not just the offline seam's.
    assert first.self_test_outcome is not None
    assert first.self_test_outcome.ran is True
    assert first.declaration_ledger["self_test_command"] is AppliedState.APPLIED
    # The adapter now passes the packet's turn budget as --turn-limit, so the
    # ledger records it as APPLIED on the engine-composed route; the receipt's
    # budget block is retained alongside validation.
    assert first.declaration_ledger["turn_budget"] is AppliedState.APPLIED
    assert first.declaration_ledger["deadline_seconds"] is AppliedState.DECLARED_NOT_APPLIED
    assert first.budget is not None
    assert first.budget.state is BudgetState.WITHIN
    # The engine's own validation is the authoritative verdict, retained
    # alongside -- never replaced by -- the harness cross-check above, and the
    # reason a phase that would otherwise fold forward stops here.
    assert first.validation is not None
    assert first.validation.outcome is ValidationOutcome.FAILED
    assert first.validation.exit_code != 0


def test_a_passing_self_test_command_runs_against_the_real_candidate_commit(
    tmp_path: Path,
) -> None:
    """The engine seam's own version of HP7's second closed gap: no live
    workspace survives `deliver` (the isolated worktree is deleted on
    success), so the harness materializes the real candidate commit via
    `git archive` before running the declared command against it."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0, harness_root=tmp_path / "harness",
    )
    packet = dataclasses.replace(_packet("phase-1-home"), self_test_command=("true",))

    result = implementer(packet)

    assert result.reported_outcome == "delivered"
    outcome = receipts[-1]["self_test_outcome"]
    assert outcome["ran"] is True
    assert outcome["exit_code"] == 0


def test_a_failing_self_test_command_is_retained_with_its_exit_code(
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
    packet = dataclasses.replace(_packet("phase-1-home"), self_test_command=("false",))

    result = implementer(packet)

    assert result.reported_outcome == "delivered"
    outcome = receipts[-1]["self_test_outcome"]
    assert outcome["ran"] is True
    assert outcome["exit_code"] != 0
    # The engine's own run is the recorded authority; the harness cross-check
    # above is retained separately and cannot override it.
    assert receipts[-1]["code"] == "TESTS_FAILED"
    assert receipts[-1]["validation"] == "failed"
    assert receipts[-1]["validation_exit"] != 0


def test_no_self_test_command_writes_no_outcome_in_the_receipt(
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
    packet = dataclasses.replace(_packet("phase-1-home"), self_test_command=None)

    implementer(packet)

    assert "self_test_outcome" not in receipts[-1]


def test_a_grader_crash_on_phase_two_still_leaves_phase_one_retained(
    tmp_path: Path,
) -> None:
    """The crash-safety property this route was missing: phase 1 passes,
    phase 2's grader raises. Preserve-before-judging means phase 1's
    already-graded decision, and phase 2's real candidate commit's content,
    both survive on disk -- not nothing, which is what waiting until the
    whole chain finished (the prior version) would have left. A passing
    self-test command keeps the engine's validation ``PASSED`` so the
    composed route reaches phase 2 instead of stopping on ``FAILED``."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0, harness_root=tmp_path / "harness",
    )
    output = tmp_path / "chain.json"
    # The route now rejects on a ``FAILED`` engine validation before the
    # grader runs; a trivially-true self-test keeps validation ``PASSED`` so
    # this test still exercises the phase-2 grader crash it is here for.
    spec = dataclasses.replace(
        load_session_spec(TASK), self_test_command=("true",)
    )

    def crashing_grader(step_id: str, ws: Path) -> tuple[str, str]:
        if step_id == "phase-2-board":
            raise RuntimeError("grader exploded")
        return "pass", "scripted pass"

    with pytest.raises(RuntimeError, match="grader exploded"):
        run_and_record_engine_chain(
            TASK, load_manifest(TASK), spec,
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


_EXHAUST_FAKE = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "harness = Path(sys.argv[1])\n"
    "counter = harness / '.phase-counter'\n"
    "index = int(counter.read_text()) if counter.is_file() else 0\n"
    "counter.write_text(str(index + 1))\n"
    "if index == 0:\n"
    "    Path('app.py').write_text('# partial\\n')\n"
    "    time.sleep(3)\n"
    "else:\n"
    "    Path('models.py').write_text('# phase 2\\n')\n"
)


def test_a_deadline_exhausted_phase_is_delivered_but_partial_and_advances_the_base(
    tmp_path: Path,
) -> None:
    """BUDGET_EXHAUSTED is delivered-but-partial: the retained partial
    candidate becomes the next phase's base exactly as OK/TESTS_FAILED do,
    and the receipt's budget block records the exhaustion state."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    harness_root = tmp_path / "harness"
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, "-c", _EXHAUST_FAKE, str(harness_root)],
        timeout=60.0, harness_root=harness_root,
    )
    first = dataclasses.replace(
        _packet("phase-1-home"), deadline_seconds=0.5, self_test_command=("true",),
    )
    second = dataclasses.replace(_packet("phase-2-board"), self_test_command=("true",))

    result_one = implementer(first)
    assert result_one.reported_outcome == "delivered", receipts
    assert result_one.changed_files == ("app.py",)
    assert receipts[0]["code"] == "BUDGET_EXHAUSTED"
    assert receipts[0]["budget"]["state"] == "deadline_exhausted"

    result_two = implementer(second)
    assert result_two.reported_outcome == "delivered", receipts
    assert receipts[1]["code"] == "OK"
    assert receipts[1]["base_commit"] == receipts[0]["candidate_commit"]


def test_a_passed_validation_on_an_exhausted_attempt_is_not_a_completion(
    tmp_path: Path,
) -> None:
    """The chain stops on exhaustion with its own reason even when the
    engine's validation of the partial candidate passes -- a passing suite
    on a partial candidate is not a completion."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    harness_root = tmp_path / "harness"
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, "-c", _EXHAUST_FAKE, str(harness_root)],
        timeout=60.0, harness_root=harness_root,
    )
    spec = dataclasses.replace(
        load_session_spec(TASK), self_test_command=("true",)
    )

    record = run_and_record_engine_chain(
        TASK, load_manifest(TASK), spec,
        implementer, receipts, repo, _grade_pass,
        tmp_path / "chain.json", turn_budget=40, tool_call_budget=60,
        deadline_seconds=0.5,
    )

    assert [p.step_id for p in record.phases] == ["phase-1-home"]
    first = record.phases[0]
    assert first.accepted is False
    assert first.reason == "engine budget exhausted: deadline_exhausted"
    assert first.result.reported_outcome == "delivered"
    assert first.budget is not None
    assert first.budget.state is BudgetState.DEADLINE_EXHAUSTED
    assert first.declaration_ledger["turn_budget"] is AppliedState.APPLIED
    assert first.declaration_ledger["deadline_seconds"] is AppliedState.APPLIED
    assert first.validation is not None
    assert first.validation.outcome is ValidationOutcome.PASSED
