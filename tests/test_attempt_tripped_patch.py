"""`tripped_patch_path` on a BUDGET_EXCEEDED record: the harvested secondary.

Default tier. Ruling R-1: the record names the harvested patch and nothing
more; the verdict is a day-after classifier output, never a run-record field,
so the attempt path never re-enters the oracle for a tripped cell. The record
shapes are built by hand and round-tripped through the writer and loader.
"""

import json
from pathlib import Path

import pytest

import satyrn_evals.attempt as attempt_module
from satyrn_evals.attempt_record import (
    AttemptCode,
    AttemptOutcome,
    AttemptRecord,
    load_attempt_record,
    write_attempt_record,
)
from satyrn_evals.manifest import TaskManifest
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict
from satyrn_evals.workspace import (
    TRIPPED_PATCH_NAME,
    WorkspaceCode,
    WorkspaceResult,
)

SHA = "0" * 40
DIGEST = "1" * 64

_GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)


def _record(**overrides: object) -> AttemptRecord:
    fields: dict = dict(
        version=1, outcome=AttemptOutcome.REFUSED, code=AttemptCode.BUDGET_EXCEEDED,
        message="attempt command spent 48001 output tokens, over the budget of 48000",
        task="t", command=("pi",), command_exit=None, patch_path=None, transcript_path="transcript.txt",
        patch_digest=None, transcript_digest=DIGEST, verdict=None, receipt_path=None, timeout=3000.0,
        rung="R1", contract_digest=DIGEST, workspace_base_sha=SHA, attempt_dir="t-1",
    )
    return AttemptRecord(**(fields | overrides))


def _manifest() -> TaskManifest:
    return TaskManifest(
        name="t",
        contract="Fix it.",
        oracle=("python", "-m", "pytest"),
        expected_test_ids=(),
        source_paths=(),
        fixtures={},
    )


# --- the record shape (Ruling R-1) ---


def test_a_record_carrying_a_tripped_patch_path_round_trips(tmp_path: Path) -> None:
    record = _record(tripped_patch_path=TRIPPED_PATCH_NAME)
    write_attempt_record(tmp_path / "attempt.json", record)
    body = json.loads((tmp_path / "attempt.json").read_text())
    assert body["tripped_patch_path"] == TRIPPED_PATCH_NAME
    loaded = load_attempt_record(tmp_path / "attempt.json")
    assert loaded.tripped_patch_path == TRIPPED_PATCH_NAME
    assert loaded.verdict is None


def test_a_record_without_a_tripped_patch_path_writes_the_older_field_set(
    tmp_path: Path,
) -> None:
    """Ruling 13: every committed result's cells must keep loading."""
    write_attempt_record(tmp_path / "attempt.json", _record())
    body = json.loads((tmp_path / "attempt.json").read_text())
    assert "tripped_patch_path" not in body
    assert "tripped_verdict" not in body
    assert load_attempt_record(tmp_path / "attempt.json").tripped_patch_path is None


def test_a_non_budget_exceeded_record_may_not_carry_a_tripped_patch_path() -> None:
    with pytest.raises(ValueError, match="tripped_patch_path"):
        _record(
            code=AttemptCode.COMMAND_TIMEOUT,
            tripped_patch_path=TRIPPED_PATCH_NAME,
        )


def test_a_budget_exceeded_record_may_carry_a_tripped_patch_path() -> None:
    """The sibling success to the refusal above."""
    assert _record(tripped_patch_path=TRIPPED_PATCH_NAME).tripped_patch_path == (
        TRIPPED_PATCH_NAME
    )


def test_a_tripped_patch_path_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="tripped_patch_path"):
        _record(tripped_patch_path="")


def test_a_non_empty_tripped_patch_path_is_accepted() -> None:
    """The sibling success to the refusal above."""
    assert _record(tripped_patch_path="tripped.diff").tripped_patch_path == "tripped.diff"


def test_the_removed_tripped_verdict_shape_no_longer_loads(tmp_path: Path) -> None:
    write_attempt_record(
        tmp_path / "attempt.json", _record(tripped_patch_path=TRIPPED_PATCH_NAME)
    )
    body = json.loads((tmp_path / "attempt.json").read_text())
    body["tripped_verdict"] = "pass"
    (tmp_path / "attempt.json").write_text(json.dumps(body))
    with pytest.raises(ValueError, match="unexpected"):
        load_attempt_record(tmp_path / "attempt.json")


# --- the attempt path never grades a tripped cell ---


def _attempt_dir(tmp_path: Path, *, tripped: bool) -> Path:
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    (attempt_dir / "patch.diff").write_text(_GOOD_PATCH)
    (attempt_dir / "transcript.txt").write_text("read the task; wrote the fix\n")
    if tripped:
        (attempt_dir / TRIPPED_PATCH_NAME).write_text(
            "diff --git a/src/app.py b/src/app.py\n"
        )
    return attempt_dir


def test_a_tripped_cell_never_reaches_the_grader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deadline-expiry recovery cannot re-enter grading: no grade call."""
    calls: list[object] = []

    def fail_grade(*args: object, **kwargs: object) -> Receipt:
        calls.append(args)
        raise AssertionError("the attempt path must not grade a tripped cell")

    monkeypatch.setattr(attempt_module, "grade", fail_grade)
    attempt_dir = _attempt_dir(tmp_path, tripped=True)

    record = attempt_module._finish_attempt(
        workspace=WorkspaceResult(
            WorkspaceCode.BUDGET_EXCEEDED, "over budget", None, "b" * 40
        ),
        task_dir=tmp_path / "task",
        attempt_dir=attempt_dir,
        patch_path=attempt_dir / "patch.diff",
        transcript_path=attempt_dir / "transcript.txt",
        manifest=_manifest(),
        effective_command=["fake-agent"],
        timeout=30.0,
        rung=None,
        digest="a" * 64,
    )

    assert calls == []
    assert record.code is AttemptCode.BUDGET_EXCEEDED
    assert record.verdict is None
    assert record.tripped_patch_path == TRIPPED_PATCH_NAME
    assert load_attempt_record(attempt_dir / "attempt.json") == record


def test_a_tripped_cell_without_a_harvested_patch_records_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No harvested patch: the record names no secondary, and still no grade."""
    calls: list[object] = []

    def fail_grade(*args: object, **kwargs: object) -> Receipt:
        calls.append(args)
        raise AssertionError("the attempt path must not grade a tripped cell")

    monkeypatch.setattr(attempt_module, "grade", fail_grade)
    attempt_dir = _attempt_dir(tmp_path, tripped=False)

    record = attempt_module._finish_attempt(
        workspace=WorkspaceResult(
            WorkspaceCode.BUDGET_EXCEEDED, "over budget", None, "b" * 40
        ),
        task_dir=tmp_path / "task",
        attempt_dir=attempt_dir,
        patch_path=attempt_dir / "patch.diff",
        transcript_path=attempt_dir / "transcript.txt",
        manifest=_manifest(),
        effective_command=["fake-agent"],
        timeout=30.0,
        rung=None,
        digest="a" * 64,
    )

    assert calls == []
    assert record.tripped_patch_path is None


def test_a_normal_cell_still_reaches_the_grader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sibling success: removing tripped grading left delivered grading live."""
    calls: list[Path] = []

    def fake_grade(
        task_dir: Path, patch_path: Path, receipt_path: Path, **kwargs: object
    ) -> Receipt:
        calls.append(patch_path)
        return Receipt("t", DIGEST, Verdict.PASS, "ok", None)

    monkeypatch.setattr(attempt_module, "grade", fake_grade)
    attempt_dir = _attempt_dir(tmp_path, tripped=False)

    record = attempt_module._finish_attempt(
        workspace=WorkspaceResult(WorkspaceCode.OK, "done", 0, "b" * 40),
        task_dir=tmp_path / "task",
        attempt_dir=attempt_dir,
        patch_path=attempt_dir / "patch.diff",
        transcript_path=attempt_dir / "transcript.txt",
        manifest=_manifest(),
        effective_command=["fake-agent"],
        timeout=30.0,
        rung=None,
        digest="a" * 64,
    )

    assert calls == [attempt_dir / "patch.diff"]
    assert record.code is AttemptCode.OK
    assert record.verdict is Verdict.PASS
    assert record.tripped_patch_path is None
