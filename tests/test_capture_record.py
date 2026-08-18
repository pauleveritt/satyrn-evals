import json

import pytest

from satyrn_evals.capture_record import (
    CHECK_NAMES,
    CaptureOutcome,
    CaptureRecord,
    load_capture_record,
    merge_cleanup_failure,
    write_capture_record,
)


def _captured() -> CaptureRecord:
    return CaptureRecord(
        version=1,
        outcome=CaptureOutcome.CAPTURED,
        code="OK",
        message="task captured",
        repo="/src/app",
        base_sha="b" * 40,
        fix_sha="f" * 40,
        task_dir="/tasks/app",
        oracle=("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "a"),
        expected_test_ids=("a",),
        check_outcomes={name: "passed" for name in CHECK_NAMES},
    )


def _refused() -> CaptureRecord:
    return CaptureRecord(
        version=1,
        outcome=CaptureOutcome.REFUSED,
        code="REPO_DIRTY",
        message="source tree dirty",
        repo="/src/app",
        base_sha=None,
        fix_sha=None,
        task_dir=None,
        oracle=None,
        expected_test_ids=None,
        check_outcomes={name: "not-run" for name in CHECK_NAMES},
    )


def test_write_captured_roundtrip(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _captured())
    data = json.loads(path.read_text())
    assert data["version"] == 1
    assert data["outcome"] == "captured"
    assert data["code"] == "OK"
    assert data["oracle"] == ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook", "a"]
    assert data["check_outcomes"]["winnable"] == "passed"
    assert load_capture_record(path) == _captured()


def test_write_refused_roundtrip(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    assert data["outcome"] == "refused"
    assert data["base_sha"] is None
    assert load_capture_record(path) == _refused()


def test_load_rejects_bad_outcome(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["outcome"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outcome"):
        load_capture_record(path)


def test_load_rejects_bad_check_outcomes(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["check_outcomes"] = {"source_preflight": "passed"}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="check_outcomes"):
        load_capture_record(path)


def test_load_rejects_missing_required_field(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    del data["code"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="missing a field"):
        load_capture_record(path)


def test_merge_cleanup_failure_precedence() -> None:
    pending = _refused()
    merged = merge_cleanup_failure(pending, "cannot remove locked worktree /tmp/wt")
    assert merged.code == "CLEANUP_FAILED"
    assert merged.outcome is CaptureOutcome.REFUSED
    assert "displaced REPO_DIRTY" in merged.message
    assert "source tree dirty" in merged.message
    assert merged.task_dir is None


def test_merge_cleanup_failure_demotes_captured_to_refused() -> None:
    captured = _captured()
    merged = merge_cleanup_failure(captured, "cannot remove locked worktree /tmp/wt")
    assert merged.outcome is CaptureOutcome.REFUSED
    assert merged.code == "CLEANUP_FAILED"
    assert "displaced OK" in merged.message
