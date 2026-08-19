import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

import satyrn_evals.attempt as attempt_module
from satyrn_evals.attempt import attempt_dir_name, decide_refusal
from satyrn_evals.attempt_record import AttemptOutcome, AttemptRecord
from satyrn_evals.errors import UsageError

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

    def fake_run(
        command: list[str], *, cwd: Path, env: dict[str, str], capture_output: bool
    ) -> subprocess.CompletedProcess[bytes]:
        assert command == ["fake-agent"]
        assert (Path(cwd) / "solution.py").is_file()
        assert env[attempt_module.TASK_NAME_ENV] == "t"
        assert env[attempt_module.TASK_CONTRACT_ENV] == "Fix it."
        assert capture_output is True
        if patch is not None:
            Path(env[attempt_module.PATCH_ENV]).write_bytes(patch)
        if transcript is not None:
            Path(env[attempt_module.TRANSCRIPT_ENV]).write_bytes(transcript)
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(attempt_module.subprocess, "run", fake_run)
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

    def cannot_start(*_args: object, **_kwargs: object) -> Never:
        raise OSError("not executable")

    monkeypatch.setattr(attempt_module.subprocess, "run", cannot_start)
    output = tmp_path / "attempts"
    with pytest.raises(UsageError, match="cannot start"):
        attempt_module.attempt(
            task="t", tasks_root=tasks_root, output=output, command=["missing-agent"]
        )
    assert list(output.iterdir()) == []


@pytest.mark.parametrize(
    ("patch", "transcript", "code"),
    [
        (None, TRANSCRIPT.encode(), "NO_PATCH"),
        (GOOD_PATCH.encode(), None, "TRANSCRIPT_MISSING"),
        (GOOD_PATCH.encode() + b"\xff\n", TRANSCRIPT.encode(), "PATCH_INVALID"),
    ],
)
def test_attempt_records_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: bytes | None,
    transcript: bytes | None,
    code: str,
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
