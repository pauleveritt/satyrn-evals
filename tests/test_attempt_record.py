import json
from pathlib import Path

import pytest

import satyrn_evals.attempt_record as attempt_record_module
from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.verdict import Verdict


def _attempted() -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.ATTEMPTED,
        code=AttemptCode.OK,
        message="attempt recorded and graded",
        task="format_number",
        command=("fake_attempt.py", "--good"),
        command_exit=0,
        patch_path="patch.diff",
        transcript_path="transcript.txt",
        patch_digest="a" * 64,
        transcript_digest="b" * 64,
        verdict=Verdict.PASS,
        receipt_path="receipt.json",
        workspace_base_sha="c" * 40,
    )


def _refused() -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.REFUSED,
        code=AttemptCode.NO_PATCH,
        message="attempt refused: NO_PATCH",
        task="format_number",
        command=("fake_attempt.py", "--no-patch"),
        command_exit=0,
        patch_path=None,
        transcript_path="transcript.txt",
        patch_digest=None,
        transcript_digest="b" * 64,
        verdict=None,
        receipt_path=None,
        workspace_base_sha="c" * 40,
    )


def test_write_attempted_roundtrip(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _attempted())
    data = json.loads(path.read_text())
    assert data["version"] == 1
    assert data["outcome"] == "attempted"
    assert data["code"] == "OK"
    assert data["command"] == ["fake_attempt.py", "--good"]
    assert data["command_exit"] == 0
    assert data["verdict"] == "pass"
    assert load_attempt_record(path) == _attempted()


def test_write_refused_roundtrip(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    assert data["outcome"] == "refused"
    assert data["patch_path"] is None
    assert data["patch_digest"] is None
    assert data["verdict"] is None
    assert data["receipt_path"] is None
    assert load_attempt_record(path) == _refused()


def test_load_rejects_bad_outcome(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    data["outcome"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outcome"):
        load_attempt_record(path)


def test_load_rejects_bad_verdict(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _attempted())
    data = json.loads(path.read_text())
    data["verdict"] = "maybe"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="verdict"):
        load_attempt_record(path)


def test_load_rejects_missing_required_field(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    del data["code"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="missing a field"):
        load_attempt_record(path)


def test_load_rejects_unreadable_json(tmp_path: Path) -> None:
    path = tmp_path / "attempt.json"
    path.write_text("not json")
    with pytest.raises(ValueError, match="cannot read attempt record"):
        load_attempt_record(path)


def test_load_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "attempt.json"
    path.write_text("[]")
    with pytest.raises(ValueError, match="not an object"):
        load_attempt_record(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("version", True, "version"),
        ("message", 1, "text"),
        ("task", None, "text"),
        ("command", "sh", "not an array"),
        ("command", ["sh", 1], "command"),
        ("command_exit", "zero", "command_exit"),
        ("patch_path", None, "must agree"),
        ("transcript_digest", 1, "SHA-256"),
        ("workspace_base_sha", "not-a-sha", "Git object ID"),
    ],
)
def test_load_rejects_wrong_field_shapes(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _attempted())
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=message):
        load_attempt_record(path)


def test_load_rejects_unexpected_field_but_accepts_legacy_v3(tmp_path: Path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    data["unexpected"] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unexpected fields"):
        load_attempt_record(path)

    data.pop("unexpected")
    data.pop("workspace_base_sha")
    data.pop("retained_path")
    path.write_text(json.dumps(data))
    loaded = load_attempt_record(path)
    assert loaded.code is AttemptCode.NO_PATCH
    assert loaded.workspace_base_sha is None
    assert loaded.retained_path is None


@pytest.mark.parametrize("field", ["workspace_base_sha", "retained_path"])
def test_load_rejects_partial_v4_shape(tmp_path: Path, field: str) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    data.pop(field)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="both V4 workspace fields"):
        load_attempt_record(path)


def test_load_rejects_operational_code_in_legacy_shape(tmp_path: Path) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, _refused())
    data = json.loads(path.read_text())
    data.pop("workspace_base_sha")
    data.pop("retained_path")
    data["code"] = AttemptCode.WORKSPACE_FAILED
    data["command_exit"] = None
    data["transcript_path"] = None
    data["transcript_digest"] = None
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="legacy.*operational"):
        load_attempt_record(path)


def test_legacy_marker_rejects_v4_values() -> None:
    values = {
        field: getattr(_refused(), field)
        for field in (
            "version",
            "outcome",
            "code",
            "message",
            "task",
            "command",
            "command_exit",
            "patch_path",
            "transcript_path",
            "patch_digest",
            "transcript_digest",
            "verdict",
            "receipt_path",
            "workspace_base_sha",
            "retained_path",
        )
    }
    with pytest.raises(ValueError, match="legacy.*V4 workspace values"):
        AttemptRecord(**values, _legacy=True)  # type: ignore[arg-type]


@pytest.mark.parametrize("record", [_attempted(), _refused()])
def test_legacy_v3_roundtrip_remains_legacy(
    tmp_path: Path, record: AttemptRecord
) -> None:
    path = tmp_path / "attempt.json"
    write_attempt_record(path, record)
    data = json.loads(path.read_text())
    data.pop("workspace_base_sha")
    data.pop("retained_path")
    path.write_text(json.dumps(data))

    legacy = load_attempt_record(path)
    write_attempt_record(path, legacy)

    assert set(json.loads(path.read_text())) == {
        "version",
        "outcome",
        "code",
        "message",
        "task",
        "command",
        "command_exit",
        "patch_path",
        "transcript_path",
        "patch_digest",
        "transcript_digest",
        "verdict",
        "receipt_path",
    }
    assert load_attempt_record(path) == legacy


def _valid_v4_record(code: AttemptCode) -> AttemptRecord:
    values: dict[str, object] = {
        "version": 1,
        "outcome": AttemptOutcome.REFUSED,
        "code": code,
        "message": "result",
        "task": "t",
        "command": ("cmd",),
        "command_exit": None,
        "patch_path": None,
        "transcript_path": None,
        "patch_digest": None,
        "transcript_digest": None,
        "verdict": None,
        "receipt_path": None,
        "workspace_base_sha": None,
        "retained_path": None,
    }
    match code:
        case AttemptCode.OK:
            values.update(
                outcome=AttemptOutcome.ATTEMPTED,
                command_exit=0,
                patch_path="patch.diff",
                transcript_path="transcript.txt",
                patch_digest="a" * 64,
                transcript_digest="b" * 64,
                verdict=Verdict.PASS,
                receipt_path="receipt.json",
                workspace_base_sha="c" * 40,
            )
        case AttemptCode.NO_PATCH | AttemptCode.PATCH_INVALID:
            values.update(command_exit=0, workspace_base_sha="c" * 40)
        case AttemptCode.TRANSCRIPT_MISSING:
            values.update(
                command_exit=0,
                patch_path="patch.diff",
                patch_digest="a" * 64,
                workspace_base_sha="c" * 40,
            )
        case AttemptCode.TRANSCRIPT_EMPTY:
            values.update(
                command_exit=0,
                patch_path="patch.diff",
                transcript_path="transcript.txt",
                patch_digest="a" * 64,
                transcript_digest="b" * 64,
                workspace_base_sha="c" * 40,
            )
        case AttemptCode.WORKSPACE_FAILED:
            pass
        case AttemptCode.COMMAND_TIMEOUT:
            values["workspace_base_sha"] = "c" * 40
        case AttemptCode.CLEANUP_FAILED:
            values["retained_path"] = "/tmp/retained"
    return AttemptRecord(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("code", list(AttemptCode))
def test_v4_code_matrix_accepts_each_code(code: AttemptCode) -> None:
    record = _valid_v4_record(code)
    assert record.code is code
    assert record.outcome is (
        AttemptOutcome.ATTEMPTED if code is AttemptCode.OK else AttemptOutcome.REFUSED
    )


def test_attempt_policy_is_complete() -> None:
    assert set(attempt_record_module._ATTEMPT_POLICIES) == set(AttemptCode)


@pytest.mark.parametrize(
    ("code", "changes", "message"),
    [
        (AttemptCode.OK, {"command_exit": None}, "requires command_exit"),
        (AttemptCode.NO_PATCH, {"workspace_base_sha": None}, "requires workspace_base_sha"),
        (AttemptCode.COMMAND_TIMEOUT, {"command_exit": 7}, "null command_exit"),
        (AttemptCode.COMMAND_TIMEOUT, {"workspace_base_sha": None}, "requires workspace_base_sha"),
        (
            AttemptCode.TRANSCRIPT_MISSING,
            {"patch_path": None, "patch_digest": None},
            "requires a patch",
        ),
        (
            AttemptCode.TRANSCRIPT_MISSING,
            {"transcript_path": "transcript.txt", "transcript_digest": "b" * 64},
            "no transcript",
        ),
        (
            AttemptCode.TRANSCRIPT_EMPTY,
            {"transcript_path": None, "transcript_digest": None},
            "requires patch and transcript",
        ),
        (
            AttemptCode.WORKSPACE_FAILED,
            {"patch_path": "patch.diff", "patch_digest": "a" * 64},
            "cannot contain delivered artifacts",
        ),
    ],
)
def test_v4_code_matrix_rejects_impossible_shapes(
    code: AttemptCode, changes: dict[str, object], message: str
) -> None:
    valid = _valid_v4_record(code)
    values = {
        field: getattr(valid, field)
        for field in (
            "version",
            "outcome",
            "code",
            "message",
            "task",
            "command",
            "command_exit",
            "patch_path",
            "transcript_path",
            "patch_digest",
            "transcript_digest",
            "verdict",
            "receipt_path",
            "workspace_base_sha",
            "retained_path",
        )
    }
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        AttemptRecord(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"version": 2}, "version"),
        ({"message": ""}, "text and command"),
        ({"task": ""}, "text and command"),
        ({"command": ()}, "text and command"),
        ({"patch_path": ""}, "non-empty"),
        ({"transcript_digest": "g" * 64}, "SHA-256"),
        ({"code": AttemptCode.NO_PATCH}, "requires outcome refused"),
        ({"verdict": None}, "requires a verdict"),
        ({"receipt_path": None}, "receipt path"),
    ],
)
def test_attempted_record_invariants(changes: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "version": 1,
        "outcome": AttemptOutcome.ATTEMPTED,
        "code": AttemptCode.OK,
        "message": "attempted",
        "task": "t",
        "command": ("cmd",),
        "command_exit": 0,
        "patch_path": "patch.diff",
        "transcript_path": "transcript.txt",
        "patch_digest": "a" * 64,
        "transcript_digest": "b" * 64,
        "verdict": Verdict.PASS,
        "receipt_path": "receipt.json",
        "workspace_base_sha": "c" * 40,
    }
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        AttemptRecord(**values)  # type: ignore[arg-type]


def test_refused_record_invariants() -> None:
    values: dict[str, object] = {
        "version": 1,
        "outcome": AttemptOutcome.REFUSED,
        "code": AttemptCode.OK,
        "message": "refused",
        "task": "t",
        "command": ("cmd",),
        "command_exit": None,
        "patch_path": None,
        "transcript_path": None,
        "patch_digest": None,
        "transcript_digest": None,
        "verdict": None,
        "receipt_path": None,
    }
    with pytest.raises(ValueError, match="requires outcome attempted"):
        AttemptRecord(**values)  # type: ignore[arg-type]
    values["code"] = AttemptCode.NO_PATCH
    values["verdict"] = Verdict.FAIL
    with pytest.raises(ValueError, match="no verdict"):
        AttemptRecord(**values)  # type: ignore[arg-type]
    values["verdict"] = None
    values["receipt_path"] = "receipt.json"
    with pytest.raises(ValueError, match="no verdict or receipt"):
        AttemptRecord(**values)  # type: ignore[arg-type]


def test_cleanup_record_invariants() -> None:
    values: dict[str, object] = {
        "version": 1,
        "outcome": AttemptOutcome.REFUSED,
        "code": AttemptCode.CLEANUP_FAILED,
        "message": "cleanup failed",
        "task": "t",
        "command": ("cmd",),
        "command_exit": None,
        "patch_path": None,
        "transcript_path": None,
        "patch_digest": None,
        "transcript_digest": None,
        "verdict": None,
        "receipt_path": None,
    }
    with pytest.raises(ValueError, match="requires retained_path"):
        AttemptRecord(**values)  # type: ignore[arg-type]
    values["code"] = AttemptCode.NO_PATCH
    values["command_exit"] = 0
    values["workspace_base_sha"] = "c" * 40
    values["retained_path"] = "/tmp/retained"
    with pytest.raises(ValueError, match="only CLEANUP_FAILED"):
        AttemptRecord(**values)  # type: ignore[arg-type]
