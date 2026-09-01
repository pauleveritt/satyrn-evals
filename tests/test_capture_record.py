import json
from pathlib import Path

import pytest

from satyrn_evals.capture_record import (
    CHECK_NAMES,
    CaptureCode,
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
        code=CaptureCode.OK,
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
        code=CaptureCode.REPO_DIRTY,
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
    assert data["oracle"] == [
        "python",
        "-m",
        "pytest",
        "-p",
        "satyrn_evals.oracle_hook",
        "a",
    ]
    assert data["check_outcomes"]["winnable"] == "passed"
    assert load_capture_record(path) == _captured()


def test_write_refused_roundtrip(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    assert data["outcome"] == "refused"
    assert data["base_sha"] is None
    assert load_capture_record(path) == _refused()


def test_writer_never_overwrites_an_existing_path(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    path.write_text("existing\n")
    with pytest.raises(FileExistsError):
        write_capture_record(path, _refused())
    assert path.read_text() == "existing\n"


def test_writer_does_not_leave_partial_destination_on_publish_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import satyrn_evals.capture_record as record_module

    path = tmp_path / "r.json"

    def fail_link(
        _source: Path, _destination: Path, *, follow_symlinks: bool
    ) -> None:
        assert follow_symlinks is False
        raise OSError("cannot publish")

    monkeypatch.setattr(record_module.os, "link", fail_link)
    with pytest.raises(OSError, match="cannot publish"):
        write_capture_record(path, _refused())

    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_writer_rolls_back_its_link_when_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import satyrn_evals.capture_record as record_module

    path = tmp_path / "r.json"
    real_link = record_module.os.link
    interrupted = KeyboardInterrupt("stop")

    def link_then_interrupt(
        source: Path, destination: Path, *, follow_symlinks: bool
    ) -> None:
        real_link(source, destination, follow_symlinks=follow_symlinks)
        raise interrupted

    monkeypatch.setattr(record_module.os, "link", link_then_interrupt)
    with pytest.raises(KeyboardInterrupt) as raised:
        write_capture_record(path, _refused())

    assert raised.value is interrupted
    assert list(tmp_path.iterdir()) == []


def test_load_rejects_bad_outcome(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["outcome"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outcome"):
        load_capture_record(path)


def test_capture_record_constructor_rejects_unknown_code() -> None:
    with pytest.raises(ValueError, match="not a valid CaptureCode"):
        CaptureRecord(
            version=1,
            outcome=CaptureOutcome.REFUSED,
            code="REPO_DITRY",
            message="source tree dirty",
            repo="/src/app",
            base_sha=None,
            fix_sha=None,
            task_dir=None,
            oracle=None,
            expected_test_ids=None,
            check_outcomes={name: "not-run" for name in CHECK_NAMES},
        )


def test_capture_record_preserves_positional_constructor_api() -> None:
    record = _refused()
    assert CaptureRecord(
        record.version,
        record.outcome,
        record.code,
        record.message,
        record.repo,
        record.base_sha,
        record.fix_sha,
        record.task_dir,
        record.oracle,
        record.expected_test_ids,
        record.check_outcomes,
    ) == record


def test_constructor_and_writer_validate_declared_shape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="message"):
        CaptureRecord(
            1,
            CaptureOutcome.REFUSED,
            CaptureCode.REPO_DIRTY,
            "",
            "/src/app",
            None,
            None,
            None,
            None,
            None,
            {name: "not-run" for name in CHECK_NAMES},
        )

    corrupted = _refused()
    object.__setattr__(corrupted, "message", "")
    with pytest.raises(ValueError, match="message"):
        write_capture_record(tmp_path / "r.json", corrupted)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", 2, "version"),
        ("base_sha", "", "base_sha"),
        ("oracle", ("python", ""), "oracle"),
    ],
)
def test_writer_rejects_corrupted_record_fields(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    corrupted = _refused()
    object.__setattr__(corrupted, field, value)

    with pytest.raises(ValueError, match=message):
        write_capture_record(tmp_path / "r.json", corrupted)


@pytest.mark.parametrize("version", [2, "1", True, None])
def test_load_rejects_bad_version(tmp_path: Path, version: object) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="version"):
        load_capture_record(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "REPO_DITRY"),
        ("message", None),
        ("message", ""),
        ("repo", []),
        ("base_sha", 1),
        ("fix_sha", False),
        ("task_dir", {}),
    ],
)
def test_load_rejects_bad_scalar_field_types(
    tmp_path: Path, field: str, value: object
) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=field):
        load_capture_record(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("oracle", "python"),
        ("oracle", ["python", 3]),
        ("oracle", [""]),
        ("expected_test_ids", "test_a"),
        ("expected_test_ids", [None]),
        ("expected_test_ids", [""]),
    ],
)
def test_load_rejects_bad_sequence_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=field):
        load_capture_record(path)


def test_load_rejects_bad_check_outcomes(tmp_path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["check_outcomes"] = {"source_preflight": "passed"}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="check_outcomes"):
        load_capture_record(path)


def test_load_rejects_non_object_check_outcomes(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["check_outcomes"] = []
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="check_outcomes must be an object"):
        load_capture_record(path)


def test_load_rejects_bad_check_state_type(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["check_outcomes"]["source_preflight"] = 1
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


def test_load_rejects_unexpected_field(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["extra"] = "value"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unexpected field"):
        load_capture_record(path)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("code", "REPO_DIRTY", "code must be OK"),
        ("task_dir", None, "all captured artifacts"),
        ("oracle", [], "must be non-empty"),
        ("expected_test_ids", [], "must be non-empty"),
    ],
)
def test_load_rejects_bad_captured_invariants(
    tmp_path: Path, field: str, value: object, match: str
) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _captured())
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=match):
        load_capture_record(path)


def test_load_rejects_captured_failed_check(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _captured())
    data = json.loads(path.read_text())
    data["check_outcomes"]["winnable"] = "failed"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="checks must all be passed"):
        load_capture_record(path)


def test_load_rejects_refused_ok_code(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["code"] = "OK"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="must not be OK"):
        load_capture_record(path)


def test_load_rejects_refused_mismatched_oracle_fields(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["oracle"] = ["python", "-m", "pytest"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="both be null or both be present"):
        load_capture_record(path)


def test_load_rejects_non_cleanup_refusal_with_task_dir(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["task_dir"] = "/tasks/app"
    data["oracle"] = ["python", "-m", "pytest"]
    data["expected_test_ids"] = ["test_a"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="only CLEANUP_FAILED"):
        load_capture_record(path)


def test_load_rejects_cleanup_task_without_captured_artifacts(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    write_capture_record(path, _refused())
    data = json.loads(path.read_text())
    data["code"] = "CLEANUP_FAILED"
    data["task_dir"] = "/tasks/app"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="must name oracle and expected_test_ids"):
        load_capture_record(path)


@pytest.mark.parametrize(
    ("content", "message"),
    [("{", "cannot read"), ("[]", "not an object")],
    ids=["invalid-json", "non-object"],
)
def test_load_rejects_invalid_document(
    tmp_path: Path, content: str, message: str
) -> None:
    path = tmp_path / "r.json"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        load_capture_record(path)


def test_load_rejects_unreadable_document(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot read"):
        load_capture_record(tmp_path / "missing.json")


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


def test_cleanup_failure_after_capture_roundtrips(tmp_path: Path) -> None:
    merged = merge_cleanup_failure(_captured(), "retained /tmp/wt")
    path = tmp_path / "r.json"
    write_capture_record(path, merged)
    assert load_capture_record(path) == merged
