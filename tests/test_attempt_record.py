import json

import pytest

from satyrn_evals.attempt_record import (
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
        code="OK",
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
    )


def _refused() -> AttemptRecord:
    return AttemptRecord(
        version=1,
        outcome=AttemptOutcome.REFUSED,
        code="NO_PATCH",
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
