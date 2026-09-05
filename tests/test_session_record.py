"""Session records: codes, round-trip durability, derived outcomes."""

import json
from pathlib import Path

import pytest

from satyrn_evals.session_manifest import SessionSpec, SessionStep
from satyrn_evals.session_record import (
    SessionCode,
    SessionRecord,
    StepRecord,
    deepest_feature_milestone,
    load_session_record,
    session_outcomes,
    write_session_record,
)

SPEC = SessionSpec(
    steps=(
        SessionStep("add-a", "feature", "Add a.", ("t_a.py::t_one",)),
        SessionStep("add-b", "feature", "Add b.", ("t_b.py::t_one",)),
        SessionStep("add-c", "feature", "Add c.", ("t_c.py::t_one",)),
        SessionStep("review", "review", "Review.", ()),
    ),
    base_preservation_selectors=("t_base.py::t_keep",),
)


def _record(**overrides: object) -> SessionRecord:
    base: dict[str, object] = {
        "version": 1,
        "task": "session-mechanics",
        "adapter_command": ("adapter",),
        "base_commit": "b" * 40,
        "code": SessionCode.COMPLETE,
    }
    base.update(overrides)
    return SessionRecord(**base)  # type: ignore[arg-type]


def _record_with(contamination):
    step = StepRecord(
        step_id="s1",
        prompt_digest="d",
        outcome="settled",
        patch_path="checkpoints/00-s1.patch",
        patch_digest="p",
        patch_bytes=10,
        contamination=contamination,
    )
    return SessionRecord(
        version=1,
        task="session-mechanics",
        adapter_command=("fake",),
        base_commit="a" * 40,
        code=SessionCode.COMPLETE,
        steps=(step,),
    )


def test_step_record_contamination_round_trips(tmp_path: Path) -> None:
    finding = {"visibility": "hidden", "checks": [
        {"check": "grader_content_in_patch", "outcome": "clean", "evidence": []},
        {"check": "grader_name_in_payload", "outcome": "unmeasured", "evidence": []},
    ]}
    path = tmp_path / "session-record.json"
    write_session_record(path, _record_with(finding))
    loaded = load_session_record(path)
    assert loaded.steps[0].contamination == finding


def test_legacy_step_record_without_contamination_loads(tmp_path: Path) -> None:
    path = tmp_path / "session-record.json"
    write_session_record(path, _record_with(None))
    data = json.loads(path.read_text())
    data["steps"][0].pop("contamination", None)  # pre-V7 records omit the key
    path.write_text(json.dumps(data))
    loaded = load_session_record(path)
    assert loaded.steps[0].contamination is None


def test_writer_omits_contamination_when_none(tmp_path: Path) -> None:
    path = tmp_path / "session-record.json"
    write_session_record(path, _record_with(None))
    data = json.loads(path.read_text())
    assert "contamination" not in data["steps"][0]


def test_record_round_trip_durably(tmp_path: Path) -> None:
    record = _record(
        conversation_id="conv-1",
        terminal_step="review",
        steps=(
            StepRecord("add-a", "p1", "settled", patch_digest="d" * 64, patch_bytes=10),
            StepRecord("review", "p4", "settled"),
        ),
    )
    path = tmp_path / "session-record.json"
    write_session_record(path, record)
    assert not path.with_name(path.name + ".tmp").exists()
    loaded = load_session_record(path)
    assert loaded == record
    data = json.loads(path.read_text())
    assert data["code"] == "COMPLETE"


def test_record_version_and_code_validated() -> None:
    with pytest.raises(ValueError, match="version"):
        _record(version=2)
    with pytest.raises(ValueError, match="SessionCode"):
        _record(code="COMPLETE")  # type: ignore[arg-type]


def test_deepest_milestone_all_settled_and_passed() -> None:
    steps = (
        StepRecord("add-a", "p1", "settled", feature_verdict="pass"),
        StepRecord("add-b", "p2", "settled", feature_verdict="pass"),
        StepRecord("add-c", "p3", "settled", feature_verdict="pass"),
        StepRecord("review", "p4", "settled", feature_verdict="pass"),
    )
    assert deepest_feature_milestone(SPEC, steps) == 3


def test_deepest_milestone_agent_error_at_step_two() -> None:
    steps = (
        StepRecord("add-a", "p1", "settled", feature_verdict="pass"),
        StepRecord("add-b", "p2", "agent-error"),
    )
    assert deepest_feature_milestone(SPEC, steps) == 1


def test_deepest_milestone_zero_when_first_fails_or_violates_scope() -> None:
    assert deepest_feature_milestone(
        SPEC, (StepRecord("add-a", "p1", "settled", feature_verdict="fail"),)
    ) == 0
    assert deepest_feature_milestone(
        SPEC,
        (
            StepRecord(
                "add-a",
                "p1",
                "settled",
                feature_verdict="pass",
                scope_violations=("outside.txt",),
            ),
        ),
    ) == 0
    assert deepest_feature_milestone(SPEC, ()) == 0


def test_deepest_milestone_review_never_advances() -> None:
    steps = (
        StepRecord("add-a", "p1", "settled", feature_verdict="pass"),
        StepRecord("review", "p4", "settled", feature_verdict="pass"),
    )
    spec = SessionSpec(
        steps=(SPEC.steps[0], SPEC.steps[3]),
        base_preservation_selectors=SPEC.base_preservation_selectors,
    )
    assert deepest_feature_milestone(spec, steps) == 1


def test_session_outcomes_derives_without_conflating() -> None:
    good = SessionSpec(
        steps=(SPEC.steps[0], SPEC.steps[3]),
        base_preservation_selectors=SPEC.base_preservation_selectors,
    )
    record = _record(
        steps=(
            StepRecord("add-a", "p1", "settled", patch_digest="d" * 64,
                       patch_bytes=12, feature_verdict="pass"),
            StepRecord("review", "p4", "settled",
                       preservation_verdict="pass"),
        )
    )
    outcomes = session_outcomes(record, good)
    assert outcomes["all_prompts_settled"] is True
    assert outcomes["deepest_milestone"] == 1
    assert outcomes["retained_nonempty_patch"] is True
    assert outcomes["all_scope_valid"] is True
    assert outcomes["last_preservation_verdict"] == "pass"
    assert outcomes["grading_available"] is True


def test_session_outcomes_sibling_flags() -> None:
    empty = _record()
    outcomes = session_outcomes(empty, SPEC)
    assert outcomes["all_prompts_settled"] is False
    assert outcomes["retained_nonempty_patch"] is False
    assert outcomes["grading_available"] is False
    scoped = _record(steps=(StepRecord("add-a", "p1", "settled",
                                       scope_violations=("x",)),))
    assert session_outcomes(scoped, SPEC)["all_scope_valid"] is False
    unavailable = _record(code=SessionCode.GRADE_UNAVAILABLE)
    assert session_outcomes(unavailable, SPEC)["grading_available"] is False
    failed = _record(code=SessionCode.WORKSPACE_FAILED)
    assert session_outcomes(failed, SPEC)["grading_available"] is False


def test_record_round_trips_artifact_digests_and_recovery_path(tmp_path: Path) -> None:
    record = _record(
        provenance={"repo": "bundled synthetic fixture", "base_sha": "unrecorded", "fix_sha": "unrecorded"},
        retained_path="/tmp/retained",
        steps=(
            StepRecord(
                "add-a", "p1", "settled",
                patch_digest="d" * 64, patch_bytes=10,
                snapshot_digest="a" * 64,
                transcript_prefix_digest="b" * 64,
                transcript_prefix_bytes=2048,
            ),
        ),
    )
    path = tmp_path / "session-record.json"
    write_session_record(path, record)
    assert load_session_record(path) == record


def test_load_session_record_refuses_non_object_and_wrong_version(
    tmp_path: Path,
) -> None:
    path = tmp_path / "session-record.json"
    path.write_text("[1]")
    with pytest.raises(ValueError, match="not an object"):
        load_session_record(path)
    path.write_text(json.dumps({"version": 2}))
    with pytest.raises(ValueError, match="version"):
        load_session_record(path)


def test_grader_keeps_a_zero_step_record_unchanged(tmp_path: Path) -> None:
    """A record with no captured steps grades to itself (no preservation,
    no feature receipts — nothing to conflate)."""
    from satyrn_evals.session_grader import SessionGrader

    record = _record()
    path = tmp_path / "session-record.json"
    write_session_record(path, record)
    grader = SessionGrader(task_dir=tmp_path)  # never touched: no steps
    graded = grader.grade_record(
        record,
        SPEC,
        _OverlayShim(),  # type: ignore[bad-argument-type]  # trap shim: overlay must never be touched for zero-step records
        tmp_path,
    )
    assert graded.code is record.code
    assert graded.steps == ()


class _OverlayShim:
    """Grader's overlay parameter is unused for zero-step records."""

    def __getattr__(self, name: str):
        raise AssertionError("overlay must not be touched")


def test_grader_skips_preservation_for_a_patchless_last_step(
    tmp_path: Path,
) -> None:
    """A captured step without a patch artifact: no feature grading, no
    preservation — the record is returned with its code unchanged."""
    from satyrn_evals.session_grader import SessionGrader

    record = _record(steps=(StepRecord("add-a", "p1", "agent-error"),))
    graded = SessionGrader(task_dir=tmp_path).grade_record(
        record, SPEC,
        _OverlayShim(),  # type: ignore[bad-argument-type]  # trap shim: overlay must never be touched for zero-step records
        tmp_path,
    )
    assert graded.code is record.code
    assert graded.steps[0].feature_verdict is None
    assert graded.steps[0].preservation_verdict is None


def test_preservation_is_invalid_when_the_patch_edits_a_protected_public_test(
    tmp_path: Path,
) -> None:
    """A patch that changes a protected public test makes preservation
    circular; the grader must record 'invalid', not a vacuous pass
    (smoke-2 finding; the sibling — a non-protected out-of-scope file
    still grades — lives in the integration session-grading tests)."""
    from satyrn_evals.session_grader import (
        PRESERVATION_INVALID,
        SessionGrader,
    )

    spec = SessionSpec(
        steps=(SPEC.steps[0], SPEC.steps[3]),
        base_preservation_selectors=("t_base.py::t_keep",),
    )
    record = _record(
        steps=(
            StepRecord(
                "add-a", "p1", "settled",
                patch_path="checkpoints/01-add-a.patch",
                scope_violations=("t_base.py",),
            ),
        )
    )
    graded = SessionGrader(task_dir=tmp_path).grade_record(
        record, spec,
        _OverlayShim(),  # type: ignore[bad-argument-type]  # trap shim: overlay must never be touched for zero-step records
        tmp_path,
    )
    step = graded.steps[0]
    assert step.preservation_verdict == PRESERVATION_INVALID
    assert step.preservation_receipt_path is None
    assert step.scope_violations == ("t_base.py",)  # the violation is recorded
    assert graded.code is record.code  # not GRADE_UNAVAILABLE: machinery worked


def test_deepest_milestone_counts_a_later_repair() -> None:
    """A failed earlier checkpoint that a later cumulative pass repairs
    must not score zero (independent-review finding): checkpoint 2's
    cumulative selection passed even though checkpoint 1 had failed."""
    steps = (
        StepRecord("add-a", "p1", "settled", feature_verdict="fail"),
        StepRecord("add-b", "p2", "settled", feature_verdict="pass"),
        StepRecord("add-c", "p3", "settled", feature_verdict="fail"),
    )
    assert deepest_feature_milestone(SPEC, steps) == 2


def test_deepest_milestone_is_the_deepest_pass_not_a_trailing_one() -> None:
    steps = (
        StepRecord("add-a", "p1", "settled", feature_verdict="pass"),
        StepRecord("add-b", "p2", "settled", feature_verdict="fail"),
        StepRecord("add-c", "p3", "settled", feature_verdict="pass"),
    )
    assert deepest_feature_milestone(SPEC, steps) == 3
