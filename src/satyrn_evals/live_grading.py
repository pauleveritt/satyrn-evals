"""A live `PhaseGrader` for the engine-composed route: real per-phase
verdicts from the real oracle, fed by real candidate commits -- the piece
HP7's pre-run record named as missing ("this record has not yet named
what plays that role outside the offline route's scripted fixtures").

`SessionGrader.grade_record` grades each checkpoint by copying `base/`
fresh and applying **one** patch -- cumulative from base, never a prior
checkpoint's patch applied on top (`session_grader.py`'s own module
docstring: "copies the base, applies the checkpoint patch"). Under the
engine-composed route, a phase's own receipt names its *predecessor's*
candidate as `base_commit` (fold-forward isolation), not the session's
original base -- so this module diffs every phase's candidate against
`repo`'s own first commit, never against the receipt's `base_commit`,
to produce the cumulative-from-base patch grading expects.
"""

import subprocess
from pathlib import Path

from satyrn_evals.manifest import TaskManifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.route import PhaseGrader
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import SessionSpec
from satyrn_evals.session_record import SessionCode, SessionRecord, StepRecord

#: Grading reads the patch's content, not this digest -- a session
#: record's `prompt_digest` is provenance for offline replay, which does
#: not apply to a patch built fresh from a live commit each call.
_UNUSED_PROMPT_DIGEST = "0" * 64


def _cumulative_diff(repo: Path, initial_commit: str, candidate_commit: str) -> str:
    return subprocess.run(
        ["git", "diff", "--no-color", initial_commit, candidate_commit],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout


def live_session_grader(
    task_dir: Path,
    manifest: TaskManifest,
    spec: SessionSpec,
    repo: Path,
    initial_commit: str,
    receipts: list[dict[str, object]],
    session_dir: Path,
) -> PhaseGrader:
    """`receipts` is the same list `engine_command_implementer` appends
    to -- read here, not owned here. By the time `run_phases` calls the
    returned grader for a step, that step's own receipt is already the
    last entry (the implementer runs, and appends, before grading), so
    `receipts[:n]` always aligns with `spec.steps[:n]` in order.
    """
    overlay = load_overlay(task_dir, manifest)
    session_dir.mkdir(parents=True, exist_ok=True)
    grader = SessionGrader(task_dir=task_dir)

    def grade(step_id: str, ws: Path) -> tuple[str, str]:
        n = len(receipts)
        steps_so_far = spec.steps[:n]
        step_records: list[StepRecord] = []
        for step, receipt in zip(steps_so_far, receipts, strict=True):
            candidate_commit = receipt["candidate_commit"]
            assert isinstance(candidate_commit, str)
            diff = _cumulative_diff(repo, initial_commit, candidate_commit)
            patch_name = f"{step.id}.patch"
            (session_dir / patch_name).write_text(diff)
            step_records.append(
                StepRecord(
                    step_id=step.id,
                    prompt_digest=_UNUSED_PROMPT_DIGEST,
                    outcome="settled",
                    patch_path=patch_name,
                )
            )
        record = SessionRecord(
            version=1,
            task=task_dir.name,
            adapter_command=("engine_command_implementer",),
            base_commit=initial_commit,
            code=SessionCode.COMPLETE,
            steps=tuple(step_records),
        )
        graded = grader.grade_record(record, spec, overlay, session_dir)
        current = next(s for s in graded.steps if s.step_id == step_id)
        verdict = current.feature_verdict or "unavailable"
        return verdict, f"{verdict} from the real grader for {step_id}"

    return grade
