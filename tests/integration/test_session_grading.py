"""Offline session grading over retained checkpoint artifacts."""

import json
import shutil
import sys
from pathlib import Path

import pytest

from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session import run_session
from satyrn_evals.session_grader import SessionGrader
from satyrn_evals.session_manifest import load_session_spec
from satyrn_evals.session_record import SessionCode, session_outcomes


def _session_dir(tmp_path: Path) -> Path:
    dirs = [p for p in tmp_path.iterdir()
            if p.is_dir() and "mini-session-session-" in p.name]
    assert len(dirs) == 1
    return dirs[0]

pytestmark = pytest.mark.integration

DATA = Path(__file__).resolve().parent / "data"
FAKE = Path(__file__).resolve().parent / "fake_session_adapter.py"
TASK = DATA / "mini-session"
TASK_DIVERGENT = DATA / "mini-session-divergent"


def test_clean_session_grades_every_checkpoint(tmp_path: Path) -> None:
    record = _graded(tmp_path, "clean")
    assert record.code is SessionCode.COMPLETE
    assert [s.feature_verdict for s in record.steps] == ["pass", "pass", "pass"]
    assert record.steps[-1].preservation_verdict == "pass"
    assert record.steps[-1].feature_receipt_path is not None
    receipt = json.loads(
        (next(tmp_path.iterdir()) / record.steps[0].feature_receipt_path).read_text()
    )
    assert receipt["verdict"] == "pass"
    outcomes = session_outcomes(
        record, load_session_spec(TASK)
    )
    assert outcomes["deepest_milestone"] == 2
    assert outcomes["last_preservation_verdict"] == "pass"
    assert outcomes["grading_available"] is True


def test_divergent_preservation_grades_via_the_session_path(
    tmp_path: Path,
) -> None:
    """T5 wiring: the preservation opt-out works through the real
    SessionGrader call site (session_grader.py:122-128), not only through
    direct grade() calls.

    mini-session-divergent's manifest expected_test_ids include a hidden
    id that is NOT among session.json's base_preservation_selectors, so
    V7's auto-overlay would swap the preservation selectors and yield
    UNAVAILABLE. The opt-out must keep the preservation verdict PASS.
    """
    spec = load_session_spec(TASK_DIVERGENT)
    manifest = load_manifest(TASK_DIVERGENT)
    # non-vacuity guard: the fixture must actually diverge, or this test
    # silently passes whether or not the opt-out exists
    assert set(manifest.expected_test_ids) != set(spec.base_preservation_selectors)

    record = run_session(
        task="mini-session-divergent",
        tasks_root=DATA,
        output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), "clean"],
    )
    session_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    graded = SessionGrader(task_dir=TASK_DIVERGENT).grade_record(
        record, spec, load_overlay(TASK_DIVERGENT, manifest), session_dir
    )
    assert graded.code is SessionCode.COMPLETE
    assert [s.feature_verdict for s in graded.steps] == ["pass", "pass", "pass"]
    assert graded.steps[-1].preservation_verdict == "pass"


def test_scope_checkpoint_skips_hidden_but_keeps_evidence(tmp_path: Path) -> None:
    record = _graded(tmp_path, "scope")
    assert record.code is SessionCode.SCOPE_VIOLATION
    violating = record.steps[1]
    assert violating.scope_violations
    assert violating.feature_verdict is None  # hidden grading skipped
    assert violating.feature_receipt_path is None
    assert (next(tmp_path.iterdir()) / violating.patch_path).exists()  # evidence kept
    assert record.steps[0].feature_verdict == "pass"  # clean checkpoint graded
    # review's tree still holds outside.txt: its hidden grading is skipped
    # too, while its preserved base behavior is still graded (below)
    assert record.steps[2].feature_verdict is None
    assert record.steps[-1].preservation_verdict == "pass"


def _graded(tmp_path: Path, scenario: str, **kw: float):
    record = run_session(
        task="mini-session",
        tasks_root=DATA,
        output=tmp_path,
        adapter_command=[sys.executable, str(FAKE), scenario],
        **kw,
    )
    session_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    grader = SessionGrader(task_dir=TASK)
    return grader.grade_record(
        record, load_session_spec(TASK), load_overlay(TASK, load_manifest(TASK)),
        session_dir,
    )


def test_grading_reads_only_retained_artifacts(tmp_path: Path) -> None:
    """Regrade a captured session from its artifacts alone (BRIEF rule 3)."""
    record = _graded(tmp_path, "clean")
    assert record.code is SessionCode.COMPLETE


def test_broken_oracle_is_grade_unavailable(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt-task"
    shutil.copytree(TASK, corrupt)
    manifest = json.loads((corrupt / "manifest.json").read_text())
    manifest["oracle"] = ["nonexistent-oracle-binary"]
    (corrupt / "manifest.json").write_text(json.dumps(manifest))
    record = _graded(tmp_path, "clean")
    assert record.code is not None
    grader = SessionGrader(task_dir=corrupt)
    regressed = grader.grade_record(
        record, load_session_spec(corrupt),
        load_overlay(corrupt, load_manifest(corrupt)),
        next(p for p in tmp_path.iterdir() if p.is_dir()),
    )
    assert regressed.code is SessionCode.GRADE_UNAVAILABLE
    assert regressed.steps  # grading failure must not drop the captured step


def test_silent_oracle_is_unavailable_not_exception(tmp_path: Path) -> None:
    """An oracle that runs but writes no hook file yields an UNAVAILABLE
    receipt — the grader flags the step, the step stays recorded."""
    import json as _json
    import shutil as _shutil

    silent = tmp_path / "silent-task"
    _shutil.copytree(TASK, silent)
    manifest = _json.loads((silent / "manifest.json").read_text())
    manifest["oracle"] = ["true"]  # runs, exits 0, writes no hook result
    (silent / "manifest.json").write_text(_json.dumps(manifest))
    record = _graded(tmp_path, "clean")
    assert record.code is not None
    grader = SessionGrader(task_dir=silent)
    regressed = grader.grade_record(
        record,
        load_session_spec(silent),
        load_overlay(silent, load_manifest(silent)),
        _session_dir(tmp_path),
    )
    assert regressed.code is SessionCode.GRADE_UNAVAILABLE
    assert regressed.steps  # grading failure must not drop the captured step
    assert regressed.steps[0].feature_verdict == "unavailable"


def _shutil(source: Path, target: Path) -> None:  # helper indirection
    import shutil

    shutil.copytree(source, target)


def test_preservation_unavailable_maps_grade_unavailable(
    tmp_path: Path,
) -> None:
    import json as _json

    silent = tmp_path / "silent-pres"
    _shutil(TASK, silent)
    manifest = _json.loads((silent / "manifest.json").read_text())
    manifest["oracle"] = ["true"]
    (silent / "manifest.json").write_text(_json.dumps(manifest))
    grader = SessionGrader(task_dir=silent)
    spec = load_session_spec(silent)
    overlay = load_overlay(silent, load_manifest(silent))
    # a captured record from the healthy task, graded by the silent one:
    # feature grading is unavailable, so preservation never runs
    record = _graded(tmp_path, "clean")
    assert record.code is not None
    session_dir = _session_dir(tmp_path)
    healthy = SessionGrader(task_dir=TASK)
    graded = healthy.grade_record(record, spec, overlay, session_dir)
    assert graded.steps[-1].preservation_verdict == "pass"
    # now grade the same artifacts with the silent oracle: the feature
    # receipt is unavailable and the code maps to GRADE_UNAVAILABLE
    regressed = grader.grade_record(record, spec, overlay, session_dir)
    assert regressed.code is SessionCode.GRADE_UNAVAILABLE
    assert regressed.steps  # grading failure must not drop the captured step


def test_protected_public_test_edit_makes_preservation_invalid(
    tmp_path: Path,
) -> None:
    """Smoke-2 finding fixed: a session whose patch edits the protected
    public test must not present a passing preservation receipt. The
    record ends SCOPE_VIOLATION, the violation is retained, and the
    last step's preservation verdict is explicitly 'invalid' with no
    receipt — not a circular pass."""
    from satyrn_evals.session_grader import PRESERVATION_INVALID

    record = _graded(tmp_path, "edit-public-test")
    assert record.code is SessionCode.SCOPE_VIOLATION
    last = record.steps[-1]
    assert "test_solution.py" in last.scope_violations
    assert last.preservation_verdict == PRESERVATION_INVALID
    assert last.preservation_receipt_path is None
