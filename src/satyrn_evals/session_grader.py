"""Offline session grading: retained checkpoint patches only, never live.

Runs only after the adapter is torn down. The feature grader copies the
base, applies the checkpoint patch, overlays the grader-only files, and
runs the cumulative hidden selection; the preservation grader runs the
declared public selectors on the last captured checkpoint without the
overlay. A scope violation skips that checkpoint's hidden grading but is
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
        for index, step in enumerate(record.steps):
            if step.scope_violations or step.patch_path is None:
                # the full patch stays in evidence; hidden grading skipped
                graded.append(step)
                continue
            patch_path = session_dir / step.patch_path
            cumulative = _cumulative_selectors(spec, index)
            feature_receipt = receipt_dir / f"{index + 1:02d}-{step.step_id}.json"
            receipt = self._grade(patch_path, feature_receipt, overlay, cumulative)
            if receipt is not None:
                graded.append(
                    dataclasses.replace(
                        step,
                        feature_verdict=receipt.verdict.value,
                        feature_receipt_path=os.fspath(
                            feature_receipt.relative_to(session_dir)
                        ),
                    )
                )
                if receipt.verdict is Verdict.UNAVAILABLE:
                    unavailable = True
            else:
                # grading failed: the captured step stays in the record
                graded.append(step)
                unavailable = True
        if graded and graded[-1].patch_path is not None:
            last = graded[-1]
            protected = _protected_public_test_files(spec)
            if any(
                within_source(violation, tuple(protected))
                for violation in last.scope_violations
            ):
                # the patch edited a protected public test: grading
                # preservation against the model's own edited test would
                # be circular (a passing receipt would not evidence
                # preserved base behavior). Record the scope violation
                # (already on the step) and mark preservation explicitly
                # not meaningful.
                graded[-1] = dataclasses.replace(
                    last, preservation_verdict=PRESERVATION_INVALID
                )
            else:
                preservation_receipt = (
                    receipt_dir / f"preservation-{last.step_id}.json"
                )
                # preservation grades the patch as captured — the full
                # evidence patch — so a scope violation is a candidate
                # failure, never infrastructure unavailability.
                receipt = self._grade(
                    session_dir / last.patch_path,
                    preservation_receipt,
                    None,
                    spec.base_preservation_selectors,
                    enforce_allowlist=False,
                    auto_overlay=False,
                )
                if receipt is not None:
                    graded[-1] = dataclasses.replace(
                        last,
                        preservation_verdict=receipt.verdict.value,
                        preservation_receipt_path=os.fspath(
                            preservation_receipt.relative_to(session_dir)
                        ),
                    )
                    if receipt.verdict is Verdict.UNAVAILABLE:
                        unavailable = True
                else:
                    unavailable = True
        code = SessionCode.GRADE_UNAVAILABLE if unavailable else record.code
        return dataclasses.replace(record, code=code, steps=tuple(graded))

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
