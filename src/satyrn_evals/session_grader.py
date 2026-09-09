"""Offline session grading: retained checkpoint patches only, never live.

Runs only after the adapter is torn down. The feature grader copies the
base, applies the checkpoint patch, overlays the grader-only files, and
runs the cumulative hidden selection; the preservation grader runs the
declared public selectors at every captured checkpoint without the
overlay (per-checkpoint since 2026-09-08 -- last-checkpoint-only grading
could not see a base regression that a later step repaired). A scope violation skips that checkpoint's hidden grading but is
a candidate failure, never infrastructure unavailability (2026-09-01
spec, Offline grading).
"""

import dataclasses
import os
from pathlib import Path

from satyrn_evals.errors import SatyrnError
from satyrn_evals.grade import grade
from satyrn_evals.overlay import OverlaySpec
from satyrn_evals.patch import within_source
from satyrn_evals.receipt import Receipt
from satyrn_evals.session_manifest import SessionSpec
from satyrn_evals.session_record import (
    SessionCode,
    SessionRecord,
    StepRecord,
)
from satyrn_evals.verdict import Verdict

# The value recorded when preservation is not meaningful for a
# checkpoint: the captured patch changed a protected public test, so
# grading against the model's own edited test would be circular. It is
# distinct from pass/fail/unavailable — the machinery worked; the
# measurement is definitionally void for that checkpoint.
PRESERVATION_INVALID = "invalid"


def _protected_public_test_files(spec: SessionSpec) -> frozenset[str]:
    """The public-test files the preservation selectors execute.

    Each base-preservation selector is a pytest node id whose module part
    (before ``::``) is the file that must stay pristine for preservation
    to mean anything.
    """
    files = {selector.split("::", 1)[0] for selector in spec.base_preservation_selectors}
    return frozenset(module for module in files if module)


def _touches_protected(step: StepRecord, protected: frozenset[str]) -> bool:
    """Whether this checkpoint's patch touched a declared preservation file."""
    return any(
        within_source(violation, tuple(protected))
        for violation in step.scope_violations
    )


def _preservation_dirs(protected: frozenset[str]) -> tuple[str, ...]:
    """The directories the declared preservation files live in."""
    return tuple(
        sorted({os.path.dirname(path) for path in protected if os.path.dirname(path)})
    )


def _blocks_feature_grading(step: StepRecord, protected: frozenset[str]) -> bool:
    """Whether this checkpoint's out-of-scope writes should cost it a verdict.

    A scope violation remains a candidate failure (2026-09-01 spec), and a
    write outside the declared areas still skips hidden grading. The single
    exemption, added 2026-09-08: a file the solver ADDED alongside the
    preservation tests, which is not itself one of them.

    Why only that: over twelve sessions, 9 of 12 wrote something under
    `tests/`, because writing tests is what a coding agent does. Two of those
    were new files, and losing a checkpoint's verdict over them measures the
    task's phrasing rather than the solver. Editing a declared preservation
    file stays disqualifying -- that is the circularity the guard exists for --
    and a write anywhere else stays disqualifying too.
    """
    if _touches_protected(step, protected):
        return True
    allowed = _preservation_dirs(protected)
    return any(
        not (allowed and within_source(violation, allowed))
        for violation in step.scope_violations
    )


def _cumulative_selectors(spec: SessionSpec, index: int) -> tuple[str, ...]:
    """The ordered union of hidden selectors introduced through step ``index``."""
    selectors: list[str] = []
    for step in spec.steps[: index + 1]:
        selectors.extend(step.new_feature_selectors)
    return tuple(selectors)


@dataclasses.dataclass(frozen=True, slots=True)
class SessionGrader:
    """Grades retained checkpoint patches after confirmed teardown."""

    task_dir: Path

    def grade_record(
        self,
        record: SessionRecord,
        spec: SessionSpec,
        overlay: OverlaySpec,
        session_dir: Path,
    ) -> SessionRecord:
        """Fill verdicts and receipt paths into a captured record."""
        receipt_dir = session_dir / "receipts"
        receipt_dir.mkdir(exist_ok=True)
        graded: list[StepRecord] = []
        unavailable = False
        protected = _protected_public_test_files(spec)
        for index, step in enumerate(record.steps):
            current = step
            if step.patch_path is None or _blocks_feature_grading(step, protected):
                # Hidden grading is skipped only for contact with a DECLARED
                # preservation file (2026-09-08, narrowed from "any scope
                # violation"). Measured over twelve sessions, 9 of 12 wrote
                # something under `tests/` -- writing tests is what a coding
                # agent does -- and every one lost its feature verdict to a
                # guard aimed at circularity it could not cause: feature
                # grading runs against the overlay, materialised over the
                # workspace, so a model-authored file elsewhere cannot forge a
                # hidden pass. `scope_violations` still records every
                # out-of-scope path and the session code is unchanged; only
                # what blocks a verdict has narrowed.
                pass
            else:
                patch_path = session_dir / step.patch_path
                cumulative = _cumulative_selectors(spec, index)
                feature_receipt = receipt_dir / f"{index + 1:02d}-{step.step_id}.json"
                receipt = self._grade(patch_path, feature_receipt, overlay, cumulative)
                if receipt is not None:
                    current = dataclasses.replace(
                        current,
                        feature_verdict=receipt.verdict.value,
                        feature_receipt_path=os.fspath(
                            feature_receipt.relative_to(session_dir)
                        ),
                    )
                    if receipt.verdict is Verdict.UNAVAILABLE:
                        unavailable = True
                else:
                    # grading failed: the captured step stays in the record
                    unavailable = True
            # Preservation at EVERY checkpoint (2026-09-08), not only the last.
            # A base behaviour broken mid session and repaired before the end
            # was previously invisible, and one left broken was reported only
            # as a final-state fact with no record of when it broke. Cumulative
            # feature selectors already catch a later prompt regressing an
            # earlier feature; this was the remaining hole, and seeing it is
            # why a session evaluation exists.
            if current.patch_path is not None:
                current, step_unavailable = self._grade_preservation(
                    current, spec, protected, session_dir, receipt_dir
                )
                unavailable = unavailable or step_unavailable
            graded.append(current)
        code = SessionCode.GRADE_UNAVAILABLE if unavailable else record.code
        return dataclasses.replace(record, code=code, steps=tuple(graded))

    def _grade_preservation(
        self,
        step: StepRecord,
        spec: SessionSpec,
        protected: frozenset[str],
        session_dir: Path,
        receipt_dir: Path,
    ) -> tuple[StepRecord, bool]:
        """One checkpoint's base-preservation verdict, and whether it failed.

        Preservation grades the patch as captured -- the full evidence patch --
        so a scope violation is a candidate failure, never infrastructure
        unavailability. The one exception is a patch that edited a protected
        public test: grading preservation against the model's own edited test
        would be circular, since a passing receipt would not evidence preserved
        base behaviour. That checkpoint is marked explicitly not meaningful,
        and its neighbours are unaffected.
        """
        if _touches_protected(step, protected):
            return dataclasses.replace(
                step, preservation_verdict=PRESERVATION_INVALID
            ), False
        assert step.patch_path is not None  # the caller checked
        receipt_path = receipt_dir / f"preservation-{step.step_id}.json"
        receipt = self._grade(
            session_dir / step.patch_path,
            receipt_path,
            None,
            spec.base_preservation_selectors,
            enforce_allowlist=False,
            auto_overlay=False,
        )
        if receipt is None:
            return step, True
        return dataclasses.replace(
            step,
            preservation_verdict=receipt.verdict.value,
            preservation_receipt_path=os.fspath(
                receipt_path.relative_to(session_dir)
            ),
        ), receipt.verdict is Verdict.UNAVAILABLE

    def _grade(
        self,
        patch_path: Path,
        receipt_path: Path,
        overlay: OverlaySpec | None,
        selectors: tuple[str, ...],
        enforce_allowlist: bool = True,
        auto_overlay: bool = True,
    ) -> Receipt | None:
        try:
            return grade(
                self.task_dir,
                patch_path,
                receipt_path,
                overlay=overlay,
                selectors=selectors,
                expected=selectors,
                enforce_allowlist=enforce_allowlist,
                auto_overlay=auto_overlay,
            )
        except SatyrnError:
            return None
