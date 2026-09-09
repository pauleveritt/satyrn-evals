"""HP2's integration half: the real oracle, and the real executable seam.

Two things live here rather than in the default tier, and neither by choice:

* **The fixture-named verdicts.** `known-good.patch` and `known-broken.patch`
  differ by one line -- a timezone-aware default factory against a naive one
  -- so only the oracle tells them apart, and the oracle spawns. Asserting a
  fixture-named verdict offline would make "names the fixture" a label on a
  scripted result.
* **The executable seam.** `command_implementer` is what a live run drives.
  Proving the callable and the executable make the same decisions is what
  keeps the two from drifting apart while both stay green.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import load_manifest, resolve_task
from satyrn_evals.overlay import load_overlay
from satyrn_evals.route import ROUTE_SCENARIO, command_implementer, run_phases
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.session_record import SessionCode, SessionRecord, StepRecord

pytestmark = pytest.mark.integration

TASK_NAME = "agentclinic-session-phased"
FAKE = Path(__file__).parent / "fake_implementer.py"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}

#: The accept/reject sequence both tiers assert. The default-tier route test
#: reaches it through the callable; this file reaches it through a real
#: process. A divergence here is the seams drifting.
EXPECTED_SEQUENCE = [(step, True) for step in ROUTE_SCENARIO]


def _record_over(session_dir: Path, task_dir: Path, patches: list[str]) -> SessionRecord:
    spec = load_session_spec(task_dir)
    steps = []
    for step, name in zip(spec.steps, patches, strict=True):
        shutil.copy(task_dir / "fixtures" / f"{name}.patch", session_dir / f"{name}.patch")
        steps.append(
            StepRecord(
                step_id=step.id,
                prompt_digest="d" * 64,
                outcome="settled",
                patch_path=f"{name}.patch",
            )
        )
    return SessionRecord(
        version=1,
        task=TASK_NAME,
        adapter_command=("fixture",),
        base_commit="b" * 40,
        code=SessionCode.COMPLETE,
        steps=tuple(steps),
    )


def _grade(tmp_path: Path, patches: list[str]):
    task_dir = resolve_task(TASK_NAME)
    manifest = load_manifest(task_dir)
    return SessionGrader(task_dir=task_dir).grade_record(
        _record_over(tmp_path, task_dir, patches),
        load_session_spec(task_dir),
        load_overlay(task_dir, manifest),
        tmp_path,
    )


def test_the_known_good_fixture_is_accepted_at_its_final_checkpoint(
    tmp_path: Path,
) -> None:
    """Named fixture, real oracle. `known-good.patch` is byte-identical to
    `checkpoint-3.patch`, verified with `cmp`, so one fixture set serves the
    progression and the witness."""
    graded = _grade(tmp_path, ["checkpoint-1", "checkpoint-2", "known-good"])
    assert [s.feature_verdict for s in graded.steps] == ["pass", "pass", "pass"]
    # Preservation is `None` for every step, and that is correct rather than a
    # gap: this task starts from an empty skeleton, so `session.json` declares
    # `base_preservation_selectors: []` -- there is no base behaviour to
    # preserve. Asserting "pass" here would have been asserting a measurement
    # that was never taken.
    assert all(s.preservation_verdict is None for s in graded.steps)


def test_the_known_broken_fixture_is_rejected_at_its_final_checkpoint(
    tmp_path: Path,
) -> None:
    """The refusal half of the evidence floor, named by fixture.

    `known-broken.patch` differs from `known-good.patch` by one line: a
    `datetime.now` default factory with no timezone.
    """
    graded = _grade(tmp_path, ["checkpoint-1", "checkpoint-2", "known-broken"])
    assert graded.steps[-1].feature_verdict == "fail"


def test_the_executable_seam_makes_the_same_decisions_as_the_callable(
    tmp_path: Path,
) -> None:
    """The drift guard. A real process writes the result document; the route
    reads it through the same parser the default tier tests."""
    task_dir = resolve_task(TASK_NAME)

    def grader(step_id: str, workspace: Path) -> tuple[str, str]:
        return "pass", f"scripted pass for {step_id}"

    decisions = run_phases(
        task_dir,
        load_manifest(task_dir),
        load_session_spec(task_dir),
        command_implementer([sys.executable, str(FAKE)], tmp_path),
        tmp_path,
        grader,
        base_revision="3e6607e533792ab0",
        **BUDGETS,
    )
    assert [(d.step_id, d.accepted) for d in decisions] == EXPECTED_SEQUENCE
    assert (tmp_path / "models.py").is_file()
    assert "phase-3" in (tmp_path / "app.py").read_text()


def test_the_executable_refuses_to_write_outside_the_declared_scope(
    tmp_path: Path,
) -> None:
    """The sibling of the seam test: the executable enforces scope itself, so
    a permissive fake cannot hide a route defect."""
    (tmp_path / ".satyrn-packet.json").write_text(
        '{"writable_paths": ["nothing"], "objective": "x"}'
    )
    (tmp_path / ".phase-counter").write_text("0")
    proc = subprocess.run(
        [sys.executable, str(FAKE)],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "SATYRN_HANDOFF_PACKET": str(tmp_path / ".satyrn-packet.json"),
            "SATYRN_IMPLEMENTER_RESULT": str(tmp_path / ".satyrn-result.json"),
        },
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "outside declared scope" in proc.stderr
    assert not (tmp_path / ".satyrn-result.json").exists()
