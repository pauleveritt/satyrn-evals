import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import satyrn_evals.attempt as attempt_module
from satyrn_evals.attempt import attempt_dir_name, decide_refusal
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome, AttemptRecord
from satyrn_evals.errors import UsageError
from satyrn_evals.workspace import WorkspaceCode, WorkspaceResult

GOOD_PATCH = (
    "diff --git a/solution.py b/solution.py\n"
    "--- a/solution.py\n"
    "+++ b/solution.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def double(n):\n"
    "-    return n\n"
    "+    return n * 2\n"
)
TRANSCRIPT = "read the task; wrote the fix\n"


def _task(tasks_root: Path) -> Path:
    task_dir = tasks_root / "t"
    (task_dir / "base").mkdir(parents=True)
    (task_dir / "base" / "solution.py").write_text("def double(n): return n\n")
    (task_dir / "fixtures").mkdir()
    (task_dir / "fixtures" / "known-good.patch").write_text(GOOD_PATCH)
    (task_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "t",
                "contract": "Fix it.",
                "oracle": ["python", "-m", "pytest"],
                "expected_test_ids": ["test_solution.py::test_one"],
                "source_paths": ["solution.py"],
                "fixtures": {"known_good": "fixtures/known-good.patch"},
            }
        )
    )
    return task_dir


def _run_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
    transcript: bytes | None,
) -> tuple[AttemptRecord, Path]:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def fake_run_workspace(**kwargs: Any) -> WorkspaceResult:
        command = kwargs["command"]
        env = kwargs["environment"]
        assert command == ["fake-agent"]
        assert kwargs["base"] == tasks_root / "t" / "base"
        assert env[attempt_module.TASK_NAME_ENV] == "t"
        assert env[attempt_module.TASK_CONTRACT_ENV] == "Fix it."
        if patch is not None:
            Path(env[attempt_module.PATCH_ENV]).write_bytes(patch)
        if transcript is not None:
            Path(env[attempt_module.TRANSCRIPT_ENV]).write_bytes(transcript)
        return WorkspaceResult(
            WorkspaceCode.OK,
            "attempt command completed",
            7,
            "b" * 40,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", fake_run_workspace)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )
    return record, next(output.iterdir())


def test_valid_artifacts_proceed() -> None:
    assert decide_refusal(GOOD_PATCH, TRANSCRIPT) is None


def test_missing_patch_is_no_patch() -> None:
    assert decide_refusal(None, TRANSCRIPT) == "NO_PATCH"


def test_empty_patch_is_no_patch() -> None:
    assert decide_refusal("", TRANSCRIPT) == "NO_PATCH"


def test_whitespace_patch_is_no_patch() -> None:
    assert decide_refusal("   \n", TRANSCRIPT) == "NO_PATCH"


def test_non_diff_patch_is_patch_invalid() -> None:
    assert decide_refusal("this is not a unified diff\n", TRANSCRIPT) == "PATCH_INVALID"


def test_missing_transcript_is_transcript_missing() -> None:
    assert decide_refusal(GOOD_PATCH, None) == "TRANSCRIPT_MISSING"


def test_empty_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "") == "TRANSCRIPT_EMPTY"


def test_whitespace_transcript_is_transcript_empty() -> None:
    assert decide_refusal(GOOD_PATCH, "  \n") == "TRANSCRIPT_EMPTY"


def test_patch_checked_before_transcript() -> None:
    # both bad: patch fails first (spec: patch checks run first)
    assert decide_refusal(None, None) == "NO_PATCH"
    assert decide_refusal("not a diff\n", None) == "PATCH_INVALID"


def test_attempt_dir_name_is_deterministic_given_when() -> None:
    when = datetime(2026, 8, 18, 14, 15, 23, 123456, tzinfo=UTC)
    assert attempt_dir_name("format_number", when) == "format_number-20260818-141523-123456"


def test_attempt_dir_name_changes_with_when() -> None:
    a = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 1, tzinfo=UTC))
    b = attempt_dir_name("t", datetime(2026, 8, 18, 14, 15, 23, 2, tzinfo=UTC))
    assert a != b


def test_attempt_rejects_empty_command_before_creating_output(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="command is empty"):
        attempt_module.attempt(task="t", tasks_root=tasks_root, output=output, command=[])
    assert not output.exists()


def test_attempt_start_failure_removes_fresh_attempt_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def cannot_start(**_kwargs: object) -> WorkspaceResult:
        return WorkspaceResult(
            WorkspaceCode.COMMAND_UNAVAILABLE,
            "attempt command cannot start: not executable",
            None,
            "b" * 40,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", cannot_start)
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="cannot start"):
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=["missing-agent"]
        )
    assert list(output.iterdir()) == []


@pytest.mark.parametrize(
    ("patch", "transcript", "code"),
    [
        (None, TRANSCRIPT.encode(), AttemptCode.NO_PATCH),
        (GOOD_PATCH.encode(), None, AttemptCode.TRANSCRIPT_MISSING),
        (
            GOOD_PATCH.encode() + b"\xff\n",
            TRANSCRIPT.encode(),
            AttemptCode.PATCH_INVALID,
        ),
    ],
)
def test_attempt_records_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
    transcript: bytes | None,
    code: AttemptCode,
) -> None:
    record, attempt_dir = _run_attempt(tmp_path, monkeypatch, patch, transcript)
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code == code
    assert record.command_exit == 7
    assert record.patch_path == ("patch.diff" if patch is not None else None)
    assert record.transcript_path == (
        "transcript.txt" if transcript is not None else None
    )
    assert json.loads((attempt_dir / "attempt.json").read_text())["code"] == code


@pytest.mark.parametrize(
    ("workspace_code", "attempt_code", "retained"),
    [
        (WorkspaceCode.WORKSPACE_FAILED, AttemptCode.WORKSPACE_FAILED, None),
        (WorkspaceCode.COMMAND_TIMEOUT, AttemptCode.COMMAND_TIMEOUT, None),
        (
            WorkspaceCode.CLEANUP_FAILED,
            AttemptCode.CLEANUP_FAILED,
            "/tmp/retained-worktree",
        ),
    ],
)
def test_attempt_records_workspace_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workspace_code: WorkspaceCode,
    attempt_code: AttemptCode,
    retained: str | None,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def refused(**_kwargs: object) -> WorkspaceResult:
        return WorkspaceResult(
            workspace_code,
            f"workspace result: {workspace_code}",
            None,
            "b" * 40,
            retained,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", refused)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )
    assert record.outcome is AttemptOutcome.REFUSED
    assert record.code is attempt_code
    assert record.message == f"workspace result: {workspace_code}"
    assert record.command_exit is None
    assert record.workspace_base_sha == "b" * 40
    assert record.retained_path == retained


def test_workspace_refusal_rejects_unhandled_code() -> None:
    unavailable = WorkspaceResult(
        WorkspaceCode.COMMAND_UNAVAILABLE,
        "unavailable",
        None,
        "a" * 40,
    )
    with pytest.raises(AssertionError, match="unexpected workspace outcome"):
        attempt_module._workspace_refusal(unavailable)


@pytest.mark.parametrize(
    ("workspace_code", "expected_code", "retained"),
    [
        (
            WorkspaceCode.CLEANUP_FAILED,
            AttemptCode.CLEANUP_FAILED,
            "/tmp/retained-worktree",
        ),
        (WorkspaceCode.OK, AttemptCode.PATCH_INVALID, None),
    ],
)
def test_artifact_read_failure_cannot_hide_workspace_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workspace_code: WorkspaceCode,
    expected_code: AttemptCode,
    retained: str | None,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).mkdir()
        return WorkspaceResult(
            workspace_code,
            "workspace cleanup failed" if retained else "attempt command completed",
            0 if workspace_code is WorkspaceCode.OK else None,
            "b" * 40,
            retained,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", run)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )

    assert record.code is expected_code
    assert record.retained_path == retained
    assert "not a regular file" in record.message
    attempt_dir = next(output.iterdir())
    assert json.loads((attempt_dir / "attempt.json").read_text())["code"] == expected_code


@pytest.mark.parametrize("primary", [KeyboardInterrupt(), MemoryError("read")])
def test_artifact_baseexception_preserves_cleanup_recovery_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    primary: BaseException,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    retained = "/tmp/retained-worktree"

    monkeypatch.setattr(
        attempt_module,
        "run_workspace",
        lambda **_kwargs: WorkspaceResult(
            WorkspaceCode.CLEANUP_FAILED,
            "workspace cleanup failed",
            None,
            "b" * 40,
            retained,
        ),
    )
    monkeypatch.setattr(
        attempt_module,
        "_read_artifact",
        lambda *_args: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(type(primary)) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert primary.__notes__ == [
        f"workspace cleanup failed; retained at {retained}"
    ]


def test_artifact_baseexception_without_cleanup_evidence_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    primary = KeyboardInterrupt()
    monkeypatch.setattr(
        attempt_module,
        "run_workspace",
        lambda **_kwargs: WorkspaceResult(
            WorkspaceCode.OK, "attempt command completed", 0, "b" * 40
        ),
    )
    monkeypatch.setattr(
        attempt_module,
        "_read_artifact",
        lambda *_args: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(KeyboardInterrupt) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert not hasattr(primary, "__notes__")


@pytest.mark.parametrize("failure", ["digest", "record"])
def test_post_workspace_baseexception_preserves_cleanup_recovery_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)
    retained = "/tmp/retained-worktree"
    primary = MemoryError(failure)

    def run(**kwargs: Any) -> WorkspaceResult:
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).write_text(
            TRANSCRIPT
        )
        return WorkspaceResult(
            WorkspaceCode.CLEANUP_FAILED,
            "workspace cleanup failed",
            0,
            "b" * 40,
            retained,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", run)
    if failure == "digest":
        monkeypatch.setattr(
            attempt_module,
            "patch_digest",
            lambda _value: (_ for _ in ()).throw(primary),
        )
    else:
        monkeypatch.setattr(
            attempt_module,
            "write_attempt_record",
            lambda *_args: (_ for _ in ()).throw(primary),
        )

    with pytest.raises(MemoryError) as raised:
        attempt_module.attempt(
            task="t",
            tasks_root=tasks_root,
            output=tmp_path / "attempts",
            command=["fake-agent"],
        )

    assert raised.value is primary
    assert primary.__notes__ == [
        f"workspace cleanup failed; retained at {retained}"
    ]


def test_transcript_read_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_text(GOOD_PATCH)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).mkdir()
        return WorkspaceResult(
            WorkspaceCode.OK,
            "attempt command completed",
            0,
            "b" * 40,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", run)
    record = attempt_module.attempt(
        task="t",
        tasks_root=tasks_root,
        output=tmp_path / "attempts",
        command=["fake-agent"],
    )
    assert record.code is AttemptCode.TRANSCRIPT_MISSING
    assert "not a regular file" in record.message


@pytest.mark.parametrize("patch", [None, b"  \n"])
def test_patch_absence_precedes_transcript_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
) -> None:
    tasks_root = tmp_path / "tasks"
    _task(tasks_root)

    def run(**kwargs: Any) -> WorkspaceResult:
        if patch is not None:
            Path(kwargs["environment"][attempt_module.PATCH_ENV]).write_bytes(patch)
        Path(kwargs["environment"][attempt_module.TRANSCRIPT_ENV]).mkdir()
        return WorkspaceResult(
            WorkspaceCode.OK,
            "attempt command completed",
            0,
            "b" * 40,
        )

    monkeypatch.setattr(attempt_module, "run_workspace", run)
    output = tmp_path / "attempts"
    record = attempt_module.attempt(
        task="t", tasks_root=tasks_root, output=output, command=["fake-agent"]
    )

    assert record.code is AttemptCode.NO_PATCH
    attempt_dir = next(output.iterdir())
    assert json.loads((attempt_dir / "attempt.json").read_text())["code"] == "NO_PATCH"


def test_artifact_read_oserror_is_contained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "artifact"
    artifact.write_text("value")
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda _path: (_ for _ in ()).throw(OSError("read")),
    )
    value, error = attempt_module._read_artifact(artifact, "patch")
    assert value is None
    assert error is not None and "cannot read" in error
